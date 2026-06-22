"""ShanHai Agent Runtime。

提供 Agent 生命周期与基础抽象。约束（见 AGENTS.md）：
- Agent 禁止直接绑定/调用模型 → 必须经 ModelRouter。
- Agent 禁止直接访问数据库 → 必须经 Tool → Service。
"""

from shanhai_agent_runtime.agent import Agent
from shanhai_agent_runtime.memory import InMemoryMemory, Memory

__all__ = ["Agent", "Memory", "InMemoryMemory"]
