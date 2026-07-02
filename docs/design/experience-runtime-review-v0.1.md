# Experience Runtime Review v0.1（PR-4 Design Gate）

> 状态：**Review Gate — Design Only，不写代码**。
> 前置：PR-1 Runtime Kernel Foundation ✅ Closed；PR-2 RuntimeContext v1 ✅ Closed；PR-3 RunStore Identity Migration ✅ Implementation + Closure Review Completed。
> 目标：在进入 PR-4 实现前，冻结 Experience Runtime 的职责边界、依赖 DAG、MVP scope 与禁止项。

---

## 0. Current Runtime Spine

PR-3 完成后，Runtime identity spine 已落地：

```text
Runtime Kernel boundary
        │
        │ owns run identity
        ▼
run_id
        ├──────────────► RuntimeContext.identity_context.run_id
        ├──────────────► RuntimeEvent.run_id
        └──────────────► RunRecord.run_id
```

RunStore 已降级为：

```text
RunStore = execution trace persistence
```

PR-4 不应改变这条 spine。PR-4 只讨论 Experience Runtime 的读侧边界：

```text
Experience Runtime
        │
        │ selected references / projection
        ▼
RuntimeContext.experience_context
```

---

## Q1. Experience Runtime 职责

### Q1.1 推荐定义

Experience Runtime 是 Runtime Kernel 的经验读侧协作者：

```text
Experience Runtime
    =
experience access
    +
selection
    +
projection
```

它负责把已有经验资产 / 经验候选的可运行引用，转换成一次 Run 可使用的 `experience_context`。

### Q1.2 不负责

Experience Runtime 不是：

```text
Memory
Artifact storage
Learning system
Agent runtime
Decision engine
Trading strategy
Evaluation pipeline
```

禁止：

- 直接读取 / 写入 Memory。
- 修改 Artifact。
- 写 ExperienceEvent。
- 更新 Candidate lifecycle。
- 触发 Evaluation / Evolution。
- 调用 Model / Tool / AgentRunner。
- 生成交易策略或市场决策。

### Q1.3 Owner responsibility

Experience Runtime owner 负责：

```text
Candidate access
Candidate selection
Runtime projection
Selection contract tests
```

不负责：

```text
Runtime execution
Run identity
Agent loop
Memory access
Artifact production
Experience evolution / learning
```

---

## Q2. ExperienceCandidateProvider Boundary

### Q2.1 冻结主链路

PR-4 应冻结以下读侧链路：

```text
ExperienceCandidateProvider
        │
        │ provides candidate refs / views
        ▼
ExperienceSelector
        │
        │ select(...)
        ▼
ExperienceSelection
        │
        │ project(...)
        ▼
ExperienceProjection
        │
        ▼
RuntimeContext.experience_context
```

### Q2.2 Provider 是 Access Port

`ExperienceCandidateProvider` 是 Experience Access Port，不是具体存储实现。

允许未来实现：

```text
LocalArtifactCandidateProvider
VectorCandidateProvider
GraphCandidateProvider
ExternalCognitionCandidateProvider
```

但 PR-4 第一阶段只冻结 Port 与最小 stub，不冻结具体 reader。

### Q2.3 Selector 不学习

冻结：

```text
Selector selects.
Evolution learns.
```

Selector 禁止：

```text
modify Artifact
update Experience
learn weights
write Candidate
access Memory
call Model directly
```

Selector 输出的是 per-run decision：

```text
ExperienceSelection
```

不是：

```text
ExperienceArtifact
ExperienceEvent
MemoryRecord
RuntimeEvent
```

### Q2.3.A Selector / Evolution Boundary（冻结）

Selector 的性质：

```text
stateless
deterministic
per-run
read-only
```

Evolution 的性质：

```text
learning
feedback
optimization
promotion
artifact production trigger
```

边界规则：

| Capability | Selector | Evolution |
|---|---|---|
| per-run candidate ranking | ✅ | 可消费结果 |
| learning weights | ❌ | ✅ |
| feedback ingestion | ❌ | ✅ |
| promotion decision | ❌ | ✅ |
| artifact mutation / production | ❌ | ✅（经既有 Promotion → Artifact Bridge） |
| memory access | ❌ | ❌（不在 PR-4） |

> 核心冻结：**Selector 不学习，Evolution 学习**。PR-4 不引入任何 `learning_weight` / `feedback_score` / `adaptive_ranker`。

### Q2.3.B ExperienceSelection Contract（冻结）

`ExperienceSelection` 是 Selector 的输出，表示一次 Run 的经验选择结果。

