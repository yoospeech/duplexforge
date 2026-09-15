import unittest
from unittest.mock import MagicMock, patch

from duplexforge.dialogue import (
    LANGUAGES,
    PATTERNS,
    OpenAICompatibleDialogueGenerator,
    TemplateDialogueGenerator,
)


class DialogueTests(unittest.TestCase):
    def test_all_template_patterns_are_valid(self):
        generator = TemplateDialogueGenerator(seed=7)
        for index, pattern in enumerate(PATTERNS):
            plan = generator.generate("카페에서 음료 주문하기", pattern, index)
            plan.validate()
            self.assertEqual(plan.goal, "카페에서 음료 주문하기")
            self.assertEqual(
                {event.speaker for event in plan.events}, {"user", "assistant"}
            )

    def test_backchannel_has_negative_end_offset(self):
        plan = TemplateDialogueGenerator().generate(
            "운동 계획 세우기", "backchannel", 0
        )
        backchannel = next(
            event for event in plan.events if event.event_type == "backchannel"
        )
        self.assertEqual(backchannel.timing.anchor_point, "end")
        self.assertLess(backchannel.timing.offset_ms, 0)

    def test_every_language_and_pattern(self):
        goals = {
            "ko": "호텔 예약하기",
            "en": "book a hotel",
            "es": "reservar un hotel",
            "fr": "réserver un hôtel",
        }
        for language in LANGUAGES:
            generator = TemplateDialogueGenerator(seed=3, language=language)
            for index, pattern in enumerate(PATTERNS):
                plan = generator.generate(goals[language], pattern, index)
                self.assertEqual(plan.language, language)
                self.assertTrue(all(event.text for event in plan.events))

    @patch("duplexforge.dialogue.urllib.request.urlopen")
    def test_openai_compatible_response_is_parsed(self, urlopen):
        response = MagicMock()
        response.read.return_value = (
            b'{"choices":[{"message":{"content":"{\\"goal\\":\\"x\\",'
            b'\\"scenario\\":\\"normal\\",\\"language\\":\\"ko\\",'
            b'\\"events\\":[{\\"id\\":\\"e1\\",\\"speaker\\":\\"user\\",'
            b'\\"text\\":\\"hello\\",\\"event_type\\":\\"normal\\",'
            b'\\"timing\\":{\\"anchor_id\\":null,\\"anchor_point\\":\\"end\\",'
            b'\\"offset_ms\\":0}}]}"}}]}'
        )
        urlopen.return_value.__enter__.return_value = response
        generator = OpenAICompatibleDialogueGenerator(
            api_key="test", model="local", base_url="http://localhost:8000/v1"
        )
        plan = generator.generate("테스트 목적", "normal", 0)
        self.assertEqual(plan.goal, "테스트 목적")
        self.assertEqual(plan.events[0].text, "hello")

    @patch("duplexforge.dialogue.urllib.request.urlopen")
    def test_trtllm_request_uses_non_thinking_without_response_format(self, urlopen):
        response = MagicMock()
        response.read.return_value = (
            b'{"choices":[{"message":{"content":"{\\"goal\\":\\"x\\",'
            b'\\"scenario\\":\\"normal\\",\\"language\\":\\"en\\",'
            b'\\"events\\":[{\\"id\\":\\"e1\\",\\"speaker\\":\\"user\\",'
            b'\\"text\\":\\"hello\\",\\"event_type\\":\\"normal\\",'
            b'\\"timing\\":{\\"anchor_id\\":null,\\"anchor_point\\":\\"end\\",'
            b'\\"offset_ms\\":0}}]}"}}]}'
        )
        urlopen.return_value.__enter__.return_value = response
        generator = OpenAICompatibleDialogueGenerator(
            api_key="test",
            model="nvidia/Qwen3-8B-FP8",
            language="en",
            use_response_format=False,
            non_thinking=True,
        )
        generator.generate("test", "normal", 0)
        request = urlopen.call_args.args[0]
        body = __import__("json").loads(request.data)
        self.assertNotIn("response_format", body)
        self.assertIn("/no_think", body["messages"][1]["content"])
        self.assertEqual(body["max_tokens"], 2048)


if __name__ == "__main__":
    unittest.main()
