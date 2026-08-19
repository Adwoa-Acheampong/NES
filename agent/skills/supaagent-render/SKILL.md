---
name: supaagent-render
description: Render a Black Star Legacy 3D portfolio asset in Unreal Engine 5.8 and publish a 360 virtual tour.
author: NES
version: 1.0.0
---

# SupaAgent Render Skill

You are an expert pipeline manager for the Black Star Legacy system. When the user asks you to render, build, or publish a 3D asset or virtual tour, you should use this skill.

## Instructions
1. Your goal is to execute the `run_pipeline.py` script located at `C:\Users\lenovo\OneDrive\Desktop\NES\NES\run_pipeline.py`.
2. Extract the `project_name` from the user's request.
3. Determine if a `category` (architecture or automotive), `asset_path`, or `flagship` flag is required based on the user's input.
4. Run the python script using your terminal/command execution tool.
   Example Command:
   ```cmd
   python "C:\Users\lenovo\OneDrive\Desktop\NES\NES\run_pipeline.py" --project-name "{project_name}"
   ```
5. Wait for the command to finish. Look for the `PIPELINE_SUMMARY_JSON=` output in the standard output.
6. Relay a friendly summary of the JSON result back to the user over the chat.

## Constraints
- Do NOT use OpenClaw or third-party gateways. Run this script directly on the host machine.
- If the UE render takes a long time, inform the user that the process has started and report back when finished.
