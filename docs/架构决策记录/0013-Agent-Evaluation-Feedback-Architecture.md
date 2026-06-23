# ADR 0013：Agent Evaluation Feedback 架构

状态：已采纳
日期：2026-06-23

## 背景

ShanHai 已具备完整的「运行 → 记录 → 评估」前半段：

- Agent Runtime（think → act → observe，ADR 0006）产出结构化 `RunResult` / `Step`。
- `RunStore`（ADR 0008）+ Local-first 持久化（ADR 0009）把每次运行可靠沉淀为可读数据。
- Evaluation Loop Layer 1（ADR 0010）以 `RuntimeEvaluator` 把运行轨迹度量为 `EvaluationResult`（`success` / `step_count` / `tool_usage_count` / `error_type`）。
- Agent Memory（ADR 0012）定义了三层记忆，其中 **Experience Memory**（`scope=EXPERIENCE`）负责跨运行的经验沉淀，经 `MemoryTool → MemoryService → MemoryStore` 访问。

但目前 `EvaluationResult` 产出后**就地消费即止**——度量数据没有被提炼为可复用的经验，也没有回流到 Experience Memory。换言之，闭环只走到「度量」，缺了「**从度量中学到什么、并把它沉淀下来供以后用**」这一段。

下一阶段需要建立 **Evaluation Feedback 闭环**：`Evaluation → Feedback → Experience Memory`，让 Agent 的每次运行不仅被度量，还能被**归因、提炼、沉淀**，并最终反哺后续运行。本 ADR **只设计架构，不实现代码**，目标是确定：Feedback 层定位、闭环结构、`EvaluationResult` 与 Experience Memory 的边界、Experience Candidate 的生成规则，以及如何支撑未来投资分析场景。

约束（AGENTS.md / 协作协议）：

- Feedback 是新的组合层，属架构变更，先 ADR 后实现（本 ADR）。
- 模块独立 + 调用链铁律：Feedback 不直接访问数据库、不直接访问 Memory 存储后端、不直接调用模型；写经验统一走 `MemoryTool → MemoryService → Storage`。
- 不得破坏 ADR 0010「Evaluation 只读取数、单向依赖 agent-runtime」与 ADR 0012「Memory 经 Tool/Service 访问、不重复拥有知识」的既有边界。

## 待决问题（评审重点）

1. **定位**：Feedback 是 Evaluation 的一部分，还是独立一层？它和「度量」有什么本质区别？
2. **闭环结构**：`Evaluation → Feedback → Experience Memory` 各环节的输入/输出是什么？闭环如何「合拢」（经验如何反哺下一次运行）？
3. **边界**：`EvaluationResult` 与 Experience Memory（`MemoryRecord`）各自拥有什么？如何避免把原始度量直接堆进经验库（污染、冗余）？
4. **生成规则**：从 `EvaluationResult` 到一条可沉淀的经验，需要什么**确定性规则**来决定「什么值得记、记什么、记多少、何时晋升」？
5. **未来场景**：如何让这套机制天然支撑「策略复盘 / 判断正确性分析 / Agent 能力提升」？
6. **模块归属**：Feedback 代码应落在哪个模块，才能既连接 evaluation 与 memory，又不让二者互相依赖？

## 决定（建议方案，待确认）

### 1. 定位：Feedback 是「度量 → 经验」的解释/归因层

三个动词区分三段职责，互不重叠：

| 环节 | 动词 | 本质 | 产出 |
|------|------|------|------|
| Evaluation | **度量**（measure） | 客观量化「发生了什么」 | `EvaluationResult`（metrics + passed） |
| Feedback | **归因/提炼**（interpret） | 从度量中判断「意味着什么、该学什么」 | `ExperienceCandidate`（候选经验） |
| Experience Memory | **沉淀**（remember） | 把有价值的经验长期保存、供检索复用 | `MemoryRecord(scope=EXPERIENCE)` |

