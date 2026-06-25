# Decision Registry（决策注册表）— Layer 2

> 设计依据：[ADR 0000 §D3/§D9](../../docs/架构决策记录/0000-项目元上下文架构.md)
> 这是 ShanHai「认知 → 行为」的桥：`Decision → ADR → Runtime Policy → Agent Behavior`。

回答 AI 最需要的两个问题：**为什么这么设计？哪些方案已被否决？**
Decision 永不替代 Raw（[conversations/raw/](../conversations/raw/)）与
ContextEvent（[events/stream.jsonl](../events/stream.jsonl)）；它是从事实流人工提炼出的认知层。

## 文件布局

```
decisions/
├── README.md          # 本文件
├── registry.jsonl     # 唯一结构事实源：DecisionRecord（JSON，每行一条，机器读）
└── records/           # 人读叙述：每条决策一份 markdown（背景/决定/原因/备选/否决/回链）
    ├── DEC-0001-meta-context-layer.md
    ├── DEC-0002-runtime-meta-boundary.md
    ├── DEC-0003-context-first-then-platform.md
    ├── DEC-0004-future-market-cognition.md
    └── DEC-0005-context-identity-principle.md
```

## 两层分工（不维护重复事实，ADR 0000 §D9）

| 文件 | 角色 | 读者 | 写入方式 |
|---|---|---|---|
| `registry.jsonl` | **唯一结构事实源** | 机器（Commit 5 builder 直接 `json.loads` 逐行读） | 人工提炼 append；schema 见 `tools/context/schema.py` 的 `DecisionRecord` |
| `records/DEC-*.md` | 人读叙述 / 解释层 | 人 / AI | 人工撰写，与 jsonl 同 id 一一对应 |

> 不再派生 `registry.yaml`：它既非事实源也非最终文档，会产生第三份状态、未来必然与 jsonl
> 漂移不一致，违反 ADR 0000「不维护重复事实」。`registry.jsonl`（机器读）+ `records/*.md`
> （人读）已覆盖「机器 + 人」全部需求。需要快速浏览时按需渲染**瞬态视图**（不落盘）：
> `python3 -m tools.context.decisions`；未来由 `context doctor` 接管。
>
> 零依赖铁律：工具只 **parse**（读）JSON，故无需任何第三方 YAML 库。

## 写入纪律（事实源 append-only）

1. 新决策：先在 `registry.jsonl` append 一条 `DecisionRecord`（带 `related_context_events`
   回链到 [events/stream.jsonl](../events/stream.jsonl) 的 `evt_id`，构成可审计性桥
   `Decision → Evidence ContextEvent → Origin raw#id`）。
2. 同步在 `records/` 写一份 `DEC-XXXX-*.md` 人读叙述。
3. 需要浏览时跑 `python3 -m tools.context.decisions` 打印瞬态人读视图（不落盘，无第二事实源）。
4. 决策变更不就地改语义：用 `status`（proposed/accepted/rejected/superseded）演进；
   被本决策否决的方案折进记录本身（`rejected_alternatives` 字段，**与 `status=rejected` 区分**：
   后者描述「这条决策本身的状态」），**不单设 rejected-decisions.md**。
5. `type` 字段标注决策分类（默认 `architecture`，战略类用 `strategy`）；闭集枚举留未来 ADR。

## 当前首批决策

| id | 标题 | type | 状态 |
|---|---|---|---|
| DEC-0001 | ShanHai 需要独立的 Meta Context Layer | architecture | accepted |
| DEC-0002 | Runtime Memory 与 Meta Context 分离 | architecture | accepted |
| DEC-0003 | 先完成上下文统一，再进入平台能力建设（Context before Capability） | strategy | accepted |
| DEC-0004 | 未来方向：资本市场短线认知能力（future_direction，不开发） | strategy | proposed |
| DEC-0005 | Context Identity Principle（稳定身份归标识符，可变属性归元数据） | architecture | accepted |
