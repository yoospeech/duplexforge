from __future__ import annotations

import asyncio
import math
import shutil
import subprocess
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Protocol


@dataclass(frozen=True, slots=True)
class VoiceProfile:
    id: str
    locale: str
    gender: str


def _voice(voice_id: str, gender: str) -> VoiceProfile:
    return VoiceProfile(voice_id, "-".join(voice_id.split("-")[:2]), gender)


EDGE_VOICE_POOLS = {
    "ko": (
        _voice("ko-KR-HyunsuMultilingualNeural", "male"),
        _voice("ko-KR-InJoonNeural", "male"),
        _voice("ko-KR-SunHiNeural", "female"),
    ),
    "en": (
        _voice("en-US-AndrewNeural", "male"),
        _voice("en-US-AvaNeural", "female"),
        _voice("en-US-BrianNeural", "male"),
        _voice("en-US-EmmaNeural", "female"),
        _voice("en-US-GuyNeural", "male"),
        _voice("en-US-JennyNeural", "female"),
        _voice("en-GB-RyanNeural", "male"),
        _voice("en-GB-SoniaNeural", "female"),
        _voice("en-AU-NatashaNeural", "female"),
        _voice("en-AU-WilliamMultilingualNeural", "male"),
        _voice("en-IN-NeerjaNeural", "female"),
        _voice("en-IN-PrabhatNeural", "male"),
        _voice("en-CA-ClaraNeural", "female"),
        _voice("en-CA-LiamNeural", "male"),
        _voice("en-IE-ConnorNeural", "male"),
        _voice("en-IE-EmilyNeural", "female"),
    ),
    "es": (
        _voice("es-ES-AlvaroNeural", "male"),
        _voice("es-ES-ElviraNeural", "female"),
        _voice("es-ES-XimenaNeural", "female"),
        _voice("es-MX-DaliaNeural", "female"),
        _voice("es-MX-JorgeNeural", "male"),
        _voice("es-AR-ElenaNeural", "female"),
        _voice("es-AR-TomasNeural", "male"),
        _voice("es-CO-GonzaloNeural", "male"),
        _voice("es-CO-SalomeNeural", "female"),
        _voice("es-CL-CatalinaNeural", "female"),
        _voice("es-CL-LorenzoNeural", "male"),
        _voice("es-PE-AlexNeural", "male"),
        _voice("es-PE-CamilaNeural", "female"),
        _voice("es-US-AlonsoNeural", "male"),
        _voice("es-US-PalomaNeural", "female"),
    ),
    "fr": (
        _voice("fr-FR-DeniseNeural", "female"),
        _voice("fr-FR-EloiseNeural", "female"),
        _voice("fr-FR-HenriNeural", "male"),
        _voice("fr-FR-RemyMultilingualNeural", "male"),
        _voice("fr-FR-VivienneMultilingualNeural", "female"),
        _voice("fr-CA-AntoineNeural", "male"),
        _voice("fr-CA-JeanNeural", "male"),
        _voice("fr-CA-SylvieNeural", "female"),
        _voice("fr-BE-CharlineNeural", "female"),
        _voice("fr-BE-GerardNeural", "male"),
        _voice("fr-CH-ArianeNeural", "female"),
        _voice("fr-CH-FabriceNeural", "male"),
    ),
}


@dataclass(slots=True)
class AudioBuffer:
    samples: array
    sample_rate: int

    @property
    def duration_ms(self) -> int:
        return round(len(self.samples) * 1000 / self.sample_rate)


class SpeechSynthesizer(Protocol):
    name: str

    def synthesize(self, text: str, speaker: str, output_path: Path) -> AudioBuffer: ...


def read_wav(path: Path) -> AudioBuffer:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError(f"only 16-bit PCM WAV is supported: {path}")
    values = array("h")
    values.frombytes(frames)
    if channels == 2:
        values = array(
            "h",
            (
                int((values[i] + values[i + 1]) / 2)
                for i in range(0, len(values), 2)
            ),
        )
    elif channels != 1:
        raise ValueError(f"only mono/stereo WAV is supported: {path}")
    return AudioBuffer(values, rate)


