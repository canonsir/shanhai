# ADR 0020：Knowledge Evolution Layer（从「派生信念」进入「可演化、可追溯的解释性认知」）

状态：**提案中（Proposed）** —— 三项框架裁决经 Review Gate 确认（见 §3 D1–D3）；详细契约（Knowledge Object / Revision / Evidence Binding / Evolution Pipeline / Snapshot 边界）以 [M3.4 S4.0 Knowledge Evolution Contract Design](../design/m3.4-knowledge-evolution-contract.md) 承载，待本轮 Review Gate 批准。**本 ADR 属 S4.0 Design Gate，doc-only：不写实现、不接 LLM、不接 iFinD、不改 schema。**
日期：2026-07-01
目标版本：v0.3.0
里程碑：Milestone 3 — Market Intelligence Platform Alpha（S4 = Knowledge Evolution 设计阶段）

关系：**additive 扩展** [ADR 0019（Market Intelligence Context Layer，Contract Accepted + R1）](0019-Market-Intelligence-Context-Layer.md)。ADR 0019 定义了认知四层骨架（Observation → Knowledge → KnowledgeObject → MarketContextSnapshot）与 bitemporal 读能力；本 ADR 细化其中 **KnowledgeObject 层的「解释性信念如何产生、如何绑定证据、如何演化」**，并冻结 LLM 进入认知系统的唯一合法路径。本 ADR **不推翻** ADR 0019 的 D4（Knowledge = deterministic latest-per-key）与 R1-4（ContextAssembler 纯 deterministic），而是在其之上新增一个**并行的解释层**（见 D2）。结构模板承接 [ADR 0016（Experience Evolution Layer）](0016-Experience-Evolution-Layer-Architecture.md) / [ADR 0017（Candidate Lifecycle，Accepted）](0017-Experience-Candidate-Lifecycle-Architecture.md) / [ADR 0018（Artifact Layer MVP）](0018-Experience-Artifact-Layer-MVP.md)——ShanHai 已在 experience 域实现 `Event → Candidate → Validation → Artifact` 的可验证演化，本 ADR 是它在 market-knowledge 域的镜像。

---

## 1. 背景（Context）

ADR 0019（M3.4）已把 ShanHai 从 Persistence 推进到 Cognition 的**事实地基**：

```
Observation（append-only spine，M3.3）
   ↓ 确定性调和（latest per logical_key，D4 / R1-4 assembler）
Knowledge（派生的「当前信念」＝事实层的当前真相）
```

S1–S3 已验证这条事实链**可回放、可复现**：`ObservationReadPort`（InMemory / SQLite parity）能确定性地回答「截至 knowledge_at，关于某 subject，系统看见过哪些 observation」。这是 Knowledge Evolution 得以成立的前提——**如果 Observation 层不能稳定复现，后面的认知演化都是假的**。

但到目前为止，「Knowledge」只是**事实的确定性投影**：

```
Observation：  2026-06-01 公司发布公告（一条事实）
Knowledge：    该 logical_key 的最新值 = 公告内容（latest per key）
```

它**回答不了** ShanHai 的核心问题：

```
「该公告提高了盈利确定性」        ← 这是解释，不是事实
「市场认知从成长股 → 稳定现金流」  ← 这是随时间演化的信念，不是某一天的数据
「AI 为什么在 2026-03 这么判断？」  ← 这是可追溯的认知历史，不是当前快照
```

这些是**解释性信念（interpreted belief）**：它们不能由 observation 确定性投影得到，需要**推理**；它们会**随证据累积而演化**；它们必须**可被追问「凭什么」**。这正是 ShanHai 与普通 AI 股票分析工具的最终差距所在。

## 2. 问题（Problem）

