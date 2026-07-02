# Runtime Kernel v0.7 — Implementation Plan Review（实现计划稿，仅设计，不写代码）

> 状态：**✅ v0.7 Approved（Implementation Plan 批准 + Phase 1/PR-1 解冻 + 5 项 implementation governance 约束已折入 §0.C）→ 执行 Phase 1 / PR-1 Runtime Kernel Skeleton** — Review 批准实现计划并进入 Phase 1；解冻**仅 PR-1**（只创建 package skeleton + contract tests，完成后停 Review Gate，**不继续 PR-2**）。补充 5 项 governance 约束（Q1 PR-1 纯结构提交 / Q2 冻结 5-commit 顺序 / Q3 三包 owner 职责 / Q4 新增 R7 Context Ownership Drift / Q5 Contract Test Layer），已折入 §0.C。
> 状态（历史）：⏳ Implementation Plan Review（v0.7）— 在 v0.6 实现边界冻结之上，确定**如何把 5-Phase 落地为可控的工程交付**：PR 拆分策略 / commit 顺序 / 每个 package 的 owner / migration 风险 / 测试策略。
> 阶段：Phase 1 — Agent Runtime / Runtime Kernel Implementation Plan。
> 前置：[Runtime Kernel v0.6 Implementation Boundary](runtime-kernel-v0.6-implementation-boundary.md) ✅ **Implementation Boundary Frozen（含 7 实现级约束）**；[v0.5 Contract Freeze](runtime-kernel-v0.5-contract-freeze.md) ✅ Contract Frozen（含 6 约束）；[v0.4 Architecture](runtime-kernel-architecture-v0.4.md) ✅ Direction Approved；[v0.3 Context API](runtime-context-api-v0.3.md) ✅ Direction Approved。
> 本轮聚焦五问：**Q1** PR 拆分策略｜**Q2** commit 顺序｜**Q3** 每个 package 的 owner｜**Q4** migration 风险｜**Q5** 测试策略。
> 关联：[ADR 0006 执行模型]、[ADR 0008/0009 RunStore]、[ADR 0018 Artifact](../架构决策记录/0018-Experience-Artifact-Layer-MVP.md)、[DEC-0002](../../.shanhai-meta/decisions/records/DEC-0002-runtime-meta-boundary.md)、[DEC-0004](../../.shanhai-meta/decisions/records/DEC-0004-future-market-cognition.md)、[DEC-0005](../../.shanhai-meta/decisions/records/DEC-0005-context-identity-principle.md)。

---

## 0. 本轮要确定什么 / 不确定什么

| 确定（implementation plan） | 不确定（留 implementation phase / 各 PR 内） |
|---|---|
| **PR 拆分边界**与每个 PR 的范围/不可混入项（Q1） | 各 PR 内具体函数体实现 |
| **commit 顺序**与 commit message 形态（Q2） | 单 commit 的逐行 diff |
| 每个 package 的 **owner / 契约守护边界**（Q3） | 引入第二个人类协作者（个人项目） |
| migration 的**风险清单与缓解措施**（Q4） | migration window 关闭的具体时间点（另议） |
| 每个 Phase 的**测试策略与验收断言**（Q5） | 测试用例的完整代码 |

> 「实现计划」= 在动第一行代码前，确立「怎么切、怎么排、谁守边界、风险在哪、怎么验」；作为 implementation phase 每个 PR 的对照基准。**本轮零代码改动、零建包**。

### 0.A 本轮严守的上游已冻结约束（不得在 v0.7 破坏）

- v0.5 六约束：生命周期 API 非业务 API / 7 个 `*_context` immutable / RuntimeEvent identity envelope / Selection≠Artifact / DAG 禁横向 / Kernel 不读 Meta + Provider 非 Plugin。
- v0.6 七约束：orchestration package ≠ service layer（+types.py）/ 容器 frozen ≠ 递归 frozen（+schema_version）/ run_id 单向 ownership（migration window only）/ ExperienceCandidateProvider（Experience Access Port）/ Evaluation 异步不阻塞 / Agent Runtime Boundary（调用非包含）/ Memory Boundary（经 AgentRuntime）。
- 仍保持（用户冻结）：不实现 Commit 7 独立功能、不接 Memory、不接 Domain Provider、不实现市场能力、**不改变 AgentRunner 核心循环**。

### 0.B 计划的总原则（贯穿 Q1–Q5）

