from app.ai.base import BaseAIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.mock_provider import DeterministicMockAIProvider
from app.core.config import settings


def get_ai_provider() -> BaseAIProvider:
    """Factory function returning the configured legal intelligence provider."""
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        return GeminiProvider(api_key=settings.GEMINI_API_KEY, model_name=settings.GEMINI_MODEL)
    return DeterministicMockAIProvider()
