"""M3.6.3 Observation Materialization — 契约测试（§6 十四用例）。

验证 m3.6.3 rev 2 冻结的 Identity 边界，全部离线、无网络、无 SQLite：
  Identity 算法可纯函数单测（这是把它单独冻结的最大收益）；spine 走既有内存
  ``InMemoryObservationReadPort`` 做 append-only 写回 + 读回校验（不接真实源、不改 spine）。

覆盖用户点名的 5 条（①②③④⑤）+ 幂等/修订/provenance/粒度/AST 守护（⑥⑦⑧⑨⑩）
+ rev 2 新增 4 条（⑪ scope-key per fact_type / ⑫ canonical serializer / ⑬ dedup≠conflict
/ ⑭ identity 与 materializer 解耦）。

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_observation_materializer
"""

from __future__ import annotations

import ast
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from shanhai_market_data import (
    CanonicalSerializer,
    DefaultEffectiveScopeStrategy,
    DefaultIdentityStrategy,
    IngestReport,
    ObservationDraft,
    ObservationIdentity,
    ObservationMaterializer,
    SourceRef,
    SubjectRef,
    ingest_drafts,
)
from shanhai_market_data.models import FactType
from shanhai_market_data.ports.in_memory_observation_reader import InMemoryObservationReadPort
from shanhai_market_data.ports.observation_reader import Observation

ROOT = Path(__file__).resolve().parents[2]

# --- fixtures ----------------------------------------------------------------

_SUBJECT = SubjectRef(entity_type="company", entity_id="company:600519", label="贵州茅台")
_SOURCE = SourceRef(source_id="eastmoney", source_name="EastMoney", provider="eastmoney")


def _materializer() -> ObservationMaterializer:
    return ObservationMaterializer(DefaultIdentityStrategy())


def _quote_draft(
    *,
    object_value: str = "1194.96",
    occurred_at: datetime = datetime(2026, 6, 30, 15, 0, 0),
    captured_at: datetime = datetime(2026, 6, 30, 18, 0, 0),
    source: SourceRef = _SOURCE,
    predicate: str = "quote.close",
) -> ObservationDraft:
    return ObservationDraft(
        subject=_SUBJECT,
        fact_type=FactType.QUOTE,
        predicate=predicate,
        object_value=object_value,
        occurred_at=occurred_at,
        captured_at=captured_at,
        source_ref=source,
    )


# --- ① same draft → same hash（确定性）---------------------------------------


def test_same_draft_same_identity() -> None:
    m = _materializer()
    a = m.materialize(_quote_draft())
    b = m.materialize(_quote_draft())
    assert (a.logical_key, a.content_hash) == (b.logical_key, b.content_hash)
    assert a.content_hash.startswith("sha256:")
    print("[OK] ① same draft → same (logical_key, content_hash)（确定性）")


# --- ② value different → hash different --------------------------------------


def test_value_change_changes_hash() -> None:
    m = _materializer()
    a = m.materialize(_quote_draft(object_value="1194.96"))
    b = m.materialize(_quote_draft(object_value="1200.00"))
    assert a.logical_key == b.logical_key
    assert a.content_hash != b.content_hash
    print("[OK] ② object_value 变 → content_hash 变（同 logical_key）")


# --- ③ source different, content same → identity same ------------------------


def test_source_excluded_from_identity() -> None:
    m = _materializer()
    a = m.materialize(_quote_draft(source=_SOURCE))
    other = SourceRef(
        source_id="akshare",
        source_name="akshare",
        provider="akshare",
        hash="sha256:deadbeef",
    )
    b = m.materialize(_quote_draft(source=other))
    assert (a.logical_key, a.content_hash) == (b.logical_key, b.content_hash)
    print("[OK] ③ 换源不改身份（source_ref 不参与 identity）")


# --- ④ captured_at different, content same → identity same -------------------


