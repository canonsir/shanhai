# ShanHai Project State

> 项目实时状态快照。供 AI（ChatGPT / Claude / GPT / Codex / Trae）与协作者快速对齐进度。
> 每完成一个阶段或重要模块时更新本文件。Git 是唯一事实来源。

## 版本

v0.2.0

## 当前阶段

Phase 1 — Agent Runtime（进行中）

```
Phase 1
 |
 +-- Experience Evolution Layer
       |
       +-- Stage 2-b Completed（package skeleton / lifecycle service / validator·promotion contracts / regression coverage）
```

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
- [x] Experience Event Infrastructure（ADR 0014 Stage 1）：`services/experience` 落地 `ExperienceEvent` / `ExperienceEventType` / `ExperienceRefs` + `ExperienceStore` 抽象 + `InMemoryExperienceStore`（append-only，支持 append / get / list-filter）。模块零业务依赖（仅 pydantic），结构上保证「引用而非复制」（经 refs 关联 run_id/evaluation/entity，不复制 RunStore 内容）；Episode/Semantic/Vector/Graph/DB/LLM 不在本 Stage
- [x] Memory Runtime Access Layer（ADR 0012 Layer 1）：`services/memory` 落地 `MemoryScope`/`MemoryRecord`/`MemoryQuery` 契约 + 三 adapter（Runtime 进程内可读写 / Knowledge 只读委派 / Experience 只读委派）+ `MemoryService`（按 scope 路由，只读 scope 拒写）+ 单 `MemoryTool`（action 派发，Agent 唯一通道，受授权约束）。`wiki-engine` 新增最小只读 `KnowledgeService`（Entity 索引 + get/search，无向量）。不实现 vector/semantic/自动总结/持久 MemoryStore，不修改 ExperienceStore
- [x] Evaluation Feedback 闭环 — Stage 1（ADR 0013：FailurePattern → Candidate → Lesson）：`services/feedback` 落地 `ExperienceCandidate`/`CandidateKind` + `FeedbackRule` 抽象 + `FailurePatternRule`（确定性失败归因）+ `CandidateRegistry`（去重合并 + 阈值晋升）+ `FeedbackEngine`（规则→候选→去重→晋升→`ExperienceStore.append` 落 `type=lesson` 事件）。打通 `Run → RunStore → Evaluation → Feedback → ExperienceEvent(lesson)`，读侧反哺经现有 `MemoryTool`（EXPERIENCE 只读）。写经验经 `ExperienceStore.append`（service→service，决策①），不给 Memory 增 Experience 写能力；引用而非复制（lesson 只引用 run_id/evaluation_ref，不内嵌 metrics）。不实现 regression/effective_path、Episode/SemanticExperience 投影、模型在环、Vector/Graph/CQRS/新增 DB
- [x] Experience Outcome 回填基座 — Stage 2-a（ADR 0015：decision → outcome → lesson 事实链）：新增 `services/experience/.../ingest`——`resolve_episode_id`（回退收口）+ `ExperienceRecorder`（`RunRecord → decision`，可选 `observation`，从 RunStore 取稳定 run_id，不改 AgentRunner）+ `OutcomeIngestor.ingest(decision_event_id, outcome, occurred_at)`（外部结果 → `type=outcome` 事件，经 `parent_event_id` 挂回 decision，append-only 不回改、occurred_at/recorded_at 分离）；`ExperienceStore.list` 增 `episode_id`/`parent_event_id` 过滤（仅扩展查询，不改 schema/append 契约）；`feedback/engine.py` 改用 `resolve_episode_id`。episode 跨 run（`episode_id != run_id`，一 episode 串多 run）。不变量保持：Agent 不直接写 Experience、agent-runtime 不依赖 experience，生产者均 service→service（新增单向 `experience → agent-runtime` 只读 RunRecord）。Stage 2-a 不接真实数据源（调用方注入结构化结果）；不做 Semantic/Episode 物化投影/Vector/Graph/CQRS/EventBus/EvaluationStore/Memory 持久化/LLM 自动归因
- [x] Experience Evolution Layer — Stage 2-b（ADR 0016/0017：Candidate 生命周期 + 来源解耦）：新增 `services/experience-evolution`（独立包，仅依赖 pydantic）——**package skeleton**（`models.py` 枚举 + 值对象 + `ValidationVerdict` 跨模块契约、`candidate.py` `ExperienceCandidate` 结构化假设实体 + `ALLOWED_TRANSITIONS` 带 Actor 权限状态机、`repository.py` `CandidateRepository` 抽象 + `InMemoryCandidateRepository`）+ **lifecycle service**（`service.py` `CandidateService`，公共面恰为 create/transition/apply_validation/get/list，状态变更唯一通道、非 Orchestrator；`proposals.py` `CandidateProposal` 纯 input contract；`producers.py` `CandidateProducer` Protocol）+ **validator/promotion contracts**（`validator.py` `Validator.validate(candidate, context)→ValidationVerdict` + 只读 Reader Protocol + Noop；`promotion.py` `PromotionGate.evaluate(candidate)→PromotionDecision`，字段锁定 approved/reason/candidate_id/validation_snapshot_ref + Noop）+ **regression coverage**（`tests/test_candidate_lifecycle.py` 5 边界用例 + 依赖方向 AST 校验）。`services/feedback` 仅新增 `FeedbackProposalAdapter`（feedback candidate → CandidateProposal，旁路喂入，不绕过 Service），Stage 0 `CandidateRegistry` 主链路不动。不变量保持：`experience-evolution` 不 import `feedback`、`experience` 不 import `experience-evolution`、`feedback → experience-evolution` 单向（AST 校验）；不改 `ExperienceEvent` schema / `ExperienceStore.append` 契约。明确延期：Validator/PromotionGate 策略实现、Candidate 持久化（DB/Vector/Graph）、Evolution Workflow 编排、ExperienceArtifact、Knowledge Projection、Stage 3 Registry/Store 迁移
- [x] Runtime Kernel — v0.7 Phase 1 / PR-1 Skeleton（纯结构骨架，建立 ownership boundary，零行为变更，✅ Closed）：新增 `services/runtime-kernel`（orchestrator，非 executor，仅依赖 pydantic）——`lifecycle.py`（`RuntimeState` 不可逆状态机 `CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED` + `can_transition`/`assert_transition`，非法迁移如 `RUNNING→READY` 抛错）、`context.py`（`RuntimeContext` 不可变容器 = 7 个 `*_context` + `schema_version="1.0"`，run_id 仅在 identity_context，不持执行能力 / R7 Context Ownership Drift 治理）、`events.py`（`RuntimeEvent` identity envelope + `RuntimeEventType`，payload 透传不新造 schema）、`kernel.py`（`RuntimeKernel` 4 方法 `create/assemble/execute/close` 占位 `NotImplementedError`，禁实例化 AgentRunner/RunStore/ExperienceCandidateProvider）、`types.py`（`RuntimeHandle`）。Contract Test Layer（`tests/runtime_kernel/` 4 文件：context immutability/schema_version/run_id 单点/R7 字段冻结 + lifecycle 合法链/非法迁移 + event envelope + AST 依赖边界）；依赖方向 `runtime-kernel → agent-runtime public interface`（调用非包含），不依赖 experience-artifact / agent-runtime internals。PR-1 范围外（明确禁止）：no AgentRunner integration / no RunStore change / no Experience Runtime / no Memory / no Domain Provider / no ArtifactReader。
- [x] Runtime Kernel — PR-2 RuntimeContext v1 Contract Implementation（纯契约实现，零执行集成，✅ Closed）：`RuntimeContext` 冻结为 Execution Initialization Snapshot；`metadata_context → intent_context`；七个 context v1 schema 固定为 identity/task/intent/experience/policy/constraint/environment；所有 context model 使用 `frozen=True + extra="forbid"`，集合字段使用 tuple，`schema_version` 固定为 `Literal["1.0"]`；`experience_context` 只承载 `SelectedExperienceRef` 与选择理由/分数，不承载 Artifact dump / Memory / embedding。新增/强化 contract tests（deep immutable、unknown/execution/storage 字段拒绝、schema evolution v1.0 forbid、字段级 contract table）。未触碰 `kernel.py` / `events.py` / `lifecycle.py` / AgentRunner / RunStore / Experience Runtime / Memory / ArtifactReader / E2E。
- [x] Runtime Kernel — PR-3 RunStore Identity Migration（identity ownership migration only，✅ Implementation Completed，✅ Closure Review Completed）：`RunStore.save_run` contract 扩展为 `save_run(run, run_id: str | None = None) -> str`；external `run_id` 为 Runtime-owned identity 主路径，`run_id=None` 仅作为 migration window fallback 并发出 `DeprecationWarning`；`InMemoryRunStore` / `SqliteRunStore` / `PostgresRunStore` 同步签名，不暴露 `generate_run_id()`；新增 run identity / trace identity contract tests，验证 `RuntimeContext.run_id = RuntimeEvent.run_id = RunRecord.run_id`。Closure Review 见 `docs/design/runstore-identity-migration-closure-review.md`：确认满足冻结约束、migration window 处于 Phase 1、无 forbidden boundary violation。未触碰 RuntimeKernel execution path / `kernel.py` / `events.py` / `lifecycle.py` / RuntimeContext contract / AgentRunner / Experience Runtime / Memory / Artifact Layer / Evaluation / E2E。**完成后停在 PR-4 Experience Runtime Review Gate。**
- [x] Agent Runtime 单元测试（通过）

