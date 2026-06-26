# Experience Runtime Contract Closure Review（PR-4.1 Post Implementation）

> 状态：**✅ Closure Review Completed — PR-4.1 Approved**。
> 对象：`b94e01c feat(experience-runtime): add contract layer`。
> 范围：contract completeness / schema stability / dependency boundary / v0.6-v0.7 frozen constraints consistency。
> 明确不进入：PR-4.2 Candidate Provider Adapter、RuntimeContext execution flow、RuntimeKernel / AgentRunner / Experience Artifact 修改。

---

## 1. Implementation Summary

PR-4.1 新增 Experience Runtime contract layer：

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

已实现 public interfaces：

```text
ExperienceCandidateProvider
ExperienceSelector
ExperienceProjection
```

已实现 type contracts：

```text
ArtifactRef
Metadata
Summary
DecisionHint
ExperienceQuery
ExperienceCandidateView
ExperienceSelection
ExperienceProjectionResult
```

PR-4.1 保持 contract-only：

- 无真实 provider。
- 无 selector algorithm。
- 无 projection runtime。
- 无 ArtifactReader。
- 无 Memory / Evolution / Evaluation。
- 无 RuntimeContext execution integration。

---

## 2. Contract Completeness

| Contract | Status | Review |
|---|---|---|
| `ExperienceCandidateProvider` | ✅ Pass | Access Port 存在，接口只返回 `ExperienceCandidateView` tuple；未暴露写入 / 存储 / Memory 能力。 |
| `ExperienceSelector` | ✅ Pass | Selector 接口存在，输入 candidates + query，输出 `ExperienceSelection`；未实现真实 ranking。 |
| `ExperienceProjection` | ✅ Pass | Projection 接口存在，输入 `ExperienceSelection`，输出 `ExperienceProjectionResult`；未修改 RuntimeContext。 |
| `ExperienceQuery` | ✅ Pass | 只包含 task / intent / constraints / environment 信号；未包含 model / tools / memory / agent_state。 |
| `ExperienceCandidateView` | ✅ Pass | 只包含 candidate_id / artifact_ref / summary / metadata；未包含 artifact_content / embedding / memory_state。 |
| `ExperienceSelection` | ✅ Pass | 字段冻结为 candidate_id / artifact_ref / relevance_score / selection_reason。 |
| `ExperienceProjectionResult` | ✅ Pass | 输出 experience_refs / selection_reason / selection_score + Metadata / Summary / DecisionHint，符合 projection 只读视图定位。 |

结论：contract surface 完整覆盖 PR-4.1 Gate 要求。

---

## 3. Schema Stability

所有 value contracts 继承 `_FrozenModel`：

```python
model_config = ConfigDict(frozen=True, extra="forbid")
```

已验证：

- unknown fields 被拒绝。
- `ExperienceSelection` 不接受：

```text
artifact_content
embedding
memory_state
learning_weight
feedback_score
model_prompt
agent_instruction
```

- `ExperienceCandidateView` 不接受：

```text
artifact_content
raw_document
embedding
memory_state
learning_weight
```

- `ExperienceProjectionResult` 不接受：

```text
artifact_content
full_rule
knowledge_graph
memory_snapshot
runtime_state
```

Projection result 可映射到 RuntimeContext v1：

```text
ExperienceProjectionResult.experience_refs
        -> RuntimeContext.experience_context.experience_refs

ExperienceProjectionResult.selection_reason
        -> RuntimeContext.experience_context.selection_reason

ExperienceProjectionResult.selection_score
        -> RuntimeContext.experience_context.selection_score
```

结论：schema 与 RuntimeContext v1 兼容，未倒逼 RuntimeContext 扩字段。

---

## 4. Dependency Boundary

### 4.1 experience-runtime dependencies

PR-4.1 只依赖：

```text
stdlib
pydantic
shanhai_experience_runtime self modules
```

dependency boundary tests 已验证 `experience-runtime` 不 import：

```text
shanhai_agent_runtime
shanhai_memory
shanhai_evaluation
shanhai_feedback
shanhai_experience_evolution
```

### 4.2 Artifact persistence boundary

已验证 `experience-runtime` 不 import：

```text
shanhai_experience_artifact.repository
shanhai_experience_artifact.service
```

PR-4.1 没有接 ArtifactReader / Artifact persistence。

### 4.3 Reverse dependency boundary

已验证：

```text
experience-artifact -> experience-runtime
```

