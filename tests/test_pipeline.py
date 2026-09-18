import json
import tempfile
import unittest
import wave
from pathlib import Path

from duplexforge.audio import EDGE_VOICE_POOLS
from duplexforge.pipeline import GenerationConfig, _select_voices, generate_dataset
<<<<<<< HEAD
from duplexforge.pipeline import _select_qwen3_voices
=======
>>>>>>> origin/main


class PipelineTests(unittest.TestCase):
    def test_pipeline_creates_audio_text_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            records = generate_dataset(
                GenerationConfig(
                    goal="식당 예약하기",
                    output_dir=output,
                    count=4,
                    tts_backend="tone",
                    dialogue_backend="template",
                )
            )
            self.assertEqual(len(records), 4)
            self.assertTrue((output / "manifest.jsonl").exists())

            for record in records:
                sample = output / record["id"]
                metadata = json.loads(
                    (sample / "metadata.json").read_text(encoding="utf-8")
                )
                self.assertEqual(metadata["goal"], "식당 예약하기")
                self.assertTrue(metadata["events"])
                self.assertTrue((sample / "transcript.txt").exists())
                for filename in ("user.wav", "assistant.wav", "mixed.wav"):
                    with wave.open(str(sample / filename), "rb") as wav:
                        self.assertEqual(wav.getnchannels(), 1)
                        self.assertEqual(wav.getsampwidth(), 2)
                        self.assertGreater(wav.getnframes(), 0)
<<<<<<< HEAD
                with wave.open(str(sample / "moshi.wav"), "rb") as wav:
                    self.assertEqual(wav.getnchannels(), 2)
                    self.assertEqual(wav.getframerate(), 24000)
                transcript = json.loads(
                    (sample / "moshi.json").read_text(encoding="utf-8")
                )
                self.assertTrue(transcript["alignments"])
                self.assertIn(
                    "SPEAKER_MAIN",
                    {item[2] for item in transcript["alignments"]},
                )
            moshi_records = [
                json.loads(line)
                for line in (output / "moshi.jsonl").read_text().splitlines()
            ]
            self.assertEqual(len(moshi_records), 4)
            self.assertEqual(set(moshi_records[0]), {"path", "duration"})

    def test_barge_in_truncates_assistant_after_stop_latency(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            generate_dataset(
                GenerationConfig(
                    goal="예약 내용 수정하기",
                    output_dir=output,
                    count=1,
                    patterns=("barge_in",),
                    dialogue_backend="template",
                    tts_backend="tone",
                )
            )
            metadata = json.loads(
                (output / "sample_000000" / "metadata.json").read_text()
            )
            assistant = next(e for e in metadata["events"] if e["id"] == "e2")
            barge_in = next(e for e in metadata["events"] if e["id"] == "e3")
            self.assertTrue(assistant["metadata"]["barge_in_truncated"])
            self.assertEqual(
                assistant["end_ms"],
                barge_in["start_ms"] + barge_in["metadata"]["stop_latency_ms"],
            )
=======
>>>>>>> origin/main

    def test_interruption_is_rendered_as_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            generate_dataset(
                GenerationConfig(
                    goal="호텔 체크인하기",
                    output_dir=output,
                    count=1,
                    patterns=("interruption",),
                    dialogue_backend="template",
                    tts_backend="tone",
                )
            )
            metadata = json.loads(
                (output / "sample_000000" / "metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            assistant = next(
                item for item in metadata["events"] if item["id"] == "e2"
            )
            interruption = next(
                item for item in metadata["events"] if item["id"] == "e3"
            )
            self.assertLess(assistant["start_ms"], interruption["start_ms"])
            self.assertLess(interruption["start_ms"], assistant["end_ms"])

    def test_discard_event_audio_updates_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            generate_dataset(
                GenerationConfig(
                    goal="호텔 체크인하기",
                    output_dir=output,
                    count=1,
                    keep_event_audio=False,
                    dialogue_backend="template",
                    tts_backend="tone",
                )
            )
            sample = output / "sample_000000"
            metadata = json.loads(
                (sample / "metadata.json").read_text(encoding="utf-8")
            )
            self.assertFalse((sample / "events").exists())
            self.assertTrue(all(not item["audio_path"] for item in metadata["events"]))

    def test_language_is_written_to_manifest_and_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            records = generate_dataset(
                GenerationConfig(
                    goal="reservar una mesa",
                    language="es",
                    output_dir=output,
                    count=1,
                    dialogue_backend="template",
                    tts_backend="tone",
                )
            )
            metadata = json.loads(
                (output / "sample_000000" / "metadata.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(records[0]["language"], "es")
            self.assertEqual(metadata["language"], "es")
            self.assertIn("¿", metadata["events"][0]["text"])

    def test_random_strategy_covers_every_voice_per_epoch(self):
        for language, pool in EDGE_VOICE_POOLS.items():
            config = GenerationConfig(
                goal="test",
                output_dir=Path("unused"),
                language=language,
                dialogue_backend="template",
            )
            pairs = [_select_voices(config, index) for index in range(len(pool))]
            self.assertEqual({pair[0].id for pair in pairs}, {v.id for v in pool})
            self.assertEqual({pair[1].id for pair in pairs}, {v.id for v in pool})
            self.assertTrue(all(user.id != assistant.id for user, assistant in pairs))
            self.assertEqual(pairs, [_select_voices(config, i) for i in range(len(pool))])

<<<<<<< HEAD
    def test_qwen_assistant_is_fixed_while_users_vary(self):
        config = GenerationConfig(goal="test", output_dir=Path("unused"))
        first = _select_qwen3_voices(config, 0)
        second = _select_qwen3_voices(config, 1)
        self.assertNotEqual(first[0]["instruct"], second[0]["instruct"])
        self.assertEqual(first[1], second[1])

    def test_qwen_configured_assistant_instruction_is_fixed(self):
        instruction = "A warm Korean woman in her thirties with a clear calm voice."
        config = GenerationConfig(
            goal="test", output_dir=Path("unused"), assistant_voice=instruction
        )
        self.assertEqual(_select_qwen3_voices(config, 9)[1]["instruct"], instruction)

    def test_target_hours_stops_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "target"
            config = GenerationConfig(
                goal="시간 목표",
                output_dir=output,
                count=None,
                target_duration_hours=0.001,
                dialogue_backend="template",
                tts_backend="tone",
            )
            first = generate_dataset(config)
            self.assertGreaterEqual(sum(item["duration"] for item in first), 3.6)
            second = generate_dataset(config)
            self.assertEqual(first, second)

=======
>>>>>>> origin/main

if __name__ == "__main__":
    unittest.main()