1. **事实 ≠ 解释**：ADR 0019 D4 的「Knowledge」是确定性派生信念（事实层当前真相），但 ShanHai 的认知资产是**解释性信念**（interpretation），二者是不同层、不同生成方式，不能混为一谈。
2. **解释不能是 AI summary storage**：若把 KnowledgeObject 定义成 `{name, industry, valuation, summary}`，它会退化成「AI 摘要仓库」——一个更贵的 daily_stock_analysis。解释性信念必须**每一条都绑定证据（evidence）**，否则无法区分「有据判断」与「幻觉」。
3. **认知会演化，但不能覆盖**：公司认知会从 v1 迭代到 v2、v3（`成长股 → 稳定现金流`）。若用 `CompanyKnowledge.update()` 覆盖，系统就永远回答不了「AI 在 2026-03 为什么那么想」。演化必须是**版本链（append），不是覆盖（overwrite）**。
4. **LLM 进入认知系统的路径极其危险**：`Observation → LLM → Knowledge` 直连会让 LLM 变成事实来源（database），幻觉直接污染认知资产。必须约束 LLM 只做 **reasoner**（对已有证据推理），不做 **database**（凭空生成事实）。
5. **不能推翻已冻结的确定性层**：ADR 0019 R1-4 已冻结「ContextAssembler 第一版纯 deterministic、禁 LLM」。引入解释层不得破坏这条——否则事实回放能力（S1–S3 刚验证的地基）会被非确定性推理污染。

本阶段目标定性：

```
定义「解释性信念如何产生、绑定证据、演化、被追溯」（interpretation contract）
    ——而非——
接入 LLM / 生成公司分析（reasoning implementation）
```

## 3. 决定（Decision）

> **本 ADR 的三项 D1–D3 是经 Review Gate 确认的框架裁决**（用户在 S4.0 启动前经 AskUserQuestion 明确选定）；D4–D8 是在此框架下对 ADR 0019 KnowledgeObject 层的细化冻结。

### D1 — 文档形式：新增 ADR 0020 + S4.0 契约设计稿（框架裁决 ①）

Knowledge Evolution 是 ShanHai 核心价值层，其边界值得独立 ADR 冻结，不混入 M3.4 Context Layer 实现设计（那是 deterministic assembly 的落地文档）。故：

- **本 ADR（0020）** 冻结「层是什么、与 0019 的关系、LLM 归属、不变量」。
- **[S4.0 契约设计稿](../design/m3.4-knowledge-evolution-contract.md)** 承载 5 项细节交付：Knowledge Object contract / Knowledge Revision model / Evidence binding contract / Evolution pipeline / 与 MarketContextSnapshot 的边界。
- 二者均 **doc-only**；实现拆步，逐步经 Review Gate。

### D2 — 层关系：Knowledge Evolution 是**新增并行解释层**，不取代 deterministic Knowledge（框架裁决 ②）

这是本 ADR 与 ADR 0019 关系的核心裁决，**明确不推翻 D4 / R1-4**：

```
Observation（append-only 事实，M3.3）
   │
   ├─(A) 确定性调和 ─────────────► Knowledge（latest per logical_key）
   │     ADR 0019 D4 / R1-4                = 事实层「当前真相」（deterministic，无 LLM）
   │     ContextAssembler 保持纯 deterministic，本 ADR 不改
   │
   └─(B) 解释性演化 ─────────────► KnowledgeObject（interpreted beliefs，evidence-bound，versioned）
         本 ADR（Knowledge Evolution）      = 认知层「解释与信念」（经 reasoning，版本链）
```

- **(A) 与 (B) 并行、互不取代**：(A) 是「系统看到的事实的当前值」，deterministic、可确定性回放；(B) 是「系统对事实的解释」，经推理、可演化、可追溯。二者共享同一 Observation 事实源。
- **R1-4 不被推翻**：deterministic `ContextAssembler` 仍是纯 deterministic（查询/过滤/排序/as_of/provenance/quality），**永不含 LLM**。解释性推理**不进入** ContextAssembler，只发生在 Knowledge Evolution 层的 pipeline 内（见 D6）。
- **D4 四层语义被细化而非改写**：D4 的 KnowledgeObject 槽位（原「主体聚合画像，M3.5 细化」）由本 ADR 明确为「evidence-bound、versioned 的解释性信念聚合」，**否定** `{name, industry, valuation, summary}` 式 AI summary storage。

### D3 — LLM 归属：reasoning-engine（M3.7）；evolution 侧只留 ref 接口 ReasoningPort（框架裁决 ③）

