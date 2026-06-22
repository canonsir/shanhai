# ShanHai（山海）

> AI Native 的中国资本市场认知与决策系统。

ShanHai 不是传统股票软件，核心目标是构建一个能长期学习中国资本市场的 AI 系统：

```
数据 → 知识 → 认知 → 分析 → 策略 → 执行
```

## 当前阶段：Phase 0 — Harness Foundation

只搭建 AI Agent 平台基础设施，**暂不实现**行情页面 / 券商交易 / 自动交易 / 量化策略 / 回测。

本阶段交付：

1. 项目工程结构（Monorepo）
2. Model Router V0.1
3. Agent Runtime Skeleton
4. Tool Registry
5. 数据库基础环境（PostgreSQL + pgvector + Redis）
6. Wiki Engine Schema

## 总体架构

```
Application Layer    →  Web / API / Console
Agent Intelligence   →  Research / Analysis / Knowledge / Strategy Agent
Harness Core         →  Agent Runtime · Workflow Engine · Memory · Tool Registry · Model Router
Knowledge Layer      →  ShanHai Wiki · Knowledge Graph · Vector Memory
Data Layer           →  PostgreSQL · pgvector · Redis · Object Storage
```

## 架构原则

- **模型与业务解耦**：Agent 禁止直接调用模型，必须经 `Model Router`。
- **知识优先**：核心资产是知识（公司/行业/产业链/政策/事件/经验），不是代码。
- **模块独立**：各 service / package 边界清晰、可单独替换。
- **调用链铁律**：`Agent → Tool → Service → Database`，Agent 不直连模型与数据库。

## 目录结构

```
shanhai/
├── apps/            # web(Node) / api(FastAPI)
├── services/        # harness-core / model-router / agent-runtime / wiki-engine / data-pipeline / evaluation
├── packages/        # schemas / prompts / tools
├── infrastructure/  # docker-compose.yml / database
├── docs/            # 含 架构决策记录(ADR)
└── tests/
```

## 技术栈（见 docs/架构决策记录）

- 服务与 API：Python 3.11+ / FastAPI
- 前端：Node + pnpm
- 包管理：uv（Python workspace）+ pnpm（Node workspace）
- Workflow：自研最小骨架（受 LangGraph 思想启发）
- Model Provider：Phase 0 使用 Mock Provider

## 快速开始

前置工具：Python 3.11+、Node、[uv](https://docs.astral.sh/uv/)、pnpm、Docker。

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 安装 Python 工作区依赖
uv sync

# 3. 启动基础数据库服务
docker compose -f infrastructure/docker-compose.yml up -d

# 4. 验证 Harness（Router 切模型 / Agent 调 Tool）
uv run python -m tests.smoke
```

> 若本地未安装 uv，可退化使用 `python -m venv .venv && source .venv/bin/activate` 后对各包执行 `pip install -e`。

## 验收标准（Phase 0）

- `docker compose up` 能启动基础服务
- Model Router 可以切换模型
- Agent 可以调用 Tool
- 数据库可连接
- Wiki Entity Schema 存在

## 文档

- 协作规范与 Agent 开发约束：[AGENTS.md](AGENTS.md)
- 项目实时状态：[PROJECT_STATE.md](PROJECT_STATE.md)
- AI 架构评审入口：[REVIEW.md](REVIEW.md)
- 架构决策记录：[docs/架构决策记录/](docs/架构决策记录/)
- 变更记录：[CHANGELOG.md](CHANGELOG.md)
