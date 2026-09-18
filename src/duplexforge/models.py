from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Speaker = Literal["user", "assistant"]
EventType = Literal[
    "normal",
    "overlap",
    "backchannel",
    "interruption",
    "barge_in",
    "hesitation",
    "pause_fragment",
    "resume",
]
AnchorPoint = Literal["start", "end"]


@dataclass(slots=True)
class Timing:
    """Place an event relative to an earlier event.

    With ``anchor_id=None``, ``offset_ms`` is an absolute time from the start of
    the dialogue. Otherwise start time is anchor.start/end + offset_ms.
    Negative offsets from an anchor's end naturally create overlap.
    """

    anchor_id: str | None = None
    anchor_point: AnchorPoint = "end"
    offset_ms: int = 0

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "Timing":
        value = value or {}
        return cls(
            anchor_id=value.get("anchor_id"),
            anchor_point=value.get("anchor_point", "end"),
            offset_ms=int(value.get("offset_ms", 0)),
        )


@dataclass(slots=True)
class Event:
    id: str
    speaker: Speaker
    text: str
    event_type: EventType = "normal"
    timing: Timing = field(default_factory=Timing)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Event":
        return cls(
            id=str(value["id"]),
            speaker=value["speaker"],
            text=str(value["text"]).strip(),
            event_type=value.get("event_type", "normal"),
            timing=Timing.from_dict(value.get("timing")),
            metadata=dict(value.get("metadata", {})),
        )


@dataclass(slots=True)
class DialoguePlan:
    goal: str
    scenario: str
    events: list[Event]
    language: str = "ko"
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal must not be empty")
        if not self.events:
            raise ValueError("dialogue must contain at least one event")

        known: set[str] = set()
        valid_speakers = {"user", "assistant"}
        valid_types = {
            "normal",
            "overlap",
            "backchannel",
            "interruption",
            "barge_in",
            "hesitation",
            "pause_fragment",
            "resume",
        }
        for event in self.events:
            if not event.id or event.id in known:
                raise ValueError(f"duplicate or empty event id: {event.id!r}")
            if event.speaker not in valid_speakers:
                raise ValueError(f"invalid speaker in {event.id}: {event.speaker}")
            if event.event_type not in valid_types:
                raise ValueError(
                    f"invalid event_type in {event.id}: {event.event_type}"
                )
            if not event.text:
                raise ValueError(f"empty text in event {event.id}")
            if event.timing.anchor_id is not None:
                if event.timing.anchor_id not in known:
                    raise ValueError(
                        f"event {event.id} must anchor to an earlier event; "
                        f"unknown {event.timing.anchor_id!r}"
                    )
                if event.timing.anchor_id == event.id:
                    raise ValueError(f"event {event.id} cannot anchor to itself")
            if event.timing.anchor_point not in {"start", "end"}:
                raise ValueError(
                    f"invalid anchor point in {event.id}: {event.timing.anchor_point}"
                )
            known.add(event.id)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DialoguePlan":
        plan = cls(
            goal=str(value["goal"]),
            scenario=str(value.get("scenario", "generated")),
            language=str(value.get("language", "ko")),
            events=[Event.from_dict(item) for item in value["events"]],
            metadata=dict(value.get("metadata", {})),
        )
        plan.validate()
        return plan
