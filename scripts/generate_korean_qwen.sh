#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-/home/ysw/Documents/anaconda3/envs/vocos_3.13/bin/python}"
TARGET_HOURS="${1:-10}"
OUTPUT_DIR="${2:-outputs/korean_duplex_${TARGET_HOURS}h}"
BASE_URL="${BASE_URL:-http://localhost:8000/v1}"
DIALOGUE_MODEL="${DIALOGUE_MODEL:-nvidia/Qwen3-8B-FP8}"
TTS_MODEL="${TTS_MODEL:-Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign}"
SEED="${SEED:-42}"

ASSISTANT_VOICE="${ASSISTANT_VOICE:-A Korean woman in her thirties with one consistent warm, clear and calm voice. Preserve exactly the same speaker identity, timbre, pitch range and speaking style in every dialogue. Speak naturally in Korean at a moderate conversational pace.}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  exit 2
fi

if ! [[ "$TARGET_HOURS" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || \
   ! "$PYTHON_BIN" -c "raise SystemExit(0 if float('$TARGET_HOURS') > 0 else 1)"; then
  echo "TARGET_HOURS must be a positive number, got: $TARGET_HOURS" >&2
  exit 2
fi

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export NUMBA_CACHE_DIR="${NUMBA_CACHE_DIR:-/tmp/duplexforge-numba}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"

if ! curl --fail --silent --show-error --max-time 3 "$BASE_URL/models" >/dev/null; then
  echo "Dialogue server is not reachable at $BASE_URL" >&2
  echo "Start it in another terminal with: scripts/start_trtllm_qwen3_8b.sh" >&2
  exit 3
fi

echo "Generating Korean duplex conversations until at least $TARGET_HOURS hours"
echo "Output: $PROJECT_DIR/$OUTPUT_DIR"
echo "Dialogue model: $DIALOGUE_MODEL"
echo "TTS model: $TTS_MODEL"
echo "Assistant VoiceDesign instruction is fixed; user personas vary by sample."

"$PYTHON_BIN" -m duplexforge generate \
  --goal "일상, 고객 상담, 예약, 주문, 여행, 교육, 일정 관리, 기기 문제 해결 등 다양한 도메인에서 사용자의 요청을 듣고 조건을 확인한 뒤 자연스럽게 해결하기" \
  --language ko \
  --dialogue-backend trtllm \
  --base-url "$BASE_URL" \
  --model "$DIALOGUE_MODEL" \
  --tts-backend qwen3 \
  --qwen-tts-model "$TTS_MODEL" \
  --qwen-tts-device cuda:0 \
  --qwen-tts-attention auto \
  --assistant-voice "$ASSISTANT_VOICE" \
  --target-hours "$TARGET_HOURS" \
  --seed "$SEED" \
  --discard-event-audio \
  --output "$OUTPUT_DIR"

"$PYTHON_BIN" -m duplexforge validate "$OUTPUT_DIR"