| # | 原则 | 含义 |
|---|---|---|
| 1 | **一 Phase 一 PR，逐 Phase 解冻** | 5 个 Phase = 5 个 PR；每个 PR 单独 Review Gate 批准后才开工下一个（AGENTS.md §5.3） |
| 2 | **additive first，behavior-change last** | 骨架/契约 PR 不改既有行为；唯一行为变更（RunStore migration）单独隔离在 Phase 2 PR |
| 3 | **PR 不跨包混职责** | 一个 PR 的主改动落在单一 package 边界内（migration PR 例外：跨 kernel↔agent-runtime 但仅身份链） |
| 4 | **每个 PR 自带测试 + 文档 + 回归** | 沿用既有节奏（`tests/` + `main()` smoke + CHANGELOG/PROJECT_STATE 更新） |
| 5 | **绿到绿（green-to-green）** | 每个 PR 合入前既有回归全过，不留半成品 |

### 0.C v0.7 Review 补充的 5 项 implementation governance 约束（用户冻结，解冻 PR-1 前折入）

> 在批准 v0.7 实现计划、解冻 Phase 1/PR-1 之前，Review 追加 5 项治理约束。核心立意：**PR-1 的价值是建立 ownership boundary，不是建立功能**；治理点保证未来 review 能判断 boundary 是否被污染。

| # | 约束 | 落点 Q | 核心红线 |
|---|---|---|---|
| G1 | **PR-1 必须保持纯结构提交** | Q1 | 仅允许空接口 / 类型定义 / docstring / placeholder；**禁止实例化** `AgentRunner(...)` / `RunStore(...)` / `ExperienceCandidateProvider(...)`。建立 ownership boundary，非功能。 |
| G2 | **冻结 5-commit 顺序** | Q2 | `Commit1 chore: skeleton → Commit2 feat: lifecycle → Commit3 feat: RuntimeContext → Commit4 feat: RuntimeEvent → Commit5 test: contract tests`。禁单 commit 混 package+model+migration+adapter。 |
| G3 | **三包 owner 负责/不负责矩阵** | Q3 | runtime-kernel / experience-runtime / agent-runtime 各有「负责 vs 不负责」清单（见 Q3.4），跨界即污染。 |
| G4 | **R7 Context Ownership Drift** | Q4 | RuntimeContext 建出后禁被塞执行能力（`model=`/`tools=`/`memory_service=`/`market_strategy`）。判据：字段描述「why/how contextualized」而非「how it executes」。 |
| G5 | **Contract Test Layer** | Q5 | `tests/runtime_kernel/` 下 4 个 contract 测试，测**不可违反的边界**而非实现：lifecycle 禁 `RUNNING→READY`；dependency boundary 禁 `runtime-kernel→experience-artifact` / `→agent-runtime internals`，只允许 `→agent-runtime public interface`。 |

---

## Q1 — PR 拆分策略

### Q1.1 结论：5 个 PR，与 5-Phase 一一对应（冻结拆分边界）

```
PR-1  Phase 1   runtime-kernel skeleton + RuntimeContext model + lifecycle state machine   （新增包，零行为变更）
PR-2  Phase 2   RunStore identity migration（migration window）                              （唯一行为变更，隔离）
PR-3  Phase 3   experience-runtime skeleton（CandidateProvider/Selector/Projection interface）（新增包，纯接口）
PR-4  Phase 4   AgentRunner adapter（RuntimeContext → AgentContext）                          （新增 adapter，循环不变）
PR-5  Phase 5   第一条 E2E 串联                                                              （串联既有件，零新能力）
```

### Q1.2 每个 PR 的范围与「不可混入项」（冻结）

