# Experience Runtime Contract Implementation Review（PR-4.1 Gate）

> 状态：**Design Review Gate — 不写代码**。
> 上游：`docs/design/experience-runtime-review-v0.1.md` 已冻结 PR-4 总边界。
> 目标：在进入 PR-4.1 实现前，冻结 Experience Runtime contract package boundary；只允许 interfaces / contracts / types / tests，不实现 selector/provider 逻辑，不接 RuntimeContext execution flow。

---

## 0. PR-4.1 Position

PR-4 总路线：

```text
PR-4.1 Experience Runtime Contract
        ↓
PR-4.2 Candidate Provider Adapter
        ↓
PR-4.3 Selector MVP
        ↓
PR-4.4 Projection
        ↓
PR-4.5 RuntimeContext Integration
```

当前只 review PR-4.1。

PR-4.1 的价值：

```text
establish ownership boundary
        +
freeze public contracts
        +
lock dependency DAG with tests
```

不是：

```text
implement intelligent selection
connect runtime execution
read real artifact store
```

---

## Q1. Package Boundary

### Q1.1 允许新增

PR-4.1 若获准实现，只允许新增：

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
    __init__.py
    test_candidate_provider_contract.py
    test_selector_contract.py
    test_projection_contract.py
    test_dependency_boundary.py
```

允许同步：

```text
pyproject.toml
CHANGELOG.md
docs/PROJECT_STATE.md
docs/design/experience-runtime-contract-implementation-review-pr4.1.md
```

本地无 `uv` 时，可按既有 workspace 模式补 editable `.pth`，但必须只指向 `services/experience-runtime`。

### Q1.2 禁止修改

PR-4.1 禁止修改：

```text
services/runtime-kernel/
services/agent-runtime/
services/memory/
services/evaluation/
services/experience-evolution/
services/feedback/
apps/
```

尤其禁止：

```text
RuntimeKernel.execute
RuntimeKernel.assemble
RuntimeContext schema
RuntimeEvent schema
AgentRunner
RunStore
ArtifactBuilder
Memory
E2E flow
```

---

## Q2. Public Contract Surface

### Q2.1 Candidate Provider

`ExperienceCandidateProvider` 是 Access Port，不是 storage implementation。

推荐最小接口：

```python
class ExperienceCandidateProvider(Protocol):
    def list_candidates(self, query: ExperienceQuery) -> tuple[ExperienceCandidateView, ...]:
        ...
```

允许：

```text
query input
candidate refs
read-only candidate view
```

禁止：

```text
database driver
memory client
artifact mutation
candidate lifecycle update
model call
tool call
```

### Q2.2 Selector

`ExperienceSelector` 是 per-run selector。

推荐最小接口：

```python
class ExperienceSelector(Protocol):
    def select(
        self,
        candidates: tuple[ExperienceCandidateView, ...],
        query: ExperienceQuery,
    ) -> ExperienceSelection:
        ...
```

冻结性质：

```text
stateless
deterministic
per-run
read-only
```

PR-4.1 允许 Noop / deterministic placeholder selector，但禁止真实 ranking 策略。

### Q2.3 Projection

`ExperienceProjection` 把 `ExperienceSelection` 转成 RuntimeContext v1 可承载的 experience refs。

推荐最小接口：

```python
class ExperienceProjection(Protocol):
    def project(self, selection: ExperienceSelection) -> ExperienceProjectionResult:
        ...
```

Projection 允许输出：

```text
ArtifactRef
Metadata
Summary
Decision Hint
```

Projection 禁止：

```text
modify Artifact
persist Experience
update Memory
extend RuntimeContext schema
dump Artifact content
```

---

## Q3. Type Contracts

### Q3.1 ExperienceQuery

允许字段：

```python
ExperienceQuery:
    task_type
    intent
    constraints
    environment
```

禁止字段：

```python
model
tools
memory
agent_state
conversation_history
```

### Q3.2 ExperienceCandidateView

允许字段：

```python
ExperienceCandidateView:
    candidate_id
    artifact_ref
    summary
    metadata
