# .shanhai-meta/ — ShanHai Project Context Layer（项目元上下文层）

> 设计依据：[ADR 0000：ShanHai 项目元上下文架构](../docs/架构决策记录/0000-项目元上下文架构.md)
> AI 入口：仓库根目录 [AI_CONTEXT.md](../AI_CONTEXT.md)

支撑不同 AI 模型、不同开发环境、不同会话之间共享**一致项目上下文**的基础设施。
它是 **Meta 层**（给人 + AI 协作），与 Runtime 层（`services/`，给 Agent）正交对称：

```
Runtime 世界（给 Agent）                 Meta 世界（给 人 + AI 协作）
  services/{memory,experience,…}           .shanhai-meta/{context,decisions,…}
  .shanhai/  运行落盘（可丢弃，gitignore）
```

本层**纳入 git 版本控制**（持久化核心资产），区别于 `.shanhai/`（可丢弃运行数据，已 gitignore）。

## 目录结构

```
.shanhai-meta/
├── README.md                  # 本文件
├── project.yaml               # 项目元信息：版本 / 阶段 / baseline / 冻结项 / 参与方
│
├── conversations/raw/         # Layer 1：原始对话归档（不改 / 不删 / 永久）—— 事实源
├── events/stream.jsonl        # ContextEvent 统一事实流（append-only）       —— 事实源
├── decisions/                 # Layer 2：Decision Registry（人工确认）       —— 事实源
│   ├── README.md
│   ├── registry.jsonl         # 唯一结构事实源：DecisionRecord（机器读）
│   └── records/DEC-XXXX-*.md  # 人读叙述 / 解释层（每条决策一份）
└── context/                   # Layer 3：Context Snapshot（builder/renderer 重建，勿手改）—— 派生
    ├── cognition.json         # AI 启动认知枢纽（CognitionSnapshot，5A 确定性装配，机器读）
    └── current-state.md       # 上者的人读视图（5B renderer 渲染，纯函数）
```

## 三层语义

| 层 | 内容 | 读者价值 |
|---|---|---|
| Layer 1 Raw | 原始对话（不可变） | AI 历史原料 |
| Layer 2 Decision Registry | 为什么这么决定 / 什么被否决 | AI 最需要的 |
| Layer 3 Context Snapshot | 当前版本 / 架构 / 冻结 / 阶段 | AI 启动入口（cognition.json） |

## Source of Truth 与 Projection 分离（ADR 0000 §D9）

- **事实源（append-only）**：`conversations/raw/`、`events/stream.jsonl`、`decisions/`、`project.yaml`
- **派生（builder/renderer 重建）**：`context/cognition.json`（机器读枢纽）→ `context/current-state.md`（人读视图）
- **AI 不直接修改 `context/` 派生物**；要改，改事实源后重跑 `tools/context/builder.py` → `renderer.py`。
- **治理（手写，非派生）**：`AI_CONTEXT.md` 是 bootstrap manifest / Governance，不由 builder/renderer 生成。

## 同步工具

脚本在 [tools/context/](../tools/context/)（纯 Python 标准库，零依赖）：

- `import_chat.py` —— ChatGPT/Claude 导出 → ContextEvent 流（`actor=unknown`，幂等去重）
- `decisions.py` —— Decision Registry：加载 `registry.jsonl`（唯一结构事实源）→ 打印瞬态人读视图（不落盘）
- `append_conversation.py` —— 单条追加 ContextEvent（持续同步入口；已推迟，先建认知层）
- `builder.py` —— Cognition Snapshot Builder：`project.yaml` + `registry.jsonl` → `context/cognition.json`（确定性装配，禁 LLM）
- `renderer.py` —— Cognition Snapshot Renderer：`context/cognition.json` → `context/current-state.md`（人读视图，纯函数，禁 LLM）
- `health.py` —— Context Health Check：Source（事实源存在）/ Integrity（决策回链命中 stream）/ Projection（派生物存在），输出 OK / FAILED（只读，禁 LLM）

## Context Foundation Completed（Commit 5C 封板）

ADR 0000 的认知基础设施（Raw → ContextEvent → Decision Registry → Cognition Snapshot → Human View）
已闭环完成。本层（`.shanhai-meta/`）连同 `tools/context/schema.py` 自此进入 **稳定基础层（stable foundation layer）**。

- **语义冻结**（不是代码冻结）：已有契约 `ContextEvent` / `DecisionRecord` / `CognitionSnapshot` 的语义保持稳定。
- **修改已有契约需 ADR**：对上述结构的字段语义变更，必须先有新的 ADR。
- **扩展不受限**：Runtime 阶段新增 `ObservationEvent` / `MarketEvent` / `DecisionEvent` 等新类型属正常扩展，无需 ADR。
- `cognition.json._metadata.cognition_id`（`sha256:...`）是内容指纹（content identity，非 version）：内容不变则不变，可答「这次启动认知 == 上次?」。
