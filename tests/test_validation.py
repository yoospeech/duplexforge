import tempfile
import unittest
from pathlib import Path

from duplexforge.pipeline import GenerationConfig, generate_dataset
from duplexforge.validation import validate_dataset


class ValidationTests(unittest.TestCase):
    def test_generated_dataset_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "dataset"
            generate_dataset(
                GenerationConfig(
                    goal="문의 처리하기",
                    output_dir=output,
                    count=4,
                    dialogue_backend="template",
                    tts_backend="tone",
                )
            )
            report = validate_dataset(output)
            self.assertTrue(report.ok, report.issues)
            self.assertEqual(report.sample_count, 4)

    def test_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_dataset(Path(tmp))
            self.assertFalse(report.ok)


if __name__ == "__main__":
    unittest.main()
