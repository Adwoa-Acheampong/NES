#!/usr/bin/env python3
"""
gen_image.py  -  Tier 1: generate a still image locally via ComfyUI, drop it into
the website, and (optionally) regenerate responsive variants.

No Unreal Engine. Use for hero shots, section backgrounds, thumbnails, concepts.

Usage:
    python pipeline/media/gen_image.py --name estate-hero \
        --prompt "warm modern Ghanaian estate at golden hour, editorial, photoreal" \
        --workflow flux_image.api.json
    # then it lands in assets/estate-hero.png and runs the optimizer

Config (pipeline/config.json -> "media") sets defaults: workflow file, node ids,
steps, size. The workflow JSON itself lives in pipeline/media/workflows/ (export
it once from ComfyUI in API format -- see media/README.md).
"""
import argparse
import json
import os
import shutil
import subprocess
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


def main():
    cfg = load_config().get("media", {}).get("image", {})
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="output base name, e.g. estate-hero")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--negative", default=cfg.get("negative", "lowres, text, watermark, deformed"))
    ap.add_argument("--workflow", default=cfg.get("workflow", "flux_image.api.json"))
    ap.add_argument("--width", type=int, default=cfg.get("width", 1600))
    ap.add_argument("--height", type=int, default=cfg.get("height", 900))
    ap.add_argument("--steps", type=int, default=cfg.get("steps", 28))
    ap.add_argument("--seed", type=int, default=cfg.get("seed", -1))
    ap.add_argument("--no-optimize", action="store_true", help="skip optimize-images.js")
    args = ap.parse_args()

    nodes = cfg.get("nodes", {})  # map of role -> {node, field}
    wf = load_workflow(args.workflow)

    # Inject our params into the workflow using the node-id map from config.
    def apply(role, value):
        m = nodes.get(role)
        if m:
            set_node_input(wf, m["node"], m["field"], value)
    apply("positive", args.prompt)
    apply("negative", args.negative)
    apply("width", args.width)
    apply("height", args.height)
    apply("steps", args.steps)
    if args.seed >= 0:
        apply("seed", args.seed)

    client = ComfyClient()
    print("[gen_image] queuing '{}' via {}".format(args.name, args.workflow))
    pid = client.queue(wf)
    hist = client.wait(pid, timeout_sec=cfg.get("timeout_sec", 600))

    tmp = os.path.join(ROOT, "pipeline", "output", "media_tmp")
    saved = client.download_outputs(hist, tmp)
    if not saved:
        print("ERROR: ComfyUI returned no image", file=sys.stderr)
        sys.exit(1)

    # Move the first image to assets/<name>.png (originals live in assets/).
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)
    dst = os.path.join(assets, "{}.png".format(args.name))
    shutil.copy2(saved[0], dst)
    print("[gen_image] -> {}".format(os.path.relpath(dst, ROOT)))

    if not args.no_optimize:
        tools = os.path.join(ROOT, "tools")
        if os.path.exists(os.path.join(tools, "optimize-images.js")):
            try:
                subprocess.run(["node", "optimize-images.js"], cwd=tools, check=False)
            except FileNotFoundError:
                print("WARN: node not found; skipped variant regen")

    print("IMAGE_RESULT_JSON=" + json.dumps(
        {"name": args.name, "path": os.path.relpath(dst, ROOT)}))


if __name__ == "__main__":
    main()
