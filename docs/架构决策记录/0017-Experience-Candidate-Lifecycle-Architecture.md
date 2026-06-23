# ADR 0017：Experience Candidate Lifecycle 架构（候选经验 → 能力单元的生命周期）

状态：**已采纳（Accepted）** —— Stage 2-b 已实现并经回归测试与 Review Gate 验收（commit `8f001af` / `7312ef1` / `da4016c` / `481690f`）。本 ADR 内容已对齐最终实现。
日期：2026-06-23（Draft）／ 2026-06-23 转 Accepted（Stage 2-b Finalization）
关系：承接 [ADR 0016（Experience Evolution Layer，Proposed）](0016-Experience-Evolution-Layer-Architecture.md) 的层边界，向下细化「Candidate 在层内如何流转」。ADR 0016 定义「层是什么」（四层语义 + Artifact 能力单元定位）；本 ADR 定义「Candidate 从候选经验到能力单元的生命周期」（数据模型 / 状态机 / Validation / Promotion / 模块归属）。不重定义 Candidate，不扩展 ADR 0016。关联 ADR 0013（Feedback）/ 0014（Event Log Lite）/ 0015（Outcome 回填基座）。

## 1. 背景

ADR 0016 冻结了 Experience 四层语义（`ExperienceEvent → ExperienceCandidate → ExperienceArtifact → Knowledge Document`）与「Artifact 是能力单元、非 title/content/embedding」的边界，但**未定义 Candidate 在层内如何流转**。

现状（已实现，ADR 0013 Stage 1）：

- `services/feedback` 内的 `ExperienceCandidate`（`kind/agent/summary/dedup_key/source_run_ids/source_evaluator/signals/occurrences/score/created_at`）已承担「候选经验聚合」职责：**去重 / occurrence 累积 / threshold 晋升入口**。
- `CandidateRegistry`（`dedup_key → Candidate` 进程内去重合并 + 阈值晋升）+ `FeedbackEngine._promote`（达标候选落 `type=lesson` 事件）。

核心差距：当前晋升判据是 `occurrence >= threshold`——它只能证明「**这个问题经常发生**」，不能证明「**这个经验有效**」。`occurrence` 是**频次（frequency）**，不是**有效性（validity）**。真正的学习闭环需要：

```
decision → outcome → validation → candidate confidence
```

**关键定性（本 ADR 的语义基线，区别于上一版 Proposal）**：

- **不**把现有 `ExperienceCandidate` 降格为 `CandidateSignal` 再重建一个新 Candidate。现有 Candidate 虽弱，但已承担候选经验聚合职责，重命名会造成：① 历史语义断裂（ADR 0013 Stage 1 已建立 `Feedback → Candidate → lesson`，演进应是 Candidate **能力增强**而非否定）；② Evolution Layer 与 Feedback **平行体系**割裂。
- **正确演进**：`ExperienceCandidate` 保留为 **Experience Evolution Layer 核心实体**；Feedback 是它的**一种 Producer（来源）**，不拥有 Candidate；现有 `CandidateRegistry` 是 Evolution Layer 的 **Stage 0 实现**，后续是「**演进迁移**」而非「重建」。

```
                    Feedback
                       │
Outcome Evaluation ────┤
                       │
Path Mining ───────────┤
                       │
Human Curated ─────────┤
                       │
                       ▼
              ExperienceCandidate
              (Evolution Layer 核心实体)
                       │
                  Validation     （基于 outcome，非 frequency）
                       │
                  Promotion      （唯一 Artifact 入口）
                       │
                       ▼
              ExperienceArtifact
```

约束（AGENTS.md / 协作协议）：本 ADR 先设计后实现。Draft 阶段不写代码；Stage 2-b 经 Review Gate 逐 commit 实现后转 Accepted。**不改既有 schema/contract**（ExperienceEvent / ExperienceStore append 契约不变，feedback Stage 0 主链路不变）。

## 2. 待决问题（本 ADR 收敛）

