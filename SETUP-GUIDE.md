# Black Star Legacy — Full Setup Guide (zero → first automated tour)

Follow top to bottom. Each stage ends with a **✅ check** so you know it worked
before moving on. Most of the time cost is downloads (Unreal Engine is tens of GB).

Legend: `▢` = do this, `✅` = how to confirm success.

---

## Stage 1 — Epic account + Unreal Engine 5.8

▢ Open Chrome → **https://www.unrealengine.com/en-US/download**
▢ Sign in, or **create a free Epic Games account** (verify the email).
▢ Download the **Epic Games Launcher** (~60 MB installer) and run it. Accept the
   Windows UAC prompt (that one's yours — it can't be automated).
▢ Open the launcher → sign in → top tabs → **Unreal Engine** → **Library**.
▢ Click the **+** next to "ENGINE VERSIONS" → choose **5.8.x** → **Install**.
   - Default install location is fine. Needs ~50–100 GB free during install.
   - Leave "Starter Content" and "Engine Source" optional; defaults are OK.

✅ When done, the launcher shows **5.8** with a **Launch** button.

---

## Stage 2 — Enable the plugins we need

▢ In the launcher click **Launch** (5.8). On the Project Browser pick
   **Games → Blank**, Blueprint, name it `BlkkLegacyStaging`, location anywhere
   sensible, **Create**.
▢ Editor → **Edit → Plugins**. Search and **enable** each of these, then
   **restart** the editor when prompted:
   - **Unreal MCP**  (internal name "Model Context Protocol")  ← the key one
   - **Python Editor Script Plugin**
   - **Movie Render Queue**
   - **Panoramic Capture**
   - **Datasmith** importers (only if you'll import Revit/CAD later)
   - **Pixel Streaming** (only needed for the flagship interactive stream)

✅ After restart, **Edit → Plugins** shows all of the above ticked.

---

## Stage 3 — Start the MCP server (Editor Preferences, NOT Project Settings)

The Toolset Registry auto-enables with the Unreal MCP plugin — there's no
separate registries toggle. You just turn the server on.

▢ **Edit → Editor Preferences** → **General** group → **Model Context Protocol**.
▢ Turn on **Auto Start Server**. Default **Server Port Number** is **8000**,
   URL path `/mcp`.
▢ Restart, then **Window → Output Log** → confirm it bound to
   `http://127.0.0.1:8000/mcp`.
▢ Generate the agent configs from the console (backtick `` ` ``):
   `ModelContextProtocol.GenerateClientConfig All` → writes `.mcp.json` + Codex
   TOML to the project root.

✅ Output Log shows the server on `http://127.0.0.1:8000/mcp` (port 8000 default).

---

## Stage 4 — Install + connect Claude Code (your agent)

You already have Node.js. In a **new terminal** (PowerShell or CMD):

▢ Install Claude Code:
```
npm install -g @anthropic-ai/claude-code
```
▢ Connect it to Unreal (use the port from Stage 3):
```
claude mcp add unreal-engine --transport http http://localhost:<PORT>/mcp
```
   (Alternative: copy the `mcpServers` block from
   `pipeline/agent/claude_mcp.json` into a `.mcp.json`, replacing `<PORT>`.)
▢ With the **editor still open**, start the agent beside it:
```
claude
```
▢ Test the bridge — type:
```
List all actors in the current level.
```

✅ It replies with real actor names from your level. If it returns nothing or an
   error → the Toolset registries (Stage 3) aren't enabled, or the port is wrong.

---

## Stage 5 — Render/publish prerequisites (one-time)

In a terminal at the website folder:
```
cd "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
python -m pip install -r pipeline\requirements.txt
copy pipeline\config.example.json pipeline\config.json
notepad pipeline\config.json
```
▢ In `config.json` set:
   - `unreal.editor_cmd` → path to `UnrealEditor-Cmd.exe`
     (default: `C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe`)
   - `unreal.project` → full path to your `BlkkLegacyStaging.uproject`
   - `publish.method` → `git` for now (we set up hosting in Stage 7).
▢ Make sure the image optimizer deps are present once:
```
cd tools && npm install && cd ..
```

✅ `python pipeline\run_pipeline.py --help` prints usage with no error.

---

## Stage 6 — First automated scene + tour

▢ Editor open, `claude` running beside it. Paste the scene recipe as context:
   open `pipeline/agent/scene-recipe.md`, copy all, paste into Claude with:
```
Use these rules for everything below:
<paste scene-recipe.md here>

Now build the "Havilah House" as category architecture:
a warm modern interior, ~600x500cm living space, two windows on the back wall,
glass doors to a courtyard, 4 tour points (Living Room, Courtyard, Entry,
Upper Landing). Save all when done, then run:
python pipeline/run_pipeline.py --project-name "Havilah House" --category architecture
```

✅ You get a `PIPELINE_SUMMARY_JSON=` line, and `tours/havilah-house/index.html`
   exists. Open it with `node serve-local.js` then browse to the tour.

---

## Stage 7 — Publish the site (hosting)

Recommended: **Cloudflare Pages** or **Netlify** (free, deploys on git push).
▢ Put the site under git and push to GitHub:
```
cd "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
git init && git add -A && git commit -m "init: site + pipeline"
```
   then create a GitHub repo and push (GitHub Desktop is installed if you prefer).
▢ In Cloudflare Pages / Netlify: connect the repo, build command = none,
   output dir = `/`.
▢ Keep `publish.method = "git"` — every pipeline run commits new media and
   pushes; the host auto-deploys.

✅ Visiting your site URL shows the page; `/tours/havilah-house/` shows the tour.

---

## Stage 8 — Phone control with OpenClaw (optional, last)

▢ `npm install -g openclaw` → `openclaw init` → `openclaw gateway:watch`
▢ Connect the Telegram or WhatsApp adapter when prompted.
▢ Set the site path so the command works:
```
setx BLKK_SITE "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
```
▢ Register the command using `pipeline/openclaw/blkk-render.command.json` (or
   point a shell command at `pipeline\openclaw\run.bat`).

✅ Message the bot: *"Build the Nubia House tour and publish it"* → it runs the
   agent + pipeline and replies with the summary.

---

## Order of operations (the short version)
1. Epic account → install UE 5.8.
2. Enable plugins (esp. **Unreal MCP**) → restart.
3. **Enable MCP Toolset registries** → note the port.
4. `npm i -g @anthropic-ai/claude-code` → `claude mcp add unreal-engine ...` → test.
5. `pip install -r pipeline/requirements.txt`, set `config.json`.
6. Run `claude` beside the editor, build a scene with `scene-recipe.md`, run the pipeline.
7. Git + Cloudflare/Netlify for hosting.
8. OpenClaw for phone triggering.

## If something stalls, tell me
- the exact error text, or
- the Output Log line (Stage 3), or
- what the `claude` test in Stage 4 returned.
I'll debug that specific step.
