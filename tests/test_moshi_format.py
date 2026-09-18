import json
import tempfile
import unittest
import wave
from pathlib import Path

from duplexforge.pipeline import GenerationConfig, generate_dataset


class MoshiFormatIntegrationTests(unittest.TestCase):
    def test_sphn_contract_and_adjacent_transcript(self):
        """Structural integration test for current moshi-finetune input contract."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            generate_dataset(GenerationConfig(
                goal="한국어 테스트", output_dir=root, count=1,
                patterns=("overlap",), dialogue_backend="template", tts_backend="tone",
            ))
            row = json.loads((root / "moshi.jsonl").read_text().strip())
            wav_path = Path(row["path"])
            self.assertTrue(wav_path.with_suffix(".json").is_file())
            with wave.open(str(wav_path), "rb") as wav:
                self.assertEqual(wav.getnchannels(), 2)
                self.assertAlmostEqual(row["duration"], wav.getnframes() / wav.getframerate(), places=3)
            alignments = json.loads(wav_path.with_suffix(".json").read_text())["alignments"]
            self.assertEqual(alignments, sorted(alignments, key=lambda value: value[1][0]))
            self.assertTrue(all(len(value) == 3 for value in alignments))


if __name__ == "__main__":
    unittest.main()