def write_wav(path: Path, audio: AudioBuffer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(audio.sample_rate)
        wav.writeframes(audio.samples.tobytes())


def write_stereo_wav(path: Path, left: AudioBuffer, right: AudioBuffer) -> None:
    """Write sample-aligned PCM16 stereo (left then right)."""
    if left.sample_rate != right.sample_rate:
        raise ValueError("stereo channel sample rates must match")
    length = max(len(left.samples), len(right.samples))
    interleaved = array("h")
    for index in range(length):
        interleaved.append(left.samples[index] if index < len(left.samples) else 0)
        interleaved.append(right.samples[index] if index < len(right.samples) else 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(left.sample_rate)
        wav.writeframes(interleaved.tobytes())


def empty_audio(duration_ms: int, sample_rate: int) -> AudioBuffer:
    length = max(0, round(duration_ms * sample_rate / 1000))
    return AudioBuffer(array("h", [0]) * length, sample_rate)


def overlay(target: AudioBuffer, source: AudioBuffer, start_ms: int) -> None:
    if target.sample_rate != source.sample_rate:
        raise ValueError("sample rates must match before mixing")
    start = round(start_ms * target.sample_rate / 1000)
    required = start + len(source.samples)
    if required > len(target.samples):
        target.samples.extend([0] * (required - len(target.samples)))
    for pos, value in enumerate(source.samples, start=start):
        target.samples[pos] = _clip16(target.samples[pos] + value)


def combine(left: AudioBuffer, right: AudioBuffer, gain: float = 0.72) -> AudioBuffer:
    if left.sample_rate != right.sample_rate:
        raise ValueError("sample rates must match before mixing")
    length = max(len(left.samples), len(right.samples))
    samples = array("h", [0]) * length
    for i in range(length):
        a = left.samples[i] if i < len(left.samples) else 0
        b = right.samples[i] if i < len(right.samples) else 0
        samples[i] = _clip16(round((a + b) * gain))
    return AudioBuffer(samples, left.sample_rate)


def _clip16(value: int | float) -> int:
    return max(-32768, min(32767, int(value)))


@dataclass(slots=True)
class ToneSynthesizer:
    """Dependency-free debug synthesizer.

    It produces speech-shaped tones, not intelligible speech. This makes the full
    pipeline reproducible offline while keeping timestamps and overlaps testable.
    """

    sample_rate: int = 24000
    name: str = "tone-debug"

    def synthesize(self, text: str, speaker: str, output_path: Path) -> AudioBuffer:
        base = 190 if speaker == "user" else 260
        char_ms = 72
        gap_ms = 14
        samples = array("h")
        phase = 0.0
        for char in text:
            if char.isspace():
                samples.extend([0] * round(self.sample_rate * 0.045))
                continue
            duration_ms = 105 if char in ".?!。？！" else char_ms
            count = round(self.sample_rate * duration_ms / 1000)
            frequency = base + (ord(char) % 11) * 13
            fade = max(1, round(self.sample_rate * 0.008))
            for i in range(count):
                envelope = min(1.0, i / fade, (count - i) / fade)
                value = 5200 * envelope * math.sin(phase)
                samples.append(_clip16(value))
                phase += 2 * math.pi * frequency / self.sample_rate
            samples.extend([0] * round(self.sample_rate * gap_ms / 1000))
        samples.extend([0] * round(self.sample_rate * 0.08))
        audio = AudioBuffer(samples, self.sample_rate)
        write_wav(output_path, audio)
        return audio


@dataclass(slots=True)
class EdgeTTSSynthesizer:
    """Multilingual neural TTS through the optional ``edge-tts`` package."""

    user_voice: str = "ko-KR-InJoonNeural"
    assistant_voice: str = "ko-KR-SunHiNeural"
    sample_rate: int = 24000
    name: str = "edge-tts"

    def synthesize(self, text: str, speaker: str, output_path: Path) -> AudioBuffer:
        try:
            import edge_tts
        except ImportError as exc:
            raise RuntimeError(
                "edge-tts is not installed. Run: pip install -e '.[edge]'"
            ) from exc
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg is required by the edge TTS backend")

        voice = self.user_voice if speaker == "user" else self.assistant_voice
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="duplexforge-tts-") as tmp:
            mp3_path = Path(tmp) / "speech.mp3"

            async def render() -> None:
                await edge_tts.Communicate(text, voice).save(str(mp3_path))

            asyncio.run(render())
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(mp3_path),
                    "-ac",
                    "1",
                    "-ar",
                    str(self.sample_rate),
                    "-c:a",
                    "pcm_s16le",
                    str(output_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()}")
        return read_wav(output_path)


QWEN3_LANGUAGE_NAMES = {
    "ko": "Korean",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
}


@dataclass(slots=True)
class Qwen3TTSSynthesizer:
    """Qwen3-TTS VoiceDesign through the official PyTorch package."""

    language: str
    user_instruct: str
    assistant_instruct: str
    model_id: str = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    device: str = "cuda:0"
    attention: str = "auto"
    seed: int = 42
    name: str = "qwen3-tts-pytorch"

    _model_cache: ClassVar[dict[tuple[str, str, str], Any]] = {}

    def _load_model(self) -> Any:
        key = (self.model_id, self.device, self.attention)
        if key in self._model_cache:
            return self._model_cache[key]
        try:
            import torch
            from qwen_tts import Qwen3TTSModel
        except ImportError as exc:
            raise RuntimeError(
                "Qwen3-TTS is not installed. Run: pip install -e '.[qwen3-tts]'"
            ) from exc
        kwargs: dict[str, Any] = {
            "device_map": self.device,
            "dtype": torch.bfloat16,
        }
        if self.attention != "auto":
            kwargs["attn_implementation"] = self.attention
        model = Qwen3TTSModel.from_pretrained(self.model_id, **kwargs)
        self._model_cache[key] = model
        return model

    def synthesize(self, text: str, speaker: str, output_path: Path) -> AudioBuffer:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("PyTorch is required by the Qwen3-TTS backend") from exc
        model = self._load_model()
        line_seed = self.seed + sum(ord(char) for char in f"{speaker}:{text}")
        torch.manual_seed(line_seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(line_seed)
        instruct = self.user_instruct if speaker == "user" else self.assistant_instruct
        wavs, sample_rate = model.generate_voice_design(
            text=text,
            language=QWEN3_LANGUAGE_NAMES[self.language],
            instruct=instruct,
        )
        waveform = wavs[0]
        if hasattr(waveform, "detach"):
            waveform = waveform.detach().float().cpu().numpy()
        if hasattr(waveform, "reshape"):
            waveform = waveform.reshape(-1)
        audio = AudioBuffer(
            array("h", (_clip16(round(float(value) * 32767)) for value in waveform)),
            int(sample_rate),
        )
        write_wav(output_path, audio)
        return audio


@dataclass(slots=True)
class Qwen3EdgeLLMSynthesizer:
    """Qwen3-TTS VoiceDesign through NVIDIA TensorRT Edge-LLM."""

    language: str
    user_instruct: str
    assistant_instruct: str
    binary: Path
    engine_dir: Path
    checkpoint_dir: Path
    name: str = "qwen3-tts-tensorrt-edge-llm"

    def synthesize(self, text: str, speaker: str, output_path: Path) -> AudioBuffer:
        return self.synthesize_batch([(text, speaker, output_path)])[0]

    def synthesize_batch(
        self, requests: list[tuple[str, str, Path]]
    ) -> list[AudioBuffer]:
        import json

        if not self.binary.is_file():
            raise RuntimeError(f"TensorRT Edge-LLM TTS binary not found: {self.binary}")
        missing = [
            name for name in ("talker", "code2wav")
            if not (self.engine_dir / name).exists()
        ]
        if missing:
            raise RuntimeError(
                f"missing engine components in {self.engine_dir}: "
                + ", ".join(missing)
            )
        for _, _, path in requests:
            path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="duplexforge-edgellm-") as tmp:
            tmp_dir = Path(tmp)
            input_path = tmp_dir / "input.json"
            audio_dir = tmp_dir / "audio"
            audio_dir.mkdir()
            payload = {
                "batch_size": len(requests),
                "enable_thinking": False,
                "requests": [
                    {
                        "messages": [{"role": "user", "content": text}],
                        "language": QWEN3_LANGUAGE_NAMES[self.language],
                        "instruct": self.user_instruct
                        if speaker == "user"
                        else self.assistant_instruct,
                    }
                    for text, speaker, _ in requests
                ],
            }
            input_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            command = [
                str(self.binary),
                f"--talkerEngineDir={self.engine_dir / 'talker'}",
                f"--code2wavEngineDir={self.engine_dir / 'code2wav'}",
                f"--tokenizerDir={self.engine_dir / 'talker'}",
                f"--checkpointDir={self.checkpoint_dir}",
                f"--inputFile={input_path}",
                f"--outputAudioDir={audio_dir}",
                f"--batchSize={len(requests)}",
            ]
            clone_dir = self.engine_dir / "clone_encoders"
            if clone_dir.exists():
                command.append(f"--cloneEncoderDir={clone_dir}")
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise RuntimeError(f"TensorRT Edge-LLM TTS failed: {detail}")
            output: list[AudioBuffer] = []
            for index, (_, _, destination) in enumerate(requests):
                generated = audio_dir / f"audio_req{index}.wav"
                if not generated.exists():
                    raise RuntimeError(f"TensorRT Edge-LLM did not create {generated.name}")
                shutil.copyfile(generated, destination)
                output.append(read_wav(destination))
            return output
