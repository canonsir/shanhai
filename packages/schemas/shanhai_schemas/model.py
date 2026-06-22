"""模型调用相关的共享契约。

这些类型被 model-router 与 agent-runtime 共用，独立于具体 Provider 实现。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TaskType(str, Enum):
    """任务类型，用于 Router 按能力选择模型。"""

    REASONING = "reasoning"
    CODING = "coding"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    GENERAL = "general"


class Message(BaseModel):
    role: Role
    content: str


class Capability(BaseModel):
    """模型能力画像。分值越高代表越擅长；cost 越低代表越便宜。"""

    reasoning: int = 0
    coding: int = 0
    extraction: int = 0
    summarization: int = 0
    # cost: low / medium / high
    cost: str = "medium"


class ModelSpec(BaseModel):
    """models.yaml 中的单个模型注册条目。"""

    name: str
    provider: str
    capability: Capability = Field(default_factory=Capability)
    # 透传给 provider 的额外参数（如 base_url、model id 等）
    options: dict = Field(default_factory=dict)
