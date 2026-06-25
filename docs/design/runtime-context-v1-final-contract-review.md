# RuntimeContext v1 Final Contract Review（PR-2 Design Gate）

> 状态：**Design Review — 待批准，不写代码**。
> 前置：PR-1 Runtime Kernel Skeleton + Contract Layer 已 Approved。
> 目标：冻结 RuntimeContext v1 的最终定位、schema、immutability、AgentContext 边界与 PR-2 implementation scope。

---

## 0. Review 结论草案

RuntimeContext v1 应定义为：

> **Execution Initialization Snapshot**

它是 Runtime Kernel 在 `assemble()` 阶段生成的、用于初始化一次执行的不可变语境快照。

它不是：

- Agent state
- Memory
- Conversation state
- Experience storage
- Model / Tool / Prompt / Agent 配置容器

方向必须保持：

```text
Runtime Kernel
    assemble()
        ↓
RuntimeContext
        ↓
AgentContext
        ↓
AgentRunner
```

禁止反向：

```text
AgentContext → RuntimeContext
AgentRunner  → RuntimeContext mutation
```

核心不变量：

- RuntimeContext 只描述「本次执行为什么 / 如何被语境化」。
- AgentContext 承载「本次执行如何进行」。
- RuntimeContext 是 immutable snapshot；AgentContext 是 mutable execution state。

---

## Q1. RuntimeContext 的最终定位与边界

### Q1.1 定位

RuntimeContext = **Execution Initialization Snapshot**。

它在 Runtime Kernel `assemble()` 中生成，作为 Agent Runtime 启动执行前的输入快照。

### Q1.2 允许承载

- execution identity
- task description
- user / decision intent（非 chain-of-thought）
- selected experience references（非 Artifact 全量）
- policy / constraint
- generic runtime environment
- schema version

### Q1.3 禁止承载

- Agent mutable state：`current_step` / `messages` / `tool_result` / `observations`
- Model / Tool / Memory 句柄：`llm_client` / `model` / `router` / `tools` / `tool_registry` / `memory` / `memory_service`
- Conversation storage：`conversation_id` / `conversation_history`
- Experience storage：Artifact full content / Memory full content / vector payload
- Domain data：stock price / fundamental data / market quote snapshot

### Q1.4 Review 判据

任一字段进入 RuntimeContext 前必须通过：

> Does this field describe why/how this run is contextualized, not how this run executes?

如果答案偏向「how this run executes」，字段不允许进入 RuntimeContext。

---

## Q2. 七个 `*_context` schema 是否冻结

### Q2.0 PR-1 与本 Review 的差异

PR-1 skeleton 当前是：

```python
identity_context
task_context
experience_context
policy_context
environment_context
constraint_context
metadata_context
schema_version
```

本 Review 建议 RuntimeContext v1 调整为：

```python
identity_context
task_context
intent_context
experience_context
policy_context
constraint_context
environment_context
schema_version
```

原因：

- `intent_context` 是执行初始化快照的核心语义：描述用户/决策意图。
- `metadata_context: dict[str, Any]` 风险较高，容易成为 R7 漂移入口。
- 若确实需要元信息，应优先通过受控字段或未来 typed extension，而不是 v1 放自由 dict。

> 这是 PR-2 需要批准的 schema 调整点。未批准前不得改代码。

### Q2.1 `identity_context`

定位：execution identity，不是 user identity。

Allowed fields：

```python
run_id: str
trace_id: str | None = None
schema_version: str | None = None
```

Forbidden fields：

```python
user_profile
memory_id
conversation_id
account_id
portfolio_id
```

Future extension point：

- `trace_id`：跨系统观测链路。
- `parent_run_id`：未来支持 run fork / retry 时再评审。

治理：

- `run_id` 是执行身份。
- user / conversation / memory 身份不得混入 identity_context。

### Q2.2 `task_context`

定位：描述「我要执行什么」。

