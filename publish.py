#!/usr/bin/env python3
"""
publish.py  -  Stage rendered media into the website and deploy.

Steps:
    1. Copy cinematic MP4(s)  -> assets/video/<slug>.mp4
    2. Copy hero still(s)     -> assets/<slug>-hero.png  (if a still was rendered)
    3. Regenerate responsive variants + manifest by running the project's own
       tool:  node tools/optimize-images.js   (single source of truth)
    4. Tours are already in tours/<slug>/ (build_tour.py put them there).
    5. Deploy via config publish.method:  git | sftp | s3 | none

Usage:
    python pipeline/publish.py --slug modern-villa
    python pipeline/publish.py --slug modern-villa --method git
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config():
    p = os.path.join(ROOT, "pipeline", "config.json")
    if not os.path.exists(p):
        p = os.path.join(ROOT, "pipeline", "config.example.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def stage_media(cfg, slug):
    moved = {"video": [], "stills": []}
    cin_dir = os.path.join(ROOT, cfg["paths"]["output_cinematics"], slug)
    assets = os.path.join(ROOT, cfg["paths"]["site_assets"])
    video_dir = os.path.join(assets, "video")
    os.makedirs(video_dir, exist_ok=True)

    if os.path.isdir(cin_dir):
        for f in sorted(os.listdir(cin_dir)):
            low = f.lower()
            if low.endswith((".mp4", ".mov")):
                dst = os.path.join(video_dir, "{}.mp4".format(slug))
                shutil.copy2(os.path.join(cin_dir, f), dst)
                moved["video"].append(os.path.relpath(dst, ROOT))
            elif low.endswith(".png") and "hero" in low:
                dst = os.path.join(assets, "{}-hero.png".format(slug))
                shutil.copy2(os.path.join(cin_dir, f), dst)
                moved["stills"].append(os.path.relpath(dst, ROOT))
    return moved


def regenerate_variants():
    """Run the project's existing optimizer so manifest + AVIF/WebP stay consistent."""
    tools = os.path.join(ROOT, "tools")
    if not os.path.exists(os.path.join(tools, "optimize-images.js")):
        print("WARN: tools/optimize-images.js not found; skipping variant regen")
        return
    print("[publish] regenerating variants via node tools/optimize-images.js ...")
    try:
        subprocess.run(["node", "optimize-images.js"], cwd=tools, check=True)
    except FileNotFoundError:
        print("WARN: node not on PATH; install Node or run optimize-images.js manually")
    except subprocess.CalledProcessError as e:
        print("WARN: optimizer exited {} (continuing)".format(e.returncode))


# --------------------------------------------------------------------------- #
# Deploy backends
# --------------------------------------------------------------------------- #
def deploy_git(cfg, slug):
    g = cfg["publish"]["git"]
    msg = "{}{}".format(g.get("commit_prefix", "media: "), "add tour + media for {}".format(slug))
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    # Don't fail the whole run if there's nothing to commit.
    r = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT)
    if r.returncode == 0:
        subprocess.run(["git", "push", g.get("remote", "origin"), g.get("branch", "main")],
                       cwd=ROOT, check=True)
    return "git push to {}/{}".format(g.get("remote", "origin"), g.get("branch", "main"))


def deploy_sftp(cfg, slug):
    try:
        import paramiko
    except ImportError:
        print("ERROR: paramiko not installed (pip install paramiko)", file=sys.stderr)
        raise
    s = cfg["publish"]["sftp"]
    host, port = s["host"], int(s.get("port", 22))
    user, remote_root = s["username"], s["remote_root"]
    if not host or not user:
        raise RuntimeError("SFTP host/username missing in config.json")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = s.get("key_path") or None
    password = os.environ.get("BLKK_SFTP_PASSWORD") or None
    ssh.connect(host, port=port, username=user,
                key_filename=key_path if key_path else None, password=password)
    sftp = ssh.open_sftp()

    def _mkdirs(remote):
        parts, cur = remote.strip("/").split("/"), ""
        for p in parts:
            cur += "/" + p
            try:
                sftp.stat(cur)
            except IOError:
                sftp.mkdir(cur)

    # Sync just the folders we touched: assets/ and tours/<slug>/
    for rel in ["assets", os.path.join("tours", slug)]:
        local = os.path.join(ROOT, rel)
        for dirpath, _, files in os.walk(local):
            rrel = os.path.relpath(dirpath, ROOT).replace("\\", "/")
            _mkdirs("{}/{}".format(remote_root.rstrip('/'), rrel))
            for fn in files:
                lp = os.path.join(dirpath, fn)
                rp = "{}/{}/{}".format(remote_root.rstrip('/'), rrel, fn)
                sftp.put(lp, rp)
    sftp.close()
    ssh.close()
    return "sftp upload to {}@{}:{}".format(user, host, remote_root)


def deploy_s3(cfg, slug):
    s = cfg["publish"]["s3"]
    bucket, prefix = s["bucket"], s.get("prefix", "")
    if not bucket:
        raise RuntimeError("S3 bucket missing in config.json")
    base = "s3://{}/{}".format(bucket, prefix).rstrip("/")
    subprocess.run(["aws", "s3", "sync", os.path.join(ROOT, "assets"),
                    base + "/assets"], check=True)
    subprocess.run(["aws", "s3", "sync", os.path.join(ROOT, "tours", slug),
                    base + "/tours/" + slug], check=True)
    dist = s.get("cloudfront_distribution_id")
    if dist:
        subprocess.run(["aws", "cloudfront", "create-invalidation",
                        "--distribution-id", dist, "--paths", "/*"], check=True)
    return "s3 sync to {}".format(base)


DEPLOYERS = {"git": deploy_git, "sftp": deploy_sftp, "s3": deploy_s3}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--method", default=None, choices=["git", "sftp", "s3", "none"])
    args = ap.parse_args()
    cfg = load_config()
    method = args.method or cfg["publish"].get("method", "none")

    result = {"slug": args.slug, "method": method, "ok": False, "stage": "stage_media"}
    try:
        result["moved"] = stage_media(cfg, args.slug)
        result["stage"] = "variants"
        regenerate_variants()
        result["stage"] = "deploy"
        if method == "none":
            result["deploy"] = "skipped (method=none)"
        else:
            result["deploy"] = DEPLOYERS[method](cfg, args.slug)
        result["ok"] = True
        result["stage"] = "done"
    except Exception as e:  # noqa
        result["error"] = str(e)
        print("PUBLISH FAILED at {}: {}".format(result["stage"], e), file=sys.stderr)

    print("PUBLISH_RESULT_JSON=" + json.dumps(result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
