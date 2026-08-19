#!/usr/bin/env python3
"""
build_tour.py  -  Turn rendered 360 panoramas into a Pannellum virtual tour.

Reads:  pipeline/output/panoramas/<slug>/  (equirectangular images + scenes.json)
Writes: tours/<slug>/  (index.html + tour.json + copied panoramas)

The generated tour is a fully static, self-contained folder you can open
directly or serve from the same static host as the rest of blkklegacy.
Pannellum is loaded from CDN; pass --vendor to copy it locally instead.

Usage:
    python pipeline/build_tour.py --slug modern-villa --title "Modern Villa"
    python pipeline/build_tour.py --slug modern-villa --vendor   # offline-safe
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root


def load_config():
    cfg_path = os.path.join(ROOT, "pipeline", "config.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(ROOT, "pipeline", "config.example.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_panoramas(pano_dir):
    """Return list of (scene_id, label, image_filename) preserving scenes.json order."""
    exts = (".png", ".jpg", ".jpeg")
    images = sorted(f for f in os.listdir(pano_dir) if f.lower().endswith(exts))
    scenes_json = os.path.join(pano_dir, "scenes.json")
    ordered = []
    if os.path.exists(scenes_json):
        with open(scenes_json, "r", encoding="utf-8") as f:
            meta = json.load(f)
        for scene in meta.get("scenes", []):
            match = next((im for im in images if scene in im), None)
            if match:
                ordered.append((scene, scene.replace("-", " ").title(), match))
        # Append any leftover images not referenced in scenes.json
        used = {m[2] for m in ordered}
        for im in images:
            if im not in used:
                sid = os.path.splitext(im)[0]
                ordered.append((sid, sid.replace("-", " ").title(), im))
    else:
        for im in images:
            sid = os.path.splitext(im)[0]
            ordered.append((sid, sid.replace("-", " ").title(), im))
    return ordered


def build_pannellum_config(scenes, cfg, first_scene_id):
    tour = {
        "default": {
            "firstScene": first_scene_id,
            "author": "Black Star Legacy",
            "sceneFadeDuration": 1000,
            "autoLoad": True,
            "autoRotate": cfg["tour"].get("auto_rotate_speed", -2),
        },
        "scenes": {},
    }
    for idx, (sid, label, fname) in enumerate(scenes):
        # Link each scene to the next with a hotspot so visitors can walk through.
        hotspots = []
        if len(scenes) > 1:
            nxt = scenes[(idx + 1) % len(scenes)]
            hotspots.append({
                "pitch": -2,
                "yaw": 0,
                "type": "scene",
                "text": "Go to {}".format(nxt[1]),
                "sceneId": nxt[0],
            })
        tour["scenes"][sid] = {
            "title": label,
            "hfov": cfg["tour"].get("default_hfov", 110),
            "type": "equirectangular",
            "panorama": "panoramas/{}".format(fname),
            "autoLoad": True,
            "hotSpots": hotspots,
        }
    return tour


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>{title} — Virtual Tour | Black Star Legacy</title>
{pannellum_css}
<style>
  html,body{{margin:0;height:100%;background:#0b0b0b;color:#f5f5f5;font-family:system-ui,sans-serif}}
  #panorama{{width:100%;height:100%}}
  #tour-title{{position:fixed;top:16px;left:16px;z-index:5;font-size:14px;
    letter-spacing:.12em;text-transform:uppercase;opacity:.85;
    background:rgba(0,0,0,.35);padding:8px 14px;border-radius:999px;backdrop-filter:blur(6px)}}
</style>
</head>
<body>
<div id="tour-title">{title}</div>
<div id="panorama"></div>
{pannellum_js}
<script>
  fetch('tour.json')
    .then(r => r.json())
    .then(cfg => pannellum.viewer('panorama', cfg));
</script>
</body>
</html>
"""

CDN_CSS = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pannellum@{v}/build/pannellum.css">'
CDN_JS = '<script src="https://cdn.jsdelivr.net/npm/pannellum@{v}/build/pannellum.js"></script>'
LOCAL_CSS = '<link rel="stylesheet" href="vendor/pannellum.css">'
LOCAL_JS = '<script src="vendor/pannellum.js"></script>'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True, help="Project slug, e.g. modern-villa")
    ap.add_argument("--title", default=None, help="Display title (default: derived from slug)")
    ap.add_argument("--vendor", action="store_true",
                    help="Copy Pannellum locally into tours/<slug>/vendor (offline-safe)")
    args = ap.parse_args()
    cfg = load_config()
    title = args.title or args.slug.replace("-", " ").title()

    pano_dir = os.path.join(ROOT, cfg["paths"]["output_panoramas"], args.slug)
    if not os.path.isdir(pano_dir):
        print("ERROR: no panoramas at {}".format(pano_dir), file=sys.stderr)
        sys.exit(1)

    scenes = find_panoramas(pano_dir)
    if not scenes:
        print("ERROR: no panorama images found in {}".format(pano_dir), file=sys.stderr)
        sys.exit(1)

    tour_dir = os.path.join(ROOT, cfg["paths"]["site_tours"], args.slug)
    out_pano = os.path.join(tour_dir, "panoramas")
    os.makedirs(out_pano, exist_ok=True)
    for _, _, fname in scenes:
        shutil.copy2(os.path.join(pano_dir, fname), os.path.join(out_pano, fname))

    tour_cfg = build_pannellum_config(scenes, cfg, scenes[0][0])
    with open(os.path.join(tour_dir, "tour.json"), "w", encoding="utf-8") as f:
        json.dump(tour_cfg, f, indent=2)

    v = cfg["tour"].get("pannellum_version", "2.5.6")
    if args.vendor:
        css, js = LOCAL_CSS, LOCAL_JS
        os.makedirs(os.path.join(tour_dir, "vendor"), exist_ok=True)
        print("NOTE: --vendor set. Place pannellum.css/.js in {}/vendor/ "
              "(download from https://cdn.jsdelivr.net/npm/pannellum@{}/build/)"
              .format(tour_dir, v))
    else:
        css, js = CDN_CSS.format(v=v), CDN_JS.format(v=v)

    html = HTML_TEMPLATE.format(title=title, pannellum_css=css, pannellum_js=js)
    with open(os.path.join(tour_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print("Tour built: {}".format(tour_dir))
    print("  scenes : {}".format(len(scenes)))
    print("  open   : tours/{}/index.html".format(args.slug))
    # Machine-readable line for the orchestrator.
    print("TOUR_RESULT_JSON=" + json.dumps(
        {"slug": args.slug, "scenes": len(scenes), "dir": "tours/{}".format(args.slug)}))


if __name__ == "__main__":
    main()
