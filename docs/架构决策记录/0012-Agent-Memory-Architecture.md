# ADR 0012：Agent Memory 架构

状态：已采纳
日期：2026-06-23

## 背景

ShanHai 已具备 Agent Runtime（think → act → observe，ADR 0006）、结构化运行记录 `RunResult` / `Step` + `RunStore`（ADR 0008）、Local-first 持久化（ADR 0009）、Evaluation Loop Layer 1（ADR 0010）、真实 Model Provider（ADR 0011），以及 Knowledge Engine 的知识 Schema（`Entity` / `Relation` / `Document`，ADR 0007）。

当前「记忆」能力分散且形态原始：

- `agent-runtime/memory.py` 仅有 `Memory` 抽象 + `InMemoryMemory`（进程内 `remember/recall/history`），是 Phase 0 的占位实现。
- [`AgentContext`](../../services/agent-runtime/shanhai_agent_runtime/context.py) 直接持有 `memory: Memory` 引用，并维护本轮 `observations` / `last_observation`。
- 客观世界知识在 `wiki-engine`（Knowledge Engine），经 `WikiExtractTool` → Service 访问。
- 历史运行轨迹在 `RunStore`，评估指标在 `evaluation`。

下一阶段进入 **Agent Harness 完善**，需要把「记忆」从占位升级为**清晰分层、边界明确、面向长期投资分析场景**的架构。本 ADR **只设计架构，不实现代码**，目标是确定：Memory 与 Knowledge Engine 的边界、三层记忆模型、`MemoryStore` 抽象接口、以及守住「Agent 不直连 DB / 不直连 Memory Storage、记忆经 Service/Tool 访问」的铁律。

约束（AGENTS.md / 协作协议）：

- Memory 是 Harness 基础能力的演进，属架构变更，先 ADR 后实现（本 ADR）。
- 模块独立 + 调用链铁律：Agent 不直接访问数据库、不直接访问 Memory 存储后端，统一走 `Agent → Tool → Service → Storage`。
- Memory 不得重复拥有 Knowledge Engine 的事实来源，不得侵入 Agent Runtime 内部，不得直接调用模型。

## 待决问题（评审重点）

1. **边界**：Memory 与 Knowledge Engine 各自拥有什么？知识（关于世界的客观事实）与记忆（Agent 如何获取/组织/复用信息）如何不重叠、不重复存储？
2. **分层**：Agent 的「记忆」是否单一概念？运行时临时状态、长期客观知识、跨运行经验沉淀，三者语义与生命周期差异巨大，如何分层以既避免早期过度设计、又预留长期演进？
3. **核心抽象**：用什么最小契约表达「一条记忆」「一次记忆读写」，才能既服务当前 Runtime scratchpad，又能平滑承接 Knowledge 检索与 Experience 沉淀？
4. **访问边界**：Agent 如何读写记忆，才能满足「不直连 DB、不直连 Memory Storage」？哪些记忆是进程内状态（可由 Context 直接承载）、哪些必须经 Tool/Service？
5. **未来场景**：如何让这套抽象天然支撑「公司研究历史 / 策略复盘 / Agent 经验积累」？

## 决定（建议方案，待确认）

### 1. Memory 与 Knowledge Engine 的边界

二者是**正交**的两个概念，职责不重叠：

| 维度 | Knowledge Engine（wiki-engine） | Memory（本 ADR） |
|------|--------------------------------|------------------|
| 本质 | 关于**世界**的客观事实 | Agent **如何获取/组织/复用**信息的访问层 |
| 视角 | 共享、客观、与具体 Agent 无关 | Agent 中心、面向一次或多次运行 |
| 内容 | `Entity` / `Relation` / `Document`（公司/行业/政策/事件…） | 运行时草稿、对知识的检索视图、跨运行经验 |
| 事实来源 | **拥有**知识的事实来源（source of truth） | **不拥有**知识，不重复存储 |
| 产生方式 | 外部数据 → 规则/模型抽取编译 | Agent 运行过程产生 / 对既有数据的检索 |

**边界铁律**：

