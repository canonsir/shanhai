# tools/context — Project Context Layer 同步工具

纯 Python 标准库（零依赖）。服务于 `.shanhai-meta/`（项目元上下文层）。
设计见 [ADR 0000](../../docs/架构决策记录/0000-项目元上下文架构.md)。

| 脚本 | 作用 | 落地 |
|---|---|---|
| `import_chat.py` | Raw 导出 → ContextEvent 流（`actor=unknown`，`raw#id` 幂等去重） | Commit 3 |
| `append_conversation.py` | 单条追加 ContextEvent（人 / 各 AI 决策的持续同步入口） | Commit 4 |
| `build_context.py` | 事实源（raw/stream/decisions）→ `context/*.md` 派生（幂等可重跑） | Commit 5 |

数据模型（ContextEvent / Record schema）落地于 Commit 2 `schema.py`。

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
