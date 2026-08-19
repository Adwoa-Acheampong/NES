"""``nes gateway start|stop|status|logs`` — multi-channel gateway management."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import click

from nes.core.config import DEFAULT_CONFIG_DIR

_PID_FILE = DEFAULT_CONFIG_DIR / "gateway.pid"
_LOG_FILE = DEFAULT_CONFIG_DIR / "gateway.log"


def _pid_alive(pid: int) -> bool:
    """Return whether *pid* identifies a running process."""
    if pid <= 0:
        return False

    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        error_invalid_parameter = 87
        synchronize = 0x00100000
        wait_object_0 = 0x00000000

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return ctypes.get_last_error() != error_invalid_parameter

        try:
            wait_result = kernel32.WaitForSingleObject(handle, 0)
            return wait_result != wait_object_0
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pid() -> int | None:
    """Read PID from pid file, return None if not found or stale."""
    if not _PID_FILE.exists():
        return None
    try:
        pid = int(_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        _PID_FILE.unlink(missing_ok=True)
        return None
    if not _pid_alive(pid):
        _PID_FILE.unlink(missing_ok=True)
        return None
    return pid


def _write_pid(pid: int) -> None:
    """Write PID to pid file."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _PID_FILE.write_text(str(pid))


@click.group()
def gateway() -> None:
    """Manage the NES multi-channel gateway."""


@gateway.command()
@click.option(
    "--install",
    is_flag=True,
    help="Generate and enable systemd/launchd service",
)
@click.option("--background", "-b", is_flag=True, help="Run as background daemon")
def start(install: bool, background: bool) -> None:
    """Start the gateway daemon."""
    if install:
        import platform as plat

        from nes.daemon.service import (
            generate_launchd_plist,
            generate_systemd_service,
        )

        if plat.system() == "Darwin":
            plist_path = (
                Path.home() / "Library/LaunchAgents/com.nes.gateway.plist"
            )
            generate_launchd_plist(plist_path)
            click.echo(f"Wrote {plist_path}")
            subprocess.run(
                ["launchctl", "load", str(plist_path)],
                check=False,
            )
        elif plat.system() == "Windows":
            click.echo(
                "Windows service install is not yet supported.\n"
                "Use 'nes gateway start --background' or run 'nes serve' directly."
            )
        else:
            service_path = (
                Path.home() / ".config/systemd/user/nes-gateway.service"
            )
            generate_systemd_service(service_path)
            click.echo(f"Wrote {service_path}")
            subprocess.run(
                ["systemctl", "--user", "daemon-reload"],
                check=False,
            )
            subprocess.run(
                ["systemctl", "--user", "enable", "--now", "nes-gateway"],
                check=False,
            )
    elif background:
        # Launch `nes serve` as a detached background process.
        existing = _read_pid()
        if existing is not None:
            click.echo(f"Gateway already running (PID {existing}).")
            click.echo("Use 'nes gateway stop' first, or 'nes gateway start' for foreground.")
            sys.exit(1)

        cmd = [sys.executable, "-m", "nes.cli", "serve"]
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        log_fh = open(_LOG_FILE, "a")  # noqa: SIM115
        spawn_kwargs: dict = {}
        if sys.platform == "win32":
            spawn_kwargs["creationflags"] = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            spawn_kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=log_fh,
            **spawn_kwargs,
        )
        _write_pid(proc.pid)
        click.echo(
            f"NES gateway started in background (PID {proc.pid})\n"
            f"  Log: {_LOG_FILE}\n"
            f"  Stop: nes gateway stop"
        )
    else:
        # Foreground mode: run `nes serve` directly so the user sees all output,
        # including the WhatsApp QR code, channel status, etc.
        click.echo("Starting NES gateway (foreground)...")
        click.echo("This will start the NES server with all configured channels.")
        click.echo("Press Ctrl+C to stop.\n")
        try:
            subprocess.run(
                [sys.executable, "-m", "nes.cli", "serve"],
                check=False,
            )
        except KeyboardInterrupt:
            click.echo("\nGateway stopped.")


@gateway.command()
def stop() -> None:
    """Stop the gateway daemon."""
    import platform as plat

    pid = _read_pid()

    if plat.system() == "Darwin":
        subprocess.run(
            ["launchctl", "remove", "com.nes.gateway"],
            check=False,
        )
    elif plat.system() == "Windows":
        if pid is None:
            click.echo("No running gateway found.")
            sys.exit(1)
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.5)
                if not _pid_alive(pid):
                    break
            else:
                try:
                    os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
                except OSError:
                    pass
        except OSError:
            pass
        _PID_FILE.unlink(missing_ok=True)
    else:
        subprocess.run(
            ["systemctl", "--user", "stop", "nes-gateway"],
            check=False,
        )
    click.echo(f"Gateway stopped{f' (PID {pid})' if pid else ''}.")


@gateway.command()
def status() -> None:
    """Check gateway status."""
    import platform as plat

    if plat.system() == "Darwin":
        subprocess.run(
            ["launchctl", "list", "com.nes.gateway"],
            check=False,
        )
    elif plat.system() == "Windows":
        pid = _read_pid()
        if pid is None:
            click.echo("Gateway is not running.")
            click.echo("Start with: nes gateway start")
        else:
            uptime_info = ""
            try:
                import psutil

                proc = psutil.Process(pid)
                uptime = time.time() - proc.create_time()
                hours, remainder = divmod(int(uptime), 3600)
                minutes, seconds = divmod(remainder, 60)
                uptime_info = f"\n  Uptime: {hours}h {minutes}m {seconds}s"
            except (ImportError, Exception):
                pass
            click.echo(
                f"Gateway is running (PID {pid}){uptime_info}\n"
                f"  Log: {_LOG_FILE}"
            )
    else:
        subprocess.run(
            ["systemctl", "--user", "status", "nes-gateway"],
            check=False,
        )


@gateway.command()
def logs() -> None:
    """View gateway logs."""
    import platform as plat

    if plat.system() == "Darwin":
        click.echo("Check ~/Library/Logs/com.nes.gateway.log")
    elif plat.system() == "Windows":
        if _LOG_FILE.exists():
            click.echo(f"Log file: {_LOG_FILE}\n")
            # Show last 50 lines
            try:
                lines = _LOG_FILE.read_text(errors="replace").splitlines()
                for line in lines[-50:]:
                    click.echo(line)
            except OSError as exc:
                click.echo(f"Could not read log: {exc}")
        else:
            click.echo("No gateway log found. Start the gateway first.")
    else:
        subprocess.run(
            ["journalctl", "--user", "-u", "nes-gateway", "-f"],
            check=False,
        )
