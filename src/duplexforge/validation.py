from __future__ import annotations

import json
import wave
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
        _validate_audio(sample_id, sample_dir, metadata, issues)
        _validate_events(sample_id, metadata, issues)
    return ValidationReport(len(records), issues)


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
        if event.get("event_type") in {"backchannel", "interruption"}:
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