- Knowledge Engine 是世界知识的**唯一事实来源**；Memory 的「知识记忆」层只是对它的**只读检索视图**，经 Service/Tool 访问，**不复制、不另存**一份知识。
- Memory 负责的是「Agent 视角的记忆通路」：本轮想什么（Runtime）、查到什么世界知识（Knowledge）、过去经历过什么（Experience）。
- 一句话：**Knowledge = 世界是什么；Memory = Agent 记得 / 查得 / 学到什么。**

### 2. 三层 Memory 模型（分层演进）

| 层级 | 名称 | 记忆对象 | 生命周期 | 存储后端 | 访问方式 |
|------|------|---------|---------|---------|---------|
| Layer 1 | **Runtime Memory**（运行时记忆） | 单次运行内的草稿：think 规划、历轮 observation、中间变量 | 单次 run，进程内 | 进程内（无持久后端） | `AgentContext` 直接承载（in-process scratchpad，**非外部存储**） |
| Layer 2 | **Knowledge Memory**（知识记忆） | 对世界知识的检索结果（公司画像、产业链、政策、事件…） | 长期、共享、只读 | **复用 Knowledge Engine**（不另存） | 经 `MemoryTool` → `MemoryService` → Knowledge Service |
| Layer 3 | **Experience Memory**（经验记忆） | 跨运行沉淀：研究历史、策略复盘、成败教训 | 长期、可累积、可检索 | 复用 `RunStore` + `evaluation` 产物，必要时新增经验存储 | 经 `MemoryTool` → `MemoryService` → `MemoryStore` |

关键判定：

- **Runtime Memory 是进程内状态，不是外部存储**，因此由 `AgentContext` 直接持有不违反「不直连 Memory Storage」——它本就没有存储后端。这正是当前 `InMemoryMemory` / `observations` 的归位。
- **Knowledge Memory 不新建存储**：知识的事实来源在 Knowledge Engine，Memory 只提供「面向 Agent 的检索入口」，读路径经 Tool/Service 复用 wiki-engine。
- **Experience Memory 优先复用既有沉淀**：运行轨迹已在 `RunStore`（ADR 0008/0009），评估指标已在 `evaluation`（ADR 0010）。经验记忆首先是对这二者的**组织与检索**；当需要结构化「教训/复盘结论」这类新形态时，才在 `MemoryStore` 下新增经验存储实现。

```
                      ┌──────────────────────────────────────┐
   单次运行内（进程内）  │  Layer 1 Runtime Memory               │  ← AgentContext 直接承载
                      └──────────────────────────────────────┘
                                   │ 经 Tool/Service（不直连存储）
                ┌──────────────────┴───────────────────┐
                ▼                                       ▼
   ┌────────────────────────┐            ┌────────────────────────────┐
   │ Layer 2 Knowledge Memory│            │ Layer 3 Experience Memory   │
   │  → Knowledge Engine     │            │  → RunStore + Evaluation     │
   │    (只读检索，不另存)     │            │    (+ 经验存储，按需)         │
   └────────────────────────┘            └────────────────────────────┘
```

本阶段定位：**先确立三层边界与 `MemoryStore` 抽象**；Runtime 归位现有实现，Knowledge/Experience 落「经 Service/Tool 的只读检索 + 复用既有存储」，复杂能力（向量检索、语义召回、经验自学习）留待后续，必要时另开 ADR。

### 3. 核心抽象（最小契约）

在新模块 `services/memory`（`shanhai_memory`）定义最小契约：

- `MemoryScope`（枚举）：`RUNTIME` / `KNOWLEDGE` / `EXPERIENCE`，标识记忆层级。
- `MemoryRecord`（数据）：一条记忆的统一载体。
  - `scope: MemoryScope`、`key: str`、`content: Any`、`tags: list[str]`、`source: str | None`（来源：run_id / document_id / evaluator…）、`created_at: datetime`、`metadata: dict`。
- `MemoryQuery`（数据）：一次检索请求。
  - `scope: MemoryScope`、`text: str | None`、`tags: list[str]`、`agent: str | None`、`limit: int`。
