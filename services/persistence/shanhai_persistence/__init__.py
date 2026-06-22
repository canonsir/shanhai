"""ShanHai Persistence — 数据落库层（见 ADR 0008）。

实现 agent-runtime 定义的 RunStore 抽象的具体后端（PostgresRunStore）。
依赖方向单向：persistence → agent-runtime（抽象），agent-runtime 不感知具体存储。
"""

from shanhai_persistence.postgres_run_store import PostgresRunStore

__all__ = ["PostgresRunStore"]