1. Candidate 是否为 Evolution Layer 核心实体？Feedback 与它是什么关系？
2. Candidate 数据模型如何区分「来源」与「验证证据」，如何支撑假设演化？
3. Candidate 生命周期有哪些状态？谁触发流转？是否允许回退？Rejected 是否终态？
4. Validation 的判据基础是 outcome 还是 frequency？Validator 的边界是什么？
5. Candidate → Artifact 的晋升门如何定义？是否允许在晋升时生成新知识内容？
6. `CandidateRegistry` 何时、如何从 `feedback` 迁出，且不破坏 Stage 1？

## 3. 决定

### Decision A — `ExperienceCandidate` 是 Experience Evolution Layer 核心实体

`ExperienceCandidate = 可验证经验假设`（**非** Event Summary、**非** Feedback 私有产物）。它是 Evolution Layer 的中心对象，承载「假设 → 验证 → 晋升」的全过程状态。现有 feedback 内的 Candidate 是其 **Stage 0 形态**，后续**能力增强**（结构化假设 + 验证统计 + 生命周期），而非被替换。

### Decision B — Feedback 是 Candidate Producer，不拥有 Candidate

- Candidate 来源多元：`Feedback / Outcome Evaluation / Successful Path Mining / Agent Self Discovery / Human Curated`，并列、可扩展。
- Feedback 退回为「众多 Producer 之一」，只**提出**候选假设，**不拥有**其生命周期与晋升权。
- Producer 与 Candidate 生命周期解耦：Producer 只能产出 `Created` 态候选；状态推进由 Evolution Layer（Validator / Promotion Gate）负责。

### Decision C — Candidate 数据模型（结构化假设 + 来源/证据分离 + 版本）

```
ExperienceCandidate
├── id                  唯一标识（hypothesis id，非 run/event id）
├── source              来源枚举：feedback | outcome_evaluation | path_mining | agent_discovery | human_curated
├── hypothesis          # 假设主体（结构化，非纯文本）
│   ├── context         适用情景（如：A股 / 政策周期 / 行业）
│   ├── condition       触发条件（可组合：政策周期底部 + 成交量突破 + 资金回流）
│   ├── action          建议动作（提高观察权重 / 规避某工具 / 采用某路径）
│   └── expected_outcome 预期结果（未来20交易日上涨概率提升）
├── hypothesis_version  假设版本（v1 → v2 …，配合 lineage 表达 Candidate 演化）
├── source_refs         # 来源（提出此假设的依据，生命周期 = 提出时）
│   ├── event_ids[]     指向 ExperienceEvent
│   ├── candidate_ids[] 指向上游 Candidate（合并/派生）
│   └── external_refs[] 外部来源（人工 curation / 挖掘任务 id）
├── evidence_refs       # 验证证据（生命周期 = 验证过程持续累积）
│   └── validation evidence：指向用于验证的 decision↔outcome 对、评估引用
├── confidence          置信度（0~1，随验证演化，非静态 occurrence）
├── validation_status   生命周期状态（见 Decision C 状态机）
├── validation_stats    success_count / failure_count / window / consistency
├── applicability       适用范围与边界（何时成立 / 何时失效，含反例约束）
├── lineage             血缘（parent_candidate_id / superseded_by / version 链 / promoted_to）
├── created_at
└── updated_at
```

设计铁律：

- **结构化假设而非 summary**：`condition / action / expected_outcome` 三段对齐投资语义，杜绝退化为「LLM Summary → Candidate」。`summary` 若保留仅作人类可读派生视图，不作语义载体。
- **`source_refs` 与 `evidence_refs` 分离**：来源（为何提出此假设）与验证证据（假设被多少真实结果支撑/证伪）是**两个不同概念、不同生命周期**。例：来源＝`FailurePatternRule` 发现「政策底部资金流入后上涨概率增加」；证据＝「20 次历史验证，15 成功 5 失败」。
- **`hypothesis_version` + `lineage.version`**：Candidate 会演化（v1「成交量放大 → 上涨」经验证细化为 v2「成交量放大 + 北向资金流入 → 上涨」）。这是**同一 Candidate 的演化**，非新建 Candidate，避免未来 Artifact 演化困难。
- **引用而非复制**（继承 ADR 0014）：`source_refs / evidence_refs` 只持 id，原始 decision/outcome 仍归 `ExperienceStore` 所有。
- **`confidence` 是演化量**：区别于现有 `score = occurrences`，随 validation 证据增减，是 Promotion 输入。

