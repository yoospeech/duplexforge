from __future__ import annotations

import json
import re
from pathlib import Path

from .audio import AudioBuffer, write_stereo_wav


ASSISTANT_LABEL = "SPEAKER_MAIN"
USER_LABEL = "SPEAKER_USER"


def export_moshi_sample(
    output_dir: Path,
    assistant: AudioBuffer,
    user: AudioBuffer,
    events: list[object],
) -> tuple[Path, Path]:
    """Export the current moshi-finetune stereo WAV + adjacent JSON format.

    Upstream consumes channel 0 as Moshi output and channel 1 as user input.
    Transcript entries are word-level approximations spread over each synthetic
    utterance. TTS-native alignments can replace these later without changing the
    exported schema.
    """
    wav_path = output_dir / "moshi.wav"
    json_path = output_dir / "moshi.json"
    write_stereo_wav(wav_path, assistant, user)
    alignments: list[list[object]] = []
    for event in sorted(events, key=lambda item: (item.start_ms, item.id)):
        words = _words(event.text)
        if not words:
            continue
        start = event.start_ms / 1000
        end = event.end_ms / 1000
        step = (end - start) / len(words)
        label = ASSISTANT_LABEL if event.speaker == "assistant" else USER_LABEL
        for index, word in enumerate(words):
            word_start = start + index * step
            word_end = start + (index + 1) * step
            alignments.append([word, [word_start, word_end], label])
    alignments.sort(key=lambda item: (item[1][0], item[1][1]))
    json_path.write_text(
        json.dumps({"alignments": alignments}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return wav_path, json_path


def _words(text: str) -> list[str]:
    return [part for part in re.findall(r"\S+", text.strip()) if part]