## 当前目标

完善 AI Harness 基础设施（Agent Runtime / Workflow / Tool / Memory / Evaluation），保证模块边界与架构正确性。

## 进行中

- [ ] PR-4 Experience Runtime Review Gate：PR-3 RunStore Identity Migration Implementation + Closure Review 已完成；`docs/design/experience-runtime-review-v0.1.md` 已补充 ExperienceSelection contract、Selector/Evolution boundary（Selector 不学习，Evolution 学习）、Projection allowed/forbidden、dependency DAG、MVP scope 与 PR-4.1~PR-4.5 分阶段路线；**当前不写 PR-4 实现、不接 Experience Runtime / Memory / ArtifactReader / E2E**。

## 下一步（已确定路线）

1. [x] 固化 Local-first 持久化（ADR 0009，已完成）
2. [~] 建立 Evaluation Loop（ADR 0010 已采纳；**Layer 1 Runtime Evaluation 已实现**：`Metric` / `EvaluationResult` / `Evaluator` / `RuntimeEvaluator`，指标 success / step_count / tool_usage_count / error_type，只经 `RunStore`/`RunResult` 取数。Layer 2/3 预留）
3. [~] 再接真实 Model Provider（ADR 0011 已采纳；**DeepSeekProvider MVP 已实现**：实现同一 `ModelProvider` 接口、按名注册、可注入 transport（默认 urllib，零新依赖），Fake Transport 单测无需真实 Key；机密走 `SHANHAI_DEEPSEEK_API_KEY`，`MockProvider` 仍为默认。Anthropic/GPT/Qwen、streaming、Router 编排 retry/fallback 待后续）
4. [~] Agent Harness 完善 — Agent Memory（ADR 0012 已采纳）：Memory 与 Knowledge Engine 正交分层；三层模型 Runtime / Knowledge / Experience Memory；Agent 经 `MemoryTool → MemoryService` 访问，不直连 DB/存储。**Layer 1 Runtime Access Layer 已实现**（`services/memory`：MemoryScope/MemoryRecord/MemoryQuery 契约 + Runtime/Knowledge/Experience 三 adapter + MemoryService 按 scope 路由（只读 scope 拒写）+ 单 MemoryTool action 派发，唯一通道；wiki-engine 新增最小只读 KnowledgeService）。持久 `MemoryStore`（Storage 层）、vector/semantic/自动总结待后续，须经 Review 批准
5. [~] Agent Harness 完善 — Evaluation Feedback（ADR 0013 已采纳；**Stage 1 已实现**）：闭环 `Run → Evaluation → Feedback → ExperienceEvent(lesson)`；度量/归因/沉淀三段分层；`services/feedback` 落地 `ExperienceCandidate` + `FailurePatternRule` + `CandidateRegistry`（去重/阈值晋升）+ `FeedbackEngine`（晋升落 `type=lesson` 事件）。写经验经 `ExperienceStore.append`（service→service，决策①），Feedback 不依赖 memory；读侧反哺经现有 `MemoryTool`（EXPERIENCE 只读）。Stage 2（regression/effective_path 规则、SemanticExperience 投影、模型在环归因）待后续，须经 Review 批准
6. [~] Agent Harness 完善 — Experience Memory（ADR 0014 已采纳；ADR 0012 的扩展，非替代）：Experience 层走 **Event Log Lite**——`ExperienceEvent`（append-only 不可变事件）+ `Episode`（情景投影）+ `SemanticExperience`（语义经验投影）；经 `refs` 引用 `run_id`/`evaluation_ref`/`entity_ids`（不复制度量与知识）；`outcome` 事件支撑 A 股延迟结果回填；`ExperienceStore` 沿用 RunStore 范式。**不引入 Vector DB / Graph DB / CQRS**。**Stage 1 Experience Event Infrastructure 已实现**（`services/experience`：Event/EventType/Refs + ExperienceStore/InMemoryExperienceStore，append/get/list-filter）。**Stage 2-a Outcome 回填基座已实现**（ADR 0015 已采纳，作为 ADR 0014 Stage 2-a 实现决策）：`services/experience/.../ingest`（`resolve_episode_id` + `ExperienceRecorder` decision/observation + `OutcomeIngestor` outcome 延迟回填，`parent_event_id` 挂回 + occurred_at/recorded_at 分离）+ `ExperienceStore.list` 增 `episode_id`/`parent_event_id` 过滤；episode 跨 run（`episode_id != run_id`）。打通可验证事实链 `decision → outcome → lesson`。**Stage 2-b Candidate 生命周期已实现**（ADR 0017 Accepted，独立 `services/experience-evolution`：CandidateService 生命周期入口 + CandidateRepository + Validator/PromotionGate 接口契约 + FeedbackProposalAdapter）。Stage 3（SemanticExperience / Episode 物化投影 / 真实数据源接入 / 延迟回填编排自动化 / CandidateRegistry·Store 迁入新层）待后续，须经 Review 批准

