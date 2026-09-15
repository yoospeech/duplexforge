from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .audio import (
    AudioBuffer,
    SpeechSynthesizer,
    combine,
    empty_audio,
    overlay,
    write_wav,
)
from .models import DialoguePlan


@dataclass(slots=True)
class RenderedEvent:
    id: str
    speaker: str
    text: str
    event_type: str
    start_ms: int
    end_ms: int
    duration_ms: int
    audio_path: str
    metadata: dict


@dataclass(slots=True)
class RenderResult:
    duration_ms: int
    events: list[RenderedEvent]
    sample_rate: int


def render_dialogue(
    plan: DialoguePlan,
    output_dir: Path,
    synthesizer: SpeechSynthesizer,
    keep_event_audio: bool = True,
) -> RenderResult:
    plan.validate()
    output_dir.mkdir(parents=True, exist_ok=True)
    event_dir = output_dir / "events"
    event_dir.mkdir(exist_ok=True)

    audio_by_id: dict[str, AudioBuffer] = {}
    interval_by_id: dict[str, tuple[int, int]] = {}
    rendered: list[RenderedEvent] = []
    sample_rate: int | None = None

    wav_paths = [event_dir / f"{event.id}_{event.speaker}.wav" for event in plan.events]
    if hasattr(synthesizer, "synthesize_batch"):
        batch = [(event.text, event.speaker, path) for event, path in zip(plan.events, wav_paths)]
        generated_audio = synthesizer.synthesize_batch(batch)  # type: ignore[attr-defined]
    else:
        generated_audio = [
            synthesizer.synthesize(event.text, event.speaker, path)
            for event, path in zip(plan.events, wav_paths)
        ]
    if len(generated_audio) != len(plan.events):
        raise RuntimeError("TTS batch result count does not match event count")

    for event, wav_path, audio in zip(plan.events, wav_paths, generated_audio):
        if sample_rate is None:
            sample_rate = audio.sample_rate
        elif audio.sample_rate != sample_rate:
            raise ValueError(
                f"TTS returned inconsistent sample rates: {sample_rate} and "
                f"{audio.sample_rate}"
            )

        timing = event.timing
        if timing.anchor_id is None:
            start_ms = timing.offset_ms
        else:
            anchor_start, anchor_end = interval_by_id[timing.anchor_id]
            anchor = anchor_start if timing.anchor_point == "start" else anchor_end
            start_ms = anchor + timing.offset_ms
        start_ms = max(0, start_ms)
        end_ms = start_ms + audio.duration_ms
        interval_by_id[event.id] = (start_ms, end_ms)
        audio_by_id[event.id] = audio
        rendered.append(
            RenderedEvent(
                id=event.id,
                speaker=event.speaker,
                text=event.text,
                event_type=event.event_type,
                start_ms=start_ms,
                end_ms=end_ms,
                duration_ms=audio.duration_ms,
                audio_path=str(wav_path.relative_to(output_dir)),
                metadata=event.metadata,
            )
        )

    assert sample_rate is not None
    duration_ms = max(item.end_ms for item in rendered) + 200
    tracks = {
        "user": empty_audio(duration_ms, sample_rate),
        "assistant": empty_audio(duration_ms, sample_rate),
    }
    for item in rendered:
        overlay(tracks[item.speaker], audio_by_id[item.id], item.start_ms)

    write_wav(output_dir / "user.wav", tracks["user"])
    write_wav(output_dir / "assistant.wav", tracks["assistant"])
    write_wav(output_dir / "mixed.wav", combine(tracks["user"], tracks["assistant"]))

    result = RenderResult(duration_ms, rendered, sample_rate)
    if not keep_event_audio:
        for path in event_dir.glob("*.wav"):
            path.unlink()
        event_dir.rmdir()
        for item in rendered:
            item.audio_path = ""

    metadata = {
        "schema_version": "1.0",
        "goal": plan.goal,
        "scenario": plan.scenario,
        "language": plan.language,
        "duration_ms": duration_ms,
        "sample_rate": sample_rate,
        "audio": {
            "user": "user.wav",
            "assistant": "assistant.wav",
            "mixed": "mixed.wav",
        },
        "events": [asdict(item) for item in rendered],
        "metadata": {**plan.metadata, "tts": synthesizer.name},
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    transcript = "\n".join(
        f"[{item.start_ms / 1000:07.3f}-{item.end_ms / 1000:07.3f}] "
        f"{item.speaker:<9} ({item.event_type}): {item.text}"
        for item in sorted(rendered, key=lambda value: (value.start_ms, value.id))
    )
    (output_dir / "transcript.txt").write_text(transcript + "\n", encoding="utf-8")

    return result