Allowed fields：

```python
task_type: str | None = None
goal: str | None = None
input: object | None = None
```

Forbidden fields：

```python
tool
tools
agent
model
router
prompt
system_prompt
```

Future extension point：

- `task_ref`：未来引用外部任务对象，但 RuntimeContext 不复制任务存储内容。
- `deadline` / `priority`：若用于 execution policy，需判断放 task_context 还是 policy_context。

治理：

- task_context 描述任务，不选择执行器。
- `agent` / `model` / `tool` 属 Agent Runtime 装配或 execution policy，不属 task schema。

### Q2.3 `intent_context`

定位：描述用户/决策意图，不承载推理过程。

Allowed fields：

```python
user_intent: str | None = None
decision_intent: str | None = None
objective: str | None = None
```

Forbidden fields：

```python
chain_of_thought
reasoning
analysis
scratchpad
hidden_state
```

Future extension point：

- `intent_source`：human / system / policy / evaluator。
- `confidence`：仅表示 intent parsing 置信度，不表示 experience score。

治理：

- intent_context 是「意图描述」，不是思维链存储。
- 不允许把模型推理、分析过程、隐藏中间态写入 RuntimeContext。

### Q2.4 `experience_context`

定位：本次执行可参考的经验引用 / 只读投影视图，不是 Artifact 或 Memory。

Allowed fields：

```python
selected_experiences: tuple[SelectedExperienceRef, ...] = ()
```

建议值对象：

```python
SelectedExperienceRef(
    artifact_id: str,
    relevance: float | None = None,
    reason: str | None = None,
)
```

Forbidden fields：

```python
artifact
artifact_full_content
memory
memory_records
embedding
vector
graph
```

Future extension point：

- `projection_ref`：未来 ExperienceProjection 的只读投影引用。
- `selection_snapshot_id`：未来 selector 输出快照引用。

治理：

- RuntimeContext 只能拿「选择结果引用 / 投影视图」，不能内嵌 Artifact 全量。
- Experience selection 的产生属于 Experience Runtime，不属于 RuntimeContext。
- RuntimeContext 不做 ranking，不做 retrieval，不做 Memory。

### Q2.5 `policy_context`

定位：规则 / 约束，不是模型策略或 prompt。

Allowed fields：

```python
risk_limits: tuple[str, ...] = ()
execution_policies: tuple[str, ...] = ()
safety_policies: tuple[str, ...] = ()
```

Forbidden fields：

```python
gpt_prompt
system_prompt
agent_instruction
model_selection_strategy
temperature
top_p
```

Future extension point：

- `policy_refs`：引用外部 policy registry 的稳定策略。
- `policy_version`：支持 replay 时按策略版本解释。

治理：

- policy_context 描述运行约束，不配置 LLM。
- prompt / instruction 属 Agent Runtime / Prompt 层，不能塞进 RuntimeContext。

### Q2.6 `constraint_context`

定位：本次执行的边界条件。

Allowed fields：

```python
constraints: tuple[str, ...] = ()
time_budget_ms: int | None = None
max_steps: int | None = None
```

Forbidden fields：

```python
tool_timeout_config
retry_policy_object
database_session
http_client
```

Future extension point：

- `resource_budget`：需要明确是抽象 budget，不是具体执行句柄。
- `compliance_constraints`：合规约束引用。

治理：

- constraint_context 可以描述边界，但不能持有执行资源。
- `max_steps` 若进入 v1，需要确认不会越过 AgentRunner ownership；默认可先不实现。

### Q2.7 `environment_context`

定位：generic runtime environment，未来可承接资本市场语境，但现在不能绑定金融领域。

Allowed fields：

```python
domain: str | None = None
environment_labels: tuple[str, ...] = ()
market_state: str | None = None
```

Forbidden fields：

```python
stock_price
fundamental_data
quote_snapshot
financial_statement
broker_account
```

Future extension point：

