"""Runtime 生命周期状态机（Runtime Kernel v0.7 Phase 1 / PR-1）。

定义一次 Run 从创建到关闭的命名态生命周期，及其**不可逆**迁移规则。
生命周期是编排契约（orchestration contract），非业务状态——Kernel 据此约束
create → assemble → execute → close 的合法推进顺序（见 v0.5/v0.6 约束）。

合法链（单向，不可逆）::

    CREATED → ASSEMBLING → READY → RUNNING → COMPLETED → CLOSED

禁止任何逆向 / 跳跃迁移，例如 ``RUNNING → READY`` / ``RUNNING → ASSEMBLING``。

本模块为纯结构（PR-1 G1）：只定义状态枚举与迁移校验，不持有任何运行状态、
不实例化执行引擎 / 存储 / 经验访问口。
"""

from __future__ import annotations

from enum import Enum


class RuntimeState(str, Enum):
    """Run 生命周期的命名态（顺序即合法推进方向）。"""

    CREATED = "created"
    ASSEMBLING = "assembling"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    CLOSED = "closed"


# 合法的单步迁移图（source → 允许的下一态集合）。
# 仅允许向前推进一步；任何未列出的迁移（含逆向、跳跃）均非法。
_ALLOWED_TRANSITIONS: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.CREATED: frozenset({RuntimeState.ASSEMBLING}),
    RuntimeState.ASSEMBLING: frozenset({RuntimeState.READY}),
    RuntimeState.READY: frozenset({RuntimeState.RUNNING}),
    RuntimeState.RUNNING: frozenset({RuntimeState.COMPLETED}),
    RuntimeState.COMPLETED: frozenset({RuntimeState.CLOSED}),
    RuntimeState.CLOSED: frozenset(),
}


def can_transition(source: RuntimeState, target: RuntimeState) -> bool:
    """判断 ``source → target`` 是否为合法单步迁移。"""
    return target in _ALLOWED_TRANSITIONS.get(source, frozenset())


def assert_transition(source: RuntimeState, target: RuntimeState) -> RuntimeState:
    """校验并返回合法的目标态；非法迁移抛 ``ValueError``。

    生命周期不可逆——这是 Kernel 编排契约的硬约束，违反即抛错而非默默纠正。
    """
    if not can_transition(source, target):
        raise ValueError(
            f"非法生命周期迁移：{source.value} → {target.value}（违反不可逆单向链）"
        )
    return target
