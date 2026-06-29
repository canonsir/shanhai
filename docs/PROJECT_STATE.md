# ShanHai Project State

> 项目实时状态快照。供 AI（ChatGPT / Claude / GPT / Codex / Trae）与协作者快速对齐进度。
> 每完成一个阶段或重要模块时更新本文件。Git 是唯一事实来源。

## 版本

v0.2.0

## 当前阶段

Milestone 3 — Market Intelligence Platform Alpha（🚧 进行中 / M3.1 Console Alpha ✅ Completed，M3.2 Data Acquisition Foundation ✅ Spike 闭环跑通，Next: M3.3 Knowledge Provenance Foundation）

> 切换点：M2.5 Phase 2 Market Knowledge Foundation 已实现并提交（checkpoint `de296c0`），ShanHai 第一次具备真实 A 股公司知识（实体身份 + MarketFact v1 + 财务/公告事实 + 公司知识时间线）。据此**结束 Foundation / Runtime 抽象阶段**：不再推进 PR-4.2 Candidate Provider，不再深挖 Runtime 契约，正式进入由真实数据驱动的 Market Intelligence Platform 建设。
> **M3.1 转折点（checkpoint `1087e7e`）**：Company Intelligence Console Alpha 已实现并经真实数据驱动的浏览器端到端验证关闭。这是项目最重要的转折点——从「设计 AI 系统」进入「构建一个真正理解中国资本市场的长期知识系统」。Console 让真实世界的数据模型被人观察、验证（先验证现实承载力，再决定抽象层如何演化），优先级高于回头继续 Experience Runtime 抽象。
> **M3.2 路线 pivot（Data Acquisition Foundation）**：原 M3.2 = Knowledge Provenance Foundation 被重排。校准后的认知节点是「M2.5 解决知识如何表达 → M3.1 证明知识模型能被消费 → M3.2 决定知识从哪里来并且能否可信」。因此先做 **Data Acquisition Foundation**（真实免费数据进入系统 + 最小内置 provenance），把完整 Knowledge Provenance / Raw Snapshot Storage 下移到 M3.3。原则：**先让现实撞模型，再让模型指导抽象**（实现优先，不提前抽象、不提交 Design Gate）。Provider 一律 source-neutral（`PublicMarketDataProvider`，providers 平级），不绑定任何单一平台；AkShare 不作为核心依赖（它是采集聚合 SDK，不是数据源）。
> **流程收敛**：不再使用 PR-4.x 命名与多文档 review gate 循环；未来统一为 `Milestone → Feature → Implementation → Review → Merge`。一个 feature 配一个实现 + 一份 review 文档。
> **数据供应商**：免费公开数据（东方财富 push2/F10、巨潮资讯 cninfo）+ 本地计算 adapter；Tushare 降级为 commercial optional（保留不删，需 token）。未来经 Market Data Hub + Adapter Layer 融合多源（新浪 / 腾讯 / 交易所 / 财联社 / Wind / JoinQuant）。

