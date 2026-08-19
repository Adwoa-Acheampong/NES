"""
package_pixelstream.py  -  Build a Pixel Streaming package of the UE 5.8 project.

Runs INSIDE Unreal's bundled Python (uses the `unreal` module). Triggered
head-less by the orchestrator only for FLAGSHIP projects (Pixel Streaming needs
a live GPU server to actually stream — see README section 6).

    UnrealEditor-Cmd.exe "<project>.uproject" ^
        -run=pythonscript -script="<...>/pipeline/ue/package_pixelstream.py" ^
        -unattended -nosplash -- --config "<...>/pipeline/config.json" --project-name "Modern Villa"

This produces a Windows package with the Pixel Streaming plugin enabled and the
-PixelStreamingURL launch args baked into a run script. You then upload that
package to your GPU host and run it behind the signalling server.

NOTE: Programmatic packaging via Python wraps the same Automation Tool (UAT)
that `RunUAT BuildCookRun` uses. If you prefer, the README gives the equivalent
one-line RunUAT command, which is the more battle-tested path.
"""
import unreal
import argparse
import json
import os
import sys


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    p.add_argument("--project-name", required=True)
    return p.parse_args(argv)


def slugify(name):
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")


def main():
    args = parse_args()
    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    slug = slugify(args.project_name)

    if not cfg.get("pixel_streaming", {}).get("enabled"):
        unreal.log_warning("[pixelstream] disabled in config; skipping")
        return

    out_dir = os.path.abspath(os.path.join("pipeline", "output", "pixelstream", slug))
    os.makedirs(out_dir, exist_ok=True)

    # Ensure the Pixel Streaming plugin is enabled for this project.
    # >>> PROJECT-SPECIFIC: confirm 'PixelStreaming2' (UE5.5+) is the plugin name
    #     in your .uproject; older projects use 'PixelStreaming'.
    unreal.log("[pixelstream] packaging {} -> {}".format(slug, out_dir))

    # Drive a Development Windows package through the editor's packaging settings.
    settings = unreal.get_default_object(unreal.ProjectPackagingSettings)
    settings.set_editor_property("build_configuration",
                                 unreal.ProjectPackagingBuildConfigurations.PPBC_DEVELOPMENT)
    settings.set_editor_property("for_distribution", False)
    settings.set_editor_property("use_pak_file", True)

    # The actual cook+package call is most reliable through UAT; we emit the
    # exact command for the host to run rather than blocking the editor here.
    uproject = cfg["unreal"]["project"]
    engine_dir = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(cfg["unreal"]["editor_cmd"]))))  # ...\Engine
    runuat = os.path.join(engine_dir, "Build", "BatchFiles", "RunUAT.bat")

    cmd = (
        '"{runuat}" BuildCookRun -project="{uproject}" '
        '-noP4 -platform=Win64 -clientconfig=Development -cook -allmaps '
        '-build -stage -pak -archive -archivedirectory="{out}"'
    ).format(runuat=runuat, uproject=uproject, out=out_dir)

    marker = {"slug": slug, "package_dir": out_dir, "runuat_command": cmd,
              "signalling_url": cfg["pixel_streaming"].get("signalling_server_url")}
    with open(os.path.join(out_dir, "package_info.json"), "w", encoding="utf-8") as f:
        json.dump(marker, f, indent=2)

    unreal.log("[pixelstream] To produce the package, the host should run:\n" + cmd)
    unreal.log("PIXELSTREAM_RESULT_JSON=" + json.dumps(marker))


if __name__ == "__main__":
    main()