LLM 是**推理器（reasoner）**，不是认知系统的成员。它属于 `reasoning-engine`（ADR 0019 R1 依赖链的 M3.7 层），**不落在 market-intelligence 内**：

```
依赖方向（沿用 ADR 0019 R1，永不反向）：
    runtime-kernel → reasoning-engine → market-intelligence → market-data
                          │
                          └── 实现 ReasoningPort（LLM reasoner，M3.7）
                                        ▲
                                        │ 只留 ref 接口（Protocol），不 import 具体推理器
    market-intelligence 的 Knowledge Evolution ──(注入 ReasoningPort)──┘
```

- **evolution 侧只定义 `ReasoningPort` 抽象**（Protocol，签名仅基元/契约类型），**不 import** reasoning-engine，不接任何具体 LLM。这与 ADR 0011 Model Router「Agent 禁止直接调用具体模型」同源。
- **S4.0 doc-only**：本阶段**不实现** ReasoningPort、**不接** LLM。pipeline 的推理步以**契约占位**表达（参考实现＝deterministic `NoopReasoner`，对齐 ADR 0017 `NoopValidator` / ADR 0018 pending-consumption 模式）。
- 铁律（继承 ADR 0016/0017/0018 并强化）：**LLM 是 reasoner 不是 database**——它对已有 Observation 证据推理，产出**候选修订**；它**不得**成为事实来源、**不得**凭空生成 evidence、**不得**直连 `Observation → LLM → Knowledge`（见 D6）。

### D4 — Knowledge Object = 「evidence-bound、versioned 的解释性信念聚合」，非 AI summary storage

对齐用户冻结形状与 ADR 0017 Candidate 数据模型（结构化假设、来源/证据分离、版本 + 血缘）：

```
KnowledgeObject（以 subject 为中心的解释性认知资产）
├── subject               主体（company / industry / event，复用 market-data SubjectRef）
├── beliefs[]             解释性信念集合（每条 belief 必须绑定 evidence，见 D5）
│     └── Belief
│         ├── statement       结构化信念主张（非自由文本 summary）
│         ├── evidence_refs[] 支撑该信念的 Observation 引用（belief-level，必须非空）
│         ├── confidence      该信念置信度（0~1，随证据演化，非静态）
│         └── polarity/scope  立场 / 适用边界（何时成立、何时失效）
├── evidence_refs[]       对象级证据索引（beliefs 各自 evidence 的并集，引用而非复制）
├── confidence            对象级综合置信度（派生自 beliefs，演化量）
├── version               当前版本号（v1 → v2 → v3，见 D6）
├── previous_version      指向上一版本（版本链锚点，禁覆盖）
└── updated_at            本版本生成时刻
```

铁律：

- **belief 必须有 evidence**：`Belief.evidence_refs` 非空是 KnowledgeObject 的构造前置条件。无证据的信念 = 幻觉，禁止落地。这是本层与 AI summary storage 的分水岭。
- **结构化信念而非 summary**：`statement` 是结构化主张（对齐 ADR 0017 `condition/action/expected_outcome` 精神），`summary` 若保留仅作人类可读派生视图，**不作语义载体、不作匹配/推理依据**（继承 ADR 0016/0017/0018）。
- **引用而非复制**：`evidence_refs` 只持 Observation 身份（`logical_key + content_hash + captured_at`），原始 observation 仍归 market-data 所有（对齐 ADR 0014/0017/0018）。
- **confidence 是演化量**：区别于 observation 的静态 `confidence`，belief/object confidence 随验证证据增减，是 Revision 的输入。

### D5 — Evidence Binding：belief ↔ Observation 的可追溯绑定（源/证据分离）

对齐 ADR 0017 Decision C「`source_refs` 与 `evidence_refs` 分离」：

```
Belief
├── evidence_refs[]   验证证据：支撑/证伪此信念的 Observation（生命周期＝持续累积）
└── (revision 记录)   来源：提出此信念修订的依据（哪条 Candidate Knowledge Change 触发，见 D6）
```

