# ADR 0010：Evaluation Loop 架构

状态：已采纳
日期：2026-06-22

## 背景

ShanHai 已完成 Agent Runtime（think → act → observe，ADR 0006）、结构化运行记录 `RunResult` / `Step`、运行记录存储 `RunStore`（ADR 0008）与 Local-first 持久化（ADR 0009，默认 SQLite 落盘）。至此，每一次 Agent 运行的完整轨迹都已可靠沉淀为可读数据。

下一阶段需要建立 **Evaluation Loop**：让 Agent 的执行结果可以被**持续评价**，进而支撑后续优化。本 ADR 只设计**长期可扩展架构**，不立即实现复杂业务（对应 Knowledge First 与「架构正确性 > 开发速度」）。

约束（AGENTS.md / 协作协议）：
- Evaluation 是新模块，属架构变更，先 ADR 后实现（本 ADR）。
- 模块独立 + 调用链铁律：Evaluation 不得直接访问数据库、不得直接调用模型、不得侵入 Agent Runtime。

## 待决问题（评审重点）

1. **定位**：Evaluation 是「测试框架」还是「Agent Runtime 的反馈闭环」？二者在数据来源、运行时机、产出形态上完全不同。
2. **分层**：单一评估器能否同时承载「运行是否健康」「输出好不好」「投资对不对」三类语义差异巨大的评价？如何分层以避免早期过度设计又预留长期演进？
3. **核心抽象**：用什么最小契约表达「一次评估的结果」「一个评估器」「一项指标」，才能既服务 Layer 1 又向 Layer 2/3 平滑扩展？
4. **数据边界**：Evaluation 如何拿到被评数据，才能既满足需求又不破坏模块边界（不直连 DB、不碰 Runtime 内部）？
5. **依赖方向**：新模块 `services/evaluation` 应依赖谁、禁止依赖谁？

## 决定（建议方案，待确认）

### 1. 定位：反馈闭环，而非测试框架

- **不是传统测试框架**：测试针对代码正确性、在 CI 中对固定断言判定通过/失败、面向开发者。
- **是 Agent Runtime 的反馈闭环**：Evaluation 面向**运行产物**（`RunResult` 轨迹），产出可度量、可累积、可对比的评价数据，服务于「持续观察 Agent 表现 → 发现退化/改进 → 指导后续优化」的闭环；它消费的是历史运行，而非临时构造的用例。

```
Agent 运行 → RunResult → RunStore（落盘）
                              │  只读
                              ▼
                        Evaluation Loop → EvaluationResult（指标）→ 复盘/优化
```

### 2. 三层 Evaluation 模型（分层演进，当前只落地 Layer 1）

| 层级 | 名称 | 评价对象 | 本阶段 |
|------|------|----------|--------|
| Layer 1 | Runtime Evaluation | 运行**过程**是否健康 | **现在实现** |
| Layer 2 | Output Evaluation | 输出**质量**好不好 | 预留接口，不实现 |
| Layer 3 | Investment Evaluation | 投资**决策**对不对 | 远期预留，仅占位 |

- **Layer 1 — Runtime Evaluation（本阶段）**：完全基于已有结构化字段，确定性、零外部依赖。
  - Run 是否成功（`RunResult.status` / `.ok`）。
  - Step 数量（`len(steps)`，及 think/act/observe 分布）。
  - Tool 调用情况（调用次数、去重工具集、是否出现未授权/失败工具）。
  - Error 分类（从 `RunResult.error` 的 `类型: 消息` 形态归类，如 PermissionError / 超时 / 其他）。
- **Layer 2 — Output Evaluation（预留）**：评价输出的质量 / 完整性 / 准确性 / 一致性。其中部分维度未来可能需要「模型在环」打分——届时**仍不得由 Evaluation 直连模型**，而是经 Tool（如 `llm_judge` 工具）或经一个独立的「评审 Agent」产出，Evaluation 只消费其结构化结果。本阶段仅定义占位，不实现。
- **Layer 3 — Investment Evaluation（远期）**：策略结果验证 / 投资决策复盘 / 历史经验积累，对应数据流末端「策略 → 执行」的回流。当前仅在抽象上预留，不设计细节。

### 3. 核心抽象（最小契约，跨三层通用）

> 仅定义形态，本 ADR 不含实现代码。

- **`Metric`（指标模型）**：一项可度量的原子结果。
  - 字段（建议）：`name`（如 `run_success` / `step_count` / `tool_call_count`）、`value`（数值或布尔/枚举的归一表示）、`unit`（可选）、`layer`（Layer 1/2/3）。
