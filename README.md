# DuplexForge

DuplexForge generates synthetic full-duplex spoken-dialogue data.  The original
project scope is goal-conditioned dialogue generation, per-speaker TTS, and
timeline rendering; the current development focus adds a **Korean data path for
Moshi fine-tuning experiments**.

```text
Goal and dialogue domain
        │
        ├─ dialogue events: turns, overlap, backchannel, interruption
        ├─ per-speaker TTS
        └─ full-duplex timeline renderer
                         │
      user.wav / assistant.wav / mixed.wav
                         │
              Moshi stereo export + alignment JSON
```

## Existing capabilities

- Goal-conditioned dialogue generation through a template backend or an
  OpenAI-compatible server
- Normal turns, overlap, interruption, barge-in, backchannel, and hesitation
- Separate user and assistant tracks, plus a mixed full-duplex track
- Event timestamps, transcript, metadata, and JSONL manifests
- Korean, English, Spanish, and French dialogue support
- Dataset validation for audio layout and event timing

The dependency-free `template + tone` mode is only for renderer and format
smoke tests.  Tone output is not usable as speech training data.

## Korean Moshi additions

The current branch adds the artifacts consumed by the checked
[`moshi-finetune`](https://github.com/kyutai-labs/moshi-finetune) loader:

- `moshi.wav`: stereo WAV, **left/channel 0 = assistant (Moshi)** and
  **right/channel 1 = user**
- `moshi.json`: adjacent alignment JSON
- `moshi.jsonl`: `{"path": "...", "duration": ...}` rows for the trainer
- `configs/korean_moshi_finetune.yaml`: conservative Korean LoRA recipe
- `configs/moshi_smoke.yaml`: small end-to-end integration check
- `docs/KOREAN_MOSHI_FINETUNING.md`: data contract and tokenizer caveats
- `docs/MOSHI_ENVIRONMENT.md`: checked NVIDIA GB10 environment notes

The exporter currently distributes words uniformly across each synthesized
utterance because the integrated TTS APIs do not provide word timestamps.
These are useful for plumbing validation, but forced alignment or native TTS
timestamps should replace them before production training.

## Recommended Korean generation path

The intended stack for the current experiment is:

- **Qwen3-8B via TensorRT-LLM**: dialogue text and event structure
- **Qwen3-TTS VoiceDesign**: Korean user and assistant audio
- **DuplexForge renderer**: timing, overlap, dual tracks, and Moshi export
- **moshi-finetune**: downstream LoRA training

For each run, the assistant VoiceDesign instruction is fixed and user persona
instructions vary per sample.  VoiceDesign is instruction-based, so this aims
for a consistent assistant voice but does not guarantee a perfectly identical
speaker identity across every generated utterance.

## Quick start: 10-hour Korean dataset

Prerequisites: a CUDA PyTorch/Qwen-TTS environment, Docker GPU access for
TensorRT-LLM, and sufficient disk space for models and WAV output.

```bash
cd ~/Documents/eee/fullduplex_data_gen
conda activate vocos_3.13
python -m pip install -e '.[qwen3-tts]'
```

Start the dialogue server in the first terminal.  On DGX Spark, the script
uses a TensorRT-LLM Docker image when no local `trtllm-serve` is available.

```bash
bash scripts/start_trtllm_qwen3_8b.sh
```

In a second terminal, generate until the target duration is reached:

```bash
cd ~/Documents/eee/fullduplex_data_gen
conda activate vocos_3.13
bash scripts/generate_korean_qwen.sh 10 outputs/korean_qwen_10h
```

The first argument is target hours and the second is the output path.  The
manifest is saved after every complete dialogue, so repeating the same command
resumes the run after a stop.

For a short throughput measurement:

```bash
bash scripts/generate_korean_qwen.sh 0.5 outputs/korean_qwen_benchmark_30m
```

The current PyTorch Qwen3-TTS path synthesizes one event at a time.  Dialogue
serving runs through TensorRT-LLM, but cross-dialogue TTS batching is not yet
implemented.

## Output layout

```text
outputs/korean_qwen_10h/
├── manifest.jsonl
├── moshi.jsonl
├── run_config.json
└── sample_000000/
    ├── user.wav
    ├── assistant.wav
    ├── mixed.wav
    ├── moshi.wav
    ├── moshi.json
    ├── metadata.json
    └── transcript.txt
```

Validate generated data and inspect a sample:

```bash
PYTHONPATH=src python -m duplexforge validate outputs/korean_qwen_10h
PYTHONPATH=src python -m duplexforge inspect \
  outputs/korean_qwen_10h/sample_000000/metadata.json
```

## Moshi fine-tuning

Moshi and `moshi-finetune` are pinned as Git submodules. After cloning
DuplexForge, initialize them and apply the project-specific GB10 dependency
and Korean vocabulary patches:

```bash
git submodule update --init --recursive
bash scripts/apply_moshi_finetune_korean_vocab_patch.sh
```

The script can be rerun; it skips patches already present in a checkout.
The tokenizer and model configuration under `models/korean_moshiko_tokenizer/`
are generated locally and are not committed. Rebuild them from the dataset
using `scripts/build_korean_moshi_tokenizer.py` before running the extended
vocabulary training configs on a fresh machine.

Point the training configuration at generated JSONL files:

```yaml
data:
  train_data: "outputs/korean_train/moshi.jsonl"
  eval_data: "outputs/korean_eval/moshi.jsonl"
```

Read [Korean Moshi fine-tuning notes](docs/KOREAN_MOSHI_FINETUNING.md) and the
[GB10 environment notes](docs/MOSHI_ENVIRONMENT.md) before a long run.  Begin
with the smoke configuration, then use 10 hours of audio to judge whether the
Korean adaptation direction is viable.

## Debug example

```bash
PYTHONPATH=src python -m duplexforge generate \
  --goal "한국어 예약 변경 요청을 자연스럽게 처리하기" \
  --language ko \
  --dialogue-backend template \
  --tts-backend tone \
  --count 4 \
  --output outputs/debug_tone
```

## Limitations and next work

- TTS generation is sequential; batch TTS is the largest throughput target.
- Synthetic dialogues require listening-based quality checks.
- Synthetic VoiceDesign personas do not replace licensed real-speaker diversity.
- Approximate alignments need a forced-alignment upgrade.
- Korean tokenizer efficiency and text-embedding adaptation require dedicated
  experiments.

## Tests

```bash
python -m unittest discover -s tests -v
```