允许字段：

```python
ExperienceSelection:
    candidate_id
    artifact_ref
    relevance_score
    selection_reason
```

可选扩展字段（仅作为未来候选，不进 PR-4.1 默认面）：

```python
rank
provider_ref
selection_policy_ref
```

禁止字段：

```python
artifact_content
embedding
memory_state
learning_weight
feedback_score
model_prompt
agent_instruction
```

语义约束：

- `candidate_id` 标识候选视图，不等同于 Artifact 主键。
- `artifact_ref` 是引用，不是 Artifact 实体。
- `relevance_score` 是 per-run selection 分数，不是可学习权重。
- `selection_reason` 是选择解释，不是 chain-of-thought。
- `ExperienceSelection` 不可回写 Artifact / Candidate / Memory。

### Q2.4 Projection 只裁剪运行视图

Projection 负责把 `ExperienceSelection` 转成 RuntimeContext 可承载的只读引用 / 视图。

Projection 可以输出：

```text
ArtifactRef
Metadata
Summary
Decision Hint
```

Projection 禁止：

- 回写 Artifact。
- 缓存跨 run 共享状态。
- 扩展 RuntimeContext schema。
- 复制 Artifact full content 到 RuntimeContext。
- 持久化 Experience。
- 更新 Memory。
- 修改 Candidate lifecycle。

Projection 输出必须适配 RuntimeContext v1 已冻结的字段：

```text
RuntimeContext.experience_context.experience_refs
RuntimeContext.experience_context.selection_reason
RuntimeContext.experience_context.selection_score
```

---

## Q3. Artifact Boundary

### Q3.1 语义区分

Artifact 是：

```text
immutable historical knowledge / validated capability asset
```

Experience Runtime 输出的是：

```text
runtime usable reference
```

二者不是同一个对象。

### Q3.2 正确关系

```text
ExperienceSelection
        │
        ▼
SelectedExperienceRef
        │
        ▼
ArtifactReader / CandidateProvider implementation
```

RuntimeContext 只接收：

```text
SelectedExperienceRef
selection_reason
selection_score
```

### Q3.3 禁止 Artifact dump

禁止：

```text
Selector
    ↓
Artifact dump
    ↓
RuntimeContext
```

禁止字段：

```text
artifact_content
full_rule
historical_memory
embedding
raw_document
knowledge_graph
```

原因：

- RuntimeContext 是 Execution Initialization Snapshot，不是 Artifact store / Memory store。
- Artifact full content 进入 Context 会绕过 Experience Runtime 与 Artifact ownership。
- 后续 evaluation / replay 只能引用 selection，而不是复制资产本体。

---

## Q4. Dependency DAG

### Q4.1 目标 DAG

PR-4 目标方向：

```text
runtime-kernel
        │
        ▼
experience-runtime
        │
        ▼
experience-artifact
```

说明：

- `runtime-kernel` 可在 assemble 阶段调用 `experience-runtime` public interface。
- `experience-runtime` 可读取 `experience-artifact` public schema / reader port。
- `experience-artifact` 不反向依赖 `experience-runtime`。

### Q4.2 禁止横向依赖

禁止：

```text
experience-runtime ──► agent-runtime
experience-runtime ──► memory
experience-runtime ──► evaluation
experience-runtime ──► feedback
experience-runtime ──► experience-evolution
```

原因：

- Agent Runtime 是 execution engine，不是 experience selection dependency。
- Memory Access 经 AgentRuntime / MemoryTool，不归 Experience Runtime。
- Evaluation / Evolution 在 execution trace 之后，不能反向影响 runtime selection。
- Feedback / Evolution 负责学习，不负责 per-run selection。

### Q4.3 Contract tests 必须守护 DAG

PR-4 contract tests 应包含 AST dependency boundary：

- `experience-runtime` 不 import `shanhai_agent_runtime`
- `experience-runtime` 不 import `shanhai_memory`
- `experience-runtime` 不 import `shanhai_evaluation`
- `experience-runtime` 不 import `shanhai_feedback`
- `experience-runtime` 不 import `shanhai_experience_evolution`
- `experience-artifact` 不反向 import `experience-runtime`

---

## Q5. MVP Scope

### Q5.1 PR-4 第一阶段允许

PR-4 第一阶段只允许：

```text
services/experience-runtime/
    pyproject.toml
    shanhai_experience_runtime/
        __init__.py
        candidate_provider.py
        selector.py
        projection.py
        types.py

tests/experience_runtime/
    test_candidate_provider_contract.py
    test_selector_contract.py
    test_projection_contract.py
    test_dependency_boundary.py
```

