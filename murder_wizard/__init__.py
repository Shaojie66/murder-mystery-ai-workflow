"""Murder Wizard - AI-powered murder mystery game generator."""

from .state import WizardState
from .generator import generate_with_llm
from .phase_runner import PhaseRunner
from .prompts.loader import PromptLoader

__all__ = [
    "WizardState",
    "generate_with_llm",
    "PhaseRunner",
    "PromptLoader",
]

__version__ = "0.2.0"
