# tools/context — Project Context Layer 同步工具

纯 Python 标准库（零依赖）。服务于 `.shanhai-meta/`（项目元上下文层）。
设计见 [ADR 0000](../../docs/架构决策记录/0000-项目元上下文架构.md)。

| 脚本 | 作用 | 落地 |
|---|---|---|
| `schema.py` | Context Domain Model：ContextEvent / DecisionRecord / ContextSnapshot（可逆 JSON + 校验） | Commit 2 ✅ |
| `import_chat.py` | Raw 导出 → ContextEvent 流（`actor=unknown`，`source.ref=raw#id` 幂等去重，provenance 保留） | Commit 3B ✅ |
| `append_conversation.py` | 单条追加 ContextEvent（人 / 各 AI 决策的持续同步入口） | Commit 4 |
| `build_context.py` | 事实源（raw/stream/decisions）→ `context/*.md` 派生（幂等可重跑） | Commit 5 |

> Commit 3 拆为 **3A Raw Archive**（原始导出原封不动迁入 `conversations/raw/`，不解析/不转换/不修改）
> 与 **3B Importer**（schema 稳定后再做 Raw → ContextEvent）。3A 先建立 Raw Source of Truth。

## ContextEvent ≠ Runtime Event（边界，务必区分）

`ContextEvent`（本层）描述**项目认知如何形成**——人 + AI 协作过程中的事实（讨论、决策、Review、批准、实现）。
它**不参与 Agent 运行**，不被任何 `services/` 消费。

`ExperienceEvent`（[ADR 0014](../../docs/架构决策记录/0014-Agent-Experience-Memory-Architecture.md)，`services/experience`）描述
**Agent 执行过程中发生了什么**——是 Runtime 世界的事实。

| | ContextEvent（Meta） | ExperienceEvent（Runtime） |
|---|---|---|
| 回答 | 项目认知如何形成 | Agent 执行了什么 |
| 例 | 「团队决定 stock-analysis 需要 X 数据源」 | 「Agent 执行了 stock-analysis 任务」 |
| 依赖 | stdlib（零依赖） | pydantic 等 Runtime 栈 |
| 消费方 | 人 + AI 协作（不被 service import） | Agent Runtime |

两个 event 互不共享、互不转换。

## 数据流（ADR 0000 §D4 / §D9）

```
conversations/raw/  ──import──▶  events/stream.jsonl  ──build──▶  context/*.md
   (事实源,不可变)               (事实源,append-only)            (派生,勿手改)
                                        ▲
                          append_conversation.py（单条追加）
                                        │
                                   decisions/（人工确认事实源）
```

## 用法（落地后）

```bash
python -m tools.context.import_chat --source .shanhai-meta/conversations/raw/<file>.json
python -m tools.context.append_conversation --type decision --source trae --body "..."
python -m tools.context.build_context
```