允许实现：

- `ExperienceCandidateProvider` 抽象 / Protocol。
- `ExperienceCandidateView` 或等价只读候选视图。
- `ExperienceSelector` 抽象 / Noop selector。
- `ExperienceSelection` contract。
- `ExperienceProjection` 抽象 / Noop projection。
- 投影到 RuntimeContext v1 允许的 `SelectedExperienceRef` 形态。
- contract tests。

### Q5.2 PR-4 第一阶段禁止

禁止：

```text
Evolution
Feedback loop
Learning
Memory integration
Trading strategy
Decision optimization
Model-based ranking
RuntimeKernel execute wiring
AgentRunner adapter
Artifact write path
ArtifactBuilder
E2E execution flow
```

### Q5.3 PR-4 Definition of Done（待批准）

PR-4 若获准进入 implementation，DoD 应为：

- `services/experience-runtime` package 可 import。
- CandidateProvider / Selector / Projection public contracts 存在。
- Selector 输出 `ExperienceSelection`，不是 Artifact。
- Projection 输出 RuntimeContext 可承载的 experience refs，不复制 Artifact content。
- dependency boundary tests 通过。
- 不修改 RuntimeKernel execute path。
- 不修改 AgentRunner。
- 不接 Memory / Evaluation / Evolution / E2E。

### Q5.4 PR-4 分阶段实现路线（冻结建议）

PR-4 不应一次性完成 Experience Runtime 全链路。建议拆为：

```text
PR-4.1 Experience Runtime Contract
        CandidateProvider / Selector / Projection / Selection contracts
        contract tests
        no real strategy

PR-4.2 Candidate Provider Adapter
        first local provider adapter
        no selector learning
        no Memory

PR-4.3 Selector MVP
        deterministic stateless selector
        no learning / feedback loop

PR-4.4 Projection
        ExperienceSelection → RuntimeContext.experience_context compatible refs
        no RuntimeContext schema change

PR-4.5 RuntimeContext Integration
        assemble-time wiring only after review
        no AgentRunner execute refactor
```

当前 Review Gate 仅冻结 PR-4 总边界；若进入实现，推荐首先批准 **PR-4.1 Experience Runtime Contract**，不要直接进入 PR-4.2+。

---

## Q6. Open Decisions

### D1. PR-4 是否实现真实 Selector？

推荐：**否**。

理由：

- PR-4 第一阶段应冻结 interface / contract。
- ranking 策略涉及智能层与未来 Evaluation feedback，不应在 skeleton 阶段写死。

### D2. PR-4 是否恢复 ArtifactReader？

推荐：**否，至少不以冻结接口名恢复**。

理由：

- v0.6 已冻结 `ExperienceCandidateProvider = Experience Access Port`。
- `ArtifactReader` 可以未来作为 local artifact provider 的具体实现，而不是核心 Port 名。

### D3. PR-4 是否修改 RuntimeContext schema？

推荐：**否**。

理由：

- RuntimeContext v1 已 closed。
- PR-4 projection 必须适配现有 `experience_context` / `SelectedExperienceRef`，不能倒逼 RuntimeContext 扩字段。

### D4. PR-4 是否接 Memory？

推荐：**否**。

理由：

- Memory Access Interface 是 AgentRuntime / MemoryTool 路径。
- Experience Runtime 接 Memory 会形成横向依赖并绕过既有边界。

### D5. PR-4 是否一次完成 CandidateProvider → Projection → RuntimeContext integration？

推荐：**否**。

理由：

- Experience Runtime 是新的 runtime 读侧能力，应先 contract 再 adapter，再 selector，再 projection，再 integration。
- 一次性接入会把 selection contract、artifact adapter、projection semantics 与 runtime assemble wiring 混在一起。
- PR-4.1 应只建立 ownership boundary 与 contract tests。

---

## 7. Review Gate 结论

当前建议：

> PR-4 可以进入 Experience Runtime contract implementation 的前提，是先批准本 Review Gate。

批准条件：

- Experience Runtime 定位为 access + selection + projection。
- CandidateProvider / Selector / Projection 只做读侧 per-run selection。
- Selector 不学习；Evolution 学习。
- RuntimeContext 只接 SelectedExperienceRef，不接 Artifact dump。
- dependency DAG 按 `runtime-kernel → experience-runtime → experience-artifact` 冻结。
- 禁止接 AgentRuntime / Memory / Evaluation / Evolution / E2E。

> 当前停在 **PR-4 Experience Runtime Review Gate**。未开始 PR-4 代码实现。
