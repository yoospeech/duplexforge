from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
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
    count: int = 4
    patterns: tuple[str, ...] = PATTERNS
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
        if self.count < 1:
            raise ValueError("count must be at least 1")
        if self.language not in LANGUAGES:
            raise ValueError(
                f"unsupported language: {self.language}; choose from {', '.join(LANGUAGES)}"
            )
        unknown = set(self.patterns) - set(PATTERNS)
        if unknown:
            raise ValueError(f"unknown patterns: {', '.join(sorted(unknown))}")
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

    for index in range(config.count):
        pattern = config.patterns[index % len(config.patterns)]
        sample_id = f"sample_{index:06d}"
        plan = generator.generate(config.goal, pattern, index)
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
    """Create two distinct and reproducible VoiceDesign personas per sample."""

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
    assistant = make("assistant", 1)
    return user, assistant
