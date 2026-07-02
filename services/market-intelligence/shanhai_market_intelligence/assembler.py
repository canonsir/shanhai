"""ContextAssembler — 把 observation 组装成 MarketContextSnapshot（ADR 0019 D4/D6 + R1-4）。

R1-4 裁决：第一版**纯 deterministic，不智能化**。它**只负责**：查询 / 过滤 /
排序 / as_of 计算 / provenance 合并 / quality 计算。**禁止**：推理 / 总结 / 判断 /
LLM 自动总结。任何「结论 / 观点 / 评级 / 摘要」都不在 M3.4——那属 reasoning-engine
（M3.7）。这样 Context 层只产出「系统知道什么」的确定性认知态，边界不混乱。

依赖倒置：构造时注入一个 ``ObservationReadPort``（market-data 侧），永远不知道背后
是 SQLite 还是 InMemory，也不 import 存储实现。cognition_state 经窄只读接口
``CognitionRefReader`` 走「引用」而非 import experience 模块；Evolution 侧的认知视图
经窄只读接口 ``KnowledgeViewReader`` 走「引用」而非 import ``KnowledgeResolver`` /
``EvolutionStore``（D9 反向：Context consumes, not owns，Case 18 守护）。

S1 边界：本文件只落**骨架**——``assemble`` 抛 ``NotImplementedError``。真正的组装
管线（read → refs → market_state → quality → cognition → freeze）在 S4 实现。

S4.3-2 接缝：本步只落「Context 能消费 Evolution 认知视图」的接缝——注入
``KnowledgeViewReader`` 端口 + 只读方法 ``knowledge_view_for``，端到端证明
``Store → Resolver → KnowledgeView → Assembler`` 链路成立。``KnowledgeView`` 仍**不进**
``MarketContextSnapshot``（R1-3 frozen shape 不改；且现有 ``KnowledgeRef`` 强绑
``resolved_from``/``confidence``，本轮无 observation、不引入 confidence policy），故
``assemble`` 保持 ``NotImplementedError``。
"""

from __future__ import annotations

from typing import Protocol

from shanhai_market_data.models import SubjectRef
from shanhai_market_data.ports import ObservationReadPort

from shanhai_market_intelligence.knowledge_view import KnowledgeView
from shanhai_market_intelligence.models import (
    AsOf,
    CognitionRef,
    MarketContextSnapshot,
)


class CognitionRefReader(Protocol):
    """窄只读接口：返回某 subject 在某 as_of 的历史认知引用（只 id/ref，不内嵌）。

    存在意义是保证 cognition_state 走「引用」而非 import experience 模块——本期
    可给 Noop 实现（返回空 tuple）。
    """

    def refs_for(
        self, subject: SubjectRef, as_of: AsOf
    ) -> tuple[CognitionRef, ...]:
        ...


class KnowledgeViewReader(Protocol):
    """窄只读接口：返回某 subject 站在 ``as_of.knowledge_at`` 的认知视图（ref-only）。

    存在意义是保证 Context 走「引用已解释好的认知视图」而非 import Evolution 的机器
    （``KnowledgeResolver`` / ``EvolutionStore``）——Context consumes, not owns（Review
    点 5 + Case 18）。实现方（组合根，在 context 之外）内部包 ``KnowledgeResolver`` +
    ``build_knowledge_view``；本文件只依赖 ``KnowledgeView`` 值类型。``None`` 表示该时点
    系统尚无对此 subject 的认知。
    """

    def view_for(
        self, subject: SubjectRef, as_of: AsOf
    ) -> KnowledgeView | None:
        ...


class ContextAssembler:
    """把 market-data 的 observation 确定性地组装为 ``MarketContextSnapshot``。

    纯 deterministic：步骤「读」是唯一 I/O，其余为纯函数（same observation +
    same as_of = same snapshot）。首版不落库（D6），返回内存对象。
    """

    def __init__(
        self,
        read_port: ObservationReadPort,
        *,
        cognition_reader: CognitionRefReader | None = None,
        knowledge_reader: KnowledgeViewReader | None = None,
    ) -> None:
        self._read_port = read_port
        self._cognition_reader = cognition_reader
        self._knowledge_reader = knowledge_reader

    def knowledge_view_for(
        self, subject: SubjectRef, as_of: AsOf
    ) -> KnowledgeView | None:
        """经注入的 ``KnowledgeViewReader`` 消费 Evolution 认知视图（S4.3-2 接缝）。

        纯 pass-through：Context 只**引用**已解释好的认知视图，不折叠 revision、不做
        selector / ranking / conflict / confidence（那会让 Assembler 变 AI brain 而非
        context builder，Review 点 5）。未注入 reader 或该时点无认知时返回 ``None``。
        """
        if self._knowledge_reader is None:
            return None
        return self._knowledge_reader.view_for(subject, as_of)

    def assemble(self, subject: SubjectRef, as_of: AsOf) -> MarketContextSnapshot:
        """在 ``as_of`` 冻结 ``subject`` 的认知态（S4 实现）。

        计划管线（纯 deterministic，无推理 / 总结 / LLM）：
          1. 读：``read_port.query(subject, knowledge_at=..., effective_at=...)``
          2. 调和 latest-as-of → observation_refs / knowledge_refs
          3. 投影 market_state（仅确定性覆盖标记）
          4. 计算 data_quality（coverage / freshness / conflicts / trust_floor / missing）
          5. 附 cognition_state（经 CognitionRefReader，只引用 id/ref）
          6. 冻结为 MarketContextSnapshot（含 deterministic snapshot_id）
        """
        raise NotImplementedError("ContextAssembler.assemble is implemented in S4")