- **evidence_ref = Observation 引用**，锚定到 append-only spine 的具体行（`logical_key + content_hash + captured_at`），因此**可确定性回放**：给定 knowledge_at，能重放「该信念当时依据了哪些 observation」。
- **绑定单向、只读**：KnowledgeObject 引用 Observation，Observation **永不**反向知道 KnowledgeObject（继承 ADR 0019 R1-1 铁律「market-data 永不知 intelligence」）。
- **禁止内嵌 observation 值**：evidence_ref 只持身份，不复制 value（避免事实与解释的双写不一致）。

### D6 — Evolution Pipeline：Observation → Candidate Knowledge Change → reasoning → Knowledge Revision（LLM 唯一合法入口）

冻结 LLM 进入认知系统的唯一路径，**禁止** `Observation → LLM → Knowledge` 直连。镜像 ADR 0016/0017 的 `Event → Candidate → Validation → Promotion → Artifact`：

```
Observation（append-only 事实）
   │ (检测到与现有 belief 相关的新证据 / 冲突 / 缺口)
   ▼
Candidate Knowledge Change      结构化「信念修订候选」（可验证假设，非 summary）
   │ 对齐 ADR 0017 ExperienceCandidate：source_refs / evidence_refs 分离、版本 + lineage
   ▼
Reasoning（经 ReasoningPort ref）  LLM 作为 reasoner 对候选 + 证据推理，产出「拟修订」
   │ D3：只留接口，S4.0 不接 LLM；参考实现＝NoopReasoner
   ▼
Revision Gate                    唯一固化入口：校验 evidence binding，只固化不创作
   │ 对齐 ADR 0017 Promotion Gate / ADR 0018 ArtifactBuilder「纯转换、只固化不创作」
   ▼
Knowledge Revision（vN → vN+1）   新版本 append，evidence-bound，禁覆盖 vN
```

铁律：

- **LLM 只在中间推理步**，且经 `ReasoningPort` 注入；它消费 `Candidate Knowledge Change + Observation 证据`，产出**拟修订提案**，**不写** KnowledgeObject、**不生成** evidence。
- **Revision Gate 是 KnowledgeObject 的唯一写入口**（对齐 ADR 0017 Decision E / ADR 0018 D4）：校验每条 belief 的 evidence_refs 非空且指向真实 observation；**只固化、不创作**——禁止 gate 携带 LLM 生成的自由文本作为信念内容载体（继承「禁 LLM Summary 作 Promotion 内容生成器」）。
- **Candidate Knowledge Change ≠ Revision**：候选是「假设」，Revision 是「经证据校验后固化的版本」。二者不同生命周期，禁跳过 pipeline 直达 Revision。

### D7 — Knowledge Revision = 版本链（append-only），禁止覆盖

对齐用户「Knowledge v1 → v2 → v3，而非 `.update()`」与 ShanHai append-only 精神（ADR 0014/0016/0017）：

```
KnowledgeObject@v1 ──previous_version──◄ KnowledgeObject@v2 ──previous_version──◄ KnowledgeObject@v3
   (evidence 集 E1)                        (evidence 集 E2 ⊇ 变化)                    (evidence 集 E3)
```

- **每次演化生成新版本**（append），旧版本**保留、不删除、不覆盖**——因此永远能回答「AI 在 2026-03 为什么这么判断」（重放 v_k 的 beliefs + evidence_refs）。
- **版本链 + bitemporal 复现**：结合 ADR 0019 D5 的 `knowledge_at`，给定过去某刻可确定性定位「当时生效的 KnowledgeObject 版本」——这是 ShanHai 历史认知回放的第二半（第一半是 S1–S3 的 observation 回放）。
- **禁 `CompanyKnowledge.update()`**：任何原地修改信念内容的 API 一律禁止。

### D8 — 与 MarketContextSnapshot 的边界：Snapshot 引用 Knowledge，Evolution 生产 Knowledge

冻结两层职责，防止 Snapshot 变成 Evolution 的旁路：

