"""ProviderRegistry + ProviderDescriptor — provider 装配边界（M3.6.2 骨架）。

落 M3.6.1 [Composition Root Design] 冻结的装配边界（D1 四层分类 / D5 Selection
Boundary）与用户裁决「Registry 只管理 ``ProviderDescriptor``，不直接管理
Provider 实例」。

设计要点：
- Registry 持有的是 ``ProviderDescriptor``（元数据 + factory），**不是** provider
  实例。构建 ``Descriptor → Factory → Provider`` 是 Composition Root 的事
  （[composition_root.py]），不是 Registry 的事。
- 因此以后接 iFinD / Wind / Mock 只是在 Descriptor 上增加 metadata，Registry
  代码永不改。
- Registry **只负责组合**：登记、按 id 取、列出、筛启用。**不负责**请求 /
  调度 / fallback / merge —— 那些是后续 ingestion / selection policy 的关注点
  （ADR 0021 D7 登记的未来项），本骨架刻意不暴露这些 surface。

命名：与既有 [registry.py] 的 ``IdentityRegistry``（entity 身份映射，无关）
区分——本模块是 provider 装配注册表，故独立文件 ``provider_registry.py``。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from shanhai_market_data.observation_provider import ObservationProvider


class ProviderTier(str, Enum):
    """Provider 四层分类（M3.6.1 D1 冻结）。

    分类只影响**装配与选择**，不影响**输出契约**——四层都实现同一个
    ``ObservationProvider``（M3.6.0 §2.2）。
    """

    DEFAULT = "default"
    OPTIONAL_FREE = "optional_free"
    OPTIONAL_COMMERCIAL = "optional_commercial"
    TEST = "test"


@dataclass(frozen=True)
class ProviderDescriptor:
    """一个 provider 的装配元数据（不是 provider 实例本身）。

    Registry 管理它而非 provider 实例：``factory`` 是「怎么造出 provider」的
    延迟构造器，真正调用发生在 Composition Root（且 M3.6.2 骨架阶段对真实源
    刻意 **不调用** factory，adapter 属 M3.6.4+）。

    字段（用户裁决 M3.6.2）：
    - ``id``：provider 稳定标识（如 "eastmoney" / "ifind"），Registry 内唯一。
    - ``tier``：四层分类（``ProviderTier``），决定装配/选择行为，不决定契约。
    - ``enabled``：是否启用。Default 默认 True；Optional 默认 False，opt-in。
    - ``factory``：``() -> ObservationProvider`` 延迟构造器；Registry 只持有、
      不调用。缺 credential 时构造/降级由 factory 与组合根负责，Registry 不管。
    - ``requires_credentials``：本 provider 声明所需 credential 的 env 键
      （如 ``("IFIND_TOKEN",)``；D4）。仅声明，Registry / provider 不读业务配置、
      不把 credential 写进 Observation。
    """

    id: str
    tier: ProviderTier
    enabled: bool
    factory: Callable[[], ObservationProvider]
    requires_credentials: tuple[str, ...] = field(default=())


class ProviderRegistry:
    """provider 装配注册表——只组合，不请求 / 调度 / fallback / merge。

    持有一组 ``ProviderDescriptor``，提供登记与查询。它是装配层组件，Context /
    Evolution / Ingestion 对它无感知（M3.6.1 D5）。它**不**发起取数、**不**做
    多 provider 路由/回退/合并——那些是 ingestion pipeline 与 selection policy
    的关注点（ADR 0021 D7 未来项），本骨架不暴露这些 surface。
    """

    def __init__(self) -> None:
        self._descriptors: dict[str, ProviderDescriptor] = {}

    def register(self, descriptor: ProviderDescriptor) -> None:
        """登记一个 descriptor；重复 id 视为装配错误，拒绝覆盖。"""
        if descriptor.id in self._descriptors:
            raise ValueError(f"provider id already registered: {descriptor.id!r}")
        self._descriptors[descriptor.id] = descriptor

    def resolve(self, provider_id: str) -> ProviderDescriptor:
        """按 id 取 descriptor（返回元数据，**不**构造 provider 实例）。"""
        try:
            return self._descriptors[provider_id]
        except KeyError:
            raise KeyError(f"unknown provider id: {provider_id!r}") from None

    def list(self) -> tuple[ProviderDescriptor, ...]:
        """按登记顺序列出全部 descriptor。"""
        return tuple(self._descriptors.values())

    def enabled(self) -> tuple[ProviderDescriptor, ...]:
        """按登记顺序列出 ``enabled=True`` 的 descriptor。"""
        return tuple(d for d in self._descriptors.values() if d.enabled)