- **Feedback 不是 Evaluation 的子集**：Evaluation 只回答「成功/失败、几步、几次工具调用」（确定性度量）；Feedback 回答「这次失败属于哪类模式、是否退化、有无可复用的有效路径」（解释 + 取舍）。二者数据来源、时效、产出形态不同。
- **Feedback 不是 Memory 的子集**：Memory 负责「存与取」；Feedback 负责「决定什么值得存」。Feedback 是二者之间的**组合/编排层**。

### 2. 闭环结构

```
Agent 运行 → RunResult → RunStore（落盘，ADR 0008/0009）
                              │ 只读
                              ▼
                        Evaluator → EvaluationResult（度量，ADR 0010）
                              │ 只读消费
                              ▼
                        Feedback（本 ADR）
                          ├─ 归因规则：EvaluationResult(+RunRecord) → ExperienceCandidate[]
                          └─ 去重 / 合并 / 晋升
                              │ 经 Tool/Service（不直连存储）
                              ▼
                        Experience Memory（沉淀，ADR 0012：scope=EXPERIENCE）
                              │ 供后续运行检索（MemoryTool，ADR 0012）
                              └──────────────► 反哺下一次 Agent 运行（闭环合拢）
```

- **写侧（本 ADR）**：`Evaluation → Feedback → Experience Memory`——把运行的度量提炼为经验并沉淀。
- **读侧（ADR 0012 已定义）**：`Agent → MemoryTool → Experience Memory`——下一次运行检索经验。二者合起来构成完整闭环：**运行 → 评估 → 反馈 → 经验 → 改进（下一次运行）**。
- 运行形态：**离线/按需**（与 ADR 0010 一致）。输入一个或一批 `(EvaluationResult, RunRecord)` → 产出并晋升经验。不引入常驻服务、不引入队列。

### 3. `EvaluationResult` 与 Experience Memory 的边界

| 维度 | `EvaluationResult`（evaluation） | Experience Memory（`MemoryRecord`，memory） |
|------|--------------------------------|---------------------------------------------|
| 本质 | 一次评估的**客观度量** | 跨运行**可复用的经验/教训** |
| 时效 | 绑定单次 run | 长期累积、可检索 |
| 内容 | `metrics` + `passed` + `detail` | 提炼后的结论 / 模式 / 建议 |
| 产生 | Evaluator 确定性产出 | Feedback 从一条或多条 `EvaluationResult` 提炼并经规则筛选 |
| 数量 | 每 run 至少一条（可多评估器） | **远少于**评估结果（只沉淀有价值的） |
| 来源关系 | 是 Experience 的**原料**，不被复制 | 经 `source` / `metadata` **引用** run_id / evaluator，而非内嵌原始 metrics |

**边界铁律**：

- **Experience 不复制原始度量**：经验记录只存「提炼结论」，并以 `source=run_id` / `metadata={evaluator, evaluation_ref}` **引用**评估结果；原始 metrics 仍归 `EvaluationResult`（及未来 `EvaluationStore`）所有，避免双写、漂移与冗余膨胀。
- **方向单一**：`EvaluationResult` → Feedback → Experience；Experience 不回写 Evaluation。
- **职责不越界**：Evaluation 永远只度量（不提炼），Memory 永远只存取（不判断价值），价值判断只在 Feedback。

### 4. Experience Candidate 生成规则

引入 `ExperienceCandidate`——一条**尚未持久化**的候选经验，由 Feedback 规则从评估结果派生；经去重/合并/晋升后，才成为 `MemoryRecord(scope=EXPERIENCE)`。

**`ExperienceCandidate` 形态（建议，仅定义不实现）**：
- `kind`：经验类型（`failure_pattern` / `regression` / `effective_path` / …）。
- `agent`：归属 Agent。
- `summary`：提炼后的结论文本（人/Agent 可读）。
- `dedup_key`：去重键（如 `agent + kind + error_type`），相同键合并而非重复存。
- `source_run_ids: list[str]`、`source_evaluator: str`：来源引用（不内嵌原始 metrics）。
- `signals: dict`：触发本候选的关键度量快照（精简，用于解释「为什么生成」）。
- `score`：置信/重要度（用于排序与晋升阈值判定）。
- `created_at`。

