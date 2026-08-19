#!/usr/bin/env python3
"""
watch_folder.py  -  Watch pipeline/hot_folder and auto-run the pipeline.

When a new 3D asset finishes copying into the hot folder, this fires
run_pipeline.py for it. Category is guessed from the filename using the
keyword map in config.json (override by naming files like
"automotive__Lamborghini.fbx" or "architecture__Modern Villa.fbx").

Run it as a background process (or let OpenClaw manage it):
    python pipeline/watch_folder.py

Stop with Ctrl+C.
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("ERROR: watchdog not installed. Run: pip install -r pipeline/requirements.txt",
          file=sys.stderr)
    sys.exit(2)


def load_config():
    p = os.path.join(ROOT, "pipeline", "config.json")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "pipeline", "config.example.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


CFG = load_config()
ACCEPTED = tuple(CFG["intake"]["accepted_formats"])
CAT_MAP = CFG["intake"]["category_by_keyword"]


def guess_category(filename):
    low = filename.lower()
    if "__" in filename:                       # explicit prefix wins
        prefix = filename.split("__", 1)[0].lower()
        if prefix in ("architecture", "automotive"):
            return prefix
    for cat, keywords in CAT_MAP.items():
        if any(k in low for k in keywords):
            return cat
    return "architecture"


def project_name(filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    if "__" in base:
        base = base.split("__", 1)[1]
    return base.replace("_", " ").strip()


def wait_until_stable(path, checks=3, interval=2.0):
    """Avoid firing while a big file is still copying: size must hold steady."""
    last = -1
    stable = 0
    while stable < checks:
        try:
            size = os.path.getsize(path)
        except OSError:
            return False
        stable = stable + 1 if size == last else 0
        last = size
        time.sleep(interval)
    return True


def process(path):
    fn = os.path.basename(path)
    if not fn.lower().endswith(ACCEPTED):
        return
    print("[watch] detected {}".format(fn))
    if not wait_until_stable(path):
        print("[watch] {} vanished before it stabilised; skipping".format(fn))
        return
    cat, name = guess_category(fn), project_name(fn)
    print("[watch] launching pipeline: '{}' ({})".format(name, cat))
    subprocess.Popen([sys.executable, os.path.join(ROOT, "pipeline", "run_pipeline.py"),
                      "--asset", path, "--project-name", name, "--category", cat])


class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            process(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            process(event.dest_path)


def main():
    hot = os.path.join(ROOT, CFG["paths"]["hot_folder"])
    os.makedirs(hot, exist_ok=True)
    obs = Observer()
    obs.schedule(Handler(), hot, recursive=False)
    obs.start()
    print("[watch] watching {}  (accepted: {})".format(hot, ", ".join(ACCEPTED)))
    print("[watch] drop an asset in to trigger. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        obs.stop()
    obs.join()


if __name__ == "__main__":
    main()
