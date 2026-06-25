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
├── conversations/             # Conversation Ingestion（Human-AI 协作历史，见下节）
│   ├── inbox/                 #   用户临时投放区（ChatGPT dump，gitignore，非事实源）
│   ├── raw/                   #   Layer 1：原始对话归档（不改 / 不删 / 永久）—— 事实源
│   ├── quarantine/            #   解析失败隔离区（保留问题输入，不丢弃）
│   └── index.jsonl            #   conversation catalog（已纳管会话目录，非 import log）
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
- `conversation_ingest.py` —— Conversation Ingestion：`conversations/inbox/` dump → `conversations/raw/` 快照 + `index.jsonl` catalog（增量纳管，不进 stream.jsonl，禁 LLM，见下节）

## Conversation Ingestion（Commit 5D：Human-AI 协作历史纳管）

把人与 AI（ChatGPT 等）的协作历史增量、安全地纳入 ShanHai Context Foundation。

- **目的**：纳管 Human-AI 协作历史，作为可追溯的推理原料。
- **输入**：`conversations/inbox/`（用户投放 ChatGPT dump；临时、gitignore、非事实源）。
- **输出**：`conversations/raw/`（每个会话一份最新全量快照，事实源）+ `conversations/index.jsonl`（已纳管会话 catalog）。
- **不负责**：reasoning / summarization / decision extraction / embedding / RAG / LLM —— 只搬运 + 登记。

**conversation 是 reasoning trace，不是 ContextEvent 事实源。** 它**不进入** `events/stream.jsonl`：
对话是人-AI 的推理轨迹，本身不是已确认进入认知系统的事件。未来若要从对话抽取决策
（`conversation → analyzer → candidate decision → DecisionRecord`），那是另一个能力，需另行设计。

**index.jsonl 是 conversation catalog（已纳管会话目录），不是 import log。** 增量按会话身份比对，
而非「id 存在即跳过」：同一 `conversation_id` 再次导出时，比对 `message_count` / `update_time`——
无变化则 skip；有变化则原地更新 raw 快照与 catalog（保留 `first_seen_at`，刷新 `last_synced_at`）。

**raw 文件名锚定稳定身份，不编码可变元数据**（见 [DEC-0005 Context Identity Principle](decisions/records/DEC-0005-context-identity-principle.md)）。
命名约定：

```
<source>-<id_prefix>-<slug>.json
```

- `<source>`：来源（如 `chatgpt`）。
- `<id_prefix>`：**统一取身份字符串前 8 位**，规则明确化，避免原生 id 与 hash fallback 长度不一致：
  - 有原生 `conversation_id`（UUID）→ 取前 8 位（首段恰为 8 位 hex）：
    `6a266982-3a08-...` → `6a266982` → `chatgpt-6a266982-山海架构.json`。
  - 无原生 id、回退到内容指纹 → 剥去 `sha256:` 方案前缀后取哈希前 8 位：
    `sha256:a81273bd...` → `a81273bd` → `chatgpt-a81273bd-山海架构.json`。
- `<slug>`：标题派生的人读 hint（可变，**仅辅助阅读，不是身份**）；标题改名不迁移文件
  （文件按 `conversation_id` 原地覆盖，title 变更只刷新 `index.jsonl`）。

> 时间戳（`first_seen_at` / `update_time`）只进 `index.jsonl`，**不进文件名 / 路径**——
> 文件名是 identity locator，不是数据库（DEC-0005）。

工具：[tools/context/conversation_ingest.py](../tools/context/conversation_ingest.py)（stdlib，禁 LLM）。
解析失败的输入移入 `conversations/quarantine/`（不退出、不丢弃），保留问题输入便于调试。

### 如何同步新的聊天历史（操作步骤）

1. **从 ChatGPT 导出** IndexedDB dump（落到 `~/Downloads/`，如 `ConversationsDatabase.json`）。
2. **复制到 inbox 投放区**（文件名随意，ingest 看的是会话内部 `conversation.id`，不看文件名）：

   ```bash
   cp ~/Downloads/ConversationsDatabase.json \
      .shanhai-meta/conversations/inbox/
   ```

3. **跑 ingest**（在仓库根目录）：

   ```bash
   python3 -m tools.context.conversation_ingest            # 正式同步
   python3 -m tools.context.conversation_ingest --dry-run  # 只看会发生什么，不写入
   ```

   输出 `new X, updated Y, skipped Z`。会话身份不变但消息增长 → 原地覆盖 raw 快照（保 `first_seen_at`）；
   全新会话 → 写新 raw 快照 + index 新增一行；无变化 → skip；解析失败 → 移入 `quarantine/`。

> raw/ 内已有的历史会话若未登记 catalog，用 `--backfill` 补登记。
> inbox 用完即清、gitignore 不纳管；正式归档的是 `raw/` 快照与 `index.jsonl`。

## Context Foundation Completed（Commit 5C 封板）

ADR 0000 的认知基础设施（Raw → ContextEvent → Decision Registry → Cognition Snapshot → Human View）
已闭环完成。本层（`.shanhai-meta/`）连同 `tools/context/schema.py` 自此进入 **稳定基础层（stable foundation layer）**。

- **语义冻结**（不是代码冻结）：已有契约 `ContextEvent` / `DecisionRecord` / `CognitionSnapshot` 的语义保持稳定。
- **修改已有契约需 ADR**：对上述结构的字段语义变更，必须先有新的 ADR。
- **扩展不受限**：Runtime 阶段新增 `ObservationEvent` / `MarketEvent` / `DecisionEvent` 等新类型属正常扩展，无需 ADR。
- `cognition.json._metadata.cognition_id`（`sha256:...`）是内容指纹（content identity，非 version）：内容不变则不变，可答「这次启动认知 == 上次?」。

### Context Foundation Status（5D 封板）

ADR 0000 认知基础设施在 5D（Conversation Ingestion + Identity Principle）后正式完成。

**Completed（已完成组件）**

- Meta Context Layer（`.shanhai-meta/` 一等公民上下文层，DEC-0001）
- Cognition Layer（`cognition.json` → `current-state.md` 确定性投影，Commit 5A/5B）
- Decision Registry（`registry.jsonl` + `records/*.md`，可审计性桥，Commit 4）
- Conversation Ingestion（Human-AI 协作历史增量纳管，Commit 5D）
- Identity Principle（稳定身份归标识符、可变属性归元数据，DEC-0005）

**Frozen（语义冻结契约，变更需 ADR）**

- `ContextEvent` / `DecisionRecord` / `CognitionSnapshot`（schema 语义；见 `tools/context/schema.py`）
- 同步登记于 [project.yaml](project.yaml) `frozen`，经 builder/renderer 投影到 `current-state.md` 的 Constraints 段。

**Next**

- Runtime Kernel Design Review（先设计、Review Gate 确认后再实现；当前不写 Runtime 代码）。

> 本状态块是**人写文档**（可自由编辑）。`context/current-state.md` 是派生视图，**不在此手改**——
> 要让机器可读状态变化，改事实源（`project.yaml` / `registry.jsonl`）再重跑 builder/renderer（DEC-0005）。
