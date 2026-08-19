---
title: Deployment
description: Deploy NES in production environments
---

# Deployment

NES supports multiple deployment strategies for different environments
and scales.

## Docker

The recommended way to deploy NES in production. Multi-stage builds
with CPU and GPU (NVIDIA CUDA, AMD ROCm) variants.

[:octicons-arrow-right-24: Docker deployment](docker.md)

## systemd (Linux)

Run NES as a managed system service on Linux servers.

[:octicons-arrow-right-24: systemd setup](systemd.md)

## launchd (macOS)

Register NES as a launch agent on macOS.

[:octicons-arrow-right-24: launchd setup](launchd.md)

## API Server

Run NES as an OpenAI-compatible HTTP server via `nes serve`.

[:octicons-arrow-right-24: API server guide](api-server.md)
