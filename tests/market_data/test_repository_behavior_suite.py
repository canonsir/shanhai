"""M3.3 Phase 2 Step 2 — Repository behaviour suite.

Proves the durable SQLite adapter is behaviourally identical to the in-memory
*reference* adapter on the read model, and pins the append-only retention
guarantee that only the durable substrate provides.

Strategy = migration-replay. One sync feeds a recording repository that captures
the exact domain write-log — identical surrogate ids, facts, and quote snapshots.
That same log is replayed into a fresh InMemory adapter and a fresh SQLite
adapter, so any read-model difference is purely adapter behaviour, never input
drift (two independent syncs would mint new UUIDs and diverge on identity). This
single fixture therefore satisfies both:

* the parity requirement (Step 2): InMemory == SQLite on intel / timeline /
  list / search, and
* the InMemory -> SQLite migration smoke test (Requirement 2): the in-memory
  write-log imports into SQLite and reads back identically.

It also pins durability (survives reopening a disk db), idempotency (double
replay is a no-op), quote convergence (the bundle QUOTE fact and ``upsert_quote``
land on one spine row), and a SQLite-only temporal retention check (storage keeps
every distinct observation so "what did we know at T" stays recoverable, while
the read model still projects the latest). The temporal check does NOT touch the
9-method contract or add an ``as_of`` parameter — it only inspects raw storage.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_repository_behavior_suite
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shanhai_market_data import (
    AShareCompanySyncService,
    CompanyIntelligence,
    DEFAULT_A_SHARE_TARGETS,
    FactType,
    InMemoryMarketKnowledgeRepository,
    MarketFact,
    SyncTarget,
)
from shanhai_market_data.sqlite_repository import SQLiteMarketKnowledgeRepository

from tests.market_data.test_data_foundation_mvp import _FakeMarketDataProvider
from tests.market_data.test_market_knowledge_facts import _FullProvider

_MAOTAI = SyncTarget(ts_code="600519.SH", expected_name="贵州茅台")
# DEFAULT_A_SHARE_TARGETS covers exactly the 10 ts_codes _FakeMarketDataProvider serves.
_TEN = DEFAULT_A_SHARE_TARGETS


# --- migration-replay harness -------------------------------------------------


class _RecordingRepository:
    """Captures the exact domain write-log produced by one sync.

    Only the five write methods are exercised by the sync service; reads are
    never called during ingestion. Recording the calls (not re-running the sync)
    is what guarantees both adapters receive byte-identical domain objects.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def upsert_company_bundle(self, **kwargs: Any) -> None:
        self.calls.append(("bundle", kwargs))

    def upsert_market_facts(self, company_id: str, facts: tuple[MarketFact, ...]) -> None:
        self.calls.append(("market", {"company_id": company_id, "facts": facts}))

    def upsert_financial_facts(self, company_id: str, facts: tuple[Any, ...]) -> None:
        self.calls.append(("financial", {"company_id": company_id, "facts": facts}))

    def upsert_announcement_facts(self, company_id: str, facts: tuple[Any, ...]) -> None:
        self.calls.append(("announcement", {"company_id": company_id, "facts": facts}))

    def upsert_quote(self, quote: Any) -> None:
        self.calls.append(("quote", {"quote": quote}))


def _record(provider: Any, targets: tuple[SyncTarget, ...]) -> _RecordingRepository:
    recorder = _RecordingRepository()
    AShareCompanySyncService(provider, recorder).sync_companies(targets)
    return recorder


def _replay(recorder: _RecordingRepository, repo: Any) -> None:
    for method, kwargs in recorder.calls:
        if method == "bundle":
            repo.upsert_company_bundle(**kwargs)
        elif method == "market":
            repo.upsert_market_facts(kwargs["company_id"], kwargs["facts"])
        elif method == "financial":
            repo.upsert_financial_facts(kwargs["company_id"], kwargs["facts"])
        elif method == "announcement":
            repo.upsert_announcement_facts(kwargs["company_id"], kwargs["facts"])
        elif method == "quote":
            repo.upsert_quote(kwargs["quote"])


