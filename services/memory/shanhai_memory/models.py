"""Memory 访问层数据契约（见 ADR 0012 §3）。

三层记忆（Runtime / Knowledge / Experience）经统一的请求 MemoryQuery 与
归一返回 MemoryRecord 通路，由 MemoryService 按 scope 路由到对应 adapter。

本阶段为 Access Layer，不实现持久 MemoryStore：契约只用于统一三 scope 的读写形态，
KNOWLEDGE / EXPERIENCE 只读委派各自事实来源，不复制、不另存。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MemoryScope(str, Enum):
    """记忆层级（见 ADR 0012 §2 三层模型）。"""

    # 单次运行内的进程内草稿（无持久后端）
    RUNTIME = "runtime"
    # 对世界知识的只读检索视图（委派 Knowledge Engine）
    KNOWLEDGE = "knowledge"
    # 跨运行经验事件的只读检索（委派 ExperienceStore）
    EXPERIENCE = "experience"


class MemoryRecord(BaseModel):
    """一条记忆的归一返回载体。

    三个 scope 的异构结果（runtime 值 / Entity / ExperienceEvent）统一收敛为此形态，
    content 持有原始对象，source 标注来源（run_id / entity_id / event_id…），不复制事实。
    """

    scope: MemoryScope
    key: str
    content: Any = None
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class MemoryQuery(BaseModel):
    """一次记忆检索请求（归一）。

    各 scope 取用所需字段：KNOWLEDGE 用 text/limit；EXPERIENCE 用 agent/text/limit；
    RUNTIME 用 key。type 透传给 adapter（如 knowledge 的 EntityType / experience 的事件类型字符串）。
    """

    scope: MemoryScope
    text: str | None = None
    key: str | None = None
    type: str | None = None
    tags: list[str] = Field(default_factory=list)
    agent: str | None = None
    limit: int = 50
