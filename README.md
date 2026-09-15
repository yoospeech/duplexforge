# DuplexForge

목적 한 줄에서 한국어·영어·스페인어·프랑스어 full-duplex 대화 학습용 **음성·텍스트 페어**를 생성하는 MVP다.

```text
목적
 └─ 대화 및 행동 생성
     ├─ normal QA
     ├─ listener backchannel
     ├─ semantic interruption
     └─ mid-utterance pause
          ↓
       화자별 TTS
          ↓
 user.wav + assistant.wav + mixed.wav + timestamp metadata.json
```

이 프로젝트에서 `turn`은 단순한 배열 순서가 아니라 시간축의 `event`다. 한 event는 앞 event의 시작 또는 끝을 기준으로 배치되며, 음수 offset으로 실제 겹침을 표현한다.

## 빠른 시작

Python 3.10 이상만 있으면 dependency-free 디버그 오디오로 전체 파이프라인을 실행할 수 있다.

```bash
python -m duplexforge generate \
  --goal "카페에서 원하는 음료를 정확히 주문하기" \
  --dialogue-backend template \
  --count 4 \
  --output outputs/cafe
```

패키지를 설치하지 않은 소스 체크아웃에서는 다음과 같이 실행한다.

```bash
PYTHONPATH=src python -m duplexforge generate \
  --goal "카페에서 원하는 음료를 정확히 주문하기" \
  --dialogue-backend template \
  --count 4 \
  --output outputs/cafe
```

`template + tone`은 네트워크와 모델 없이 구조, 타임스탬프, overlap을 검증하기 위한 명시적 디버그 모드다. 실제 기본 대화 백엔드는 `trtllm`, 기본 음성 백엔드는 PyTorch 기반 `qwen3`이다. `tone` 오디오는 사람 음성이 아니므로 학습 데이터로 사용하면 안 된다.

## Qwen3-TTS + PyTorch (기본)

Python 3.12 가상환경에서 공식 패키지를 설치한다.

```bash
python -m pip install -e '.[qwen3-tts]'
```

첫 실행 시 `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign` 체크포인트가 내려받아진다.

```bash
duplexforge generate \
  --goal "고객의 인터넷 연결 문제를 단계적으로 진단하기" \
  --language ko \
  --dialogue-backend template \
  --tts-backend qwen3 \
  --qwen-tts-device cuda:0 \
  --count 1 \
  --output outputs/qwen3_tts_test
```

FlashAttention을 별도로 설치했다면 `--qwen-tts-attention flash_attention_2`를 사용할 수 있다. 기본 `auto`는 추가 컴파일 없이 실행 가능한 attention 구현을 선택한다.

## Qwen3-TTS + TensorRT Edge-LLM

선택적으로 같은 모델을 TensorRT Edge-LLM으로 실행할 수 있다. 각 샘플에 서로 다른 사용자·어시스턴트 화자 설명을 seed 기반으로 만들며, 한 대화의 모든 event를 단일 Edge-LLM 배치로 합성한다. 한국어·영어·스페인어·프랑스어를 지원한다.

