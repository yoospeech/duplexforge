import unittest

from duplexforge.models import DialoguePlan, Event, Timing


class ModelTests(unittest.TestCase):
    def test_rejects_forward_anchor(self):
        plan = DialoguePlan(
            goal="테스트",
            scenario="invalid",
            events=[
                Event("e1", "user", "질문", timing=Timing("e2", "end", 0)),
                Event("e2", "assistant", "답변"),
            ],
        )
        with self.assertRaisesRegex(ValueError, "earlier event"):
            plan.validate()

    def test_round_trip(self):
        plan = DialoguePlan(
            goal="여행 계획",
            scenario="normal",
            events=[
                Event("e1", "user", "도와주세요."),
                Event("e2", "assistant", "네.", timing=Timing("e1", "end", 200)),
            ],
        )
        restored = DialoguePlan.from_dict(plan.to_dict())
        self.assertEqual(restored.to_dict(), plan.to_dict())


if __name__ == "__main__":
    unittest.main()