| | Knowledge Evolution（本 ADR） | MarketContextSnapshot（ADR 0019 D3/D6） |
|--|--|--|
| 职责 | **生产**演化的解释性信念（版本链） | **引用**某 as_of 冻结的认知态（ref-based） |
| 时间性 | 跨时间演化（v1→v2→v3） | 单点冻结（as_of 一刻） |
| 是否含推理 | 是（经 ReasoningPort） | 否（deterministic assembly，R1-4） |
| 是否可变 | append 新版本 | 不可变，deterministic view（D6，不落库） |

- **Snapshot 引用 KnowledgeObject 的特定版本**（经 `knowledge_refs`，ref-based），**永不触发/内嵌** Evolution 推理。ContextAssembler 保持纯 deterministic（R1-4）。
- **Evolution 永不读/写 Snapshot**：pipeline 只消费 Observation、产出 KnowledgeObject Revision；Snapshot 是下游只读消费者。
- 给定 `as_of.knowledge_at`，Snapshot 确定性地引用「当时生效的 KnowledgeObject 版本」——Evolution 的版本链 + Observation 回放共同保证 Snapshot 可复现。

## 4. 非目标（Non-goals，S4.0 全程禁止）

- ❌ 任何实现代码（本 ADR 与契约稿均 doc-only；实现前继续 Review Gate）
- ❌ 接 LLM / 实现 ReasoningPort / 写 reasoning-engine（属 M3.7）
- ❌ 接 iFinD / Wind / akshare / Tushare Pro（属 Acquisition Layer，M3.6）
- ❌ 改 M3.3 的 9 方法 Repository 契约 / 改 schema / 落 `observation_history` 或 `knowledge_object` 表
- ❌ 推翻 ADR 0019 D4（deterministic Knowledge）/ R1-4（deterministic ContextAssembler）
- ❌ 修改 RuntimeKernel / RuntimeContext / Experience Runtime / Memory / Console 契约
- ❌ Vector / Graph / Retrieval / Knowledge Projection（远期，另立 ADR）

## 5. 依赖方向（Dependency Direction，冻结，沿用 ADR 0019 R1）

```
runtime-kernel ─► reasoning-engine ─► market-intelligence ─► market-data
                       │                      │
                       │                      └─(只读 ref)─► experience（cognition 仅引用 id，不 import）
                       └── 实现 ReasoningPort（M3.7）
                                 ▲
        market-intelligence Knowledge Evolution ─(注入 ReasoningPort Protocol)─┘

# 不变量
- 依赖箭头永不反向；market-data 永不 import intelligence 任何概念（R1-1 铁律）
- Knowledge Evolution 读 Observation 只经 ObservationReadPort（只读端口，签名仅基元类型）
- Knowledge Evolution 不 import reasoning-engine；只依赖 ReasoningPort 抽象（Protocol）
- LLM 唯一入口 = Evolution Pipeline 的 reasoning 步（经 ReasoningPort），禁 Observation→LLM→Knowledge 直连
- KnowledgeObject 唯一写入口 = Revision Gate；beliefs 必须 evidence-bound
- Observation 永不反向知道 KnowledgeObject；Snapshot 永不触发 Evolution 推理
- 版本链 append-only：禁覆盖、禁删除旧版本
```

## 6. 暂缓（S4.0 不做，留待后续 Stage / ADR）

- ReasoningPort 的具体实现与 LLM 接入（M3.7 reasoning-engine）。
- Candidate Knowledge Change 的**具体触发策略**（何种 observation 变化触发候选）与 Revision Gate 的**具体校验规则**（S4.0 仅落契约 + Noop 参考，阈值/策略属后续）。
- KnowledgeObject 持久化（S4.0 仅契约；`knowledge_object` 表 / VectorStore / GraphStore 不引入）。
- Evolution Workflow 编排（检测 → Candidate → reasoning → Gate → Revision 的编排归未来 Workflow）。
- Industry / Event KnowledgeObject 细化、跨主体信念关系图。
- Knowledge Projection（WeKnora / llm-wiki / 向量检索），沿用 ADR 0016 §7 冻结。

## 7. 与既有 ADR 的关系

