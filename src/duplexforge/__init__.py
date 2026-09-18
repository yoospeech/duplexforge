"""DuplexForge: goal-to-audio full-duplex dialogue dataset generation."""

from .models import DialoguePlan, Event, Timing
from .pipeline import GenerationConfig, generate_dataset

__all__ = [
    "DialoguePlan",
    "Event",
    "Timing",
    "GenerationConfig",
    "generate_dataset",
]

__version__ = "0.1.0"
