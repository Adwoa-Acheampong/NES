"""
render_pipeline.py  -  UE 5.8 headless render stage for Black Star Legacy.

Runs INSIDE Unreal's bundled Python (the `unreal` module is only available there).
It is launched head-less by the host orchestrator like this:

    UnrealEditor-Cmd.exe "<project>.uproject" ^
        -run=pythonscript ^
        -script="<...>/pipeline/ue/render_pipeline.py" ^
        -unattended -nullrhi=0 -nosplash ^
        -- --asset "<hot_folder>/Modern Villa.fbx" --project-name "Modern Villa" --category architecture

What it does, in order:
    1. Import the asset (FBX / OBJ / GLB / Datasmith) into /Game/_Inbound/<project>.
    2. Spawn it into the configured master level for its category.
    3. Render a 4K cinematic via Movie Render Queue (uses an existing MRQ preset).
    4. Capture 360 stereo panoramas via the Panoramic Capture plugin at each
       camera marker tagged "TourPoint".
    5. Write everything to the output folders the host reads in the next stage.

IMPORTANT - this script targets the documented UE Python API but MUST be
validated against your actual project: master level paths, the MRQ preset, and
the camera/TourPoint actors are things only your project knows. Search markers
like  # >>> PROJECT-SPECIFIC  show every spot you may need to adjust.
"""

import unreal
import argparse
import json
import os
import sys
import time

LOG = unreal.log
LOG_WARN = unreal.log_warning
LOG_ERR = unreal.log_error


# --------------------------------------------------------------------------- #
# Args + config
# --------------------------------------------------------------------------- #
def parse_args():
    # Everything after the lone "--" on the UE command line is ours.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser(description="UE5.8 headless render stage")
    p.add_argument("--asset", required=True, help="Absolute path to the source 3D asset")
    p.add_argument("--project-name", required=True, help="Human name, e.g. 'Modern Villa'")
    p.add_argument("--category", default="architecture", choices=["architecture", "automotive"])
    p.add_argument("--config", required=True, help="Absolute path to pipeline/config.json")
    return p.parse_args(argv)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def slugify(name):
    return "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-").replace("--", "-")


# --------------------------------------------------------------------------- #
# 1. Import asset
# --------------------------------------------------------------------------- #
def import_asset(asset_path, project_slug):
    """Import FBX/OBJ/GLB/Datasmith into /Game/_Inbound/<slug>. Returns imported objects."""
    dest = "/Game/_Inbound/{}".format(project_slug)
    ext = os.path.splitext(asset_path)[1].lower()
    LOG("[import] {} -> {}".format(asset_path, dest))

    if ext == ".udatasmith":
        # >>> PROJECT-SPECIFIC: Datasmith import needs the Datasmith plugins enabled.
        ds = unreal.DatasmithSceneImportOptions()
        task = unreal.AssetImportTask()
        task.filename = asset_path
        task.destination_path = dest
        task.automated = True
        task.replace_existing = True
        task.save = True
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        return task.imported_object_paths

    # FBX / OBJ / GLB / GLTF via the interchange / legacy FBX pipeline.
    task = unreal.AssetImportTask()
    task.filename = asset_path
    task.destination_path = dest
    task.automated = True
    task.replace_existing = True
    task.save = True

    if ext in (".fbx", ".obj"):
        opts = unreal.FbxImportUI()
        opts.import_mesh = True
        opts.import_as_skeletal = False
        opts.import_materials = True
        opts.import_textures = True
        opts.static_mesh_import_data.set_editor_property("combine_meshes", True)
        task.options = opts
    # GLB/GLTF use the built-in glTF importer (no options object required in 5.8).

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    LOG("[import] imported: {}".format(task.imported_object_paths))
    return task.imported_object_paths


# --------------------------------------------------------------------------- #
# 2. Open master level + stage the asset
# --------------------------------------------------------------------------- #
def open_master_level(level_path):
    LOG("[stage] opening master level {}".format(level_path))
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    les.load_level(level_path)


