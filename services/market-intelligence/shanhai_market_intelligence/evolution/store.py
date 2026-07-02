"""Evolution 演化历史存储：EvolutionStore —— append-only 版本链记录（S4.2-3 抽象）。

S4.2-3（InMemory EvolutionStore）范围内的存储契约。它是认知**演化历史**的保存点：

    KnowledgeRevision → EvolutionStore（append-only）

铁律（S4.2-3 Review）：

- **Append-only（S4.0 §3 / D7）**：只 ``append_revision`` + 只读 ``get_history``。
  **结构上不存在** ``update_revision`` / ``delete_revision``——从 API 表面就杜绝覆盖
  （比运行时校验更强）。``retire != delete``：一条 belief 被 retire 只是新版本不再
  包含它，旧 revision 永久保留，可回放「AI 当时为何持有该信念」。
- **不做智能查询**：**禁** ``find_best_belief`` / ``latest_truth`` / ``resolve_conflict``
  ——这些属未来 Evolution Policy（冲突消解 / 真值选择），不是存储职责。Store 只按
  ``object_id`` 忠实回放插入顺序的历史。
- **不接 SQLite（O5）**：本步只做 InMemory reference semantics，先验证 model lifecycle
  + version chain + context consumption contract，再设计持久化。

依赖方向：import revision（同子域，``KnowledgeRevision``）；**禁** import context 侧概念
（D9）、reasoning-engine（D3）、任何存储实现（SQLite）。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shanhai_market_intelligence.evolution.revision import KnowledgeRevision


@runtime_checkable
class EvolutionStore(Protocol):
    """认知演化历史的 append-only 存储抽象（首版仅 InMemory；SQLite 属 O5 后续）。

    只有两个能力：追加一次演化事件、按 object 回放历史。**没有** update/delete，
    **没有**智能查询（真值选择 / 冲突消解属未来 Evolution Policy，不在存储层）。
    """

    def append_revision(self, revision: KnowledgeRevision) -> None:
        """追加一次演化事件（append-only；已存在的历史不可被改写）。"""
        ...

    def get_history(self, object_id: str) -> list[KnowledgeRevision]:
        """按插入顺序回放某 object 的全部 revision（不做筛选 / 排序策略 / 真值判断）。"""
        ...
