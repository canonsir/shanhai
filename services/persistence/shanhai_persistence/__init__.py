"""ShanHai Persistence — 数据落库层（见 ADR 0008 / 0009）。

实现 agent-runtime 定义的 RunStore 抽象的具体后端：
- SqliteRunStore：local-first 默认，标准库 sqlite3，零外部依赖、可落盘；
- PostgresRunStore：增强后端，面向并发/规模/共享查询（需 psycopg）。
依赖方向单向：persistence → agent-runtime（抽象），agent-runtime 不感知具体存储。
default_run_store() 按环境变量装配，默认 local-first。
"""

from shanhai_persistence.factory import default_run_store
from shanhai_persistence.postgres_run_store import PostgresRunStore
from shanhai_persistence.sqlite_run_store import SqliteRunStore

__all__ = ["SqliteRunStore", "PostgresRunStore", "default_run_store"]
