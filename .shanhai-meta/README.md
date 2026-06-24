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
│   ├── decision-log.md
│   └── rejected-decisions.md
└── context/                   # Layer 3：Context Snapshot（builder 重建，勿手改）—— 派生
    ├── current-state.md       # AI 启动首读
    ├── architecture-summary.md
    └── timeline.md
```

## 三层语义

| 层 | 内容 | 读者价值 |
|---|---|---|
| Layer 1 Raw | 原始对话（不可变） | AI 历史原料 |
| Layer 2 Decision Registry | 为什么这么决定 / 什么被否决 | AI 最需要的 |
| Layer 3 Context Snapshot | 当前版本 / 架构 / 冻结 / 阶段 | AI 启动入口 |

## Source of Truth 与 Projection 分离（ADR 0000 §D9）

- **事实源（append-only）**：`conversations/raw/`、`events/stream.jsonl`、`decisions/`
- **派生（builder 重建）**：`context/*.md`
- **AI 不直接修改 `context/` 快照**；要改，改事实源后重跑 `tools/context/build_context.py`。

## 同步工具

脚本在 [tools/context/](../tools/context/)（纯 Python 标准库，零依赖）：

- `import_chat.py` —— ChatGPT/Claude 导出 → ContextEvent 流（`actor=unknown`，幂等去重）
- `append_conversation.py` —— 单条追加 ContextEvent（持续同步入口）
- `build_context.py` —— 事实源 → `context/` 派生快照（幂等可重跑）
