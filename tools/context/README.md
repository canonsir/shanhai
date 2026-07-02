# tools/context — Project Context Layer 同步工具

纯 Python 标准库（零依赖）。服务于 `.shanhai-meta/`（项目元上下文层）。
设计见 [ADR 0000](../../docs/架构决策记录/0000-项目元上下文架构.md)。

| 脚本 | 作用 | 落地 |
|---|---|---|
| `schema.py` | Context Domain Model：ContextEvent / DecisionRecord / ContextSnapshot / CognitionSnapshot（可逆 JSON + 校验） | Commit 2 ✅（4 增补 DecisionRecord，5A 加 CognitionSnapshot） |
| `import_chat.py` | Raw 导出 → ContextEvent 流（`actor=unknown`，`source.ref=raw#id` 幂等去重，provenance 保留） | Commit 3B ✅ |
| `decisions.py` | Decision Registry：加载 `registry.jsonl`（唯一结构事实源，机器读）→ 打印瞬态人读视图（不落盘，无第二事实源） | Commit 4 ✅ |
| `append_conversation.py` | 单条追加 ContextEvent（人 / 各 AI 决策的持续同步入口） | 推迟（先建认知层，不急着导更多事实） |
| `builder.py` | Cognition Snapshot Builder：`project.yaml` + `registry.jsonl` → `context/cognition.json`（确定性装配，禁 LLM） | Commit 5A ✅ |
| `renderer.py` | Cognition Snapshot Renderer：`context/cognition.json` → `context/current-state.md`（人读视图，纯函数，禁 LLM） | Commit 5B ✅ |
| `health.py` | Context Health Check：Source（事实源存在）/ Integrity（决策回链命中 stream）/ Projection（派生物存在），输出 OK / FAILED（只读，禁 LLM） | Commit 5C ✅ |
| `conversation_ingest.py` | Conversation Ingestion：`conversations/inbox/` dump → `conversations/raw/` 快照 + `index.jsonl` catalog（增量纳管，identity 比对，失败入 quarantine，**不进 stream.jsonl**，禁 LLM） | Commit 5D ✅ |

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
conversations/raw/  ──import──▶  events/stream.jsonl
   (事实源,不可变)               (事实源,append-only)
                                        ▲
                          append_conversation.py（单条追加）

project.yaml + decisions/registry.jsonl  ──builder──▶  context/cognition.json  ──renderer──▶  context/current-state.md
   (事实源,人工确认)                       (确定性装配)     (派生认知枢纽,机器读,勿手改)   (纯函数)      (人读视图,勿手改)
```

> `cognition.json` 是唯一派生认知枢纽（Agent 直接加载）；`current-state.md` 只是它面向人的一个视图。
> `AI_CONTEXT.md` 属 Governance / bootstrap manifest（手写），**不由 builder/renderer 生成**。

### Conversation Ingestion 数据流（Commit 5D，独立线，不汇入 stream.jsonl）

```
conversations/inbox/*.json  ──conversation_ingest──┬──▶  conversations/raw/<file>.json   (最新全量快照,事实源)
   (用户投放,临时,gitignore)                        ├──▶  conversations/index.jsonl       (catalog,已纳管会话目录)
                                                    └──▶  conversations/quarantine/<file> (解析失败隔离,不丢弃)
                                                              ✗
                                                    （刻意不连 events/stream.jsonl）
```

> conversation 是 **reasoning trace，不是 ContextEvent 事实源**：增量纳管只更新 raw 快照与 catalog，
> **不进入** `events/stream.jsonl`、不自动抽 Decision。同一 `conversation_id` 再导出时比对
> `message_count` / `update_time`：无变化 skip，有变化原地更新（保 `first_seen_at`）。

## 用法（落地后）

```bash
python3 -m tools.context.import_chat --source .shanhai-meta/conversations/raw/<file>.json
python3 -m tools.context.decisions          # 加载 registry.jsonl，打印瞬态人读视图（不落盘）
python3 -m tools.context.builder            # project.yaml + registry.jsonl → context/cognition.json
python3 -m tools.context.renderer           # context/cognition.json → context/current-state.md（人读视图）
python3 -m tools.context.conversation_ingest            # inbox/*.json → raw/ 快照 + index.jsonl catalog
python3 -m tools.context.conversation_ingest --backfill # 把 raw/ 内未登记的历史会话补登记进 catalog
```
