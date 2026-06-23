# Changelog

本项目变更记录。格式参考 Keep a Changelog，遵循语义化版本。

## [Unreleased] — Phase 1：Agent Runtime

### Added
- `services/agent-runtime`：执行模型 think → act → observe（ADR 0006）。
  - `types.py`：`AgentStatus` 生命周期 + `Step` / `RunResult` 结构化运行记录 + `Plan`。
  - `context.py`：`AgentContext` 收口模型/工具访问（`complete()`→ModelRouter，`use_tool()`→ToolRegistry），从结构上保证架构铁律。
  - `runner.py`：`AgentRunner` 驱动生命周期与运行记录。
  - `agent.py`：`BaseAgent`（think/act/observe 钩子 + max_steps），保留 `Agent` 别名与 `use_tool`/`run` 向后兼容。
  - `examples.py`：`ToolEchoAgent`（单步）、`MultiStepToolAgent`（多步逐项调度）示例。
- 多步推理：`AgentRunner` 按 `max_steps` 驱动多轮 think → act → observe 循环；`AgentContext` 增加 `iteration`/`observations`/`last_observation`，支持 think 基于上一轮观察规划。
- `services/wiki-engine`：规则驱动信息提取（ADR 0007）。
  - `extractor.py`：`Extractor` 按词典识别实体、按文本模式发现关系，model-agnostic、确定性可复现。
  - `tool.py`：`WikiExtractTool` 包装 Extractor，作为 Agent 触达 Service 的唯一通道。
  - `agent.py`：`WikiExtractionAgent` 编排链路（think 经 ModelRouter 证明模型在环，act 经 Tool 调用 Service）。
- 运行记录持久化（ADR 0008）。
  - `agent-runtime/store.py`：`RunStore` 抽象 + `InMemoryRunStore` + `RunRecord`，agent-runtime 不依赖 DB 驱动。
  - `AgentRunner` 增加可选 `store` 注入，运行结束 best-effort 落库；`BaseAgent` 支持透传 `store`，不注入则零行为变化。
  - 新增 `services/persistence`：`PostgresRunStore`（psycopg 惰性导入，可选依赖 `[postgres]`）+ `infrastructure/database/init/002_agent_runs.sql`（agent_runs / agent_steps）。
- Local-first 持久化（ADR 0009）：数据库降为增强能力，非开发前置。
  - `services/persistence/sqlite_run_store.py`：`SqliteRunStore`（标准库 `sqlite3`，零外部依赖、可落盘、可查询），复用 agent_runs / agent_steps 两表模型。
  - `services/persistence/factory.py`：`default_run_store()` 按 `SHANHAI_RUN_STORE`（sqlite 默认 / memory / postgres）装配，存储选择权在应用装配层，`agent-runtime` 仍只依赖 `RunStore` 抽象。
  - 本地落盘默认 `./.shanhai/runs.db`（已 gitignore）。
- Evaluation Loop Layer 1 — Runtime Evaluation（ADR 0010）。
  - `services/evaluation/models.py`：`Metric`（name/value/layer/unit）+ `EvaluationResult`（run_id/evaluator/metrics/passed/detail/created_at，含 `value(name)` 取值）。
  - `services/evaluation/evaluator.py`：`Evaluator` 抽象 + `RuntimeEvaluator`（指标 success / step_count / tool_usage_count / error_type），输入 `RunResult` 或 `RunStore` 读出的 `RunRecord`，输出 `EvaluationResult`。
  - 边界：只经 `RunStore`/`RunResult` 只读取数，不直连 DB、不调用模型、不修改 Agent Runtime / Tool Registry；依赖单向 `evaluation → agent-runtime`。Layer 2/3 预留。
