# Experience Runtime Candidate Provider Adapter Review（PR-4.2 Design Gate）

> 状态：**Design Review Gate — 不写代码**。
> 前置：PR-4.1 Experience Runtime Contract Layer ✅ Implementation + Closure Review Completed。
> 目标：在实现第一个 `ExperienceCandidateProvider` adapter 前，冻结 ArtifactReader / ArtifactService 读侧边界、CandidateProvider I/O、依赖方向、Selector 无状态约束、ingestion 与 projection 边界，以及 PR-4.2 实现 / 禁止范围。

---

## 0. PR-4.2 Position

PR-4 总路线：

```text
PR-4.1 Experience Runtime Contract
        ✅ Completed
        ↓
PR-4.2 Candidate Provider Adapter
        ⏳ Design Gate
        ↓
PR-4.3 Selector MVP
        ↓
PR-4.4 Projection
        ↓
PR-4.5 RuntimeContext Integration
```

PR-4.2 的价值：

```text
connect first read-side source
        +
produce ExperienceCandidateView
        +
preserve artifact / runtime boundaries
```

不是：

```text
implement selector intelligence
project into RuntimeContext
connect AgentRunner / RuntimeKernel
learn from feedback
```

---

## Q1. ArtifactReader as First CandidateProvider Adapter Boundary

### Q1.1 当前 Artifact 层现实

当前 `experience-artifact` 已有：

```text
ExperienceArtifact
ArtifactService
ArtifactRepository
InMemoryArtifactRepository
```

当前尚未存在：

```text
ArtifactReader
```

因此 PR-4.2 需要先冻结一个原则：

```text
CandidateProvider adapter consumes read-side Artifact access.
```

可以有两种实现策略，必须在实现前二选一并保持最小化：

| Option | Description | Boundary Risk |
|---|---|---|
| A. Introduce `ArtifactReader` port | 在 `experience-runtime` 侧定义只读 reader Protocol，由 adapter 依赖该 port | 最清晰；不依赖 ArtifactService 写侧语义 |
| B. Use existing `ArtifactService.get/list` read subset | adapter 注入 `ArtifactService`，但只调用 `get/list` | 可复用现有对象，但 Service 也有 `create`，需测试禁止写入 |

### Q1.2 推荐冻结

推荐 PR-4.2 采用 Option A：

```python
class ArtifactReader(Protocol):
    def get(self, artifact_id: str) -> ExperienceArtifact | None:
        ...

    def list(self, limit: int = 50) -> tuple[ExperienceArtifact, ...]:
        ...
```

但注意：

- `ArtifactReader` 是 adapter 所需的只读 port。
- 它不是 Artifact persistence。
- 它不引入 Vector / Graph / Retrieval / Memory。
- 它不修改 `experience-artifact`。

### Q1.3 明确禁止

PR-4.2 adapter 禁止：

```text
ArtifactService.create(...)
ArtifactRepository.add(...)
artifact mutation
status transition
promotion / validation
embedding / vector search
graph traversal
```

---

## Q2. CandidateProvider Input / Output Contract

### Q2.1 Input

PR-4.2 `CandidateProvider` 输入必须保持 PR-4.1 contract：

```python
ExperienceQuery
```

允许使用：

```text
task_type
intent
constraints
environment
```

禁止读取：

```text
RuntimeContext object
AgentContext
AgentRunner state
Memory
conversation history
model/tool config
```

### Q2.2 Output

PR-4.2 `CandidateProvider` 输出必须保持：

```python
tuple[ExperienceCandidateView, ...]
```

允许字段：

```text
candidate_id
artifact_ref
summary
metadata
```

禁止字段：

```text
artifact_content
raw_document
embedding
memory_state
learning_weight
feedback_score
runtime_state
```

### Q2.3 Candidate ID Rule

冻结：

```text
candidate_id is runtime candidate identity.
artifact_ref.artifact_id is artifact identity.
```

两者可以相同，但语义不同。推荐：

```text
candidate_id = "artifact:<artifact_id>"
artifact_ref.artifact_id = "<artifact_id>"
```

这样后续 selector / evaluation 能区分：

- 选择了哪个 candidate view。
- candidate view 引用了哪个 stable artifact。

---

## Q3. Provider / experience-artifact Dependency Direction

### Q3.1 允许方向

PR-4.2 允许：

```text
experience-runtime
        ↓
experience-artifact public models / read-side port
```

只允许读取稳定资产引用与只读摘要所需字段：

```text
artifact_id
artifact_type
name
confidence
rule.context / rule.condition / rule.action（仅用于 summary）
expected_outcome（仅用于 summary）
```

### Q3.2 禁止方向

禁止：

```text
experience-artifact
        ↓
experience-runtime
```

禁止：

```text
experience-runtime
        ↓
experience-artifact.repository.add
experience-runtime
        ↓
ArtifactService.create
```

架构允许方向保持：

```text
runtime-kernel
        ↓
experience-runtime
        ↓
experience-artifact
```

但 PR-4.2 不新增 `runtime-kernel → experience-runtime` execution wiring；该连接仍延期到 PR-4.5 RuntimeContext Integration。

