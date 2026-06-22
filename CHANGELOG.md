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
- ADR 0006：Agent Runtime 执行模型。
- `tests/test_agent_runtime.py`：生命周期 / Agent→Tool / 未授权拒绝 / Workflow 兼容 / 多步循环 / max_steps 截断，已通过；Phase 0 冒烟测试不受影响。

### Docs
- 新增项目上下文文档体系：`docs/PRODUCT_VISION.md`、`docs/ARCHITECTURE_CONTEXT.md`、`docs/DEVELOPMENT_PRINCIPLES.md`。
- `PROJECT_STATE.md` 迁移至 `docs/PROJECT_STATE.md`，并同步修正 README / AGENTS / REVIEW / docs 索引 / ADR 0005 中的引用路径。

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
