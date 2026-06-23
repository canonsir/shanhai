# ShanHai Project State

> 项目实时状态快照。供 AI（ChatGPT / Claude / GPT / Codex / Trae）与协作者快速对齐进度。
> 每完成一个阶段或重要模块时更新本文件。Git 是唯一事实来源。

## 版本

v0.1.0

## 当前阶段

Phase 1 — Agent Runtime（进行中）

## 最新提交

- 分支：`develop`（个人项目：直接在 develop 开发，完成后 merge 到 main）
- 仓库：https://github.com/canonsir/shanhai

## 已完成

- [x] Phase 0 — Harness Foundation 全量（Monorepo / Model Router V0.1 / Tool Registry / Workflow 骨架 / Wiki Schema / DB 环境 / FastAPI / 冒烟测试 / ADR 0001-0005）
- [x] Agent Runtime 执行模型：think → act → observe（ADR 0006）
- [x] 生命周期 `AgentStatus` + 结构化运行记录 `Step` / `RunResult`
- [x] `AgentContext` 收口模型/工具访问；`AgentRunner` 编排
- [x] `BaseAgent` 钩子化 + `ToolEchoAgent` 示例（保留向后兼容）
- [x] 多步推理 Agent：`AgentRunner` 多轮 think/act/observe 循环 + `max_steps` 调度；`AgentContext` 增加 `iteration`/`observations`；`MultiStepToolAgent` 示例
- [x] Wiki 信息提取（ADR 0007）：规则驱动 `Extractor`（model-agnostic）+ `WikiExtractTool` + `WikiExtractionAgent`（模型在环，Agent→Tool→Service）
- [x] 运行记录持久化（ADR 0008）：`RunStore` 抽象 + `InMemoryRunStore` + `AgentRunner` best-effort 落库；新增 `services/persistence`（`PostgresRunStore`）
- [x] Local-first 持久化（ADR 0009）：`SqliteRunStore`（标准库 sqlite3，零依赖、可落盘）+ `default_run_store()` 装配工厂（默认 sqlite）；数据库降为增强能力，非开发前置
- [x] Evaluation Loop Layer 1（ADR 0010）：`services/evaluation` 落地 `Metric` / `EvaluationResult` / `Evaluator` / `RuntimeEvaluator`（success / step_count / tool_usage_count / error_type），只经 `RunStore`/`RunResult` 取数，Layer 2/3 预留
- [x] 真实 Model Provider（ADR 0011）：`DeepSeekProvider` 适配器（实现 `ModelProvider` 接口、可注入 transport、默认 urllib 零新依赖）；`.env.example` + 机密走环境变量；`MockProvider` 仍为默认，无 Key 可跑全部测试
- [x] Agent Runtime 单元测试（通过）

## 当前目标

完善 AI Harness 基础设施（Agent Runtime / Workflow / Tool / Memory / Evaluation），保证模块边界与架构正确性。

## 进行中

- [ ] 架构 Review（等待评审反馈）

## 下一步（已确定路线）

1. [x] 固化 Local-first 持久化（ADR 0009，已完成）
2. [~] 建立 Evaluation Loop（ADR 0010 已采纳；**Layer 1 Runtime Evaluation 已实现**：`Metric` / `EvaluationResult` / `Evaluator` / `RuntimeEvaluator`，指标 success / step_count / tool_usage_count / error_type，只经 `RunStore`/`RunResult` 取数。Layer 2/3 预留）
3. [~] 再接真实 Model Provider（ADR 0011 已采纳；**DeepSeekProvider MVP 已实现**：实现同一 `ModelProvider` 接口、按名注册、可注入 transport（默认 urllib，零新依赖），Fake Transport 单测无需真实 Key；机密走 `SHANHAI_DEEPSEEK_API_KEY`，`MockProvider` 仍为默认。Anthropic/GPT/Qwen、streaming、Router 编排 retry/fallback 待后续）
4. [ ] Agent Harness 完善 — Agent Memory（ADR 0012 已采纳，**仅设计**）：Memory 与 Knowledge Engine 正交分层；三层模型 Runtime / Knowledge / Experience Memory；`MemoryStore` 抽象（沿用 RunStore 范式）；Agent 经 `MemoryTool → MemoryService` 访问，不直连 DB/存储。实现待 Review 批准后另启
5. [ ] Agent Harness 完善 — Evaluation Feedback（ADR 0013 已采纳，**仅设计**）：闭环 `Evaluation → Feedback → Experience Memory`；度量/归因/沉淀三段分层；`ExperienceCandidate` 生成与去重/晋升规则；Feedback 独立组合层（依赖 evaluation+memory+agent-runtime，不破坏既有单向依赖）。实现依赖 ADR 0012 先落地，待 Review 批准后另启
6. [ ] Agent Harness 完善 — Experience Memory（ADR 0014 已采纳，**仅设计**；ADR 0012 的扩展，非替代）：Experience 层走 **Event Log Lite**——`ExperienceEvent`（append-only 不可变事件）+ `Episode`（情景投影）+ `SemanticExperience`（语义经验投影）；经 `refs` 引用 `run_id`/`evaluation_ref`/`entity_ids`（不复制度量与知识）；`outcome` 事件支撑 A 股延迟结果回填；`ExperienceStore` 沿用 RunStore 范式。**不引入 Vector DB / Graph DB / CQRS**。实现待 Review 批准后另启

> 方针：**数据库作为增强能力，不作为开发前置环境**。开发/测试/单机默认 local-first（SQLite），并发/规模/共享场景再切 `SHANHAI_RUN_STORE=postgres`。

### 暂缓 / 候选

- Workflow 条件分支 / 并行（评估是否引入 LangGraph，用户已暂缓）
- Wiki Engine：模型驱动抽取（依赖真实 Provider 后扩展）
- 运行记录持久化：接入真实 Postgres 验证（待 Docker 环境，作为增强后端）

## 暂不开发（明确禁止本阶段实现）

- 实时行情系统
- 券商交易接口
- 自动交易 Agent
- 复杂量化策略 / 高频策略
- 回测系统

## 不变量（不允许破坏）

- Model Router 隔离：Agent 禁止直接绑定/调用模型
- Service 边界：Agent 不直接访问数据库，调用链 `Agent → Tool → Service → Database`
- 模块独立：harness-core / agent-runtime / model-router / wiki-engine / data-pipeline / persistence 边界清晰
- 任何架构调整先写 ADR（`docs/架构决策记录/`）
- Review Gate：「下一步建议」须经架构 Review 批准后方可执行（建议 ≠ 批准）

## 已知限制

- 本机无 Docker，`docker compose up` 未实地验证（compose/SQL 仅静态检查）
- 本机无 uv/pnpm，验证时用 Homebrew Python 3.14 venv 做 editable 安装
- gh 凭证因沙箱限制以明文存于工作区 `.gh-config/`（已 gitignore）
