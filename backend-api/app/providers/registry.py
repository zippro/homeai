from __future__ import annotations

from app.providers.fal import FalProvider
from app.providers.mock import MockProvider
from app.providers.openai import OpenAIProvider


def get_provider_registry() -> dict[str, object]:
    """Create provider instances available to the orchestrator."""
    return {
        "fal": FalProvider(),
        "openai": OpenAIProvider(),
        "mock": MockProvider(),
    }
