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
- [x] Agent Runtime 单元测试（通过）

## 当前目标

完善 AI Harness 基础设施（Agent Runtime / Workflow / Tool / Memory / Evaluation），保证模块边界与架构正确性。

## 进行中

- [ ] 架构 Review（等待评审反馈）

## 下一步（Phase 1 候选）

- 多步推理 Agent：think/act/observe 循环 + max_steps 调度策略
- Workflow 条件分支 / 并行（评估是否引入 LangGraph）
- Wiki Engine：信息提取 / 实体识别 / 关系发现（当前仅 Schema）
- Model Router：接入真实 Provider（OpenAI / DeepSeek / Qwen）
- 运行记录持久化（落库，另开 ADR）

## 暂不开发（明确禁止本阶段实现）

- 实时行情系统
- 券商交易接口
- 自动交易 Agent
- 复杂量化策略 / 高频策略
- 回测系统

## 不变量（不允许破坏）

- Model Router 隔离：Agent 禁止直接绑定/调用模型
- Service 边界：Agent 不直接访问数据库，调用链 `Agent → Tool → Service → Database`
- 模块独立：harness-core / agent-runtime / model-router / wiki-engine / data-pipeline 边界清晰
- 任何架构调整先写 ADR（`docs/架构决策记录/`）

## 已知限制

- 本机无 Docker，`docker compose up` 未实地验证（compose/SQL 仅静态检查）
- 本机无 uv/pnpm，验证时用 Homebrew Python 3.14 venv 做 editable 安装
- gh 凭证因沙箱限制以明文存于工作区 `.gh-config/`（已 gitignore）
