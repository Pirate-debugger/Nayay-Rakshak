"""NYAYA RAKSHAK - Legal Q&A Engine Package."""

from app.services.qa_engine.classifier import qa_classifier
from app.services.qa_engine.engine import qa_engine
from app.services.qa_engine.hedging import qa_hedging_gate
from app.services.qa_engine.localizer import qa_localizer

__all__ = [
    "qa_classifier",
    "qa_engine",
    "qa_hedging_gate",
    "qa_localizer",
]
