"""RuntimeKernel 编排内核契约（Runtime Kernel v0.7 Phase 1 / PR-1）。

RuntimeKernel 是 **orchestrator，非 executor**：它只编排一次 Run 的生命周期、
组装 RuntimeContext、在合适时机委派执行与发出 RuntimeEvent；**不**持有执行能力、
**不**持有业务语义、**不**持有状态（三条铁律共同钉死纯编排，见 v0.6）。

owner 职责（v0.7 §0.C G3 / Q3.4，冻结）：
- 负责：Runtime lifecycle、RuntimeContext、RuntimeEvent。
- 不负责：Experience ranking、Memory、Market cognition、Agent behavior。

依赖方向（v0.5 Q5.5 / v0.7 G5，冻结）：
    runtime-kernel → agent-runtime **public interface**（调用非包含）
    禁止 runtime-kernel → experience-artifact
    禁止 runtime-kernel → agent-runtime internals

PR-1 纯结构红线（v0.7 §0.C G1）：本模块为骨架——4 个公开方法仅留
``NotImplementedError`` 占位；**禁止实例化** AgentRunner(...) / RunStore(...) /
ExperienceCandidateProvider(...)。这些名字只能作为契约说明出现在 docstring，
不得在 PR-1 被构造或调用（实际委派分别落在 PR-4 / PR-2 / PR-3）。
"""

from __future__ import annotations

from shanhai_runtime_kernel.context import RuntimeContext
from shanhai_runtime_kernel.types import RuntimeHandle


class RuntimeKernel:
    """Run 编排内核：仅 4 个公开方法 create / assemble / execute / close。

    PR-1 仅确立 API 形态与 ownership boundary，方法体留占位。
    """

    def create(self, run_id: str) -> RuntimeHandle:
        """创建一次 Run（CREATED）。PR-1 占位；身份前移到此 mint 留 PR-5。"""
        raise NotImplementedError("RuntimeKernel.create — Phase 1 PR-1 skeleton")

    def assemble(self, handle: RuntimeHandle) -> RuntimeContext:
        """组装 RuntimeContext（ASSEMBLING → READY）。PR-1 占位。

        组装语义（context assembly）由后续 Phase 实现；编排只聚合 Provider 产物，
        不自行注入执行能力（R7）。
        """
        raise NotImplementedError("RuntimeKernel.assemble — Phase 1 PR-1 skeleton")

    def execute(self, handle: RuntimeHandle, context: RuntimeContext) -> RuntimeHandle:
        """推进执行（READY → RUNNING → COMPLETED）。PR-1 占位。

        实际执行**委派** agent-runtime public interface（AgentRunner.run），
        编排不内聚执行引擎（调用非包含，PR-4）。
        """
        raise NotImplementedError("RuntimeKernel.execute — Phase 1 PR-1 skeleton")

    def close(self, handle: RuntimeHandle) -> RuntimeHandle:
        """关闭一次 Run（COMPLETED → CLOSED）。PR-1 占位。"""
        raise NotImplementedError("RuntimeKernel.close — Phase 1 PR-1 skeleton")