**生成规则（Layer 1，确定性、零外部依赖，全部来自 `EvaluationResult` + 只读 `RunRecord`）**：

1. **失败归因（failure_pattern）**：`EvaluationResult.passed == False` 时，按 `error_type` 生成失败模式候选（如 `PermissionError` → 「该 Agent 调用了未授权工具」）。`dedup_key = agent + "failure" + error_type`。
2. **退化检测（regression）**：同一 `agent` 跨多次 run 对比，`success` 率下降，或 `step_count` / `tool_usage_count` 较历史基线异常上升 → 生成退化候选。需要批量 `EvaluationResult`（经 `RunStore.list_runs` 取同 agent 历史，调用方传入）。
3. **有效路径（effective_path）**：`passed == True` 且高效（`step_count` 低于历史中位、工具使用合理）→ 生成「可复用有效路径」候选。
4. **去重 / 合并**：相同 `dedup_key` 的候选**合并计数并更新 `score`**，不产生重复经验条目。
5. **晋升阈值**：候选需达到阈值才晋升为 Experience（如同一失败模式累计出现 ≥ N 次，或 `score` ≥ 阈值）。**只有晋升的候选**经 `MemoryTool` 写入 Experience Memory；未达阈值的候选保持「候选」态（进程内/可选轻量存储），避免噪声污染经验库。

**规则边界**：

- 规则**确定性、可复现**，不调用模型（与 ADR 0010 Layer 1 同源原则）。
- 需要「模型在环」的归因（如 LLM 复盘总结失败根因）属未来 Layer 2/3：**仍不得由 Feedback 直连模型**，而是经 Tool（如 `llm_judge`）或独立「复盘 Agent」产出结构化结论，Feedback 只消费其结果。本阶段仅预留，不实现。

### 5. 模块归属与依赖方向

- 新增**独立组合层** `services/feedback`（`shanhai_feedback`）：它**同时消费** evaluation 的 `EvaluationResult` 与 memory 的写入能力，是连接二者的编排层。
- 依赖方向（单向，不破坏既有边界）：

```
feedback ──→ evaluation（只读消费 EvaluationResult / Evaluator 产物）
        └──→ memory（经 MemoryService / MemoryTool 写 Experience；不持有 MemoryStore）
        └──→ agent-runtime（只读 RunRecord / RunResult 作为归因上下文）
```

- **关键**：把 Feedback 单列为顶层组合层，使 `evaluation` 与 `memory` **互不依赖、各自仍单向依赖 agent-runtime**（守住 ADR 0010 / 0012 的依赖约束）。若把 Feedback 塞进 evaluation 会让 evaluation 依赖 memory，塞进 memory 会让 memory 依赖 evaluation——都破坏既有单向性，故均不采纳。
- 数据获取：被评数据与历史评估由**调用方/装配层**从 `RunStore` 取出后传入 Feedback（沿用 ADR 0010「Evaluator 不持有数据源」的范式）；Feedback 自身不直连任何存储。

### 6. 访问边界（强制）

- **禁止 Feedback 直连 DB / 直连 Memory Storage**：写经验经 `MemoryTool → MemoryService → MemoryStore`；读评估结果用内存对象或未来 `EvaluationStore` 抽象。
- **禁止 Feedback 调用模型 / 侵入 Runtime**：不依赖 ModelRouter/Provider，不修改 Agent Runtime / Evaluator 行为。
- **禁止 Experience 复制原始度量**：经验只引用 run_id / evaluator，不内嵌 metrics。
- **依赖单向**：`feedback → evaluation + memory + agent-runtime`（均只读/经抽象），三者不反向依赖 feedback。

