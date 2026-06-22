"""ShanHai Harness Core。

Phase 0 提供自研最小 Workflow 骨架（受 LangGraph 思想启发，见 ADR 0003）：
Node / Edge / Workflow + 顺序执行器。
"""

from shanhai_harness_core.workflow import Node, Workflow, WorkflowState

__all__ = ["Node", "Workflow", "WorkflowState"]
