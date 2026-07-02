# Runtime Kernel v0.6 — Implementation Boundary Review（实现边界稿，仅设计，不实现）

> 状态：**✅ Implementation Boundary Frozen（v0.6 方向批准 + 7 实现级约束已折入 §0.B）→ 进入** **[v0.7 Implementation Plan Review](runtime-kernel-v0.7-implementation-plan.md)** — Review 原则批准实现边界，进入边界冻结前补充 7 项实现级约束（含新增 §Q6 Agent Runtime Boundary / §Q7 Memory Boundary），目的是「避免后续建包时出现边界漂移」，已折入本文 §0.B。**仍 Design Only**：不建包、不写代码、不改 RunStore/AgentRunner、不实现 RuntimeContext/Selector、不解冻 Commit 7。**v0.7 Implementation Plan 通过后才进入 implementation phase**（仍逐 Phase 解冻批准，见 §E 5-Phase）。
> 状态（历史）：⏳ Implementation Boundary Review（v0.6）— 冻结**实现边界**（哪些文件存在 / model 形态 / identity 迁移路径 / Experience Runtime MVP 三者关系 / 第一条 end-to-end flow）。
> 阶段：Phase 1 — Agent Runtime / Runtime Kernel Implementation Boundary。
> 前置：[Runtime Kernel v0.5 Contract Freeze](runtime-kernel-v0.5-contract-freeze.md) ✅ **Contract Frozen（含 6 约束）**；[v0.4 Architecture](runtime-kernel-architecture-v0.4.md) ✅ Direction Approved；[v0.3 Context API](runtime-context-api-v0.3.md) ✅ Direction Approved。
> 本轮聚焦七问：**Q1** runtime-kernel package skeleton（哪些文件存在）｜**Q2** RuntimeContext python model（是否 Pydantic）｜**Q3** RunStore identity migration（run_id 如何前移）｜**Q4** Experience Runtime MVP（CandidateProvider / Selector / Projection 三者关系）｜**Q5** 第一条 end-to-end flow（只设计不实现）｜**Q6** Agent Runtime Boundary（Kernel 调用非包含 AgentRuntime，新增）｜**Q7** Memory Boundary（Memory 经 AgentRuntime 访问，新增）。
> 关联：[ADR 0006 执行模型]、[ADR 0008/0009 RunStore]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0004](../../.shanhai-meta/decisions/records/DEC-0004-future-market-cognition.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. 本轮要冻结什么 / 不冻结什么

| 冻结（implementation boundary） | 不冻结（留 implementation phase / 后续 Review） |
|---|---|
| package 骨架的**文件清单与各文件职责**（Q1，含 orchestration package ≠ service layer） | 各文件内函数体、类方法实现 |
| RuntimeContext 的 **model 技术选型与不变量落地方式**（Q2，Pydantic v2 frozen + schema_version；容器 frozen ≠ 递归 frozen） | 各 `*_context` 子字段的完整字段表 |
| RunStore identity migration 的**迁移步骤、兼容契约与单向 ownership**（Q3） | 实际改 `store.py` 的代码（仍 Design Only） |
| Experience Runtime MVP 中 **CandidateProvider / Selector / Projection 三者的职责与调用次序**（Q4） | 三者各自的算法/打分维度/具体来源实现 |
| 第一条 end-to-end flow 的**调用链与身份贯穿路径**（Q5，Evaluation 异步不阻塞） | 该 flow 的可运行代码、异步机制实现 |
| **Agent Runtime Boundary**（Q6，Kernel 调用非包含）/ **Memory Boundary**（Q7，经 AgentRuntime 访问） | adapter 与 Memory 接入实现（留后续 phase） |

> 「冻结实现边界」= 在文档层确立「实现时长什么样、文件怎么摆、身份怎么流」，作为 implementation phase 的对照基准；**本轮零代码改动、零建包**。

### 0.A 本轮严守的 v0.5 已冻结约束（不得在 v0.6 破坏）

- Kernel public API 仅 4 生命周期方法 `create/assemble/execute/close`，**禁业务 API**（v0.5 约束 1）。
- RuntimeContext = **7 个 `*_context`**（identity/task/experience/policy/environment/constraint/metadata），immutable（v0.5 约束 2）。
- RuntimeEvent 须含 **execution identity envelope**，`run_id` **必来自 Kernel**（v0.5 约束 3）。
- Selector 输出 = `ExperienceSelection` **非 Artifact**；`Selector→Selection→Projection→RuntimeContext`（v0.5 约束 4）。
- 依赖图 **DAG，禁横向依赖**，顶点 Context Provider（v0.5 约束 5）。
- Kernel **不读 Meta**；Domain Provider = **Provider 非 Plugin**（v0.5 约束 6）。

### 0.B Review 补充约束（v0.6 边界冻结附带，已折入下文）

Review 原则批准实现边界，进入冻结前补充 **7 项实现级约束**（含 2 条新增 §Q6/§Q7）。理由非推翻设计，而是**避免后续建包时出现边界漂移**：

| # | 约束 | 落点 |
|---|---|---|
| 1 | **runtime-kernel 是 orchestration package，不是 service layer**：禁出现 `services.py / repository.py / storage.py`，禁 `runtime-kernel → database`；**Kernel 不拥有状态**。文件清单补 `types.py`（shared types） | Q1.2 增「orchestration package ≠ service layer」铁律 + 文件清单加 `types.py` |
| 2 | **frozen 只冻结 `RuntimeContext` 容器，不递归冻结 Provider 输出**：`environment_context=MarketContext(...)` 内部 `timestamp/source/confidence` 由 Provider 自管，否则未来 Provider 难扩展；并**新增 `schema_version: "1.0"`**——这是 AI Runtime 不是普通 DTO，Agent replay 需知当时上下文版本 | Q2.2 model 加 `schema_version` + Q2.4 新增「容器冻结 ≠ 递归冻结」 |
| 3 | **run_id ownership 转移必须单向**：`Kernel.create() → run_id → RuntimeContext → AgentRunner → RunStore`；**RunStore 只接受 external identity**，禁 `if no run_id: generate()`（否则双 owner）；`save_run(run, run_id=None)` 只能存在 **migration window**（带 warning），最终应 `save_run(run, run_id)` 强制传入 | Q3.2 标 migration window only + Q3.4 新增「单向 ownership」 |
| 4 | **Reader 不冻结为 `ArtifactReader`（那是具体实现），冻结为 `ExperienceCandidateProvider`（= Experience Access Port）**：未来 Artifact 来源可能是 local artifact store / vector index / graph / external cognition service；推荐流 `CandidateProvider → ExperienceSelector → ExperienceSelection → ExperienceProjection → RuntimeContext`，`Selector = Intelligence Layer` | Q4 全节 Reader → ExperienceCandidateProvider 改名 + Q1.3 文件名同步 |
| 5 | **Evaluation 不应阻塞 Execution（异步）**：`execute() → RuntimeEvent → return result`，然后 `Evaluation async`；Runtime 是执行系统，Evaluation 是学习系统；否则未来交易决策实时链路会被 Experience Evolution 拖慢 | Q5.1 链路标 async 边界 + Q5.4 新增「Evaluation 不阻塞 Execution」 |
| 6 | **新增 Q6 Agent Runtime Boundary**：Kernel **调用** AgentRuntime，**不包含**；正确 `runtime-kernel → agent-runtime`，错误 `runtime-kernel contains AgentRunner` / `runtime-kernel.AgentRunner`；AgentRunner 保持 **execution engine** | 新增 Q6 |
| 7 | **新增 Q7 Memory Boundary**：Memory **不是** `RuntimeContext.memory`、**不是** `Kernel.memory`；正确 `AgentRuntime → Memory Access Interface`；三者不同——RuntimeContext（初始化认知）+ Memory Access（执行时查询）+ Experience Runtime（历史经验选择） | 新增 Q7 |

---

## Q1 — runtime-kernel package skeleton：哪些文件存在？

### Q1.1 现状对账（动笔前盘点既有包风格）

既有包统一风格（如 [agent-runtime](../../services/agent-runtime)、[experience-artifact](../../services/experience-artifact)）：

```
services/<pkg>/
├── pyproject.toml                 （hatchling + pydantic>=2.6，requires-python>=3.11）
└── shanhai_<pkg>/
    ├── __init__.py                （公共导出）
    └── <各职责模块>.py
```

> v0.6 沿用此风格，**不发明新结构**。runtime-kernel 与 experience-runtime 各自是独立 package（v0.4 Q1 选 B、v0.5 Q5）。

### Q1.2 `services/runtime-kernel` 骨架（冻结文件清单）

```
services/runtime-kernel/
├── pyproject.toml                 # name=shanhai-runtime-kernel；deps: pydantic, shanhai-agent-runtime, shanhai-experience-runtime
└── shanhai_runtime_kernel/
    ├── __init__.py                # 导出 RuntimeKernel / RuntimeContext / RuntimeHandle
    ├── kernel.py                  # ⭐ RuntimeKernel：create/assemble/execute/close（orchestrator，4 生命周期方法）
    ├── context.py                 # ⭐ RuntimeContext（7 个 *_context，immutable，Q2）+ RuntimeHandle
    ├── lifecycle.py               # 生命周期状态机：RuntimeState 枚举 + 合法迁移校验（v0.4 Q2 命名态）
    ├── events.py                  # RuntimeEvent identity envelope（event_id/run_id/timestamp/event_type/payload，v0.5 Q3.5）
    └── types.py                   # shared types（RuntimeHandle/RuntimeState 等跨模块共享类型，避免循环 import）
```

| 文件 | 职责 | 明确不放 |
|---|---|---|
| `kernel.py` | `RuntimeKernel` 4 方法编排；委派 `agent-runtime` 执行、委派 `experience-runtime` 选经验 | **不持** AgentRunner/Tool/Model 实例；**不含**业务方法（约束 1）；**不读** Meta（约束 6） |
| `context.py` | `RuntimeContext`（7 个 `*_context`，frozen）+ `RuntimeHandle`（持 run_id+state+装配产物引用） | 不放能力句柄（router/tool/memory 归 AgentContext）；不放 Artifact 原件 |
| `lifecycle.py` | `RuntimeState` 枚举（`CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED`）+ 不可逆迁移校验 | 不放执行逻辑（execute 委派 agent-runtime） |
| `events.py` | `RuntimeEvent` envelope 形态（payload 复用 RunResult/Step，不新造） | 不建 RuntimeEventStore（复用 RunStore，v0.4 约束 5）；run_id 不自生 |
| `types.py` | 跨模块共享类型定义（轻量、无状态、无 IO） | 不放任何 service / repository / 持久化逻辑 |

#### Q1.2.1 runtime-kernel = orchestration package ≠ service layer（采纳 0.B 约束 1）

冻结一条**包形态铁律**：runtime-kernel 是**编排包（orchestration package）**，不是**服务层（service layer）**。Kernel 编排生命周期，但**不拥有任何状态**——状态归各下游（RunStore 归 agent-runtime，Artifact 归 experience-artifact）。

```
❌ 禁止（runtime-kernel 退化为 service layer → 拥有状态 → 直连 database）：
   runtime-kernel/
     ├── services.py        # ✗ 业务服务层
     ├── repository.py      # ✗ 数据仓储
     └── storage.py         # ✗ 持久化
   runtime-kernel ──► database     # ✗ Kernel 直连存储

✅ 正确（orchestration package，无状态，只编排）：
   runtime-kernel/{kernel, context, lifecycle, events, types}.py
   runtime-kernel ──► agent-runtime（委派执行，状态落 RunStore）
   runtime-kernel ──► experience-runtime（委派选经验，读 Artifact）
```

| runtime-kernel **不拥有** | 状态归属 |
|---|---|
| 运行记录 / RunStore | **agent-runtime**（执行侧落库，Q3） |
| Artifact / 经验资产 | **experience-artifact**（生产侧） |
| database 连接 / 仓储 | 无——Kernel 不直连任何存储（约束 1） |
| 任何 `services.py/repository.py/storage.py` | 不存在此类文件（编排包负空间） |

> 与 v0.5 Q1.4「生命周期 API 非业务 API」、v0.4 Q1.3「orchestrator≠executor」一脉相承：Kernel 不持执行能力（不 executor）、不持业务语义（不 business）、**也不持状态（不 service layer）**。三条铁律共同把 Kernel 钉死为**纯编排**。

> **不存在的文件（边界负空间，明确不建）**：`selector.py`（归 experience-runtime，Q4）、`store.py`（复用 agent-runtime RunStore，Q3）、`tools.py`/`model.py`（执行能力归 agent-runtime，Q1.3 orchestrator≠executor）、任何 `market_*.py`/`domain_*.py`（领域归 Provider，约束 6）。

### Q1.3 `services/experience-runtime` 骨架（冻结文件清单，Q4 配套）

```
services/experience-runtime/
├── pyproject.toml                 # name=shanhai-experience-runtime；deps: pydantic, shanhai-experience-artifact
└── shanhai_experience_runtime/
    ├── __init__.py
    ├── selector.py                # ExperienceSelector（ABC）+ ExperienceSelection / ScoredArtifact（v0.5 Q4.1）— Intelligence Layer
    ├── projection.py              # ExperienceProjection：Selection → 只读经验视图（v0.5 Q4.3/Q4.4）
    ├── candidate_provider.py      # ExperienceCandidateProvider（ABC，= Experience Access Port）：候选来源抽象（Q4，来源可换）
    └── situation.py               # RuntimeSituation（5 context，v0.3 Q3.1）
```

> 文件名采纳 0.B 约束 4：候选来源抽象**冻结为 `ExperienceCandidateProvider`（Experience Access Port）**，不冻结为 `ArtifactReader`（那只是其中一种具体实现）。未来来源可为 local artifact store / vector index / graph / external cognition service，全部实现同一 Port（详见 Q4.1）。
>
> experience-runtime 依赖 experience-artifact（读 Artifact schema），**不依赖** runtime-kernel/agent-runtime（v0.5 Q5.5 禁横向）。runtime-kernel 在 `assemble` 阶段调用它。

### Q1.4 本轮交付物边界（冻结）

- v0.6 **只冻结上述文件清单与职责**，**不创建任何文件、不写任何代码**。
- 文件创建发生在 implementation phase，且**逐文件解冻批准**（先 runtime-kernel 骨架，再 experience-runtime 骨架）。

---

## Q2 — RuntimeContext python model：是否 Pydantic？

### Q2.1 结论：**是，Pydantic v2 `BaseModel(frozen=True)`**

理由（与既有代码栈一致 + 满足 v0.5 immutability 约束）：

| 维度 | Pydantic v2 frozen（✅ 采纳） | dataclass(frozen=True) | 纯 dict |
|---|---|---|---|
| 与既有栈一致 | ✓ `RunResult/Step/RunRecord/ExperienceArtifact` 全是 pydantic v2（统一） | ◐ 需另引风格 | ✗ 无 schema |
| immutable（v0.5 约束 2/Q2.3） | ✓ `model_config = ConfigDict(frozen=True)` 原生支持 | ✓ frozen 支持 | ✗ 可变 |
| 嵌套校验（7 个 `*_context` 子模型） | ✓ 嵌套 BaseModel 自动校验 | ◐ 手写 | ✗ 无 |
| 可观测/序列化（落 RunStore、归因 run_id） | ✓ `model_dump`/`model_validate` 原生 | ◐ 需 asdict | ◐ 手写 |
| identity 合规（DEC-0005） | ✓ 子模型分层强制「身份归 identity_context」 | ◐ | ✗ |

### Q2.2 model 形态（契约示意，非实现）

```python
# shanhai_runtime_kernel/context.py（契约示意，本轮不实现）
from pydantic import BaseModel, ConfigDict

class _FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)   # immutable：仅冻结本容器，不递归冻结 Provider 输出（Q2.4）

class IdentityContext(_FrozenModel):    ...   # run_id 等稳定标识符（DEC-0005）
class TaskContext(_FrozenModel):        ...   # 做什么/为何做/期望什么
class ExperienceContext(_FrozenModel):  ...   # 经 Projection 的只读经验视图（非 Artifact 原件）
class PolicyContext(_FrozenModel):      ...   # 步数/阈值/超时（v1 可空）
class EnvironmentContext(_FrozenModel): ...   # 领域信号注入点（v1 可空，DEC-0004 gating）
class ConstraintContext(_FrozenModel):  ...   # 运行边界（经 ContextProjection，不放 Meta 原件）
class MetadataContext(_FrozenModel):    ...   # created_at/status（可变信息，非身份）

class RuntimeContext(_FrozenModel):
    schema_version:      str = "1.0"          # ⭐ 上下文 schema 版本（AI Runtime / Agent replay，采纳 0.B 约束 2）
    identity_context:    IdentityContext
    task_context:        TaskContext
    experience_context:  ExperienceContext
    policy_context:      PolicyContext      | None = None
    environment_context: EnvironmentContext | None = None
    constraint_context:  ConstraintContext  | None = None
    metadata_context:    MetadataContext
```

> **`schema_version` 为何是必填字段（采纳 0.B 约束 2）**：RuntimeContext 是 **AI Runtime 的运行时上下文，不是普通 DTO**。未来 Agent replay / 离线复盘需要知道「当时这次运行的上下文是哪个 schema 版本」——schema 会随领域 Provider、context 子字段演化而升级，replay 必须按当时版本解释快照，否则旧 run 用新 schema 解释会语义漂移。`schema_version` 随 RuntimeContext 一同冻结进快照、随 RunRecord 落库。v1 固定 `"1.0"`。

### Q2.3 model 不变量落地方式（冻结）

| v0.5 不变量 | v0.6 落地方式 |
|---|---|
| immutable（约束 2） | `ConfigDict(frozen=True)`；Agent 拿到的是只读实例，**对 RuntimeContext 容器字段**回写抛 `ValidationError`（容器级，见 Q2.4） |
| 身份归 identity_context（DEC-0005） | `run_id` 仅出现在 `IdentityContext`，其余 context **不得**含 run_id 字段 |
| 不含 Meta 原件（约束 6/DEC-0002） | `constraint_context` 字段类型限定为投影视图模型，**禁** `dict` 直塞 cognition.json |
| 不含资产原件（约束 4） | `experience_context` 持投影视图模型，**禁**引用 `ExperienceArtifact` 存储对象 |
| 子字段可扩展 | 各 `*_context` 子模型内部字段可加；**顶层 7 个 context 冻结不增减**（`schema_version` 为元字段，不计入 7 个 context） |

> **`metadata` 命名收口**：v0.5 已把可变信息统一为 `metadata_context`（不再是平铺 `metadata`）。v0.6 落地为独立 `MetadataContext` frozen 子模型——「frozen 的 metadata」指**装配后该快照不再变**，运行态的变化进 AgentContext，不回写。

### Q2.4 容器冻结 ≠ 递归冻结 Provider 输出（采纳 0.B 约束 2）

冻结一条**冻结粒度铁律**：`frozen=True` 只冻结 **RuntimeContext 容器本身**（顶层 7 个 `*_context` 引用 + `schema_version` 装配后不可重绑定），**不强制递归冻结 Provider 注入对象的内部可变性**。

```
✅ 冻结：RuntimeContext container
        （顶层字段引用在装配后不可换、不可增减；这是 immutability 的语义边界）

❌ 不强制：all nested object recursively immutable
        （未来 environment_context=MarketContext(...) 内部 timestamp/source/confidence
          由 Market Provider 自己管理生命周期；强制递归 frozen 会让 Provider 难扩展）
```

| 层级 | 冻结策略 | 理由 |
|---|---|---|
| **RuntimeContext 容器** | **强制 frozen**（顶层引用 + schema_version 不可变） | 这是 v0.5 约束 2 immutability 的语义边界——Agent 不能换掉装配好的上下文结构 |
| 各 `*_context` 子模型 | frozen（runtime-kernel 自有的 7 个子模型，本包定义） | 本包定义的认知装配快照，应只读 |
| **Provider 注入的领域对象**（如 `MarketContext`） | **不强制递归 frozen**，由 Provider 自管 | `timestamp/source/confidence` 等是 Provider 的内部状态语义，runtime-kernel 不应越界强加 frozen，否则未来 Provider 难扩展（采纳 0.B 约束 2） |

> 关键区分：immutability 约束的是「**Kernel 装配出的认知结构不可被 Agent 篡改**」（容器级），不是「**Provider 产出的领域数据内部不可变**」（那是 Provider 的内部契约，归 Provider）。这与 v0.5 Q6.2「Domain Provider = Provider 非 Plugin，提供输入不改行为」一致：Provider 拥有自己产出对象的生命周期，runtime-kernel 只把它**作为只读引用**纳入容器。

---

## Q3 — RunStore identity migration：run_id 如何前移？

### Q3.1 现状与目标（对账）

```
现状（[store.py](../../services/agent-runtime/shanhai_agent_runtime/store.py)）：
    InMemoryRunStore.save_run(run: RunResult) -> str:
        run_id = uuid.uuid4().hex          # ← 身份在「运行后落库」时才诞生（滞后）

目标（v0.4 Q3.4 / v0.5 Q3.4，已批方向）：
    run_id = kernel.create()               # ← 身份在「运行前 create」诞生（前置，闭环必要条件）
    save_run(run, run_id=run_id)           # ← RunStore 从 create identity 变 persist identity
```

### Q3.2 迁移步骤（冻结迁移边界，**本轮不改代码**）

分两步，**向后兼容、不破坏 agent-runtime v0.2.0 契约**；但 `run_id=None` **只能存在于 migration window**（采纳 0.B 约束 3，详见 Q3.4）：

```python
# 步骤 1（migration window only）：RunStore.save_run 增可选 run_id 参数（向后兼容）
def save_run(self, run: RunResult, run_id: str | None = None) -> str:
    if run_id is None:
        # ⚠️ migration window only：迁移期临时兼容，将在 window 关闭后移除
        warnings.warn(
            "save_run(run) without run_id is deprecated; "
            "run_id must come from Kernel.create() (migration window only)",
            DeprecationWarning,
            stacklevel=2,
        )
        run_id = uuid.uuid4().hex          # 临时回退；最终形态禁止此分支（Q3.4）
    self._records[run_id] = RunRecord(run_id=run_id, result=run)
    return run_id

# 步骤 2：Kernel.create() mint run_id，一路贯穿到 save_run（新链路，最终形态）
run_id = kernel.create(...)                # CREATED 态 mint（唯一 owner）
...                                          # assemble / execute
store.save_run(result, run_id=run_id)       # persist identity（external identity）

# 最终形态（migration window 关闭后）：run_id 强制传入
def save_run(self, run: RunResult, run_id: str) -> str: ...   # 无默认值，禁内部 mint
```

| | 现状 | migration window（步骤 1） | 最终形态（window 关闭后） |
|---|---|---|---|
| `run_id` mint 点 | `save_run` 内（运行后） | 优先 external，缺省时**临时**内部 mint（带 warning） | **唯一** `Kernel.create()`（运行前） |
| RunStore 角色 | **create identity** | 过渡：兼容两种 | **persist identity（only）** |
| `save_run` 签名 | `save_run(run)` | `save_run(run, run_id=None)` + DeprecationWarning | `save_run(run, run_id)`（强制传入） |
| 兼容性 | — | 老调用仍可跑但告警 | 老调用须迁移完毕 |

### Q3.3 迁移不变量（冻结）

- **唯一身份贯穿**：`run_id` 一旦在 `create` mint，`RuntimeContext.identity_context` / `RuntimeEvent.run_id` / `RunRecord.run_id` 必须共用同一值（v0.5 Q3.5 身份链）。
- **不拆 RunStore**：仍是 Execution Trace Store，**不建 RuntimeEventStore**（v0.4 约束 5）。
- **best-effort 落库不变**：`_persist` 失败不反噬主流程（[runner.py](../../services/agent-runtime/shanhai_agent_runtime/runner.py) 现有语义）。
- **解冻顺序**：此迁移在 runtime-kernel 骨架落地后、第一条 e2e flow 之前执行，**单独解冻批准 + 兼容性测试**（列 §E，对应 Phase 2）。

### Q3.4 run_id ownership 转移必须单向（采纳 0.B 约束 3）

冻结一条**身份所有权铁律**：`run_id` 的 owner **唯一是 `Kernel.create()`**，ownership 沿**单向链**向下游传递，**RunStore 永远只接受 external identity，绝不自生**。

```
✅ 单向 ownership（唯一 owner = Kernel）：
   Kernel.create()
        │  mint run_id（唯一诞生点）
        ▼
   RuntimeContext.identity_context（携带 run_id）
        ▼
   AgentRunner（执行时透传 run_id）
        ▼
   RunStore.save_run(run, run_id)   ← 只接受 external identity（persist，不 create）

❌ 禁止（双 owner → 身份分裂）：
   RunStore.save_run:
       if no run_id:
           run_id = generate()       # ✗ RunStore 也能 mint → 两个 owner → 同一次运行可能两套身份
```

| | 单向 ownership（✅） | 双 owner（❌） |
|---|---|---|
| `run_id` 诞生点 | **唯一** `Kernel.create()` | Kernel **和** RunStore 都能 mint |
| RunStore 职责 | **persist identity**（接收 external） | 既 create 又 persist（职责混乱） |
| 风险 | 无——身份从头贯穿 | 直连 RunStore 的运行与经 Kernel 的运行身份语义不一致，归因断裂 |
| `if no run_id: generate()` | **禁止**（最终形态删除该分支） | 存在 → 隐藏第二 owner |

> **migration window 的边界**：Q3.2 步骤 1 的 `run_id=None` 内部 mint 分支**仅为迁移期临时兼容**（带 `DeprecationWarning`），不是长期能力。window 关闭后 `save_run` 必须是 `save_run(run, run_id)`（强制传入，删除内部 mint 分支）——届时 RunStore 回归**纯 persist identity**，Kernel 成为唯一 owner。这与 v0.4 Q3.4 / v0.5 Q3.4「RunStore 从 create identity 变 persist identity」收束到同一终态，但本约束额外钉死「**不得长期保留双 owner**」。

---

## Q4 — Experience Runtime MVP：CandidateProvider / Selector / Projection 三者关系

### Q4.1 三者职责（冻结边界）

> **命名采纳 0.B 约束 4**：候选来源抽象**冻结为 `ExperienceCandidateProvider`（= Experience Access Port）**，**不冻结为 `ArtifactReader`**——`ArtifactReader` 只是该 Port 在「本地 artifact store」场景下的一种具体实现。未来候选来源可能是 vector index / graph / external cognition service，但 Selector 只面向同一个 Port 抽象编程。这让 `Selector = Intelligence Layer` 的语义更清晰：Selector 不关心候选从哪来，只负责推理。

```
ExperienceCandidateProvider   候选来源 Port（抽象）：按情境产出候选池
      │                       实现可换：local artifact store / vector index / graph / external cognition service
      ▼  candidates: Iterable[ArtifactView]
ExperienceSelector            推理（Intelligence Layer）：select(situation, candidates) → ExperienceSelection（打分+排序+top-k，不学习）
      │
      ▼  ExperienceSelection（per-run 决策，非 Artifact）
ExperienceProjection          投影：project(selection) → 只读经验视图（裁剪 rule/expected_outcome/confidence/provenance）
      │
      ▼  experience_context（immutable）
RuntimeContext.experience_context
```

| 组件 | 角色 | 输入 → 输出 | 明确不做 |
|---|---|---|---|
| `ExperienceCandidateProvider` | **Experience Access Port**（候选来源抽象，可换实现） | situation → `Iterable[ArtifactView]` | 不打分、不裁剪、不选择；**不写** Artifact；**不绑定**具体存储（local/vector/graph 由实现决定） |
| `ExperienceSelector` | **Intelligence Layer / reasoning service**（stateless） | `(situation, candidates)` → `ExperienceSelection` | 不读 RuntimeEvent（约束 3）、**不学习**（归 Evolution）、**不产 Artifact**（约束 4）、**不关心候选来源** |
| `ExperienceProjection` | **裁剪/投影**（per-run） | `ExperienceSelection` → 只读视图 | 不改 Artifact、不缓存为跨运行共享 |

> `ArtifactReader` 的定位降级：它不再是冻结的接口名，而是 `ExperienceCandidateProvider` 的**首个具体实现**（local artifact store 场景，对应原 Commit 7）。冻结的是 Port，不是 Reader。

### Q4.2 三者关系铁律（冻结）

- **单向管道**：`CandidateProvider → Selector → Selection → Projection → RuntimeContext`，无反向、无环。
- **Selection ≠ Artifact**（v0.5 约束 4）：Selector 产出 `ExperienceSelection`（per-run 决策对象），经 Projection 才进 RuntimeContext；**任何一环都不回写 Artifact**。
- **read/write 对偶**：CandidateProvider/Selector/Projection 全在「读」侧（消费）；「写」Artifact 归 Evolution（生产）。三者都不属于 Evolution。
- **归属**：三者全部落 `services/experience-runtime`（v0.3 约束 6、v0.5 Q5）；**禁** Projection/Selection 进 `experience-artifact`（生产不知消费方式）。
- **候选来源唯一入口 = Port**：候选只能来自 `ExperienceCandidateProvider`（无论背后是 local/vector/graph/external），**禁 RuntimeEvent 入候选**（v0.5 Q4.2/约束 3）。
- **Selector 面向 Port，不面向实现**：Selector 依赖 `ExperienceCandidateProvider` 抽象，不依赖任何具体来源类——来源更换不影响 Selector（采纳 0.B 约束 4）。

### Q4.3 MVP 范围（冻结：最小但结构正确）

- Selector MVP 即便只有少量打分维度，**结构必须是「打分+排序+top-k」**，非 `filter(==)`（v0.5 Q4.2）。
- CandidateProvider MVP 接口为 `find_by_context / find_applicable`（语义检索意图），**非** `list()`；首个实现走 local artifact store（对应原 Commit 7，仍冻结待解冻），但**接口冻结为 Port 抽象**，未来可加 vector/graph/external 实现而不改 Selector。
- Projection MVP 做字段裁剪即可，不引入 embedding/vector/graph（§F 非目标）。

---

## Q5 — 第一条 end-to-end flow（只设计，不实现）

### Q5.1 目标链路（冻结调用链）

```
kernel.create()
   │  CREATED：mint run_id（身份诞生，Q3）
   ▼
kernel.assemble(handle)
   │  ASSEMBLING→READY：
   │    ExperienceCandidateProvider → ExperienceSelector.select → ExperienceSelection → Projection（Q4）
   │    装配 RuntimeContext（schema_version + 7 个 *_context，frozen，Q2）
   ▼
RuntimeContext（immutable，run_id 在 identity_context）
   │
   ▼
kernel.execute(context)
   │  RUNNING→COMPLETED：委派 AgentRunner.run(input, runtime_context)（agent-runtime 执行）
   ▼
RunResult / Step  →  RuntimeEvent（envelope：run_id 来自 Kernel，v0.5 Q3.5）
   │  collect 段：save_run(result, run_id=run_id) 落 RunStore（Q3）
   │
   ├──────────────► return result（execute 同步返回，执行链路到此结束，Q5.4）
   │
   ╎ （异步、非阻塞，采纳 0.B 约束 5）
   ▼
Evaluation（services/evaluation，只读消费，事实→经验闸门）
   │  判定：这次运行是否构成可学习经验？
   ▼
ExperienceEvent → Candidate → Promotion → ArtifactBuilder
   ▼
Artifact（资产，回流候选池，下次被 CandidateProvider 读取 ↺）

kernel.close(handle)
   │  CLOSED：释放 per-run 资源（含 Projection 视图）
```

### Q5.2 身份贯穿（闭环验证点，冻结）

```
Kernel.create() ─► run_id ─► RuntimeContext.identity_context ─► RuntimeEvent.run_id ─► RunRecord.run_id
                                                                                            │
                                            Context ─► Execution ─► Experience（同一 run_id 归因）▼ 闭环
```

> 第一条 e2e flow 的**验收标准**（implementation phase 用）：同一 `run_id` 能从 `create` 一路追到 `Evaluation` 消费的 `RunRecord`，证明 `Context → Execution → Experience` 按同一身份闭环（v0.5 Q3.5）。

### Q5.3 本 flow 明确不做（冻结边界）

- **不接 Evaluation 实现**：本 flow 只设计到「RuntimeEvent → Evaluation 入口」，Evaluation/Evolution/ArtifactBuilder 已是既有生产链（commit 2d91873/fb44bb9），不在本轮改动。
- **不实现任何一环代码**：本轮只冻结调用链与身份路径。
- **不接 Memory / 不接 Domain Provider**：`environment_context` 在 v1 留空（DEC-0004 gating）。
- **不解冻 Commit 7**（ExperienceCandidateProvider 的 local artifact store 实现）。

### Q5.4 Evaluation 不阻塞 Execution（采纳 0.B 约束 5）

冻结一条**执行/学习解耦铁律**：**Runtime 是执行系统，Evaluation 是学习系统，二者必须异步解耦**。`execute()` 在产出 `RuntimeEvent`（落 RunStore）后**立即返回 result**，Evaluation 在执行链路**之外**异步消费，**不得**成为 `execute()` 返回的前置依赖。

```
❌ 禁止（Evaluation 同步阻塞执行 → 实时链路被学习系统拖慢）：
   execute()
      │
      ▼
   Evaluation        ← 同步等待评估完成
      │
      ▼
   return            ← 评估完成才返回 → 交易决策实时链路被 Experience Evolution 拖慢

✅ 正确（Evaluation 异步，不阻塞）：
   execute()
      │
   RuntimeEvent（落 RunStore）
      │
      ├──► return result        ← 执行链路立即返回（同步边界到此结束）
      │
      ▼
   Evaluation（async）          ← 学习系统在执行链路之外异步消费 RunStore
```

| 维度 | Runtime（执行系统） | Evaluation（学习系统） |
|---|---|---|
| 职责 | 把 RuntimeContext 交 Agent 执行，产 RuntimeEvent，落 RunStore，返回 result | 异步消费 RunStore，判定可学习经验，产 ExperienceEvent → Artifact |
| 时延要求 | **实时**（未来交易决策实时链路） | **可延迟**（离线/异步学习，不影响实时） |
| 调用关系 | `execute()` 返回**不依赖** Evaluation 完成 | 在 `execute()` 返回**之后**异步触发 |
| 耦合 | **禁** `execute → Evaluation → return`（同步阻塞） | `RuntimeEvent` 落 RunStore 是二者唯一交接点（解耦边界） |

> 关键收益：未来资本市场实时决策链路（`create → assemble → execute → return`）的时延**只取决于 Agent 执行本身**，不会被 Experience Evolution（评估、晋升、Artifact 构建）拖慢。Evaluation 经 RunStore 作为**解耦队列**异步拉取，二者通过 `run_id` 归因关联（Q5.2），但**时序上完全独立**。本轮只冻结「异步、不阻塞」的边界语义，**不实现异步机制**（队列/任务调度留 implementation phase）。

---

## Q6 — Agent Runtime Boundary（新增，采纳 0.B 约束 6）

> 当前最大的实现风险是 **Kernel 和 AgentRunner 的边界**。本节在 implementation phase 前显式冻结，防止边界漂移。

### Q6.1 结论：Kernel **调用** AgentRuntime，**不包含** AgentRuntime（冻结）

```
✅ 正确（调用 / 依赖）：
   runtime-kernel
        │  execute 阶段委派
        ▼
   agent-runtime（AgentRunner = execution engine，独立 package）

❌ 禁止（包含 / 内聚）：
   runtime-kernel
        contains
   AgentRunner                    # ✗ Kernel 把执行引擎吞进自己

❌ 禁止（命名空间内聚）：
   runtime-kernel.AgentRunner     # ✗ AgentRunner 成为 Kernel 的子类型/成员
```

| | 调用（✅） | 包含（❌） |
|---|---|---|
| 物理位置 | AgentRunner 留 `services/agent-runtime` | AgentRunner 迁入 `runtime-kernel` |
| 依赖方向 | `runtime-kernel → agent-runtime`（单向，v0.5 Q5） | Kernel 内聚执行引擎 → 边界消失 |
| AgentRunner 定位 | **execution engine**（保持不变） | 退化为 Kernel 的内部实现细节 |
| 风险 | 无——orchestrator 与 executor 物理分离 | Kernel 膨胀为「大执行器」，违反 v0.4 Q1.3 |

### Q6.2 与既有铁律的一致性（冻结）

- **承接 v0.4 Q1.3「orchestrator ≠ executor」**：Kernel 只在 `execute` 阶段**委派** `AgentRunner.run(input, runtime_context)`，不持有 AgentRunner 实例为成员、不继承、不内聚。
- **承接 Q1.2.1「orchestration package ≠ service layer」**：Kernel 不拥有状态，也**不拥有执行引擎**——执行引擎是 agent-runtime 的资产。
- **AgentRunner 核心循环不变**：v0.6 不改 AgentRunner 的 `think→act→observe` 循环（用户冻结：「不改变 AgentRunner 核心循环」）。Kernel 接入只通过 `run(input, runtime_context)` 这一委派点，不侵入循环内部。
- **接入方式留 Phase 4**：`RuntimeContext → AgentContext` 的 adapter 在 Phase 4 落地（见 §E），本轮只冻结「调用非包含」的边界。

---

## Q7 — Memory Boundary（新增，采纳 0.B 约束 7）

> Memory 边界虽在 v0.5 / v0.3 已定义，但 implementation 阶段**必须再次冻结**，因为 Memory 极易被误塞进 RuntimeContext 或 Kernel。

### Q7.1 结论：Memory 经 AgentRuntime 访问，**不挂** RuntimeContext / Kernel（冻结）

```
❌ 禁止：RuntimeContext.memory      # ✗ Memory 不是装配期认知，不进只读快照
❌ 禁止：Kernel.memory              # ✗ Kernel 不拥有状态，更不拥有 Memory

✅ 正确：
   AgentRuntime
        │  执行时按需查询
        ▼
   Memory Access Interface（执行期能力句柄，归 AgentContext）
```

### Q7.2 三者不同（冻结：初始化认知 / 执行时查询 / 历史经验选择）

```
RuntimeContext          Memory Access            Experience Runtime
（初始化认知）           （执行时查询）            （历史经验选择）
   │                        │                        │
装配期快照、只读         执行期动态查询           装配期经 Selector 选经验
（assemble 产出）        （AgentRuntime 调用）     （CandidateProvider→Selector→Projection）
   │                        │                        │
   ▼                        ▼                        ▼
进 RuntimeContext        进 AgentContext          进 RuntimeContext.experience_context
（7 个 *_context）       （router/tool/memory）    （只读经验视图）
```

| | RuntimeContext | Memory Access | Experience Runtime |
|---|---|---|---|
| 语义 | **初始化认知**（运行前装配的只读上下文） | **执行时查询**（运行中按需读取的动态记忆） | **历史经验选择**（运行前选中的可复用经验） |
| 时点 | assemble（运行前，一次性快照） | execute（运行中，多次动态） | assemble（运行前，经 Selector） |
| 归属 | runtime-kernel 装配，immutable | **AgentRuntime** 经 Memory Access Interface | experience-runtime 选，投影进 experience_context |
| 可变性 | 只读（frozen，Q2） | 可读可写（执行期能力） | 只读视图（per-run，非 Artifact） |
| 错误归位 | ❌ 不是 `RuntimeContext.memory` | ✅ 经 `AgentRuntime → Memory Access Interface`（v0.3 已定义） | ❌ 不是 Memory（经验非记忆，语义不同） |

### Q7.3 边界不变量（冻结）

- **Memory 不进 RuntimeContext**：RuntimeContext 是装配期只读认知快照（7 个 `*_context`，无 `memory` 字段，Q2）；Memory 是执行期动态能力，归 AgentContext（v0.3 Q4「Memory Access Interface」）。
- **Memory 不进 Kernel**：Kernel 不拥有状态（Q1.2.1），更不拥有 Memory；Kernel 不经手 Memory 访问。
- **Memory ≠ Experience**：Memory（执行时查询的工作记忆）与 Experience（经 Evaluation 验证、经 Selector 选中的可复用经验）是两套不同语义；二者不合并（v0.5 Q4「Memory 不拥有资产，资产归 Experience System」）。
- **本轮不接 Memory**：v0.6 仅冻结边界，**不实现 Memory 接入**（用户冻结：「不接 Memory」）。Memory Access Interface 的接入留未来 phase。

---

## D. 七问实现边界冻结清单

| Q | 冻结项 | 结论 |
|---|---|---|
| Q1 | runtime-kernel package skeleton | `runtime-kernel/{kernel,context,lifecycle,events,types}.py`（**orchestration package ≠ service layer**，禁 services/repository/storage，禁直连 database）+ `experience-runtime/{selector,projection,candidate_provider,situation}.py`；负空间明确 |
| Q2 | RuntimeContext python model | **Pydantic v2 `BaseModel(frozen=True)`** + `schema_version:"1.0"`，7 个 `*_context` 子模型，身份仅在 identity_context；**容器 frozen ≠ 递归 frozen**（Provider 输出由 Provider 自管） |
| Q3 | RunStore identity migration | `save_run(run, run_id=None)` **仅 migration window**（带 DeprecationWarning），最终 `save_run(run, run_id)` 强制传入；**run_id ownership 单向**（唯一 owner = Kernel.create），RunStore 只接受 external identity，禁双 owner |
| Q4 | Experience Runtime MVP | `ExperienceCandidateProvider（Experience Access Port）→ Selector（Intelligence Layer）→ Selection → Projection → RuntimeContext` 单向；Selection≠Artifact；Selector 面向 Port 不面向实现；三者落 experience-runtime，全在读侧 |
| Q5 | 第一条 end-to-end flow | `create→assemble→RuntimeContext→execute(AgentRunner)→RuntimeEvent→return`；**Evaluation 异步不阻塞 Execution**；同一 run_id 贯穿验收 |
| Q6 | Agent Runtime Boundary（新增） | Kernel **调用** AgentRuntime **非包含**；正确 `runtime-kernel → agent-runtime`，禁 `runtime-kernel contains/.AgentRunner`；AgentRunner 保持 execution engine，核心循环不变 |
| Q7 | Memory Boundary（新增） | Memory **不挂** RuntimeContext/Kernel，正确 `AgentRuntime → Memory Access Interface`；三者不同——RuntimeContext（初始化认知）/ Memory Access（执行时查询）/ Experience Runtime（历史经验选择） |

---

## E. 实现顺序（5-Phase，v0.6 冻结；批准后逐 Phase 解冻，不一次全做）

采纳用户冻结的 **5-Phase 实现顺序**——批准后**不一次性全做**，每个 Phase 单独解冻批准。具体 PR 拆分 / commit 顺序 / package owner / migration 风险 / 测试策略由下一 Gate [v0.7 Implementation Plan](runtime-kernel-v0.7-implementation-plan.md) 确定。

| Phase | 范围 | 验证点 | 明确不做 |
|---|---|---|---|
| **Phase 1** | runtime-kernel skeleton + RuntimeContext model（Pydantic frozen + schema_version）+ lifecycle state machine | 骨架可 import，状态机迁移合法性 | **不接 Agent** |
| **Phase 2** | RunStore identity migration（`save_run(run, run_id=None)` migration window）| **run_id ownership 单向**（Kernel 为唯一 owner，RunStore persist identity）+ 向后兼容测试 | 不删除 migration window（window 关闭另议） |
| **Phase 3** | Experience Runtime skeleton：`ExperienceCandidateProvider` / Selector interface / Projection interface | 三者接口契约（Port 抽象） | **不实现策略**（不实现打分算法/具体来源） |
| **Phase 4** | AgentRunner adapter | `RuntimeContext → AgentContext` 转换 | 不改 AgentRunner 核心循环（Q6.2） |
| **Phase 5** | 第一条 E2E | `create → context → agent → event → evaluation` 同一 run_id 闭环 | 不接 Memory / 不接 Domain Provider；Evaluation 异步（Q5.4） |

---

## F. 非目标 / 约束（继续遵守，保持 Review Gate）

- **本阶段只冻结实现边界、不编码、不建包**：不创建 runtime-kernel/experience-runtime 任何文件、不改 RunStore/AgentRunner、不实现 RuntimeContext/Selector、不解冻 Commit 7。
- **仍保持（用户 v0.6 Review 冻结）**：不实现 Commit 7 `ExperienceCandidateProvider` 独立功能、不接 Memory、不接 Domain Provider、不实现市场能力、**不改变 AgentRunner 核心循环**。
- 不引入 Vector / Graph / Retrieval / embedding / 市场 regime / 用户偏好建模 / Memory 持久化写入。
- 不破坏 v0.5 已冻结的 6 约束（§0.A）、v0.6 新增的 7 实现级约束（§0.B）与既往不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）、市场认知 gating（DEC-0004）、agent-runtime v0.2.0 契约。
- ADR 0018 维持 **MVP Contract Established**，**不 Finalize**。

---

## G. 下一步（待批准，不自行执行）

1. 本轮七问实现边界（Q1–Q7）+ 7 实现级约束（§0.B）已折入，标记 **Implementation Boundary Frozen**。
2. 进入下一 Review Gate **[Runtime Kernel v0.7 Implementation Plan Review](runtime-kernel-v0.7-implementation-plan.md)**——目标不是写代码，而是确定：**PR 拆分策略 / commit 顺序 / 每个 package 的 owner / migration 风险 / 测试策略**。
3. v0.7 Implementation Plan 获批后，方可进入 **implementation phase**（按 §E 5-Phase 逐 Phase 解冻批准）。

> 当前完成状态：✅ Context Foundation Frozen｜✅ Conversation Ingestion｜✅ Experience Artifact Production Chain｜✅ RuntimeContext Direction Approved｜✅ Runtime Kernel Architecture v0.4 Direction Approved｜✅ Runtime Kernel v0.5 Contract Frozen（含 6 约束）｜✅ **Runtime Kernel v0.6 Implementation Boundary Frozen（含 7 实现级约束）**｜⏳ **Runtime Kernel v0.7 Implementation Plan Review — 待批准**。

> 当前停在 **Review Gate**，Design Only。不进入代码、不建包、不改 RunStore/AgentRunner、不实现 RuntimeContext/Selector、不解冻 Commit 7。
