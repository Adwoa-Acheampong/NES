#!/usr/bin/env python3
"""
run_pipeline.py  -  The single entry point OpenClaw (or you) calls.

Chains the whole flow for one asset:
    render (UE5 headless)  ->  build 360 tour  ->  [package pixel stream]  ->  publish

OpenClaw just runs ONE command and gets back a JSON summary it can relay to you
over Telegram/WhatsApp.

    python pipeline/run_pipeline.py --asset "pipeline/hot_folder/Modern Villa.fbx" ^
        --project-name "Modern Villa" --category architecture

If --asset is omitted, the newest accepted file in pipeline/hot_folder is used.

Flags:
    --no-pixelstream   skip the Pixel Streaming package (default packages only flagships)
    --flagship         also build + package Pixel Streaming for this asset
    --method git|sftp|s3|none   override publish method
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    p = os.path.join(ROOT, "pipeline", "config.json")
    if not os.path.exists(p):
        print("ERROR: pipeline/config.json not found. Copy config.example.json -> config.json "
              "and fill in your paths.", file=sys.stderr)
        sys.exit(2)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(name):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def resolve_asset(asset, cfg):
    """Resolve an explicit asset path, or choose the newest accepted hot-folder file."""
    if asset:
        path = asset if os.path.isabs(asset) else os.path.join(ROOT, asset)
        if not os.path.exists(path):
            return None, {
                "ok": False,
                "source": "explicit",
                "error": "asset not found: {}".format(path),
            }
        return path, {
            "ok": True,
            "source": "explicit",
            "asset": os.path.relpath(path, ROOT),
        }

    intake = cfg.get("intake", {})
    accepted = tuple(ext.lower() for ext in intake.get("accepted_formats", []))
    hot = cfg.get("paths", {}).get("hot_folder", os.path.join("pipeline", "hot_folder"))
    hot_abs = hot if os.path.isabs(hot) else os.path.join(ROOT, hot)
    if not os.path.isdir(hot_abs):
        return None, {
            "ok": False,
            "source": "hot_folder",
            "error": "hot folder not found: {}".format(hot_abs),
        }

    candidates = []
    for name in os.listdir(hot_abs):
        path = os.path.join(hot_abs, name)
        if not os.path.isfile(path):
            continue
        if accepted and not name.lower().endswith(accepted):
            continue
        candidates.append(path)

    if not candidates:
        return None, {
            "ok": False,
            "source": "hot_folder",
            "error": "no accepted assets found in {}".format(hot_abs),
            "accepted_formats": list(accepted),
        }

    path = max(candidates, key=os.path.getmtime)
    return path, {
        "ok": True,
        "source": "hot_folder_newest",
        "asset": os.path.relpath(path, ROOT),
        "accepted_formats": list(accepted),
    }


def run(cmd, cwd=ROOT, label=""):
    print("\n[run_pipeline] === {} ===".format(label))
    print("[run_pipeline] $ " + " ".join('"{}"'.format(c) if " " in c else c for c in cmd))
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc


def extract_json(stdout, marker):
    for line in stdout.splitlines():
        if line.startswith(marker):
            try:
                return json.loads(line[len(marker):])
            except json.JSONDecodeError:
                return None
    return None


def ue_cmd(cfg, script_rel, extra_args):
    return [
        cfg["unreal"]["editor_cmd"],
        cfg["unreal"]["project"],
        "-run=pythonscript",
        "-script={}".format(os.path.join(ROOT, "pipeline", "ue", script_rel)),
        "-unattended", "-nosplash", "-stdout", "-FullStdOutLogOutput",
        "--",
        "--config", os.path.join(ROOT, "pipeline", "config.json"),
    ] + extra_args


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", default=None,
                    help="asset path; defaults to newest accepted file in pipeline/hot_folder")
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--category", default="architecture", choices=["architecture", "automotive"])
    ap.add_argument("--flagship", action="store_true", help="also build Pixel Streaming package")
    ap.add_argument("--no-pixelstream", action="store_true")
    ap.add_argument("--method", default=None, choices=["git", "sftp", "s3", "none"])
    args = ap.parse_args()

    cfg = load_config()
    slug = slugify(args.project_name)
    summary = {"project": args.project_name, "slug": slug, "category": args.category,
               "stages": {}, "ok": False}
    t0 = time.time()
    asset_abs, intake = resolve_asset(args.asset, cfg)
    summary["stages"]["intake"] = intake
    if not intake.get("ok"):
        summary["failed_stage"] = "intake"
        _finish(summary, t0)
        return
    summary["asset"] = os.path.relpath(asset_abs, ROOT)

    # ---- Stage 1: UE render -------------------------------------------------
    p = run(ue_cmd(cfg, "render_pipeline.py",
                   ["--asset", asset_abs, "--project-name", args.project_name,
                    "--category", args.category]),
            label="UE render (cinematic + 360)")
    render = extract_json(p.stdout, "RENDER_RESULT_JSON=")
    summary["stages"]["render"] = render or {"ok": False, "note": "no result marker"}
    if not (render and render.get("ok")):
        summary["failed_stage"] = "render"
        _finish(summary, t0)
        return

    # ---- Stage 2: Pannellum tour -------------------------------------------
    p = run(["python", os.path.join(ROOT, "pipeline", "build_tour.py"),
             "--slug", slug, "--title", args.project_name],
            label="Build 360 tour (Pannellum)")
    tour = extract_json(p.stdout, "TOUR_RESULT_JSON=")
    summary["stages"]["tour"] = tour or {"ok": bool(p.returncode == 0)}

    # ---- Stage 3 (optional): Pixel Streaming package -----------------------
    want_ps = cfg.get("pixel_streaming", {}).get("enabled") and args.flagship \
        and not args.no_pixelstream
    if want_ps:
        p = run(ue_cmd(cfg, "package_pixelstream.py", ["--project-name", args.project_name]),
                label="Package Pixel Streaming (flagship)")
        ps = extract_json(p.stdout, "PIXELSTREAM_RESULT_JSON=")
        summary["stages"]["pixelstream"] = ps or {"ok": bool(p.returncode == 0)}
    else:
        summary["stages"]["pixelstream"] = {"skipped": True}

    # ---- Stage 4: Publish ---------------------------------------------------
    pub_cmd = ["python", os.path.join(ROOT, "pipeline", "publish.py"), "--slug", slug]
    if args.method:
        pub_cmd += ["--method", args.method]
    p = run(pub_cmd, label="Publish to website")
    pub = extract_json(p.stdout, "PUBLISH_RESULT_JSON=")
    summary["stages"]["publish"] = pub or {"ok": bool(p.returncode == 0)}

    summary["ok"] = bool(summary["stages"]["publish"].get("ok"))
    _finish(summary, t0)


def _finish(summary, t0):
    summary["elapsed_sec"] = round(time.time() - t0, 1)
    # Human line OpenClaw relays to the messenger.
    if summary["ok"]:
        n_scn = summary["stages"].get("tour", {}).get("scenes", "?")
        method = summary["stages"].get("publish", {}).get("method", "?")
        summary["message"] = (
            "Done: '{}' rendered, {}-scene 360 tour built, published via {} "
            "({}s).".format(summary["project"], n_scn, method, summary["elapsed_sec"]))
    else:
        summary["message"] = "Pipeline FAILED at '{}' for '{}'.".format(
            summary.get("failed_stage", "publish"), summary["project"])
    # Persist + emit.
    logs = os.path.join(ROOT, "pipeline", "logs")
    os.makedirs(logs, exist_ok=True)
    with open(os.path.join(logs, "pipeline_{}.json".format(summary["slug"])), "w",
              encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print("\nPIPELINE_SUMMARY_JSON=" + json.dumps(summary))
    print(summary["message"])
    sys.exit(0 if summary["ok"] else 1)


if __name__ == "__main__":
    main()