| PR | package 落点 | 范围（做什么） | 不可混入（红线） |
|---|---|---|---|
| **PR-1** | `services/runtime-kernel`（新建） | pyproject + `{__init__,kernel,context,lifecycle,events,types}.py` 骨架；RuntimeContext（Pydantic frozen + schema_version + 7 子模型）；RuntimeState 状态机 | 不接 Agent；kernel.py 方法体留 `NotImplementedError`/占位；**不出现 services/repository/storage**；不直连 database |
| **PR-2** | `services/agent-runtime`（改） | `save_run(self, run, run_id=None)` + DeprecationWarning（migration window）；不改 runner 核心循环 | **不删** `run_id=None` 分支（window 未关闭）；不引入 Kernel 依赖到 agent-runtime（保持反向零依赖）；不改 RunResult/Step |
| **PR-3** | `services/experience-runtime`（新建） | pyproject + `{__init__,selector,projection,candidate_provider,situation}.py`；全部为 ABC/接口契约 | **不实现策略**（无打分算法、无具体来源）；不依赖 runtime-kernel/agent-runtime（禁横向）；不解冻 Commit 7 实现 |
| **PR-4** | `services/runtime-kernel`（改，加 adapter） | `RuntimeContext → AgentContext` 转换；Kernel.execute 委派 `AgentRunner.run(input, runtime_context)` | **不改** AgentRunner 核心循环（Q6.2）；不把 AgentRunner 内聚进 kernel（调用非包含）；不接 Memory |
| **PR-5** | `services/runtime-kernel`（串联） | create→assemble→execute→close 串既有件；Kernel.create mint run_id 贯穿到 save_run | Evaluation **异步、不阻塞**（execute 返回不等 Evaluation，Q5.4）；不接 Domain Provider；`environment_context` 留空 |

### Q1.3 拆分不变量（冻结）

- **PR 顺序即依赖顺序**：PR-1 不依赖任何新包；PR-3 依赖 PR-1（RuntimeContext/Situation 类型）；PR-4 依赖 PR-1+PR-3；PR-5 依赖全部 + PR-2（身份链）。
- **PR-2 可与 PR-3 并行 review**：二者落点不同包、无相互依赖（agent-runtime 改 vs experience-runtime 新建）；但代码合入仍串行（绿到绿）。
- **每个 PR 独立可回滚**：additive PR（1/3/4/5）回滚 = 删包/删 adapter；唯一需谨慎的是 PR-2（行为变更，见 Q4）。
- **不提前合并**：每个 PR 经 Review Gate 批准方可开工与合入（建议 ≠ 批准，AGENTS.md §5.3）。

### Q1.4 PR-1 必须保持纯结构提交（G1，冻结）

> PR-1 的价值是建立 **ownership boundary**，不是建立功能。因此 PR-1 只搭骨架与契约，不引入任何执行行为。

**PR-1 允许**（新增 `services/runtime-kernel/` 下结构）：

```
services/runtime-kernel/
    pyproject.toml
    shanhai_runtime_kernel/
        __init__.py
        kernel.py
        context.py
        lifecycle.py
        events.py
        types.py
```

- 允许：空接口 / 类型定义（Pydantic 模型、枚举）/ docstring / placeholder（方法体 `NotImplementedError`）。
- **禁止**（PR-1 红线，违反即非纯结构）：

```python
AgentRunner(...)               # 禁止：实例化执行引擎
RunStore(...)                  # 禁止：实例化存储
ExperienceCandidateProvider(...)  # 禁止：实例化经验访问口
```

- 判据：PR-1 任何模块不得**实例化/调用**下游能力对象——只能在 docstring/类型注解中**引用名字**作为契约说明。`test_dependency_boundary.py` 以 AST 静态检查守护此红线。

---

## Q2 — commit 顺序

### Q2.1 commit 风格（沿用既有规范，冻结）

沿用 AGENTS.md §5 的 commit 格式 `type(scope): 描述`，scope 用 package/职责轴：`kernel / context / lifecycle / store / experience-runtime / adapter / e2e`。

```
feat(kernel): scaffold runtime-kernel package skeleton
feat(context): add RuntimeContext frozen model with schema_version
feat(lifecycle): add RuntimeState machine with irreversible transitions
test(kernel): cover state machine + frozen invariants
docs(kernel): update CHANGELOG / PROJECT_STATE for Phase 1
```

### Q2.2 各 PR 的 commit 顺序（冻结：先骨架/契约，后测试，再文档）