### 7. 支撑未来投资分析场景

| 场景 | 闭环落点 | 数据来源 | 说明 |
|------|---------|---------|------|
| **策略复盘** | Investment Evaluation（Layer 3，远期）→ Feedback → Experience | RunStore（策略运行）+ Evaluation（决策结果度量） | 策略运行被度量后，Feedback 按规则提炼「策略 X 在情形 Y 下表现/失误」候选，晋升为经验；后续策略运行经 `MemoryTool` 检索复用。 |
| **判断正确性分析** | Output/Investment Evaluation → Feedback → Experience | Evaluation（判断 vs 实际结果，需 ground truth）+ RunRecord | 当具备结果回填时，Feedback 归因「判断对/错及原因」，沉淀为正确性经验，支撑「下次类似判断更准」。 |
| **Agent 能力提升** | 全链路闭环 | 累积的 failure_pattern + effective_path 经验 | 失败模式让 Agent 避免重复踩坑，有效路径让 Agent 复用成功经验，形成「运行 → 评估 → 反馈 → 经验 → 改进」的能力进化闭环——直接服务山海「持续学习的市场认知系统」。 |

这套机制使「评估数据」不再是一次性产物，而是被持续转化为**可累积、可检索、可反哺**的经验资产，与 ADR 0012 的 Experience Memory 共同构成 Agent 自我提升的基础设施。

## 原因

- **三段分层（度量 / 归因 / 沉淀）** 让语义清晰、职责单一：Evaluation 专注客观度量，Feedback 专注价值判断与提炼，Memory 专注存取。任一环节演进不污染其它环节，契合「架构正确性 > 模块边界 > 长期扩展性」。
- **Feedback 独立为组合层** 是守住 ADR 0010 / 0012 既有单向依赖的唯一干净解法，避免 evaluation 与 memory 相互依赖。
- **Experience 只引用不复制度量** 保证单一事实来源（原始度量归 Evaluation），杜绝双写漂移与经验库膨胀，呼应 ADR 0012「Memory 不重复拥有知识」。
- **确定性候选规则 + 晋升阈值** 让经验沉淀**可控、可复现、抗噪**：只有反复出现/高置信的模式才进经验库，避免一次性噪声淹没有效经验；模型在环的复杂归因留待后续，避免过早复杂化。
- **复用既有抽象**（RunStore / EvaluationResult / MemoryTool）使整条闭环成为**纯增量**，不改既有调用方与运行行为。

## 影响

- 新增模块 `services/feedback`（`shanhai_feedback`）：`ExperienceCandidate` + `FeedbackRule`（抽象）+ Layer 1 规则实现（failure_pattern / regression / effective_path）+ `FeedbackEngine`（编排：评估结果 → 候选 → 去重/晋升 → 经 `MemoryTool` 写 Experience）。依赖 `evaluation` + `memory` + `agent-runtime` 抽象，不依赖 DB / 模型。
- `evaluation`：**零改动**（Feedback 只读消费其产物）。未来若需持久化评估结果以支撑跨 run 退化检测，再按 ADR 0010 所述「另开 ADR 设计 `EvaluationStore`」，不在本 ADR 决定。
- `memory`：作为写入下游被 Feedback 调用（经 `MemoryService`/`MemoryTool`），无新增对外行为约束（其实现仍待 ADR 0012 落地）。
- `agent-runtime` / `model-router` / `wiki-engine`：**零改动**。
- local-first：默认进程内候选 + `InMemoryMemoryStore`，无外部依赖即可跑测试（沿用 ADR 0009/0012）。
- 依赖次序提示：本 ADR 的实现**依赖 ADR 0012 Experience Memory 先落地**（写侧目标存在）。实现排期需在 Memory Layer 之后。
- 文档：CHANGELOG / PROJECT_STATE / docs 索引在**实现阶段**同步更新（本 ADR 阶段不写代码）。
- 不触碰本阶段「暂不开发」清单（行情/交易/自动交易/量化/回测）。

