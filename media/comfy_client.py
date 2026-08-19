"""
comfy_client.py  -  minimal HTTP client for a local ComfyUI server.

ComfyUI is the local backend for BOTH tiers:
  Tier 1 images  -> Flux / SDXL workflow
  Tier 2 video   -> Wan (image-to-video / text-to-video) workflow

It runs on your GPU and exposes an HTTP API (default http://127.0.0.1:8188).
This client queues an API-format workflow, waits for it, and returns the output
file paths so gen_image.py / gen_video.py can move them into the website.

Why workflows are external JSON: ComfyUI's API takes the full node graph. You
export it once from the ComfyUI UI (Settings -> "Enable dev mode options" ->
"Save (API Format)") into pipeline/media/workflows/, and these scripts inject
your prompt/params into known node ids. See media/README.md.
"""
import json
import os
import time
import urllib.request
import urllib.parse
import uuid

DEFAULT_HOST = os.environ.get("COMFYUI_HOST", "http://127.0.0.1:8188")


class ComfyClient:
    def __init__(self, host=DEFAULT_HOST):
        self.host = host.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def _post(self, path, payload):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.host + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def _get(self, path):
        with urllib.request.urlopen(self.host + path, timeout=30) as r:
            return json.loads(r.read())

    def queue(self, workflow):
        """Queue an API-format workflow dict. Returns prompt_id."""
        return self._post("/prompt", {"prompt": workflow, "client_id": self.client_id})["prompt_id"]

    def wait(self, prompt_id, timeout_sec=1800, poll=2.0):
        """Block until the prompt finishes; return its history entry."""
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            hist = self._get("/history/{}".format(prompt_id))
            if prompt_id in hist:
                return hist[prompt_id]
            time.sleep(poll)
        raise TimeoutError("ComfyUI job {} did not finish in {}s".format(prompt_id, timeout_sec))

    def download_outputs(self, history, dest_dir, exts=(".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm")):
        """Save all output files referenced in a history entry into dest_dir."""
        os.makedirs(dest_dir, exist_ok=True)
        saved = []
        for node_out in history.get("outputs", {}).values():
            for key in ("images", "gifs", "videos"):
                for item in node_out.get(key, []):
                    fn = item["filename"]
                    if not fn.lower().endswith(exts):
                        continue
                    params = urllib.parse.urlencode({
                        "filename": fn,
                        "subfolder": item.get("subfolder", ""),
                        "type": item.get("type", "output"),
                    })
                    url = "{}/view?{}".format(self.host, params)
                    out_path = os.path.join(dest_dir, fn)
                    with urllib.request.urlopen(url, timeout=120) as r, open(out_path, "wb") as f:
                        f.write(r.read())
                    saved.append(out_path)
        return saved


def load_workflow(name):
    """Load an API-format workflow JSON from pipeline/media/workflows/."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "workflows", name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def set_node_input(workflow, node_id, field, value):
    """Safely set workflow[node_id]['inputs'][field] = value."""
    node = workflow.get(str(node_id))
    if not node:
        raise KeyError("workflow has no node id {}".format(node_id))
    node.setdefault("inputs", {})[field] = value