| PR | commit 顺序 |
|---|---|
| **PR-1** | **（G2 冻结的 5-commit 顺序，见 Q2.4）**：① `chore(runtime-kernel): create package skeleton` ② `feat(runtime-kernel): add lifecycle state machine` ③ `feat(runtime-kernel): add RuntimeContext contract` ④ `feat(runtime-kernel): add RuntimeEvent contract` ⑤ `test(runtime-kernel): add contract tests`（文档更新随 ⑤ 或单列 docs commit） |
| **PR-2** | ① `feat(store)`: `save_run(run, run_id=None)` + DeprecationWarning（migration window）② `test(store)`: 向后兼容矩阵（不传/传 run_id）+ 单向 ownership 断言 ③ `docs`: 标注 migration window only |
| **PR-3** | ① `chore(experience-runtime)`: pyproject + 包骨架 ② `feat(experience-runtime)`: RuntimeSituation ③ `feat(experience-runtime)`: ExperienceCandidateProvider（ABC，Port）④ `feat(experience-runtime)`: ExperienceSelector（ABC）+ ExperienceSelection ⑤ `feat(experience-runtime)`: ExperienceProjection（ABC）⑥ `test` + `docs` |
| **PR-4** | ① `feat(adapter)`: RuntimeContext → AgentContext 转换 ② `feat(kernel)`: execute 委派 AgentRunner.run ③ `test(adapter)`: 转换正确性 + 核心循环回归不变 ④ `docs` |
| **PR-5** | ① `feat(kernel)`: create mint run_id 贯穿 ② `feat(e2e)`: create→assemble→execute→close 串联 ③ `test(e2e)`: 同一 run_id 闭环 + Evaluation 异步不阻塞 ④ `docs`: CHANGELOG/PROJECT_STATE + 标记里程碑 |

### Q2.3 commit 不变量（冻结）

- **每个 commit 可独立编译/导入**：骨架 commit 即便方法占位也须可 `import`（避免半截 commit 破坏回归）。
- **测试 commit 紧跟功能 commit**：同一 PR 内功能在前、测试在后、文档收尾；不把测试拖到下个 PR。
- **不混 scope**：一个 commit 只动一个职责轴（context 的 commit 不顺手改 lifecycle）。
- **migration commit 自带 warning + 测试**：PR-2 的功能 commit 必须同 PR 内带兼容测试，不允许「先改签名、后补测试」跨 commit 留空窗。

### Q2.4 PR-1 冻结的 5-commit 顺序（G2，用户冻结）

```
Commit 1   chore(runtime-kernel): create package skeleton
Commit 2   feat(runtime-kernel):  add lifecycle state machine
Commit 3   feat(runtime-kernel):  add RuntimeContext contract
Commit 4   feat(runtime-kernel):  add RuntimeEvent contract
Commit 5   test(runtime-kernel):  add contract tests
```

- **禁止**一个 commit 同时混入 `package + model + migration + adapter`——否则未来 review 无法判断 boundary 是否被污染。
- 每个 commit 单一职责、可独立 import；migration / adapter **不属于 PR-1**（分别在 PR-2 / PR-4）。

---

## Q3 — 每个 package 的 owner

### Q3.1 owner 的语义（个人项目下的定义，冻结）

本项目是个人项目（git user `shanhai`），**owner ≠ 多人分工**，而是**「该 package 的契约守护边界 + Review 责任轴」**——每个包有明确的「不可被谁破坏」的边界，Review 时按 owner 轴核对。借鉴 CODEOWNERS 思路，但落为**职责归属表**，不引入第二协作者。

### Q3.2 package owner 映射（冻结）

| package | owner 轴（契约守护职责） | 守护的核心契约 | 本计划中被哪些 PR 触碰 |
|---|---|---|---|
| `services/runtime-kernel` | **Orchestration Owner** | orchestrator≠executor、生命周期 API 非业务 API、orchestration package≠service layer、不读 Meta、不拥有状态 | PR-1（建）、PR-4（adapter）、PR-5（串联） |
| `services/agent-runtime` | **Execution Owner** | execution engine、核心循环不变、反向零依赖（不依赖 kernel/experience）、RunStore=Execution Trace Store | PR-2（store migration，**唯一行为变更**） |
| `services/experience-runtime` | **Experience Read Owner** | CandidateProvider=Port、Selector=Intelligence Layer 不学习、Selection≠Artifact、禁横向依赖、全在读侧 | PR-3（建，纯接口） |
| `services/experience-artifact` | **Artifact Production Owner** | Artifact 生产侧、不知消费方式、不反向依赖 runtime-kernel/experience-runtime | **不触碰**（只读被消费） |
| `services/evaluation` | **Learning Owner**（既有生产链） | 事实→经验唯一闸门、只读消费 RunStore、异步不阻塞 Execution | PR-5（仅接入口，异步） |

### Q3.3 owner 边界不变量（冻结）

