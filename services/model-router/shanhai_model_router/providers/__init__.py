"""Provider 包。"""

from shanhai_model_router.providers.base import CompletionResult, ModelProvider
from shanhai_model_router.providers.mock import MockProvider

__all__ = ["CompletionResult", "ModelProvider", "MockProvider"]
