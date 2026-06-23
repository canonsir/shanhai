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
- `tests/test_agent_runtime.py`：生命周期 / Agent→Tool / 未授权拒绝 / Workflow 兼容 / 多步循环 / max_steps 截断，已通过；Phase 0 冒烟测试不受影响。
- `tests/test_wiki_extraction.py`：Extractor 实体/关系/别名/去噪单测 + WikiExtractionAgent 链路集成测，已通过。
- `tests/test_run_store.py`：InMemoryRunStore 契约 + Runner 落库 + best-effort 失败容错，已通过。
- `tests/test_local_persistence.py`：SqliteRunStore 契约 + 落盘 + 跨连接持久化 + Runner 落库 + 工厂选后端，已通过。
- `tests/test_evaluation.py`：RuntimeEvaluator 成功 / 失败 / 多 Step / 空 Run / 经 RunStore 取数，已通过。
- `tests/test_deepseek_provider.py`：DeepSeekProvider 请求构造/响应解析/缺 Key 报错/异常响应 + 端到端 Agent→Router→DeepSeek（Fake Transport）+ Mock 仍默认，已通过。

### Docs
- 新增项目上下文文档体系：`docs/PRODUCT_VISION.md`、`docs/ARCHITECTURE_CONTEXT.md`、`docs/DEVELOPMENT_PRINCIPLES.md`。
- `PROJECT_STATE.md` 迁移至 `docs/PROJECT_STATE.md`，并同步修正 README / AGENTS / REVIEW / docs 索引 / ADR 0005 中的引用路径。
- `AGENTS.md` §4.1：新增「配置文件修改纪律」铁律（禁止 Write 覆盖已有配置；修改配置须 read → diff → append → verify）。

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
