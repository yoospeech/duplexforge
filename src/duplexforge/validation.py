from __future__ import annotations

import json
import wave
<<<<<<< HEAD
from array import array
=======
>>>>>>> origin/main
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ValidationIssue:
    sample_id: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    sample_count: int
    issues: list[ValidationIssue]
<<<<<<< HEAD
    statistics: dict[str, float | int] | None = None
=======
>>>>>>> origin/main

    @property
    def ok(self) -> bool:
        return not self.issues


def validate_dataset(dataset_dir: Path) -> ValidationReport:
    manifest_path = dataset_dir / "manifest.jsonl"
    if not manifest_path.exists():
        return ValidationReport(
            0, [ValidationIssue("dataset", "manifest.jsonl is missing")]
        )

    records = []
    issues: list[ValidationIssue] = []
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            issues.append(
                ValidationIssue("dataset", f"invalid manifest line {line_number}: {exc}")
            )

<<<<<<< HEAD
    all_metadata: list[dict] = []
=======
>>>>>>> origin/main
    for record in records:
        sample_id = str(record.get("id", "unknown"))
        metadata_path = dataset_dir / str(record.get("metadata_path", ""))
        if not metadata_path.is_file():
            issues.append(ValidationIssue(sample_id, "metadata file is missing"))
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            issues.append(ValidationIssue(sample_id, f"cannot read metadata: {exc}"))
            continue
        sample_dir = metadata_path.parent
<<<<<<< HEAD
        all_metadata.append(metadata)
        _validate_audio(sample_id, sample_dir, metadata, issues)
        _validate_events(sample_id, metadata, issues)
        _validate_moshi_export(sample_id, sample_dir, metadata, issues)
    return ValidationReport(len(records), issues, _statistics(all_metadata))
=======
        _validate_audio(sample_id, sample_dir, metadata, issues)
        _validate_events(sample_id, metadata, issues)
    return ValidationReport(len(records), issues)
>>>>>>> origin/main


def _validate_audio(
    sample_id: str, sample_dir: Path, metadata: dict, issues: list[ValidationIssue]
) -> None:
    expected_rate = metadata.get("sample_rate")
    expected_ms = metadata.get("duration_ms")
    for role in ("user", "assistant", "mixed"):
        relative = metadata.get("audio", {}).get(role)
        path = sample_dir / relative if relative else None
        if path is None or not path.is_file():
            issues.append(ValidationIssue(sample_id, f"{role} audio is missing"))
            continue
        try:
            with wave.open(str(path), "rb") as wav:
                rate = wav.getframerate()
                duration_ms = round(wav.getnframes() * 1000 / rate)
                if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                    issues.append(
                        ValidationIssue(sample_id, f"{role} audio is not mono PCM16")
                    )
                if rate != expected_rate:
                    issues.append(
                        ValidationIssue(
                            sample_id,
                            f"{role} sample rate {rate} != metadata {expected_rate}",
                        )
                    )
                if expected_ms is not None and abs(duration_ms - expected_ms) > 2:
                    issues.append(
                        ValidationIssue(
                            sample_id,
                            f"{role} duration {duration_ms}ms != metadata {expected_ms}ms",
                        )
                    )
        except (wave.Error, OSError, ZeroDivisionError) as exc:
            issues.append(ValidationIssue(sample_id, f"invalid {role} WAV: {exc}"))


def _validate_events(
    sample_id: str, metadata: dict, issues: list[ValidationIssue]
) -> None:
    events = metadata.get("events", [])
    duration_ms = metadata.get("duration_ms", 0)
    if not events:
        issues.append(ValidationIssue(sample_id, "no events"))
        return
    for event in events:
        event_id = event.get("id", "unknown")
        start = event.get("start_ms")
        end = event.get("end_ms")
        if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end:
            issues.append(ValidationIssue(sample_id, f"invalid interval for {event_id}"))
            continue
        if end > duration_ms:
            issues.append(
                ValidationIssue(sample_id, f"event {event_id} exceeds dialogue duration")
            )
<<<<<<< HEAD
        if event.get("event_type") in {"backchannel", "interruption", "overlap", "barge_in"}:
=======
        if event.get("event_type") in {"backchannel", "interruption"}:
