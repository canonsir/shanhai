"""Composition Root — provider 装配骨架（M3.6.2）。

落 M3.6.1 [Composition Root Design] 的 D2 默认组合 + D3 Optional 插槽 +
D5 Selection Boundary：这是**唯一**知道「有哪些 provider、谁是默认、谁是
optional」的地方（ADR 0021 D6-5 / D7）。ingestion / observation / knowledge /
context 四层永远只见 ``ObservationProvider`` 契约，永不见「是哪个源」。

M3.6.2 边界（用户裁决，⛔ 严格遵守）：
- **不接任何真实源、不写任何 adapter、不 HTTP、不 akshare、不 SQLite、不
  Persistence、不 Normalize。**
- Descriptor 的 ``factory`` 一律 **pending**：真实 adapter（EastMoney/CNInfo/
  iFinD... → ``ObservationDraft``）属 M3.6.4+。本阶段 factory 被调用即
  ``raise NotImplementedError``——骨架只装配 Descriptor 元数据，**不真正构造/
  调用 provider**。
- 默认组合 = EastMoney + CNInfo（直连免费源，canonical 默认）；Optional
  Commercial = Tushare / iFinD / Wind（默认关闭、opt-in、声明 credential）。
- **不出现 akshare**（Optional Free，属 M3.6.5，本阶段不登记）。

装配风格对齐既有 [factory.py]（``default_market_store()`` 的 env 分支风格）。
"""

from __future__ import annotations

from shanhai_market_data.observation_provider import ObservationProvider
from shanhai_market_data.provider_registry import (
    ProviderDescriptor,
    ProviderRegistry,
    ProviderTier,
)


def _pending_factory(provider_id: str):
    """返回一个「尚未实现」的 factory。

    M3.6.2 骨架阶段刻意不构造真实 provider（adapter 属 M3.6.4+）。Registry
    只持有 Descriptor 元数据；一旦有人真的去 build 这个 provider，就明确报错，
    杜绝「骨架被误当成能取数」。
    """

    def factory() -> ObservationProvider:
        raise NotImplementedError(
            f"provider adapter not implemented yet (M3.6.2 skeleton): {provider_id!r}"
        )

    return factory


def build_provider_registry() -> ProviderRegistry:
    """装配默认 provider 注册表（骨架：只登记 Descriptor，不构造 provider）。

    - Default（无 credential、默认启用、canonical 默认数据入口）：
      EastMoney（行情/财务/画像）+ CNInfo（披露公告）。
    - Optional Commercial（需 credential、默认关闭、opt-in）：
      Tushare（token+积分+权限）/ iFinD（商业授权）/ Wind（商业授权）。
      永久保留配置位——启停只是 ``enabled`` 开关，不删/加代码。

    Optional 缺 credential 时不启用、不报错阻断（D3 优雅降级）。akshare
    （Optional Free）属 M3.6.5，本阶段不登记。
    """
    registry = ProviderRegistry()

    # --- Default（canonical，默认启用，无 credential）------------------------
    registry.register(
        ProviderDescriptor(
            id="eastmoney",
            tier=ProviderTier.DEFAULT,
            enabled=True,
            factory=_pending_factory("eastmoney"),
        )
    )
    registry.register(
        ProviderDescriptor(
            id="cninfo",
            tier=ProviderTier.DEFAULT,
            enabled=True,
            factory=_pending_factory("cninfo"),
        )
    )

    # --- Optional Commercial（默认关闭，opt-in，声明 credential）-------------
    registry.register(
        ProviderDescriptor(
            id="tushare",
            tier=ProviderTier.OPTIONAL_COMMERCIAL,
            enabled=False,
            factory=_pending_factory("tushare"),
            requires_credentials=("TUSHARE_TOKEN",),
        )
    )
    registry.register(
        ProviderDescriptor(
            id="ifind",
            tier=ProviderTier.OPTIONAL_COMMERCIAL,
            enabled=False,
            factory=_pending_factory("ifind"),
            requires_credentials=("IFIND_APP_KEY", "IFIND_APP_SECRET"),
        )
    )
    registry.register(
        ProviderDescriptor(
            id="wind",
            tier=ProviderTier.OPTIONAL_COMMERCIAL,
            enabled=False,
            factory=_pending_factory("wind"),
            requires_credentials=("WIND_TOKEN",),
        )
    )

    return registry
