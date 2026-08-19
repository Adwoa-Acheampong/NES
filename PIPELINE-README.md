# Black Star Legacy — UE5.8 → Web Virtual Tour Pipeline

Automated production line for Black Star Legacy portfolio media. Two ways to
feed it, both ending in a **360° Pannellum tour** (+ optional **Pixel Streaming**)
**published to the blkklegacy website**, triggerable from Telegram/WhatsApp via
**OpenClaw**:

- **A) Fully automated (recommended) — the AI builds the scene.** A terminal
  agent (Claude Code / Codex) drives the **UE 5.8 built-in MCP plugin** to
  construct the scene from a sentence (geometry, materials, lighting, cameras),
  then runs the render + publish scripts. **No hand-made 3D assets, no manual
  staging project.** See **`AUTOMATION.md`** — this is the path that matches the
  "everything automated" goal.
- **B) Bring-your-own-asset.** Drop an existing 3D file (FBX/GLB/Datasmith) into
  `hot_folder` and the same render→tour→publish scripts run. Covered below.

```
A) You → OpenClaw → Claude Code/Codex (terminal) → UE 5.8 MCP plugin (builds scene)
                                                  → run_pipeline.py → tour → publish

B) drop asset in hot_folder ─┐
   or: run_pipeline.py  ── orchestrates ──┐
      ├─ 1. render_pipeline.py  → UnrealEditor-Cmd.exe (headless): import → stage → MRQ 4K cinematic + 360° capture
      ├─ 2. build_tour.py       → tours/<slug>/  (Pannellum: index.html + tour.json + panoramas)
      ├─ 3. package_pixelstream.py (flagship only) → UE Pixel Streaming package
      └─ 4. publish.py          → assets/ + tours/ → optimize-images.js → deploy (git/sftp/s3)
```

> **Start here for full automation:** read **`AUTOMATION.md`**. The rest of this
> file documents the render/publish half that both paths share.

> **Honest scope note.** Everything here is ready-to-run, but three things only
> *your* machine/project can supply and must be validated locally before the
> first real run: (a) the UE project + master levels, (b) the Movie Render Queue
> preset and camera/TourPoint actors, (c) your host + credentials. Search the UE
> scripts for `# >>> PROJECT-SPECIFIC` for every spot to confirm. I could not run
> Unreal or installers from the assistant session — these scripts were
> syntax-checked and the web-side stages dry-run tested, but the UE stages need
> one validation pass on your hardware.

---

## 0. Prerequisites

| Component | Why | Install |
|-----------|-----|---------|
| **Unreal Engine 5.8** | Rendering + 360 capture + Pixel Streaming | Epic Games Launcher → Engine 5.8 |
| UE plugins | `Unreal MCP` (for Path A), `Python Editor Script Plugin`, `Movie Render Queue`, `Panoramic Capture`, `Datasmith` (for Revit/IFC), `Pixel Streaming 2` | Enable in the .uproject → Plugins (MCP also needs Toolset registries enabled — see AUTOMATION.md) |
| Terminal agent (Path A) | Claude Code or Codex CLI to drive the UE MCP | `npm i -g @anthropic-ai/claude-code` / Codex CLI |
| **Python 3.10+** (host) | Orchestrator + tour builder + publish | `winget install Python.Python.3.12` |
| **Node.js** | Runs the existing `tools/optimize-images.js` | `winget install OpenJS.NodeJS.LTS` |
| **OpenClaw** | Messenger-triggered orchestration | `npm i -g openclaw` (see §5) |
| Python deps | watchdog, Pillow, paramiko | `python -m pip install -r pipeline/requirements.txt` |

---

## 1. One-time setup

```powershell
cd "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"

# Python deps for the host-side scripts
python -m pip install -r pipeline\requirements.txt

# Create your local config from the template, then edit the paths
copy pipeline\config.example.json pipeline\config.json
notepad pipeline\config.json
```

Edit `pipeline/config.json`:
- `unreal.editor_cmd` → full path to `UnrealEditor-Cmd.exe` (default is the standard 5.8 location).
- `unreal.project` → your `.uproject` (a small staging project; see §3).
- `unreal.master_levels` → the level paths you'll stage assets into.
- `unreal.render_preset_cinematic` → your saved Movie Render Queue preset.
- `publish.method` → `git`, `sftp`, `s3`, or `none` (see §4).

