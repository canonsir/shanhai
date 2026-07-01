"""Evolution 演化历史存储 —— InMemoryEvolutionStore（S4.2-3 参考实现）。

进程内 append-only 版本链：``object_id → [revision_v1, revision_v2, ...]``（按插入顺序）。

append-only 语义在此坐实（S4.2-3 Review）：

- **不提供 update / delete 方法**——从 API 表面杜绝覆盖（结构性保证 > 运行时校验）。
- ``KnowledgeRevision`` 本身 frozen（不可变），加上 ``get_history`` 返回**副本 list**，
  历史一旦写入即不可被外部改写（Case 14）。
- 不同 ``object_id`` 的历史严格隔离（Case 15），互不混入。
- **不做智能查询**：无 ``find_best_belief`` / ``latest_truth`` / ``resolve_conflict``
  （真值选择 / 冲突消解属未来 Evolution Policy，不是存储职责）。

**不接 SQLite（O5）**：本步只做 InMemory；SQLite 版本链存储属后续，届时复用 S3 已验证
的 InMemory↔SQLite parity 套件模式。
"""

from __future__ import annotations

from shanhai_market_intelligence.evolution.revision import KnowledgeRevision


class InMemoryEvolutionStore:
    """进程内 append-only 演化历史存储（EvolutionStore 参考实现）。"""

    def __init__(self) -> None:
        self._histories: dict[str, list[KnowledgeRevision]] = {}

    def append_revision(self, revision: KnowledgeRevision) -> None:
        """追加一次演化事件（append-only；同 object 的历史按插入顺序累积，不覆盖）。"""
        self._histories.setdefault(revision.object_id, []).append(revision)

    def get_history(self, object_id: str) -> list[KnowledgeRevision]:
        """回放某 object 的全部 revision（副本，外部改动不影响内部历史）。

        未知 object 返回空 list（不 raise）；不做任何筛选 / 真值判断 / 冲突消解。
        """
        return list(self._histories.get(object_id, ()))