def test_captured_at_excluded_from_identity() -> None:
    m = _materializer()
    a = m.materialize(_quote_draft(captured_at=datetime(2026, 6, 30, 18, 0, 0)))
    b = m.materialize(_quote_draft(captured_at=datetime(2026, 7, 1, 9, 0, 0)))
    assert (a.logical_key, a.content_hash) == (b.logical_key, b.content_hash)
    print("[OK] ④ captured_at 不参与 identity（knowledge time，非取值）")


# --- ⑤ predicate changed → new logical_key -----------------------------------


def test_predicate_change_new_timeline() -> None:
    m = _materializer()
    a = m.materialize(_quote_draft(predicate="quote.close"))
    b = m.materialize(_quote_draft(predicate="quote.open"))
    assert a.logical_key != b.logical_key
    print("[OK] ⑤ predicate 变 → 新 logical_key（新时间线）")


# --- ⑥ idempotent re-ingest --------------------------------------------------


def test_ingest_is_idempotent() -> None:
    m = _materializer()
    port = InMemoryObservationReadPort()
    drafts = (_quote_draft(),)
    r1 = ingest_drafts(drafts, writer=port, materializer=m)
    r2 = ingest_drafts(drafts, writer=port, materializer=m)
    assert isinstance(r1, IngestReport) and r1.ingested == 1 and r2.ingested == 1
    rows = port.query(_SUBJECT, knowledge_at=datetime(2027, 1, 1))
    assert len(rows) == 1  # 同 identity 幂等，spine 不新增第二行
    print("[OK] ⑥ 同 draft 二次 ingest → spine 行数不增（幂等）")


# --- ⑦ value revision → new row same timeline --------------------------------


def test_value_revision_appends_row() -> None:
    m = _materializer()
    port = InMemoryObservationReadPort()
    ingest_drafts((_quote_draft(object_value="1194.96"),), writer=port, materializer=m)
    ingest_drafts((_quote_draft(object_value="1200.00"),), writer=port, materializer=m)
    rows = port.query(_SUBJECT, knowledge_at=datetime(2027, 1, 1))
    assert len(rows) == 2  # 同 logical_key、新 content_hash → 修订入历史
    assert len({r.logical_key for r in rows}) == 1
    assert len({r.content_hash for r in rows}) == 2
    print("[OK] ⑦ 值修订 → 同时间线新增一行（append-only 修订）")


# --- ⑧ provenance first-writer-wins ------------------------------------------


def test_provenance_first_writer_wins() -> None:
    m = _materializer()
    port = InMemoryObservationReadPort()
    east = _quote_draft(source=SourceRef(source_id="eastmoney", source_name="EastMoney", provider="eastmoney"))
    aksh = _quote_draft(source=SourceRef(source_id="akshare", source_name="akshare", provider="akshare"))
    ingest_drafts((east,), writer=port, materializer=m)
    ingest_drafts((aksh,), writer=port, materializer=m)
    rows = port.query(_SUBJECT, knowledge_at=datetime(2027, 1, 1))
    assert len(rows) == 1  # 同值不同源 → 幂等丢弃第二条
    assert rows[0].source_ref.provider == "eastmoney"  # 保留首个写入者的 SourceRef
    print("[OK] ⑧ provenance first-writer-wins（两源同值保留首个 SourceRef）")


# --- ⑨ effective_scope granularity -------------------------------------------


def test_effective_scope_granularity() -> None:
    m = _materializer()
    # 不同交易日 → 不同 logical_key（各成时间线）
    d1 = m.materialize(_quote_draft(occurred_at=datetime(2026, 6, 30, 15, 0, 0)))
    d2 = m.materialize(_quote_draft(occurred_at=datetime(2026, 7, 1, 15, 0, 0)))
    assert d1.logical_key != d2.logical_key
    # 同交易日不同秒级 occurred_at → 同 logical_key（粗粒度到日）
    s1 = m.materialize(_quote_draft(occurred_at=datetime(2026, 6, 30, 15, 0, 1)))
    s2 = m.materialize(_quote_draft(occurred_at=datetime(2026, 6, 30, 15, 0, 59)))
    assert s1.logical_key == s2.logical_key
    assert s1.logical_key.endswith("|2026-06-30")
    print("[OK] ⑨ effective_scope 粗粒度到日（换源/秒差不裂身份，跨日各成时间线）")


