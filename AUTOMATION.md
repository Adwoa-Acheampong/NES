# Full Automation — UE 5.8 MCP → Render → Tour → Publish

This is the "everything is automated" path. The terminal agent **builds the 3D
scene itself** inside Unreal via the official UE 5.8 MCP plugin, then the
deterministic scripts render and publish. You trigger it in plain language —
locally or from your phone via OpenClaw.

```
You (Telegram/WhatsApp)
   → OpenClaw gateway
      → Claude Code / Codex (terminal, beside the open Editor)
         → UE 5.8 MCP plugin   : builds scene (geometry, materials, lighting, TourPoints)
         → run_pipeline.py      : 4K cinematic + 360° capture (headless, deterministic)
         → build_tour + publish : Pannellum tour live on blkklegacy
   ← summary relayed back to you
```

Two engines of automation, on purpose:
- **LLM + MCP** authors the scene (creative, conversational, no hand-modeling).
- **Python scripts** render + publish (reproducible, identical every run).

---

## What's official vs. what to budget time for
- UE 5.8 shipped an **experimental** first-party MCP plugin (Unreal Fest,
  June 17 2026). It connects LLMs to the Editor: Blueprints, assets, levels,
  materials, meshes, sequencing, PCG, lighting, testing.
- The setting is under **Edit → Editor Preferences → General → Model Context
  Protocol** (NOT Project Settings). Enabling the Unreal MCP plugin auto-enables
  the Toolset Registry dependency — there's no separate registries toggle.
- It's **experimental** — expect breaking changes before UE6. Win64-first.

---

## One-time setup

### 1. Enable the UE MCP plugin
1. Open your project in **UE 5.8**.
2. **Edit → Plugins**, search **Unreal MCP** (internal id `ModelContextProtocol`),
   tick **Enabled** — this auto-enables the **Toolset Registry** plugin — restart.
3. **Edit → Editor Preferences → General → Model Context Protocol** → turn on
   **Auto Start Server** (default port **8000**, path `/mcp`). Note: per Epic's
   official doc there is NO separate "toolset registries" toggle; it's automatic.
4. Confirm in the **Output Log** that the server bound to
   `http://127.0.0.1:8000/mcp`. Port is **8000** unless you change it here.

### 2. Point your terminal agent at it
Pick the agent you saw in the TikTok workflow.

**Easiest — let the plugin generate the configs.** In the UE console (backtick `` ` ``):
```
ModelContextProtocol.GenerateClientConfig All
```
This writes `.mcp.json` (Claude Code) and the Codex TOML into the project root,
pointing at `http://127.0.0.1:8000/mcp` (server name `unreal-mcp`).

Manual alternative — `claude mcp add unreal-mcp --transport http http://127.0.0.1:8000/mcp`.

Verify: launch the agent **from the project root** beside the open Editor and ask
"What actors do I have selected?" Real answer = bridge works. Nothing/error →
the editor/server isn't running, or you launched the agent from the wrong folder.

### 3. Give the agent the build rules
Load `pipeline/agent/scene-recipe.md` as context (Claude Code project rule, a
saved Agent Skill, or paste it). This guarantees the agent creates the
`StagingAnchor` / `TourPoint` / `Seq_<slug>` actors the render script needs.

### 4. Prereqs for the render/publish half
See `pipeline/README.md` §0–§1 (Python deps, `config.json`, Node for the image
optimizer, hosting). Hosting recommendation: Cloudflare Pages / Netlify
(git-push) for the static site + 360° tours; on-demand cloud GPU only for Pixel
Streaming.

---

## Daily use

### Locally (one prompt)
With the Editor open and the agent running beside it:
```
> Build a Modern Villa interior per scene-recipe.md: 600x510cm living room,
  two glass doors to a courtyard, warm daylight, 4 tour points. Then run the
  publish pipeline.
```
The agent builds the scene over MCP, saves, runs
`python pipeline/run_pipeline.py --project-name "Modern Villa" --category architecture`,
and reports the result.

### From your phone (OpenClaw)
OpenClaw bridges your messenger to the terminal agent. After the OpenClaw setup
in `README.md` §5:
> "Build the Havilah Estate villa tour from the brief in our notes and put it
>  live on the estate page."

OpenClaw runs the agent with that prompt + `scene-recipe.md`, the agent builds +
renders + publishes, and OpenClaw relays the `PIPELINE_SUMMARY_JSON` summary back
to you. For long renders it runs detached and messages you when done.

---

## How the two halves connect (why it's reliable)
The agent is free to be creative *building* the scene, but it must leave behind
the exact actors the deterministic renderer keys off:
- one `StagingAnchor`, one `TourPoint` per viewpoint (label = tour scene name),
  and `Seq_<slug>` (or `Seq_Default`).
`run_pipeline.py` then renders those identically every time → consistent tours,
no per-run surprises. Full contract is in `pipeline/agent/scene-recipe.md`.

---

## Security (don't skip)
The MCP gives the agent **full editor control** — treat its permissions like
production credentials.
- Run the agent only beside a project you intend it to modify.
- Keep the recipe's guardrails (no deleting unrelated assets).
- The MCP endpoint is `localhost` only; don't expose the port externally.
- OpenClaw can trigger real renders/publishes — scope who can message it.

---

## Honest limits of what was set up from the assistant session
- I **cannot** enable the UE plugin, toggle Toolset registries, or run the
  terminal agent for you — those happen on your machine. The configs, recipe,
  and scripts here are turnkey; you do the 4 one-time setup steps above.
- The UE MCP tool names/port are version-specific (experimental). If a tool the
  recipe assumes isn't present, check the plugin's Toolset registry list and the
  Epic doc: "Unreal MCP in Unreal Editor".
- The render-side scripts are syntax-checked and the tour/publish stages were
  dry-run tested; the UE render stage still needs one validation pass on your
  hardware (see README §3 markers).

## File map (automation layer)
```
pipeline/agent/
├── claude_mcp.json    ← Claude Code .mcp.json snippet (set <PORT>)
├── codex_config.toml  ← Codex config.toml snippet (set <PORT>)
└── scene-recipe.md    ← build rules the agent follows (the LLM↔pipeline contract)
pipeline/AUTOMATION.md ← this file
```