### Decision C（状态机）— Candidate 生命周期

```
        (Producer 提出假设)
              │
              ▼
          Created
              │  Validator 接管
              ▼
        Evaluating ◄─────────────┐
         │      │                │ (新证据 / 置信度回落，允许回退)
   达标  │      │ 证伪            │
         ▼      ▼                │
    Validated  Rejected          │
         │       │               │
  Promotion      │ context 变化  │
   Gate          │  / 时效失效    │
         ▼       ├──► Archived ──┤ (Reactivated：条件重现 → 重新 Evaluating)
      Promoted   │               │
         │       └──► (保留血缘，不删除)
         ▼
   ExperienceArtifact
   (Candidate → Archived，lineage.promoted_to = artifact_id)
```

状态语义、触发者、回退：

| 状态 | 含义 | 谁触发进入 | 进入条件 |
|------|------|-----------|----------|
| Created | 假设已提出，未验证 | **Producer**（Feedback/Mining/Human…） | 来源产出结构化假设 |
| Evaluating | 持续累积验证证据中 | **Validator**（Evolution Layer，离线/按需） | Created 被 Validator 拾取 |
| Validated | 达到验证标准 | **Validator** | 满足 ValidationPolicy（Decision D） |
| Rejected | 假设被证伪 | **Validator** | 失败率超阈 / 反例过多 |
| Promoted | 通过晋升门，待物化 | **Promotion Gate** | 满足 PromotionPolicy（Decision E） |
| Archived | 历史失效但保留血缘（含晋升后归档 / Rejected 归档） | **系统 / Validator** | Artifact 物化完成 ‖ Rejected 经判定为 context 失效 |

**回退与非终态（投资经验具时效性 / 周期依赖 / 条件变化）**：

- **`Rejected` 不是完全终态**。旧经验失效往往不是「错误」，而是 **context 改变**（例：低利率环境「政策刺激 → 上涨」；高利率环境「政策刺激 → 无反应」）。因此：
  - `Rejected → Archived`：历史失效，**保留知识血缘，禁止删除**。
  - `Archived → Reactivated（→ Evaluating）`：当条件/周期重现时可重新激活验证（保留原 id 与 lineage，记录 version）。
- **允许 `Validated → Evaluating`**：出现新反例 / confidence 跌破阈值时回退，避免假设僵化。
- **允许 `Artifact 被推翻 → 对应 Candidate 回 Evaluating`**：**不删除 Artifact**（append-only 精神），以新增反向证据 + Artifact `evolution history` 记录，并把 Candidate 拉回验证。
- 不变量：状态只能由 **Validator / Promotion Gate / 系统**改写；Producer 只能产 `Created`；**Agent 永不写 Candidate**。

### Decision D — Validator 基于 Outcome，而非 frequency

引入 **Validator** 抽象（Evolution Layer 内，离线/按需，对齐 Feedback 运行形态）：

```
ExperienceStore (decision / outcome 事实)
        │ 只读（list(parent_event_id=...) 取 decision↔outcome 对；list(episode_id=...) 聚合）
        ▼
   Validator ── 消费 evidence ──► ValidationPolicy（可插拔，确定性优先）
        │                              │
        │                        产出 ValidationVerdict
        ▼                              ▼
  更新 Candidate.confidence / validation_stats / validation_status
```

ValidationPolicy 输入维度（**仅定义架构，不实现具体阈值规则**）：成功次数 / 失败案例数量 / 时间窗口 / Outcome 一致性（expected vs 实际）/ 置信度变化趋势 / 适用范围分组。

