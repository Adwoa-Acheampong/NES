# Scene Recipe — instructions for the terminal agent (Claude Code / Codex)

You are driving the **Unreal Engine 5.8 Editor over MCP** to build a Black Star
Legacy portfolio scene, then handing off to the deterministic render pipeline.
Follow this recipe exactly so the scene is compatible with
`pipeline/ue/render_pipeline.py`.

Paste this file's contents as context (or save it as a Claude Code / Codex
project rule, or an Agent Skill) so every build is consistent.

---

## Inputs you'll be given
- **project_name** — e.g. "Modern Villa" or "Havilah Estate" (house) / a car model.
- **category** — `architecture` or `automotive`.
- **brief** — free text: dimensions, rooms, style, materials, mood.

## Hard requirements (the render pipeline depends on these)
The render script looks for specifically **named/tagged actors**. You MUST create
them via MCP, or the headless render will produce nothing:

1. **One actor tagged `StagingAnchor`** — empty actor at the scene's focal origin.
   Imported/spawned hero geometry is placed here.
2. **One actor tagged `TourPoint` per 360° viewpoint** — place a camera or empty
   actor at eye height (~160 cm) at each spot a visitor should "stand". Give each
   a clear label (e.g. "Living Room", "Courtyard", "Driver Seat") — the label
   becomes the tour scene name automatically.
3. **A Level Sequence named `Seq_<slug>`** (slug = lowercase-hyphenated
   project_name) with a flythrough camera for the 4K cinematic. If you can't
   build a bespoke one, ensure `Seq_Default` exists.
4. Save everything (`save all`) before handing off — headless render opens the
   saved level, not your unsaved editor state.

> slug example: "Modern Villa" -> `modern-villa`.

## Build order
1. **Pick the master level** for the category and open it:
   - architecture -> `MasterLevel_Estate`
   - automotive   -> `MasterLevel_Showroom`
   If it doesn't exist yet, create it once (ground plane + sky + base lighting)
   and save under `/Game/Maps/`.
2. **Block out geometry** from the brief (walls, floor, ceiling, openings for
   architecture; a turntable plinth + backdrop for automotive). Use PCG or
   spawned static meshes. Keep real-world scale (centimeters).
3. **Materials** — apply materials that match the Black Star Legacy aesthetic
   (warm, premium, natural light). Avoid neon and "AI gradient" looks.
4. **Lighting** — art-direct for the category: soft daylight + warm key (~3000–
   3500K) for interiors; controlled studio rig for automotive.
5. **Place the required actors** (StagingAnchor, one TourPoint per viewpoint,
   the camera sequence) per the hard requirements above.
6. **Self-verify** via MCP: list actors and confirm exactly one `StagingAnchor`,
   ≥1 `TourPoint`, and `Seq_<slug>` (or `Seq_Default`) exist. Fix gaps.
7. **Save all.**

## Hand off to the render + publish pipeline
After saving, trigger the deterministic output (this runs headlessly and is
identical every time):

```bash
# from the website project root
python pipeline/run_pipeline.py --project-name "<project_name>" --category <category>
# add --flagship to also build a Pixel Streaming package
```

`run_pipeline.py` will: render the cinematic + 360° panoramas, build the
Pannellum tour into `tours/<slug>/`, stage media into `assets/`, and publish.
Relay the final `PIPELINE_SUMMARY_JSON` line back to the requester.

## Guardrails
- The MCP grants full editor control — make only the changes the brief implies.
- Don't delete unrelated assets/levels.
- If a TourPoint clips into geometry, nudge it to open floor space at eye height.
- Keep panorama count reasonable (3–6 per scene) so renders stay fast.
