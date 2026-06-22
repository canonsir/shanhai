# ShanHai Project State

> 项目实时状态快照。供 AI（ChatGPT / Claude / Trae）与协作者快速对齐进度。
> 每完成一个阶段或重要模块时更新本文件。

## 版本

v0.1.0

## 当前阶段

Phase 0 — Harness Foundation

## 最新提交

- 分支：`main`
- Commit：`d8f9bee`（请以仓库最新为准）
- 仓库：https://github.com/canonsir/shanhai

## 已完成

- [x] Monorepo 工程结构（apps / services / packages / infrastructure / docs / tests）
- [x] uv + pnpm 双工作区
- [x] Model Router V0.1（Provider 抽象 + Mock + models.yaml + 能力/成本选择）
- [x] Agent Runtime Skeleton（Agent 基类 + Memory 接口）
- [x] Tool Registry（Tool 接口 + 注册机制）
- [x] Harness Core Workflow 最小骨架
- [x] Wiki Engine Schema（Entity / Relation / Document）
- [x] 数据库基础环境（docker-compose：PostgreSQL + pgvector + Redis）
- [x] FastAPI 应用层（/health、/models、/complete）
- [x] Phase 0 冒烟测试（通过）
- [x] ADR 0001-0004

## 进行中

- [ ] 架构 Review（等待评审反馈）

## 下一步（Phase 1 候选）

- Agent Runtime 增强：多步执行、Tool 调度策略
- Workflow 条件分支 / 并行（评估是否引入 LangGraph）
- Wiki Engine：信息提取 / 实体识别 / 关系发现（当前仅 Schema）
- Model Router：接入真实 Provider（OpenAI / DeepSeek / Qwen）

## 不变量（不允许破坏）

- Model Router 隔离：Agent 禁止直接绑定/调用模型
- Service 边界：Agent 不直接访问数据库，调用链 `Agent → Tool → Service → Database`
- 模块独立：harness-core / agent-runtime / model-router / wiki-engine / data-pipeline 边界清晰
- 任何架构调整先写 ADR（`docs/架构决策记录/`）

## 已知限制

- 本机无 Docker，`docker compose up` 未实地验证（compose/SQL 仅静态检查）
- 本机无 uv/pnpm，验证时用 Homebrew Python 3.14 venv 做 editable 安装
- gh 凭证因沙箱限制以明文存于工作区 `.gh-config/`（已 gitignore）
