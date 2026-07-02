# ADR 0018：Experience Artifact Layer MVP（候选经验晋升后的稳定资产承载层）

状态：**MVP Contract Established（生产侧契约已立）** —— 非 Draft（Artifact 生产链路已成稳定契约），亦**未 Finalize**（消费侧未闭环，Finalization 时转 Accepted）。每步重入 Review Gate。
日期：2026-06-24
目标版本：v0.3.0

**Scope（本 ADR 已确立的稳定契约）：**
- Artifact schema（`ExperienceArtifact` / `ArtifactRule` / `Provenance`，见 D2）
- ArtifactBuilder production bridge（`ArtifactBuilder.build(candidate, promotion_decision) → ExperienceArtifact`，纯转换，Commit 6 已落地）

**Pending（尚未闭环，留待后续 ADR / Review）：**
- Artifact consumption model（消费模型：Experience Selection 选择策略，见 [Runtime Kernel Design v0.2](../design/runtime-kernel-v0.2.md) §B）
- Projection layer（ExperienceProjection 只读投影视图）
- Runtime integration（RuntimeContext 装配与 Runtime Kernel 集成）

关系：承接 [ADR 0016（Experience Evolution Layer，Proposed）](0016-Experience-Evolution-Layer-Architecture.md) 四层语义中 `ExperienceCandidate → ExperienceArtifact` 的跃迁，落地 [ADR 0017（Candidate Lifecycle，Accepted）](0017-Experience-Candidate-Lifecycle-Architecture.md) 在 `PromotionDecision` 处留空的 **Artifact 承载层**。本 ADR **不**实现 ADR 0016 的 Knowledge Projection（Vector / Graph / Retrieval / Memory 消费），那属后续单独 ADR。

## 1. 背景（Context）

v0.2.0（ADR 0017 Accepted）已打通候选经验生命周期：

```
Feedback ─► CandidateProposal ─► CandidateService.create ─► ExperienceCandidate
                                          │
                                       Validator ─► ValidationVerdict
                                          │
                                    PromotionGate ─► PromotionDecision
```

链路在 `PromotionDecision(approved=true)` 处终止。`PromotionDecision` 只是「是否放行 + 依据引用」的瞬时决策（`approved / reason / candidate_id / validation_snapshot_ref` 四字段），**不是经验资产本身**。

```
Candidate("TimeoutError 场景应 retry 3 次")
  ─► Validation ─► PromotionDecision(approved=true)
  ─► ❌ 之后无稳定资产形态，无法被 Memory / Retrieval / Agent Runtime 消费
```

## 2. 问题（Problem）

1. 晋升后的经验缺少稳定实体（asset），无法长期持有、追踪、被下游消费。
2. 若直接在 Evolution Layer 内塞「知识沉淀 / 向量 / 图」，会让 Evolution 退化为「大杂烩」，违背 0016/0017 边界。
3. 需要一个**中间承载层**先稳定 `Validated Experience → Stable Experience Artifact`，再谈消费（Projection / Retrieval）。

本阶段目标定性：

```
经验资产化（experience as a stable asset）
    ——而非——
经验智能化（retrieval / reasoning / agent injection）
```

## 3. 决定（Decision）

### D1 — MVP Artifact 类型 = `EXPERIENCE_RULE`

`ExperienceArtifact` 第一阶段只落地一种类型 `EXPERIENCE_RULE`：**被验证的条件化经验规则**（rule + expected_outcome + 冻结 confidence）。

理由（最小可落地）：它与现有 `Candidate.Hypothesis{context, condition, action, expected_outcome}` 1:1 同构，无需引入新语义、不绑定执行/运行时；`artifact_type` 设为枚举，未来可扩展。

