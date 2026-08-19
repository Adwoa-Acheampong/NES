# The Black Star Legacy Agent — roster, roles, and routing

This is the "whole agent": a small team of cooperating agents, not one chatbot.
It turns a phone message into a published 3D virtual tour. This file defines who
does what and how requests are routed, so the system behaves predictably.

```
        Telegram / WhatsApp  (you)
                 │
                 ▼
        ┌──────────────────┐        reasoning model: Anthropic Claude
        │    OpenClaw       │  ← orchestrator / 24-7 hub (Node gateway)
        │  (router + memory)│     routes requests, runs jobs detached, replies
        └──────────────────┘
            │            │
   build/art│            │script/automation
            ▼            ▼
   ┌───────────────┐  ┌───────────────┐
   │  Claude Code  │  │    Codex      │   both connected to the SAME UE MCP
   │  (builder /   │  │  (scripter)   │
   │ art-director) │  │               │
   └───────────────┘  └───────────────┘
            │            │
            └─────┬──────┘
                  ▼  MCP (http://localhost:<PORT>/mcp)
        ┌──────────────────────────┐
        │ Unreal Engine 5.8 Editor │  builds scene: geometry, PCG, lighting, cameras
        │   + MCP plugin           │
        └──────────────────────────┘
                  │ saves level
                  ▼
        ┌──────────────────────────┐
        │  pipeline scripts        │  render → 360° tour → publish (deterministic)
        │  run_pipeline.py         │
        └──────────────────────────┘
                  ▼
            blkklegacy website (Cloudflare/Netlify)
```

---

## Roster & responsibilities

### 1. OpenClaw — orchestrator (the hub)
- Always-on local Node gateway. The only agent you talk to directly.
- Receives messages from Telegram/WhatsApp, holds light project memory, and
  **routes** each request to the right engine (below).
- Runs long jobs **detached** and posts the result when done.
- Uses your **Anthropic Claude** subscription as its reasoning/planning model.
- Owns the registered command `blkk_render` (see `openclaw/blkk-render.command.json`).

### 2. Claude Code — builder / art-director
- Connected to the UE MCP (`agent/claude_mcp.json`).
- Best at: interpreting a creative brief, building/blocking out the scene,
  art-directing lighting, placing the `StagingAnchor` / `TourPoint` / `Seq_<slug>`
  actors per `agent/scene-recipe.md`, then launching the render pipeline.
- Default engine for "build / design / make me a tour" requests.

### 3. Codex — scripter / automation
- Also connected to the UE MCP (`agent/codex_config.toml`). You already have it.
- Best at: writing/fixing Python (`pipeline/*.py`), Blueprint graph logic,
  batch operations, debugging failed runs, repetitive editor automation.
- Default engine for "fix / script / batch / automate / debug" requests.

### 4. Unreal Engine 5.8 + MCP plugin — execution surface
- The editor both agents drive over one local MCP endpoint.
- Must be running, with the MCP plugin **and Toolset registries** enabled.

### 5. Pipeline scripts — deterministic output
- `run_pipeline.py` → cinematic + 360° capture → Pannellum tour → publish.
- Same output every run; agents call it rather than re-implementing rendering.

---

## Media tiers — use the lightest tool that does the job
Not everything needs Unreal. OpenClaw picks the tier by what's asked:

| Tier | For | Tool | Script |
|---|---|---|---|
| **1 — Image** | hero shots, backgrounds, thumbnails, concepts | local ComfyUI (Flux/SDXL) | `media/gen_image.py` |
| **2 — Video** | short loops, simple portrait/product motion | local ComfyUI (Wan) | `media/gen_video.py` |
| **3 — 3D** | walkthroughs, 360° tours, interactive/Pixel Streaming | Unreal 5.8 + MCP | `run_pipeline.py` |

Tiers 1–2 run on your GPU (no engine) and publish through the SAME `publish.py`.
The agents (Claude Code/Codex) orchestrate — they write the prompt and call the
script; ComfyUI does the GPU work. Claude can also hand-author code-based visuals
(SVG/HTML) directly when that's what's wanted.

## Routing policy (how OpenClaw chooses)
| Incoming intent (examples) | Engine / Tier | Then |
|---|---|---|
| "make a hero image / background / thumbnail for X" | **Tier 1** (Claude Code calls `gen_image.py`) | → optimizer → publish |
| "animate this still", "short hero loop", "5-sec clip" | **Tier 2** (calls `gen_video.py`, Wan) | → publish |
| "build/design/create a **tour**", "art-direct the lighting", "3D walkthrough" | **Tier 3 / Claude Code** | builds scene via MCP → `run_pipeline.py` |
| "fix the render script", "batch these 5", "debug the failed run", "write a Blueprint that…" | **Codex** | edits/automates → re-runs |
| "publish what's already made", "re-deploy" | OpenClaw direct | runs `publish.py` |
| "status / what's live / last run" | OpenClaw direct | reads `pipeline/logs/*.json` |

Rule of thumb: still → Tier 1; motion-from-a-still or simple animation → Tier 2;
needs real 3D space/parallax/interactivity → Tier 3 (Unreal).

Tie-breaker: creative/visual → Claude Code; code/automation → Codex. Either can
hand off to the other (Claude Code builds, asks Codex to harden a script).

## The contract that keeps it reliable
Whichever agent builds the scene MUST leave the actors the renderer needs
(`StagingAnchor`, one labelled `TourPoint` per viewpoint, `Seq_<slug>` or
`Seq_Default`) — full spec in `agent/scene-recipe.md`. That's the seam between
the creative half (LLM authoring) and the deterministic half (scripts).

## Security posture
- The UE MCP grants full editor control — treat agent permissions like prod
  credentials. Endpoint stays on `localhost`.
- OpenClaw can trigger real renders/publishes — restrict who can message it
  (allow-list your own chat IDs in the gateway config).
- Publishing pushes to your live site — keep `publish.method` pointed at a repo
  you control; review the first few automated commits.

## Specialized Skills Registry
The `agent/skills` directory now contains a deduplicated suite of over 300 specialized agents/skills imported from Antigravity/Claude. This includes the frontend, design critique, systems design, and business analyst skills.

These specialized agents are routed through `OpenClaw` automatically when their corresponding intent matches.
Included domains:
- Backend Architecture
- Cloud Integration & Optimization
- Data Science & ML
- Business Analysis & Dashboards
- Systems Programming
- CI/CD & DevOps
- Documentation & Testing
- Research & Security