>>>>>>> origin/main
            overlaps_opposite = any(
                other.get("speaker") != event.get("speaker")
                and other.get("start_ms", 0) < end
                and start < other.get("end_ms", 0)
                for other in events
                if other is not event
            )
            if not overlaps_opposite:
                issues.append(
                    ValidationIssue(
                        sample_id,
                        f"{event.get('event_type')} {event_id} has no cross-speaker overlap",
                    )
                )

<<<<<<< HEAD

def _validate_moshi_export(
    sample_id: str, sample_dir: Path, metadata: dict, issues: list[ValidationIssue]
) -> None:
    relative = metadata.get("audio", {}).get("moshi_stereo")
    wav_path = sample_dir / relative if relative else None
    transcript_path = wav_path.with_suffix(".json") if wav_path else None
    if wav_path is None or not wav_path.is_file():
        issues.append(ValidationIssue(sample_id, "Moshi stereo WAV is missing"))
        return
    try:
        with wave.open(str(wav_path), "rb") as wav:
            if wav.getnchannels() != 2 or wav.getsampwidth() != 2:
                issues.append(ValidationIssue(sample_id, "Moshi WAV is not stereo PCM16"))
            if wav.getframerate() != metadata.get("sample_rate"):
                issues.append(ValidationIssue(sample_id, "Moshi WAV sample rate mismatch"))
            frames = wav.readframes(wav.getnframes())
            values = array("h")
            values.frombytes(frames)
            if not values:
                issues.append(ValidationIssue(sample_id, "Moshi WAV is empty"))
            elif max(abs(value) for value in values) >= 32767:
                issues.append(ValidationIssue(sample_id, "Moshi WAV contains clipping"))
    except (wave.Error, OSError) as exc:
        issues.append(ValidationIssue(sample_id, f"invalid Moshi WAV: {exc}"))
    if transcript_path is None or not transcript_path.is_file():
        issues.append(ValidationIssue(sample_id, "Moshi transcript JSON is missing"))
        return
    try:
        payload = json.loads(transcript_path.read_text(encoding="utf-8"))
        alignments = payload["alignments"]
        duration = metadata.get("duration_ms", 0) / 1000
        for alignment in alignments:
            start, end = alignment[1]
            if not (0 <= start < end <= duration + 0.002):
                issues.append(ValidationIssue(sample_id, "invalid Moshi alignment range"))
                break
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        issues.append(ValidationIssue(sample_id, f"invalid Moshi transcript: {exc}"))


def _statistics(metadata_items: list[dict]) -> dict[str, float | int]:
    events = [event for item in metadata_items for event in item.get("events", [])]
    total_ms = sum(item.get("duration_ms", 0) for item in metadata_items)
    overlap_ms = 0
    response_latencies: list[int] = []
    silence_gaps: list[int] = []
    for item in metadata_items:
        ordered = sorted(item.get("events", []), key=lambda value: value.get("start_ms", 0))
        for left, right in zip(ordered, ordered[1:]):
            if left.get("speaker") != right.get("speaker"):
                response_latencies.append(right["start_ms"] - left["end_ms"])
            silence_gaps.append(max(0, right["start_ms"] - left["end_ms"]))
        users = [e for e in ordered if e.get("speaker") == "user"]
        assistants = [e for e in ordered if e.get("speaker") == "assistant"]
        overlap_ms += sum(
            max(0, min(u["end_ms"], a["end_ms"]) - max(u["start_ms"], a["start_ms"]))
            for u in users for a in assistants
        )
    count = len(events)
    result: dict[str, float | int] = {
        "total_hours": round(total_ms / 3_600_000, 6),
        "conversations": len(metadata_items),
        "turns": count,
        "average_turn_duration_ms": round(sum(e["duration_ms"] for e in events) / count, 2) if count else 0,
        "average_response_latency_ms": round(sum(response_latencies) / len(response_latencies), 2) if response_latencies else 0,
        "overlap_ratio": round(overlap_ms / total_ms, 6) if total_ms else 0,
        "average_silence_ms": round(sum(silence_gaps) / len(silence_gaps), 2) if silence_gaps else 0,
        "user_turns": sum(e.get("speaker") == "user" for e in events),
        "assistant_turns": sum(e.get("speaker") == "assistant" for e in events),
    }
    for event_type in ("interruption", "barge_in", "backchannel"):
        number = sum(e.get("event_type") == event_type for e in events)
        result[f"{event_type}_count"] = number
        result[f"{event_type}_rate"] = round(number / count, 6) if count else 0
    return result
=======
>>>>>>> origin/main
