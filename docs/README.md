# ShanHai 文档

## 项目上下文

- [COLLABORATION_PROTOCOL.md](COLLABORATION_PROTOCOL.md)：AI 协作开发协议（三方角色、5 大架构原则、Coding Agent 工作流、Review 流程）
- [PRODUCT_VISION.md](PRODUCT_VISION.md)：产品定位、长期目标、与股票/量化软件的区别、演进路线
- [ARCHITECTURE_CONTEXT.md](ARCHITECTURE_CONTEXT.md)：架构设计原则（模型解耦 / Knowledge First / Harness First / 模块独立）
- [DEVELOPMENT_PRINCIPLES.md](DEVELOPMENT_PRINCIPLES.md)：AI Native 开发原则（Git 唯一事实来源、文档优先、ADR、不依赖聊天历史）
- [PROJECT_STATE.md](PROJECT_STATE.md)：当前阶段、进度、不变量、暂不开发项

## 架构决策记录

- [架构决策记录（ADR）](架构决策记录/)
  - [0001 语言栈与运行时](架构决策记录/0001-语言栈与运行时.md)
  - [0002 包管理工具链](架构决策记录/0002-包管理工具链.md)
  - [0003 Workflow 引擎自研最小骨架](架构决策记录/0003-Workflow引擎自研最小骨架.md)
  - [0004 Model Router 使用 Mock Provider](架构决策记录/0004-ModelRouter使用MockProvider.md)
  - [0005 AI 评审协作流程与分支模型](架构决策记录/0005-AI评审协作流程与分支模型.md)
  - [0006 Agent Runtime 执行模型](架构决策记录/0006-AgentRuntime执行模型.md)
  - [0007 Wiki 信息提取流程](架构决策记录/0007-Wiki信息提取流程.md)
  - [0008 运行记录持久化](架构决策记录/0008-运行记录持久化.md)
  - [0009 Local-first 持久化](架构决策记录/0009-Local-first持久化.md)
  - [0010 Evaluation Loop 架构](架构决策记录/0010-Evaluation-Loop-Architecture.md)
  - [0011 Model Provider 架构](架构决策记录/0011-Model-Provider-Architecture.md)
  - [0012 Agent Memory 架构](架构决策记录/0012-Agent-Memory-Architecture.md)
  - [0013 Agent Evaluation Feedback 架构](架构决策记录/0013-Agent-Evaluation-Feedback-Architecture.md)

## AI 评审入口

- [REVIEW.md](../REVIEW.md)：评审入口、读取顺序、仓库 Raw/Diff 兜底地址

## 模块边界速览

```
apps/api ─┐
          ├─ services/agent-runtime ─→ services/model-router ─→ providers
apps/web ─┘            │
                       ├─ packages/tools (Tool Registry)
                       └─ services/harness-core (Workflow)

services/wiki-engine   → 知识 Schema（Entity / Relation / Document）
services/data-pipeline → 数据接入骨架
packages/schemas       → 跨模块共享契约
```

调用链铁律：`Agent → Tool → Service → Database`；Agent 不直连模型与数据库。