**Validator 边界（冻结）**：

- **只读 `ExperienceEvent`**（经 `ExperienceStore.list`，Stage 2-a 已具备 `parent_event_id` / `episode_id` 过滤）。
- **不直接修改 Event**（事实层 append-only 不可变）。
- **不调用 Agent**（避免自证循环）。
- **不依赖 Feedback**（Validator 是 Evolution Layer 能力，不绑定任一 Producer）。
- 不直连 DB、不调用模型（确定性优先，与 ADR 0010/0013 同源原则）。

> `Validation != occurrence count` 是 Evolution Layer 与普通 Feedback 的最大区别：`occurrence >= threshold` 只证明「问题常发生」，`decision → outcome → validation → confidence` 才形成「经验是否有效」的真实学习闭环。

### Decision E — Promotion Gate 是 Artifact 唯一入口

```
ExperienceCandidate (Validated)
        + N 次成功验证（success_count ≥ N）
        + 适用范围明确（applicability 非空且边界清晰）
        + 失败率低于阈值（failure_count / total < ε）
        + 置信度达标（confidence ≥ θ）
        │  PromotionPolicy 评估（可插拔）
        ▼
   Promotion Gate ──► ExperienceArtifact（能力单元，ADR 0016 §4.1）
        │
        ▼
   Candidate.status = Archived，lineage.promoted_to = artifact_id
```

**Promotion 约束（冻结）**：

- **Promotion 不生成新的知识内容**。Artifact 是 **`Candidate + validation + lineage` 的稳定能力表示**，只做「相变固化」，不做内容创作。
- **禁止** `Candidate → LLM Summary → Artifact`（否则退化为知识库）。
- **Promotion Gate 是 Artifact 唯一入口**：禁止任何路径绕过 Validation 直达 Artifact。
- **`PromotionDecision` 字段严格锁定为四项**：`approved` / `reason` / `candidate_id` / `validation_snapshot_ref`。**禁止** `artifact` / `artifact_content` / `summary` / `embedding` / `knowledge_document` 等字段——晋升决策只是「是否放行 + 依据引用」，不携带任何被创作的内容。
- Artifact 模型与存储属 ADR 0016 Phase 3 实现范围；本 ADR 仅定义**晋升门的下游接口契约**，不实现 Artifact 层。

### Decision F — `CandidateRegistry` 自 feedback 演进迁移至 Experience Evolution Layer（两阶段）

避免一次迁移破坏 Stage 1，分两阶段：

```
Stage 2-b（本阶段，已实现）：
   保持   services/feedback/CandidateRegistry          （Stage 0 实现不动，Stage 1 主链路不破坏）
   新增   services/experience-evolution/CandidateService   （生命周期入口，多 Producer 经 Proposal 提交候选）
   新增   services/experience-evolution/CandidateRepository（生命周期存储抽象 + InMemoryCandidateRepository）
   旁路   services/feedback/FeedbackProposalAdapter        （feedback candidate → CandidateProposal，单向喂入，不绕过 Service）

Stage 3：
   迁移   CandidateRegistry / CandidateStore / Validator / PromotionGate
   进入   services/experience-evolution
   Feedback 收敛为 Producer，仅经 CandidateService 提交候选
```

- **演进而非重建**：Stage 2-b 不委派、也不改动 feedback 的 `CandidateRegistry`（Stage 0 去重/阈值主链路保持原样）；Evolution Layer 引入**独立的** `CandidateRepository` 抽象承载新生命周期实体的存储，feedback 经 `FeedbackProposalAdapter` 作为众多 Producer 之一**旁路**喂入 `CandidateProposal`。Stage 3 再将 Registry/Store 等真正迁入新层、统一收口。
- 依赖方向（单向，不破坏既有边界）：`experience-evolution → experience(只读事实) + agent-runtime(只读上下文)`；Producer（含 feedback）单向喂入 `CandidateService`，**不反向依赖**（`experience-evolution` 不 import `feedback`，由回归测试 AST 静态校验）。