## 备选方案（已考虑）

- **把 Feedback 并入 Evaluation（Evaluator 直接写经验）**：会让 evaluation 依赖 memory，破坏 ADR 0010 单向依赖，且混淆「度量」与「价值判断」职责，不采纳。
- **把 Feedback 并入 Memory（MemoryService 内做提炼）**：会让 memory 依赖 evaluation，破坏 ADR 0012 边界，且让存储层承担业务判断，不采纳。
- **把原始 `EvaluationResult` 直接全量写入 Experience Memory**：经验库被一次性度量淹没、与 Evaluation 双写漂移、检索价值低，不采纳；改为「提炼 + 引用 + 阈值晋升」。
- **候选无阈值、即时晋升**：噪声经验（偶发失败）污染经验库，降低后续检索信噪比，不采纳；引入去重合并 + 晋升阈值。
- **Feedback 直接调用模型做归因总结**：破坏「不直连模型」铁律且引入非确定性，不采纳；模型在环的归因经 Tool / 复盘 Agent 产出、Feedback 只消费结构化结果（留待 Layer 2/3）。
- **引入常驻 Feedback 服务 / 事件队列实时触发**：超出当前需要、过早引入运维复杂度，不采纳；本阶段离线/按需，与 ADR 0010 一致。

## 增补（Addendum，2026-06-23）：Stage 1 实现决策

> 背景：本 ADR §6 成文于 ADR 0014 之前，当时把 Feedback 写经验路径描述为「经 `MemoryTool → MemoryService → MemoryStore`」。其后 ADR 0014（Event Log Lite）确立 `ExperienceStore.append` 为经验写原语，ADR 0012 Layer 1 落地时将 Memory 的 `EXPERIENCE` scope 设为**对 Agent 只读**（写抛 `PermissionError`）。二者与 §6 字面冲突。经 Phase 2 评审，Stage 1 按下述决策落地，§6 原文据此修正。

### A. 写经验路径归口到 Experience 领域服务（决策①，已采纳）

- **Feedback 写经验经 `ExperienceStore.append()`（service → service），不经 MemoryService/MemoryTool。** 不给 `MemoryService` 增加 `EXPERIENCE` 写能力。
- 理由：「Agent 禁止直连存储」约束的主体是 **Agent**；Feedback 是离线/按需的**系统编排层（非 Agent）**，调用 Experience **领域服务**属合规的 Service → Service。
- 由此守住两条不变量：① **Memory 始终是 Agent 的访问层，`EXPERIENCE` 对 Agent 只读**；② **`lesson` 经验只由确定性反馈回路赚取，Agent 不能自写经验**（防自证/噪声污染）。
- 因此本 ADR §5 的依赖方向，在 Stage 1 实现中修正为：

```
feedback ──→ evaluation     （只读消费 EvaluationResult）
        └──→ experience      （经 ExperienceStore.append 写 lesson 事件）
        └──→ agent-runtime    （只读 RunRecord / RunResult 作为归因上下文）
```

  `feedback` **不依赖 `memory`**；读侧反哺仍由 ADR 0012 的 `MemoryTool`（`EXPERIENCE` scope，只读 `search/read`）承担，二者解耦。

### B. 晋升产物 = `type=lesson` 的 `ExperienceEvent`（衔接 ADR 0014）

- `ExperienceCandidate` 晋升后，以 `ExperienceEventType.LESSON` 事件 `append` 进 `ExperienceStore`（呼应 ADR 0014 §3/§4）。
- 引用而非复制：`refs.run_id` 取促发 run；`refs.evaluation_ref = f"{run_id}:{evaluator}"`；原始 metrics 不内嵌，`payload` 仅存提炼结论与精简 `signals` + `source_run_ids`。

### C. Stage 1 范围收敛（已采纳）

