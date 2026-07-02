"""ObservationProvider — canonical 写侧 provider 契约（M3.6.2 骨架）。

落 M3.6.0 冻结的契约（[m3.6.0-provider-contract-review.md]、[m3.6 design §2]）：
provider 只产**语义观测草稿** ``ObservationDraft``（有语义、无身份），身份
（``logical_key`` / ``content_hash``）由共享 ingestion pipeline 确定性算出。
这是「统一 Observation 而非统一 Provider」（ADR 0021 D2）的落点。

命名裁决（ADR 0021 D3）：用户 spec 的 ``MarketDataProvider`` 与 legacy
[provider.py] 的 ``MarketDataProvider`` 撞名，canonical 契约改名
``ObservationProvider``，与 legacy 并存于迁移窗口，二者不互相修改。

边界（Data Provider Boundary，ADR 0021 D6）：provider 只产 Observation /
不产 Knowledge / 不调 LLM / 不访问 Evolution / 可替换 / credential 配置化。
本模块只 import market-data 自己的类型（``SubjectRef`` / ``FactType`` /
``SourceRef``），**绝不** import market-intelligence（依赖方向铁律）。

M3.6.2 边界：本文件只落契约（Protocol + 两个 frozen DTO），**不含任何
adapter 实现**、不接任何真实源、不做归一化/持久化。
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


class DataQuery(_FrozenModel):
    """向一个 provider 请求某 subject 的某些 fact 家族的观测。

    provider 据此取数并映射成 ``ObservationDraft``。query 只表达「要什么」，
    不表达「怎么算身份」「落哪张表」——那是 ingestion pipeline 的关注点。
    """

    subject: SubjectRef
    fact_types: tuple[FactType, ...] = ()
    since: datetime | None = None
    until: datetime | None = None
    limit: int | None = None


class ObservationDraft(_FrozenModel):
    """provider 产出的「语义观测草稿」——有语义、无身份。

    刻意区别于 [ports/observation_reader.py] 的 ``Observation``（读侧投影，带
    ``logical_key`` / ``content_hash`` 身份）：draft 是 provider 给出的原始
    语义观测，身份由共享 ingestion pipeline 确定性算出，provider **绝不**
    自算身份。这是「provider 不背身份职责」的落点。

    与 ``Observation`` 字段几乎同构，唯独没有 ``logical_key`` / ``content_hash``
    / ``confidence``——那三项是身份/信念，属共享层与认知层，不属 provider。
    ``object_value`` 用字符串承载跨源统一；结构化明细走 typed detail 表投影，
    不塞 draft 顶层（ADR 0021 D5）。
    """

    subject: SubjectRef
    fact_type: FactType
    predicate: str | None = None
    object_value: str | None = None
    occurred_at: datetime | None = None
    published_at: datetime | None = None
    captured_at: datetime
    source_ref: SourceRef


@runtime_checkable
class ObservationProvider(Protocol):
    """canonical 写侧 provider 契约（M3.6）。所有真实 / mock 源实现它。

    单方法、无身份：provider 只搬运 + 翻译，吐 ``ObservationDraft``。一个
    provider 对不支持的 fact 家族可返回空 tuple 或 raise ``NotImplementedError``
    （沿用 M3.2 优雅降级）。返回 ``tuple``（frozen 精神），非 ``list``。
    """

    name: str

    def fetch_observations(self, query: DataQuery) -> tuple[ObservationDraft, ...]:
        ...
