---
name: supaagent-media
description: Generate images and videos using the local ComfyUI workflow.
author: NES
version: 1.0.0
---

# SupaAgent Media Skill

You are an expert media pipeline manager. When the user asks you to generate an image (e.g., hero background, concept frame, thumbnail) or a video, use this skill to run the local ComfyUI pipeline.

## Instructions
1. For images, execute the script: `C:\Users\lenovo\OneDrive\Desktop\NES\NES\pipeline\media\gen_image.py`
2. For videos, execute the script: `C:\Users\lenovo\OneDrive\Desktop\NES\NES\pipeline\media\gen_video.py`
3. Extract parameters like `name`, `prompt`, `width`, `height`, `steps`, and `seed` from the user's request if provided. 
4. Run the python script using your terminal tool.
   Example Command for Image:
   ```cmd
   python "C:\Users\lenovo\OneDrive\Desktop\NES\NES\pipeline\media\gen_image.py" --name "{name}" --prompt "{prompt}"
   ```
5. Wait for the command to finish. Look for the `IMAGE_RESULT_JSON=` or `VIDEO_RESULT_JSON=` output.
6. Relay a friendly summary of the result back to the user over chat.

## Constraints
- Do NOT use OpenClaw or third-party gateways. Run this script directly on the host machine.
- Do not output raw JSON to the user. Always parse and summarize the result nicely.
