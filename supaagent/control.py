#!/usr/bin/env python3
"""
SupaAgent local control panel.

Double-click START_SUPAAGENT.bat to open a browser UI for the common local
workflow: start services, generate a hero still, animate it, and stage approved
outputs for BLKK Star Hub. The server binds to 127.0.0.1 and only exposes the
allow-listed commands below.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parent
ROOT = PIPELINE.parent
MONOREPO = ROOT.parent
WEB_HUB_PUBLIC = MONOREPO / "apps" / "web-hub" / "public"
START_SCRIPT = PIPELINE / "supaagent" / "start.py"
GEN_IMAGE = PIPELINE / "media" / "gen_image.py"
GEN_VIDEO = PIPELINE / "media" / "gen_video.py"
WORKFLOWS = PIPELINE / "media" / "workflows"
ASSETS = ROOT / "assets"
VIDEO_ASSETS = ASSETS / "video"

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
JOBS: dict[str, dict[str, Any]] = {}
JOBS_LOCK = threading.Lock()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if not length:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def parse_marker(output: str, marker: str) -> Any:
    for line in output.splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):])
            except json.JSONDecodeError:
                return line[len(marker):]
    return None


def comfyui_ready() -> bool:
    try:
        with urlopen("http://127.0.0.1:8188/system_stats", timeout=4):
            return True
    except (OSError, URLError):
        return False


def require_media_ready(kind: str) -> None:
    workflow = WORKFLOWS / ("wan_i2v.api.json" if kind == "video" else "flux_image.api.json")
    if not workflow.exists():
        raise ValueError(
            "{} is missing. Open ComfyUI, create/test the {} workflow, then save it in API format to that exact path.".format(
                rel(workflow),
                "image-to-video" if kind == "video" else "image",
            )
        )
    if not comfyui_ready():
        raise ValueError("ComfyUI is not running yet. Click Start ComfyUI, wait until Readiness says comfyui: ready, then try again.")


def run_capture(args: list[str], timeout: int | None = None) -> dict[str, Any]:
    flags = 0
    if os.name == "nt":
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            args,
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            creationflags=flags,
            check=False,
        )
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "output": proc.stdout}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "returncode": -1, "output": str(exc)}


def create_job(label: str, args: list[str], marker: str | None = None) -> dict[str, Any]:
    job_id = "job_" + uuid.uuid4().hex[:10]
    job = {
        "id": job_id,
        "label": label,
        "status": "queued",
        "started_at": None,
        "finished_at": None,
        "returncode": None,
        "output": "",
        "marker": marker,
        "result": None,
    }
    with JOBS_LOCK:
        JOBS[job_id] = job

    def worker() -> None:
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "running"
            JOBS[job_id]["started_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        result = run_capture(args)
        parsed = parse_marker(result["output"], marker) if marker else None
        with JOBS_LOCK:
            JOBS[job_id].update(
                {
                    "status": "complete" if result["ok"] else "failed",
                    "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "returncode": result["returncode"],
                    "output": result["output"][-12000:],
                    "result": parsed,
                }
            )

    threading.Thread(target=worker, daemon=True).start()
    return job


def setup_state() -> dict[str, Any]:
    comfyui_dir = ""
    comfyui_path_ok = False
    cfg_path = PIPELINE / "supaagent" / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            comfyui_dir = str(cfg.get("services", {}).get("comfyui", {}).get("working_dir", ""))
            expanded = os.path.expandvars(
                comfyui_dir
                .replace("{ROOT}", str(ROOT))
                .replace("{PIPELINE}", str(PIPELINE))
                .replace("{MONOREPO}", str(MONOREPO))
            )
            comfyui_path_ok = bool(comfyui_dir) and "%" not in expanded and Path(expanded).exists()
        except Exception:  # noqa: BLE001
            comfyui_path_ok = False
    return {
        "pipeline_config": (PIPELINE / "config.json").exists(),
        "supa_config": (PIPELINE / "supaagent" / "config.json").exists(),
        "comfyui_path": comfyui_path_ok,
        "image_workflow": (WORKFLOWS / "flux_image.api.json").exists(),
        "video_workflow": (WORKFLOWS / "wan_i2v.api.json").exists(),
        "web_hub_public": WEB_HUB_PUBLIC.exists(),
    }


def status_payload() -> dict[str, Any]:
    res = run_capture([sys.executable, str(START_SCRIPT), "--status-only"], timeout=45)
    services = parse_marker(res["output"], "SUPAAGENT_STATUS_JSON=")
    return {
        "setup": setup_state(),
        "services": services.get("services", []) if isinstance(services, dict) else [],
        "raw": res["output"],
    }


def list_assets() -> dict[str, Any]:
    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    video_exts = {".mp4", ".webm"}
    images = []
    videos = []
    if ASSETS.exists():
        for path in sorted(ASSETS.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.suffix.lower() in image_exts:
                images.append({"path": rel(path), "name": path.name, "mtime": path.stat().st_mtime})
    if VIDEO_ASSETS.exists():
        for path in sorted(VIDEO_ASSETS.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if path.suffix.lower() in video_exts:
                videos.append({"path": rel(path), "name": path.name, "mtime": path.stat().st_mtime})
    return {"images": images[:80], "videos": videos[:80]}


def safe_int(value: Any, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(min_value, min(parsed, max_value))


def slug_name(value: Any, default: str) -> str:
    raw = str(value or default).strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in raw)
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or default


def start_service(data: dict[str, Any]) -> dict[str, Any]:
    only = str(data.get("only") or "").strip()
    args = [sys.executable, str(START_SCRIPT)]
    if only:
        args += ["--only", only]
    return create_job("Start " + (only or "SupaAgent stack"), args, "SUPAAGENT_STATUS_JSON=")


def generate_image(data: dict[str, Any]) -> dict[str, Any]:
    require_media_ready("image")
    name = slug_name(data.get("name"), "blkkstarhub-hero-01")
    prompt = str(data.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Prompt is required.")
    args = [
        sys.executable,
        str(GEN_IMAGE),
        "--name",
        name,
        "--prompt",
        prompt,
        "--width",
        str(safe_int(data.get("width"), 1920, 512, 4096)),
        "--height",
        str(safe_int(data.get("height"), 1080, 512, 4096)),
        "--steps",
        str(safe_int(data.get("steps"), 28, 1, 80)),
    ]
    seed = safe_int(data.get("seed"), -1, -1, 2147483647)
    if seed >= 0:
        args += ["--seed", str(seed)]
    return create_job("Generate still: " + name, args, "IMAGE_RESULT_JSON=")


def generate_video(data: dict[str, Any]) -> dict[str, Any]:
    require_media_ready("video")
    name = slug_name(data.get("name"), "blkkstarhub-hero-loop-01")
    prompt = str(data.get("prompt") or "").strip()
    image = str(data.get("image") or "").strip()
    if not prompt:
        raise ValueError("Prompt is required.")
    if image.startswith("/") or ".." in Path(image).parts:
        raise ValueError("Choose an image from the asset list.")
    args = [
        sys.executable,
        str(GEN_VIDEO),
        "--name",
        name,
        "--prompt",
        prompt,
        "--frames",
        str(safe_int(data.get("frames"), 49, 8, 241)),
        "--fps",
        str(safe_int(data.get("fps"), 16, 6, 60)),
    ]
    seed = safe_int(data.get("seed"), -1, -1, 2147483647)
    if seed >= 0:
        args += ["--seed", str(seed)]
    if image:
        args += ["--image", image]
    return create_job("Animate still: " + name, args, "VIDEO_RESULT_JSON=")


def copy_to_hub(data: dict[str, Any]) -> dict[str, Any]:
    src_rel = str(data.get("path") or "").strip()
    media_type = str(data.get("type") or "image").strip()
    target_name = Path(str(data.get("target") or Path(src_rel).name)).name
    if not src_rel or src_rel.startswith("/") or ".." in Path(src_rel).parts:
        raise ValueError("Choose an output from the asset list.")
    src = ROOT / src_rel
    if not src.exists():
        raise ValueError("Output does not exist: " + src_rel)
    subdir = "video" if media_type == "video" else "heroes"
    dst_dir = WEB_HUB_PUBLIC / "hub" / subdir
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / target_name
    shutil.copy2(src, dst)
    return {"ok": True, "source": rel(src), "target": str(dst.relative_to(WEB_HUB_PUBLIC)).replace("\\", "/")}


def open_local_target(data: dict[str, Any]) -> dict[str, Any]:
    target = str(data.get("target") or "").strip()
    allowed = {
        "supa_config": PIPELINE / "supaagent" / "config.json",
        "pipeline_config": PIPELINE / "config.json",
        "workflows": WORKFLOWS,
        "assets": ASSETS,
        "hub_public": WEB_HUB_PUBLIC / "hub",
    }
    path = allowed.get(target)
    if not path:
        raise ValueError("Unknown local target.")
    if not path.exists():
        raise ValueError("Path does not exist yet: " + rel(path))
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(path)])
    return {"ok": True, "path": rel(path)}


HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SupaAgent Control Panel</title>
  <style>
    :root { --bg:#080808; --panel:#111; --panel2:#151515; --line:rgba(255,255,255,.12); --fg:#f4efe7; --muted:rgba(244,239,231,.62); --dim:rgba(244,239,231,.38); --gold:#c9a84c; --bad:#d86b5e; --good:#71c995; }
    * { box-sizing: border-box; }
    body { margin:0; background:radial-gradient(80% 80% at 80% 0%, rgba(201,168,76,.10), transparent 55%), var(--bg); color:var(--fg); font-family: Inter, "DM Sans", system-ui, sans-serif; }
    header { padding:28px clamp(18px,4vw,48px); border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:18px; align-items:center; position:sticky; top:0; background:rgba(8,8,8,.84); backdrop-filter:blur(14px); z-index:2; }
    h1, h2 { font-family: Georgia, serif; font-weight:400; letter-spacing:.02em; margin:0; }
    h1 { font-size:clamp(28px,5vw,52px); }
    h2 { font-size:24px; }
    p { color:var(--muted); line-height:1.65; }
    main { padding:32px clamp(18px,4vw,48px) 64px; max-width:1280px; margin:0 auto; }
    .grid { display:grid; grid-template-columns: repeat(12, 1fr); gap:18px; }
    .card { grid-column:span 6; background:linear-gradient(180deg, rgba(255,255,255,.035), rgba(255,255,255,.015)); border:1px solid var(--line); padding:22px; min-height:170px; }
    .card.full { grid-column:1 / -1; }
    .card.third { grid-column:span 4; }
    label { display:block; color:var(--dim); text-transform:uppercase; letter-spacing:.18em; font-size:10px; margin:14px 0 7px; }
    input, textarea, select { width:100%; border:1px solid var(--line); background:#090909; color:var(--fg); padding:12px 13px; font:inherit; outline:none; }
    textarea { min-height:118px; resize:vertical; }
    button { border:1px solid var(--gold); background:transparent; color:var(--gold); padding:12px 16px; text-transform:uppercase; letter-spacing:.12em; font-size:11px; cursor:pointer; margin:8px 8px 0 0; }
    button.primary { background:var(--gold); color:#080808; }
    button:hover { filter:brightness(1.08); }
    .status { display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; }
    .pill { border:1px solid var(--line); padding:7px 10px; color:var(--muted); font-size:12px; }
    .pill.good { border-color:rgba(113,201,149,.45); color:var(--good); }
    .pill.bad { border-color:rgba(216,107,94,.45); color:var(--bad); }
    .pill.warn { border-color:rgba(201,168,76,.45); color:var(--gold); }
    .jobs { display:grid; gap:10px; margin-top:14px; }
    .job { background:var(--panel2); border:1px solid var(--line); padding:14px; }
    pre { max-height:260px; overflow:auto; background:#050505; border:1px solid var(--line); padding:12px; color:var(--muted); white-space:pre-wrap; }
    .split { display:grid; grid-template-columns: 1fr 1fr; gap:12px; }
    .small { font-size:12px; color:var(--dim); }
    @media (max-width: 860px) { .card, .card.third { grid-column:1 / -1; } .split { grid-template-columns:1fr; } header { position:relative; } }
  </style>
</head>
<body>
  <header>
    <div>
      <div class="small">Local only - 127.0.0.1</div>
      <h1>SupaAgent Control Panel</h1>
    </div>
    <button onclick="refreshAll()">Refresh Status</button>
  </header>
  <main>
    <section class="grid">
      <div class="card full">
        <h2>Readiness</h2>
        <p>This panel starts local services and creates local media only. It does not publish, post, message, spend money, or delete files.</p>
        <div id="setup" class="status"></div>
        <div id="services" class="status"></div>
        <button onclick="openTarget('supa_config')">Open SupaAgent Config</button>
        <button onclick="openTarget('workflows')">Open Workflows Folder</button>
        <button onclick="window.open('http://127.0.0.1:8188/', '_blank')">Open ComfyUI</button>
      </div>

      <div class="card third">
        <h2>1. Start Stack</h2>
        <p>Start only what you need. For hero images, ComfyUI is required. For previewing the hub, start BLKK Star Hub.</p>
        <button class="primary" onclick="startService('comfyui')">Start ComfyUI</button>
        <button onclick="startService('blkkstarhub')">Start Hub</button>
        <button onclick="startService('openclaw')">Start OpenClaw</button>
      </div>

      <div class="card">
        <h2>2. Generate Hero Still</h2>
        <label>Name</label>
        <input id="imgName" value="blkkstarhub-hero-01">
        <label>Prompt</label>
        <textarea id="imgPrompt">premium Pan-African digital commerce hub in Accra at dusk, black and gold institutional luxury, marketplace, autos, estate, crafted products, digital trade floor, cinematic editorial photography, deep contrast, practical luxury, no text, no logos, no watermark</textarea>
        <div class="split">
          <div><label>Width</label><input id="imgWidth" value="1920"></div>
          <div><label>Height</label><input id="imgHeight" value="1080"></div>
        </div>
        <div class="split">
          <div><label>Steps</label><input id="imgSteps" value="28"></div>
          <div><label>Seed</label><input id="imgSeed" value="101"></div>
        </div>
        <button class="primary" onclick="generateImage()">Generate Still</button>
      </div>

      <div class="card">
        <h2>3. Animate Still</h2>
        <label>Still Image</label>
        <select id="videoImage"></select>
        <label>Name</label>
        <input id="vidName" value="blkkstarhub-hero-loop-01">
        <label>Motion Prompt</label>
        <textarea id="vidPrompt">slow cinematic push-in, subtle parallax, controlled gold light sweep, faint dust in the air, premium digital marketplace energy, restrained motion, no text, no morphing, no logo</textarea>
        <div class="split">
          <div><label>Frames</label><input id="vidFrames" value="49"></div>
          <div><label>FPS</label><input id="vidFps" value="16"></div>
        </div>
        <label>Seed</label>
        <input id="vidSeed" value="101">
        <button class="primary" onclick="generateVideo()">Animate Selected Still</button>
      </div>

      <div class="card">
        <h2>4. Stage For Hub</h2>
        <p>After you like an output, copy it into the BLKK Star Hub public folder. This does not edit the page or publish it.</p>
        <label>Still Output</label>
        <select id="copyImage"></select>
        <label>Hub Hero Filename</label>
        <input id="copyImageName" value="blkkstarhub-hero-01.png">
        <button onclick="copyToHub('image')">Copy Still To Hub</button>
        <label>Video Output</label>
        <select id="copyVideo"></select>
        <label>Hub Video Filename</label>
        <input id="copyVideoName" value="blkkstarhub-hero-loop-01.mp4">
        <button onclick="copyToHub('video')">Copy Video To Hub</button>
      </div>

      <div class="card full">
        <h2>Jobs</h2>
        <div id="jobs" class="jobs"></div>
      </div>
    </section>
  </main>
  <script>
    const $ = (id) => document.getElementById(id);
    async function api(path, options = {}) {
      const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...options });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Request failed');
      return data;
    }
    function pill(label, state) {
      const cls = state === true ? 'good' : state === false ? 'bad' : 'warn';
      const txt = state === true ? 'ready' : state === false ? 'missing' : state;
      return `<span class="pill ${cls}">${label}: ${txt}</span>`;
    }
    async function refreshStatus() {
      const data = await api('/api/status');
      const s = data.setup || {};
      $('setup').innerHTML = [
        pill('pipeline config', s.pipeline_config),
        pill('supa config', s.supa_config),
        pill('ComfyUI path', s.comfyui_path),
        pill('image workflow', s.image_workflow),
        pill('video workflow', s.video_workflow),
        pill('web hub public', s.web_hub_public)
      ].join('');
      $('services').innerHTML = (data.services || []).map((x) => {
        const cls = x.status === 'ready' ? 'good' : x.status === 'down' ? 'bad' : 'warn';
        return `<span class="pill ${cls}">${x.name}: ${x.status}</span>`;
      }).join('');
    }
    async function refreshAssets() {
      const data = await api('/api/assets');
      const imgOptions = (data.images || []).map((x) => `<option value="${x.path}">${x.path}</option>`).join('');
      const vidOptions = (data.videos || []).map((x) => `<option value="${x.path}">${x.path}</option>`).join('');
      $('videoImage').innerHTML = imgOptions || '<option value="">No stills yet</option>';
      $('copyImage').innerHTML = imgOptions || '<option value="">No stills yet</option>';
      $('copyVideo').innerHTML = vidOptions || '<option value="">No videos yet</option>';
    }
    async function refreshJobs() {
      const data = await api('/api/jobs');
      $('jobs').innerHTML = (data.jobs || []).map((j) => `
        <div class="job">
          <strong>${j.label}</strong>
          <span class="pill ${j.status === 'complete' ? 'good' : j.status === 'failed' ? 'bad' : 'warn'}">${j.status}</span>
          ${j.result ? `<pre>${JSON.stringify(j.result, null, 2)}</pre>` : ''}
          ${j.output ? `<details><summary>Output</summary><pre>${j.output}</pre></details>` : ''}
        </div>`).join('') || '<p>No jobs yet.</p>';
    }
    async function refreshAll() {
      await Promise.all([refreshStatus(), refreshAssets(), refreshJobs()]);
    }
    async function startService(only) {
      try {
        await api('/api/start-service', { method: 'POST', body: JSON.stringify({ only }) });
        setTimeout(refreshAll, 900);
      } catch (err) {
        alert(err.message);
      }
    }
    async function generateImage() {
      try {
        await api('/api/generate-image', { method: 'POST', body: JSON.stringify({
          name: $('imgName').value, prompt: $('imgPrompt').value, width: $('imgWidth').value,
          height: $('imgHeight').value, steps: $('imgSteps').value, seed: $('imgSeed').value
        })});
        setTimeout(refreshJobs, 900);
      } catch (err) {
        alert(err.message);
      }
    }
    async function generateVideo() {
      try {
        await api('/api/generate-video', { method: 'POST', body: JSON.stringify({
          name: $('vidName').value, prompt: $('vidPrompt').value, image: $('videoImage').value,
          frames: $('vidFrames').value, fps: $('vidFps').value, seed: $('vidSeed').value
        })});
        setTimeout(refreshJobs, 900);
      } catch (err) {
        alert(err.message);
      }
    }
    async function copyToHub(type) {
      try {
        const path = type === 'video' ? $('copyVideo').value : $('copyImage').value;
        const target = type === 'video' ? $('copyVideoName').value : $('copyImageName').value;
        const res = await api('/api/copy-to-hub', { method: 'POST', body: JSON.stringify({ type, path, target }) });
        alert('Copied to public/hub/' + res.target);
      } catch (err) {
        alert(err.message);
      }
    }
    async function openTarget(target) {
      try {
        await api('/api/open-target', { method: 'POST', body: JSON.stringify({ target }) });
      } catch (err) {
        alert(err.message);
      }
    }
    setInterval(refreshJobs, 4000);
    setInterval(refreshAssets, 8000);
    refreshAll();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def send_json(self, payload: Any, status: int = 200) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        try:
            if self.path == "/" or self.path.startswith("/?"):
                raw = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif self.path == "/api/status":
                self.send_json(status_payload())
            elif self.path == "/api/assets":
                self.send_json(list_assets())
            elif self.path == "/api/jobs":
                with JOBS_LOCK:
                    jobs = sorted(JOBS.values(), key=lambda j: j["id"], reverse=True)
                self.send_json({"jobs": jobs[:50]})
            else:
                self.send_json({"error": "Not found"}, 404)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, 500)

    def do_POST(self) -> None:  # noqa: N802
        try:
            data = read_json_body(self)
            if self.path == "/api/start-service":
                self.send_json(start_service(data), 202)
            elif self.path == "/api/generate-image":
                self.send_json(generate_image(data), 202)
            elif self.path == "/api/generate-video":
                self.send_json(generate_video(data), 202)
            elif self.path == "/api/copy-to-hub":
                self.send_json(copy_to_hub(data))
            elif self.path == "/api/open-target":
                self.send_json(open_local_target(data))
            else:
                self.send_json({"error": "Not found"}, 404)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, 400)


def available_port() -> int:
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((HOST, port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free local port found for SupaAgent control panel.")


def main() -> int:
    port = available_port()
    server = ThreadingHTTPServer((HOST, port), Handler)
    url = "http://{}:{}/".format(HOST, port)
    print("SupaAgent Control Panel")
    print("Open: " + url)
    print("Close this window to stop the panel. Started services keep running.")
    if os.environ.get("SUPAAGENT_NO_BROWSER") != "1":
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SupaAgent control panel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