```
Foundation Phase ✅ Completed（Runtime / Experience 契约抽象阶段已收尾，不再扩展）
 |
 +-- PR-1 Runtime Kernel Skeleton ✅ Closed
 +-- PR-2 RuntimeContext v1 ✅ Closed
 +-- PR-3 RunStore Identity Migration ✅ Closed
 +-- PR-4.1 Experience Runtime Contract Layer 🧊 Frozen / Reason: Waiting for real market knowledge validation
 +-- PR-4.2 Candidate Provider Adapter ❌ Not pursued（被 Milestone 3 取代；不再按 PR-4.x 推进）

Milestone 2
 |
 +-- Data Foundation MVP ✅ Implementation Completed
 +-- market-data service / Tushare Provider / Entity Schema MVP / Knowledge Store / Company Intelligence API
 +-- Market Data Runtime MVP ✅ Scheduled ingestion / PostgreSQL Store / Resolver / API / Console
 +-- Market Knowledge Expansion ⏳ Design only（M2.3，蓝本已被 Phase 2 实现采用）
 +-- Market Foundation Hardening
      +-- Phase 0 Closure ✅ Design Review Completed
      +-- Phase 1 Entity Hardening ✅ Closure PASS（带 2 项归属 Phase 3 的登记风险）
      +-- Phase 2 Market Knowledge Foundation ✅ Implementation Completed / Review PASS（checkpoint de296c0）
      +-- Phase 3 Storage Refactor ⏳ Deferred（并入 Milestone 3 M3.3 Knowledge Provenance Foundation：Postgres identity tables / R1+R2 / cache-shadowing）

Milestone 3 — Market Intelligence Platform Alpha 🚧
 |
 +-- M3.1 Company Intelligence Console Alpha ✅ Completed（checkpoint `1087e7e`；真实数据驱动浏览器端到端验证：知识模型可被人观察验证，页面不是展示数据而是验证模型）
 +-- M3.2 Data Acquisition Foundation ✅ Spike 闭环跑通（真实免费数据 spike：东方财富 + 巨潮资讯经 source-neutral PublicMarketDataProvider 流入 600519.SH，带最小内置 SourceRef provenance；Console 端到端验收。"闭环跑通则 M3.2 正式开始"门槛已达成）
 +-- M3.3 Knowledge Provenance Foundation ⏳ Planned / Next（不可变 raw data provenance：External Data → Raw Snapshot → Normalized Entity → Knowledge Fact；raw storage engine / data lake / object storage / parquet warehouse；含 Phase 3 Storage Refactor：Postgres identity tables / R1+R2 / cache-shadowing）
 +-- M3.x Semantic Vocabulary Enhancement ⏳ Planned（Knowledge Vocabulary Layer：predicate → display_name → description；doc-only 登记，不改 MarketFact）
 +-- M3.4 Web Platform ⏳ Not started（Bun + Next.js + React + Tailwind + Rspack；apps/{api,console,worker}；定位 Bloomberg 公司百科 + AI Research Notebook）
 |
 +-- Runtime / Memory / Evolution / Trading ⛔ Not in scope
```

依赖顺序：`Market Data → Market Knowledge → Console（模型验证）→ Data Acquisition（真实数据进入 + 最小 provenance）→ Knowledge Provenance（raw snapshot → normalization → knowledge）→ Web Platform`。真实 Candidate / Experience Runtime 推迟到平台积累真实市场知识后再反向验证（路线：`Foundation → Market Data → Knowledge Model → Console Validation → 真实研究流程 → Candidate Provider → Experience Runtime`）。

## 最新提交