| ADR | 关系 | 本 ADR 是否要求其改动 |
|-----|------|----------------------|
| 0019（Context Layer） | 本 ADR additive 扩展其 KnowledgeObject 层；**不推翻** D4（deterministic Knowledge）/ R1-4（deterministic Assembler）；沿用 R1 依赖链与 D5 bitemporal | 否（实现期在 0019「与既有 ADR 关系」追加前向引用本 ADR，非本轮） |
| 0018（Artifact MVP） | Revision Gate「只固化不创作」、confidence 演化/快照语义、provenance 引用而非复制，镜像其 ArtifactBuilder/D2/D3 | 否 |
| 0017（Candidate Lifecycle） | Candidate Knowledge Change 镜像 ExperienceCandidate（结构化假设 / source_refs÷evidence_refs / 版本+lineage / Gate 唯一入口） | 否 |
| 0016（Evolution Layer） | market-knowledge 域是 experience 域 `Event→Candidate→Artifact` 的镜像；共享「事实成长为能力/信念」哲学 | 否 |
| 0011（Model Provider） | ReasoningPort「只留接口、不 import 具体推理器」与「Agent 禁直调模型」同源 | 否 |
| 0014（Event Log Lite） | Observation append-only、引用而非复制、只读事实层，为 evidence binding 基础 | 否 |

## 原因

- **事实与解释分层（D2）**：deterministic Knowledge 是事实当前真相，解释性信念是认知资产，二者生成方式不同、演化性不同，必须分层。additive 新增不推翻已验证的确定性回放地基。
- **belief 必须有 evidence（D4/D5）**：这是 ShanHai 与 AI summary storage 的唯一硬边界；无证据的信念不可追溯、不可证伪、等于幻觉。
- **版本链不覆盖（D7）**：认知历史可追溯是 ShanHai 差异化核心（回答「AI 当时为什么这么想」）；覆盖式 update 会永久销毁认知历史。
- **LLM 经 pipeline 而非直连（D3/D6）**：LLM 作 reasoner 而非 database，把幻觉挡在证据校验的 Revision Gate 之外，守住认知资产可信度。
- **复用 experience 域先例（0016/0017/0018）**：ShanHai 已在 experience 域验证 `Candidate → Validation → Promotion → Artifact` 可行，market-knowledge 域直接镜像，降低设计风险。

## 影响

- 新增本规划 ADR（Proposed）+ [S4.0 契约设计稿](../design/m3.4-knowledge-evolution-contract.md)，**不新增/修改任何代码、schema、依赖**。
- 明确 ADR 0019 KnowledgeObject 层的语义（interpreted / evidence-bound / versioned），为其未来实现（里程碑经 Review 确认，reasoning 部分归 M3.7）冻结边界。
- 不触碰 ADR 0019 已冻结的 deterministic Knowledge / ContextAssembler / Snapshot（ref-based / deterministic view）。
- 不触碰本阶段「暂不开发」清单（实时行情 / 交易 / 自动交易 / 量化 / 回测）。

## 备选方案（已考虑）

- **KnowledgeObject = `{name, industry, valuation, summary}`**：退化为 AI summary storage / 更贵的 daily_stock_analysis，不采纳；采用 evidence-bound、versioned 的信念聚合（D4）。
- **`Observation → LLM → Knowledge` 直连**：LLM 变事实来源，幻觉直接污染认知资产，不采纳；改为 `Candidate → reasoning → Revision Gate` 且 belief 必须 evidence-bound（D6）。
- **`CompanyKnowledge.update()` 覆盖式演化**：永久销毁认知历史，回答不了「当时为何这么判断」，不采纳；采用版本链 append（D7）。
- **把解释性推理塞进 ContextAssembler**：推翻 R1-4、污染 deterministic 回放地基，不采纳；解释只发生在 Evolution pipeline，Snapshot 保持 deterministic（D2/D8）。
- **LLM/ReasoningPort 落在 market-intelligence 内**：把推理器拉进认知层，违反 ADR 0011「不直调模型」与 R1 依赖方向，不采纳；LLM 归 reasoning-engine，evolution 侧只留 ReasoningPort 接口（D3）。
- **把 Knowledge Evolution 并入 ADR 0019**：0019 已 Contract Accepted 且聚焦 deterministic Context，混入会范围爆炸并模糊「事实/解释」边界，不采纳；分立本 ADR（D1）。