- 真实 Model Provider — DeepSeek 适配器（ADR 0011，Phase 2.5.1）。
  - `services/model-router/.../providers/deepseek.py`：`DeepSeekProvider` 实现 `ModelProvider.complete(spec, messages) -> CompletionResult`；网络调用走可注入 transport，默认标准库 urllib（零新依赖），从 `spec.options` 取 `model`/`base_url`/`timeout`。
  - 机密只从环境变量 `SHANHAI_DEEPSEEK_API_KEY` 读取，缺失明确报错；新增根目录 `.env.example`（`.env` 已 gitignore）。
  - `models.yaml` 的 `deepseek` 增加 `options`（model id + base_url），不含任何密钥。
  - `MockProvider` 仍为默认 Provider：未注册真实 Provider 时按既有机制回退 mock，无 API Key 可跑全部测试。
  - 调用方与 Agent Runtime 零改动；Router 现有 `complete`/`select` 签名不变。
- ADR 0006：Agent Runtime 执行模型。
- ADR 0007：Wiki 信息提取流程（职责三层划分 + Agent→Tool→Service 调用链）。
- ADR 0008：运行记录持久化（RunStore 抽象 + 依赖注入 + best-effort 落库）。
- ADR 0009：Local-first 持久化（SQLite 默认后端 + 装配工厂，Postgres 降为增强）。
- ADR 0010：Evaluation Loop 架构（反馈闭环定位 + 三层模型 + Evaluator/EvaluationResult/Metric 契约）。
- ADR 0011：Model Provider 架构（真实 Provider 复用 ModelProvider 接口 + 机密走环境变量 + Mock 永久默认）。
- ADR 0012：Agent Memory 架构（Memory 与 Knowledge Engine 正交分层 + Runtime/Knowledge/Experience 三层模型 + MemoryStore 抽象 + Agent 经 Tool/Service 访问，仅设计）。
- ADR 0013：Agent Evaluation Feedback 架构（Evaluation→Feedback→Experience Memory 闭环 + 度量/归因/沉淀三段分层 + ExperienceCandidate 生成与晋升规则 + Feedback 独立组合层，仅设计）。
- ADR 0014：Agent Experience Memory 架构（ADR 0012 扩展，Event Log Lite：ExperienceEvent append-only 事件 + Episode/SemanticExperience 投影 + refs 引用 run_id/evaluation/entity_ids + outcome 延迟回填；不引入 Vector/Graph/CQRS，仅设计）。
- Experience Event Infrastructure（ADR 0014 Stage 1，事实基座落地）。
  - 新增 `services/experience`：`models.py`（`ExperienceEventType` 枚举 decision/observation/evaluation/outcome/lesson + `ExperienceRefs` 引用 run_id/evaluation_ref/entity_ids/parent_event_id + `ExperienceEvent` 含 payload/occurred_at/recorded_at，event_id 自动生成）。
  - `services/experience/store.py`：`ExperienceStore` 抽象（append-only，无 update/delete）+ `InMemoryExperienceStore`（沿用 RunStore 范式），支持 `append`/`get`/`list`（按 agent/type/entity_id/since/limit 过滤，occurred_at 倒序，无向量检索）。
  - 边界：模块零业务依赖（仅 `pydantic`），结构上无法访问 RunStore/Evaluation/Knowledge 类型，从设计上保证「引用而非复制」；不实现 Episode 投影 / SemanticExperience / Vector / Graph / DB / LLM（留待后续 Stage，待真实 Agent 运行数据验证）。
  - 接入根 `pyproject.toml` workspace（members + sources）。
