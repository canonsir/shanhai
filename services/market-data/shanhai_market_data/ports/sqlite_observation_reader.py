"""SQLiteObservationReadPort — ObservationReadPort 的 SQLite 实现（M3.4 S3）。

第二个 ``ObservationReadPort`` 实现。行为参考基线是 S2 的
``InMemoryObservationReadPort``（S2-2 冻结：**InMemory == SQLite**）：任何一批
observation 灌入两个适配器，对同一 ``(subject, knowledge_at, effective_at,
fact_types)`` 查询必须返回**逐字段相等**的结果。

关键约束（S3）：
  - S3-1 零 schema 变更：直接复用 M3.3 冻结的 ``SCHEMA_SQL`` 与编解码 helper
    （``_dumps`` / ``_loads`` / ``_iso`` / ``_dt_or_none`` / ``_subject_label_payload``
    / ``_subject_ref``），不新增 ``observation_history`` 表、不加 ``effective_at``
    索引。读能力只是「在现有 append-only spine 之上做只读投影」。
  - S3-2 同一读语义：``query`` 返回 ``captured_at <= knowledge_at`` 下的**全部
    历史行**（append-only），**不是** ``SELECT latest``（那属 Knowledge Layer；
    见 ``sqlite_repository._latest_observations`` 的 current-truth 读模型，本端口
    刻意不用）。
  - S3-3 排序稳定性：``ORDER BY captured_at ASC, logical_key ASC, content_hash
    ASC``。刻意**不用** ``observation_id``（自增代理键，InMemory 参考实现里并不
    存在，用它会与参考语义分叉）——改用 S2 已冻结的确定性内容键
    ``(captured_at, logical_key, content_hash)``，它与后端无关，两端排序一致。
  - S3-4 单向依赖：本文件属 market-data，只依赖 stdlib ``sqlite3`` + market-data
    自身模型/端口，绝不 import 任何 ``shanhai_market_intelligence`` 概念。

``effective_at`` 与 InMemory 一致：**接受但不解释**（保留给 S4 Knowledge
Evolution 的世界视角过滤）。
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from shanhai_market_data.models import FactType, SourceRef, SubjectRef
from shanhai_market_data.ports.observation_reader import Observation
from shanhai_market_data.sqlite_repository import (
    SCHEMA_SQL,
    SCHEMA_VERSION,
    _dt_or_none,
    _dumps,
    _iso,
    _loads,
    _subject_label_payload,
    _subject_ref,
)


class SQLiteObservationReadPort:
    """SQLite-backed ``ObservationReadPort`` over the frozen M3.3 spine.

    ``path=":memory:"`` keeps one shared connection for the process (a fresh
    ``:memory:`` connection would see an empty database); disk-backed paths
    reconnect per call, mirroring ``SQLiteMarketKnowledgeRepository``.
    """

    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        self._lock = threading.Lock()
        self._memory_conn: sqlite3.Connection | None = None
        if path == ":memory:":
            self._memory_conn = sqlite3.connect(path, check_same_thread=False)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON")
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # --- connection / schema (reuses frozen SCHEMA_SQL; S3-1 zero change) -----

    def _connect(self) -> sqlite3.Connection:
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _close(self, conn: sqlite3.Connection) -> None:
        if conn is not self._memory_conn:
            conn.close()

    def _init_schema(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(SCHEMA_SQL)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
                conn.commit()
            finally:
                self._close(conn)

    # --- write (append-only ingestion; idempotent on identity) ----------------

    def record(self, observation: Observation) -> None:
        """Append one observation; idempotent on ``(logical_key, content_hash)``."""
        with self._lock:
            conn = self._connect()
            try:
                self._insert(conn, observation)
                conn.commit()
            finally:
                self._close(conn)

    def record_many(self, observations: tuple[Observation, ...]) -> None:
        with self._lock:
            conn = self._connect()
            try:
                for observation in observations:
                    self._insert(conn, observation)
                conn.commit()
            finally:
                self._close(conn)

    @staticmethod
    def _insert(conn: sqlite3.Connection, observation: Observation) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_observation "
            "(logical_key, content_hash, fact_type, subject_type, subject_id, "
            "predicate, object_type, object_value, occurred_at, published_at, "
            "captured_at, confidence, source_ref, attributes, schema_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                observation.logical_key,
                observation.content_hash,
                observation.fact_type.value,
                observation.subject.entity_type,
                observation.subject.entity_id,
                observation.predicate,
                "text",
                observation.object_value,
                _iso(observation.occurred_at),
                _iso(observation.published_at),
                _iso(observation.captured_at),
                observation.confidence,
                _dumps(observation.source_ref.model_dump(mode="json")),
                _dumps(_subject_label_payload(observation.subject)),
                None,
            ),
        )

    # --- read (ObservationReadPort contract; full history, not latest) --------

    def query(
        self,
        subject: SubjectRef,
        *,
        knowledge_at: datetime,
        effective_at: datetime | None = None,
        fact_types: tuple[FactType, ...] = (),
    ) -> tuple[Observation, ...]:
        """Return ``subject`` observations with ``captured_at <= knowledge_at``.

        Full append-only history (S3-2, never a latest projection). Ordered by
        the frozen content key ``(captured_at, logical_key, content_hash)`` for
        deterministic InMemory parity (S3-3). ``effective_at`` is accepted but
        not interpreted (reserved for S4), matching the in-memory reference.
        """
        _ = effective_at  # S3: accepted, not interpreted (parity with InMemory)
        sql = (
            "SELECT logical_key, content_hash, fact_type, subject_type, subject_id, "
            "predicate, object_value, occurred_at, published_at, captured_at, "
            "confidence, source_ref, attributes "
            "FROM knowledge_observation "
            "WHERE subject_type = ? AND subject_id = ? AND captured_at <= ?"
        )
        params: list[Any] = [subject.entity_type, subject.entity_id, _iso(knowledge_at)]
        allowed = tuple(fact_types)
        if allowed:
            placeholders = ",".join("?" for _ in allowed)
            sql += f" AND fact_type IN ({placeholders})"
            params.extend(ft.value for ft in allowed)
        sql += " ORDER BY captured_at ASC, logical_key ASC, content_hash ASC"
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(sql, tuple(params)).fetchall()
            finally:
                self._close(conn)
        return tuple(self._row_to_observation(row) for row in rows)

    @staticmethod
    def _row_to_observation(row: sqlite3.Row) -> Observation:
        payload = _loads(row["attributes"]) or {}
        return Observation(
            logical_key=row["logical_key"],
            content_hash=row["content_hash"],
            fact_type=FactType(row["fact_type"]),
            subject=_subject_ref(row, payload),
            predicate=row["predicate"],
            object_value=row["object_value"],
            occurred_at=_dt_or_none(row["occurred_at"]),
            published_at=_dt_or_none(row["published_at"]),
            captured_at=_dt_or_none(row["captured_at"]),
            confidence=row["confidence"],
            source_ref=SourceRef.model_validate(_loads(row["source_ref"])),
        )
