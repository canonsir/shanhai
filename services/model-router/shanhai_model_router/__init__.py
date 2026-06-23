"""ShanHai Model Router。

统一管理所有模型调用。Agent 禁止直接绑定模型，必须经此路由：

    Agent → ModelRouter.complete(task, messages, context) → 选定 Provider

Phase 0 使用 Mock Provider（见 ADR 0004），真实 Provider 保留接口与注册位。
"""

from shanhai_model_router.providers.base import (
    CompletionResult,
    ModelProvider,
)
from shanhai_model_router.providers.deepseek import DeepSeekProvider
from shanhai_model_router.providers.mock import MockProvider
from shanhai_model_router.registry import ModelRegistry
from shanhai_model_router.router import ModelRouter

__all__ = [
    "CompletionResult",
    "ModelProvider",
    "MockProvider",
    "DeepSeekProvider",
    "ModelRegistry",
    "ModelRouter",
]
