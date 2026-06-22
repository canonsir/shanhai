# ADR 0009：Local-first 持久化（默认可落盘，数据库作为增强）

状态：已采纳
日期：2026-06-22

## 背景

ADR 0008 落地了 `RunStore` 抽象与两个实现：

- `InMemoryRunStore`（`agent-runtime`）：进程内、**易失**，运行结束即丢；
- `PostgresRunStore`（`services/persistence`）：可持久化，但**需要 Docker / 外部数据库**。

二者之间存在断层：本机无 Docker（已知限制）时，运行记录运行后即消失，`evaluation` 没有任何可读数据，「运行过程成为一等数据」无从落地。

阶段方针调整（本 ADR 的直接动因）：

> **数据库作为增强能力，不作为开发前置环境。**

即：开发、测试、单机使用应**默认即可持久化**，无需先起任何外部服务；Postgres 退为面向并发 / 规模 / 共享查询场景的**可选增强后端**。

## 待决问题（评审重点）

1. **本地默认后端选型**：SQLite（stdlib，支持查询）、JSONL append-only（最简，查询弱）、还是 DuckDB（分析强，引入依赖）？
2. **新实现的归属**：放 `services/persistence`（与 Postgres 并列），还是因 `sqlite3` 是标准库而放回 `agent-runtime`？
3. **装配方式**：谁来决定「默认用 SQLite」——是否提供工厂 `default_run_store()`，按环境变量选择后端，且不破坏 `agent-runtime` 的存储无关性？
4. **落盘路径与配置**：默认路径、可配置项、是否纳入 `.gitignore`。
5. **Schema 一致性**：是否与 Postgres 复用同一张 `agent_runs` + `agent_steps` 两表模型（仅方言适配）？

## 决定（建议方案，待确认）

1. **本地默认后端选 SQLite（标准库 `sqlite3`，零外部依赖）。**
   - 既能落盘持久化，又支持 `list_runs` 的过滤 / 排序 / limit；
   - 无需任何安装或服务，天然契合 local-first 与「本机无 Docker」的现实；
   - 相比 JSONL：保留按 agent / step / tool 维度查询能力；相比 DuckDB：不引入第三方依赖。

2. **新增 `SqliteRunStore`，放 `services/persistence`（与 `PostgresRunStore` 并列）。**
   - 实现同一 `RunStore` 抽象，复用与 Postgres 一致的 `agent_runs` + `agent_steps` 两表模型，仅做 SQLite 方言适配（`TEXT` 存 JSON、`AUTOINCREMENT`、`?` 占位符）。
   - 尽管 `sqlite3` 是标准库，仍置于持久化层而非 `agent-runtime`，以守住「基础设施模块不含任何具体存储实现」的边界（ADR 0008 §3 同精神）。`agent-runtime` 继续只依赖 `RunStore` 抽象。

3. **提供装配工厂 `default_run_store()`（放 `services/persistence`），实现 local-first 默认。**
   - 按环境变量选择后端：`SHANHAI_RUN_STORE` ∈ `sqlite`(默认) / `memory` / `postgres`；
     - `sqlite` → 路径取 `SHANHAI_SQLITE_PATH`，默认 `./.shanhai/runs.db`；
     - `postgres` → DSN 取 `SHANHAI_PG_DSN`；
     - `memory` → 测试用。
   - **存储选择权属于应用装配层，不属于 `agent-runtime`**：`BaseAgent` / `AgentRunner` 仍只接收注入的 `store`，默认不注入即不落库（零行为变化）；但项目「推荐装配」从「无」升级为「SQLite 落盘」。

4. **数据库定位调整：Postgres 从「持久化前置」降为「增强后端」。**
   - 开发 / 测试 / 单机默认 local-first（SQLite），不再要求 Docker；
   - 当出现多 Agent 并发写、跨进程共享查询、规模化分析需求时，再切换 `SHANHAI_RUN_STORE=postgres` 启用增强后端。

5. **Schema 一致**：SQLite 与 Postgres 共用同一逻辑模型；建表 SQL 各自内置（`init_schema()` 幂等），便于无 Docker 下首跑即自建库表。

## 原因

- 用「同一抽象 + 多后端 + 装配工厂」满足 local-first，同时不破坏 ADR 0008 的模块边界（`agent-runtime` 仍不依赖任何存储实现）。
- SQLite 在「零依赖」「可落盘」「可查询」三者间取得最佳平衡，正好匹配「数据库作为增强、非前置」的方针。
- 复用两表模型让 SQLite ↔ Postgres 切换无缝，evaluation 读取逻辑后端无关。

## 影响

- `services/persistence` 新增 `sqlite_run_store.py`（`SqliteRunStore`）与 `factory.py`（`default_run_store()`）；`__init__.py` 导出。
- `agent-runtime` **不改动**：继续只持有 `RunStore` 抽象与 `InMemoryRunStore`。
- 新增本地落盘目录 `./.shanhai/`，纳入 `.gitignore`。
- `evaluation`（ADR 0010，另起）可直接基于 `RunStore.list_runs` 读取本地 SQLite 数据做度量，无需 DB。
- `PROJECT_STATE.md`「下一步」与「已知限制」相应更新：持久化默认 local-first，Postgres 为增强。

## 备选方案（已考虑）

- **JSONL append-only 单文件**：实现最简、天然可追加，但失去结构化查询（按 agent / status / tool 过滤需全量扫描），与 evaluation 的度量需求不匹配，不采纳。
- **DuckDB**：分析能力强、列存高效，但引入第三方依赖且对当前规模过度，违背「零基础设施」初衷，暂不采纳（规模化分析阶段可再议）。
- **sqlite3 实现放回 `agent-runtime`**：因是标准库看似可行，但会让通用运行时模块内含具体存储实现，侵蚀 ADR 0008 确立的边界，不采纳。
- **默认仍 InMemory，仅文档建议手动接 SQLite**：最省事，但「local-first 持久化」名不副实，运行记录默认仍丢失，不采纳。
