# ADR 0016：Experience Evolution Layer 架构（让事实成长为能力）

状态：**提案中（Proposed）** —— 仅规划，不实现代码。
日期：2026-06-23
关系：承接 ADR 0014（Event Log Lite）/ ADR 0015（Outcome 回填基座，Stage 2-a）/ ADR 0013（Evaluation Feedback）。ADR 0015 解决「**如何让事实进入系统**」；本 ADR 解决「**如何让事实成长为能力**」。二者是不同问题，故分立。

## 1. 背景

ShanHai 已打通经验闭环的事实层：

- ADR 0014 确立 `ExperienceEvent`（append-only 不可变事件）。
- ADR 0015 Stage 2-a 补齐生产者体系（`ExperienceRecorder` / `OutcomeIngestor` / `Feedback`）与延迟结果回填，打通 `decision → outcome → lesson` 事实链。
- ADR 0013 Stage 1 在 `feedback` 内实现 `ExperienceCandidate` + `CandidateRegistry`（去重/合并/阈值晋升），晋升落 `type=lesson` 事件。

但**事实不等于能力**。当前隐含风险：若把 `ExperienceArtifact` 当作「更好的 lesson」直接塞进知识库，系统会退化为传统 RAG：

```
失败记录 → 总结经验 → 存知识库（Vector / Search）
```

这是「记忆」，不是「进化」。EvoMap 的核心启发不是 Memory，而是：

> **Experience = 可传播、可评价、可演化的能力单元。**

本 ADR 规划 **Experience Evolution Layer**：把「候选经验」经验证、晋升、谱系追踪、持续演化，固化为**可复用、可组合、可验证的认知资产**（`ExperienceArtifact`），并明确其与外部知识（Knowledge Document / WeKnora / llm-wiki）的边界。

约束（AGENTS.md / 协作协议）：本 ADR 属架构规划，先 ADR 后实现；本轮**不写任何代码、不改既有 schema/contract**。

## 2. 四层语义边界（冻结）

| 类型 | 职责 | 当前状态 |
|------|------|----------|
| `ExperienceEvent` | 事实记录（发生过什么） | 已实现（ADR 0014/0015） |
| `ExperienceCandidate` | 待验证的经验假设（可能是规律） | 已实现于 feedback（ADR 0013 Stage 1） |
| `ExperienceArtifact` | 已验证、可复用的能力单元 | 本 ADR 规划，未实现 |
| `Knowledge Document` | 外部知识信息（非经验） | 属 Knowledge Engine，另域 |

关系链（单向，不成环）：

```
External Knowledge
        │
        ▼
      Agent
        │
        ▼
 ExperienceEvent          事实层（ADR 0014/0015）
        │
        ▼
 ExperienceCandidate      候选层（ADR 0013，演进归本 ADR）
        │
   validation             验证
        │
        ▼
 ExperienceArtifact       能力层（本 ADR）
        │
        └──► Knowledge Projection ──► WeKnora / llm-wiki   知识投影层（下游）
```

**铁律**：

- `ExperienceArtifact ≠ Knowledge Document`：前者是「已验证可复用能力」，后者是「外部知识信息」。
- **WeKnora / llm-wiki 不是 Experience 的存储**，而是 `ExperienceArtifact` 的**下游知识投影层**。Experience 产生层与 Knowledge Projection 层**解耦**。

## 3. 待决问题（下一阶段评审重点，本 ADR 仅列出）

1. **Candidate 来源解耦**：如何让 `ExperienceCandidate` 接受多来源（Feedback / Outcome Evaluation / Successful Path Mining / Agent Self Discovery / Human Curated），而不长期绑定 Feedback？
2. **Artifact 模型**：`ExperienceArtifact` 应包含哪些结构化字段才能「可传播、可评价、可演化」，而非退化为 `title/content/embedding`？
3. **Validation**：候选经验如何被验证（回测 / outcome 复核 / 重复出现 / 人工确认）才允许晋升为 Artifact？
4. **Promotion / Lineage / Evolution**：晋升规则、谱系追踪（Artifact 从哪些 Candidate/Event 而来）、演化历史（mutation → evaluation → promotion）如何建模？
5. **CandidateRegistry 归属**：何时、如何把 `CandidateRegistry` 从 `feedback` 子模块迁出为独立 Experience Evolution Layer？
6. **依赖与边界**：新层如何只读消费事实层、单向写入 Artifact 存储，且不破坏 ADR 0010/0012/0014/0015 既有边界？

## 4. 规划方向（建议，待后续确认，不实现）

### 4.1 ExperienceArtifact 须是「能力单元」

目标字段（建议，最终以实现期 ADR 修订为准）：

```
ExperienceArtifact
├── identity            稳定标识（可被引用/组合）
├── capability          这条经验赋予的能力（做什么）
├── context             适用的情境/前提
├── evidence            支撑证据（引用 Event / Outcome / 评估）
├── applicability       适用范围与边界（何时用、何时不用）
├── evaluation          有效性度量（命中率 / 置信 / 收益）
├── lineage             谱系（由哪些 Candidate/Event 演化而来）
└── evolution history   演化历史（mutation / evaluation / promotion 轨迹）
```