- Memory Runtime Access Layer（ADR 0012 Layer 1，记忆访问层落地；不含持久 Storage）。
  - 新增 `services/memory`：`models.py`（`MemoryScope` RUNTIME/KNOWLEDGE/EXPERIENCE + `MemoryRecord` 归一返回 + `MemoryQuery` 归一请求）。
  - `adapters.py`：`RuntimeMemoryAdapter`（薄包 agent-runtime `Memory`，进程内 scratchpad，可读写）+ `KnowledgeReadAdapter`（只读委派 `KnowledgeService`）+ `ExperienceReadAdapter`（只读委派 `ExperienceStore.get/list`，绝不 append）。
  - `service.py`：`MemoryService` 按 scope 路由 read/search/write，KNOWLEDGE/EXPERIENCE 只读（write 抛 `PermissionError`），不调模型/不直连 DB/不复制事实。
  - `tool.py`：单 `MemoryTool`（name="memory"）action 派发 read/search/write，作为 Agent 触达 Memory 的唯一通道，受 `AgentContext.use_tool` 授权约束；Agent 不持有 Service/Store 引用。
  - `services/wiki-engine/service.py`：新增最小只读 `KnowledgeService`（进程内 Entity 索引 + `get_entity` + `search` by text/type，无向量），为 Knowledge Memory 提供只读检索入口；事实来源仍属 Knowledge Engine。
  - 约束：不实现 vector / semantic memory / 自动总结 / 持久 `MemoryStore`；不修改 ADR 0014 EventStore（只读消费）。依赖单向 `memory → tools + agent-runtime + wiki-engine + experience`。
  - 接入根 `pyproject.toml` workspace（members + sources）。
- Evaluation Feedback 闭环 — Stage 1（ADR 0013，FailurePattern → Candidate → Lesson）。
  - 新增 `services/feedback`：`models.py`（`ExperienceCandidate` 候选经验 + `CandidateKind` 枚举，只引用 run_id/evaluator、不内嵌原始 metrics）。
  - `rules.py`：`FeedbackRule` 抽象 + `FailurePatternRule`（`passed==False` 按 `error_type` 产候选，`dedup_key=agent|failure|error_type`，确定性、不调用模型）。
  - `registry.py`：`CandidateRegistry`（进程内同 `dedup_key` 合并计数 + 来源累加 + 阈值晋升判定，抗一次性噪声）。
  - `engine.py`：`FeedbackEngine.process(EvaluationResult, RunRecord?)` 编排「规则 → 候选 → 去重 → 阈值晋升 → `ExperienceStore.append` 落 `type=lesson` 事件」，同模式不重复晋升。
  - 写经验路径（决策①）：Feedback 为离线系统编排层（非 Agent），经 `ExperienceStore.append`（service→service）写经验，**不**给 `MemoryService` 增 EXPERIENCE 写能力；EXPERIENCE 对 Agent 保持只读，读侧反哺仍由 `MemoryTool` 承担。
  - 引用而非复制：lesson 事件经 `refs.run_id`/`refs.evaluation_ref` 引用来源，`payload` 仅存提炼结论 + 精简 signals + source_run_ids，绝不内嵌 metrics。
  - 约束：仅 `FailurePattern` 单规则；不实现 regression/effective_path、Episode/SemanticExperience 投影、模型在环归因、Vector/Graph/CQRS、新增 DB；不改 `AgentRunner` 与 `ExperienceStore` 契约（只 append）。依赖单向 `feedback → evaluation + experience + agent-runtime`。
  - ADR 0013 增补 Addendum（Stage 1 实现决策）：写经验归口 ExperienceStore、晋升产物=lesson 事件、Stage 1 范围收敛。
  - 接入根 `pyproject.toml` workspace（members + sources）。
