# DuplexForge

DuplexForge turns a one-line objective into multilingual **audio-text pairs** for training full-duplex spoken dialogue systems. It supports Korean, English, Spanish, and French.

```text
Objective
 └─ Dialogue and behavior generation
     ├─ normal QA
     ├─ listener backchannel
     ├─ semantic interruption
     └─ mid-utterance pause
          ↓
       Per-speaker TTS
          ↓
<<<<<<< HEAD
 user.wav + assistant.wav + mixed.wav + Moshi stereo WAV + timestamps
=======
 user.wav + assistant.wav + mixed.wav + timestamp metadata.json
>>>>>>> origin/main
```

A `turn` in DuplexForge is a timeline event, not merely an item in an ordered array. Each event is positioned relative to the start or end of an earlier event. Negative offsets create real cross-speaker overlap.

## Features

- Goal-conditioned dialogue generation with Qwen3-8B through TensorRT-LLM
- Natural speech with Qwen3-TTS VoiceDesign through PyTorch
- Optional Qwen3-TTS acceleration through NVIDIA TensorRT Edge-LLM
- Korean, English, Spanish, and French generation
- Reproducible, randomized speaker personas
- Normal turns, backchannels, interruptions, pauses, and resumptions
- Separate user and assistant tracks plus a mixed full-duplex track
- Timestamped JSON metadata, transcripts, and JSONL manifests
<<<<<<< HEAD
- Current `moshi-finetune` export: assistant-left/user-right stereo WAV,
  adjacent alignment JSON, and `moshi.jsonl`
=======
>>>>>>> origin/main
- Dataset validation for audio format, event timing, and speaker overlap

## Quick start

Python 3.10 or newer is sufficient for the dependency-free debug pipeline.

```bash
python -m duplexforge generate \
  --goal "Order the desired drink at a cafe" \
  --dialogue-backend template \
  --tts-backend tone \
  --count 4 \
  --output outputs/cafe
```

From a source checkout without installing the package:

```bash
PYTHONPATH=src python -m duplexforge generate \
  --goal "Order the desired drink at a cafe" \
  --dialogue-backend template \
  --tts-backend tone \
  --count 4 \
  --output outputs/cafe
```

`template + tone` is an explicit debug mode for testing structure, timestamps, and overlaps without a network connection or model. Tone audio is not human speech and must not be used as training data. The production defaults are `trtllm` for dialogue generation and the PyTorch-based `qwen3` backend for speech.

## Qwen3-TTS with PyTorch (default)

The default speech model is `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`. The official Qwen package recommends a Python 3.12 environment.

```bash
python -m pip install -e '.[qwen3-tts]'
```

The model checkpoint is downloaded automatically on the first run.

```bash
duplexforge generate \
  --goal "Diagnose a customer's internet connection problem step by step" \
  --language ko \
  --dialogue-backend template \
  --tts-backend qwen3 \
  --qwen-tts-device cuda:0 \
  --count 1 \
  --output outputs/qwen3_tts_test
```

If FlashAttention is installed and supported by the GPU, pass `--qwen-tts-attention flash_attention_2`. The default `auto` mode works without compiling FlashAttention.

<<<<<<< HEAD
For Qwen3-TTS, DuplexForge creates a different reproducible user persona for
each sample while keeping one assistant VoiceDesign identity fixed across the
entire dataset run. Pass `--assistant-voice "..."` to define that fixed target
voice explicitly. Descriptions and model identifiers are stored in
`metadata.json` for reproducibility.
=======
For every sample, DuplexForge creates distinct user and assistant VoiceDesign descriptions from the selected seed. The descriptions and model identifier are stored in `metadata.json` for reproducibility.
>>>>>>> origin/main

## Qwen3-TTS with TensorRT Edge-LLM

