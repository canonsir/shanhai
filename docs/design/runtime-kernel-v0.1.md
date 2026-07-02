# Runtime Kernel Design Review v0.1（设计稿，仅讨论，不编码）

> 状态：**Design Review（Draft for discussion）** — 本文件只做架构设计与方向收敛，不写代码、不新增模块、不新增 Reader、不接 Agent、不接 Memory。
> 阶段：Phase 1 — Agent Runtime / 进入 **Runtime Kernel Design**。
> 前置：Commit 6（ADR 0018 Artifact Bridge）✅ Approved；Commit 7（ArtifactReader）**暂停**，待本 Review 决定消费模型后再定。
> 关联：[ADR 0000 项目元上下文架构](../架构决策记录/0000-项目元上下文架构.md)、[ADR 0012 Agent Memory]、[ADR 0014 Experience Memory]、[ADR 0018 Experience Artifact Layer MVP](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002 Runtime/Meta 分离](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0005 Context Identity Principle](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. 为什么先 Review 再实现

`ArtifactReader` 不是一个简单 CRUD，而是一次**消费模型设计**：谁、以什么形态、在什么时机读取 `ExperienceArtifact`，决定了 Reader 的接口长什么样。若先实现 Reader 再设计 Runtime，会把消费模型**反向锁死**在存储读接口上。因此本 Review 的目标是：

```
先回答「Runtime 如何消费经验」 → 再决定 ArtifactReader 是否存在、长什么样
```

本文件**不**给出最终实现，只收敛方向，并把可延期项显式登记为 future decision。

---

## 1. 现状盘点（设计必须基于真实代码，避免重复造层）

设计 Runtime Kernel 前先确认：**很多职责已经有归属**，Runtime Kernel 不能把它们重新吃进来。

| 已存在能力 | 归属模块 | 现状 |
|---|---|---|
| Agent 执行循环 think→act→observe | `services/agent-runtime`（`AgentRunner` / `BaseAgent`） | 已实现，多步 `max_steps` 循环 |
| 模型访问（解耦） | `services/model-router`（经 `AgentContext.complete`） | 已实现，Agent 不绑定模型 |
| 工具编排 | `services/tools`（经 `AgentContext.use_tool`，受授权约束） | 已实现 |
| 运行记录落库 | `AgentRunner._persist` → `RunStore`（sqlite/postgres） | 已实现，best-effort |
| 三层记忆访问门面 | `services/memory`（`MemoryService` + 三 adapter + `MemoryTool`） | 已实现：`RUNTIME` 读写 / `KNOWLEDGE`·`EXPERIENCE` 只读 |
| 经验事实流 | `services/experience`（`ExperienceEvent` / `ExperienceStore`，append-only） | 已实现 |
| 事实链回填 | `experience/.../ingest`（`ExperienceRecorder` decision/observation + `OutcomeIngestor` outcome） | 已实现 |
| 候选经验生命周期 | `services/experience-evolution`（Candidate→Validation→Promotion） | 已实现 |
| 已验证资产 + 生产桥 | `services/experience-artifact`（Artifact 容器）+ `ArtifactBuilder`（纯转换） | 已实现（Commit 5/6） |

**关键结论**：Runtime Kernel 不是「Agent 执行引擎」（那是 agent-runtime），不是「工具编排器」（那是 tools），不是「模型选择器」（那是 model-router）。这些都已有主人。Runtime Kernel 的责任必须在它们**之外**且**之上**，否则就会变成 Question 1 警告的「万能层」。

---

## 2. 当前架构三层全景

```
                     Meta Layer（人 + AI 协作认知，DEC-0002）
   ContextEvent ─► DecisionRecord ─► CognitionSnapshot ─► current-state.md
        ▲ 治理 / bootstrap，不参与产品 Runtime（AI_CONTEXT.md / DEC-0002 严格分离）
   ──────────────────────────────────────────────────────────────────────
                     Runtime / Experience Layer（Agent 执行世界）
   ExperienceEvent ─► Candidate ─► PromotionGate ─► ArtifactBuilder ─► ExperienceArtifact
        │                                                                   │
        └────────────── (生产侧已闭环) ────────────────────────────────────┘
                                                                            │
                                              (消费侧 = 本 Review 待设计)  ▼
                                                                          ???
   ──────────────────────────────────────────────────────────────────────
                     Runtime Kernel（本阶段设计目标）
                              TODO（见 §4 责任定义）
```

生产侧（`Candidate → Promotion → Artifact`）已完成；**消费侧（`Artifact → ? → Runtime`）未定**，这是 Runtime Kernel Design 的核心缺口。

---

## 3. 一条贯穿全篇的设计原则

> **Runtime Kernel 是「装配 + 边界」层，不是「逻辑 + 万能」层。**

它只做两件别人没做的事：
1. **Context Assembly**：把一次运行所需的「工作集」（输入 + 相关经验投影 + 可用工具/策略）装配成 `RuntimeContext`。
2. **Run Boundary**：拥有一次运行的进入/退出边界，在边界处把运行事实**发射为 ExperienceEvent**（复用既有 ingest，不新造事件流）。

其余一律**委派**：循环→agent-runtime，工具→tools，模型→model-router，存储→各 Service。

---

## 4. Question 1 — Runtime 的核心职责是什么？

避免 Runtime 变万能层。逐项判定用户列出的候选职责：

| 候选职责 | 是否归 Runtime Kernel | 理由 |
|---|---|---|
| context assembling | ✅ **是（核心）** | 目前无人负责「把经验/输入装配成一次运行的上下文」，这是真正的缺口 |
| state transition（运行级） | ✅ 是（运行边界级） | 运行的 created→running→completed/failed 生命周期归 Runtime 边界；**注意**：Agent 微观步骤状态已在 `AgentRunner`，不重复 |
| agent loop | ❌ 否 | 已由 `agent-runtime` 的 `AgentRunner` 拥有 |
| tool orchestration | ❌ 否 | 已由 `tools` + `AgentContext.use_tool` 拥有 |
| decision execution | ❌ 否 | 属 Agent / 未来 Decision Agent，不属 Kernel |

### 决策点 D-A：Runtime Kernel 与 agent-runtime 的关系

- **方案 1（替代）**：Runtime Kernel 取代 agent-runtime，自己跑循环。
  - ✗ 推翻已稳定的 ADR 0006 执行模型，重复造轮子，blast radius 大。
- **方案 2（协调，推荐）**：Runtime Kernel **位于 agent-runtime 之上**，负责装配 `RuntimeContext` 并喂给 `AgentRunner`，在运行边界收集结果发射事件；`AgentRunner` 仍是循环引擎。
  - ✓ 不动 agent-runtime 契约，职责单一，符合「装配+边界」定位。

**推荐：方案 2。** Runtime Kernel = **Context Assembler + Run Boundary**，是 agent-runtime 的「上游装配器 + 下游事件边界」，不吞掉循环。

---

## 5. Question 2 — Context Foundation 如何进入 Runtime？

这是最容易踩雷的一题，因为 [DEC-0002] 已冻结：

> ContextEvent（Meta）与 ExperienceEvent（Runtime）**严格分离**：不共享、不转换、不互相消费。系统级名称不用 "Memory"。

且 [AI_CONTEXT.md] 明确：`.shanhai-meta/` **不参与 Agent 运行**，`CognitionSnapshot` 是「AI Engineer/构建期」的启动认知，不是「产品 Runtime 执行期」的输入。

### 选项与判定

- **方案 A**：Runtime 直接读取 `CognitionSnapshot` / `DecisionRecord` / `ConversationEvent`。
  - ❌ **否决**：直接违反 DEC-0002；把产品运行耦合到项目治理元认知，污染语义。
- **方案 B（推荐基线）**：**Runtime 不消费 Context Foundation**。Meta 层仅服务于「构建期治理」（Review Gate / 架构纪律 / 启动认知），与运行期正交。
  - ✓ 保持 DEC-0002 边界完整。v0.1 采用此方案。
- **方案 C（仅登记为未来方向）**：若将来某项治理事实（如 frozen constraint）确需到达运行期，必须经一个**显式、只读、单向的 ContextProjection**，把 Meta 事实翻译成 Runtime **Policy 对象**——绝不共享 schema、绝不双向。
  - 现在**不建**（遵循 DEC-0004 式纪律：先登记、不实现）。

**推荐：v0.1 = 方案 B。** Runtime Context **不含**任何 Meta 层数据。若未来出现具体需求，再以单向 ContextProjection（Meta→Runtime Policy）跨界，永不共享模型。

> 推论：Runtime Kernel 装配的 `RuntimeContext` 的来源 = **运行输入 + Experience 投影 + 工具/策略**，**不含** cognition.json / decisions。

---

## 6. Question 3 — ExperienceArtifact 如何被消费？（核心）

用户已倾向方案 C（Projection）。逐项判定：

- **方案 A**：`Runtime → ArtifactReader → ExperienceArtifact`。
  - ✗ Runtime 直接理解经验**存储结构**；Kernel 耦合 artifact 内部形态。
- **方案 B**：`Runtime → Memory → Artifact`。
  - ✗ Artifact 被降级成普通 Memory 数据，丢失「资产」语义。
- **方案 C（推荐）**：`ExperienceArtifact → Experience Projection → RuntimeContext`。
  - ✓ Artifact 保持资产层；Runtime 只消费**投影后的上下文**，不触达存储结构。

### 推荐：方案 C，并细化「投影」的职责

定义一个未来组件 **ExperienceProjection（经验投影 / Experience Context Provider）**：

```
RuntimeSituation（当前运行情境：输入 / agent / 目标）
        │
        ▼
ExperienceProjection.project(situation) → ExperienceContext（只读：本次运行相关的若干 Artifact 投影）
        │
        ▼
RuntimeContext（Runtime Kernel 装配）
```

投影的**真正难点**不是「读」，而是「**选**」：如何判断哪些 Artifact 与当前运行相关（按 context/condition 匹配？按 confidence 排序？按 applicability？）。**这正是 `ArtifactReader` 不应现在实现的原因**——Reader 的查询接口必须由投影的**选择需求**反向决定，否则会先验地锁死成一个通用 `list()`。

### 对 ArtifactReader 的结论（回答「是否需要」）

- **需要，但晚于投影设计**：`ArtifactReader` 的定位 = **ExperienceProjection 面向存储的只读端口（read port）**，而非给 Runtime 直接用的 API。
- **Commit 7 恢复条件**：先冻结 ExperienceProjection 的 `project(situation)` 查询形态 → 再据此定义 `ArtifactReader` 接口（如 `find_applicable(context, type, min_confidence, limit)` 而非裸 `list()`）。

---

## 7. Question 4 — Memory 与 Experience 的关系

用户倾向：`ExperienceArtifact != Memory`。**赞同**，并基于现有代码给出精确定位。

现状（已实现）：`MemoryService` 是一个**访问门面（access façade）**，不是存储，已有三 scope：

```
Memory（access façade，门面，非资产）
  ├── runtime scope     进程内 scratchpad（可读写）
  ├── knowledge scope   → KnowledgeService（只读委派）
  └── experience scope  → ExperienceStore 事件（只读委派）  ← 当前是「事件级」
```

### 推荐定位

- **Memory ≠ ExperienceArtifact**：Memory 是**访问/投递门面**；ExperienceArtifact 是 `experience-artifact` 拥有的**资产**。
- 二者关系：Memory 的 `experience` scope **可在未来**从「事件级只读」升级为「**经 ExperienceProjection 投影后的 Artifact 只读视图**」，但 Memory **不拥有、不重定义** Artifact——它只暴露一个 read view。
- 这样既守住「Artifact != Memory」，又复用既有 Memory 门面作为 Agent 侧投递通道，避免另造平行投递路径。

### 两条消费路径的协同（需显式说明，否则会冲突）

| 路径 | 形态 | 时机 | 谁触发 |
|---|---|---|---|
| Path 1（已存在） | `Agent → MemoryTool → MemoryService(EXPERIENCE)` | 运行**中**按需拉取 | Agent 主动 |
| Path 2（本设计提出） | `Runtime Kernel → ExperienceProjection → RuntimeContext` | 运行**前**预装配 | Kernel 主动 |

二者**互补**：Path 2 是运行开始时「策展好的」资产上下文；Path 1 是运行中临时查阅。**约束**：Artifact 级消费一律走投影（Path 2，或由投影回填的 Memory experience-scope），**禁止 Agent 内部裸读 Artifact**。

---

## 8. Question 5 — Runtime 是否产生新的 ContextEvent？

**核心澄清（DEC-0002）：不产生 ContextEvent。** ContextEvent 属 Meta 层（项目推理史）。运行执行事实属 **Runtime/Experience 世界 = ExperienceEvent**。

用户设想的 `RuntimeEvent`，在 ShanHai 语义里就是 **ExperienceEvent**，且**机制已存在**：

```
User Request → Runtime（run boundary）→ Decision → Execution Result
       └─► 在运行边界发射 ExperienceEvent：
            ExperienceRecorder：RunRecord → type=decision（可选 observation）
            OutcomeIngestor   ：外部结果   → type=outcome（parent 挂回 decision）
```

### 推荐

- Runtime Kernel 在**运行完成边界**经既有 `experience.ingest`（service→service，append-only，refs 不复制）发射 ExperienceEvent。
- **不新造**第二条运行事件流；**不发** ContextEvent。
- 若未来出现「运行级生命周期」独立语义（区别于 decision/outcome），按 [AI_CONTEXT.md] 既定口径，那是 **ExperienceEventType 的正常扩展（无需 ADR）**，仍属同一条 experience 事实流，**仍非** ContextEvent。

---

## 9. 身份原则（DEC-0005）在 Runtime 的应用

> 稳定身份归不可变标识符；可变属性归元数据。

Runtime 沿用既有标识，无需新身份方案：

| 对象 | identity（标识符） | metadata（可变） |
|---|---|---|
| 一次运行 | `run_id`（来自 RunStore） | status / 时间戳 |
| 一个情景 | `episode_id`（跨 run 聚合） | — |
| 经验事件 | `event_id` | recorded_at / occurred_at |
| 资产 | `artifact_id` | confidence / status |

未来若引入「Runtime 会话/任务」实体，必须同样遵循：`runtime_*_id` 为身份，时间/状态入 metadata，**不得**把可变信息编码进标识符。

---

## 10. 推荐的目标架构（消费侧填空）

```
                       Runtime Kernel（装配 + 边界）
   RuntimeSituation ─► [Context Assembly] ─► RuntimeContext ─► AgentRunner（既有循环）
            │                  ▲                                     │
            │                  │                                     ▼
            │        ExperienceProjection.project()            Run Result
            │                  ▲                                     │
            │                  │ (read port, 待定)                  ▼
            │            ArtifactReader ──► ExperienceArtifact   [Run Boundary]
            │                                                     experience.ingest
            │                                                  ExperienceEvent(decision/outcome)
            └──────────────────────────────────────────────────────┘

   边界铁律：
   - 不读 Meta（cognition/decisions）—— DEC-0002
   - Artifact 只经 Projection 消费，Agent 不裸读 —— §6/§7
   - 只发 ExperienceEvent，不发 ContextEvent —— §8
   - Kernel 不含循环/工具/模型逻辑 —— §4
```

---

## 11. 本 Review 后待决项（明确延期，逐项再 Review）

| 待决项 | 依赖前置 | 倾向 |
|---|---|---|
| ArtifactReader 是否需要 / 接口形态 | 先冻结 ExperienceProjection 查询形态 | 需要，作为投影的 read port（非通用 list） |
| ExperienceProjection 是否需要 | Runtime Kernel 责任冻结后 | 需要（方案 C 的核心） |
| Runtime Context API（`RuntimeContext` 字段） | D-A 方案 2 确认后 | 待专项设计 |
| Memory Integration（experience-scope 升级为投影视图） | 投影定型后 | 复用既有门面，不另造 |
| Agent Integration | 以上确定后 | agent-runtime 契约不变，Kernel 在其上层装配 |

---

## 12. 非目标 / 约束（本阶段继续遵守）

- 本阶段**只设计、不编码**：不新增 Runtime 模块、不新增 Reader、不接 Agent、不接 Memory。
- 不引入 Vector / Graph / Retrieval / Memory 持久化写入 / Prompt·Skill 自动生成。
- 不破坏冻结不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）。
- ADR 0018 维持**非 Finalize**：生产侧（Candidate→Promotion→Artifact）已确立，消费侧（Artifact→?→Runtime）待本 Review 收敛后再 Finalize。

---

## 13. 建议的下一步（待批准，不自行执行）

1. 确认 **D-A 方案 2**（Runtime Kernel = agent-runtime 之上的「装配 + 边界」层）。
2. 确认 **Q3 方案 C**（Artifact 经 ExperienceProjection 消费）。
3. 批准后，进入 **Runtime Context API 专项设计**（定义 `RuntimeContext` / `RuntimeSituation` / `ExperienceProjection.project()` 形态）。
4. 待投影查询形态冻结，再恢复并重定义 **Commit 7 = ArtifactReader（作为投影 read port）**。

> 当前停在 **Runtime Kernel Design Review**，等待方向批准。不编码、不进入实现、不恢复 Commit 7。
