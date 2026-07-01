"""Evolution 推理插槽：ReasoningPort（Protocol）+ NoopReasoner（deterministic 参考实现）。

S4.2-2 唯一交付。核心意义（S4.2-2 Review）：

> 不是提供智能，而是**冻结未来智能插槽**。

链路里 reasoning 步只落**抽象**（``ReasoningPort``）+ 一个**不推理**的参考实现
（``NoopReasoner``），证明 pipeline 在不接 LLM 的前提下可跑通、可测：

    CandidateKnowledgeChange → ReasoningPort → ProposedRevision → RevisionGate → …

铁律：

- **evolution 侧只 import ``ReasoningPort`` 抽象**（本模块定义），**不** import
  reasoning-engine、**不**接任何 LLM/OpenAI/Claude（ADR 0020 D3；与 ADR 0011「Agent
  禁直调模型」同源）。真实推理器 + LLM 属 reasoning-engine（M3.7）。
- **NoopReasoner 恒等映射、deterministic**：相同 candidate → 相同 ``ProposedRevision``
  （belief_id 由 ``derive_belief_id`` 确定性派生，无随机、无时间注入）。保证 pipeline
  可确定性测试（S4.2-2 Case 11：内容 hash 一致）。
- **不生成 evidence（守 evidence-first）**：只把 ``candidate.evidence_refs`` 直通给
  belief，不凭空造证据。若 candidate 无 evidence → 产出的 belief evidence 为空 →
  由 ``Belief`` 构造校验直接拒（无证据不允许创建），这正是 evidence-first 护栏。
- **不计算 confidence（R4-3 / Review 点 5）**：``confidence=None``（未评估），不设占位、
  不做聚合公式。
- **reasoner 可互换、不影响 Gate（S4.2-2 Case 12）**：``NoopReasoner`` 与未来
  ``FutureLLMReasoner`` 都满足 ``ReasoningPort``，产出的 ``ProposedRevision`` 走同一
  Gate 输入协议——Gate 对任何 mode 一视同仁做 deterministic 校验，不感知 reasoner 身份。

依赖方向：import evidence / models / revision（同子域）+ market-data 无直接引用；**禁**
import context 侧概念（D9）与 reasoning-engine（D3）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shanhai_market_intelligence.evolution.models import (
    Belief,
    BeliefStatement,
    CandidateKnowledgeChange,
)
from shanhai_market_intelligence.evolution.revision import (
    BeliefDelta,
    ProposedRevision,
    derive_belief_id,
    derive_object_id,
)

NOOP_REASONING_MODE = "noop"


@runtime_checkable
class ReasoningPort(Protocol):
    """把「信念修订候选」转成「拟修订提案」的抽象（未来智能插槽）。

    由 reasoning-engine（M3.7）用真实推理器 + LLM 实现；S4.2-2 只提供 deterministic
    的 ``NoopReasoner`` 参考实现。契约（ADR 0020 D3/D6）：``reason`` 消费候选，产出
    ``ProposedRevision``；**不**写 KnowledgeObject、**不**生成 evidence——产出的每条拟
    belief 必须携带候选自带的 ``evidence_refs``（evidence-first）。
    """

    def reason(self, candidate: CandidateKnowledgeChange) -> ProposedRevision: ...


class NoopReasoner:
    """S4.2-2 deterministic 参考实现（对齐 ADR 0017 NoopValidator）：不推理、不总结。

    把 ``candidate.hypothesis`` 恒等映射为一条 ``Belief``（dimension/claim 直通），
    evidence 直通，confidence 保持 ``None``（不计算）。它证明架构形状成立，但**不产生
    任何真实认知**——真实推理等 M3.7 接入 ``ReasoningPort``。
    """

    def reason(self, candidate: CandidateKnowledgeChange) -> ProposedRevision:
        evidence_refs = candidate.evidence_refs
        belief = Belief(
            belief_id=derive_belief_id(candidate, evidence_refs),
            statement=BeliefStatement(
                dimension=candidate.hypothesis.dimension,
                claim=candidate.hypothesis.claim,
            ),
            evidence_refs=evidence_refs,  # 直通：不造证据（无 evidence → Belief 构造即拒）
            confidence=None,  # 不计算（R4-3 / Review 点 5）
        )
        return ProposedRevision(
            candidate_id=candidate.candidate_id,
            object_id=derive_object_id(candidate.subject),
            proposed_beliefs=(belief,),
            proposed_delta=BeliefDelta(added=(belief.belief_id,)),
            reasoning_ref=None,  # S4.2-2 无推理记录
            reasoning_mode=NOOP_REASONING_MODE,
        )