- 分支：`develop`（个人项目：直接在 develop 开发，完成后 merge 到 main）
- 仓库：https://github.com/canonsir/shanhai
- **历史 checkpoint `de296c0`**：`feat(market-data): complete M2.5 phase2 market knowledge foundation` —— ShanHai 第一个真正产品形态节点（真实 A 股公司知识进入系统）。后续 Milestone 3 围绕此节点展开。
- **M3.1 checkpoint `1087e7e`**：`feat(console): company intelligence console alpha` —— `apps/console`（Bun + Next.js 16 + React 19 + Tailwind v4）只读消费现有 Market Data API，六分区 Company Detail（Identity / Facts / Financial / Announcement / Timeline / Sources）。经真实数据驱动（离线 fixture seed 3 家公司）浏览器端到端验证：搜索 / 过滤 / 六区块渲染 / Timeline 基准+方向切换 / 404 优雅。验证中修复 `company-timeline.tsx` unhandledRejection（timeline 接口失败无 catch）。验证结论：Entity Model（Company → ListedEntity → Security → Listing）可被产品入口自然承载，M2.5 方向正确。

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
- [x] Experience Runtime — PR-4.1 Contract Layer（纯契约层，✅ Implementation Completed，✅ Closure Review Completed）：新增 `services/experience-runtime`，只包含 `ExperienceCandidateProvider` / `ExperienceSelector` / `ExperienceProjection` Protocol interfaces 与 `ExperienceQuery` / `ExperienceCandidateView` / `ExperienceSelection` / `ExperienceProjectionResult` 类型契约；`ExperienceSelection` 仅允许 candidate_id / artifact_ref / relevance_score / selection_reason；Projection 只输出 ArtifactRef / Metadata / Summary / DecisionHint 形态；新增 `tests/experience_runtime/` contract + dependency boundary tests。Closure Review 见 `docs/design/experience-runtime-contract-closure-review-pr4.1.md`：确认 contract completeness / schema stability / dependency boundary / frozen constraints consistency 均通过。未触碰 RuntimeContext execution flow / RuntimeKernel / AgentRunner / ArtifactReader / Memory / Evaluation / Evolution / E2E。**完成后停在 PR-4.2 Candidate Provider Adapter Review Gate。**
- [x] Foundation Phase Closure（Runtime / Experience Contract Foundation，✅ Completed）：PR-1 Runtime Kernel、PR-2 RuntimeContext v1、PR-3 RunStore Identity Migration、PR-4.1 Experience Runtime Contract Layer 均完成 implementation + closure；PR-4.2 仅完成 Candidate Provider Adapter Design Gate，明确停止 implementation。Closure Review 见 `docs/design/foundation-phase-closure-review.md`。当前分支完成 Foundation 文档整理，下一阶段需重新进入 Review Gate 后再开工。
- [x] Milestone 2 — Data Foundation MVP Phase 1（真实 A 股数据闭环，✅ Implementation Completed）：新增 `services/market-data`，包含 `TushareProvider`（标准库 HTTP + fake transport 测试，token 走 `SHANHAI_TUSHARE_TOKEN`）、Market Entity Schema MVP（Company / ListedEntity / Security / Listing / Industry / QuoteSnapshot / MarketFact）、`AShareCompanySyncService`（默认贵州茅台/宁德时代等 10 家 A 股公司）、`InMemoryMarketKnowledgeStore`、`CompanyIntelligenceAPI`；新增 `tests/market_data/` 覆盖 Provider、10 公司同步、API、身份不塌缩、依赖边界与无交易 surface。未修改 RuntimeKernel / Experience Runtime / RuntimeContext，未实现 PR-4.2 Adapter / Memory Evolution / 交易策略。
- [x] Milestone 2.2 — Market Data Runtime MVP（每天自动获得真实 A 股数据，✅ Implementation Completed）：新增 `EntityResolver` v0.1、`PostgresMarketKnowledgeStore`（`SHANHAI_MARKET_PG_DSN` + lazy psycopg）、`TushareScheduledIngestion`（run_once + daily loop）、Company Intelligence API routes（`/companies` / `/companies/search` / `/companies/{ts_code}` / `/market/ingestion/tushare/run`）与 Company Console Alpha（`/console/companies`）。`.env.example` 仅新增 Tushare / market store 占位，真实 token 不入库。未修改 RuntimeKernel / Experience Runtime / RuntimeContext / AgentRunner / Memory，未做 Trading Strategy。
- [x] Milestone 2.3 — Market Knowledge Expansion Review（Design Gate，⏳ Design Only）：新增 `docs/design/market-knowledge-expansion-review-m2.3.md`，冻结 MarketFact schema v1 / FinancialFact / AnnouncementFact / NewsFact / Entity linking strategy / Timeline model；明确 M2.3 目标是从“知道公司存在”进入“理解公司发生了什么”。当前不写 M2.3 实现、不继续 Runtime 抽象、不实现 PR-4.2 Adapter、不做 Memory Evolution、不做 Trading Strategy。
- [x] Milestone 2.5 — Phase 1 Entity Hardening（Market Entity Identity 从 ts_code 解耦，✅ Implementation Completed，Closure PASS）：`identity.py` 新增 `new_internal_id(entity_type)` 代理键（不编码外部码），旧 `*_from_ts_code` 降级为迁移留痕；新增 `registry.py`（`IdentityRegistry` = `entity_identity_mapping`，确定性 `resolve_or_allocate` 外部码→代理键 + `link` 多源映射 + `record_legacy_migration` old→new 留痕 + 正/反双向索引可回滚，纯确定性无 AI/fuzzy/embedding）；`resolver.py` v0.1 改为经 registry 做确定性映射（同一 ts_code 复用同一代理键）；`models.py` 新增 `IdentityMapping` 模型 + `Company.external_ids`（外部码作为属性）；`store.py` 移除硬编码 `security:cn-a:{ts_code}` 反查，改 `ts_code → security_id` 索引；`mapper.py`/`sync.py` 共享一个 resolver，保证 bundle 与 quote 的 security_id 一致；测试删除“前缀不同即身份不同”假阳性，改验真实生命周期关系（`listed_entity.company_id == company.company_id` 等）+ 代理键不可由 ts_code 推导 + ts_code 仅为属性，新增 `tests/market_data/test_identity_registry.py`（确定性复用 / 多源映射 / old→new 迁移与回滚 / 冲突报错）。未触碰 RuntimeKernel / RuntimeContext / Experience Runtime；未实现 PR-4.2 / Memory Evolution / Trading；未重构 Postgres cache（属 Phase 3）。
- [x] Milestone 2.5 — Phase 2 Market Knowledge Foundation（让真实 A 股公司知识进入系统，✅ Implementation Completed / Review PASS）：按用户指令取消 design gate，改「实现优先 + 单一 review 文档」。`models.py` `MarketFact` 升级为认知单元 v1（`subject_ref`/`predicate`/`object_value`/`object_ref` + 三时间戳 occurred_at/published_at/captured_at + source_ref/evidence_refs/confidence/entity_links/attributes，`schema_version="market_fact.v1"`），新增独立 `FinancialFact`（period/metric/unit/yoy）与 `AnnouncementFact`（announcement_id/type/title/document_url/document_hash），新增 read model `CompanyTimelineEvent` + 值对象 `SubjectRef`/`FactAttribute`/`EntityLink` + 枚举 `FactType`/`TimeBasis`/`AnnouncementType`；新增 `fact_mapper.py`（profile/industry/quote → MarketFact；fina_indicator 一行拆每指标一条 FinancialFact；anns_d → AnnouncementFact 启发式分类）；新增 `timeline.py`（`build_company_timeline` 三类事实家族投影到一条有序时间线，read model 非超级表，三时间戳回退永不塌缩）；`tushare.py` 新增 `fina_indicator`/`anns_d`，`provider.py` 新增可选 `FinancialDataProvider`/`AnnouncementDataProvider` Protocol，`sync.py` 用 `getattr` 能力探测优雅降级，`store.py` 三类 fact 分桶 + `get_company_timeline`，`api.py` payload 增 facts/timeline；`apps/api/.../main.py` 新增 Console Alpha 数据模型验证页 `/company/{ts_code}` + `/companies/{ts_code}/timeline`；新增 `tests/market_data/test_market_knowledge_facts.py`（6 用例），market-data 全量 5 文件全绿。Review 见 `docs/design/market-foundation-hardening-phase2-implementation-review-m2.5.md`。边界：不修改 RuntimeKernel / Experience Runtime；不实现 Selector / Memory Evolution / Trading；不做 AI entity merge；不做 Postgres identity registry migration（R1/R2 归 Phase 3）。
- [x] Milestone 3 — M3.1 Company Intelligence Console Alpha（用真实产品入口验证 Market Foundation 能否承载公司认知，✅ Completed，checkpoint `1087e7e`）：新增 `apps/console`（Bun 1.3.14 + Next.js 16 App Router/Turbopack + React 19 + TypeScript + Tailwind v4 + shadcn 风格手写组件 + Radix + lucide-react）。只读消费现有 Market Data API（`/companies` / `/companies/search` / `/companies/{ts_code}` / `/companies/{ts_code}/timeline`），**未改任何 API 契约**。`company-search.tsx` 搜索+列表（含错误兜底），`company/[tsCode]/page.tsx` server component 六分区 Company Detail（Identity / Facts / Financial / Announcement / Timeline / Sources），`company-timeline.tsx` 支持 TimeBasis（published_at/occurred_at/captured_at）切换 + 最新/最早方向切换。验证方式：Tushare token 积分受限（四接口全 40203），改用离线 fixture seed 3 家公司（贵州茅台/宁德时代/比亚迪）灌入 `InMemoryMarketKnowledgeStore` 做真实 ingestion shape 验证，浏览器端到端跑通搜索/过滤/六区块/timeline 切换/404 优雅。验证中修复 `company-timeline.tsx` unhandledRejection（reload 只有 try/finally 无 catch，timeline 接口失败 rejection 无人接）。**验证结论**：Entity Model（Company → ListedEntity → Security → Listing）可被产品入口自然承载，六分区自然成立，M2.5 方向正确；UI 层比单元测试更早暴露模型表达问题。**验证发现（已登记不实现）**：① Facts 展示裸 `predicate`（如 `classified_in_industry`）人类研究员需脑补语义 → 登记 M3.x Semantic Vocabulary Enhancement；② Source provenance 需从 attribute 升级为独立 provenance 模型 → 登记 M3.2 Knowledge Provenance Foundation。边界：未修改 RuntimeKernel / RuntimeContext / Experience Runtime；未实现 Selector / Memory / Evolution / Trading；未删除后端遗留 HTML console（`apps/api` 的 `/company/{ts_code}` / `/console/companies` 作历史验证痕迹保留，待 console 稳定后单独 `cleanup(api)`）。
- [x] Milestone 3 — M3.2 Data Acquisition Foundation（真实免费数据进入系统 + 最小内置 provenance，✅ Spike 闭环跑通）：按路线 pivot「先让现实撞模型」做真实数据 Data Adapter Spike（实现优先、不提交 Design Gate）。`services/market-data` 新增 source-neutral 供给层：`provider.py` `PublicMarketDataProvider` Protocol（`fetch_company_profile/fetch_security/fetch_quote/fetch_financial/fetch_announcement`，未实现接口优雅 `NotImplementedError` 降级）+ `providers/`（`_http.py` pluggable transport `(method,url,*,data,headers,timeout)->(status,body)` + stdlib urllib 实现 + `content_hash`(sha256)/`secid_for`；`eastmoney.py` `EastMoneyProvider`：push2 行情/资料 + datacenter F10 财务，价格 ÷100，`raw://eastmoney/{dataset}/{ymd}/{ts_code}.json`；`cninfo.py` `CninfoAnnouncementProvider`：topSearch→orgId 两步 + hisAnnouncement，PDF 前缀 `http://static.cninfo.com.cn/`，trust_level=L1_official）；`acquisition.py` `PublicDataAcquisitionService.acquire_company(ts_code)`（profile→map_stock_basic→quote→financial→announcement→`store.upsert_company_bundle`/`upsert_quote`，返回 `AcquisitionReport`）。`models.py` `SourceRef` additive 5 字段（provider/dataset/raw_snapshot_ref/version/hash）+ 4 个 source-neutral record（属性兼容现有 mapper/fact_mapper 的 `getattr` 读取，零改映射层即注入真实 SourceRef）。`apps/api/.../main.py` wiring：共享 `PublicDataAcquisitionService` 实例 + `POST /market/acquisition/public/run`（best-effort）+ `@app.on_event("startup")` best-effort seed（`SHANHAI_SKIP_PUBLIC_SEED` 可跳过，网络失败不阻断启动）。`apps/console` `types.ts` 镜像新 provenance 字段 + `source-tag.tsx` 显示 dataset/provider/raw_ref/hash。新增 `tests/market_data/test_public_providers.py`（4 离线用例，canned real-shaped payload + injected transport，证明闭环不依赖 live 网络）。**验证（live + browser）**：API 重启后 startup seed 拉取真实数据，`curl /companies/600519.SH` + 浏览器 `http://localhost:3000/company/600519.SH` 确认贵州茅台 name=贵州茅台/industry=白酒Ⅱ/close=1194.96(2026-06-29,eastmoney.daily)/财务(eastmoney.f10_main_finance roe=10.57)/公告(cninfo 原文 PDF)全部带真实 provenance（sha256 hash + raw:// ref + trust_level L3_public_aggregator / L1_official）。**GPT 设定的「闭环跑通则 M3.2 正式开始」门槛达成。** 边界：Tushare 降为 commercial optional（保留不删）；存储用 InMemoryStore（venv 无 psycopg，Postgres 落库归 M3.3）；不做 raw storage engine / data lake / object storage / parquet（归 M3.3）；未修改 RuntimeKernel / RuntimeContext / Experience Runtime；未实现 Selector / Memory / Evolution / Trading。已知小瑕疵（未修，非阻断）：「权益分派」公告被启发式分类为 `other`（关键词表缺「权益分派」）。
- [x] Agent Runtime 单元测试（通过）

