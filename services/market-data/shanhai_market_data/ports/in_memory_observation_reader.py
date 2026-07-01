"""InMemoryObservationReadPort — ObservationReadPort 的内存参考实现（M3.4 S2）。

这是 ``ObservationReadPort`` 的第一个实现，也是 S3 SQLite 实现的 **behaviour
reference**（延续 M3.3「InMemory == SQLite」parity 传统）：任何一批 observation
灌入本适配器与将来的 ``SQLiteObservationReadPort``，对同一
``(subject, knowledge_at, effective_at, fact_types)`` 查询必须返回逐字段相等的
结果。

与 ``InMemoryMarketKnowledgeRepository`` 的关键区别：那个仓库是 current-truth，
按 ``fact_id`` 覆盖、**不保留历史**（见 test_repository_behavior_suite 的
``test_sqlite_retains_observation_history_storage_only``）。本适配器刻意是
**append-only**——保留同一 ``logical_key`` 下每一条不同 ``content_hash`` 的
observation，这样「截至某 knowledge_at 系统看见过哪些观测」才是可回放的；这正是
ObservationReadPort 存在的意义，也是它不能复用 current-truth 仓库的原因。

S2 边界（Review Gate 批准 + 澄清）——只实现**最小确定性读**：
  允许：subject 过滤 / fact_types 过滤 / captured_at <= knowledge_at 过滤 /
        返回 append-only observation。
  不允许：latest-per-key 投影 / effective_at 解释 / knowledge 重建 / 冲突调和 /
          cognition 生成。``effective_at`` 保留给 S4 Knowledge Evolution——本层
          **接受但不解释**该参数（与将来 SQLite 实现保持一致的 defer 行为）。

S2 不扩 schema（S2-1）：不新增 ObservationVersion / ObservationSnapshot 等类型，
只消费 §3 已冻结的 ``Observation`` 契约。不接 SQLite（S2-2 由 S3 落地）。
"""

from __future__ import annotations

from datetime import datetime

from shanhai_market_data.models import FactType, SubjectRef
from shanhai_market_data.ports.observation_reader import Observation


class InMemoryObservationReadPort:
    """Append-only, process-local ``ObservationReadPort`` 参考实现。

    写入经 ``record`` / ``record_many`` 累积（幂等于
    ``(logical_key, content_hash)``），读取经 ``query`` 做纯确定性过滤。它不是
    持久化仓库、不是 Memory / Experience / RuntimeContext，也不参与写业务链路，
    只为验证读契约领域语义与作为 SQLite parity 的对照基线。
    """

    def __init__(self) -> None:
        # 保留插入顺序 + 以 (logical_key, content_hash) 幂等；不覆盖历史。
        self._observations: list[Observation] = []
        self._seen: set[tuple[str, str]] = set()

    # --- 写入（测试 / 灌数用；非业务写链路）---------------------------------

    def record(self, observation: Observation) -> None:
        """追加一条 observation；同 ``(logical_key, content_hash)`` 幂等去重。"""
        identity = (observation.logical_key, observation.content_hash)
        if identity in self._seen:
            return
        self._seen.add(identity)
        self._observations.append(observation)

    def record_many(self, observations: tuple[Observation, ...]) -> None:
        for observation in observations:
            self.record(observation)

    # --- 读取（ObservationReadPort 契约）------------------------------------

    def query(
        self,
        subject: SubjectRef,
        *,
        knowledge_at: datetime,
        effective_at: datetime | None = None,
        fact_types: tuple[FactType, ...] = (),
    ) -> tuple[Observation, ...]:
        """返回 ``subject`` 在 ``captured_at <= knowledge_at`` 下的 observation。

        纯确定性最小读（S2）：
          1. subject 过滤（entity_type + entity_id 匹配；label 不参与身份）。
          2. captured_at <= knowledge_at（系统视角；append-only spine 的历史行）。
          3. fact_types 过滤（为空 = 全部家族）。
        返回**全部命中历史行**，不做 latest-per-key 投影。

        ``effective_at`` 在 S2 **接受但不解释**（保留给 S4 Knowledge Evolution 的
        世界视角过滤）；此处显式忽略以与将来 SQLite 实现保持一致的 defer 行为。
        """
        _ = effective_at  # S2 保留不解释（S4 落地世界视角过滤）
        allowed = set(fact_types)
        results = [
            obs
            for obs in self._observations
            if obs.subject.entity_type == subject.entity_type
            and obs.subject.entity_id == subject.entity_id
            and obs.captured_at <= knowledge_at
            and (not allowed or obs.fact_type in allowed)
        ]
        # 确定性排序：captured_at 升序，再以身份 (logical_key, content_hash) 破平手，
        # 使输出与插入顺序无关（parity 前提）。
        results.sort(key=lambda obs: (obs.captured_at, obs.logical_key, obs.content_hash))
        return tuple(results)
