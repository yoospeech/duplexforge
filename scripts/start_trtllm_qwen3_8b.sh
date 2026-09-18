#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
model_id="${TRTLLM_MODEL:-nvidia/Qwen3-8B-FP8}"
server_host="${TRTLLM_HOST:-0.0.0.0}"
server_port="${TRTLLM_PORT:-8000}"
config_path="${TRTLLM_CONFIG:-configs/trtllm_qwen3_8b.yaml}"
runtime="${TRTLLM_RUNTIME:-auto}"
image="${TRTLLM_IMAGE:-nvcr.io/nvidia/tensorrt-llm/release:1.3.0rc13}"

if [[ "${runtime}" != "docker" ]] && command -v trtllm-serve >/dev/null 2>&1; then
  exec trtllm-serve "${model_id}" \
    --host "${server_host}" \
    --port "${server_port}" \
    --config "${config_path}"
fi

if [[ "${runtime}" == "local" ]]; then
  echo "error: TRTLLM_RUNTIME=local 이지만 trtllm-serve를 찾을 수 없습니다." >&2
  exit 127
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "error: trtllm-serve와 docker를 모두 찾을 수 없습니다." >&2
  exit 127
fi

if ! docker info >/dev/null 2>&1; then
  echo "error: Docker daemon에 접근할 수 없습니다." >&2
  echo "현재 계정의 Docker 권한을 확인한 뒤 다시 로그인하거나, 이 스크립트를 sudo로 실행하세요." >&2
  exit 1
fi

if [[ "${config_path}" = /* ]]; then
  echo "error: Docker 실행 시 TRTLLM_CONFIG는 프로젝트 내부의 상대 경로여야 합니다." >&2
  exit 2
fi

hf_cache="${HF_HOME:-${HOME}/.cache/huggingface}"
mkdir -p "${hf_cache}"

echo "TensorRT-LLM container: ${image}"
echo "Model: ${model_id}"
echo "Endpoint: http://${server_host}:${server_port}/v1"

exec docker run --rm \
  --gpus all \
  --ipc host \
  --network host \
  --ulimit memlock=-1 \
  --ulimit stack=67108864 \
  -e "HF_TOKEN=${HF_TOKEN:-}" \
  -e HF_HOME=/root/.cache/huggingface \
  -v "${hf_cache}:/root/.cache/huggingface" \
  -v "${project_dir}:/workspace/duplexforge:ro" \
  -w /workspace/duplexforge \
  "${image}" \
  trtllm-serve "${model_id}" \
    --host "${server_host}" \
    --port "${server_port}" \
    --config "${config_path}"