## 当前目标

M3.2 Data Acquisition Foundation 的 **真实数据 spike 闭环已跑通**——`services/market-data` source-neutral 供给层（`PublicMarketDataProvider` + EastMoney / CNInfo stdlib adapter + `PublicDataAcquisitionService`）让 600519.SH 的真实免费数据（东方财富行情/资料/F10 财务 + 巨潮资讯公告）流入 `InMemoryMarketKnowledgeStore`，每条 fact 携带最小内置 `SourceRef` provenance（provider/dataset/captured_at/raw_snapshot_ref/version/hash），Console 端到端验收：贵州茅台带 eastmoney/cninfo 真实 provenance 正确渲染。**GPT 设定的「闭环跑通则 M3.2 正式开始」门槛达成**——验证了「先让现实撞模型，再让模型指导抽象」是正确路线。**下一步进入 M3.3 Knowledge Provenance Foundation**：引入不可变 raw data snapshot 存储（raw storage engine / Postgres 落库），把 `External Data → Raw Snapshot → Normalized Entity → Knowledge Fact` 分层物化，为多源融合（免费公开 + 本地计算 adapter，平级，不绑定单一平台）奠基。Runtime / Experience 契约抽象阶段已收尾，按路线 `Foundation → Market Data → Knowledge Model → Console Validation → Data Acquisition → Knowledge Provenance → 真实研究流程 → Candidate Provider → Experience Runtime`，不回头继续 Experience Runtime。