本期不选（留 `artifact_type` 扩展位）：`Skill / Skill Hint`（隐含可执行能力，需 Tool/Runtime 绑定 → 触碰 Agent Runtime）、`Prompt / Instruction`（属 Prompt Projection 产物，是消费侧投影而非 Artifact 本体）、`Behavior Policy / Agent Strategy`（耦合 Agent 运行时决策）、`Knowledge Unit`（语义过宽，易漂移成知识库）。

### D2 — Artifact 数据模型（能力单元，非 title/content/embedding）

```
ExperienceArtifact
├── artifact_id          唯一标识
├── artifact_type        枚举（MVP: EXPERIENCE_RULE）
├── status               枚举（MVP: ACTIVE；ARCHIVED 预留，本期无流转逻辑）
├── name                 人类可读名称（派生视图，非语义载体 / 非匹配依据）
├── rule  (ArtifactRule 能力核心)
│     ├── context
│     ├── condition
│     └── action
├── expected_outcome     预期结果（D1 必备：描述「何时应用 + 期待什么结果」，供未来 Evaluation 判断价值）
├── confidence           晋升时刻的验证置信度快照（冻结值，见 D3）
├── provenance (Provenance 来源引用，MVP 仅 source_type + source_id)
│     ├── source_type    例："promotion_decision"
│     └── source_id      例：PromotionDecision / candidate 关联 id
└── created_at
```

铁律对齐（继承 0016/0017）：

- 语义只由 `rule + expected_outcome` 承载；`name` 为人类可读派生视图，**不作语义载体、不作未来匹配/投影依据**。
- `provenance` 引用而非复制，MVP **仅** `{source_type, source_id}`；**不**提前建 `Artifact → Candidate → Event → Feedback` 完整 lineage——完整血缘留 Projection Layer。
- Artifact 是「相变固化」的稳定资产，本期 `confidence` 为晋升快照、`status` 无流转。

### D3 — `confidence` 取 Promotion 快照，不回写 Candidate

```
错误：Candidate.confidence ──实时绑定──► Artifact.confidence   （Candidate 后续可能变化）
正确：PromotionDecision（晋升时刻）──快照──► Artifact.confidence   （不可变资产）
```

Promotion 后 Artifact 即不可变经验资产；其 `confidence` 是晋升瞬间的置信度快照，不随后续 Candidate 再验证漂移。本期亦**不**回填 `Candidate.lineage.promoted_to`（需 CandidateService 介入，会改动 v0.2.0 已冻结的 lifecycle 行为），列为后续开放点。

### D4 — 三个构件，职责单一，不合并

| 构件 | 位置 | 职责 | 禁止 |
|------|------|------|------|
| `ArtifactRepository`(ABC) + `InMemoryArtifactRepository` | experience-artifact | `add / get / list` | 绑定 DB/Vector/Graph |
| `ArtifactService` | experience-artifact | `create / get / list` | `generate / retrieve / embed / project / inject` / promotion / validation / builder / lifecycle |
| `ArtifactBuilder` | **experience-evolution**（Commit 6，本 ADR 范围，非 Commit 5） | `build(candidate, promotion_decision) → ExperienceArtifact`（纯函数，要求 approved=true） | 持久化 / 调用 ArtifactService / 改 PromotionGate 职责 |
| `ArtifactReader`(Protocol) + 最小实现 | experience-artifact（Commit 7） | `get_active_artifacts()` | 接入 Memory / Retrieval / Agent Runtime |

PromotionGate 职责不变（只判断是否晋升）；ArtifactBuilder 只负责「生成晋升后的资产描述」。**不合并职责**。

### D5 — 依赖方向（关键架构判断）

```
feedback ─► experience-evolution ─► experience-artifact          （单向，允许）
                                          └────────► projection layer（未来，另立 ADR）
```

- **允许** `experience-evolution → experience-artifact`：故 `ArtifactBuilder`（同时需要 Candidate + PromotionDecision + Artifact 模型）落在 experience-evolution 侧（Commit 6）。
- **禁止** `experience-artifact → experience-evolution`：artifact 层只依赖 pydantic，**不导入** evolution / feedback / experience（AST 校验）。
- **禁止** Artifact 反向参与 Candidate 生命周期：本期 Artifact 仅前向引用来源 id；Candidate→Artifact 反向血缘本期不做。