def _first_bundle(recorder: _RecordingRepository) -> dict[str, Any]:
    for method, kwargs in recorder.calls:
        if method == "bundle":
            return kwargs
    raise AssertionError("recorder captured no company bundle")


# --- order-insensitive read-model comparison ----------------------------------


def _normalize(intel: CompanyIntelligence) -> dict[str, Any]:
    """Canonical, order-insensitive view of one CompanyIntelligence.

    Fact families and source refs are multisets (the two adapters iterate them in
    different physical orders), so they are sorted by a stable key. The timeline
    is deterministically ordered by ``build_company_timeline`` (event_time,
    event_id), so it is compared as-is — its ordering IS a behaviour under test.
    """
    data = intel.model_dump(mode="json")
    for key in ("facts", "financial_facts", "announcement_facts"):
        data[key] = sorted(data[key], key=lambda f: f["fact_id"])
    data["source_refs"] = sorted(
        data["source_refs"],
        key=lambda r: (r["source_id"], r.get("external_id") or "", r.get("captured_at") or ""),
    )
    return data


def _intel_map(repo: Any, ts_codes: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for ts_code in ts_codes:
        item = repo.get_company_intelligence_by_ts_code(ts_code)
        assert item is not None, f"missing intelligence for {ts_code}"
        out[ts_code] = _normalize(item)
    return out


def _raw_count(path: str, sql: str, params: tuple[Any, ...]) -> int:
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute(sql, params).fetchone()[0])
    finally:
        conn.close()


# --- tests --------------------------------------------------------------------


def test_parity_company_intelligence() -> None:
    """The full CompanyIntelligence read model is identical across adapters.

    Doubles as the InMemory -> SQLite migration smoke test: the same domain
    write-log imports into SQLite and reads back equal to the in-memory adapter.
    """
    recorder = _record(_FullProvider(), (_MAOTAI,))

    inmem = InMemoryMarketKnowledgeRepository()
    sqlite_repo = SQLiteMarketKnowledgeRepository(path=":memory:")
    _replay(recorder, inmem)
    _replay(recorder, sqlite_repo)

    inmem_intel = inmem.get_company_intelligence_by_ts_code("600519.SH")
    sqlite_intel = sqlite_repo.get_company_intelligence_by_ts_code("600519.SH")
    assert inmem_intel is not None and sqlite_intel is not None

    # Sanity: the fixture actually carries every fact family + a quote.
    assert {f.fact_type for f in inmem_intel.facts} >= {
        FactType.PROFILE,
        FactType.INDUSTRY,
        FactType.QUOTE,
    }
    assert inmem_intel.financial_facts and inmem_intel.announcement_facts
    assert inmem_intel.latest_quote is not None

    assert _normalize(inmem_intel) == _normalize(sqlite_intel)
    print("[OK] CompanyIntelligence 读模型 InMemory == SQLite（含 facts/financial/announcement/quote）")


def test_parity_timeline_ordering_and_basis_switch() -> None:
    recorder = _record(_FullProvider(), (_MAOTAI,))
    inmem = InMemoryMarketKnowledgeRepository()
    sqlite_repo = SQLiteMarketKnowledgeRepository(path=":memory:")
    _replay(recorder, inmem)
    _replay(recorder, sqlite_repo)

    from shanhai_market_data import TimeBasis

    for kwargs in (
        {},
        {"time_basis": TimeBasis.OCCURRED_AT, "latest_first": False},
        {"time_basis": TimeBasis.CAPTURED_AT, "latest_first": True},
    ):
        inmem_tl = inmem.get_company_timeline("600519.SH", **kwargs)
        sqlite_tl = sqlite_repo.get_company_timeline("600519.SH", **kwargs)
        inmem_dump = [e.model_dump(mode="json") for e in inmem_tl]
        sqlite_dump = [e.model_dump(mode="json") for e in sqlite_tl]
        assert inmem_dump == sqlite_dump, f"timeline diverged for {kwargs}"
        assert inmem_tl  # non-empty
    print("[OK] Company Timeline 顺序与基准切换 InMemory == SQLite")


