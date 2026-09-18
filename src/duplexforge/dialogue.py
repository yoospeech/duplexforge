from __future__ import annotations

import json
import random
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .models import DialoguePlan, Event, Timing


<<<<<<< HEAD
PATTERNS = (
    "normal",
    "overlap",
    "interruption",
    "barge_in",
    "backchannel",
    "hesitation",
)
=======
PATTERNS = ("normal", "backchannel", "interruption", "pause")
>>>>>>> origin/main
LANGUAGES = ("ko", "en", "es", "fr")
LANGUAGE_NAMES = {
    "ko": "Korean",
    "en": "English",
    "es": "Spanish",
    "fr": "French",
}

TEMPLATES = {
    "ko": {
        "normal_questions": [
            "'{goal}'라는 목표가 있는데 어디서부터 시작하면 좋을까요?",
            "'{goal}'에 관해 핵심만 간단히 알려주세요.",
        ],
        "normal_answers": [
            "좋아요. '{goal}'를 위해 먼저 원하는 결과와 제약 조건을 정리해 보세요. 그다음 작은 단계부터 하나씩 확인하면 됩니다.",
            "'{goal}'에서 중요한 것은 목표를 구체화하는 일입니다. 필요한 조건을 적고 우선순위를 정한 뒤 실행 가능한 첫 단계부터 시작하세요.",
        ],
        "back_question": "'{goal}'를 잘 진행하는 방법을 설명해 주세요.",
        "back_answer": "먼저 '{goal}'의 성공 기준을 정하고, 필요한 자료와 제약 조건을 확인하는 것이 좋습니다.",
        "backchannels": ["네.", "음, 그렇군요.", "알겠어요."],
        "back_resume": "그다음 결과를 작은 단위로 검토하면서 부족한 부분을 보완하면 됩니다.",
        "interrupt_question": "'{goal}'에 대해 자세히 설명해 주세요.",
        "interrupt_lead": "'{goal}'를 체계적으로 이해하려면 먼저 배경과 여러 조건을 살펴봐야 하는데",
        "corrections": [
            "잠깐만요. 설명보다 바로 실행할 수 있는 예시가 필요해요.",
            "아니요, 초보자가 할 수 있는 방법으로 알려주세요.",
        ],
        "interrupt_answer": "알겠습니다. 가장 간단한 예시는 '{goal}'에 해당하는 결과 하나를 정하고, 오늘 할 수 있는 첫 작업을 바로 수행하는 것입니다.",
        "pause_first": "제가 '{goal}'를 해보려고 하는데",
        "pause_second": "처음이라서 가장 쉬운 순서부터 알고 싶어요.",
        "pause_answer": "그렇다면 '{goal}'의 전체 범위를 한꺼번에 다루지 말고, 가장 작은 예제를 먼저 완성해 보세요.",
    },
    "en": {
        "normal_questions": [
            "My goal is '{goal}'. Where should I start?",
            "Could you briefly explain the key points of '{goal}'?",
        ],
        "normal_answers": [
            "Sure. For '{goal}', first define the desired outcome and constraints. Then work through one small step at a time.",
            "The key to '{goal}' is making the objective specific. List the requirements, prioritize them, and begin with the first actionable step.",
        ],
        "back_question": "Please explain how to approach '{goal}' effectively.",
        "back_answer": "First, define what success means for '{goal}', then identify the resources and constraints involved.",
        "backchannels": ["Right.", "Mm-hm.", "Got it."],
        "back_resume": "Then review the result in small pieces and improve anything that is still missing.",
        "interrupt_question": "Please explain '{goal}' in detail.",
        "interrupt_lead": "To understand '{goal}' systematically, we first need to consider the background and several conditions, but",
        "corrections": [
            "Wait. I need an example I can use right away, not a long explanation.",
            "No, please explain it in a way a beginner can follow.",
        ],
        "interrupt_answer": "Understood. The simplest example is to choose one concrete outcome for '{goal}' and complete one task you can do today.",
        "pause_first": "I'm trying to work on '{goal}', but",
        "pause_second": "I'm new to it, so I'd like to know the easiest order to follow.",
        "pause_answer": "In that case, don't tackle all of '{goal}' at once. Complete the smallest possible example first.",
    },
    "es": {
        "normal_questions": [
            "Mi objetivo es '{goal}'. ¿Por dónde debería empezar?",
            "¿Puedes explicarme brevemente los puntos clave de '{goal}'?",
        ],
        "normal_answers": [
            "Claro. Para '{goal}', primero define el resultado deseado y las limitaciones. Después, avanza paso a paso.",
            "La clave de '{goal}' es concretar el objetivo. Anota los requisitos, establece prioridades y empieza por la primera acción posible.",
        ],
        "back_question": "Explícame cómo abordar '{goal}' de manera eficaz.",
        "back_answer": "Primero, define qué significa tener éxito en '{goal}' y luego identifica los recursos y las limitaciones.",
        "backchannels": ["Sí.", "Ajá.", "Entiendo."],
        "back_resume": "Después, revisa el resultado en partes pequeñas y mejora lo que todavía falte.",
        "interrupt_question": "Explícame '{goal}' con detalle.",
        "interrupt_lead": "Para entender '{goal}' de forma sistemática, primero debemos considerar el contexto y varias condiciones, pero",
        "corrections": [
            "Espera. Necesito un ejemplo que pueda usar ahora, no una explicación larga.",
            "No, explícamelo de una forma que pueda seguir un principiante.",
        ],
        "interrupt_answer": "Entendido. El ejemplo más sencillo es elegir un resultado concreto para '{goal}' y completar hoy una primera tarea.",
        "pause_first": "Estoy intentando trabajar en '{goal}', pero",
        "pause_second": "soy principiante y quiero saber cuál es el orden más sencillo.",
        "pause_answer": "En ese caso, no intentes abarcar todo '{goal}' a la vez. Completa primero el ejemplo más pequeño posible.",
    },
    "fr": {
        "normal_questions": [
            "Mon objectif est « {goal} ». Par où dois-je commencer ?",
            "Pouvez-vous m'expliquer brièvement les points clés de « {goal} » ?",
        ],
        "normal_answers": [
            "Bien sûr. Pour « {goal} », définissez d'abord le résultat attendu et les contraintes. Avancez ensuite étape par étape.",
            "Pour « {goal} », l'essentiel est de préciser l'objectif. Notez les besoins, fixez les priorités et commencez par une première action concrète.",
        ],
        "back_question": "Expliquez-moi comment aborder efficacement « {goal} ».",
        "back_answer": "Commencez par définir la réussite de « {goal} », puis identifiez les ressources et les contraintes.",
        "backchannels": ["Oui.", "Hum-hum.", "D'accord."],
        "back_resume": "Examinez ensuite le résultat par petites parties et améliorez ce qui manque encore.",
        "interrupt_question": "Expliquez-moi « {goal} » en détail.",
        "interrupt_lead": "Pour comprendre « {goal} » méthodiquement, il faut d'abord examiner le contexte et plusieurs conditions, mais",
        "corrections": [
            "Attendez. J'ai besoin d'un exemple utilisable tout de suite, pas d'une longue explication.",
            "Non, expliquez-le d'une manière accessible à un débutant.",
        ],
        "interrupt_answer": "Compris. L'exemple le plus simple consiste à choisir un résultat concret pour « {goal} » et à réaliser aujourd'hui une première tâche.",
        "pause_first": "J'essaie de travailler sur « {goal} », mais",
        "pause_second": "je débute et j'aimerais connaître l'ordre le plus simple.",
        "pause_answer": "Dans ce cas, n'abordez pas tout « {goal} » à la fois. Réalisez d'abord le plus petit exemple possible.",
    },
}


