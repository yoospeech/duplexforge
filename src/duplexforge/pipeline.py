from __future__ import annotations

import json
import os
import random
<<<<<<< HEAD
import sys
from dataclasses import dataclass, field
=======
from dataclasses import dataclass
>>>>>>> origin/main
from pathlib import Path

from .audio import (
    EDGE_VOICE_POOLS,
    EdgeTTSSynthesizer,
    Qwen3EdgeLLMSynthesizer,
    Qwen3TTSSynthesizer,
    SpeechSynthesizer,
    ToneSynthesizer,
    VoiceProfile,
)
from .dialogue import (
    LANGUAGES,
    PATTERNS,
    DialogueGenerator,
    OpenAICompatibleDialogueGenerator,
    TemplateDialogueGenerator,
)
from .renderer import render_dialogue


@dataclass(slots=True)
class GenerationConfig:
    goal: str
    output_dir: Path
    language: str = "ko"
<<<<<<< HEAD
    count: int | None = 4
    target_duration_hours: float | None = None
    patterns: tuple[str, ...] = ()
    pattern_weights: dict[str, float] = field(
        default_factory=lambda: {
            "normal": 0.45,
            "overlap": 0.10,
            "interruption": 0.15,
            "barge_in": 0.10,
            "backchannel": 0.10,
            "hesitation": 0.10,
        }
    )
=======
    count: int = 4
    patterns: tuple[str, ...] = PATTERNS
