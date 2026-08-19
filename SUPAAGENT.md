# SupaAgent Integration Map

This folder is the first working production module for the wider personal
SupaAgent. It should not stay BLKK-only. Treat it as the media, render, and
publish vertical that the general agent can call for any project.

## Current Working Vertical

```text
prompt / phone message / dropped asset
  -> NES router
  -> Claude Code or Codex
  -> Unreal 5.8 MCP or local ComfyUI
  -> deterministic Python pipeline
  -> website assets, tours, videos, logs
  -> publish target
  -> summary back to you
```

The important design is already here: creative agents build or prepare the
scene, but deterministic scripts own rendering, packaging, publishing, and logs.

## Starting SupaAgent

The local launcher lives in `pipeline/supaagent/`.

No-command control panel:

```text
Double-click START_SUPAAGENT.bat
```

That opens a browser control panel where you can check services, start ComfyUI,
start BLKK Star Hub, generate a hero still, animate it, and copy approved local
outputs into the Hub public asset folder.

First-time setup:

```powershell
copy pipeline\supaagent\config.example.json pipeline\supaagent\config.json
notepad pipeline\supaagent\config.json
```

At minimum, set the ComfyUI working directory. Either set an environment
variable:

```powershell
setx COMFYUI_DIR "C:\Path\To\ComfyUI"
```

or replace `%COMFYUI_DIR%` directly inside `pipeline/supaagent/config.json`.

Status check only:

```powershell
.\pipeline\supaagent\start.ps1 -StatusOnly
```

Dry run, showing what would launch:

```powershell
.\pipeline\supaagent\start.ps1 -DryRun
```

Start/check the configured services:

```powershell
.\pipeline\supaagent\start.ps1
```

Start/check one service:

```powershell
.\pipeline\supaagent\start.ps1 -Only comfyui
.\pipeline\supaagent\start.ps1 -Only openclaw
```

The launcher emits `SUPAAGENT_STATUS_JSON=` so NES or another orchestrator
can read service state.

## Registered Capabilities

| Capability | Entry point | Best for | Output marker |
|---|---|---|---|
| `render_tour` | `pipeline/run_pipeline.py` | UE 5.8 cinematic, 360 tour, optional Pixel Streaming | `PIPELINE_SUMMARY_JSON=` |
| `watch_assets` | `pipeline/watch_folder.py` | Hands-off asset intake from `pipeline/hot_folder` | pipeline log JSON |
| `publish_media` | `pipeline/publish.py` | Stage media, regenerate variants, deploy | `PUBLISH_RESULT_JSON=` |
| `generate_image` | `pipeline/media/gen_image.py` | Hero images, thumbnails, concepts via ComfyUI | `IMAGE_RESULT_JSON=` |
| `generate_video` | `pipeline/media/gen_video.py` | Short loops and image-to-video via Wan/ComfyUI | `VIDEO_RESULT_JSON=` |
| `build_ue_scene` | `pipeline/agent/scene-recipe.md` + UE MCP | Agent-built 3D scenes, TourPoints, sequences | saved UE level |
| `phone_control` | `pipeline/nes/*` | Telegram/WhatsApp-triggered orchestration | messenger reply |
| `start_services` | `pipeline/supaagent/start.py` | Check/start ComfyUI, OpenClaw, app URLs, optional UE MCP | `SUPAAGENT_STATUS_JSON=` |

## General SupaAgent Layers

```text
1. Inbox
   WhatsApp, Telegram, desktop prompt, hot folder, browser, scheduled job.

2. Router
   NES is the local hub. It decides which engine or command should run.

3. Memory
   Global personal style, project records, asset indexes, decisions, people,
   channels, approval history. Store credentials as references/env vars only.

4. Engines
   Claude Code, Codex, Claude Design, OpenAI, Midjourney, ComfyUI, UE 5.8 MCP,
   browser/NES operators, and future tools.

5. Capability Modules
   Web build, media generation, 3D tours, social content, outreach, research,
   deployment, reporting.

6. Approval Gate
   The agent can prepare and test freely. It asks before public, costly, or
   irreversible actions.

7. Execution + Log
   Run commands detached when slow, emit machine-readable JSON, save logs, reply
   with the summary and next decision.
```

## Routing Policy

Use the lightest working tier:

```text
still image / thumbnail / concept
  -> generate_image

short animation / hero loop / image-to-video
  -> generate_video

true walkthrough / car showroom / building tour / 360 / interaction
  -> build_ue_scene, then render_tour

website edits / app builds / automation code
  -> Codex or Claude Code, then tests/browser check

visual direction / layout critique / brand mood
  -> Claude Design or creative-director prompt

message sending / WhatsApp / social posting
  -> NES/browser operator, with approval before send/post
```

## Approval Rules

No approval needed:
- Drafting copy, prompts, scene recipes, captions, scripts.
- Running local checks and dry runs.
- Generating local images/videos.
- Reading logs and indexing local assets.

Approval required:
- Sending WhatsApp, email, DMs, or form submissions.
- Posting to social media.
- Publishing or deploying to a live site.
- Spending money or starting paid cloud GPU resources.
- Deleting or moving user files.
- Changing credentials, access, or platform settings.

## Existing Gap Closed

`pipeline/openclaw/run.bat` and `blkk-render.command.json` expected asset-less
phone commands to use the newest hot-folder asset. `run_pipeline.py` now matches
that behavior: `--asset` is optional and an `intake` stage records whether the
asset was explicit or resolved from `pipeline/hot_folder`.

## Next Build Steps

1. Add a generic `supaagent/projects/` registry so this pipeline can serve BLKK,
   car projects, real estate projects, client sites, and social campaigns.
2. Add an asset indexer that tags files by project, subject, medium, format,
   rights/status, and recommended use.
3. Add a job schema:

```json
{
  "id": "job_2026_06_30_001",
  "project": "example-build",
  "intent": "generate_video",
  "brief": "Create a 5 second hero loop from this product still.",
  "inputs": [],
  "approval": "required_before_publish",
  "status": "queued"
}
```

4. Add a dashboard or inbox folder where outputs wait for approval before
   publishing, posting, or messaging.
5. Rename BLKK-specific environment assumptions in future wrappers into generic
   variables such as `SUPA_WORKSPACE`, while keeping `BLKK_SITE` as this
   project module's compatibility alias.