The same model can optionally run through [NVIDIA TensorRT Edge-LLM](https://github.com/NVIDIA/TensorRT-Edge-LLM). DuplexForge sends all events in one dialogue as a single Edge-LLM batch and supplies per-request `language` and `instruct` fields.

Install TensorRT Edge-LLM for the target platform, download the model checkpoint, and build the engines:

```bash
TensorRT-Edge-LLM/.venv/bin/tensorrt-edgellm-build \
  --model-dir models/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --engine-dir engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --plugin-path TensorRT-Edge-LLM/build/libNvInfer_edgellm_plugin.so \
  --max-input-len 2048 \
  --max-kv-cache-capacity 4096 \
  --max-batch-size 8
```

Set `--max-batch-size` to at least the maximum number of events in one dialogue. Then run:

```bash
PYTHONPATH=src python -m duplexforge generate \
  --goal "Diagnose a customer's internet connection problem step by step" \
  --language ko \
  --dialogue-backend trtllm \
  --tts-backend qwen3-edgellm \
  --edgellm-binary TensorRT-Edge-LLM/build/examples/omni/qwen3_tts_inference \
  --edgellm-engine-dir engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --qwen-tts-checkpoint models/Qwen3-TTS-12Hz-1.7B-VoiceDesign \
  --count 20 \
  --output outputs/network_support
```

Configure `EDGELLM_PLUGIN_PATH` and the dynamic-library search path according to the TensorRT Edge-LLM installation guide for the target platform.

## Edge TTS prototype backend

For a lightweight prototype, install `edge-tts` and ensure `ffmpeg` is available:

```bash
python -m pip install -e '.[edge]'

duplexforge generate \
  --goal "Coordinate a medical appointment" \
  --language ko \
  --dialogue-backend template \
  --tts-backend edge \
  --count 8 \
  --output outputs/hospital
```

The built-in Edge TTS pools contain:

| Code | Language | Voices | Regions |
|---|---|---:|---|
| `ko` | Korean | 3 | South Korea |
| `en` | English | 16 | US, UK, Australia, India, Canada, Ireland |
| `es` | Spanish | 15 | Spain, Mexico, Argentina, Colombia, Chile, Peru, US |
| `fr` | French | 12 | France, Canada, Belgium, Switzerland |

Edge TTS accesses an external service. Review its terms before using generated audio in a dataset.

The default `--voice-strategy random` is coverage-balanced rather than independent random sampling. Every voice appears once in each role during an epoch equal to the pool size. The two roles never receive the same voice in one sample, and the same seed reproduces the assignments.

```bash
# List the built-in voice pools.
duplexforge voices
duplexforge voices --language es

# Apply coverage-balanced randomized voices.
duplexforge generate --language en --goal "Book a flight" \
  --dialogue-backend template --tts-backend edge \
  --voice-strategy random --count 32 --output outputs/en_flight

# Use fixed voices instead.
duplexforge generate --language ko --goal "Reserve a restaurant table" \
  --dialogue-backend template --tts-backend edge \
  --voice-strategy fixed --count 10 --output outputs/ko_fixed
```

Additional language examples:

```bash
duplexforge generate --language en --goal "Book a hotel room" \
  --dialogue-backend template --tts-backend edge \
  --count 4 --output outputs/en_hotel

duplexforge generate --language es --goal "Reservar una mesa" \
  --dialogue-backend template --tts-backend edge \
  --count 4 --output outputs/es_restaurant

duplexforge generate --language fr --goal "Planifier un voyage" \
  --dialogue-backend template --tts-backend edge \
  --count 4 --output outputs/fr_travel
```

## Goal-conditioned dialogue generation

The recommended dialogue backend serves `nvidia/Qwen3-8B-FP8` with TensorRT-LLM. DuplexForge requests non-thinking output through the OpenAI-compatible `/v1/chat/completions` endpoint.

```bash
# Terminal 1: start TensorRT-LLM.
scripts/start_trtllm_qwen3_8b.sh

# Terminal 2: generate dialogue and speech.
.venv/bin/duplexforge generate \
  --goal "Diagnose a customer's internet connection problem step by step" \
  --language ko \
  --dialogue-backend trtllm \
  --base-url http://localhost:8000/v1 \
  --model nvidia/Qwen3-8B-FP8 \
  --tts-backend qwen3 \
  --count 20 \
  --output outputs/network_support
```

The server configuration is in `configs/trtllm_qwen3_8b.yaml`. Reduce `max_batch_size` and `max_num_tokens` if GPU memory is limited. The equivalent direct command is:

```bash
trtllm-serve nvidia/Qwen3-8B-FP8 \
  --host 0.0.0.0 --port 8000 \
  --config configs/trtllm_qwen3_8b.yaml
```

For another OpenAI-compatible server, use `--dialogue-backend openai` with its base URL, model identifier, and API key.

## Output layout

```text
outputs/cafe/
├── manifest.jsonl
├── run_config.json
└── sample_000000/
    ├── user.wav
    ├── assistant.wav
    ├── mixed.wav
<<<<<<< HEAD
    ├── moshi.wav
    ├── moshi.json
=======
>>>>>>> origin/main
    ├── metadata.json
    ├── transcript.txt
    └── events/
        ├── e1_user.wav
        └── e2_assistant.wav
```

Core `metadata.json` structure:

```json
{
  "goal": "Order a drink at a cafe",
  "scenario": "semantic_interruption",
  "audio": {
    "user": "user.wav",
    "assistant": "assistant.wav",
    "mixed": "mixed.wav"
  },
  "events": [
    {
      "speaker": "user",
      "text": "Wait, please make that iced.",
      "event_type": "interruption",
      "start_ms": 3210,
      "end_ms": 4790,
      "metadata": {"expected_action": "stop_and_listen"}
    }
  ]
}
```

See `docs/metadata.schema.json` for the complete schema. Inspect one sample with:

```bash
duplexforge inspect outputs/cafe/sample_000000/metadata.json
```

Validate WAV formats, track lengths, event ranges, and cross-speaker overlap after a larger run:

```bash
duplexforge validate outputs/cafe
```

<<<<<<< HEAD
The validator also prints total hours, turn duration, response latency, overlap
ratio, and interruption/barge-in/backchannel counts. `moshi.jsonl` is directly
shaped for the current `moshi-finetune` loader. Its paths are absolute so the
loader does not depend on the training process working directory. The Moshi
channel convention is fixed by upstream: left/channel 0 is assistant (Moshi),
right/channel 1 is user.

For the conservative Korean LoRA recipe and known tokenizer/alignment caveats,
see `configs/korean_moshi_finetune.yaml` and
`docs/KOREAN_MOSHI_FINETUNING.md`.

=======
>>>>>>> origin/main
## Dialogue patterns

```bash
duplexforge generate \
  --goal "Handle a product refund request" \
  --patterns interruption,backchannel \
  --count 100 \
  --output outputs/refund
```

- `normal`: sequential question and answer
- `backchannel`: a short listener response while the other speaker continues
- `interruption`: a semantic interruption that should make the other speaker stop
<<<<<<< HEAD
- `overlap`: both waveforms continue during cooperative overlap
- `barge_in`: user overlap followed by assistant truncation after stop latency
- `hesitation`: a mid-utterance false end during which the listener keeps waiting
=======
- `pause`: a long mid-utterance pause during which the listener should keep waiting
>>>>>>> origin/main

## Tests

```bash
python -m unittest discover -s tests -v
```

<<<<<<< HEAD
The current exporter approximates word boundaries inside each synthesized
utterance because the integrated TTS APIs do not return alignments. Production
training should add forced alignment or use backend-native word timestamps.
Planned improvements include VAP/Easy-Turn quality filtering, room impulse
response and background-noise augmentation, and larger licensed reference-voice
banks. See `docs/references.md` for open-source projects and license notes.
=======
The current MVP focuses on data generation and timeline rendering. Planned improvements include word-level alignment, VAP/Easy-Turn quality filtering, room impulse response and background-noise augmentation, and larger licensed reference-voice banks. See `docs/references.md` for open-source projects and license notes.
>>>>>>> origin/main
