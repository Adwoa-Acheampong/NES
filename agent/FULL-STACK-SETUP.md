# Full-Stack Agent Setup — ordered, do top to bottom

Stand up the whole agent: UE MCP → Claude Code + Codex → OpenClaw → phone control
→ first end-to-end tour. Each layer has a ✅ check; don't move on until it passes.

> What I (the assistant) can't do from here: install software, type into your
> terminal, or run the editor on your machine. Everything below is exact and
> copy-pasteable; you run it. Paste me any error and I'll fix that step.

Prereqs already done: ✅ disk cleared, ✅ UE 5.8 installed. You also already have
**Node.js** and **Codex** installed.

---

## Layer 1 — Unreal Engine MCP (the execution surface)
1. Launch UE 5.8 → create/open project `BlkkLegacyStaging` (Games → Blank).
2. **Edit → Plugins**: enable **Unreal MCP** (auto-enables the Toolset Registry
   plugin), **Python Editor Script Plugin**, **Movie Render Queue**,
   **Panoramic Capture**. Restart.
3. **Edit → Editor Preferences → General → Model Context Protocol**: turn on
   **Auto Start Server** (default port **8000**, path `/mcp`). There is NO
   separate "Toolset registries" toggle — it's automatic.
4. **Window → Output Log**: confirm the server bound to `http://127.0.0.1:8000/mcp`.
5. Console (backtick `` ` ``) → `ModelContextProtocol.GenerateClientConfig All`
   writes `.mcp.json` (Claude Code) + Codex TOML to the project root.

✅ Endpoint is `http://127.0.0.1:8000/mcp` (port 8000 unless you changed it).

---

## Layer 2 — Connect the two agent engines to the MCP
Easiest: let the plugin write the configs. In the UE console (backtick `` ` ``):
```
ModelContextProtocol.GenerateClientConfig All
```
This writes `.mcp.json` (Claude Code) and the Codex TOML into the **project root**,
already pointing at `http://127.0.0.1:8000/mcp` (server name `unreal-mcp`).

Install Claude Code if needed: `npm install -g @anthropic-ai/claude-code`.
(Manual alternative: `claude mcp add unreal-mcp --transport http http://127.0.0.1:8000/mcp`.)

Then launch each agent **from the project root** (where the configs were written),
with the editor open:
```
claude
> List all actors in the current level.        # should return real names
```
```
codex
> List all actors in the current level.         # should return real names
```
✅ Both return real actor names. (Empty/error → Toolset registries off or wrong PORT.)

---

## Layer 3 — Render/publish pipeline prereqs
```
cd "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
python -m pip install -r pipeline\requirements.txt
copy pipeline\config.example.json pipeline\config.json
cd tools && npm install && cd ..
```
Edit `pipeline\config.json`: `unreal.editor_cmd`, `unreal.project` (your .uproject),
`publish.method = "git"`.

✅ `python pipeline\run_pipeline.py --help` prints usage.

---

## Layer 4 — OpenClaw (the orchestrator / hub)
```
npm install -g openclaw
openclaw init
```
1. Copy `pipeline/openclaw/openclaw.config.example.jsonc` → your OpenClaw config;
   set `<PORT>`, your Anthropic auth, and `BLKK_SITE`.
2. Register the pipeline command from `pipeline/openclaw/blkk-render.command.json`.
3. Set env:
   ```
   setx BLKK_SITE "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
   ```
4. Start it (keep the UE editor open in another window):
   ```
   openclaw gateway:watch
   ```
✅ OpenClaw starts, lists engines `claude-code` + `codex`, and the `blkk_render` command.

---

## Layer 5 — Messaging channel (phone control)
1. Create a Telegram bot (BotFather) → token. Set it:
   ```
   setx OPENCLAW_TELEGRAM_TOKEN "<token>"
   ```
2. In the OpenClaw config, set `channels.telegram.enabled = true` and put **your**
   Telegram chat id in `allowedChatIds` (lock it to you).
3. Restart `openclaw gateway:watch`. Message the bot "ping".

✅ The bot replies. (WhatsApp adapter is analogous; enable when ready.)

---

## Layer 6 — First end-to-end run
From your phone, message the bot:
```
Build the Havilah House interior tour — warm modern, ~600x500cm living space,
glass doors to a courtyard, 4 tour points. Then publish it.
```
OpenClaw routes to **Claude Code** → builds the scene over the UE MCP (using
`AGENTS.md` + `scene-recipe.md`) → runs `run_pipeline.py` → tour built + published
→ you get the `PIPELINE_SUMMARY_JSON` summary back.

✅ `tours/havilah-house/index.html` exists and (after Layer 7) is live on the site.

Try the scripter path too:
```
The last render had no panoramas — debug it and re-run.
```
→ routes to **Codex**, which inspects logs/scene and fixes.

---

## Layer 7 — Hosting (publish target)
Cloudflare Pages or Netlify, git-push deploy:
```
cd "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
git init && git add -A && git commit -m "init: site + agent pipeline"
```
Push to GitHub, connect the repo in Cloudflare/Netlify (build = none, output = `/`).
Keep `publish.method = "git"` so each run auto-deploys.

✅ Your live URL shows the page and `/tours/<slug>/` shows the tour.

---

## Order at a glance
1. UE MCP + Toolset registries → PORT.
2. Connect Claude Code + Codex to the PORT (both test OK).
3. Pipeline prereqs + `config.json`.
4. OpenClaw gateway with both engines + the command.
5. Telegram channel locked to your id.
6. End-to-end run from phone.
7. Hosting for live publish.

## Files this references
```
pipeline/agent/AGENTS.md                       roster + routing policy
pipeline/agent/scene-recipe.md                 the build contract
pipeline/agent/claude_mcp.json                 Claude Code ↔ UE MCP
pipeline/agent/codex_config.toml               Codex ↔ UE MCP
pipeline/openclaw/openclaw.config.example.jsonc gateway: engines+channels+routing
pipeline/openclaw/blkk-render.command.json     the render command
pipeline/openclaw/run.bat                       wrapper
pipeline/run_pipeline.py                        render → tour → publish
```
