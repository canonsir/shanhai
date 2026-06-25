"""RuntimeContext v1 契约（Runtime Kernel PR-2）。

RuntimeContext 是 **Execution Initialization Snapshot**：Runtime Kernel 在
``assemble()`` 阶段生成的、用于初始化一次执行的不可变语境快照。

与 ``AgentContext``（agent-runtime 的执行期能力句柄，持有 router/tool_registry/
memory）严格区分：RuntimeContext **不**持有任何执行能力。

R7 — Context Ownership Drift 治理判据（v0.7 §0.C G4，冻结）：
    任何拟加入的字段必须能回答
        "Does this field describe 'why/how this run is contextualized',
         not 'how this run executes'?"
    若它描述的是「这次运行如何执行」（model / tools / memory_service /
    market_strategy 等执行能力），**不允许进入**。执行能力归 AgentContext。

契约要点（v0.5/v0.6 冻结）：
- 7 个 ``*_context`` 子契约：identity / task / intent / experience / policy /
  constraint / environment。
- ``schema_version`` 落库即带（AI Runtime / replay 按当时版本解释）。
- **deep immutable by schema**：所有子模型 ``frozen=True``，集合字段用 tuple。
- ``extra="forbid"``：未知字段必须拒绝；新增字段需走 schema evolution。
- **run_id 仅在 identity_context**：身份单点承载，其余子契约不含 run_id。

PR-2 只实现 RuntimeContext contract；不接 AgentRunner / RunStore / Experience
Runtime / Memory / ArtifactReader。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    """不可变契约基类：构造后回写字段、未知字段均抛 ``ValidationError``。"""

    model_config = ConfigDict(frozen=True, extra="forbid")


class IdentityContext(_FrozenModel):
    """运行身份语境——execution identity，非 user identity。"""

    run_id: str
    trace_id: str | None = None
    schema_version: Literal["1.0"] = "1.0"


class TaskContext(_FrozenModel):
    """任务语境：描述「我要执行什么」，不选择 agent/model/tool。"""

    task_type: str | None = None
    goal: str | None = None
    input: object | None = None


class IntentContext(_FrozenModel):
    """意图语境：描述为什么执行，不承载 chain-of-thought / reasoning trace。"""

    objective: str | None = None
    user_intent: str | None = None
    decision_intent: str | None = None


class SelectedExperienceRef(_FrozenModel):
    """被选择经验的只读引用；不承载 Artifact / Memory 全量内容。"""

    artifact_id: str
    relevance: float | None = None
    reason: str | None = None


class ExperienceContext(_FrozenModel):
    """经验语境：只保存经验引用 / 选择理由，不保存 Artifact dump。"""

    experience_refs: tuple[SelectedExperienceRef, ...] = ()
    selection_reason: str | None = None
    selection_score: float | None = None


class PolicyContext(_FrozenModel):
    """策略语境：规则 / 约束，不是 prompt 或模型策略。"""

    risk_limits: tuple[str, ...] = ()
    execution_policies: tuple[str, ...] = ()
    safety_policies: tuple[str, ...] = ()


class EnvironmentContext(_FrozenModel):
    """环境语境：generic provider output，不是 domain database。"""

    domain: str | None = None
    environment_labels: tuple[str, ...] = ()
    market_state: str | None = None


class ConstraintContext(_FrozenModel):
    """约束语境：执行边界条件，不持有 runtime state / resource handle。"""

    constraints: tuple[str, ...] = ()
    time_budget_ms: int | None = None
    max_steps: int | None = None


class RuntimeContext(_FrozenModel):
    """Execution Initialization Snapshot：7 个 ``*_context`` + ``schema_version``。

    身份只在 ``identity_context``；其余子契约不含 run_id（v0.6 单向 ownership）。
    """

    identity_context: IdentityContext
    task_context: TaskContext = Field(default_factory=TaskContext)
    intent_context: IntentContext = Field(default_factory=IntentContext)
    experience_context: ExperienceContext = Field(default_factory=ExperienceContext)
    policy_context: PolicyContext = Field(default_factory=PolicyContext)
    constraint_context: ConstraintContext = Field(default_factory=ConstraintContext)
    environment_context: EnvironmentContext = Field(default_factory=EnvironmentContext)
    schema_version: Literal["1.0"] = "1.0"

    @property
    def run_id(self) -> str:
        """便捷读取身份；身份始终来自 identity_context（单点承载）。"""
        return self.identity_context.run_id
