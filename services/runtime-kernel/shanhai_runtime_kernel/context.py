"""RuntimeContext 契约（Runtime Kernel v0.7 Phase 1 / PR-1）。

RuntimeContext 描述「**这次 Run 为什么 / 如何被语境化**（why/how this run is
contextualized）」，是 Kernel 编排时的**语境契约**，不是执行句柄。

与 ``AgentContext``（agent-runtime 的执行期能力句柄，持有 router/tool_registry/
memory）严格区分：RuntimeContext **不**持有任何执行能力。

R7 — Context Ownership Drift 治理判据（v0.7 §0.C G4，冻结）：
    任何拟加入的字段必须能回答
        "Does this field describe 'why/how this run is contextualized',
         not 'how this run executes'?"
    若它描述的是「这次运行如何执行」（model / tools / memory_service /
    market_strategy 等执行能力），**不允许进入**。执行能力归 AgentContext。

契约要点（v0.5/v0.6 冻结）：
- 7 个 ``*_context`` 子契约：identity / task / experience / policy / environment /
  constraint / metadata。
- ``schema_version`` 落库即带（AI Runtime / replay 按当时版本解释）。
- **容器 immutable**（``frozen=True``）：回写抛 ``ValidationError``。
  注意：容器冻结 ≠ 递归冻结——Provider 注入对象的内部由各 Provider 自管。
- **run_id 仅在 identity_context**：身份单点承载，其余子契约不含 run_id。

本模块为纯结构（PR-1 G1）：只定义 Pydantic 模型，不实例化执行引擎 / 存储 /
经验访问口。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    """不可变基类：构造后回写字段抛 ``ValidationError``。"""

    model_config = ConfigDict(frozen=True)


class IdentityContext(_FrozenModel):
    """运行身份语境——**唯一**承载 run_id 的子契约。"""

    run_id: str


class TaskContext(_FrozenModel):
    """任务语境：这次 Run 要完成什么（why contextualized 的任务面）。"""

    objective: str | None = None
    task_type: str | None = None


class ExperienceContext(_FrozenModel):
    """经验语境：本次 Run 被注入的经验视图引用（只读投影，非 Artifact 本体）。"""

    selection_ref: str | None = None


class PolicyContext(_FrozenModel):
    """策略语境：约束本次 Run 的策略 / 守则（非执行参数）。"""

    policies: tuple[str, ...] = ()


class EnvironmentContext(_FrozenModel):
    """环境语境：运行所处环境描述（PR-1 留空，PR-5 再填）。"""

    labels: tuple[str, ...] = ()


class ConstraintContext(_FrozenModel):
    """约束语境：本次 Run 的边界 / 限制条件。"""

    constraints: tuple[str, ...] = ()


class MetadataContext(_FrozenModel):
    """元数据语境：非语义的附带信息（来源 / 标记等）。"""

    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeContext(_FrozenModel):
    """Run 语境契约的不可变容器：7 个 ``*_context`` + ``schema_version``。

    身份只在 ``identity_context``；其余子契约不含 run_id（v0.6 单向 ownership）。
    """

    identity_context: IdentityContext
    task_context: TaskContext = Field(default_factory=TaskContext)
    experience_context: ExperienceContext = Field(default_factory=ExperienceContext)
    policy_context: PolicyContext = Field(default_factory=PolicyContext)
    environment_context: EnvironmentContext = Field(default_factory=EnvironmentContext)
    constraint_context: ConstraintContext = Field(default_factory=ConstraintContext)
    metadata_context: MetadataContext = Field(default_factory=MetadataContext)
    schema_version: str = "1.0"

    @property
    def run_id(self) -> str:
        """便捷读取身份；身份始终来自 identity_context（单点承载）。"""
        return self.identity_context.run_id
