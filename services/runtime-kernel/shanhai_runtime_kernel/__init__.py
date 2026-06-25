"""ShanHai Runtime Kernel — Run 编排内核（Runtime Kernel v0.7 Phase 1 / PR-1 skeleton）。

定位：**orchestrator，非 executor**。只编排一次 Run 的生命周期、组装语境契约
（RuntimeContext）、在合适时机委派执行与发出运行事件（RuntimeEvent）；不持有执行
能力 / 业务语义 / 状态。

owner 职责（v0.7 §0.C G3 / Q3.4）：
- 负责：Runtime lifecycle、RuntimeContext、RuntimeEvent。
- 不负责：Experience ranking、Memory、Market cognition、Agent behavior。

依赖方向（v0.5 Q5.5 / v0.7 G5）：
    runtime-kernel → agent-runtime public interface（调用非包含）
    禁止 runtime-kernel → experience-artifact
    禁止 runtime-kernel → agent-runtime internals
本包仅依赖 pydantic；PR-1 不 import 任何下游能力包（纯结构，G1）。

PR-1 范围（v0.7 §0.C / E.1 DoD，冻结）：
- 必须存在：kernel / context / lifecycle / events / types。
- 必须提供最小 contract：RuntimeKernel / RuntimeContext / RuntimeEvent / RuntimeState。
- 明确禁止：no AgentRunner integration / no RunStore change / no Experience Runtime /
  no Memory / no Domain Provider / no ArtifactReader。

注：契约分 Commit 逐步加入（Q2.4 冻结的 5-commit 顺序），导出列表随之增长。
"""

from shanhai_runtime_kernel.context import (
    ConstraintContext,
    EnvironmentContext,
    ExperienceContext,
    IdentityContext,
    MetadataContext,
    PolicyContext,
    RuntimeContext,
    TaskContext,
)
from shanhai_runtime_kernel.events import RuntimeEvent, RuntimeEventType
from shanhai_runtime_kernel.kernel import RuntimeKernel
from shanhai_runtime_kernel.lifecycle import (
    RuntimeState,
    assert_transition,
    can_transition,
)
from shanhai_runtime_kernel.types import RuntimeHandle

__all__ = [
    "RuntimeKernel",
    "RuntimeContext",
    "IdentityContext",
    "TaskContext",
    "ExperienceContext",
    "PolicyContext",
    "EnvironmentContext",
    "ConstraintContext",
    "MetadataContext",
    "RuntimeEvent",
    "RuntimeEventType",
    "RuntimeState",
    "can_transition",
    "assert_transition",
    "RuntimeHandle",
]