不存在。

结论：dependency DAG 未被污染；PR-4.1 没有横向依赖 AgentRuntime / Memory / Evaluation / Evolution。

---

## 5. Frozen Constraints Consistency

| Frozen Constraint | Status | Review |
|---|---|---|
| Experience Runtime = access + selection + projection | ✅ Pass | 三个 Protocol 分别对应 provider / selector / projection。 |
| Selector 不学习，Evolution 学习 | ✅ Pass | Selection contract 不含 learning_weight / feedback_score；未依赖 evolution。 |
| RuntimeContext 只接 refs，不接 Artifact dump | ✅ Pass | Projection result 只提供 refs / reason / score / metadata / summary / hint。 |
| 不实现真实 provider | ✅ Pass | 仅存在 Protocol 和测试 stub。 |
| 不实现 selector algorithm | ✅ Pass | 仅存在 Protocol 和测试中的 deterministic fixture。 |
| 不接 ArtifactReader | ✅ Pass | 无 ArtifactReader / repository / service import。 |
| 不接 Memory | ✅ Pass | 无 memory import / API。 |
| 不接 RuntimeContext execution flow | ✅ Pass | 未修改 runtime-kernel；测试仅验证 projection shape compatibility。 |
| 不改 AgentRunner / RunStore | ✅ Pass | 未触碰 agent-runtime / persistence。 |

结论：PR-4.1 与 v0.6 / v0.7 已冻结约束一致。

---

## 6. Test Evidence

Closure Review 复跑：

```bash
PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_candidate_provider_contract
PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_selector_contract
PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_projection_contract
PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_dependency_boundary
PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_dependency_boundary
PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_context_v1_contract
PYTHONPATH=. .venv/bin/python -m tests.test_artifact_bridge
```

结果：

| Test | Result |
|---|---|
| `tests.experience_runtime.test_candidate_provider_contract` | ✅ Pass |
| `tests.experience_runtime.test_selector_contract` | ✅ Pass |
| `tests.experience_runtime.test_projection_contract` | ✅ Pass |
| `tests.experience_runtime.test_dependency_boundary` | ✅ Pass |
| `tests.runtime_kernel.test_dependency_boundary` | ✅ Pass |
| `tests.runtime_kernel.test_context_v1_contract` | ✅ Pass |
| `tests.test_artifact_bridge` | ✅ Pass |

此前 PR-4.1 implementation 阶段已跑既有全量回归，结果为 all-pass。

---

## 7. Forbidden Boundary Verification

PR-4.1 commit touched:

```text
CHANGELOG.md
docs/PROJECT_STATE.md
docs/design/experience-runtime-contract-implementation-review-pr4.1.md
pyproject.toml
services/experience-runtime/*
tests/experience_runtime/*
```

Forbidden files / areas not modified:

| Boundary | Status |
|---|---|
| RuntimeKernel | ✅ Not touched |
| `kernel.py` / `events.py` / `lifecycle.py` | ✅ Not touched |
| RuntimeContext contract | ✅ Not touched |
| RuntimeEvent contract | ✅ Not touched |
| AgentRunner | ✅ Not touched |
| RunStore | ✅ Not touched |
| Experience Artifact models / service / repository | ✅ Not touched |
| Memory | ✅ Not touched |
| Evaluation | ✅ Not touched |
| E2E flow | ✅ Not touched |

No forbidden boundary violation found.

---

## 8. Review Findings

No code defects found.

Residual notes:

- PR-4.1 uses test fixtures to demonstrate Protocol conformance; this is intentional and does not constitute provider / selector implementation.
- Local editable `.pth` may exist in developer environment for importability, but it is environment setup, not committed contract surface.
- PR-4.2 must not be inferred as approved by this closure review.

---

## 9. Final Decision

```text
PR-4.1 Experience Runtime Contract Layer
    ✅ Implementation Completed
    ✅ Closure Review Completed
    ✅ Approved

Next:
PR-4.2 Candidate Provider Adapter
    ⏸️ Review Gate required
```

Decision:

- PR-4.1 satisfies frozen Design Constraints.
- Contract completeness is sufficient for the current layer.
- Schema is stable and rejects forbidden fields.
- Dependency boundary is clean.
- No RuntimeContext execution flow, RuntimeKernel, AgentRunner, Experience Artifact, Memory, Evaluation, or E2E integration was introduced.

Stop here. Do not enter PR-4.2 implementation without a separate Review Gate approval.