def spawn_asset(imported_paths):
    """Place the first imported static mesh at the level's StagingAnchor, else origin."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    # >>> PROJECT-SPECIFIC: place a tagged actor named 'StagingAnchor' in each master
    #     level to control where imported assets land. Falls back to world origin.
    location = unreal.Vector(0, 0, 0)
    rotation = unreal.Rotator(0, 0, 0)
    for actor in eas.get_all_level_actors():
        if actor.actor_has_tag("StagingAnchor"):
            location = actor.get_actor_location()
            rotation = actor.get_actor_rotation()
            break

    mesh = None
    for path in imported_paths:
        obj = unreal.load_asset(path)
        if isinstance(obj, unreal.StaticMesh):
            mesh = obj
            break
    if mesh is None:
        LOG_WARN("[stage] no StaticMesh found in import; skipping spawn")
        return None

    actor = eas.spawn_actor_from_object(mesh, location, rotation)
    actor.set_actor_label("Staged_Asset")
    LOG("[stage] spawned {} at {}".format(mesh.get_name(), location))
    return actor


# --------------------------------------------------------------------------- #
# 3. Cinematic render via Movie Render Queue
# --------------------------------------------------------------------------- #
def render_cinematic(cfg, project_slug):
    out_dir = os.path.join(cfg["paths"]["output_cinematics"], project_slug)
    os.makedirs(out_dir, exist_ok=True)
    preset_path = cfg["unreal"]["render_preset_cinematic"]
    LOG("[cinematic] MRQ preset {} -> {}".format(preset_path, out_dir))

    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)

    # >>> PROJECT-SPECIFIC: the level sequence that drives the cinematic camera.
    job.sequence = unreal.SoftObjectPath("/Game/Cinematics/Seq_{}".format(project_slug)) \
        if unreal.EditorAssetLibrary.does_asset_exist("/Game/Cinematics/Seq_{}".format(project_slug)) \
        else unreal.SoftObjectPath("/Game/Cinematics/Seq_Default")
    job.map = unreal.SoftObjectPath(unreal.EditorLevelLibrary.get_editor_world().get_path_name())

    preset = unreal.load_asset(preset_path)
    if preset:
        job.set_configuration(preset.get_configuration())

    # Override output directory so the host knows where files land.
    out_setting = job.get_configuration().find_or_add_setting_by_class(
        unreal.MoviePipelineOutputSetting)
    out_setting.output_directory = unreal.DirectoryPath(os.path.abspath(out_dir))
    out_setting.file_name_format = "{sequence_name}_{frame_number}"

    executor = unreal.MoviePipelinePIEExecutor()
    finished = {"done": False, "success": False}

    def _on_finished(exec_ref, success):
        finished["done"] = True
        finished["success"] = success
        LOG("[cinematic] finished success={}".format(success))

    executor.on_executor_finished_delegate.add_callable(_on_finished)
    subsystem.render_queue_with_executor_instance(executor)

    # Block until MRQ completes (headless run keeps the process alive).
    timeout = time.time() + 60 * 30
    while not finished["done"] and time.time() < timeout:
        unreal.SystemLibrary.delay(unreal.get_editor_world(), 1.0)
        time.sleep(1.0)
    return out_dir if finished["success"] else None


# --------------------------------------------------------------------------- #
# 4. 360 stereo panorama capture (Panoramic Capture plugin)
# --------------------------------------------------------------------------- #
def capture_panoramas(cfg, project_slug):
    """
    Capture an equirectangular 360 panorama at each actor tagged 'TourPoint'.
    Uses the Panoramic Capture plugin's console command, which writes per-eye
    equirect frames. We move the camera to each TourPoint then trigger a capture.
    """
    out_dir = os.path.abspath(os.path.join(cfg["paths"]["output_panoramas"], project_slug))
    os.makedirs(out_dir, exist_ok=True)
    res_x, res_y = cfg["unreal"].get("panorama_resolution", [8192, 4096])

    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    tour_points = [a for a in eas.get_all_level_actors() if a.actor_has_tag("TourPoint")]
    if not tour_points:
        LOG_WARN("[pano] no 'TourPoint' actors found; capturing one panorama at origin")
        tour_points = [None]

    world = unreal.get_editor_world()
    captured = []

    # Configure plugin output. The plugin reads these CVars.
    unreal.SystemLibrary.execute_console_command(world, "SP.OutputDir \"{}\"".format(out_dir))
    unreal.SystemLibrary.execute_console_command(world, "SP.StepCaptureWidth {}".format(res_x))
    unreal.SystemLibrary.execute_console_command(world, "SP.HorizontalAngularIncrement 30")
    unreal.SystemLibrary.execute_console_command(world, "SP.VerticalAngularIncrement 30")

    for i, tp in enumerate(tour_points):
        scene_name = "scene{:02d}".format(i + 1)
        if tp is not None:
            loc = tp.get_actor_location()
            # >>> PROJECT-SPECIFIC: move the panoramic capture pawn / player start.
            unreal.SystemLibrary.execute_console_command(
                world, "SP.SetCameraLocation {} {} {}".format(loc.x, loc.y, loc.z))
            scene_name = slugify(tp.get_actor_label()) or scene_name
        LOG("[pano] capturing {} ({}x{})".format(scene_name, res_x, res_y))
        unreal.SystemLibrary.execute_console_command(world, "SP.PanoramicScreenshot")
        # Give the plugin time to walk all capture steps and stitch.
        time.sleep(15)
        captured.append(scene_name)

    # Write a sidecar so the tour builder knows the scene order + labels.
    sidecar = {
        "project": project_slug,
        "resolution": [res_x, res_y],
        "scenes": captured,
    }
    with open(os.path.join(out_dir, "scenes.json"), "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2)
    LOG("[pano] {} panorama(s) -> {}".format(len(captured), out_dir))
    return out_dir


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    args = parse_args()
    cfg = load_config(args.config)
    slug = slugify(args.project_name)
    LOG("==== render_pipeline START: {} ({}) ====".format(args.project_name, args.category))

    result = {"project": args.project_name, "slug": slug, "category": args.category,
              "cinematic_dir": None, "panorama_dir": None, "ok": False, "stage": "start"}

    try:
        result["stage"] = "import"
        imported = import_asset(args.asset, slug)

        result["stage"] = "stage"
        level = cfg["unreal"]["master_levels"][args.category]
        open_master_level(level)
        spawn_asset(imported)

        result["stage"] = "cinematic"
        result["cinematic_dir"] = render_cinematic(cfg, slug)

        result["stage"] = "panorama"
        result["panorama_dir"] = capture_panoramas(cfg, slug)

        result["ok"] = True
        result["stage"] = "done"
    except Exception as e:  # noqa
        LOG_ERR("[render_pipeline] FAILED at {}: {}".format(result["stage"], e))
        result["error"] = str(e)

    # Emit a machine-readable result the host orchestrator parses from the log file.
    out_marker = os.path.join(cfg["paths"]["logs"] if "logs" in cfg["paths"]
                              else "pipeline/logs", "render_result_{}.json".format(slug))
    try:
        os.makedirs(os.path.dirname(out_marker), exist_ok=True)
        with open(out_marker, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    except Exception as e:  # noqa
        LOG_ERR("could not write result marker: {}".format(e))

    LOG("RENDER_RESULT_JSON=" + json.dumps(result))
    LOG("==== render_pipeline END ok={} ====".format(result["ok"]))


if __name__ == "__main__":
    main()
