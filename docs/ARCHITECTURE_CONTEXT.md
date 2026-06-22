# ShanHai 架构上下文（Architecture Context）

> 解释 ShanHai 架构「为什么这样设计」。这是理解代码前应先读的设计意图说明，不替代 ADR（具体决策见 `docs/架构决策记录/`）。

## 分层总览

```
Application Layer    Web / API / Console
        ↓
Agent Intelligence   Research / Analysis / Knowledge / Strategy Agent
        ↓
Harness Core         Agent Runtime · Workflow · Memory · Tool Registry · Model Router
        ↓
Knowledge Layer      ShanHai Wiki · Knowledge Graph · Vector Memory
        ↓
Data Layer           PostgreSQL · pgvector · Redis · Object Storage
```

设计意图：自底向上、严格分层，上层依赖下层的稳定契约，下层不感知上层业务。

## 原则一：Agent 与模型解耦

Agent 永远不绑定具体模型厂商。模型是可替换的能力，不是 Agent 的属性。

禁止：

```
Agent → OpenAI / Claude
```

必须：

```
Agent
 ↓
Model Router
 ↓
Model Provider（OpenAI / Anthropic / DeepSeek / Qwen / Local）
```

落地方式：Agent 仅通过 `AgentContext.complete(...)` 调用模型，由 `Model Router` 按任务能力/成本选择 Provider。代码中不允许出现对某个厂商 SDK 的直接依赖。

## 原则二：Knowledge First

金融领域的核心资产不是模型，而是知识。模型会迭代更替，知识会持续增值。

核心知识资产：

- 财报
- 新闻
- 政策
- 公司关系
- 产业链
- 历史事件
- 投资经验

落地方式：所有研究过程被结构化记录（`Step` / `RunResult`），知识经 Wiki Engine 编译为实体与关系，长期沉淀进知识层而非散落于对话。

## 原则三：Harness First

当前优先建设 AI 运行底座，而不是面向交易的业务功能。

优先建设：

- Agent Runtime
- Workflow
- Tool
- Memory
- Evaluation

暂不建设：

- 行情页面
- 券商交易
- 自动下单

理由：底座决定上层能走多远。先把「Agent 如何稳定地思考、调用工具、记忆、被评估」做对，再谈业务。

## 原则四：模块独立

`harness-core / agent-runtime / model-router / wiki-engine / data-pipeline` 边界清晰、可单独替换。

禁止：

- Wiki 直接处理 Agent 逻辑
- Agent 直接访问数据库
- 业务代码直接调用模型

## 调用链铁律

```
Agent → Tool → Service → Database
```

Agent 触达外部能力的唯一入口是 Tool；触达模型的唯一入口是 Model Router。这条链路由 `AgentContext` 在结构上强制收口，未授权工具在运行时被拒绝。

## 相关 ADR

- 0001 语言栈与运行时
- 0002 包管理工具链
- 0003 Workflow 引擎自研最小骨架
- 0004 Model Router 使用 Mock Provider
- 0005 AI 评审协作流程与分支模型
- 0006 Agent Runtime 执行模型
