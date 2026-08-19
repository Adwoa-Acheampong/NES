#!/usr/bin/env python3
"""
SupaAgent service launcher.

Starts/checks the local services that make the personal agent useful:
ComfyUI, project dev servers, OpenClaw, and optional UE MCP.

This script only manages local service processes. It does not publish, post,
message, spend money, delete files, or touch credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PIPELINE = HERE.parent
ROOT = PIPELINE.parent
MONOREPO = ROOT.parent
DEFAULT_CONFIG = HERE / "config.json"
EXAMPLE_CONFIG = HERE / "config.example.json"
LOG_DIR = PIPELINE / "logs" / "supaagent"


def load_config(path: Path) -> dict[str, Any]:
    chosen = path if path.exists() else EXAMPLE_CONFIG
    with chosen.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_config_path"] = str(chosen)
    cfg["_using_example"] = chosen == EXAMPLE_CONFIG
    return cfg


def expand(value: str) -> str:
    value = (
        value
        .replace("{ROOT}", str(ROOT))
        .replace("{PIPELINE}", str(PIPELINE))
        .replace("{MONOREPO}", str(MONOREPO))
    )
    return os.path.expandvars(value)


def service_order(cfg: dict[str, Any]) -> list[str]:
    services = cfg.get("services", {})
    configured = list(services.keys())
    order = [name for name in cfg.get("startup_order", []) if name in services]
    order.extend(name for name in configured if name not in order)
    return order


def check_url(url: str, timeout: float) -> dict[str, Any]:
    if not url:
        return {"status": "unknown", "reason": "no health_url"}
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return {"status": "ready", "http_status": response.status}
    except urllib.error.HTTPError as exc:
        # A local HTTP response still proves the service is alive.
        return {"status": "ready", "http_status": exc.code}
    except Exception as exc:  # noqa: BLE001
        return {"status": "down", "reason": str(exc)}


def start_process(name: str, svc: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    command = expand(str(svc.get("command", "")).strip())
    if not command:
        return {"started": False, "reason": "no command configured"}

    workdir_raw = str(svc.get("working_dir", "")).strip()
    workdir = Path(expand(workdir_raw)) if workdir_raw else ROOT
    if not workdir.exists():
        return {
            "started": False,
            "reason": "working_dir not found: {}".format(workdir),
        }

    log_path = LOG_DIR / "{}.log".format(name)
    if dry_run:
        return {
            "started": False,
            "dry_run": True,
            "command": command,
            "working_dir": str(workdir),
            "log": str(log_path),
        }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = log_path.open("a", encoding="utf-8")
    log.write("\n\n=== {} | {} ===\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), command))
    log.flush()

    flags = 0
    startupinfo = None
    if os.name == "nt":
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if not bool(svc.get("visible", False)):
            flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.Popen(
        command,
        cwd=str(workdir),
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        shell=True,
        creationflags=flags,
        startupinfo=startupinfo,
    )
    return {
        "started": True,
        "pid": proc.pid,
        "command": command,
        "working_dir": str(workdir),
        "log": str(log_path),
    }


def wait_until_ready(url: str, timeout_sec: float, request_timeout: float) -> dict[str, Any]:
    if not url:
        return {"status": "unknown", "reason": "no health_url"}
    deadline = time.time() + max(0, timeout_sec)
    last = {"status": "down", "reason": "not checked"}
    while time.time() <= deadline:
        last = check_url(url, request_timeout)
        if last.get("status") == "ready":
            return last
        time.sleep(1)
    return last


def evaluate_service(
    name: str,
    svc: dict[str, Any],
    defaults: dict[str, Any],
    *,
    dry_run: bool,
    no_start: bool,
) -> dict[str, Any]:
    request_timeout = float(svc.get("request_timeout_sec", defaults.get("request_timeout_sec", 3)))
    startup_timeout = float(svc.get("startup_timeout_sec", defaults.get("startup_timeout_sec", 30)))
    health_url = expand(str(svc.get("health_url", "")).strip())

    result: dict[str, Any] = {
        "name": name,
        "enabled": bool(svc.get("enabled", True)),
        "required": bool(svc.get("required", False)),
        "description": svc.get("description", ""),
        "health_url": health_url,
    }
    if not result["enabled"]:
        result["status"] = "disabled"
        return result

    health = check_url(health_url, request_timeout)
    result["health"] = health
    if health.get("status") == "ready":
        result["status"] = "ready"
        return result

    if no_start:
        result["status"] = "down" if health_url else "unknown"
        return result

    start = start_process(name, svc, dry_run)
    result["start"] = start
    if dry_run:
        result["status"] = "dry_run"
        return result

    if not start.get("started"):
        result["status"] = "down" if health_url else "unknown"
        return result

    ready = wait_until_ready(health_url, startup_timeout, request_timeout)
    result["health_after_start"] = ready
    result["status"] = "ready" if ready.get("status") == "ready" else "started"
    return result


def print_summary(results: list[dict[str, Any]], cfg: dict[str, Any]) -> None:
    print("SupaAgent service check")
    print("Config: {}".format(cfg["_config_path"]))
    if cfg.get("_using_example"):
        print("NOTE: using config.example.json. Copy it to pipeline/supaagent/config.json for real local paths.")
    print("")
    for item in results:
        name = item["name"]
        status = item.get("status", "unknown")
        extra = ""
        if item.get("start", {}).get("pid"):
            extra = " pid={}".format(item["start"]["pid"])
        elif item.get("health", {}).get("reason"):
            extra = " ({})".format(item["health"]["reason"])
        print("- {:14} {:10}{}".format(name, status, extra))
    print("")
    print("SUPAAGENT_STATUS_JSON=" + json.dumps({"services": results}, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="path to SupaAgent config.json")
    parser.add_argument("--only", action="append", default=[], help="service name to check/start; repeatable")
    parser.add_argument("--status-only", action="store_true", help="check health only; do not start anything")
    parser.add_argument("--dry-run", action="store_true", help="show what would start without launching processes")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    defaults = cfg.get("defaults", {})
    services = cfg.get("services", {})
    only = set(args.only)
    names = [name for name in service_order(cfg) if not only or name in only]
    results = [
        evaluate_service(name, services[name], defaults, dry_run=args.dry_run, no_start=args.status_only)
        for name in names
    ]
    print_summary(results, cfg)

    failed_required = [
        item["name"]
        for item in results
        if item.get("required") and item.get("status") not in {"ready", "started", "dry_run"}
    ]
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
