"""Runtime Kernel 支撑类型（Runtime Kernel v0.7 Phase 1 / PR-1）。

承载 Kernel 编排过程中跨方法传递的轻量句柄。纯结构（G1）：不持执行能力、
不持业务语义、不持下游状态。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from shanhai_runtime_kernel.lifecycle import RuntimeState


class RuntimeHandle(BaseModel):
    """一次 Run 的编排句柄：绑定运行身份与当前生命周期态。

    句柄是不可变快照——状态推进由 Kernel 通过生命周期校验产生新句柄，
    而非原地改写（编排不拥有可变状态，v0.6 约束）。
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    state: RuntimeState