### Expose the UE command-line tool (so OpenClaw can find it)
Add the UE binaries dir to your PATH (optional but convenient):
```powershell
setx PATH "%PATH%;C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64"
```

---

## 2. Daily use

**Manual (one asset):**
```powershell
# Drop "Modern Villa.fbx" into pipeline\hot_folder, then:
python pipeline\run_pipeline.py --project-name "Modern Villa" --category architecture
```

**Hands-off (folder watcher):**
```powershell
python pipeline\watch_folder.py
# now just drop assets into pipeline\hot_folder — each one auto-runs
```

**From your phone (OpenClaw):** see §5. e.g.
> "I added the Modern Villa model to the asset folder. Run the UE5 pipeline to
> generate a 360 tour and 4K animation, then publish it to the portfolio page."

Output lands in:
- `assets/video/<slug>.mp4` — 4K cinematic
- `tours/<slug>/index.html` — the interactive 360° tour
- `assets/<slug>-hero.png` + regenerated AVIF/WebP variants + updated `assets-manifest.json`

### Linking a tour from a page
Add a link/iframe on the relevant page (e.g. `estate.html`):
```html
<a href="tours/modern-villa/index.html">Explore the 360° tour</a>
<!-- or embed -->
<iframe src="tours/modern-villa/index.html" style="width:100%;height:70vh;border:0" loading="lazy"></iframe>
```

---

## 3. The UE staging project

> **Path A (full automation):** you don't have to build this by hand — the MCP
> agent can create the master levels, lighting, and the required actors for you
> following `pipeline/agent/scene-recipe.md`. The notes below are the spec the
> agent fulfils (and the manual fallback for Path B).

The pipeline renders from a UE project with **"showroom" master levels**. Built
once (by you, or automatically by the agent):

1. New UE 5.8 project (Blank, scalable). Save it; point `unreal.project` at the `.uproject`.
2. Create two levels and set them in `config.json → unreal.master_levels`:
   - `MasterLevel_Estate` — lighting + ground for houses.
   - `MasterLevel_Showroom` — studio lighting for cars.
3. In each level:
   - Place an empty actor tagged **`StagingAnchor`** where imported meshes should appear.
   - Place camera/marker actors tagged **`TourPoint`** at each spot you want a 360°
     panorama (one panorama per TourPoint; the tour links them in order).
   - Add a `Seq_Default` Level Sequence with a flythrough camera (the cinematic
     uses `Seq_<slug>` if it exists, else `Seq_Default`).
4. Create a Movie Render Queue preset (4K, PNG/MP4, anti-aliasing) and save it;
   point `unreal.render_preset_cinematic` at it.

> Tip: name a TourPoint "Living Room" and the tour scene becomes "Living Room"
> automatically.

---

## 4. Hosting (currently "not set up")

Your site is **static HTML** — the easiest, cheapest hosting is a static host
with git-push deploys. Recommended:

**Cloudflare Pages or Netlify (free, recommended):**
1. Put this folder under git (`git init`) and push to GitHub.
2. Connect the repo in Cloudflare Pages / Netlify; set build = none, publish dir = `/`.
3. In `config.json` set `publish.method = "git"`. Every pipeline run commits the
   new media and pushes → the host auto-deploys.

**Traditional web host (cPanel/VPS):** set `publish.method = "sftp"`, fill
`publish.sftp.host/username/remote_root`, and use an **SSH key** (`key_path`) or
the `BLKK_SFTP_PASSWORD` environment variable. Never put passwords in config.json.

**AWS:** `publish.method = "s3"`, set bucket + optional CloudFront id (auto-invalidated).

> 360° tours and the cinematic MP4 are plain static files — they work on **any**
> of the above. Pixel Streaming is the exception (next section).

---

## 5. OpenClaw wiring (phone control)

OpenClaw is a local Node gateway that connects a messenger (Telegram/WhatsApp)
to local commands and to Claude.

1. Install + start the gateway:
   ```powershell
   npm install -g openclaw
   openclaw init
   openclaw gateway:watch
   ```
2. Connect your Telegram/WhatsApp adapter per OpenClaw's setup prompts.
3. Register the pipeline command. Use `pipeline/openclaw/blkk-render.command.json`
   as the spec, or point a shell command at the wrapper:
   ```
   pipeline\openclaw\run.bat "Modern Villa" architecture
   pipeline\openclaw\run.bat "Lamborghini" automotive --flagship
   ```