- **跨 owner 改动须显式标注**：唯一跨 owner 的 PR 是 PR-2（Orchestration 期望前移 run_id ⇄ Execution Owner 改 store），Review 时双轴核对——既不能让 kernel 反向被 agent-runtime 依赖，也不能让 store 自生身份（双 owner，Q4）。
- **新建包的 owner 在建包 PR 即确立**：PR-1 确立 runtime-kernel owner 契约，PR-3 确立 experience-runtime owner 契约（写入各包 README/`__init__` docstring）。
- **owner 不持有下游状态**：Orchestration Owner（kernel）不拥有 RunStore/Artifact 状态（归各自 owner，Q1.2.1）。
- **依赖方向受 owner 守护**：DAG 顶点 = Context Provider，`runtime-kernel → {experience-runtime, agent-runtime}`，两条下游互不依赖；任何 PR 不得引入横向/反向边（v0.5 Q5.5）。

### Q3.4 三包 owner 负责 / 不负责矩阵（G3，用户冻结）

> owner responsibility 落为「负责 vs 不负责」清单——跨界即 boundary 污染，Review 按此核对。

| package | **负责** | **不负责** |
|---|---|---|
| `runtime-kernel` | Runtime lifecycle、RuntimeContext、RuntimeEvent | Experience ranking、Memory、Market cognition、Agent behavior |
| `experience-runtime` | Candidate selection、Projection、Experience reasoning | Runtime execution |
| `agent-runtime` | Agent execution loop、Tool calling、Model interaction | Context assembly、Experience selection |

- runtime-kernel 是 **orchestrator**：只编排 lifecycle / context / event，不做经验排序、不碰 Memory、不做市场认知、不定义 Agent 行为。
- experience-runtime 在 **读侧**：只做候选选择 / 投影 / 经验推理，不执行 Runtime。
- agent-runtime 是 **executor**：只跑执行循环 / 工具 / 模型，不做上下文组装、不做经验选择。
- 写入各包 `__init__` docstring，作为建包 PR 即确立的 owner 契约（Q3.3）。

---

## Q4 — migration 风险

> migration 风险**集中在 PR-2（RunStore identity migration）**——这是 5 个 PR 中**唯一的行为变更**，也是身份链闭环的关键前移。其余 PR 为 additive，风险低。

### Q4.1 风险清单与缓解（冻结）

| # | 风险 | 触发场景 | 缓解措施 | 兜底 |
|---|---|---|---|---|
| R1 | **破坏 agent-runtime v0.2.0 向后兼容** | 既有 `save_run(run)` 调用方（runner `_persist`、既有测试）签名变更后报错 | `save_run(run, run_id=None)` 保留默认值（migration window）；老调用零改动 | 向后兼容测试矩阵（Q5 Phase 2） |
| R2 | **双 owner 身份分裂** | RunStore 仍能内部 mint，与 Kernel.create 形成两个 owner → 同一运行两套 run_id | migration window 内 `run_id=None` 分支带 `DeprecationWarning`；最终形态删除该分支强制 `save_run(run, run_id)`（v0.6 Q3.4） | 单向 ownership 断言测试（给 run_id 时禁内部 mint） |
| R3 | **身份链断裂** | `RuntimeContext.identity_context.run_id` / `RuntimeEvent.run_id` / `RunRecord.run_id` 不一致 | 全链路用同一 run_id；PR-5 e2e 断言四处一致 | 身份链一致性测试（Q5 Phase 5） |
| R4 | **best-effort 落库语义被改变** | migration 顺手改了 `_persist` 的「失败不反噬主流程」语义 | PR-2 不碰 runner._persist 的 try/except 语义；只加可选参数 | 回归既有 RunStore 测试 |
| R5 | **schema_version replay 误读** | 未来 schema 升级后，旧 RunRecord 用新 schema 解释漂移 | RuntimeContext 落库即带 `schema_version:"1.0"`（v0.6 Q2.2）；replay 按当时版本解释 | 本计划只埋点，replay 机制留未来 phase |
| R6 | **migration window 长期滞留** | `run_id=None` 兼容分支变成永久能力 → 双 owner 长期存在 | window 关闭为独立后续 Gate（不在本 5-Phase 内）；DeprecationWarning 持续提示 | 计划中明确标注 window 是临时态 |
| R7 | **Context Ownership Drift** | RuntimeContext 建出后其他模块往里塞执行能力（`model="gpt-x"` / `tools=[...]` / `memory_service=...` / `RuntimeContext.market_strategy`）→ context 退化为执行句柄，混淆 orchestrator/executor 边界 | RuntimeContext review 判据：**「Does this field describe 'why/how this run is contextualized', not 'how this run executes'?」** 答案是「how it executes」则**不允许进入** | `test_context_contract.py` 断言 7 个 `*_context` 字段集合冻结、不含 model/tools/memory_service 等执行字段 |

