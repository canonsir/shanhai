"""M3.6.2 Provider Skeleton — 契约测试（骨架，无真实源）。

验证 M3.6.2 冻结的四件事，全部离线、无网络、无持久化：
  ① ObservationProvider Protocol（runtime_checkable，单方法无身份）
  ② ObservationDraft（8 字段、无身份、frozen）+ DataQuery（frozen）
  ③ ProviderRegistry + ProviderDescriptor（只组合，无请求 surface）
  ④ Composition Root skeleton（Default 组合 / Optional 插槽 / factory pending）

对齐 M3.6.1 装配边界：Registry 管理 Descriptor 而非 provider 实例；本阶段
Descriptor.factory 一律 pending（真实 adapter 属 M3.6.4+），骨架不真正构造
或调用任何 provider、不接任何源、不出现 akshare。

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_observation_provider_skeleton
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime

from shanhai_market_data import (
    DataQuery,
    ObservationDraft,
    ObservationProvider,
    ProviderDescriptor,
    ProviderRegistry,
    ProviderTier,
    SourceRef,
    SubjectRef,
    build_provider_registry,
)
from shanhai_market_data.models import FactType, _FrozenModel

# --- fixtures ----------------------------------------------------------------

_SUBJECT = SubjectRef(entity_type="company", entity_id="company:600519", label="贵州茅台")
_SOURCE = SourceRef(source_id="mock", source_name="mock source")


class _MockObservationProvider:
    """确定性 mock ObservationProvider（duck-typed，仅测试用，非数据源）。"""

    name = "mock"

    def __init__(self, drafts: tuple[ObservationDraft, ...] = ()) -> None:
        self._drafts = drafts

    def fetch_observations(self, query: DataQuery) -> tuple[ObservationDraft, ...]:
        return self._drafts


def _draft() -> ObservationDraft:
    return ObservationDraft(
        subject=_SUBJECT,
        fact_type=FactType.QUOTE,
        predicate="quote.close",
        object_value="1194.96",
        captured_at=datetime(2026, 6, 30, 15, 0, 0),
        source_ref=_SOURCE,
    )


# --- ① ObservationDraft / DataQuery 契约 --------------------------------------


def test_draft_has_no_identity_fields() -> None:
    """draft 有语义、无身份：不得含 logical_key / content_hash / confidence。"""
    fields = set(ObservationDraft.model_fields)
    forbidden = {"logical_key", "content_hash", "observation_id", "version", "confidence"}
    leaked = fields & forbidden
    assert not leaked, f"ObservationDraft 泄漏身份/信念字段: {sorted(leaked)}"
    assert fields == {
        "subject",
        "fact_type",
        "predicate",
        "object_value",
        "occurred_at",
        "published_at",
        "captured_at",
        "source_ref",
    }
    print("[OK] ObservationDraft 8 字段、无身份/信念字段")


def test_draft_is_frozen_and_strict() -> None:
    d = _draft()
    assert issubclass(ObservationDraft, _FrozenModel)
    try:
        d.object_value = "999"  # type: ignore[misc]
        assert False, "ObservationDraft 应 frozen，赋值须报错"
    except Exception:
        pass
    try:
        ObservationDraft(
            subject=_SUBJECT,
            fact_type=FactType.QUOTE,
            captured_at=datetime(2026, 6, 30),
            source_ref=_SOURCE,
            logical_key="x",  # type: ignore[call-arg]
        )
        assert False, "extra=forbid：draft 不接受 logical_key 等额外字段"
    except Exception:
        pass
    print("[OK] ObservationDraft frozen + extra=forbid")


def test_data_query_defaults_and_frozen() -> None:
    q = DataQuery(subject=_SUBJECT)
    assert q.fact_types == ()
    assert q.since is None and q.until is None and q.limit is None
    assert issubclass(DataQuery, _FrozenModel)
    q2 = DataQuery(subject=_SUBJECT, fact_types=(FactType.QUOTE, FactType.FINANCIAL), limit=10)
    assert q2.fact_types == (FactType.QUOTE, FactType.FINANCIAL)
    assert q2.limit == 10
    print("[OK] DataQuery 默认值 + frozen")


# --- ② ObservationProvider Protocol ------------------------------------------


def test_provider_protocol_runtime_checkable() -> None:
    provider = _MockObservationProvider(drafts=(_draft(),))
    assert isinstance(provider, ObservationProvider)
    out = provider.fetch_observations(DataQuery(subject=_SUBJECT))
    assert isinstance(out, tuple) and len(out) == 1
    assert isinstance(out[0], ObservationDraft)

    class _NotAProvider:
        name = "nope"

    assert not isinstance(_NotAProvider(), ObservationProvider)
    print("[OK] ObservationProvider runtime_checkable，mock 满足 / 缺方法者不满足")


# --- ③ ProviderRegistry + ProviderDescriptor ---------------------------------


def _mock_descriptor(provider_id: str = "mock", enabled: bool = True) -> ProviderDescriptor:
    return ProviderDescriptor(
        id=provider_id,
        tier=ProviderTier.TEST,
        enabled=enabled,
        factory=lambda: _MockObservationProvider(),
    )


def test_registry_register_resolve_list_enabled() -> None:
    reg = ProviderRegistry()
    reg.register(_mock_descriptor("a", enabled=True))
    reg.register(_mock_descriptor("b", enabled=False))

    assert reg.resolve("a").id == "a"
    assert {d.id for d in reg.list()} == {"a", "b"}
    assert {d.id for d in reg.enabled()} == {"a"}

    try:
        reg.resolve("missing")
        assert False, "resolve 未知 id 应报错"
    except KeyError:
        pass
    try:
        reg.register(_mock_descriptor("a"))
        assert False, "重复 id 应拒绝覆盖"
    except ValueError:
        pass
    print("[OK] ProviderRegistry register/resolve/list/enabled")


def test_descriptor_manages_metadata_not_instance() -> None:
    """Registry 持有 Descriptor（元数据 + factory），resolve 不构造 provider。"""
    reg = ProviderRegistry()
    reg.register(_mock_descriptor("mock"))
    desc = reg.resolve("mock")
    assert isinstance(desc, ProviderDescriptor)
    # resolve 返回的是 descriptor，不是 provider 实例——构造是组合根的事。
    assert not isinstance(desc, ObservationProvider)
    # descriptor 是 frozen dataclass。
    try:
        desc.enabled = False  # type: ignore[misc]
        assert False, "ProviderDescriptor 应 frozen"
    except FrozenInstanceError:
        pass
    # factory 由组合根按需调用，构造出的实例满足契约。
    provider = desc.factory()
    assert isinstance(provider, ObservationProvider)
    print("[OK] Registry 管理 Descriptor 元数据而非 provider 实例，factory 延迟构造")


def test_registry_has_no_request_surface() -> None:
    """Registry 只组合：不得暴露请求/调度/fallback/merge。"""
    surface = set(dir(ProviderRegistry))
    forbidden = {
        "fetch",
        "fetch_observations",
        "ingest",
        "schedule",
        "fallback",
        "merge",
        "select",
        "route",
    }
    leaked = surface & forbidden
    assert not leaked, f"ProviderRegistry 泄漏非组合职责 surface: {sorted(leaked)}"
    print("[OK] ProviderRegistry 无请求/调度/fallback/merge surface")


# --- ④ Composition Root skeleton ---------------------------------------------


def test_default_registry_composition() -> None:
    reg = build_provider_registry()
    ids = {d.id for d in reg.list()}
    # Default 组合 = EastMoney + CNInfo，默认启用。
    defaults = {d.id for d in reg.enabled()}
    assert {"eastmoney", "cninfo"} <= defaults
    for did in ("eastmoney", "cninfo"):
        d = reg.resolve(did)
        assert d.tier is ProviderTier.DEFAULT
        assert d.enabled is True
        assert d.requires_credentials == ()
    # 本阶段不出现 akshare（Optional Free，属 M3.6.5）。
    assert "akshare" not in ids
    print("[OK] Composition Root：Default 组合 EastMoney+CNInfo 默认启用，无 akshare")


def test_commercial_slots_disabled_with_credentials() -> None:
    reg = build_provider_registry()
    for did in ("tushare", "ifind", "wind"):
        d = reg.resolve(did)
        assert d.tier is ProviderTier.OPTIONAL_COMMERCIAL
        assert d.enabled is False
        assert len(d.requires_credentials) >= 1
    # Disabled registry 视角：enabled() 只含 default，不含任何 commercial。
    enabled_ids = {d.id for d in reg.enabled()}
    assert enabled_ids.isdisjoint({"tushare", "ifind", "wind"})
    print("[OK] Composition Root：Optional Commercial 插槽默认关闭 + 声明 credential")


def test_skeleton_factories_are_pending() -> None:
    """骨架不接真实源：Default/Commercial 的 factory 被调用即 NotImplementedError。"""
    reg = build_provider_registry()
    for did in ("eastmoney", "cninfo", "tushare", "ifind", "wind"):
        try:
            reg.resolve(did).factory()
            assert False, f"{did} factory 应 pending（M3.6.2 不接真实源）"
        except NotImplementedError:
            pass
    print("[OK] Composition Root：所有真实源 factory pending（骨架不构造/不调用）")


def main() -> None:
    test_draft_has_no_identity_fields()
    test_draft_is_frozen_and_strict()
    test_data_query_defaults_and_frozen()
    test_provider_protocol_runtime_checkable()
    test_registry_register_resolve_list_enabled()
    test_descriptor_manages_metadata_not_instance()
    test_registry_has_no_request_surface()
    test_default_registry_composition()
    test_commercial_slots_disabled_with_credentials()
    test_skeleton_factories_are_pending()
    print("\nM3.6.2 Provider Skeleton 契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