4. Set the `BLKK_SITE` env var (the wrapper and command descriptor use it):
   ```powershell
   setx BLKK_SITE "C:\Users\lenovo\OneDrive\Desktop\Black Star Legacy\blkk-legacy\blkklegacy web platform"
   ```
5. Now message the agent naturally. It runs the command, watches stdout for the
   `PIPELINE_SUMMARY_JSON=` line (also saved to `pipeline/logs/`), and relays the
   result to you.

> Because a UE render takes minutes, have OpenClaw run the job **detached** and
> report back when the summary line appears — don't block the chat on it.

---

## 6. Pixel Streaming (flagship interactive 3D)

Pixel Streaming renders the live UE scene on a **GPU server** and streams pixels
to the browser. It is **not** static — it needs a running machine with an NVIDIA
GPU. Use it sparingly (flagship projects), since the server costs money while on.

Flow:
1. `run_pipeline.py --flagship` builds the package (`package_pixelstream.py` emits
   the exact `RunUAT BuildCookRun` command; run it or let the script drive it).
2. Spin up an **on-demand GPU host** only when you want the experience live:
   - AWS `g5.xlarge`, Tensordock, or Vast.ai (NVIDIA, Windows or Linux).
3. Copy the package up, run the bundled signalling server + the packaged app with
   `-PixelStreamingURL`. Point `pixel_streaming.signalling_server_url` at it.
4. Embed in a page:
   ```html
   <iframe src="https://stream.blkklegacy.com/?project=modern-villa"
           allow="autoplay; fullscreen" style="width:100%;height:80vh;border:0"></iframe>
   ```
5. Shut the GPU host down when not in use to stop billing.

> Practical recommendation: ship **360° tours** as the default everywhere (free,
> instant, fits your static site) and reserve Pixel Streaming for one or two
> hero projects you turn on for launches/meetings.

---

## 7. File map

```
pipeline/
├── README.md                  ← this file (render/publish half)
├── AUTOMATION.md              ← FULL automation: UE MCP → render → tour → publish
├── agent/                     ← terminal-agent (Path A) setup
│   ├── claude_mcp.json        ← Claude Code .mcp.json snippet (set <PORT>)
│   ├── codex_config.toml      ← Codex config.toml snippet (set <PORT>)
│   └── scene-recipe.md        ← build rules the agent follows (LLM↔pipeline contract)
├── config.example.json        ← copy to config.json (gitignored) and edit
├── requirements.txt
├── run_pipeline.py            ← single entry point (OpenClaw calls this)
├── watch_folder.py            ← hot-folder auto-trigger
├── build_tour.py              ← Pannellum 360 tour generator
├── publish.py                 ← stage media + regen variants + deploy
├── ue/
│   ├── render_pipeline.py     ← UE5.8 headless: import → stage → cinematic + 360
│   └── package_pixelstream.py ← UE5.8 Pixel Streaming package (flagship)
├── openclaw/
│   ├── blkk-render.command.json ← OpenClaw command spec
│   └── run.bat                ← wrapper OpenClaw/you can call
├── hot_folder/                ← drop assets here
├── output/                    ← render artifacts (gitignored)
└── logs/                      ← per-run JSON summaries (gitignored)
```

Additional SupaAgent/OpenClaw files:
- `SUPAAGENT.md` - general personal-agent integration map.
- `openclaw/gen-image.command.json` - OpenClaw command spec for ComfyUI stills.
- `openclaw/gen-video.command.json` - OpenClaw command spec for ComfyUI video.

## 8. Troubleshooting

- **"pipeline/config.json not found"** — you skipped §1; copy the example.
- **UE render produces nothing** — open the project in the GUI once and confirm
  the master level, `Seq_Default`, MRQ preset, `StagingAnchor`/`TourPoint` actors
  exist and the Python/MRQ/Panoramic Capture plugins are enabled.
- **360 capture empty** — the Panoramic Capture plugin CVars (`SP.*`) vary by
  version; verify the plugin is enabled and check the UE log for `SP.` warnings.
- **Tour shows broken images** — open `tours/<slug>/index.html` via a local
  server (`node serve-local.js`) not `file://`, so `fetch('tour.json')` works.
- **optimize-images.js fails** — `cd tools && npm install` once (needs `sharp`).