- `domain_context_ref`：未来 Domain Provider 产物引用。
- `market_regime_ref`：未来市场状态快照引用。

治理：

- environment_context 可以表达「domain=finance」或抽象市场状态标签。
- 不能把行情、财报、账户、交易数据直接塞入 Runtime Kernel。

---

## Q3. Immutable Strategy

### Q3.1 结论建议

RuntimeContext v1 应采用：

```text
deep immutable by schema
```

不是只做 top-level frozen。

### Q3.2 具体策略

所有 RuntimeContext 相关 Pydantic model：

```python
ConfigDict(
    frozen=True,
    extra="forbid",
)
```

集合字段优先使用：

```python
tuple[...]  # 而不是 list[...]
```

不使用：

```python
dict[str, Any]  # 除非通过 typed value object 包起来
list[Any]
object-with-mutable-internals
```

### Q3.3 原因

RuntimeContext 是执行初始化快照。

如果执行过程中可变：

- Execution Trace 会失真。
- Evaluation 无法判断当时执行的真实上下文。
- Experience Evolution 会学习到被执行期修改过的上下文。
- Replay 无法可靠复现。

### Q3.4 PR-2 必测

- top-level 回写抛 `ValidationError`。
- child context 回写抛 `ValidationError`。
- unknown field 抛 `ValidationError`。
- tuple 字段不可 append / 不可原地修改。
- 禁止 `RuntimeContext(model=...)` / `RuntimeContext(tools=...)` / `RuntimeContext(memory_service=...)`。

---

## Q4. RuntimeContext → AgentContext 转换边界

### Q4.1 方向冻结

唯一允许方向：

```text
RuntimeContext → AgentContext
```

禁止：

```text
AgentContext → RuntimeContext
AgentRunner mutates RuntimeContext
AgentContext stores mutable RuntimeContext reference for mutation
```

### Q4.2 转换方式建议

未来 PR-4 可使用：

```python
AgentContext.from_runtime_context(runtime_context)
```

但 PR-2 不实现该方法。

### Q4.3 RuntimeContext 中可进入 AgentContext 的内容

允许作为初始化输入或只读视图进入：

- `identity_context.run_id`
- `task_context.goal`
- `task_context.input`
- `intent_context.user_intent`
- `intent_context.decision_intent`
- `experience_context.selected_experiences` 的只读投影视图
- `policy_context` / `constraint_context` 的只读约束
- `environment_context` 的抽象标签

### Q4.4 永远不能进入 RuntimeContext 的 AgentContext 内容

这些属于 mutable execution state：

- `current_step`
- `iteration`
- `messages`
- `observations`
- `tool_result`
- `steps`
- `router`
- `tool_registry`
- `memory`
- granted tool object / model client / db session

### Q4.5 AgentContext 不应保存 RuntimeContext 可变引用

建议：

- AgentContext 可以保存 `runtime_context_snapshot` 的只读引用，前提是 deep immutable。
- 更保守的做法是只复制需要的只读字段，避免 Agent 侧误以为可回写 RuntimeContext。

PR-2 不做转换实现，只冻结边界。

---

## Q5. PR-2 Implementation Scope

### Q5.1 允许修改文件

PR-2 允许修改：

```text
services/runtime-kernel/shanhai_runtime_kernel/context.py
services/runtime-kernel/shanhai_runtime_kernel/__init__.py
tests/runtime_kernel/test_context_contract.py
docs/design/runtime-context-v1-final-contract-review.md
docs/design/runtime-context-contract-implementation-review-pr2.md
CHANGELOG.md
docs/PROJECT_STATE.md
```

若新增 value object，可仍放在：

```text
services/runtime-kernel/shanhai_runtime_kernel/context.py
```

或在 Review 批准后拆到：

```text
services/runtime-kernel/shanhai_runtime_kernel/types.py
```

### Q5.2 禁止修改文件 / 模块

PR-2 禁止修改：