- `tests/test_agent_runtime.py`：生命周期 / Agent→Tool / 未授权拒绝 / Workflow 兼容 / 多步循环 / max_steps 截断，已通过；Phase 0 冒烟测试不受影响。
- `tests/test_wiki_extraction.py`：Extractor 实体/关系/别名/去噪单测 + WikiExtractionAgent 链路集成测，已通过。
- `tests/test_run_store.py`：InMemoryRunStore 契约 + Runner 落库 + best-effort 失败容错，已通过。
- `tests/test_local_persistence.py`：SqliteRunStore 契约 + 落盘 + 跨连接持久化 + Runner 落库 + 工厂选后端，已通过。
- `tests/test_evaluation.py`：RuntimeEvaluator 成功 / 失败 / 多 Step / 空 Run / 经 RunStore 取数，已通过。
- `tests/test_deepseek_provider.py`：DeepSeekProvider 请求构造/响应解析/缺 Key 报错/异常响应 + 端到端 Agent→Router→DeepSeek（Fake Transport）+ Mock 仍默认，已通过。
- `tests/test_experience.py`：ExperienceStore append/get/未命中/自动 event_id/list 过滤(agent/type/entity_id/since/limit)+倒序/append-only 拒绝覆盖且无 update-delete/refs 只引用不复制，已通过。
- `tests/test_memory.py`：三 scope（runtime 读写 / knowledge 只读检索 / experience 只读检索）+ 只读 scope 拒写 + MemoryTool action 派发 + 经 AgentContext 授权访问与未授权拒绝，已通过。
- `tests/test_feedback.py`：FailurePatternRule 失败产候选/成功不产 + CandidateRegistry 合并计数与阈值晋升 + FeedbackEngine 阈值前不落/达阈值晋升一条/不重复晋升 + lesson 只引用不复制度量 + 端到端 Run→Eval→Feedback→Lesson 并经 MemoryTool 只读反哺，已通过。

### Docs
- 新增项目上下文文档体系：`docs/PRODUCT_VISION.md`、`docs/ARCHITECTURE_CONTEXT.md`、`docs/DEVELOPMENT_PRINCIPLES.md`。
- `PROJECT_STATE.md` 迁移至 `docs/PROJECT_STATE.md`，并同步修正 README / AGENTS / REVIEW / docs 索引 / ADR 0005 中的引用路径。
- `AGENTS.md` §4.1：新增「配置文件修改纪律」铁律（禁止 Write 覆盖已有配置；修改配置须 read → diff → append → verify）。
- `docs/AI_COLLABORATION_PRINCIPLES.md`：新增 AI 协作原则（任何 AI Agent 进入仓库须先读）——AI Solution Engineer 角色定位、探索→讨论→收敛→ADR→实现 协作模式、三方职责（Human Owner / GPT 顾问 / AI 工程师）、四阶段工作流、核心架构边界；AGENTS.md 头部与 §7、docs 索引同步引用。

## [Phase 0] — Harness Foundation

### Added
- 初始化 Monorepo 工程结构（apps / services / packages / infrastructure / docs / tests）。
- uv（Python workspace）+ pnpm（Node workspace）双工具链配置。
- 根级文档：README.md、AGENTS.md、.env.example、.gitignore。
- 架构决策记录（ADR）：语言栈、包管理工具链、Workflow 自研骨架、Model Router Mock Provider。
- `packages/schemas`：跨模块共享契约（Message / ModelSpec / Capability / TaskType / Role）。
- `packages/tools`：Tool 接口 + ToolRegistry 注册机制 + EchoTool 示例。
- `services/model-router`：Provider 抽象 + MockProvider + models.yaml 注册表 + 按能力/成本选模型的 Router。
- `services/agent-runtime`：Agent 基类（Agent→Tool 调用链约束）+ Memory 接口 + InMemoryMemory。
- `services/harness-core`：自研最小 Workflow 骨架（Node / Workflow + 顺序执行器）。
- `services/wiki-engine`：Entity / Relation / Document Schema（公司/行业/政策/事件/人物/概念）。
- `services/data-pipeline`、`services/evaluation`：骨架占位。
- `apps/api`：FastAPI 应用（/health、/models、/complete）。
- `apps/web`：pnpm workspace 占位。
- `infrastructure/docker-compose.yml`：PostgreSQL(pgvector) + Redis；`database/init/001_init.sql` 启用 vector 扩展。
- `tests/smoke.py`：Phase 0 冒烟测试（Router 切换 / Agent→Tool / Wiki Schema），已通过。
- `PROJECT_STATE.md` / `REVIEW.md`：AI 评审入口与项目状态文件。
- ADR 0005：AI 评审协作流程与分支模型（main ← develop）。
- AGENTS.md 补充分支模型与 AI 评审协作约定。
