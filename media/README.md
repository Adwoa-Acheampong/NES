# Tier 1 & 2 — Local AI media (images + Wan video) via ComfyUI

The lightweight track. No Unreal Engine — runs on your GPU through one local
**ComfyUI** server that both the image and video scripts call over HTTP.

```
agent (Claude Code / Codex via OpenClaw)
   ├─ Tier 1  python pipeline/media/gen_image.py   → ComfyUI (Flux/SDXL) → assets/<name>.png
   └─ Tier 2  python pipeline/media/gen_video.py   → ComfyUI (Wan)       → assets/video/<name>.mp4
                                                      → optimize-images.js → publish.py
```

Use Unreal (Tier 3) only for real 3D: walkthroughs, 360° tours, interactive.

---

## VRAM / disk matrix (pick variants to match your GPU)
Local generation is the heavy part. Confirm your GPU's VRAM, then choose:

| Your VRAM | Tier 1 image | Tier 2 Wan video | Notes |
|-----------|--------------|------------------|-------|
| 6–8 GB    | SDXL, or Flux **GGUF Q4** | **Wan 2.1/2.2 1.3B**, short clips (≈2–3 s, 480p) | use quantized models; lower steps |
| 10–12 GB  | Flux GGUF Q5/Q8 | Wan 1.3B comfortably; 14B GGUF slow | sweet spot for a laptop 4070/4080 |
| 16–24 GB  | Flux dev (fp8/full) | Wan **14B** (720p), longer clips | desktop 4090 / pro cards |
| < 6 GB / no NVIDIA | use a cloud API instead | cloud (fal/Replicate) | local not practical; tell me and I'll switch the scripts to API |

Disk: model files are large — Flux dev ≈ 12–24 GB, Wan 14B ≈ 30+ GB, SDXL ≈ 7 GB.
(You just cleared space; budget for this.)

---

## One-time install
1. **ComfyUI** (portable Windows build is easiest): download, unzip, run
   `run_nvidia_gpu.bat`. It serves `http://127.0.0.1:8188`.
2. **Models** → into `ComfyUI/models/`:
   - Image: Flux (`unet/`, `clip/`, `vae/`) or an SDXL checkpoint (`checkpoints/`).
   - Video: Wan model + text encoder + VAE (per the Wan ComfyUI guide), into the
     matching `models/` subfolders.
   - On 6–12 GB VRAM use **GGUF quantized** variants + the ComfyUI-GGUF nodes.
3. Build a working graph for each (image, Wan t2v, Wan i2v), test in the UI, then
   **Save (API Format)** into `pipeline/media/workflows/` (see that folder's README).
4. Map the node ids in `pipeline/config.json → media` (template in the workflows README).
5. Python deps for the clients are stdlib-only — nothing extra to install.

✅ Check: `python pipeline/media/gen_image.py --name test --prompt "a red cube on white"`
produces `assets/test.png`.

---

## Usage
```bash
# Tier 1 — hero still
python pipeline/media/gen_image.py --name estate-hero \
  --prompt "warm modern Ghanaian estate at golden hour, editorial, photoreal"

# Tier 2 — animate that still into a hero loop
python pipeline/media/gen_video.py --name estate-loop --image assets/estate-hero.png \
  --prompt "slow cinematic push-in, gentle warm light"
```
Both print a `*_RESULT_JSON=` line OpenClaw relays. Output flows through the same
`publish.py` as the Unreal tier, so deploying is identical.

## How the agents use this
Per `agent/AGENTS.md`, OpenClaw routes "make a hero image / background" to Tier 1
and "short loop / animate this" to Tier 2 — reserving Unreal for true 3D. The
agents call these scripts; ComfyUI does the GPU work.