同时保持禁止：

```text
experience-runtime
        X agent-runtime
        X memory
        X evaluation
        X feedback
        X experience-evolution
```

---

## Q4. Selector Remains Pure / Stateless

PR-4.2 不实现 selector algorithm。

但 adapter 设计必须继续保护 Selector 边界：

```text
CandidateProvider
        ↓
tuple[ExperienceCandidateView, ...]
        ↓
Selector
```

Selector 继续冻结为：

```text
stateless
deterministic
per-run
read-only
```

Provider 禁止提前替 Selector 做：

```text
ranking
learning
feedback scoring
memory-aware personalization
model-based reasoning
```

Provider 允许做的只读过滤仅限：

```text
status/type/basic query constraints
limit
```

Provider 不输出：

```text
learning_weight
feedback_score
adaptive_rank
```

---

## Q5. Candidate Ingestion vs RuntimeContext Projection Boundary

### Q5.1 Candidate Ingestion Boundary

PR-4.2 是 candidate access adapter：

```text
ArtifactReader / read-side source
        ↓
ExperienceCandidateProvider
        ↓
ExperienceCandidateView
```

它不负责：

```text
Projection
RuntimeContext writing
RuntimeContext schema extension
Agent prompt injection
RuntimeEvent emission
```

### Q5.2 Projection Boundary

Projection 仍属于后续 PR-4.4 / PR-4.5：

```text
ExperienceSelection
        ↓
ExperienceProjection
        ↓
RuntimeContext.experience_context
```

PR-4.2 不允许：

```text
CandidateProvider
        ↓
RuntimeContext.experience_context
```

也不允许：

```text
Artifact dump
        ↓
RuntimeContext
```

---

## Q6. PR-4.2 Implementation Scope

### Q6.1 允许修改

若 PR-4.2 implementation 获批，只允许：

```text
services/experience-runtime/
    shanhai_experience_runtime/
        artifact_reader.py        # if Option A approved
        artifact_candidate_provider.py
        __init__.py

tests/experience_runtime/
    test_artifact_candidate_provider_contract.py
    test_candidate_provider_dependency_boundary.py

docs/
CHANGELOG.md
```

可按需要更新：

```text
pyproject.toml
```

前提：只为声明 `shanhai-experience-artifact` workspace dependency，不引入其他依赖。

### Q6.2 禁止修改

PR-4.2 禁止修改：

```text
services/runtime-kernel/
services/agent-runtime/
services/memory/
services/evaluation/
services/feedback/
services/experience-evolution/
apps/
```

尤其禁止：

```text
RuntimeKernel
RuntimeContext
RuntimeEvent
AgentRunner
RunStore
ArtifactService.create semantics
ArtifactRepository.add semantics
E2E flow
```

### Q6.3 禁止实现

PR-4.2 禁止：

```text
Selector strategy / ranking algorithm
Projection runtime
RuntimeContext integration
Memory integration
Evolution / Learning
Feedback loop
Model call
Tool call
Vector / Graph / Retrieval
Trading strategy / market decision
```

---

## Q7. Contract Tests Required

PR-4.2 implementation 必须新增 / 更新 tests 覆盖：

1. Adapter can read artifacts through read-side port and produce `ExperienceCandidateView`.
2. Candidate output contains refs / summary / metadata only.
3. Candidate output rejects artifact_content / embedding / memory_state / learning_weight / feedback_score.
4. Adapter never calls write APIs (`create`, `add`, `save`, `persist`, `update`, `delete`).
5. `experience-runtime` dependency boundary remains clean:

```text
no agent-runtime
no memory
no evaluation
no feedback
no experience-evolution
```

6. `experience-artifact` does not depend on `experience-runtime`.
7. Provider does not import or instantiate selector / projection.

---

## Q8. Frozen Decisions Before Implementation

本 Design Gate 冻结以下实现前置决定：

1. 采用 Option A：在 `experience-runtime` 侧定义 `ArtifactReader` read-side port。
2. `ArtifactRef.artifact_type` 使用 Artifact public model 的稳定类型值；adapter 不暴露 Artifact 实例本体。
3. `ExperienceCandidateView.summary` 允许由 Artifact rule / expected_outcome 生成短摘要，但禁止输出 raw artifact content。
4. `Metadata.entries` 仅允许携带只读描述性元数据，例如 `confidence` / `artifact_name` / `source_type`。
5. PR-4.2 只提供一个 `ArtifactCandidateProvider` adapter，不提供 ranking / selector / projection。
6. PR-4.2 不修改 `experience-artifact`，不把 `ArtifactReader` 反向放入 Artifact 层。

---

## 9. Recommended Decision

建议冻结：

```text
PR-4.2 = Artifact-backed CandidateProvider Adapter
```

采用：

```text
ArtifactReader port
        ↓
ArtifactCandidateProvider
        ↓
ExperienceCandidateView
```

并保持：

```text
no Selector algorithm
no Projection runtime
no RuntimeContext execution flow
no Memory / Evolution / Feedback
```

当前结论：

```text
PR-4.2 Candidate Provider Adapter
        ⏳ Design Review Gate
        ❌ Not approved for implementation yet
```