## Milestone 3 路线（已确定）

> 流程：`Milestone → Feature → Implementation → Review → Merge`（不再 PR-4.x gate / 多文档循环；一个 feature 一份 review）。

### M3.1 Company Intelligence Console Alpha ✅ Completed（checkpoint `1087e7e`）
- **目标**：用真实 A 股公司数据验证当前知识模型（Knowledge Model Validator，非产品 dashboard）。
- **范围**：① 创建 `apps/console`；② Bun + Next.js 16 + React 19 + Tailwind v4 + 基础 design system；③ 实现 Company Intelligence 页面（公司搜索 / 详情 / Fact / Financial / Announcement / Timeline / Sources）；④ 只读接入现有 Market Data API（不改契约）；⑤ 验证 Company entity model / MarketFact v1 / FinancialFact / AnnouncementFact / Timeline model。
- **结果**：六分区 Company Detail 自然成立，Entity Model 可被产品入口承载，M2.5 方向正确。Tushare 积分受限下用离线 fixture seed 3 家公司完成真实数据驱动的浏览器端到端验证；修复 timeline unhandledRejection。
- **暴露的模型 gap（已登记，本里程碑不实现）**：① Facts 裸 `predicate` 缺语义层 → M3.x Semantic Vocabulary Enhancement；② Source 仅为 attribute、需升级为独立 provenance 模型 → M3.2/M3.3 Provenance（M3.2 已落最小内置 SourceRef，完整 raw snapshot 归 M3.3）。
- **交付**：feature commit `feat(console): company intelligence console alpha`。