먼저 [TensorRT Edge-LLM](https://github.com/NVIDIA/TensorRT-Edge-LLM)의 플랫폼별 설치를 마치고 모델 체크포인트를 준비한다. 최신 ONNX-less builder 예시는 다음과 같다.

```bash
TensorRT-Edge-LLM/.venv/bin/tensorrt-edgellm-build \
  --model-dir models/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --engine-dir engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --plugin-path TensorRT-Edge-LLM/build/libNvInfer_edgellm_plugin.so \
  --max-input-len 2048 \
  --max-kv-cache-capacity 4096 \
  --max-batch-size 8
```

`--max-batch-size`는 한 대화에 들어갈 최대 event 수 이상이어야 한다. 엔진 생성 후 DuplexForge를 실행한다.

```bash
PYTHONPATH=src python -m duplexforge generate \
  --goal "고객의 인터넷 연결 문제를 단계적으로 진단하기" \
  --language ko \
  --dialogue-backend trtllm \
  --tts-backend qwen3-edgellm \
  --edgellm-binary TensorRT-Edge-LLM/build/examples/omni/qwen3_tts_inference \
  --edgellm-engine-dir engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --qwen-tts-checkpoint models/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --count 20 \
  --output outputs/network_support
```

Edge-LLM 런타임은 `language`와 `instruct`를 요청별로 받는다. DuplexForge는 이 필드에 언어와 randomized VoiceDesign persona를 넣고, 생성에 사용된 설명을 `metadata.json`에 보존한다. 배포 환경에 맞게 `EDGELLM_PLUGIN_PATH`와 동적 라이브러리 경로도 TensorRT Edge-LLM 설치 지침에 따라 설정해야 한다.

## 실제 한국어 음성 생성

간편한 프로토타입은 `edge-tts`와 시스템의 `ffmpeg`를 사용한다.

```bash
python -m pip install -e '.[edge]'

duplexforge generate \
  --goal "병원 진료 예약 일정을 조율하기" \
  --language ko \
  --dialogue-backend template \
  --tts-backend edge \
  --count 8 \
  --output outputs/hospital
```

지원 언어별 Edge TTS 화자 풀은 다음과 같다. `--user-voice`, `--assistant-voice`로 개별 변경할 수 있다.

| 코드 | 언어 | 화자 수 | 지역 |
|---|---|---:|---|
| `ko` | 한국어 | 3 | 한국 |
| `en` | 영어 | 16 | 미국·영국·호주·인도·캐나다·아일랜드 |
| `es` | 스페인어 | 15 | 스페인·멕시코·아르헨티나·콜롬비아·칠레·페루·미국 |
| `fr` | 프랑스어 | 12 | 프랑스·캐나다·벨기에·스위스 |

Edge TTS는 외부 서비스에 접근하므로 데이터 이용 조건을 확인해야 한다.

기본 `--voice-strategy random`은 단순 추첨이 아니라 **coverage-balanced random**이다. seed에 따라 화자 순서를 섞되, 화자 풀 크기만큼의 샘플마다 모든 화자가 사용자 역할과 어시스턴트 역할에 각각 한 번씩 등장한다. 같은 샘플의 두 역할에는 동일 화자를 배정하지 않는다. 같은 `--seed`를 주면 조합도 재현된다.

```bash
# 실제 내장 화자 풀 확인
duplexforge voices
duplexforge voices --language es

# 샘플마다 coverage-balanced random 화자 적용(기본값)
duplexforge generate --language en --goal "book a flight" \
  --tts-backend edge --voice-strategy random --count 32 --output outputs/en_flight

# 두 화자를 명시적으로 고정할 때만 사용
duplexforge generate --language ko --goal "식당 예약하기" \
  --tts-backend edge --voice-strategy fixed --count 10 --output outputs/ko_fixed
```

언어별 생성 예시:

```bash
duplexforge generate --language en --goal "book a hotel room" \
  --tts-backend edge --count 4 --output outputs/en_hotel

duplexforge generate --language es --goal "reservar una mesa" \
  --tts-backend edge --count 4 --output outputs/es_restaurant

duplexforge generate --language fr --goal "planifier un voyage" \
  --tts-backend edge --count 4 --output outputs/fr_travel
```

## LLM으로 목적 맞춤 대화 생성

권장 기본 구성은 `nvidia/Qwen3-8B-FP8`을 TensorRT-LLM으로 서빙하는 방식이다. Qwen3의 non-thinking 모드로 대화만 생성하며, DuplexForge는 `/v1/chat/completions`에 연결한다.

```bash
# 터미널 1: TensorRT-LLM 서버 시작
scripts/start_trtllm_qwen3_8b.sh

# 터미널 2: 대화와 음성 생성
.venv/bin/duplexforge generate \
  --goal "고객의 인터넷 연결 문제를 단계적으로 진단하기" \
  --language ko \
  --dialogue-backend trtllm \
  --base-url http://localhost:8000/v1 \
  --model nvidia/Qwen3-8B-FP8 \
  --tts-backend edge \
  --count 20 \
  --output outputs/network_support
```

서버 설정은 `configs/trtllm_qwen3_8b.yaml`에 있다. GPU 메모리가 부족하면 `max_batch_size`와 `max_num_tokens`를 낮춘다. 직접 명령을 실행할 수도 있다.

```bash
trtllm-serve nvidia/Qwen3-8B-FP8 \
  --host 0.0.0.0 --port 8000 \
  --config configs/trtllm_qwen3_8b.yaml
```

다른 OpenAI-compatible 서버를 사용할 때는 `--dialogue-backend openai`와 해당 `--base-url`, `--model`, API key를 지정하면 된다.

## 출력 구조

```text
outputs/cafe/
├── manifest.jsonl
├── run_config.json
└── sample_000000/
    ├── user.wav
    ├── assistant.wav
    ├── mixed.wav
    ├── metadata.json
    ├── transcript.txt
    └── events/
        ├── e1_user.wav
        └── e2_assistant.wav
```

`metadata.json`의 핵심 형태:

```json
{
  "goal": "카페에서 음료 주문하기",
  "scenario": "semantic_interruption",
  "audio": {
    "user": "user.wav",
    "assistant": "assistant.wav",
    "mixed": "mixed.wav"
  },
  "events": [
    {
      "speaker": "user",
      "text": "잠깐만요. 아이스로 바꿀게요.",
      "event_type": "interruption",
      "start_ms": 3210,
      "end_ms": 4790,
      "metadata": {"expected_action": "stop_and_listen"}
    }
  ]
}
```

전체 명세는 [docs/metadata.schema.json](docs/metadata.schema.json)에 있다. 샘플을 사람이 빠르게 확인하려면:

```bash
duplexforge inspect outputs/cafe/sample_000000/metadata.json
```

대량 생성 후 WAV 포맷, 트랙 길이, event 범위, 실제 cross-speaker overlap을 검사하려면:

```bash
duplexforge validate outputs/cafe
```

## 패턴 선택

```bash
duplexforge generate \
  --goal "상품 환불 요청 처리하기" \
  --patterns interruption,backchannel \
  --count 100 \
  --output outputs/refund
```

- `normal`: 순차 QA
- `backchannel`: 시스템 답변 중 사용자의 짧은 맞장구, 기대 행동은 계속 말하기
- `interruption`: 의미 있는 끼어들기, 기대 행동은 멈추고 듣기
- `pause`: 사용자 문장 중 긴 멈춤, 기대 행동은 계속 듣기

## 테스트

```bash
python -m unittest discover -s tests -v
```

현재 MVP는 데이터 생성 및 렌더링에 집중한다. 다음 단계는 로컬 한국어 TTS 어댑터, word-level alignment, VAP/Easy-Turn 기반 품질 필터, 배경 소음과 RIR augmentation이다. 관련 공개 프로젝트와 라이선스 메모는 [docs/references.md](docs/references.md)에 정리했다.