- `MemoryStore`（抽象，见下节）：记忆存储后端接口。
- `MemoryService`：编排层，按 `scope` 把读写路由到对应后端（Knowledge → wiki Service；Experience → RunStore/Evaluation/经验存储），对上提供统一语义。
- `MemoryTool`：包装 `MemoryService`，作为 **Agent 触达 Memory 的唯一通道**（与 `WikiExtractTool` 同构）。

向后兼容：现有 `agent-runtime/memory.py` 的 `Memory` / `InMemoryMemory`（`remember/recall/history`）**保留为 Runtime Memory 的进程内实现**，不被本 ADR 推翻；三层抽象在其之上扩展。

### 4. `MemoryStore` 抽象接口

参照 `RunStore`（ADR 0008）的「抽象 + 进程内默认实现 + 可选 DB 实现」范式，定义：

```
class MemoryStore(ABC):
    def write(self, record: MemoryRecord) -> str: ...          # 写入一条记忆，返回 id
    def read(self, key: str, scope: MemoryScope) -> MemoryRecord | None: ...
    def search(self, query: MemoryQuery) -> list[MemoryRecord]: ...
```

要点：

- **接口与后端解耦**：`MemoryStore` 只描述「记忆怎么读写」，不绑定具体存储。默认 `InMemoryMemoryStore`（进程内、零依赖，供测试与 local-first）；持久实现（如复用 SQLite / Postgres）置于 `services/persistence`，惰性导入、可选依赖，**`memory` 模块不依赖任何 DB 驱动**（沿用 ADR 0008/0009）。
- **Knowledge 层不经 `MemoryStore` 另存**：`MemoryService` 在 `KNOWLEDGE` scope 下把检索委派给 Knowledge Service，而非写入 `MemoryStore`；`MemoryStore` 主要服务 `EXPERIENCE` 的结构化沉淀与 `RUNTIME` 的可选落盘。
- **读多写少**：Knowledge 只读；Experience 以「运行结束后追加 + 复盘检索」为主；Runtime 默认进程内、不落盘（需要时才落）。

### 5. 访问边界（强制，守住铁律）

```
Agent
  │  Runtime Memory：本轮草稿 / 观察
  ├─ context（AgentContext，进程内 scratchpad，非外部存储）
  │
  │  Knowledge / Experience Memory：跨运行 / 持久
  └─ context.use_tool("memory_*", ...) → MemoryTool → MemoryService
                                                          ├─ KNOWLEDGE  → Knowledge Service（wiki-engine，只读）
                                                          └─ EXPERIENCE → RunStore / Evaluation / MemoryStore
```

- **禁止 Agent 直连 DB**：任何持久记忆经 `Tool → Service → Storage`。
- **禁止 Agent 直连 Memory Storage**：Agent 不持有 `MemoryStore` 引用；只持有 `AgentContext`（Runtime）与经授权的 `MemoryTool`。
- **禁止 Memory 重复拥有知识**：Knowledge 层只读委派 Knowledge Engine，不另存事实。
- **禁止 Memory 调用模型 / 侵入 Runtime**：Memory 不调用 Model Router，不修改 Agent Runtime 内部状态；依赖单向 `memory → (agent-runtime 抽象 / wiki-engine 抽象)`，绝不反向。
- **Runtime Memory 例外说明**：进程内 scratchpad 没有存储后端，由 `AgentContext` 直接承载不构成「直连存储」；一旦需要落盘，即转为经 `MemoryStore`，回到 Tool/Service 路径。

### 6. 支撑未来投资分析场景

| 场景 | 落在哪层 | 数据来源 | 说明 |
|------|---------|---------|------|
| **公司研究历史** | Knowledge + Experience | Knowledge Engine（公司画像/产业链）+ RunStore（历次研究运行） | 查「这家公司是什么」走 Knowledge；查「我以前怎么研究过它、结论如何」走 Experience。 |
| **策略复盘** | Experience | RunStore（策略运行轨迹）+ Evaluation（指标）+ 经验存储（复盘结论） | 复盘是对历史运行 + 评估结果的组织与检索，天然落 Experience；结构化「复盘结论」按需写入 `MemoryStore`。 |
| **Agent 经验积累** | Experience | RunStore + Evaluation + 经验存储 | 成败教训、可复用经验沉淀为 `MemoryRecord(scope=EXPERIENCE)`，供后续运行检索，形成「运行 → 评估 → 经验 → 改进」闭环。 |