## 4. 非目标（Non-goals，Commit 5/6/7 全程禁止）

- ❌ Vector Store（Retrieval contract 未定）
- ❌ Graph Memory（经验关系模型未稳定）
- ❌ Retrieval / Memory 写入 / Agent 注入（消费链路需单独 ADR）
- ❌ Prompt / Skill / Policy 自动生成（Artifact 类型仅 `EXPERIENCE_RULE`）
- ❌ Artifact 持久化后端（DB）、Artifact 状态流转（archive / supersede）、Candidate 回填 `promoted_to`
- ❌ 修改 Agent Runtime / Memory Layer / ExperienceEvent / ExperienceStore 契约
- ❌ 修改 `.shanhai-meta` / Context Foundation（已封板）

## 5. 依赖方向（Dependency Direction，冻结）

```
feedback ─► experience-evolution ─► experience-artifact ─► experience（只读事实，不变）

# 不变量
- experience-artifact 仅依赖 pydantic；不 import evolution / feedback / experience
- experience-evolution → experience-artifact：单向（仅 ArtifactBuilder，Commit 6）
- ArtifactService 不参与 promotion / validation / lifecycle
- Artifact 不反向参与 Candidate 生命周期
```

## 6. 未来扩展（Future Extension，留位不实现）

```
ExperienceArtifact
   ├── Vector Projection
   ├── Graph Projection
   ├── Prompt Projection
   └── Skill Projection      → Projection Layer + Memory 消费（ADR 0019+，单独建立）
```

`artifact_type` 枚举扩展、Artifact 生命周期（ACTIVE / ARCHIVED / SUPERSEDED + 再验证回退）、Candidate↔Artifact 双向血缘，均为后续阶段。

## 原因

- **补齐资产承载层**：把瞬时 `PromotionDecision` 沉淀为稳定 `ExperienceArtifact`，让被验证经验可管理 / 可追踪 / 可消费，且不污染 Evolution Layer 职责。
- **MVP 单类型 `EXPERIENCE_RULE`**：与 Hypothesis 同构，最小可落地、零运行时耦合，保留扩展位。
- **confidence 快照 + 不可变资产**：避免 Candidate 后续变化污染已晋升资产；守住「相变固化」语义。
- **ArtifactBuilder 归 evolution**：满足 `evolution → artifact` 单向依赖，杜绝 `artifact → evolution` 反向耦合。
- **provenance 仅 source 引用**：避免提前设计完整 lineage / Event Graph，把复杂度留给 Projection Layer。

## 影响

- 新增独立包 `services/experience-artifact`（仅依赖 pydantic）；experience-evolution 在 Commit 6 新增对 artifact 的单向依赖。
- 不触碰 v0.2.0 已冻结内容（Candidate lifecycle 行为 / ExperienceEvent / ExperienceStore / Agent Runtime / Memory）。
- 不触碰本阶段「暂不开发」清单（行情 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **MVP 直接做 Skill / Prompt / Policy**：耦合 Agent Runtime 或属投影产物，不采纳；先做 `EXPERIENCE_RULE`。
- **Artifact confidence 实时绑定 Candidate**：Candidate 可变会污染已晋升资产，不采纳；改为晋升快照。
- **ArtifactBuilder 放 experience-artifact**：会形成 `artifact → evolution` 反向依赖，不采纳；放 experience-evolution。
- **provenance 直接建完整 Artifact→Candidate→Event→Feedback lineage**：过早复杂化，不采纳；MVP 仅 `{source_type, source_id}`。
- **在本 ADR 一次性做到 Retrieval / Vector / Graph / Agent 注入**：Retrieval contract 未定、关系模型未稳定，不采纳；分层分 ADR。
