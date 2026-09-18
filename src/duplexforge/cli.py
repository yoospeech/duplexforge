from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audio import EDGE_VOICE_POOLS
from .dialogue import LANGUAGES, PATTERNS
from .pipeline import GenerationConfig, generate_dataset
from .validation import validate_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="duplexforge",
        description="목적 한 줄에서 full-duplex 음성·텍스트 데이터셋을 생성합니다.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="데이터셋 생성")
    generate.add_argument("--goal", required=True, help="대화가 달성할 목적")
    generate.add_argument(
        "--language",
        choices=LANGUAGES,
        default="ko",
        help="대화 언어: ko(한국어), en(영어), es(스페인어), fr(프랑스어)",
    )
    generate.add_argument("--output", type=Path, required=True, help="출력 디렉터리")
    amount = generate.add_mutually_exclusive_group(required=True)
    amount.add_argument("--target-hours", type=float, help="누적 대화 시간 목표")
    amount.add_argument(
        "--count", type=int, help="debug/호환용 고정 대화 수"
    )
    generate.add_argument(
        "--patterns",
        default="",
        help=(
            f"쉼표로 구분한 고정 순환 패턴: {','.join(PATTERNS)}. "
            "미지정 시 configs/default.yaml과 같은 기본 확률 분포 사용"
        ),
    )
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument(
        "--dialogue-backend",
        choices=("template", "openai", "trtllm"),
        default="trtllm",
    )
    generate.add_argument(
        "--tts-backend",
        choices=("tone", "edge", "qwen3", "qwen3-edgellm"),
        default="qwen3",
    )
    generate.add_argument("--model", default="nvidia/Qwen3-8B-FP8")
    generate.add_argument("--base-url", default="http://localhost:8000/v1")
    generate.add_argument("--api-key", help="미지정 시 OPENAI_API_KEY 사용")
    generate.add_argument("--user-voice", help="미지정 시 언어별 기본 화자")
    generate.add_argument(
        "--assistant-voice",
        help=(
            "Edge backend에서는 voice ID, Qwen3 backend에서는 전체 데이터셋에 "
            "고정할 VoiceDesign instruction"
        ),
    )
    generate.add_argument(
        "--qwen-tts-model",
        default="Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
    )
    generate.add_argument("--qwen-tts-device", default="cuda:0")
    generate.add_argument(
        "--qwen-tts-attention",
        choices=("auto", "sdpa", "flash_attention_2"),
        default="auto",
    )
    generate.add_argument(
        "--edgellm-binary", type=Path,
        default=Path("TensorRT-Edge-LLM/build/examples/omni/qwen3_tts_inference"),
    )
    generate.add_argument(
        "--edgellm-engine-dir", type=Path,
        default=Path("engines/Qwen3-TTS-12Hz-1.7B-VoiceDesign"),
    )
    generate.add_argument(
        "--qwen-tts-checkpoint", type=Path,
        default=Path("models/Qwen3-TTS-12Hz-1.7B-VoiceDesign"),
    )
    generate.add_argument(
        "--voice-strategy",
        choices=("random", "fixed"),
        default="random",
        help="샘플별 화자 선택 방식(기본: random)",
    )
    generate.add_argument(
        "--discard-event-audio",
        action="store_true",
        help="최종 트랙 생성 후 event별 임시 WAV 삭제",
    )
    inspect = subparsers.add_parser("inspect", help="metadata.json 요약 출력")
    inspect.add_argument("metadata", type=Path)
    validate = subparsers.add_parser("validate", help="생성 데이터셋 무결성 검사")
    validate.add_argument("dataset", type=Path)
    voices = subparsers.add_parser("voices", help="내장 Edge TTS 화자 풀 출력")
    voices.add_argument("--language", choices=LANGUAGES)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            patterns = tuple(item.strip() for item in args.patterns.split(",") if item.strip())
            config = GenerationConfig(
                goal=args.goal,
                output_dir=args.output,
                language=args.language,
                count=args.count,
                target_duration_hours=args.target_hours,
                patterns=patterns,
                seed=args.seed,
                dialogue_backend=args.dialogue_backend,
                tts_backend=args.tts_backend,
                model=args.model,
                base_url=args.base_url,
                api_key=args.api_key,
                user_voice=args.user_voice,
                assistant_voice=args.assistant_voice,
                qwen_tts_model=args.qwen_tts_model,
                qwen_tts_device=args.qwen_tts_device,
                qwen_tts_attention=args.qwen_tts_attention,
                edgellm_binary=args.edgellm_binary,
                edgellm_engine_dir=args.edgellm_engine_dir,
                qwen_tts_checkpoint=args.qwen_tts_checkpoint,
                voice_strategy=args.voice_strategy,
                keep_event_audio=not args.discard_event_audio,
            )
            records = generate_dataset(config)
            total_ms = sum(record["duration_ms"] for record in records)
            print(
                f"생성 완료: {len(records)}개, {total_ms / 3_600_000:.4f}시간, "
                f"{args.output.resolve()}"
            )
            return 0
        if args.command == "inspect":
            payload = json.loads(args.metadata.read_text(encoding="utf-8"))
            print(f"goal: {payload['goal']}")
            print(f"scenario: {payload['scenario']}")
            print(f"duration: {payload['duration_ms'] / 1000:.3f}s")
            for event in sorted(payload["events"], key=lambda item: item["start_ms"]):
                print(
                    f"{event['start_ms'] / 1000:7.3f}-"
                    f"{event['end_ms'] / 1000:7.3f} "
                    f"{event['speaker']:9} {event['event_type']:16} {event['text']}"
                )
            return 0
        if args.command == "validate":
            report = validate_dataset(args.dataset)
            if report.statistics:
                print(json.dumps(report.statistics, ensure_ascii=False, indent=2))
            if report.ok:
                print(f"검증 통과: {report.sample_count}개 샘플")
                return 0
            print(
                f"검증 실패: {report.sample_count}개 샘플, "
                f"{len(report.issues)}개 문제",
                file=sys.stderr,
            )
            for issue in report.issues:
                print(f"- {issue.sample_id}: {issue.message}", file=sys.stderr)
            return 1
        if args.command == "voices":
            languages = (args.language,) if args.language else LANGUAGES
            for language in languages:
                print(f"[{language}]")
                for voice in EDGE_VOICE_POOLS[language]:
                    print(f"  {voice.id:38} {voice.gender:6} {voice.locale}")
            return 0
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