>>>>>>> origin/main
    seed: int = 42
    dialogue_backend: str = "trtllm"
    tts_backend: str = "qwen3"
    model: str = "nvidia/Qwen3-8B-FP8"
    base_url: str = "http://localhost:8000/v1"
    api_key: str | None = None
    user_voice: str | None = None
    assistant_voice: str | None = None
    qwen_tts_model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    qwen_tts_device: str = "cuda:0"
    qwen_tts_attention: str = "auto"
    edgellm_binary: Path = Path("TensorRT-Edge-LLM/build/examples/omni/qwen3_tts_inference")
    edgellm_engine_dir: Path = Path("engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
    qwen_tts_checkpoint: Path = Path("models/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
    voice_strategy: str = "random"
    keep_event_audio: bool = True

    def validate(self) -> None:
        if not self.goal.strip():
            raise ValueError("goal must not be empty")
<<<<<<< HEAD
        if self.count is not None and self.count < 1:
            raise ValueError("count must be at least 1")
        if self.target_duration_hours is not None and self.target_duration_hours <= 0:
            raise ValueError("target_duration_hours must be positive")
        if self.count is None and self.target_duration_hours is None:
            raise ValueError("count or target_duration_hours is required")
=======
        if self.count < 1:
            raise ValueError("count must be at least 1")
>>>>>>> origin/main
        if self.language not in LANGUAGES:
            raise ValueError(
                f"unsupported language: {self.language}; choose from {', '.join(LANGUAGES)}"
            )
        unknown = set(self.patterns) - set(PATTERNS)
        if unknown:
            raise ValueError(f"unknown patterns: {', '.join(sorted(unknown))}")
<<<<<<< HEAD
        unknown_weights = set(self.pattern_weights) - set(PATTERNS)
        if unknown_weights or any(value < 0 for value in self.pattern_weights.values()):
            raise ValueError("pattern weights must be non-negative known patterns")
        if not self.patterns and sum(self.pattern_weights.values()) <= 0:
            raise ValueError("at least one pattern weight must be positive")
=======
>>>>>>> origin/main
        if self.dialogue_backend not in {"template", "openai", "trtllm"}:
            raise ValueError(f"unknown dialogue backend: {self.dialogue_backend}")
        if self.tts_backend not in {"tone", "edge", "qwen3", "qwen3-edgellm"}:
            raise ValueError(f"unknown TTS backend: {self.tts_backend}")
        if self.voice_strategy not in {"random", "fixed"}:
            raise ValueError(f"unknown voice strategy: {self.voice_strategy}")


def generate_dataset(config: GenerationConfig) -> list[dict]:
    config.validate()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    generator = _make_dialogue_generator(config)
    rng = random.Random(config.seed)
    records: list[dict] = []
<<<<<<< HEAD
    manifest = config.output_dir / "manifest.jsonl"
    if config.target_duration_hours is not None and manifest.exists():
        records = [
            json.loads(line)
            for line in manifest.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    initial_count = len(records)
    total_duration_ms = sum(int(item.get("duration_ms", 0)) for item in records)
    target_duration_ms = (
        round(config.target_duration_hours * 3_600_000)
        if config.target_duration_hours is not None
        else None
    )

    index = initial_count
    while True:
        if target_duration_ms is not None and total_duration_ms >= target_duration_ms:
            break
        if target_duration_ms is None and config.count is not None:
            if index - initial_count >= config.count:
                break
        if config.patterns:
            pattern = config.patterns[index % len(config.patterns)]
        else:
            names = tuple(config.pattern_weights)
            weights = tuple(config.pattern_weights[name] for name in names)
            pattern = random.Random(f"{config.seed}:{index}:timeline").choices(
                names, weights=weights, k=1
            )[0]
        sample_id = f"sample_{index:06d}"
        plan = _generate_valid_plan(generator, config.goal, pattern, index)
=======

    for index in range(config.count):
        pattern = config.patterns[index % len(config.patterns)]
        sample_id = f"sample_{index:06d}"
        plan = generator.generate(config.goal, pattern, index)
>>>>>>> origin/main
        plan.metadata["sample_id"] = sample_id
        plan.metadata["seed"] = config.seed
        synthesizer, voices = _make_synthesizer(config, index)
        if voices:
            plan.metadata["voices"] = voices
        sample_dir = config.output_dir / sample_id
        result = render_dialogue(
            plan,
            sample_dir,
            synthesizer,
            keep_event_audio=config.keep_event_audio,
        )
        record = {
            "id": sample_id,
            "goal": config.goal,
            "language": plan.language,
            "scenario": plan.scenario,
            "pattern": pattern,
            "duration_ms": result.duration_ms,
            "sample_rate": result.sample_rate,
            "voices": voices,
            "metadata_path": f"{sample_id}/metadata.json",
            "mixed_audio_path": f"{sample_id}/mixed.wav",
            "user_audio_path": f"{sample_id}/user.wav",
            "assistant_audio_path": f"{sample_id}/assistant.wav",
<<<<<<< HEAD
            "path": str((sample_dir / "moshi.wav").resolve()),
            "duration": result.duration_ms / 1000,
            "split": "train" if rng.random() < 0.9 else "validation",
        }
        records.append(record)
        total_duration_ms += result.duration_ms
        index += 1

        # Persist progress after every sample so a long target-hours run can be
        # safely resumed after interruption.
        _write_manifests(config.output_dir, records)

    _write_manifests(config.output_dir, records)
    run_config = {
        "goal": config.goal,
        "language": config.language,
        "count": len(records),
        "target_duration_hours": config.target_duration_hours,
        "actual_duration_hours": total_duration_ms / 3_600_000,
        "patterns": list(config.patterns) if config.patterns else None,
        "pattern_weights": config.pattern_weights,
=======
            "split": "train" if rng.random() < 0.9 else "validation",
        }
        records.append(record)

    manifest = config.output_dir / "manifest.jsonl"
    manifest.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )
    run_config = {
        "goal": config.goal,
        "language": config.language,
        "count": config.count,
        "patterns": list(config.patterns),
>>>>>>> origin/main
        "seed": config.seed,
        "dialogue_backend": config.dialogue_backend,
        "tts_backend": config.tts_backend,
        "voice_strategy": config.voice_strategy,
        "model": config.model if config.dialogue_backend != "template" else None,
        "base_url": config.base_url if config.dialogue_backend != "template" else None,
        "user_voice": config.user_voice,
        "assistant_voice": config.assistant_voice,
        "qwen_tts_model": config.qwen_tts_model if config.tts_backend.startswith("qwen3") else None,
        "qwen_tts_device": config.qwen_tts_device if config.tts_backend == "qwen3" else None,
        "edgellm_binary": str(config.edgellm_binary) if config.tts_backend == "qwen3-edgellm" else None,
        "edgellm_engine_dir": str(config.edgellm_engine_dir) if config.tts_backend == "qwen3-edgellm" else None,
        "qwen_tts_checkpoint": str(config.qwen_tts_checkpoint) if config.tts_backend == "qwen3-edgellm" else None,
    }
    (config.output_dir / "run_config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return records


<<<<<<< HEAD
def _write_manifests(output_dir: Path, records: list[dict]) -> None:
    (output_dir / "manifest.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )


def _generate_valid_plan(
    generator: DialogueGenerator, goal: str, pattern: str, index: int, max_attempts: int = 4
):
    """Retry malformed LLM timeline responses without losing a long run.

    Template generation is deterministic and already validated.  An LLM can
    occasionally return a forward or nonexistent timing anchor despite the
    schema prompt; retrying produces a fresh structured response for the same
    sample id and preserves the target-duration accounting.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return generator.generate(goal, pattern, index)
        except ValueError as exc:
            last_error = exc
            if attempt < max_attempts:
                print(
                    f"warning: invalid dialogue plan for sample_{index:06d} "
                    f"(attempt {attempt}/{max_attempts}): {exc}; retrying",
                    file=sys.stderr,
                )
    assert last_error is not None
    raise RuntimeError(
        f"failed to create a valid dialogue plan for sample_{index:06d} "
        f"after {max_attempts} attempts: {last_error}"
    ) from last_error
    (output_dir / "moshi.jsonl").write_text(
        "".join(
            json.dumps({"path": item["path"], "duration": item["duration"]}) + "\n"
            for item in records
        ),
        encoding="utf-8",
    )


=======
>>>>>>> origin/main
def _make_dialogue_generator(config: GenerationConfig) -> DialogueGenerator:
    if config.dialogue_backend == "template":
        return TemplateDialogueGenerator(seed=config.seed, language=config.language)
    is_trtllm = config.dialogue_backend == "trtllm"
    api_key = config.api_key or os.environ.get("OPENAI_API_KEY")
    if is_trtllm and not api_key:
        api_key = "tensorrt_llm"
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY is required for --dialogue-backend openai "
            "(or pass --api-key)"
        )
    return OpenAICompatibleDialogueGenerator(
        api_key=api_key,
        model=config.model,
        base_url=config.base_url,
        language=config.language,
        use_response_format=not is_trtllm,
        non_thinking=is_trtllm,
    )


def _make_synthesizer(
    config: GenerationConfig, index: int
) -> tuple[SpeechSynthesizer, dict]:
    if config.tts_backend == "tone":
        return ToneSynthesizer(), {}
    if config.tts_backend == "qwen3":
        user, assistant = _select_qwen3_voices(config, index)
        metadata = {"user": user, "assistant": assistant}
        return (
            Qwen3TTSSynthesizer(
                language=config.language,
                user_instruct=user["instruct"],
                assistant_instruct=assistant["instruct"],
                model_id=config.qwen_tts_model,
                device=config.qwen_tts_device,
                attention=config.qwen_tts_attention,
                seed=config.seed + index * 1009,
            ),
            metadata,
        )
    if config.tts_backend == "qwen3-edgellm":
        user, assistant = _select_qwen3_voices(config, index)
        metadata = {"user": user, "assistant": assistant}
        return (
            Qwen3EdgeLLMSynthesizer(
                language=config.language,
                user_instruct=user["instruct"],
                assistant_instruct=assistant["instruct"],
                binary=config.edgellm_binary,
                engine_dir=config.edgellm_engine_dir,
                checkpoint_dir=config.qwen_tts_checkpoint,
            ),
            metadata,
        )
    user, assistant = _select_voices(config, index)
    metadata = {
        "user": _profile_dict(user),
        "assistant": _profile_dict(assistant),
    }
    return (
        EdgeTTSSynthesizer(user_voice=user.id, assistant_voice=assistant.id),
        metadata,
    )


def _select_voices(
    config: GenerationConfig, index: int
) -> tuple[VoiceProfile, VoiceProfile]:
    pool = list(EDGE_VOICE_POOLS[config.language])
    if config.voice_strategy == "fixed":
        selected = pool[:2]
    else:
        selected = list(_balanced_random_pair(pool, config, index))

    user = _custom_profile(config.user_voice) if config.user_voice else selected[0]
    assistant = (
        _custom_profile(config.assistant_voice)
        if config.assistant_voice
        else selected[1]
    )
    if user.id == assistant.id:
        assistant = next(profile for profile in pool if profile.id != user.id)
    return user, assistant


def _balanced_random_pair(
    pool: list[VoiceProfile], config: GenerationConfig, index: int
) -> tuple[VoiceProfile, VoiceProfile]:
    """Random-looking, reproducible pairs with full pool coverage per epoch."""

    size = len(pool)
    epoch, position = divmod(index, size)
    users = pool.copy()
    epoch_rng = random.Random(
        f"{config.seed}:{config.language}:{epoch}:voice-order"
    )
    epoch_rng.shuffle(users)
    # A non-zero rotation preserves full coverage and guarantees distinct roles.
    shift = epoch_rng.randrange(1, size)
    assistants = users[shift:] + users[:shift]
    return users[position], assistants[position]


def _custom_profile(voice_id: str) -> VoiceProfile:
    locale = "-".join(voice_id.split("-")[:2])
    return VoiceProfile(voice_id, locale, "unknown")


def _profile_dict(profile: VoiceProfile) -> dict[str, str]:
    return {"id": profile.id, "locale": profile.locale, "gender": profile.gender}


def _select_qwen3_voices(config: GenerationConfig, index: int) -> tuple[dict, dict]:
<<<<<<< HEAD
    """Create a diverse user and one dataset-stable assistant persona."""
=======
    """Create two distinct and reproducible VoiceDesign personas per sample."""
>>>>>>> origin/main

    genders = ("female", "male")
    ages = ("young adult", "adult", "middle-aged", "older adult")
    timbres = ("warm and soft", "clear and bright", "low and mellow", "light and airy")
    styles = ("calm and friendly", "natural and conversational", "confident but relaxed", "patient and empathetic")

    def make(role: str, salt: int) -> dict[str, str]:
        rng = random.Random(f"{config.seed}:{config.language}:{index}:{role}:{salt}")
        gender = rng.choice(genders)
        age = rng.choice(ages)
        timbre = rng.choice(timbres)
        style = rng.choice(styles)
        identity = f"qwen3-vd-{config.language}-{index:06d}-{role}"
        instruct = (
            f"A distinct {age} {gender} speaker with a {timbre} voice. "
            f"Speak in a {style} manner, at a realistic conversational pace. "
            "Keep the same vocal identity throughout this dialogue."
        )
        return {
            "id": identity,
            "locale": config.language,
            "gender": gender,
            "instruct": instruct,
            "model": config.qwen_tts_model,
        }

    user = make("user", 0)
<<<<<<< HEAD
    if config.assistant_voice:
        assistant = {
            "id": f"qwen3-vd-{config.language}-assistant-fixed",
            "locale": config.language,
            "gender": "configured",
            "instruct": config.assistant_voice,
            "model": config.qwen_tts_model,
        }
    else:
        # Do not include the sample index: the target Moshi identity must remain
        # stable throughout an entire dataset run.
        rng = random.Random(f"{config.seed}:{config.language}:assistant-fixed")
        gender = rng.choice(genders)
        age = rng.choice(ages)
        timbre = rng.choice(timbres)
        style = rng.choice(styles)
        assistant = {
            "id": f"qwen3-vd-{config.language}-assistant-fixed",
            "locale": config.language,
            "gender": gender,
            "instruct": (
                f"A single consistent {age} {gender} Korean assistant with a "
                f"{timbre} voice. Speak in a {style} manner at a realistic "
                "conversational pace. Preserve exactly the same speaker identity "
                "for every utterance and every dialogue."
            ),
            "model": config.qwen_tts_model,
        }
=======
    assistant = make("assistant", 1)
>>>>>>> origin/main
    return user, assistant
