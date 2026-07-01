"""market-data ports — 对外只读契约（M3.4 additive）。

放 market-data 暴露给下游（market-intelligence）的只读端口 Protocol 与其
DTO。端口的签名只用基元类型，绝不 import 任何 intelligence 概念（R1 铁律
「market-data 永远不知道 intelligence 存在」）。
"""

from shanhai_market_data.ports.in_memory_observation_reader import (
    InMemoryObservationReadPort,
)
from shanhai_market_data.ports.observation_reader import (
    Observation,
    ObservationReadPort,
)

__all__ = [
    "Observation",
    "ObservationReadPort",
    "InMemoryObservationReadPort",
]
