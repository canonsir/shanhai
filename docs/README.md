# ShanHai 文档

- [架构决策记录（ADR）](架构决策记录/)
  - [0001 语言栈与运行时](架构决策记录/0001-语言栈与运行时.md)
  - [0002 包管理工具链](架构决策记录/0002-包管理工具链.md)
  - [0003 Workflow 引擎自研最小骨架](架构决策记录/0003-Workflow引擎自研最小骨架.md)
  - [0004 Model Router 使用 Mock Provider](架构决策记录/0004-ModelRouter使用MockProvider.md)

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
