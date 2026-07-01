"""ShanHai Market Intelligence — Context Layer（见 ADR 0019 + 修订 R1）。

M3.4：ShanHai 从「可持久化基础设施」迈向「认知系统」的分水岭。本层回答
「在某个时间点，关于某主体，系统**认为自己知道什么**」——不是「今天有哪些
数据」。核心产物 ``MarketContextSnapshot``（ref-based 认知快照），由
``ContextAssembler`` 从 market-data 的 append-only observation spine 确定性组装。

依赖方向（ADR 0019 §5 R1 修订，单向不成环）：
    runtime-kernel → reasoning-engine → market-intelligence → market-data
本模块 import market-data（下游 import 上游）；**market-data 永远不知道本模块
存在**（R1-1 铁律）。本模块读 market-data 只经 ``ObservationReadPort`` 只读端口，
不 import 存储实现；cognition_state 只引用 experience 的 id/ref，不 import
experience 模块。

S1（本次）范围：package skeleton + domain models（ref-based Snapshot + 值对象）
+ ContextAssembler 骨架（NotImplementedError）+ ObservationReadPort 端口契约
（落 market-data 侧）。**不接任何数据库**。

不在范围（持续冻结，见 ADR 0019 §4）：任何 provider 接入（iFinD/Wind/akshare）/
LLM / Agent / Reasoning / Knowledge Object 物化 / context_snapshot 落表 /
推理 / 总结 / 判断（第一版 ContextAssembler 纯 deterministic）。
"""

from shanhai_market_intelligence.assembler import (
    CognitionRefReader,
    ContextAssembler,
)
from shanhai_market_intelligence.models import (
    AsOf,
    CognitionRef,
    CognitionState,
    Conflict,
    DataQuality,
    KnowledgeRef,
    MarketContextSnapshot,
    MarketState,
    ObservationRef,
)

__all__ = [
    "AsOf",
    "ObservationRef",
    "KnowledgeRef",
    "MarketState",
    "CognitionRef",
    "CognitionState",
    "Conflict",
    "DataQuality",
    "MarketContextSnapshot",
    "ContextAssembler",
    "CognitionRefReader",
]
