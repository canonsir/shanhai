"""Market Intelligence domain models — Context Layer 认知快照（ADR 0019 D3/D4/D5/D7 + R1-3）。

本层建模「在某个时间点，系统**认为自己知道什么**」——不是「今天有哪些数据」。
所有 model ``frozen=True, extra="forbid"``；集合一律用 ``tuple``，保持不可变可哈希。

R1-3 防 God Object 裁决：``MarketContextSnapshot`` 严格收紧为 **ref-based**，只有
7 个认知内容字段 ``{subject, as_of, observation_refs, knowledge_refs, market_state,
cognition_state, data_quality}``（+ 3 个可复现 meta）。**禁止**按数据种类平铺内嵌
（``financials/news/technical/chip`` ...），否则半年后必然长成 daily_stock_analysis
的 ContextPack。值不进 snapshot——需要具体值时，消费方持 ref 回 market-data 取。

依赖方向：本模块 import market-data（下游 import 上游，允许）；market-data 永远
不知道本模块存在（R1-1 铁律）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from shanhai_market_data.models import FactType, SourceRef, SourceTrustLevel, SubjectRef


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AsOf(_FrozenModel):
    """bitemporal 双时间轴（D5）：系统视角 + 世界视角。"""

    effective_at: datetime  # 世界视角：截至这一刻成立 / 可见的事实
    knowledge_at: datetime  # 系统视角：只采纳 captured_at <= 此刻 的 observation


class ObservationRef(_FrozenModel):
    """引用一条 observation 的身份（不内嵌值）。

    ``captured_at`` 只为排序 / 新鲜度，不是值本身。需要值时持此 ref 回
    market-data 取。
    """

    logical_key: str
    content_hash: str
    fact_type: FactType
    captured_at: datetime


class KnowledgeRef(_FrozenModel):
    """引用「某 logical_key 调和后的当前信念」——仍是 ref，非值。

    ``resolved_from`` 记录该信念来自哪条 observation，作为可复现锚点。
    """

    logical_key: str
    resolved_from: ObservationRef
    confidence: float = 1.0


class MarketState(_FrozenModel):
    """系统当下对该 subject 的「认知覆盖状态」——非行情数据。

    v1 只放确定性状态标记（哪些家族有知识、本快照内最低信任度），不放任何
    判断 / 结论 / 评级（ContextAssembler 第一版纯 deterministic，R1-4）。
    """

    known_fact_families: tuple[FactType, ...] = ()
    trust_floor: SourceTrustLevel | None = None


class CognitionRef(_FrozenModel):
    """cognition_state 成员：引用历史认知，禁复制内容、禁 import experience。"""

    ref: str  # experience / run / outcome / lesson 的 id
    kind: str  # previous_analysis / previous_prediction / feedback
    at: datetime | None = None
    horizon: str | None = None


class CognitionState(_FrozenModel):
    """「我以前怎么想 / 预测 / 被验证」——全 ref，不内嵌 experience 内容。"""

    refs: tuple[CognitionRef, ...] = ()


class Conflict(_FrozenModel):
    """同 logical_key 多源不一致——不静默取一个，显式列出竞争来源。"""

    logical_key: str
    competing_sources: tuple[SourceRef, ...] = ()


class DataQuality(_FrozenModel):
    """这份认知本身有多可信 / 完整 / 新鲜（D7：让消费方区分知道 / 存疑 / 不知道）。"""

    coverage: tuple[tuple[str, float], ...] = ()  # (dimension, 0..1)
    freshness_max_staleness_days: float | None = None
    stale_dimensions: tuple[str, ...] = ()
    conflicts: tuple[Conflict, ...] = ()
    trust_floor: SourceTrustLevel | None = None
    missing: tuple[str, ...] = ()  # 显式缺失，不静默当 0


class MarketContextSnapshot(_FrozenModel):
    """某个 as_of 冻结的、可推理、可复现的市场认知态（本层产物，D3/D4）。

    ref-based（R1-3）：内容只引用已持久化的 observation / knowledge，加上系统在
    该时刻的状态与自我质量评估。不内嵌数据值，不按数据种类平铺。

    命名护栏（D3）：与 runtime-kernel 的 ``RuntimeContext`` 不撞名；禁裸
    ``Context`` / ``ContextBuilder``。
    """

    # ── 7 个认知内容字段（R1-3 严格 shape）────────────────────────────
    subject: SubjectRef
    as_of: AsOf
    observation_refs: tuple[ObservationRef, ...] = ()
    knowledge_refs: tuple[KnowledgeRef, ...] = ()
    market_state: MarketState
    cognition_state: CognitionState
    data_quality: DataQuality
    # ── 可复现 meta（非认知内容；P2 确定性锚点，测试用）────────────────
    snapshot_id: str  # deterministic from (subject, as_of, observation 身份集合)
    schema_version: Literal["market_context_snapshot.v1"] = "market_context_snapshot.v1"
    assembled_at: datetime