明确**不是** `title / content / embedding` 三元组。

### 4.2 Candidate 来源多元化（解耦 Feedback）

```
        Feedback ─────────┐
Outcome Evaluation ───────┤
Successful Path Mining ───┼──►  ExperienceCandidate
Agent Self Discovery ─────┤
Human Curated ────────────┘
```

`CandidateRegistry` 后续演进为 **Experience Evolution Layer**（独立层），而非 Feedback 子模块。Feedback 退回为「众多 Candidate 生产者之一」。

### 4.3 演化闭环（参考 EvoMap）

```
ExperienceArtifact
      │ mutation     （变异/重组：生成候选变体）
      ▼
   evaluation        （评价：在真实/回放场景验证有效性）
      ▼
   promotion         （晋升：保留更优变体，淘汰劣者）
      └──► 回写 lineage / evolution history
```

## 5. 阶段路线（建议顺序，逐阶段经 Review）

```
Phase 1（已完成）  事实层：ExperienceEvent
Phase 2（当前）    反馈闭环：Decision → Outcome → Candidate
Phase 3（未来）    经验资产化：Candidate → Validation → Artifact      ← 本 ADR 主体
Phase 4           知识投影：Artifact → Projection → WeKnora / llm-wiki
Phase 5           经验演化：Artifact → Mutation → Evaluation → Promotion（EvoMap）
```

对应实现 Stage 建议：

```
Stage 2-b  ExperienceCandidate 生命周期（Event → Candidate → Validation），Candidate 来源解耦起步
Stage 3    ExperienceArtifact 模型与晋升（可复用认知资产）
Stage 4    Knowledge Projection 接入 WeKnora / llm-wiki
Stage 5    Experience Evolution（mutation / evaluation / promotion）
```

## 6. 必须保持的不变量（跨阶段冻结）

- `ExperienceEvent` **append-only**（不可变事件）。
- `outcome` **不修改 decision**（靠 `parent_event_id` 关联）。
- `ExperienceArtifact` **不覆盖 Event**（Artifact 引用 Event，事实层保持原样）。
- **Agent 只读 Experience**（经 `MemoryTool`，无写路径）。
- **Knowledge Projection 与 Experience 解耦**（WeKnora / llm-wiki 是下游投影，不是 Experience 存储）。

## 7. 暂缓（在 `ExperienceArtifact` 模型确定前一律不做）

```
❌ Vector Search           ❌ Graph Experience
❌ WeKnora 接入            ❌ llm-wiki 同步
❌ 自动 Experience Summary（LLM 自动总结）
```

原因：在 Artifact 模型成型前接入知识库/向量检索，会把低质量经验提前污染知识空间，并把系统锁死为 RAG 形态。

## 8. 与既有 ADR 的关系

| ADR | 关系 | 本 ADR 是否要求其改动 |
|-----|------|----------------------|
| 0015（Outcome 回填基座） | 提供事实层与 Candidate 入口；本 ADR 承接其 Decision F 的演进边界 | 否（0015 Decision F 已加前向引用本 ADR） |
| 0013（Evaluation Feedback） | Feedback 降为 Candidate 多来源之一；`CandidateRegistry` 演进为独立层 | 否（0013 Addendum F 已声明该演进方向） |
| 0014（Event Log Lite） | 事实层契约不变；Artifact 引用 Event，不改 Event schema | 否 |
| 0012（Memory） | Agent 仍经 `MemoryTool` 只读 Experience；Artifact 读侧通路另议 | 后续实现期再对齐 |

## 原因

- **分立 ADR**：「让事实进入系统」（0015）与「让事实成长为能力」（本 ADR）是不同问题，混在一处会让 0015 范围失焦、Artifact 设计被事实层细节绑架。
- **先冻结边界、后实现**：在 Artifact 模型未定前接知识库/向量会锁死为 RAG；先以 ADR 冻结「能力单元」语义与不变量，避免未来重构。
- **Candidate 来源解耦**：未来 Candidate 来源远多于 Feedback，提前解耦可避免「Feedback = Experience 入口」的长期绑定。

## 影响

- 本轮：**仅新增本规划 ADR（Proposed）**，不新增/修改任何代码、schema、依赖。
- 未来（经 Review 后另启实现）：新增 Experience Evolution 层（`ExperienceCandidate` 生命周期 + `ExperienceArtifact` + Validation/Promotion/Lineage/Evolution），`CandidateRegistry` 自 `feedback` 迁出。
- 不触碰本阶段「暂不开发」清单（行情 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **把 Artifact/Evolution 并入 ADR 0015**：导致 0015 范围爆炸、事实层与能力层耦合，不采纳；分立本 ADR。
- **直接把 lesson/Artifact 写入 WeKnora / llm-wiki 做向量检索**：退化为传统 RAG，低质量经验污染知识空间，不采纳；WeKnora/llm-wiki 定位为 Artifact 下游投影层。
- **Artifact 用 `title/content/embedding` 简单结构**：无法表达能力、谱系与演化，不采纳；采用能力单元结构（identity/capability/.../evolution history）。
- **CandidateRegistry 长期留在 feedback**：把 Experience 演化绑死单一来源，不采纳；规划迁出为独立层。
