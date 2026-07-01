"""Context 侧认知视图桥：KnowledgeView —— Context 消费 Evolution 的唯一形状（S4.3）。

D9「Context MAY consume Knowledge」的落地点：Context 层**只消费已解释好的认知视图**，
不回看原始 revision、不自己折叠 delta（Review 点 5）。数据流单向：

    Evolution: KnowledgeResolver.resolve_at(...) → ResolvedKnowledge（Evolution 拥有）
                          │  consume（值，非机器）
                          ▼
    Context:   build_knowledge_view(resolved) → KnowledgeView（喂给 ContextAssembler）

铁律：

- **consumes, not owns**：本模块 import Evolution 产出的 ``ResolvedKnowledge``**值类型**，
  但**禁** import ``EvolutionStore`` / ``KnowledgeResolver`` 这类 Evolution 机器
  （Case 18 AST 守护）——Context 不持有演化写入口、不驱动解析，只接成品。
- **ref-only、纯投影**：``build_knowledge_view`` 是无 I/O 纯函数，只把 ref-only 的
  ``ResolvedKnowledge`` 平移成 Context 词表，不新增判断 / 排名 / 真值 / LLM。
- **没有 current truth**：视图带 ``knowledge_at``——它是"站在某时点的认知视图"，
  不是"当前信念"。

依赖方向：import evolution 的 ``ResolvedKnowledge`` + market-data ``SubjectRef``；
market-data 永不知本模块存在（R1-1）。
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from shanhai_market_data.models import SubjectRef

from shanhai_market_intelligence.evolution.resolver import ResolvedKnowledge


class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class KnowledgeView(_FrozenModel):
    """Context 可消费的认知视图引用（ref-only；ContextAssembler 未来放入 Snapshot）。

    只引用「站在 ``knowledge_at`` 时该 object 处于哪个版本、当时持有哪些 belief_id」，
    不内嵌 belief 值（值经 KnowledgeObjectStore 回取，本轮不做）。``resolved_version``
    为 None 表示该时点系统尚无对此 subject 的认知（早于首个 revision）。
    """

    object_id: str
    subject: SubjectRef
    resolved_version: int | None
    resolved_revision_id: str | None
    belief_ids: tuple[str, ...]  # = ResolvedKnowledge.live_belief_ids（当时持有的信念 id）
    knowledge_at: datetime


def build_knowledge_view(resolved: ResolvedKnowledge) -> KnowledgeView:
    """把 Evolution 的 ``ResolvedKnowledge`` 平移为 Context 侧 ``KnowledgeView``（纯投影）。

    不做任何再解释：字段一一对应，只换到 Context 词表。这保证「Context 不重复 Evolution
    逻辑」——若未来 belief 折叠规则变化，只改 Resolver，Context 侧无感。
    """
    return KnowledgeView(
        object_id=resolved.object_id,
        subject=resolved.subject,
        resolved_version=resolved.resolved_version,
        resolved_revision_id=resolved.resolved_revision_id,
        belief_ids=resolved.live_belief_ids,
        knowledge_at=resolved.as_of_knowledge_at,
    )