> **R7 治理判据（G4，用户冻结）**：任何拟加入 RuntimeContext 的字段，必须能回答「描述**为什么/如何被语境化**（why/how contextualized）」——若它描述的是「**这次运行如何执行**（how it executes，即 model/tools/memory/strategy 等执行能力）」，一律拒绝进入。执行能力归 `AgentContext`（执行期句柄），不归 `RuntimeContext`（语境契约）。

### Q4.2 migration 执行护栏（冻结）

- **PR-2 隔离**：migration 单独成 PR，不与骨架/串联混合 → 行为变更可独立 review、独立回滚。
- **分两步、不一步到位**：步骤 1（加可选参数，本 5-Phase 范围）；步骤 2（强制传入、删 None 分支，**window 关闭，另开 Gate**）。本计划只交付步骤 1。
- **不改 RunResult/Step/RunRecord schema**：migration 只改 `save_run` 签名，不动数据模型（v0.4 约束 5 不拆 RunStore）。
- **reverse 依赖红线**：agent-runtime 不得为接收 run_id 而 import runtime-kernel（run_id 是 `str`，透传不需类型依赖）。

---

## Q5 — 测试策略

### Q5.1 测试基线（沿用既有工程约定，冻结）

本机无 pytest，沿用既有约定：每个测试模块用 `main()` + `print("[OK] ...")` + `✅`，以 `PYTHONPATH=. .venv/bin/python -m tests.<module>` 运行；新包测试落 `tests/`，每个 PR 自带测试 + 既有回归全过（绿到绿）。

### Q5.2 各 Phase 测试矩阵（冻结验收断言）

| Phase / PR | 测试目标 | 关键断言 |
|---|---|---|
| **Phase 1 / PR-1** | 骨架可用 + 不变量 | ① 包可 `import`，`__init__` 导出 RuntimeKernel/RuntimeContext/RuntimeHandle ② RuntimeContext 回写抛 `ValidationError`（frozen 容器）③ `schema_version` 默认 `"1.0"` ④ 状态机合法迁移通过、非法迁移（`RUNNING→ASSEMBLING`）抛错 ⑤ run_id 仅在 identity_context，其余 context 无 run_id 字段 |
| **Phase 2 / PR-2** | 向后兼容 + 单向 ownership | ① `save_run(run)`（不传）仍工作并产 run_id + 触发 `DeprecationWarning` ② `save_run(run, run_id="x")` 持外部身份、**不**内部 mint（断言返回值==外部值）③ 既有 RunStore 回归（get_run/list_runs）全过 ④ `_persist` best-effort 语义不变（落库失败不反噬） |
| **Phase 3 / PR-3** | 接口契约（纯抽象） | ① CandidateProvider/Selector/Projection 均为 ABC，直接实例化抛 `TypeError` ② 接口签名契约：`select(situation, candidates)→ExperienceSelection`、`project(selection)→view`、`find_by_context/find_applicable` ③ experience-runtime 不 import runtime-kernel/agent-runtime（禁横向，可用 import 静态检查断言） |
| **Phase 4 / PR-4** | adapter 正确 + 循环不变 | ① `RuntimeContext → AgentContext` 字段映射正确（identity/task→input，experience_context→只读视图）② AgentRunner 核心循环回归（既有 think/act/observe 测试全过，零变更）③ Kernel 不持有 AgentRunner 成员（调用非包含，可断言无实例属性） |
| **Phase 5 / PR-5** | e2e 闭环 + 异步边界 | ① 同一 run_id 从 create 贯穿到 RunRecord（断言四处 run_id 相等）② `execute()` 返回**不依赖** Evaluation 完成（断言 execute 返回时 Evaluation 未必已执行，异步不阻塞）③ create→assemble→execute→close 状态机走完整合法路径 |

### Q5.3 测试不变量（冻结）