### M3.2 Data Acquisition Foundation ✅ Spike 闭环跑通
- **路线 pivot**：原 M3.2 = Knowledge Provenance Foundation 被重排为 M3.3。校准后的认知节点：「M2.5 知识如何表达 → M3.1 知识模型能被消费 → M3.2 知识从哪里来并且能否可信」。故先做 **Data Acquisition Foundation**（真实免费数据进入 + 最小内置 provenance），完整 raw snapshot 存储下移 M3.3。
- **原则**：实现优先、**先让现实撞模型再让模型指导抽象**（不提前抽象、不提交 Design Gate，先跑真实数据 spike）。
- **范围（已实现）**：① source-neutral `PublicMarketDataProvider`（`fetch_company_profile/fetch_security/fetch_quote/fetch_financial/fetch_announcement`，providers 平级）；② EastMoney（push2 行情/资料 + datacenter F10 财务）+ CNInfo（topSearch→orgId + hisAnnouncement 公告）stdlib adapter，pluggable transport 便于离线测试；③ `PublicDataAcquisitionService.acquire_company` 真实数据流入 `InMemoryMarketKnowledgeStore`；④ 最小内置 `SourceRef` provenance（provider/dataset/captured_at/raw_snapshot_ref/version/hash）；⑤ API wiring（startup seed + `POST /market/acquisition/public/run`）+ Console provenance 渲染。
- **结果**：600519.SH 真实数据闭环跑通，Console 端到端验收贵州茅台带 eastmoney/cninfo 真实 provenance。**「闭环跑通则 M3.2 正式开始」门槛达成。**
- **不绑定单一平台**：AkShare 不作为核心依赖（采集聚合 SDK 非数据源）；Tushare 降为 commercial optional（保留不删）。
- **交付**：feature commit `feat(market-data): add free data acquisition foundation`。

### M3.3 Knowledge Provenance Foundation ⏳ Planned / Next
- **定位**：在 M3.2 最小内置 provenance 之上，引入**不可变 raw data snapshot 存储**与完整 provenance 治理。来源未来不止 EastMoney/CNInfo（还有新浪 / 腾讯 / Wind / 交易所公告 / 研报 / 社交舆情），因此 raw snapshot 与 source 必须建模为一等公民，而非散落 attribute，否则将重蹈 identity（外部码当主键）的覆辙。
- **Goals**：
  - Introduce immutable raw data snapshot storage（raw storage engine / Postgres 落库 / 对象存储）
  - Materialize `External Data → Raw Snapshot → Normalized Entity → Knowledge Fact` 分层
  - Preserve source traceability（raw_snapshot_ref 指向真实不可变快照）
  - Support future multi-source ingestion