> TODO（已登记，延后执行）：**ADR 0012 implementation alignment update** —— 待 Memory / Experience persistence 阶段统一回填（避免一次修改多个基础 ADR）。

> 架构演进边界（ADR 0015 Decision F + ADR 0016 Proposed + ADR 0017 Accepted）：Experience 四层语义 `ExperienceEvent（事实，已实现）→ ExperienceCandidate（待验证假设，evolution Stage 2-b 已实现生命周期）→ ExperienceArtifact（已验证可复用能力，延期）→ Knowledge Document（外部知识，另域）`；`ExperienceEvent ≠ 最终经验资产`、`lesson` 仅为事件层反馈、`ExperienceArtifact ≠ Knowledge Document`。Artifact 须为「能力单元」（identity/capability/context/evidence/applicability/evaluation/lineage/evolution history），非 title/content/embedding。WeKnora / llm-wiki 属 Artifact 下游 **Knowledge Projection Layer**（非 Experience 存储），与 Experience 解耦。Candidate 来源多元化（Feedback / Outcome / Discovery / Human），Stage 2-b 已起独立 `services/experience-evolution`（CandidateService 生命周期入口 + Validator/PromotionGate 接口契约），feedback 经 `FeedbackProposalAdapter` 降为 Producer；Stage 3 再迁 `CandidateRegistry/Store`。完整模型见 **ADR 0016（Proposed）/ ADR 0017（Accepted）**。
> 经验层阶段路线（逐阶段经 Review）：`Stage 2-a 事实链（已完成）→ Stage 2-b Candidate 生命周期 + 来源解耦（已完成）→ Stage 3 ExperienceArtifact → Stage 4 Knowledge Projection（接 WeKnora/llm-wiki）→ Stage 5 Experience Evolution（EvoMap：mutation/evaluation/promotion）`。在 `ExperienceArtifact` 模型确定前暂缓：Vector Search / Graph Experience / WeKnora 接入 / llm-wiki 同步 / 自动 Experience Summary。
> 跨阶段冻结不变量：ExperienceEvent append-only、outcome 不修改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Knowledge Projection 与 Experience 解耦。

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
- 模块独立：harness-core / agent-runtime / runtime-kernel / model-router / wiki-engine / data-pipeline / evaluation / experience / experience-evolution / experience-artifact / memory / feedback / persistence 边界清晰
- 任何架构调整先写 ADR（`docs/架构决策记录/`）
- Review Gate：「下一步建议」须经架构 Review 批准后方可执行（建议 ≠ 批准）

## 已知限制

- 本机无 Docker，`docker compose up` 未实地验证（compose/SQL 仅静态检查）
- 本机无 uv/pnpm，验证时用 Homebrew Python 3.14 venv 做 editable 安装
- gh 凭证因沙箱限制以明文存于工作区 `.gh-config/`（已 gitignore）
