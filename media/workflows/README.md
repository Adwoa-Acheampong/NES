# ComfyUI API workflows

`gen_image.py` and `gen_video.py` inject prompts/params into **API-format**
workflow JSON files that live here. You export these once from ComfyUI:

1. In ComfyUI: **Settings → enable "Dev mode options"**.
2. Build (or load) a working graph for your model, test it once in the UI.
3. **Save (API Format)** → save into this folder with the expected name.

Expected files (names referenced by config.json → media):
- `flux_image.api.json`   — Tier 1 stills (Flux or SDXL)
- `wan_t2v.api.json`      — Tier 2 text-to-video (Wan)
- `wan_i2v.api.json`      — Tier 2 image-to-video (Wan)

## Wiring node ids
After exporting, open the JSON and note the node ids for the inputs we drive,
then map them in `pipeline/config.json → media.image.nodes` / `media.video.nodes`.
Example (ids will differ in your export):

```json
"media": {
  "image": {
    "workflow": "flux_image.api.json",
    "nodes": {
      "positive": { "node": "6",  "field": "text" },
      "negative": { "node": "7",  "field": "text" },
      "width":    { "node": "5",  "field": "width" },
      "height":   { "node": "5",  "field": "height" },
      "steps":    { "node": "3",  "field": "steps" },
      "seed":     { "node": "3",  "field": "seed" }
    }
  },
  "video": {
    "workflow": "wan_i2v.api.json",
    "nodes": {
      "positive": { "node": "6",  "field": "text" },
      "image":    { "node": "52", "field": "image" },
      "frames":   { "node": "40", "field": "length" },
      "fps":      { "node": "41", "field": "fps" },
      "seed":     { "node": "3",  "field": "seed" }
    }
  }
}
```

These `.api.json` files are gitignored by default (they reference local model
names). Commit them only if you want them versioned.