- **`EvaluationResult`（评估结果）**：对**某一被评对象**的一次评估产出。
  - 字段（建议）：`target_run_id`（被评 `RunRecord` 的 id；批量评估则为聚合标识）、`evaluator`（产出者名）、`metrics: list[Metric]`、`passed: bool | None`（可选总判定，闭环语义下允许「只度量不判定」）、`detail`（结构化补充）、`created_at`。
- **`Evaluator`（评估器接口）**：抽象基类，单一方法 `evaluate(target) -> EvaluationResult`。
  - `target` 为 `RunRecord`（或其列表），**由调用方从 `RunStore` 取出后传入**；Evaluator 自身不持有数据源。
  - Layer 1 提供具体实现 `RuntimeEvaluator`；Layer 2/3 仅以子类占位，便于后续扩展且不改动接口。

这三者构成跨层稳定契约：新增评价维度 = 新增 `Metric` 名称 / 新增 `Evaluator` 实现，**不改既有接口**。

### 4. 边界（强制）

- **数据来源唯一**：Evaluation 只能通过 `RunStore`（`get_run` / `list_runs`）获取被评数据。
- **禁止**：直接访问数据库（不依赖 psycopg / sqlite3 等驱动）、直接调用模型（不依赖 ModelRouter/Provider）、侵入或修改 Agent Runtime（不 import runner/agent 内部、不改其行为）。
- **依赖方向（单向）**：`evaluation → agent-runtime`（仅消费 `RunStore` 抽象与 `RunResult` / `Step` / `AgentStatus` 等只读类型）。`agent-runtime` 不反向依赖 `evaluation`；`evaluation` 不依赖 `persistence` 的具体实现（只认抽象 `RunStore`，由装配层注入 `default_run_store()` 的产物）。

### 5. 运行形态

- 本阶段为**离线/按需**评估：传入一个或一批 `RunRecord` → 产出 `EvaluationResult`。不引入常驻服务、不引入队列。
- 评估结果的持久化：本阶段先返回内存对象（供调用方打印/断言/聚合）；是否落库（复用 `RunStore` 思路新增 `EvaluationStore`）留待 Layer 2 接入、数据量增长时**另开 ADR**，不在本阶段决定。

## 原因

- 「反馈闭环」定位让 Evaluation 直接服务于 Knowledge First——把「运行表现」沉淀为可累积、可对比的度量，而非一次性测试断言。
- 三层模型用**分层**隔离语义差异巨大的三类评价：当前只实现确定性的 Layer 1（零外部依赖、可在 local-first 内闭环），Layer 2/3 以接口预留，避免过早设计又不堵死演进，契合「架构正确性 > 长期扩展性 > 开发速度」。
- `Metric` / `EvaluationResult` / `Evaluator` 三件套是评估领域的通用最小抽象，跨三层复用，新增维度不破坏契约。
- 「只经 RunStore 取数 + 单向依赖」从结构上保证模块独立与调用链铁律，与 ADR 0008/0009 的存储抽象天然衔接（Evaluator 后端无关：SQLite 或 Postgres 都一样读）。

## 影响

- 新增模块职责落到既有占位包 `services/evaluation`（当前仅 `__init__` 占位）：实现 `EvaluationResult` / `Metric` / `Evaluator` / `RuntimeEvaluator`（Layer 1），Layer 2/3 占位。
- 依赖：`services/evaluation` 新增对 `shanhai-agent-runtime` 的依赖（只读抽象与类型）；不引入任何 DB / 模型依赖。
- 对 `agent-runtime` / `persistence` / `wiki-engine` **零改动**；不改变 Agent 编写方式与运行行为。
- `PROJECT_STATE.md` 下一步第②项推进；后续测试基于 `InMemoryRunStore`/`SqliteRunStore` 造数据驱动 `RuntimeEvaluator`，无需外部环境。
- 文档：CHANGELOG / docs 索引在**实现阶段**同步更新（本 ADR 阶段不写代码）。

## 备选方案（已考虑）

- **把 Evaluation 做成 pytest 风格测试框架**：与「反馈闭环」定位冲突——测试面向固定断言与代码正确性，无法承载「持续度量、累积对比运行表现」，不采纳。
- **单层通用 Evaluator（不分层）**：实现最省，但 Runtime / Output / Investment 三类评价在数据来源与判定方式上差异巨大，强行合一会导致接口臃肿且难演进，不采纳；改以分层 + 统一三件套契约。
- **Evaluation 直接读 DB 或直接调模型打分**：能少绕一层，但破坏「只经 RunStore 取数、不直连 DB、不直连模型」的铁律与模块独立，坚决不采纳；模型在环的质量评估改由 Tool / 评审 Agent 产出、Evaluation 只消费结果。
- **本阶段即落地 EvaluationStore 持久化评估结果**：超出当前需要（Layer 1 结果可即时消费），过早引入存储设计，留待 Layer 2 另开 ADR。