```text
services/agent-runtime/
services/experience-runtime/
services/experience-artifact/
services/memory/
services/persistence/
services/evaluation/
```

PR-2 禁止修改行为：

- AgentRunner integration
- RunStore identity migration
- Experience selection
- Projection
- Memory access
- Domain Provider
- ArtifactReader
- E2E integration

### Q5.3 PR-2 最小实现建议

如果本 Review 批准，PR-2 最小实现为：

1. RuntimeContext v1 schema 从 PR-1 skeleton 调整为七 context：
   - `identity_context`
   - `task_context`
   - `intent_context`
   - `experience_context`
   - `policy_context`
   - `constraint_context`
   - `environment_context`
2. 移除 / 不引入自由形态 `metadata_context`。
3. 所有 context model 使用 `ConfigDict(frozen=True, extra="forbid")`。
4. 列表字段使用 `tuple[...]`。
5. 为 `SelectedExperienceRef` 增加 typed value object，只放 `artifact_id/relevance/reason`，不放 Artifact 全量。
6. 增补 contract tests：
   - unknown field rejected
   - execution fields rejected
   - intent_context forbids reasoning fields
   - experience_context forbids full artifact / memory payload
7. 不触碰 Kernel execute / AgentRunner / RunStore。

---

## 6. Open Decisions（需 Review 批准）

### D1. 是否以 `intent_context` 替代 `metadata_context`？

推荐：**是**。

理由：

- `intent_context` 是 Execution Initialization Snapshot 的核心语义。
- `metadata_context` 容易成为 God Context 的逃逸口。
- 未来如果确实需要 metadata，应使用 typed refs / labels，而不是 `dict[str, Any]`。

影响：

- 需要更新 PR-1 contract test 的字段集合。
- 需要修改 `RuntimeContext` 导出。
- 这是 schema 调整，但仍在 PR-2 Review Gate 范围内，尚未进入 AgentRunner / RunStore 集成，修改成本最低。

### D2. `identity_context` 是否加入 `trace_id`？

推荐：**PR-2 可加入，可选字段**。

理由：

- trace_id 属 execution observability identity，不是 user identity。
- 对未来 RuntimeEvent / Evaluation 串联有价值。

限制：

- 不加入 `conversation_id` / `user_id` / `memory_id`。

### D3. `RuntimeEvent` 是否在 PR-2 扩展？

推荐：**否**。

理由：

- PR-2 聚焦 RuntimeContext v1。
- RuntimeEvent 已通过 PR-1 Review，未发现越界。
- event schema 扩展应等 AgentRuntime adapter / Evaluation 接入前再评审。

### D4. 生命周期是否加入 `FAILED` / `CANCELLED`？

推荐：**否，PR-2 不加**。

理由：

- 失败 / 取消需要和 AgentRuntime `AgentStatus`、RunStore、Evaluation 语义一起审。
- PR-2 不触碰执行行为。

### D5. package naming 是否保持？

推荐：**保持**。

理由：

- `runtime-kernel` 准确表达 orchestrator boundary。
- `runtime-core` 容易被误解为执行核心。
- `runtime-orchestrator` 过窄，弱化 Kernel 对 lifecycle/context/event 的契约守护职责。

---

## 7. Review Gate 结论

当前建议：

> 批准进入 PR-2 的前提，是先批准本 RuntimeContext v1 Final Contract。

若批准，PR-2 只做 RuntimeContext v1 contract implementation，不做执行集成。

PR-2 结束条件：

- RuntimeContext v1 schema 冻结。
- deep immutable + `extra="forbid"` 落地。
- R7 防漂移 contract tests 增强。
- 不改 AgentRunner。
- 不改 RunStore identity。
- 不接 Experience Runtime / Memory / Domain Provider / ArtifactReader。

> 当前停在 **RuntimeContext v1 Final Contract Review Gate**。未开始 PR-2 代码实现。
