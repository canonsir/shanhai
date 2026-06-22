"""Provider 抽象接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel
from shanhai_schemas import Message, ModelSpec


class CompletionResult(BaseModel):
    """模型补全结果。"""

    model: str
    provider: str
    content: str


class ModelProvider(ABC):
    """所有模型 Provider 的基类。

    真实 Provider（OpenAI / Anthropic / DeepSeek / Qwen / Local）按此接口实现，
    Router 与调用方不感知具体实现。
    """

    name: str = ""

    @abstractmethod
    def complete(
        self,
        spec: ModelSpec,
        messages: list[Message],
    ) -> CompletionResult:
        """调用具体模型完成补全。"""
        raise NotImplementedError