def test_parity_list_and_search_breadth() -> None:
    recorder = _record(_FakeMarketDataProvider(), _TEN)
    inmem = InMemoryMarketKnowledgeRepository()
    sqlite_repo = SQLiteMarketKnowledgeRepository(path=":memory:")
    _replay(recorder, inmem)
    _replay(recorder, sqlite_repo)

    ts_codes = tuple(_FakeMarketDataProvider._names)  # noqa: SLF001
    assert _intel_map(inmem, ts_codes) == _intel_map(sqlite_repo, ts_codes)

    inmem_list = {i.security.ts_code: _normalize(i) for i in inmem.list_company_intelligence()}
    sqlite_list = {
        i.security.ts_code: _normalize(i) for i in sqlite_repo.list_company_intelligence()
    }
    assert inmem_list == sqlite_list
    assert len(sqlite_list) == 10

    inmem_search = [_normalize(i) for i in inmem.search_company("宁德")]
    sqlite_search = [_normalize(i) for i in sqlite_repo.search_company("宁德")]
    assert inmem_search == sqlite_search
    assert len(sqlite_search) == 1
    print("[OK] list_company_intelligence / search_company 在 10 家公司上 InMemory == SQLite")


def test_durability_survives_reopen() -> None:
    recorder = _record(_FullProvider(), (_MAOTAI,))
    inmem = InMemoryMarketKnowledgeRepository()
    _replay(recorder, inmem)

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "market.db")
        writer = SQLiteMarketKnowledgeRepository(path=path)
        _replay(recorder, writer)
        del writer  # drop the writing handle; rely solely on what is on disk

        reopened = SQLiteMarketKnowledgeRepository(path=path)
        sqlite_intel = reopened.get_company_intelligence_by_ts_code("600519.SH")
        inmem_intel = inmem.get_company_intelligence_by_ts_code("600519.SH")
        assert sqlite_intel is not None and inmem_intel is not None
        assert _normalize(inmem_intel) == _normalize(sqlite_intel)
    print("[OK] SQLite 落盘后重开连接仍与 InMemory 读模型一致（durability）")


def test_idempotent_double_replay_is_noop() -> None:
    recorder = _record(_FullProvider(), (_MAOTAI,))
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "market.db")
        repo = SQLiteMarketKnowledgeRepository(path=path)

        _replay(recorder, repo)
        once_intel = _normalize(repo.get_company_intelligence_by_ts_code("600519.SH"))
        once_obs = _raw_count(path, "SELECT COUNT(*) FROM knowledge_observation", ())
        once_companies = _raw_count(path, "SELECT COUNT(*) FROM company", ())

        _replay(recorder, repo)  # replay the identical log a second time
        twice_intel = _normalize(repo.get_company_intelligence_by_ts_code("600519.SH"))
        twice_obs = _raw_count(path, "SELECT COUNT(*) FROM knowledge_observation", ())
        twice_companies = _raw_count(path, "SELECT COUNT(*) FROM company", ())

        assert once_intel == twice_intel
        assert once_obs == twice_obs, "re-ingesting identical facts must not append rows"
        assert once_companies == twice_companies == 1
    print("[OK] 同一写日志二次重放幂等（observation/company 行数稳定，读模型不变）")


def test_quote_convergence_single_spine_row() -> None:
    recorder = _record(_FullProvider(), (_MAOTAI,))
    quote = next(kw["quote"] for m, kw in recorder.calls if m == "quote")
    quote_logical_key = f"fact:{quote.security_id}:quote:{quote.trade_date.isoformat()}"

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "market.db")
        repo = SQLiteMarketKnowledgeRepository(path=path)
        _replay(recorder, repo)

        spine_rows = _raw_count(
            path,
            "SELECT COUNT(*) FROM knowledge_observation WHERE logical_key = ?",
            (quote_logical_key,),
        )
        detail_rows = _raw_count(
            path,
            "SELECT COUNT(*) FROM quote_observation q "
            "JOIN knowledge_observation o ON q.observation_id = o.observation_id "
            "WHERE o.logical_key = ?",
            (quote_logical_key,),
        )
        assert spine_rows == 1, "bundle QUOTE fact and upsert_quote must converge to one spine row"
        assert detail_rows == 1
    print("[OK] QUOTE fact 与 upsert_quote 收敛到单一 spine 行 + 单一 quote_observation 明细")