## 4. 模块归属与依赖方向

```
services/
 ├── experience/              事实层（Event / Store / ingest，ADR 0014/0015，不变）
 ├── feedback/                Candidate Producer 之一（Stage 0 Registry 暂留，Stage 3 迁出）
 │      └── evolution_adapter.py  FeedbackProposalAdapter（feedback candidate → CandidateProposal）
 └── experience-evolution/    本 ADR 新层（Stage 2-b 起，已实现骨架与生命周期契约）
        ├── models.py         （ExperienceCandidate 值对象 + 枚举 + ValidationVerdict：结构化假设 + source/evidence 分离 + version）
        ├── candidate.py      （ExperienceCandidate 实体 + ALLOWED_TRANSITIONS 状态机 + is_allowed_transition）
        ├── repository.py     （CandidateRepository 抽象 + InMemoryCandidateRepository）
        ├── proposals.py      （CandidateProposal：input contract，非 generator）
        ├── producers.py      （CandidateProducer Protocol）
        ├── service.py        （CandidateService：生命周期入口 create/transition/apply_validation/get/list）
        ├── validator.py      （Validator ABC validate(candidate, context)→ValidationVerdict + Reader Protocol + NoopValidator）
        └── promotion.py      （PromotionGate ABC evaluate(candidate)→PromotionDecision + NoopPromotionGate）

# 不变量
- experience-evolution → experience（只读事实）/ agent-runtime（只读上下文）：单向
- experience-evolution 不 import feedback；experience 不 import experience-evolution（AST 静态校验）
- Producer（feedback / mining / human …）→ CandidateProposal → CandidateService.create()：单向喂入
- 状态变更唯一通道 CandidateService.transition() / apply_validation()；调用方禁止 candidate.validation_status = xxx
- Validator 只读 Event，不改 Event、不调用 Agent、不依赖 Feedback、不写 ExperienceStore、不创建 Artifact
- Promotion Gate 是 Artifact 唯一入口；Agent 不写 Candidate / Artifact
```

## 5. 必须保持的不变量（继续冻结）

```
ExperienceEvent ──append-only──► ExperienceCandidate ──validation──► ExperienceArtifact ──► Knowledge Projection (WeKnora / llm-wiki)
```

禁止：

- Artifact 直接覆盖 Event。
- Knowledge Document 反向成为 Experience。
- Agent 写 Candidate / 写 Artifact。
- Vector DB 提前进入核心模型。
- LLM Summary 作为经验来源 / 作为 Promotion 内容生成器。

## 6. 暂缓（Stage 2-b 不做，留待后续 Stage）

- Stage 3 的实际迁移（Registry/Store/Validator/PromotionGate 迁入新层）——Stage 2-b 仅建生命周期入口与接口契约。
- Validator / PromotionGate 的**具体策略实现**（Stage 2-b 仅落接口 + Noop 实现，ValidationPolicy/PromotionPolicy 阈值规则属后续）。
- Candidate 持久化（Stage 2-b 仅 InMemoryCandidateRepository；CandidateDB / VectorStore / GraphStore 不引入）。
- Evolution Workflow 编排（Validator → apply_validation → PromotionGate → transition 的编排归未来 Workflow，CandidateService 不承担编排职责）。
- `ExperienceArtifact` 模型与存储（属 ADR 0016 Phase 3）。
- Vector / Graph / WeKnora / llm-wiki / 自动 Summary / Skill Mutation / Model Distillation（沿用 ADR 0016 §7 冻结，直到 Artifact 模型稳定）。

## 7. 与既有 ADR 的关系