- **Not included**：
  - News crawler
  - Research report ingestion
  - Sentiment analysis
  - AI merge
- **Provenance 模型形态**（M3.2 已落最小内置版，M3.3 补 raw snapshot 物化）：
  ```
  Fact
   └── Source
        + provider          # 数据来源方（eastmoney / cninfo / wind / ...）
        + dataset           # 接口/数据集（daily_quote / f10_main_finance / announcement / ...）
        + captured_at       # 抓取时刻
        + raw_snapshot_ref  # 指向不可变原始快照（M3.3 物化存储）
        + version           # 来源数据版本
        + hash              # 原始内容指纹（防篡改 / 去重）
  ```
- **分层目标**：`External Data → Raw Snapshot → Normalized Entity → Knowledge Fact`（raw ingestion → normalization → knowledge）。免费公开数据 adapter + 本地计算 adapter 平级，经 Market Data Hub + Adapter Layer 内部统一为 Canonical Entity / Canonical Fact / Canonical Timeline。
- 并入原 Phase 3 Storage Refactor（Postgres identity tables / R1+R2 external_ids 登记 / cache-shadowing 治理）。

### M3.x Semantic Vocabulary Enhancement ⏳ Planned（doc-only 登记，不改 MarketFact）
- **背景**：Console 验证暴露 Facts 展示裸 `predicate`（如 `classified_in_industry` / `closing_price`），人类研究员需脑补语义。当前验证的是「schema 能否承载现实」而非「产品文案是否完善」，故只登记不修代码。
- **方向**：引入 **Knowledge Vocabulary Layer**，将 predicate 映射到展示语义：
  ```json
  {
    "predicate": "classified_in_industry",
    "display_name": "所属行业",
    "description": "公司所属申万行业分类"
  }
  ```
- **边界**：现阶段不修改 `MarketFact`；vocabulary 作为独立映射层，待 M3.3 之后排期。

### M3.4 Web Platform
- 技术栈：Bun + Next.js + React + Tailwind + Rspack；目录结构 `apps/{api, console, worker}`。
- 第一版定位：「Bloomberg 公司百科 + AI Research Notebook」。
- 禁止：dashboard / 大屏 / K 线 / 智能交易页面。

## 当前 Gate / 暂停点

- [x] **M2.5 Phase 1 Closure Review Gate**：✅ 已批准 PASS（`docs/design/market-foundation-hardening-phase1-closure-review-m2.5.md`，带 R1/R2 两项归属 Phase 3 的登记风险）。
- [x] **M2.5 Phase 2 Implementation Review**：✅ PASS（`docs/design/market-foundation-hardening-phase2-implementation-review-m2.5.md`）。已提交 checkpoint `de296c0` 并 push 到 `develop`。**Foundation / Runtime 抽象阶段在此收尾。**
- [x] **M3.1 Company Intelligence Console Alpha**：✅ Completed（checkpoint `1087e7e`）。Console Alpha 已实现并经真实数据驱动浏览器端到端验证关闭；用户批准 push。验证暴露的两项模型 gap 登记为 M3.2/M3.3 / M3.x（doc-only，不进入实现）。
- [x] **M3.2 Data Acquisition Foundation**：✅ Spike 闭环跑通。按路线 pivot 做真实数据 Data Adapter Spike（实现优先、不提交 Design Gate）；EastMoney + CNInfo source-neutral adapter 让 600519.SH 真实免费数据带最小内置 provenance 流入并经 Console 端到端验收，「闭环跑通则 M3.2 正式开始」门槛达成。交付 commit `feat(market-data): add free data acquisition foundation`。
- [ ] **M3.3 Knowledge Provenance Foundation（当前停靠点 / Next）**：路线与命名已对齐（doc-only 登记完成）；实现待 Review Gate 批准后开工。范围与 Goals/Not included 见上（不可变 raw snapshot 存储 + Phase 3 Storage Refactor）。
- ~~PR-4.2 Candidate Provider Adapter~~：**不再推进**（被 Milestone 3 取代；design gate 文档保留作历史参考，不进入实现）。
- ~~Milestone 2.3 Market Knowledge Expansion~~：蓝本已被 Phase 2 实现采用；后续扩展并入 M3.3 Knowledge Provenance Foundation。

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