这套分层使「世界知识」与「Agent 自身经历」互不污染：公司客观事实长存于 Knowledge Engine 并被多 Agent 共享；而某 Agent 的研究路径、策略复盘、教训积累沉淀在 Experience，可被检索复用——直接支撑山海「持续学习的市场认知系统」长期目标。

## 原因

- **正交分层**符合「Knowledge First」与模块独立：知识与记忆各司其职，Knowledge Engine 保持唯一事实来源，Memory 只做「Agent 视角的访问与沉淀」，杜绝知识重复存储与漂移。
- **复用既有抽象**（`RunStore` / Knowledge Service / Evaluation）使 Experience/Knowledge 成为**纯增量**，避免另起炉灶；`MemoryStore` 沿用 ADR 0008/0009 的「抽象 + 进程内默认 + 可选 DB」范式，守住 local-first 与「模块不依赖 DB 驱动」。
- **Tool/Service 唯一通道**与现有 `WikiExtractTool`/`ToolRegistry` 同构，结构上保证「Agent 不直连 DB / 不直连存储」铁律，且对 Agent Runtime 零侵入。
- **Runtime 进程内例外**有明确判据（有无存储后端），既归位现有实现，又不破坏边界定义。
- **缺省最小、演进可期**：先确立边界与契约，复杂检索/自学习留待后续 ADR，契合「架构正确性 > 开发速度」，避免过早复杂化。

## 影响

- 新增模块 `services/memory`（`shanhai_memory`）：`MemoryScope` / `MemoryRecord` / `MemoryQuery` / `MemoryStore`（含 `InMemoryMemoryStore`）/ `MemoryService` / `MemoryTool`。依赖单向：`memory → agent-runtime 抽象 + wiki-engine 抽象`，不依赖 DB 驱动。
- `agent-runtime`：`Memory` / `InMemoryMemory` 归位为 **Runtime Memory** 进程内实现，对外行为不变；`AgentContext` 不新增对 `MemoryStore` 的直接引用（持久记忆经 `MemoryTool`）。**实现阶段**再决定是否将 `MemoryTool` 通过 `ToolRegistry` 授权给特定 Agent。
- `persistence`：**实现阶段**可按需新增持久 `MemoryStore` 实现（复用 SQLite/Postgres），惰性导入、可选依赖。
- `wiki-engine` / `evaluation` / `model-router`：对外行为不受影响；Memory 仅作为只读消费方接入。
- 机密 / local-first：默认 `InMemoryMemoryStore`，无外部依赖即可跑测试；持久后端为增强（沿用 `SHANHAI_RUN_STORE` 思路，必要时引入独立开关）。
- 文档：CHANGELOG / PROJECT_STATE / docs 索引在**实现阶段**同步更新（本 ADR 阶段不写代码）。
- 不触碰本阶段「暂不开发」清单（行情/交易/自动交易/量化/回测）。

## 备选方案（已考虑）

- **把记忆全部塞进 Knowledge Engine**：会让「世界客观事实」与「Agent 主观经历」混存、污染事实来源、破坏共享性，不采纳；坚持二者正交。
- **单层扁平 Memory（不分层）**：无法区分进程内草稿、只读知识、持久经验三种迥异生命周期，导致接口语义混乱、难演进，不采纳。
- **Memory 自建一套知识存储（复制 wiki 数据）**：违反「Knowledge 唯一事实来源」，引入同步/漂移成本，不采纳；Knowledge 层只读委派。
- **Agent 直接持有 `MemoryStore` / 直连 DB 做记忆**：违反「Agent 不直连存储/DB」铁律，不采纳；统一经 `MemoryTool → MemoryService`。
- **本阶段即落地向量检索 / 语义召回 / 经验自学习**：超出当前需要、过早复杂化，不采纳；先定边界与契约，复杂检索另开 ADR。
- **Runtime Memory 也强制经 Tool/Service**：进程内草稿本无存储后端，强制走 Service 徒增开销且无收益，不采纳；以「有无持久后端」为边界判据。