- **每个 PR 测试与功能同 PR 交付**：不允许「先合功能、后补测试」。
- **回归优先**：每个 PR 合入前跑既有全量回归（agent-runtime / experience / experience-artifact / evolution 等），证明零破坏。
- **边界即断言**：v0.5/v0.6 的每条「禁止」尽量落为可执行断言（frozen 回写、非法迁移、ABC 不可实例化、禁横向 import、单向 ownership、异步不阻塞）——让契约可被测试守护，而非仅文档。
- **不引入测试框架**：沿用 `main()`+`print` 风格，不在本阶段引入 pytest（保持与既有一致）。

### Q5.4 Contract Test Layer（G5，用户冻结）

> 重点：**不是测试实现，而是测试不可违反的边界**。PR-1 的 contract 测试单列子目录，与未来 PR 的实现测试分离。

目录结构：

```
tests/
    runtime_kernel/
        test_context_contract.py      # RuntimeContext：frozen 回写抛错 / schema_version 默认 "1.0" / run_id 仅在 identity_context / 字段集合冻结（R7：无 model/tools/memory_service）
        test_lifecycle_contract.py     # RuntimeState：合法链通过 / 非法迁移抛错
        test_event_contract.py         # RuntimeEvent：identity envelope schema（event_id/run_id/timestamp/event_type/payload）
        test_dependency_boundary.py    # AST 静态检查依赖方向（G1 + 横向/反向红线）
```

**lifecycle 必须保证的合法链**（`test_lifecycle_contract.py`）：

```
CREATED → ASSEMBLING → READY → RUNNING → COMPLETED → CLOSED
```

禁止（断言抛错）：`RUNNING → READY`（以及其他逆向/跳跃迁移，如 `RUNNING → ASSEMBLING`）。

**dependency boundary 必须守护的方向**（`test_dependency_boundary.py`，CI 加，沿用 `test_artifact_bridge.py` 的 AST 模式）：

```
禁止： runtime-kernel → experience-artifact
禁止： runtime-kernel → agent-runtime internals
只允许： runtime-kernel → agent-runtime public interface
```

附加（G1）：断言 PR-1 源码不出现 `AgentRunner(...)` / `RunStore(...)` / `ExperienceCandidateProvider(...)` 的**实例化/调用**（纯结构提交）。

---

## D. 五问实现计划冻结清单

| Q | 冻结项 | 结论 |
|---|---|---|
| Q1 | PR 拆分策略 | **5 PR ↔ 5 Phase**；additive first、behavior-change（PR-2 migration）隔离；PR 不跨包混职责；各 PR 范围 + 红线明确 |
| Q2 | commit 顺序 | 每 PR：骨架/契约 → 功能 → 测试 → 文档；`type(scope): 描述` 风格；每 commit 可独立 import；不混 scope |
| Q3 | package owner | Orchestration（kernel）/ Execution（agent-runtime）/ Experience Read（experience-runtime）/ Artifact Production（experience-artifact）/ Learning（evaluation）；owner=契约守护轴；跨 owner（PR-2）双轴核对 |
| Q4 | migration 风险 | 集中 PR-2；R1–R6 风险清单 + 缓解 + 兜底；migration window only（步骤 1）；window 关闭另开 Gate；不改数据模型；reverse 依赖红线 |
| Q5 | 测试策略 | 沿用 `main()`+`print` 基线；5-Phase 验收断言矩阵；边界即断言；回归优先；每 PR 自带测试；**Contract Test Layer**（G5，`tests/runtime_kernel/` 4 文件） |

> **v0.7 Review 追加（G1–G5，§0.C）**：G1 PR-1 纯结构提交（禁实例化下游）｜G2 冻结 5-commit 顺序（Q2.4）｜G3 三包 owner 负责/不负责矩阵（Q3.4）｜G4 R7 Context Ownership Drift 治理判据（Q4.1）｜G5 Contract Test Layer（Q5.4）。

---

## E. 实现 Phase 解冻顺序（v0.7 获批后逐 Phase 批准）

| Phase | PR | 解冻前置 | 第一批代码？ |
|---|---|---|---|
| Phase 1 | PR-1 runtime-kernel skeleton + RuntimeContext + lifecycle | **v0.7 计划获批** | ✅ **第一批代码** |
| Phase 2 | PR-2 RunStore identity migration | PR-1 合入 + 兼容测试设计确认 | 否（行为变更，单独批准） |
| Phase 3 | PR-3 experience-runtime skeleton（接口） | PR-1 合入（依赖 RuntimeContext/Situation 类型） | 否 |
| Phase 4 | PR-4 AgentRunner adapter | PR-1 + PR-3 合入 | 否 |
| Phase 5 | PR-5 第一条 E2E | PR-1～PR-4 + PR-2 全部合入 | 否 |

