"""Evolution 证据层：EvidenceRef —— 锚定 observation 身份，绝不拥有 observation。

S4.2-1（Domain Model Implementation）范围内的证据契约。落地两条铁律：

- **Evidence-first**（S4.0 / S4.1）：信念必须绑定证据；无证据信念 = 幻觉。
- **R5-1（S4.1 Review 追加）**：Knowledge Evolution **不拥有** Observation。``EvidenceRef``
  只持 observation 的**身份**（``logical_key`` + ``content_hash``）与排序用的
  ``captured_at``，**不内嵌** ``Observation`` 值。需要值时经 ``ObservationReadPort``
  按需取（S4.2 后续步实现）。这样 market-data 拥有事实、market-intelligence 拥有
  解释，evolution 不会逐渐复制 market-data。

本模块是 evolution 子域的**基础值层**：共享的 ``_FrozenModel`` 基类定义在此，供
``models`` / ``revision`` / ``gate`` import（依赖方向 evidence ← models ← revision
← gate，单向不成环）。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, field_validator


class _FrozenModel(BaseModel):
    """evolution 子域共享的不可变值对象基类（frozen + extra=forbid）。"""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceRelation(str, Enum):
    """证据对信念的作用（反例也是证据）。"""

    supports = "supports"
    contradicts = "contradicts"
    contextualizes = "contextualizes"


class EvidenceRef(_FrozenModel):
    """锚定一条 observation 身份的证据引用（不内嵌值，R5-1）。

    ``logical_key`` + ``content_hash`` 是 observation 在 append-only spine 上的
    身份；二者必须非空——一条没有来源锚点的 ``EvidenceRef`` 不成立（无法回放、
    无法证伪）。``captured_at`` 只为版本链复现 / 新鲜度排序，不是 value 本身。
    """

    logical_key: str
    content_hash: str
    captured_at: datetime
    relation: EvidenceRelation = EvidenceRelation.supports

    @field_validator("logical_key", "content_hash")
    @classmethod
    def _identity_must_be_present(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError(
                "EvidenceRef 必须锚定真实 observation 身份"
                "（logical_key + content_hash 非空）"
            )
        return value


@runtime_checkable
class EvidenceResolver(Protocol):
    """校验 ``EvidenceRef`` 是否指向真实 observation。

    具体实现（经 ``ObservationReadPort``）属 S4.2 后续步；本步 ``RevisionGate``
    仅在被注入 resolver 时做可解析性校验，未注入则只做结构性校验（不接 adapter）。
    """

    def exists(self, ref: EvidenceRef) -> bool: ...
