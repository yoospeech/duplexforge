import json
import tempfile
import unittest
from array import array
from pathlib import Path
from unittest.mock import patch

from duplexforge.audio import AudioBuffer, Qwen3EdgeLLMSynthesizer, write_wav


class EdgeLLMTTSTests(unittest.TestCase):
    @patch("duplexforge.audio.subprocess.run")
    def test_batches_voice_design_requests(self, run):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "qwen3_tts_inference"
            binary.touch()
            engine = root / "engines"
            (engine / "talker").mkdir(parents=True)
            (engine / "code2wav").mkdir()
            captured = {}

            def fake_run(command, **kwargs):
                input_path = Path(next(x.split("=", 1)[1] for x in command if x.startswith("--inputFile=")))
                audio_dir = Path(next(x.split("=", 1)[1] for x in command if x.startswith("--outputAudioDir=")))
                captured.update(json.loads(input_path.read_text(encoding="utf-8")))
                for index in range(2):
                    write_wav(audio_dir / f"audio_req{index}.wav", AudioBuffer(array("h", [1] * 240), 24000))
                return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()

            run.side_effect = fake_run
            synth = Qwen3EdgeLLMSynthesizer(
                language="ko",
                user_instruct="young female",
                assistant_instruct="older male",
                binary=binary,
                engine_dir=engine,
                checkpoint_dir=root / "checkpoint",
            )
            outputs = [root / "a.wav", root / "b.wav"]
            audio = synth.synthesize_batch([
                ("안녕하세요", "user", outputs[0]),
                ("반갑습니다", "assistant", outputs[1]),
            ])

            self.assertEqual(len(audio), 2)
            self.assertEqual(captured["batch_size"], 2)
            self.assertEqual(captured["requests"][0]["language"], "Korean")
            self.assertEqual(captured["requests"][0]["instruct"], "young female")
            self.assertEqual(captured["requests"][1]["instruct"], "older male")
            self.assertTrue(all(path.exists() for path in outputs))


if __name__ == "__main__":
    unittest.main()
