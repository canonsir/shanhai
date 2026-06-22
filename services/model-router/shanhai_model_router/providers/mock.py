"""Mock Provider — Phase 0 默认实现（见 ADR 0004）。

不依赖外部网络与 API key，返回可预测的回显，用于验证模型可切换。
"""

from __future__ import annotations

from shanhai_schemas import Message
from shanhai_schemas import ModelSpec

from shanhai_model_router.providers.base import CompletionResult, ModelProvider


class MockProvider(ModelProvider):
    name = "mock"

    def complete(
        self,
        spec: ModelSpec,
        messages: list[Message],
    ) -> CompletionResult:
        last = messages[-1].content if messages else ""
        return CompletionResult(
            model=spec.name,
            provider=spec.provider,
            content=f"[mock:{spec.name}] {last}",
        )