class DialogueGenerator(Protocol):
    def generate(self, goal: str, pattern: str, index: int) -> DialoguePlan: ...


@dataclass(slots=True)
class TemplateDialogueGenerator:
    """Offline multilingual generator for demos, tests, and smoke checks."""

    seed: int = 42
    language: str = "ko"

    def generate(self, goal: str, pattern: str, index: int) -> DialoguePlan:
        if pattern not in PATTERNS:
            raise ValueError(f"unknown pattern: {pattern}")
        if self.language not in LANGUAGES:
            raise ValueError(f"unsupported language: {self.language}")
        rng = random.Random(f"{self.seed}:{index}:{goal}:{pattern}:{self.language}")
        method = getattr(self, f"_{pattern}")
        plan = method(goal.strip(), rng, TEMPLATES[self.language])
        plan.language = self.language
        plan.metadata.update({"generator": "template", "pattern": pattern})
        plan.validate()
        return plan

    @staticmethod
    def _normal(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        return DialoguePlan(
            goal=goal,
            scenario="normal_qa",
            events=[
                Event(
                    "e1",
                    "user",
                    rng.choice(text["normal_questions"]).format(goal=goal),
                    timing=Timing(offset_ms=0),
                ),
                Event(
                    "e2",
                    "assistant",
                    rng.choice(text["normal_answers"]).format(goal=goal),
                    timing=Timing("e1", "end", 280),
                ),
            ],
        )

    @staticmethod
    def _backchannel(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        bc = rng.choice(text["backchannels"])
        return DialoguePlan(
            goal=goal,
            scenario="listener_backchannel",
            events=[
                Event(
                    "e1",
                    "user",
                    text["back_question"].format(goal=goal),
                    timing=Timing(offset_ms=0),
                ),
                Event(
                    "e2",
                    "assistant",
                    text["back_answer"].format(goal=goal),
                    timing=Timing("e1", "end", 250),
                ),
                Event(
                    "e3",
                    "user",
                    bc,
                    event_type="backchannel",
                    timing=Timing("e2", "end", -650),
                    metadata={"expected_action": "continue_speaking"},
                ),
                Event(
                    "e4",
                    "assistant",
                    text["back_resume"].format(goal=goal),
                    event_type="resume",
                    timing=Timing("e2", "end", 60),
                ),
            ],
        )

    @staticmethod
<<<<<<< HEAD
    def _overlap(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        return DialoguePlan(
            goal=goal,
            scenario="cooperative_overlap",
            events=[
                Event(
                    "e1", "user", text["interrupt_question"].format(goal=goal)
                ),
                Event(
                    "e2",
                    "assistant",
                    text["interrupt_lead"].format(goal=goal),
                    timing=Timing("e1", "end", rng.randint(120, 420)),
                ),
                Event(
                    "e3",
                    "user",
                    rng.choice(text["corrections"]),
                    event_type="overlap",
                    timing=Timing("e2", "end", -rng.randint(350, 750)),
                    metadata={"expected_action": "continue_speaking"},
                ),
            ],
        )

    @staticmethod
=======
>>>>>>> origin/main
    def _interruption(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        correction = rng.choice(text["corrections"])
        return DialoguePlan(
            goal=goal,
            scenario="semantic_interruption",
            events=[
                Event(
                    "e1",
                    "user",
                    text["interrupt_question"].format(goal=goal),
                    timing=Timing(offset_ms=0),
                ),
                Event(
                    "e2",
                    "assistant",
                    text["interrupt_lead"].format(goal=goal),
                    timing=Timing("e1", "end", 240),
                    metadata={"truncated": True},
                ),
                Event(
                    "e3",
                    "user",
                    correction,
                    event_type="interruption",
                    timing=Timing("e2", "end", -480),
                    metadata={"expected_action": "stop_and_listen"},
                ),
                Event(
                    "e4",
                    "assistant",
                    text["interrupt_answer"].format(goal=goal),
                    timing=Timing("e3", "end", 230),
                ),
            ],
        )

    @staticmethod
<<<<<<< HEAD
    def _barge_in(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        stop_latency = rng.randint(80, 500)
        return DialoguePlan(
            goal=goal,
            scenario="barge_in_stop",
            events=[
                Event(
                    "e1", "user", text["interrupt_question"].format(goal=goal)
                ),
                Event(
                    "e2",
                    "assistant",
                    text["interrupt_lead"].format(goal=goal),
                    timing=Timing("e1", "end", rng.randint(100, 350)),
                ),
                Event(
                    "e3",
                    "user",
                    rng.choice(text["corrections"]),
                    event_type="barge_in",
                    timing=Timing("e2", "end", -rng.randint(450, 850)),
                    metadata={
                        "expected_action": "stop_and_listen",
                        "stop_latency_ms": stop_latency,
                    },
                ),
                Event(
                    "e4",
                    "assistant",
                    text["interrupt_answer"].format(goal=goal),
                    timing=Timing("e3", "end", rng.randint(100, 500)),
                ),
            ],
        )

    @staticmethod
    def _hesitation(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
=======
    def _pause(goal: str, rng: random.Random, text: dict) -> DialoguePlan:
        del rng
>>>>>>> origin/main
        return DialoguePlan(
            goal=goal,
            scenario="mid_utterance_pause",
            events=[
                Event(
                    "e1",
                    "user",
                    text["pause_first"].format(goal=goal),
<<<<<<< HEAD
                    event_type="hesitation",
=======
                    event_type="pause_fragment",
>>>>>>> origin/main
                    timing=Timing(offset_ms=0),
                    metadata={"expected_action": "continue_listening"},
                ),
                Event(
                    "e2",
                    "user",
                    text["pause_second"].format(goal=goal),
                    event_type="pause_fragment",
<<<<<<< HEAD
                    timing=Timing("e1", "end", rng.randint(350, 1200)),
=======
                    timing=Timing("e1", "end", 900),
>>>>>>> origin/main
                ),
                Event(
                    "e3",
                    "assistant",
                    text["pause_answer"].format(goal=goal),
                    timing=Timing("e2", "end", 260),
                ),
            ],
        )


SYSTEM_PROMPT = """You are an expert in designing full-duplex spoken-dialogue training data.
Create one natural two-person dialogue in the requested language, goal, and pattern.
Return only a JSON object. Events are in reference order, and each timing.anchor_id must refer to an earlier event.
스키마:
{
  "goal": "string", "scenario": "string", "language": "ko|en|es|fr",
  "events": [{
    "id": "e1", "speaker": "user|assistant", "text": "string",
<<<<<<< HEAD
    "event_type": "normal|overlap|backchannel|interruption|barge_in|hesitation|pause_fragment|resume",
=======
    "event_type": "normal|backchannel|interruption|pause_fragment|resume",
>>>>>>> origin/main
    "timing": {"anchor_id": null or "earlier event id", "anchor_point": "start|end", "offset_ms": integer},
    "metadata": {"expected_action": "optional string"}
  }]
}
Set the first event to anchor_id=null and offset_ms=0. Create overlap with a negative offset from the other event's end.
<<<<<<< HEAD
For a backchannel or overlap, the other speaker should continue speaking. For an interruption, the other speaker keeps its full waveform; for barge_in, set stop_latency_ms and the assistant stops. Keep every event short and speakable."""
=======
For a backchannel, the other speaker should continue speaking. For an interruption, the other speaker should stop and listen. Keep every event short and speakable."""
>>>>>>> origin/main


@dataclass(slots=True)
class OpenAICompatibleDialogueGenerator:
    api_key: str
    model: str
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: int = 120
    language: str = "ko"
    use_response_format: bool = True
    non_thinking: bool = False

    def generate(self, goal: str, pattern: str, index: int) -> DialoguePlan:
        del index
        body = {
            "model": self.model,
            "temperature": 0.8,
            "max_tokens": 2048,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Language: {LANGUAGE_NAMES[self.language]} ({self.language})\n"
                        f"Goal: {goal}\nPattern: {pattern}\nGenerate the dialogue."
                        + ("\n/no_think" if self.non_thinking else "")
                    ),
                },
            ],
        }
        if self.use_response_format:
            body["response_format"] = {"type": "json_object"}
        url = self.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc.reason}") from exc

        content = payload["choices"][0]["message"]["content"]
        raw = _extract_json(content)
        raw["goal"] = goal
        raw["language"] = self.language
        plan = DialoguePlan.from_dict(raw)
        plan.metadata.update(
            {"generator": "openai-compatible", "model": self.model, "pattern": pattern}
        )
        return plan


def _extract_json(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        value = json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise ValueError("LLM response did not contain a JSON object")
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value
