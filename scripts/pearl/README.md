# Pearl Tooling

This directory holds standalone Pearl ecosystem utilities that are useful during
model enablement or validation but are not part of the NES runtime.

- `model_converter.py` creates experimental Pearl-compatible staging
  checkpoints from raw Hugging Face safetensors models.

Keep user-facing mining commands in `src/nes/cli/` and runtime provider
code in `src/nes/mining/`. Scripts here should be explicit operational
tools that developers run manually.
