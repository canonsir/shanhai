"""Evolution → Context 桥：KnowledgeResolver —— 把 revision 历史解析成"某时点的认知视图"。

S4.3 第一阶段（KnowledgeReference Resolution）：Evolution 侧产出**已解释好的**认知
视图，供 Context 层消费（Context MAY consume Knowledge, D9）；Context 不自己理解
revision（Review 点 5：不让 ContextAssembler 直接 ``store.get_history()`` 再自行推导）。

    EvolutionStore → KnowledgeResolver.resolve_at(subject, knowledge_at) → ResolvedKnowledge

铁律：

- **没有 current truth**：唯一入口是 ``resolve_at(knowledge_at)``——**禁**
  ``get_current_belief`` / ``latest`` / ``best``。资本市场不存在永恒 current truth；
  一切认知都是「站在某个 knowledge_at 回看」（支持「站在 2025-12-31，当时怎么认识茅台？」）。
- **ref-only**：``ResolvedKnowledge`` 只持版本引用（object_id@version + revision_id）+
  折叠出的 ``live_belief_ids`` + revision_chain（provenance）。**不内嵌 belief 值**——
  store 只存 delta 事件，值将来经 KnowledgeObjectStore 回取（本轮不做）。
- **不做智能**：只按 ``created_at <= knowledge_at`` 过滤、按 version 折叠 delta
  （added → live、retired → 移除）。**禁** belief ranking / conflict resolution /
  真值选择 / LLM（属未来 Evolution Policy）。

依赖方向：import store / revision / evidence（同子域）+ market-data ``SubjectRef``；
**禁** import context 侧 Snapshot 概念（D9）与 reasoning-engine（D3）。
"""

from __future__ import annotations

from datetime import datetime

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution.evidence import _FrozenModel
from shanhai_market_intelligence.evolution.revision import derive_object_id
from shanhai_market_intelligence.evolution.store import EvolutionStore


class RevisionRef(_FrozenModel):
    """指向 revision_chain 中一次演化事件（provenance 锚点，ref-only）。"""

    revision_id: str
    to_version: int
    created_at: datetime


class ResolvedKnowledge(_FrozenModel):
    """某 subject 站在 ``knowledge_at`` 的"已解释认知视图"（ref-only，可复现）。

    这是 Evolution 交给 Context 的成品：Context 只消费它，不回看原始 revision。
    无任何 belief 值 / 判断 / 排名 —— 只有"当时持有哪些信念"的 id 集合 + 版本引用。
    """

    object_id: str
    subject: SubjectRef
    resolved_version: int | None  # None = knowledge_at 早于首个 revision（尚无认知）
    resolved_revision_id: str | None
    live_belief_ids: tuple[str, ...]  # 折叠 delta 得到的"当时持有的信念 id"（稳定排序）
    revision_chain: tuple[RevisionRef, ...]  # <= knowledge_at 的演化链（provenance/可回放）
    as_of_knowledge_at: datetime


class KnowledgeResolver:
    """把 append-only 的 revision 历史，确定性地解析为某时点的 ``ResolvedKnowledge``。

    纯函数式：same history + same knowledge_at = same ResolvedKnowledge。持一个
    ``EvolutionStore``（只读 ``get_history``），不拥有写入口、不做真值/冲突判断。
    """

    def __init__(self, store: EvolutionStore) -> None:
        self._store = store

    def resolve_at(
        self, subject: SubjectRef, knowledge_at: datetime
    ) -> ResolvedKnowledge:
        """站在 ``knowledge_at`` 回看：折叠该 subject 截至此刻的 revision，得认知视图。

        deterministic：按 ``created_at <= knowledge_at`` 过滤 → 按 ``to_version`` 排序
        → 逐条应用 delta（added 并入、retired 移除；revised 不改成员）→ ref-only 视图。
        knowledge_at 早于首个 revision 时返回空视图（resolved_version=None），不 raise。
        """
        object_id = derive_object_id(subject)
        selected = sorted(
            (r for r in self._store.get_history(object_id) if r.created_at <= knowledge_at),
            key=lambda r: r.to_version,
        )

        live: set[str] = set()
        for revision in selected:
            live |= set(revision.belief_delta.added)
            live -= set(revision.belief_delta.retired)

        last = selected[-1] if selected else None
        return ResolvedKnowledge(
            object_id=object_id,
            subject=subject,
            resolved_version=last.to_version if last is not None else None,
            resolved_revision_id=last.revision_id if last is not None else None,
            live_belief_ids=tuple(sorted(live)),
            revision_chain=tuple(
                RevisionRef(
                    revision_id=r.revision_id,
                    to_version=r.to_version,
                    created_at=r.created_at,
                )
                for r in selected
            ),
            as_of_knowledge_at=knowledge_at,
        )
