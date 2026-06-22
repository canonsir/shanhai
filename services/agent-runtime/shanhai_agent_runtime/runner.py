"""AgentRunner — 生命周期编排与运行记录。

驱动 think → act → observe 循环，管理 AgentStatus 流转，
并将每一步记录为 Step，最终汇总为 RunResult（见 ADR 0006）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from shanhai_agent_runtime.types import (
    AgentStatus,
    RunResult,
    Step,
    StepType,
)

if TYPE_CHECKING:
    from shanhai_agent_runtime.agent import BaseAgent


class AgentRunner:
    def __init__(self, agent: "BaseAgent") -> None:
        self.agent = agent

    def run(self, input: Any = None) -> RunResult:
        ctx = self.agent.new_context(input)
        status = AgentStatus.RUNNING
        output: Any = None
        error: str | None = None

        try:
            for _ in range(max(1, self.agent.max_steps)):
                plan = self.agent.think(ctx)
                ctx.record(Step(index=0, type=StepType.THINK, content=plan.thought))

                result = self.agent.act(ctx, plan)
                ctx.record(
                    Step(
                        index=0,
                        type=StepType.ACT,
                        content=plan.answer or "",
                        tool=plan.tool,
                        tool_args=plan.tool_args,
                        tool_result=getattr(result, "data", result),
                    )
                )
                output = result

                done = self.agent.observe(ctx, plan, result)
                ctx.record(
                    Step(index=0, type=StepType.OBSERVE, content="done" if done else "continue")
                )
                if done:
                    break

            status = AgentStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001 - 运行时需捕获并结构化记录失败
            status = AgentStatus.FAILED
            error = f"{type(exc).__name__}: {exc}"

        return RunResult(
            agent=self.agent.name,
            status=status,
            output=output,
            steps=ctx.steps,
            error=error,
        )