| ADR | 关系 | 本 ADR 是否要求其改动 |
|-----|------|----------------------|
| 0016（Evolution Layer） | 本 ADR 是其 Candidate 生命周期细化；遵循其四层语义与 Artifact 能力单元定位 | 实现期在 0016「与既有 ADR 关系」追加前向引用本 ADR（非本轮） |
| 0015（Outcome 回填基座） | 复用其 `decision → outcome` 事实链与 `list(parent_event_id/episode_id)` 查询作为 Validation 数据基础 | 否 |
| 0014（Event Log Lite） | Validator 只读 Event、不改 schema；Candidate 经 refs 引用 Event | 否 |
| 0013（Evaluation Feedback） | Feedback 收敛为 Candidate Producer；`CandidateRegistry` 两阶段迁出 | 否（0013 Addendum F 已声明演进方向） |
| 0012（Memory） | Agent 仍经 `MemoryTool` 只读 Experience，无 Candidate/Artifact 写路径 | 后续实现期再对齐 |

## 原因

- **演进而非重建**：保留 `ExperienceCandidate` 为核心实体并增强其能力，守住 ADR 0013 Stage 1 的历史语义，避免平行体系；Feedback 自然降为 Producer。
- **来源/证据分离 + 版本**：`source_refs` 与 `evidence_refs` 生命周期不同；`hypothesis_version` 支撑假设演化，避免未来 Artifact 演化困难。
- **Validation 基于 outcome**：把「频次」升级为「有效性」，是 Evolution Layer 区别于普通 Feedback 的本质，兑现真实学习闭环。
- **Rejected 非终态 + Archived/Reactivated**：投资经验具时效与周期依赖，失效多因 context 改变而非错误；保留血缘可在条件重现时复用。
- **Promotion 只固化不创作 + 唯一入口**：防止退化为 RAG 知识库，保证 Artifact 是「Candidate + validation + lineage」的稳定能力表示。
- **两阶段迁移**：先 facade 后迁移，避免一次性迁移破坏 Stage 1。

## 影响

- Stage 2-b（已实现，本 ADR 随之转 Accepted）：新增 `services/experience-evolution`——Candidate 模型（结构化假设 + source/evidence 分离 + version）、状态机（`ALLOWED_TRANSITIONS` + Actor 权限）、`CandidateRepository` 抽象 + `InMemoryCandidateRepository`、`CandidateProposal` 输入契约、`CandidateProducer` 协议、`CandidateService` 生命周期入口（`create/transition/apply_validation/get/list`）、`Validator` 接口（`validate(candidate, context)→ValidationVerdict` + Reader Protocol + Noop）、`PromotionGate` 接口（`evaluate(candidate)→PromotionDecision` + Noop）；`services/feedback` 仅**新增** `FeedbackProposalAdapter`（feedback candidate → CandidateProposal）并加 `shanhai-experience-evolution` 依赖，Stage 0 `CandidateRegistry` 主链路不动。生命周期回归测试 `tests/test_candidate_lifecycle.py` 覆盖 5 个边界用例 + 依赖方向 AST 校验。
- Stage 3（待后续 Review）：`CandidateRegistry/Store/Validator/PromotionGate` 迁入新层，Feedback 收敛为 Producer。
- 不触碰本阶段「暂不开发」清单（行情 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **把现有 Candidate 降格为 CandidateSignal 再重建新 Candidate**：造成历史语义断裂与平行体系，Review 否决；改为保留 Candidate 为核心实体、能力增强。
- **`source_refs` 与 `evidence_refs` 合并为单一 `evidence_refs`**：混淆来源与验证证据两种不同生命周期，不采纳；拆分。
- **无 `hypothesis_version`、假设变更即新建 Candidate**：丢失演化血缘，Artifact 演化困难，不采纳；引入版本 + lineage。
- **`Rejected` 为完全终态、失效即删除**：丢失周期性可复用经验与血缘，不采纳；引入 `Archived/Reactivated`。
- **Promotion 经 LLM 总结生成 Artifact 内容**：退化为知识库，不采纳；Promotion 只固化不创作。
- **一次性把 CandidateRegistry 迁出 feedback**：破坏 Stage 1，不采纳；两阶段（facade → 迁移）。
- **Candidate 生命周期由 Feedback 推进**：把 Evolution 绑死单一来源，不采纳；状态推进归 Validator/Promotion Gate。