def test_sqlite_retains_observation_history_storage_only() -> None:
    """SQLite-only: storage keeps every distinct observation (append-only spine).

    Realises the Temporal replay intent without touching the contract. Re-emitting
    the same logical_key with changed content appends a new observation rather than
    overwriting, so a future ``as_of`` query could still reconstruct "what we knew
    at T". The read model still projects the latest. The in-memory reference adapter
    overwrites by fact_id and therefore cannot retain this history — that is exactly
    why the durable substrate matters.

    A dedicated temporal logical_key with fully controlled ``captured_at`` keeps the
    ordering deterministic (the bundle's own facts carry ``captured_at=now()``, so
    reusing one would make the assertion clock-dependent).
    """
    recorder = _record(_FullProvider(), (_MAOTAI,))
    bundle = _first_bundle(recorder)
    company_id = bundle["company"].company_id
    template = next(f for f in bundle["facts"] if f.fact_type is FactType.INDUSTRY)
    temporal_key = f"fact:{company_id}:test:temporal_industry"

    obs_v1 = template.model_copy(
        update={
            "fact_id": temporal_key,
            "object_value": "白酒",
            "captured_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
        }
    )
    obs_v2 = template.model_copy(
        update={
            "fact_id": temporal_key,
            "object_value": "白酒（更名）",
            "captured_at": datetime(2026, 3, 2, tzinfo=timezone.utc),
        }
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "market.db")
        sqlite_repo = SQLiteMarketKnowledgeRepository(path=path)
        _replay(recorder, sqlite_repo)
        # Two distinct-content observations under one logical_key, ascending in time.
        sqlite_repo.upsert_market_facts(company_id, (obs_v1,))
        sqlite_repo.upsert_market_facts(company_id, (obs_v2,))

        retained = _raw_count(
            path,
            "SELECT COUNT(*) FROM knowledge_observation WHERE logical_key = ?",
            (temporal_key,),
        )
        # Both "白酒" and the later "白酒（更名）" are physically present.
        assert retained == 2, "append-only spine must retain prior observations"
        assert _raw_count(
            path,
            "SELECT COUNT(*) FROM knowledge_observation "
            "WHERE logical_key = ? AND object_value = ?",
            (temporal_key, "白酒"),
        ) == 1, "the earlier observation must remain recoverable (what we knew at T)"

        # Read projection returns the latest captured observation for that key.
        intel = sqlite_repo.get_company_intelligence_by_ts_code("600519.SH")
        assert intel is not None
        projected = next(f for f in intel.facts if f.fact_id == temporal_key)
        assert projected.object_value == "白酒（更名）"

    # Contrast: the in-memory reference adapter overwrites by fact_id (no history).
    inmem = InMemoryMarketKnowledgeRepository()
    _replay(recorder, inmem)
    inmem.upsert_market_facts(company_id, (obs_v1,))
    inmem.upsert_market_facts(company_id, (obs_v2,))
    inmem_intel = inmem.get_company_intelligence_by_ts_code("600519.SH")
    assert inmem_intel is not None
    inmem_temporal = [f for f in inmem_intel.facts if f.fact_id == temporal_key]
    assert len(inmem_temporal) == 1 and inmem_temporal[0].object_value == "白酒（更名）"
    print("[OK] SQLite append-only 保留历史 observation（read 投影 latest）；InMemory 仅覆盖")


def main() -> None:
    test_parity_company_intelligence()
    test_parity_timeline_ordering_and_basis_switch()
    test_parity_list_and_search_breadth()
    test_durability_survives_reopen()
    test_idempotent_double_replay_is_noop()
    test_quote_convergence_single_spine_row()
    test_sqlite_retains_observation_history_storage_only()
    print("\nM3.3 Phase 2 Step 2 Repository Behaviour Suite 测试全部通过 ✅")


if __name__ == "__main__":
    main()
