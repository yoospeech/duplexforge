# Moshi training environment on NVIDIA GB10

Environment: `/home/ysw/Documents/anaconda3/envs/moshi_finetune`

```bash
conda activate moshi_finetune
```

Pinned source revisions:

- `kyutai-labs/moshi-finetune`: `2acc879fe7c48f885a18f6cc9548bccb2674d87b`
- `kyutai-labs/moshi`: `7b5f6505ca1d828e5c9dce11555d3b1d1319ae28`

The unpinned Moshi dependency on current main conflicts with
`moshi-finetune`'s `sphn==0.1.12`, so Moshi is pinned to the matching 0.2.9-era
revision. On linux-aarch64, that revision's bitsandbytes 0.45 wheel is
unavailable; bitsandbytes is omitted because the BF16 model path does not use
8-bit loading. PyTorch and torchaudio are aligned with the existing GB10 setup:
`torch 2.9.0+cu130` and `torchaudio 2.9.0`.

CUDA smoke check passed on NVIDIA GB10. PyTorch emits a warning because the GPU
reports compute capability 12.1 while this wheel advertises support through
12.0; basic CUDA execution works, but long training must still be monitored for
unsupported kernels.

## Verified smoke training

`configs/moshi_smoke.yaml` completed one full LoRA optimizer step on 2026-09-17:

- loss: 6.185
- peak allocated GPU memory: 15.2 GB
- elapsed time: 1 minute 50 seconds
- LoRA rank: 8
- sequence duration: 10 seconds

This run used tone-debug audio only to verify the complete data/Mimi/Moshi
forward-backward pipeline. It is not evidence of Korean speech quality.
