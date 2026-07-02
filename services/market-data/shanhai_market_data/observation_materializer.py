"""Observation Materialization — ``ObservationDraft → Observation`` 这一层（M3.6.3）。

落 [m3.6.3 设计（rev 2）](../../../docs/design/m3.6.3-observation-materialization-design.md)
冻结的 Identity 边界：把 provider 产出的**语义草稿** ``ObservationDraft``（有语义、
无身份）确定性地组装成 spine 读侧 DTO ``Observation``（带 ``logical_key`` /
``content_hash`` 身份）。整层无 I/O、无 fact_type 分支散落，身份策略与组装彻底解耦：

    ObservationDraft
          │
          ▼
    EffectiveScopeStrategy   每个 fact_type 的生效范围键（trade_date / report_period / …）
          │  effective_scope
          ▼
    IdentityStrategy         logical_key 模板 + content_hash（经 CanonicalSerializer）
          │  ObservationIdentity(logical_key, content_hash)
          ▼
    ObservationMaterializer  Draft + Identity → Observation（纯组装，无 key 规则/fact_type 分支）
          │
          ▼
    Observation ─▶ _ObservationWriter.record_many ─▶ append-only spine（不改）

只有 ``EffectiveScopeStrategy`` 随 fact_type 扩展（新增 fact_type = 加一条 scope
规则）；``IdentityStrategy`` 的 logical_key 模板与 ``ObservationMaterializer`` 的组装
逻辑永远不用动（Blocking 1 的目的）。

边界（Data Provider Boundary，ADR 0021 D6 · m3.6.3 §1 MUST NOT）：本模块只产
Observation / 不产 Knowledge / 不调 LLM / 不访问 Evolution / 不发 HTTP / 不碰
SQLite schema。只 import market-data 自己的类型，绝不 import market-intelligence。

M3.6.3 边界：本文件只落 Materializer + Identity 三件套 + 薄编排 ``ingest_drafts``，
**不含任何真实 adapter**、不接任何真实源、不改 spine。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from shanhai_market_data.models import FactType, _FrozenModel
from shanhai_market_data.observation_provider import ObservationDraft
from shanhai_market_data.ports.observation_reader import Observation


# --- Identity 值对象 ----------------------------------------------------------


class ObservationIdentity(_FrozenModel):
    """一条 observation 的身份 = timeline 身份 + 取值指纹（不可变值对象）。

    由 ``IdentityStrategy`` 产出、交给 ``ObservationMaterializer`` 组装。spine 幂等键
    = ``(logical_key, content_hash)``（既有，不改）。
    """

    logical_key: str
    content_hash: str


# --- CanonicalSerializer（跨语言确定性序列化，§2.5）----------------------------


class CanonicalSerializer:
    """把「值」序列化成**跨语言确定性字节**——同一逻辑值 → 同一 bytes → 同一 hash。

    ``content_hash`` 的稳定性取决于序列化字节完全一致：今天 Python、明天 Rust / Go
    若各自算 hash，浮点 / 时间 / None / 布尔 / 键序稍有差异就会 hash 不一致、历史全废。
    故把序列化收敛到这一个类，明确各类型的规范表示（m3.6.3 §2.5 冻结表）：

      dict → 键 UTF-8 字典序排序；str → 原样（ensure_ascii=False）；None → null；
      bool → true/false（不与 0/1 混）；int → 十进制原样；float / Decimal → 定点
      字符串（不走二进制浮点，float 与等值 Decimal 归一为同一表示）；datetime / date
      → ISO-8601（date = YYYY-MM-DD）；序列 → 保留顺序。

    纯函数、无 I/O、不认识 fact_type——只认识「值 → 规范 bytes」。
    """

    @staticmethod
    def dumps(value: Any) -> str:
        """产出规范 JSON 字符串（compact + sort_keys），确定性可复现。"""
        return json.dumps(
            CanonicalSerializer._canonical(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _canonical(value: Any) -> Any:
        # bool 必须先于 int 判定（bool 是 int 子类），否则 True/False 会退化成 1/0。
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return CanonicalSerializer._decimal_text(Decimal(str(value)))
        if isinstance(value, Decimal):
            return CanonicalSerializer._decimal_text(value)
        if isinstance(value, str):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {str(k): CanonicalSerializer._canonical(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [CanonicalSerializer._canonical(v) for v in value]
        return str(value)

    @staticmethod
    def _decimal_text(value: Decimal) -> str:
        # 定点表示，杜绝科学计数法（1E+2 → "100"），使 float 10.57 与 Decimal("10.57")
        # 归一到同一字符串。
        return format(value, "f")


# --- EffectiveScopeStrategy（per fact_type 生效范围键，§2.4）-------------------


@runtime_checkable
class EffectiveScopeStrategy(Protocol):
    """fact_type → ``effective_scope`` 具名键。**唯一随 fact_type 扩展的地方**。"""

    def scope_of(self, draft: ObservationDraft) -> str:
        ...


class DefaultEffectiveScopeStrategy:
    """冻结的 per-fact_type scope 映射（m3.6.3 §2.4）。新增 fact_type = 加一条规则。

      QUOTE → trade_date（occurred_at → 交易日）
      FINANCIAL → report_period（occurred_at 报告期末 → date）
      ANNOUNCEMENT → announcement_id（= source_ref.external_id，非日期）
      INDUSTRY → industry_version（occurred_at 版本生效日 → date）
      POLICY / NEWS → publish_period（published_at 优先 / occurred_at → 发布日）
      PROFILE → ""（latest-only，画像属最新态，无周期）
      ANOMALY / CAPITAL_FLOW / SHAREHOLDER → event_date（occurred_at → 事件日）

    时间类 scope 刻意粗到「日」——保证「换源不改身份」：两源对同一交易日的 close，即使
    ``occurred_at`` 时间戳差几秒，也落到同一 ``trade_date`` → 同一 ``logical_key``。
    """

    def scope_of(self, draft: ObservationDraft) -> str:
        ft = draft.fact_type
        if ft is FactType.ANNOUNCEMENT:
            return draft.source_ref.external_id or ""
        if ft is FactType.PROFILE:
            return ""
        if ft in (FactType.POLICY, FactType.NEWS):
            moment = draft.published_at or draft.occurred_at
            return moment.date().isoformat() if moment is not None else ""
        # QUOTE / FINANCIAL / INDUSTRY / ANOMALY / CAPITAL_FLOW / SHAREHOLDER：
        # 生效范围取自 occurred_at，归一到「日」。
        moment = draft.occurred_at
        return moment.date().isoformat() if moment is not None else ""


# --- IdentityStrategy（logical_key 模板 + content_hash 公式，§2.2/§2.3）--------


@runtime_checkable
class IdentityStrategy(Protocol):
    """draft → ``(logical_key, content_hash)``。唯一定身份处；不含 I/O。"""

    def identify(self, draft: ObservationDraft) -> ObservationIdentity:
        ...


class DefaultIdentityStrategy:
    """冻结的身份算法（m3.6.3 §2.2/§2.3），依赖注入 scope 策略 + canonical 序列化。

      logical_key  = "{entity_type}:{entity_id}|{fact_type}|{predicate}|{effective_scope}"
      content_hash = "sha256:" + sha256( CanonicalSerializer.dumps(
                         [logical_key, object_value, predicate] ) )

    这是**模板不是分支**：本策略只按上式填空，不 case fact_type；随 fact_type 变化的
    只有 ``effective_scope`` 的取值，被隔离在 ``EffectiveScopeStrategy``。content_hash
    刻意排除 captured_at / source_ref / confidence / 原始时间戳（§2.3）——换源、换抓取
    时刻都不改身份。
    """

    def __init__(
        self,
        scope: EffectiveScopeStrategy | None = None,
        serializer: CanonicalSerializer | None = None,
    ) -> None:
        self._scope = scope if scope is not None else DefaultEffectiveScopeStrategy()
        self._serializer = serializer if serializer is not None else CanonicalSerializer()

    def identify(self, draft: ObservationDraft) -> ObservationIdentity:
        predicate = draft.predicate or ""
        effective_scope = self._scope.scope_of(draft)
        logical_key = (
            f"{draft.subject.entity_type}:{draft.subject.entity_id}"
            f"|{draft.fact_type.value}|{predicate}|{effective_scope}"
        )
        digest = hashlib.sha256(
            self._serializer.dumps(
                [logical_key, draft.object_value, predicate]
            ).encode("utf-8")
        ).hexdigest()
        return ObservationIdentity(
            logical_key=logical_key, content_hash=f"sha256:{digest}"
        )


# --- ObservationMaterializer（纯组装 Draft + Identity → Observation，§1）--------


class ObservationMaterializer:
    """``ObservationDraft`` + ``ObservationIdentity`` → ``Observation``。

    纯组装、无 I/O、**不含任何 key 拼接规则 / fact_type 分支**——身份全部委托注入的
    ``IdentityStrategy``（§2）。以后 Financial / Quote / Announcement / … 的身份规则
    变化只动策略侧，Materializer 永远不用动（Blocking 1）。

    ``observation_id`` **不**由此层产：读侧 ``Observation`` DTO 本就没有该字段，它是
    SQLite 行的存储态 surrogate，由 spine 写入时分配（呼应「不改 spine」）。
    ``confidence`` 用 spine 默认 1.0（信念，非身份），此处不设。
    """

    def __init__(self, identity: IdentityStrategy) -> None:
        self._identity = identity

    def materialize(self, draft: ObservationDraft) -> Observation:
        ident = self._identity.identify(draft)
        return Observation(
            logical_key=ident.logical_key,
            content_hash=ident.content_hash,
            fact_type=draft.fact_type,
            subject=draft.subject,
            predicate=draft.predicate,
            object_value=draft.object_value,
            occurred_at=draft.occurred_at,
            published_at=draft.published_at,
            captured_at=draft.captured_at,
            source_ref=draft.source_ref,
        )

    def materialize_many(
        self, drafts: tuple[ObservationDraft, ...]
    ) -> tuple[Observation, ...]:
        return tuple(self.materialize(draft) for draft in drafts)


# --- Spine 接缝：窄写端口 + 薄编排（§5）---------------------------------------


@runtime_checkable
class _ObservationWriter(Protocol):
    """spine 写侧最小端口——让编排依赖接口而非具体适配器。

    既有 ``InMemoryObservationReadPort`` / ``SQLiteObservationReadPort`` 已 structural
    fit（它们本就有 ``record`` / ``record_many``），无需为此端口改动它们。
    """

    def record(self, observation: Observation) -> None:
        ...

    def record_many(self, observations: tuple[Observation, ...]) -> None:
        ...


class IngestReport(_FrozenModel):
    """一次 ``ingest_drafts`` 的结果摘要（materialize 为 1:1，``ingested`` = draft 数）。

    spine 层的幂等丢弃 / 修订追加不在此计数（那是 append-only spine 的语义，需经
    ``ObservationReadPort.query`` 读回才可观测）。
    """

    ingested: int


def ingest_drafts(
    drafts: tuple[ObservationDraft, ...],
    *,
    writer: _ObservationWriter,
    materializer: ObservationMaterializer,
) -> IngestReport:
    """薄编排（push 模型）：drafts → materialize → 写 spine（幂等由 spine 保证，§3）。

    输入是 **drafts 而非 provider**：M3.6.3 不依赖任何真实/mock provider（adapter 属
    M3.6.4+），用手工构造的 draft 即可端到端验证 ``draft → Observation → spine → 读回``。
    provider-pull 编排（``provider.fetch → ingest_drafts``）留待 M3.6.4 一行接上。
    """
    observations = materializer.materialize_many(drafts)
    writer.record_many(observations)
    return IngestReport(ingested=len(observations))
