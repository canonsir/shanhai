"""最小 Workflow 骨架（见 ADR 0003）。

设计要点：
- Node：一个可执行步骤，输入/输出共享的 state（dict）。
- Workflow：按注册顺序与边（edges）线性推进。
- 暂不支持并行/条件分支/持久化，留待后续按需引入 LangGraph 时再评估。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

WorkflowState = dict
NodeFn = Callable[[WorkflowState], WorkflowState]


@dataclass
class Node:
    name: str
    fn: NodeFn

    def run(self, state: WorkflowState) -> WorkflowState:
        return self.fn(state)


@dataclass
class Workflow:
    name: str
    _nodes: dict[str, Node] = field(default_factory=dict)
    _order: list[str] = field(default_factory=list)
    _entry: str | None = None

    def add_node(self, name: str, fn: NodeFn) -> "Workflow":
        if name in self._nodes:
            raise ValueError(f"节点已存在: {name}")
        self._nodes[name] = Node(name=name, fn=fn)
        self._order.append(name)
        if self._entry is None:
            self._entry = name
        return self

    def run(self, state: WorkflowState | None = None) -> WorkflowState:
        """按注册顺序线性执行所有节点。"""
        current: WorkflowState = dict(state or {})
        for name in self._order:
            current = self._nodes[name].run(current)
        return current

    @property
    def nodes(self) -> list[str]:
        return list(self._order)