# --- ⑩ boundary AST guard ----------------------------------------------------


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def _code_identifiers(path: Path) -> set[str]:
    """Collect lowercased code identifiers via AST (names / attrs / defs).

    Deliberately excludes docstrings, string literals and comments: the module's
    own boundary prose legitimately says "不调 LLM / 不产 Knowledge", which must
    not be mistaken for actually using those symbols (AST-guard style).
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    idents: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            idents.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            idents.add(node.attr.lower())
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            idents.add(node.name.lower())
    return idents


def test_materializer_module_boundary() -> None:
    module = ROOT / "services" / "market-data" / "shanhai_market_data" / "observation_materializer.py"
    imported = _imports(module)
    forbidden = {
        "shanhai_market_intelligence",
        "shanhai_runtime_kernel",
        "shanhai_experience_runtime",
        "shanhai_memory",
        "shanhai_experience_evolution",
    }
    leaked = imported & forbidden
    assert not leaked, f"observation_materializer 越界 import: {sorted(leaked)}"
    idents = _code_identifiers(module)
    forbidden_symbols = {"belief", "knowledgeobject", "model_router", "llm", "reasoning", "sqlite"}
    leaked_symbols = idents & forbidden_symbols
    assert not leaked_symbols, f"observation_materializer 泄漏认知/持久化符号: {sorted(leaked_symbols)}"
    print("[OK] ⑩ 模块边界：不 import intelligence/runtime/evolution、代码不含 LLM/Knowledge/SQLite 符号")


# --- ⑪ scope key per fact_type（Blocking 2）----------------------------------


def test_scope_key_per_fact_type() -> None:
    scope = DefaultEffectiveScopeStrategy()
    occurred = datetime(2026, 3, 31, 0, 0, 0)

    quote = _quote_draft(occurred_at=datetime(2026, 7, 1, 15, 0, 0))
    assert scope.scope_of(quote) == "2026-07-01"  # QUOTE → trade_date

    financial = ObservationDraft(
        subject=_SUBJECT, fact_type=FactType.FINANCIAL, predicate="fin.revenue",
        object_value="54702912385.23", occurred_at=occurred,
        captured_at=datetime(2026, 4, 30), source_ref=_SOURCE,
    )
    assert scope.scope_of(financial) == "2026-03-31"  # FINANCIAL → report_period

    ann_source = SourceRef(source_id="cninfo", source_name="CNInfo", external_id="1225379934")
    announcement = ObservationDraft(
        subject=_SUBJECT, fact_type=FactType.ANNOUNCEMENT, predicate="ann.title",
        object_value="权益分派实施公告", occurred_at=datetime(2026, 6, 22),
        captured_at=datetime(2026, 6, 22), source_ref=ann_source,
    )
    assert scope.scope_of(announcement) == "1225379934"  # ANNOUNCEMENT → announcement_id（非日期）

    profile = ObservationDraft(
        subject=_SUBJECT, fact_type=FactType.PROFILE, predicate="profile.industry",
        object_value="白酒Ⅱ", captured_at=datetime(2026, 6, 30), source_ref=_SOURCE,
    )
    assert scope.scope_of(profile) == ""  # PROFILE → latest-only 空段

    # logical_key 全链体现具名键
    m = _materializer()
    assert m.materialize(announcement).logical_key.endswith("|1225379934")
    assert m.materialize(profile).logical_key.endswith("|")
    print("[OK] ⑪ scope key per fact_type（trade_date/report_period/announcement_id/latest-only）")


# --- ⑫ canonical serializer 稳定（Non-blocking 2）----------------------------


def test_canonical_serializer_stable() -> None:
    s = CanonicalSerializer()
    # 键序打乱 → 同 bytes
    assert s.dumps({"b": 1, "a": 2}) == s.dumps({"a": 2, "b": 1})
    # None / bool 不与 0/1 混
    assert s.dumps(None) == "null"
    assert s.dumps(True) == "true" and s.dumps(False) == "false"
    assert s.dumps(True) != s.dumps(1)
    # float 与等值 Decimal-string 归一到同一定点表示（消解二进制浮点误差）
    assert s.dumps(10.57) == s.dumps(Decimal("10.57")) == '"10.57"'
    # 科学计数法被消解为定点（1E+2 → "100"，不泄漏指数形式）
    assert s.dumps(Decimal("1E+2")) == '"100"'
    assert "E" not in s.dumps(Decimal("1E+2")) and "e" not in s.dumps(Decimal("1E+2"))
    # datetime → ISO-8601
    assert s.dumps(datetime(2026, 7, 1, 15, 0, 0)) == '"2026-07-01T15:00:00"'
    # 序列保留顺序（顺序即语义）
    assert s.dumps([1, 2]) != s.dumps([2, 1])
    print("[OK] ⑫ CanonicalSerializer 稳定（键序/None/bool/float=Decimal/datetime/顺序）")


# --- ⑬ dedup ≠ conflict（Non-blocking 3）------------------------------------


def test_dedup_is_not_conflict_resolution() -> None:
    m = _materializer()
    port = InMemoryObservationReadPort()
    # 同 logical_key、不同 object_value（值分歧，非完全相同 identity）
    ingest_drafts((_quote_draft(object_value="1194.96"),), writer=port, materializer=m)
    ingest_drafts((_quote_draft(object_value="1200.00"),), writer=port, materializer=m)
    rows = port.query(_SUBJECT, knowledge_at=datetime(2027, 1, 1))
    # 都各自 append 成行——本层不判定谁对、不合并（冲突调和留 Evolution）
    assert len(rows) == 2
    assert {r.object_value for r in rows} == {"1194.96", "1200.00"}
    assert len({r.logical_key for r in rows}) == 1
    print("[OK] ⑬ dedup ≠ conflict（值分歧两行都保留，本层不取舍/不合并）")


# --- ⑭ identity decoupled from materializer（Blocking 1）---------------------


class _StubIdentityStrategy:
    """固定 identity 的 stub——证明 Materializer 无自有 key 规则（策略可替换、无需 mock）。"""

    def identify(self, draft: ObservationDraft) -> ObservationIdentity:
        return ObservationIdentity(logical_key="stub|key", content_hash="sha256:stub")


def test_identity_is_decoupled_from_materializer() -> None:
    m = ObservationMaterializer(_StubIdentityStrategy())
    obs = m.materialize(_quote_draft(object_value="whatever"))
    # Materializer 输出的身份完全等于 stub 值 → 它不含自有 key 拼接规则
    assert (obs.logical_key, obs.content_hash) == ("stub|key", "sha256:stub")
    # 但语义字段仍如实搬运（纯组装职责）
    assert obs.object_value == "whatever" and obs.fact_type is FactType.QUOTE
    assert isinstance(obs, Observation)
    print("[OK] ⑭ identity 与 Materializer 解耦（注入 stub 即替换身份，Materializer 无 key 规则）")


def main() -> None:
    test_same_draft_same_identity()
    test_value_change_changes_hash()
    test_source_excluded_from_identity()
    test_captured_at_excluded_from_identity()
    test_predicate_change_new_timeline()
    test_ingest_is_idempotent()
    test_value_revision_appends_row()
    test_provenance_first_writer_wins()
    test_effective_scope_granularity()
    test_materializer_module_boundary()
    test_scope_key_per_fact_type()
    test_canonical_serializer_stable()
    test_dedup_is_not_conflict_resolution()
    test_identity_is_decoupled_from_materializer()
    print("\nM3.6.3 Observation Materialization 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