```

禁止字段：

```python
artifact_content
raw_document
embedding
memory_state
learning_weight
```

### Q3.3 ExperienceSelection

允许字段：

```python
ExperienceSelection:
    candidate_id
    artifact_ref
    relevance_score
    selection_reason
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

### Q3.4 ExperienceProjectionResult

允许字段：

```python
ExperienceProjectionResult:
    experience_refs
    selection_reason
    selection_score
```

必须能映射到 RuntimeContext v1：

```text
RuntimeContext.experience_context.experience_refs
RuntimeContext.experience_context.selection_reason
RuntimeContext.experience_context.selection_score
```

禁止字段：

```python
artifact_content
full_rule
knowledge_graph
memory_snapshot
runtime_state
```

---

## Q4. Dependency Boundary

PR-4.1 目标 DAG：

```text
experience-runtime
        ↓
experience-artifact public schema / refs
```

PR-4.1 暂不要求 `runtime-kernel → experience-runtime` integration。

禁止依赖：

```text
experience-runtime → agent-runtime
experience-runtime → memory
experience-runtime → evaluation
experience-runtime → feedback
experience-runtime → experience-evolution
experience-runtime → apps
```

反向禁止：

```text
experience-artifact → experience-runtime
```

理由：

- Experience Runtime 是 read-side runtime collaborator。
- Agent Runtime 是 execution engine。
- Memory / Evaluation / Evolution 是后续层，不应被 selection contract 反向拉入。
- Artifact Layer 是 knowledge asset owner，不反向依赖 Runtime 读侧。

---

## Q5. Contract Tests

PR-4.1 必须新增 contract tests，测试不可违反的边界，而不是智能效果。

### Q5.1 Candidate Provider Contract

覆盖：

```text
provider returns immutable/read-only candidate views
candidate view contains refs, not artifact content
provider API does not expose write/update methods
```

### Q5.2 Selector Contract

覆盖：

```text
selector returns ExperienceSelection
selection contains candidate_id / artifact_ref / relevance_score / selection_reason
selection does not contain artifact_content / embedding / memory_state / learning_weight
selector object has no persistent mutable state
```

### Q5.3 Projection Contract

覆盖：

```text
projection maps ExperienceSelection to ExperienceProjectionResult
projection result shape is compatible with RuntimeContext v1 experience_context
projection does not dump Artifact content
projection does not mutate selection
```

### Q5.4 Dependency Boundary Contract

覆盖：

```text
experience-runtime does not import agent-runtime
experience-runtime does not import memory
experience-runtime does not import evaluation
experience-runtime does not import feedback
experience-runtime does not import experience-evolution
experience-artifact does not import experience-runtime
```

---

## Q6. PR-4.1 Definition of Done（待批准）

PR-4.1 完成标准：

- `services/experience-runtime` package exists and imports.
- Public exports include:

```text
ExperienceCandidateProvider
ExperienceSelector
ExperienceProjection
ExperienceQuery
ExperienceCandidateView
ExperienceSelection
ExperienceProjectionResult
```

- Contract tests pass.
- Dependency boundary tests pass.
- No RuntimeContext schema change.
- No RuntimeKernel execution / assemble wiring.
- No AgentRunner change.
- No Memory / Evaluation / Evolution / E2E integration.
- Docs / PROJECT_STATE / CHANGELOG updated.

---

## Q7. Explicit Non-Goals

PR-4.1 不做：

```text
real artifact adapter
real selector ranking
model-based selection
learning
feedback loop
memory integration
runtime-kernel integration
agent-runtime integration
E2E execution flow
trading strategy
decision optimization
```

---

## 8. Review Gate Decision

当前建议：

> PR-4.1 可以进入 Experience Runtime Contract implementation，前提是批准本 Review Gate。

批准后实施原则：

- contract first
- dependency boundary first
- behavior later
- integration last

> 当前停在 **PR-4.1 Experience Runtime Contract Implementation Review Gate**。未开始代码实现。
