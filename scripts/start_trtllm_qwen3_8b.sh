#!/usr/bin/env bash
set -euo pipefail

model_id="${TRTLLM_MODEL:-nvidia/Qwen3-8B-FP8}"
server_host="${TRTLLM_HOST:-0.0.0.0}"
server_port="${TRTLLM_PORT:-8000}"
config_path="${TRTLLM_CONFIG:-configs/trtllm_qwen3_8b.yaml}"

exec trtllm-serve "${model_id}" \
  --host "${server_host}" \
  --port "${server_port}" \
  --config "${config_path}"