> 每个 Phase = 一次独立 Review Gate：**完成上一 PR → 提出下一 PR 计划 → Review → 批准 → 开工**（AGENTS.md §5.3）。**v0.7 已获批：解冻 Phase 1（PR-1）作为第一批代码；后续 Phase（PR-2～PR-5）仍逐个解冻，本轮不进入 PR-2。**

### E.1 PR-1 Definition of Done（用户冻结）

**必须存在**：

```
services/runtime-kernel package
    kernel.py
    context.py
    lifecycle.py
    events.py
    types.py
```

**必须提供**（最小 contract）：`RuntimeKernel`、`RuntimeContext`、`RuntimeEvent`、`RuntimeState`。

**必须测试**（`tests/runtime_kernel/`，G5）：`import boundary`、`state transition`、`context immutability`、`event schema`。

**明确禁止**（PR-1 范围外）：

```
no AgentRunner integration   no RunStore change      no Experience Runtime
no Memory                    no Domain Provider      no ArtifactReader
```

> DoD 满足 = PR-1 完成 → 停 Review Gate（**不继续 PR-2**）。

---

## F. 非目标 / 约束（继续遵守，保持 Review Gate）

- **本轮范围 = 仅 Phase 1 / PR-1**：只创建 runtime-kernel package skeleton + contract tests（纯结构，禁实例化下游）；**完成后停 Review Gate，不进入 PR-2**。
- **仍保持（用户冻结）**：additive first / behavior change last；不改 AgentRunner 行为、不改 RunStore identity、不实现 Selector、不实现 Projection、不恢复 Commit 7 ArtifactReader、不接 Memory、不接 Domain Provider、不实现市场能力、**不改变 AgentRunner 核心循环**。
- 不引入 Vector / Graph / Retrieval / embedding / 市场 regime / 用户偏好建模 / Memory 持久化写入 / pytest 框架。
- 不破坏 v0.5 六约束、v0.6 七约束与既往不变量：ExperienceEvent append-only、outcome 不改 decision、Artifact 不覆盖 Event、Agent 只读 Experience、Meta↔Runtime 分离（DEC-0002）、身份原则（DEC-0005）、市场认知 gating（DEC-0004）、agent-runtime v0.2.0 契约。
- ADR 0018 维持 **MVP Contract Established**，**不 Finalize**。

---

## G. 下一步（v0.7 已获批，执行 Phase 1 / PR-1）

1. ✅ v0.7 实现计划 + 5 项 governance 约束（G1–G5，§0.C）获批。
2. **执行 Phase 1 / PR-1 = 第一批代码**：只创建 runtime-kernel package skeleton（kernel/context/lifecycle/events/types）+ `tests/runtime_kernel/` contract tests；纯结构、禁实例化下游（G1）；按 Q2.4 冻结的 5-commit 顺序提交。
3. PR-1 满足 E.1 DoD 后 **停 Review Gate**，不进入 PR-2；后续 Phase（PR-2～PR-5）仍逐个解冻批准（建议 ≠ 批准）。

> 当前完成状态：✅ Context Foundation Frozen｜✅ Conversation Ingestion｜✅ Experience Artifact Production Chain｜✅ RuntimeContext Direction Approved｜✅ Runtime Kernel Architecture v0.4 Direction Approved｜✅ Runtime Kernel v0.5 Contract Frozen（含 6 约束）｜✅ Runtime Kernel v0.6 Implementation Boundary Frozen（含 7 实现级约束）｜✅ **Runtime Kernel v0.7 Implementation Plan Approved（含 5 项 governance 约束 G1–G5）**｜🔓 **Phase 1 / PR-1 Runtime Kernel Skeleton 已解冻 — 执行中（不进入 PR-2）**。

> **本轮执行 = 仅 PR-1**：创建 package skeleton + contract tests（纯结构，禁实例化 AgentRunner/RunStore/ExperienceCandidateProvider）；不改 RunStore/AgentRunner、不实现 Selector/Projection、不接 Memory、不解冻 Commit 7。**PR-1 完成后停 Review Gate。**
