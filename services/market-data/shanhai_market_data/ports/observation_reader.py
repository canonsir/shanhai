"""ObservationReadPort — market-data 对外的第二个只读契约（M3.4 S1，additive）。

与冻结的 9 方法 ``MarketKnowledgeRepository`` 并列、互不修改。9 方法是
current-truth 读；本端口是「截至某 ``knowledge_at`` 的 observation」历史读，
支撑上层做 bitemporal ``as_of`` 认知（历史认知回放）。

R1 命名裁决（ADR 0019 D2 修订）：原名 ``KnowledgeReadPort`` 已改名
``ObservationReadPort``。理由：market-data 是 **Observation Store**，不是
Knowledge Store；``Knowledge*`` 命名会暗示 market-data 拥有 knowledge，污染
领域所有权。真正的 ``Observation → Knowledge Extraction → KnowledgeObject``
属 market-intelligence 内部。

关键边界（R1 铁律「market-data 永远不知道 intelligence 存在」）：本端口放在
market-data、返回 market-data 自己的 ``Observation`` 只读 DTO，故签名只用
**基元类型**（``knowledge_at: datetime`` 等），**绝不** 引用 market-intelligence
的 ``AsOf`` / ``KnowledgeObject`` / ``MarketContextSnapshot``。概念上的
``query(subject, as_of)`` 中的 ``as_of`` 由 intelligence 侧的 ContextAssembler
从自己的 ``AsOf`` 拆成两个 datetime 再调用本端口。

S1 边界：本文件只落 Protocol + ``Observation`` DTO（interface only，**不含
实现**）。InMemory 实现在 S2、SQLite 实现在 S3。
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from shanhai_market_data.models import (
    FactType,
    SourceRef,
    SubjectRef,
    _FrozenModel,
)


class Observation(_FrozenModel):
    """一条 observation 的只读投影 DTO（属 market-data，非 intelligence）。

    1:1 映射 append-only ``knowledge_observation`` spine 的一行；其身份是
    ``(logical_key, content_hash, captured_at)``。它是 market-data 对外暴露的
    读契约类型——market-intelligence import 它是「下游 import 上游」，符合
    依赖方向 ``market-intelligence → market-data``。

    刻意区别于 ``MarketFact``：``MarketFact`` 是 latest 投影后的领域对象（当前
    信念），``Observation`` 是历史观测记录（事实输入）。二者不合并，避免把
    「历史观测」与「当前信念」混成一个类型。结构化 detail（financial / quote /
    announcement）不在此展开，需要时经现有投影路径取。
    """

    logical_key: str
    content_hash: str
    fact_type: FactType
    subject: SubjectRef
    predicate: str | None = None
    object_value: str | None = None
    occurred_at: datetime | None = None
    published_at: datetime | None = None
    captured_at: datetime
    confidence: float = 1.0
    source_ref: SourceRef


@runtime_checkable
class ObservationReadPort(Protocol):
    """截至某 ``knowledge_at`` 的 observation 历史读端口（只读，additive）。

    读 append-only spine（M3.3 已保留历史），按 ``captured_at <= knowledge_at``
    过滤——返回该 subject 在那一刻可见的所有 observation（历史行，不是 latest
    投影）。因 spine append-only + 本端口只读，历史认知回放是确定性的。
    """

    def query(
        self,
        subject: SubjectRef,
        *,
        knowledge_at: datetime,
        effective_at: datetime | None = None,
        fact_types: tuple[FactType, ...] = (),
    ) -> tuple[Observation, ...]:
        """返回 ``subject`` 在 ``captured_at <= knowledge_at`` 约束下的 observation。

        - ``knowledge_at``：系统视角，只采纳此刻及之前捕获的 observation。
        - ``effective_at``：世界视角（可选）；给出时进一步用
          ``occurred_at/published_at <= effective_at`` 过滤。
        - ``fact_types``：为空 = 全部家族；否则只返回命中家族。
        """
        ...
