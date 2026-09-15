import json
import tempfile
import unittest
import wave
from pathlib import Path

from duplexforge.audio import EDGE_VOICE_POOLS
from duplexforge.pipeline import GenerationConfig, _select_voices, generate_dataset


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


if __name__ == "__main__":
    unittest.main()
