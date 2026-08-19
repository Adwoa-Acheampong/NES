#!/usr/bin/env python3
"""
gen_video.py  -  Tier 2: generate a short animated clip locally with Wan (via
ComfyUI), drop it into the website as an MP4.

No Unreal Engine. Use for ambient hero loops, simple portrait/product motion,
short story beats. Two modes:
  - text-to-video  (--prompt only)
  - image-to-video (--image assets/estate-hero.png  -> animates an existing still)

Usage:
    python pipeline/media/gen_video.py --name estate-loop \
        --prompt "slow cinematic push-in, warm light, gentle dust motes" \
        --image assets/estate-hero.png --workflow wan_i2v.api.json

Wan model variant (1.3B vs 14B) and frame count depend on your VRAM -- set them
in pipeline/config.json -> media.video and in the exported workflow. See README.
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from comfy_client import ComfyClient, load_workflow, set_node_input  # noqa: E402


def load_config():
    p = os.path.join(ROOT, "pipeline", "config.json")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "pipeline", "config.example.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_image(client, image_path):
    """Upload a still to ComfyUI's input dir so an image-to-video workflow can load it."""
    import urllib.request
    import mimetypes
    boundary = "----blkkboundary"
    fn = os.path.basename(image_path)
    with open(image_path, "rb") as f:
        content = f.read()
    ctype = mimetypes.guess_type(fn)[0] or "image/png"
    body = (
        ("--%s\r\n" % boundary).encode()
        + ('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % fn).encode()
        + ("Content-Type: %s\r\n\r\n" % ctype).encode()
        + content + ("\r\n--%s--\r\n" % boundary).encode()
    )
    req = urllib.request.Request(
        client.host + "/upload/image", data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary})
    with urllib.request.urlopen(req, timeout=60) as r:
        json.loads(r.read())
    return fn


def main():
    cfg = load_config().get("media", {}).get("video", {})
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="output base name, e.g. estate-loop")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--image", default=None, help="still to animate (image-to-video)")
    ap.add_argument("--workflow", default=cfg.get("workflow", "wan_t2v.api.json"))
    ap.add_argument("--frames", type=int, default=cfg.get("frames", 49))
    ap.add_argument("--fps", type=int, default=cfg.get("fps", 16))
    ap.add_argument("--seed", type=int, default=cfg.get("seed", -1))
    args = ap.parse_args()

    nodes = cfg.get("nodes", {})
    wf = load_workflow(args.workflow)
    client = ComfyClient()

    def apply(role, value):
        m = nodes.get(role)
        if m:
            set_node_input(wf, m["node"], m["field"], value)

    apply("positive", args.prompt)
    apply("frames", args.frames)
    apply("fps", args.fps)
    if args.seed >= 0:
        apply("seed", args.seed)
    if args.image:
        img_abs = args.image if os.path.isabs(args.image) else os.path.join(ROOT, args.image)
        if not os.path.exists(img_abs):
            print("ERROR: image not found: {}".format(img_abs), file=sys.stderr)
            sys.exit(1)
        uploaded = upload_image(client, img_abs)
        apply("image", uploaded)

    print("[gen_video] queuing '{}' via {} ({} frames @ {}fps)".format(
        args.name, args.workflow, args.frames, args.fps))
    pid = client.queue(wf)
    hist = client.wait(pid, timeout_sec=cfg.get("timeout_sec", 1800))

    tmp = os.path.join(ROOT, "pipeline", "output", "media_tmp")
    saved = client.download_outputs(hist, tmp, exts=(".mp4", ".webm"))
    if not saved:
        print("ERROR: ComfyUI returned no video", file=sys.stderr)
        sys.exit(1)

    video_dir = os.path.join(ROOT, "assets", "video")
    os.makedirs(video_dir, exist_ok=True)
    dst = os.path.join(video_dir, "{}.mp4".format(args.name))
    shutil.copy2(saved[0], dst)
    print("[gen_video] -> {}".format(os.path.relpath(dst, ROOT)))
    print("VIDEO_RESULT_JSON=" + json.dumps(
        {"name": args.name, "path": os.path.relpath(dst, ROOT)}))


if __name__ == "__main__":
    main()