- **仅实现 `FailurePattern → Candidate → Lesson` 闭环**：单规则 `FailurePatternRule`（`passed==False` 按 `error_type` 产候选）+ `CandidateRegistry`（进程内去重/合并/计数）+ 阈值晋升 + `ExperienceStore.append`。
- **不在 Stage 1**：`regression` / `effective_path` 规则、`Episode` / `SemanticExperience` 投影（属 ADR 0014 Stage 2/3）、模型在环归因、Vector/Graph/CQRS、新增 DB；不修改 `AgentRunner` 与 `ExperienceStore` 契约（只 append）。
- 模块落点不变：新增 `services/feedback`（`shanhai_feedback`），离线/按需运行。

## 增补（Addendum 2，2026-06-23）：Feedback / Candidate 语义对齐（ADR 0015 Decision F 衍生）

> 背景：ADR 0015 Decision F 确立 Experience 三层演进边界（`ExperienceEvent → ExperienceCandidate → ExperienceArtifact`），并指出「`ExperienceEvent = Experience`」是长期风险假设。本增补据此补充 Feedback 的架构语义定位，**不改动 Stage 1 任何代码与行为**。

### D. Feedback 的本质产物是 `ExperienceCandidate`，而非 `lesson` 事件

- Feedback 归因/提炼的**本质产物是 `ExperienceCandidate`**（候选规律），与本 ADR §1/§4 一致。`lesson` 事件只是 Stage 1 候选晋升后的**落地形态之一**（写入事件层供即时反哺）。
- 因此 Feedback 的架构语义修正为：

```
Evaluation
   │
Feedback
   │
ExperienceCandidate        ← Feedback 的本质产物（候选规律）

Stage 1（已实现）：
   Candidate → ExperienceEvent(type=lesson)     # 事件层即时反馈，不代表稳定知识

Future（延期，另启 ADR）：
   Candidate → ExperienceArtifact               # 经验证/晋升的可复用、可演化经验资产
```

### E. 语义边界声明（约束未来，不改当前实现）

- **`lesson` 事件是事件层反馈，不等于稳定知识**：它属事实流（`ExperienceEvent`），是 Feedback 在事件层的即时归因产物，**不等同于** `ExperienceArtifact`。
- **`ExperienceArtifact` 经 Candidate Promotion 生成**：未来由 `ExperienceCandidate` 经验证/晋升固化为经验资产，该层另启 ADR 设计，不在当前范围。
- **当前实现保持不变**：Stage 1 的 `ExperienceCandidate` / `FailurePatternRule` / `CandidateRegistry` / `FeedbackEngine`（晋升落 `type=lesson` 事件）及其依赖方向、写经验路径（决策①）**全部不变**。本增补仅澄清架构语义层次，为未来 Artifact 化预留边界，避免届时重构。

### F. `ExperienceCandidate` 属 Experience Evolution 概念，不长期绑定 Feedback（演进声明）

> 非阻塞演进声明：`ExperienceCandidate` 本质属于 **Experience Evolution** 概念，而非 Feedback 私有产物。当前 Stage 1 由 Feedback 模块产生与管理，仅是起步形态。

- **当前 Stage 1**：`ExperienceCandidate` 由 `Feedback` 模块产生和管理（`CandidateRegistry` 进程内去重/合并/晋升）。
- **未来**：随着 `ExperienceArtifact` Promotion、Experience Mining、成功路径发现等能力增加，`CandidateRegistry` 可能演进为**独立的 Experience Evolution Layer**。
- **原因**：未来 Candidate 来源不会只有 Feedback。例如**成功策略发现 / 高频有效路径挖掘 / Agent Skill Evolution** 都可能产生 Candidate。因此避免长期绑定 `Feedback → Candidate` 这一单一来源假设。
- **本声明不改当前实现**：Stage 1 仍由 Feedback 承载 Candidate 生产与管理；演进至独立 Layer 时另启 ADR。
