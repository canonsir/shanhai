# ShanHai — Current State（人读视图）

> 本文件是 `context/cognition.json` 的**人读投影**（由 `tools/context/renderer.py` 渲染）。
> 派生物，**请勿手改**（会被重渲染覆盖）。要更新内容：改事实源（`project.yaml` /
> `decisions/registry.jsonl`）→ 重跑 `tools.context.builder` → 重跑 `tools.context.renderer`。
>
> generated_at: `2026-06-25T05:18:01+00:00`（继承自 cognition.json）
>
> cognition_id: `sha256:88b592b041ed7653d81a2dbecba8c4102bf370d988010219b580f29e78b48e8e`（content identity，内容不变则不变）

## Project Identity

- **Project**：ShanHai
- **Mission**：构建能持续学习、理解和分析中国资本市场的 AI Native 认知与决策系统（数据→知识→认知→分析→策略→执行）
- **Description**：AI Native 的中国资本市场认知与决策系统

## Current Phase

- **Phase**：ADR 0000 Project Context Layer（建设中）
- **Status**：building

## Decisions（已确认）

| ID | Type | Title |
|---|---|---|
| DEC-0001 | architecture | ShanHai 需要独立的 Meta Context Layer |
| DEC-0002 | architecture | Runtime Memory 与 Meta Context 分离 |
| DEC-0003 | strategy | 先完成上下文统一，再进入平台能力建设（Context before Capability） |
| DEC-0005 | architecture | Context Identity Principle（稳定身份归标识符，可变属性归元数据） |

> 「为什么这么决定 / 否决了什么」见 `decisions/registry.jsonl` 的 `reason` 与 `decisions/records/*.md`（本视图不内联理由，避免成为第二事实源）。

## Constraints（Frozen，AI 不得擅自修改）

- [frozen] Agent Runtime（services/agent-runtime）
- [frozen] Agent Runtime Memory（services/memory，ADR 0012）
- [frozen] ExperienceEvent schema / ExperienceStore.append 契约（ADR 0014）
- [frozen] Experience Candidate 生命周期（ADR 0017）
- [frozen] ContextEvent schema 语义（Context Foundation，ADR 0000，变更需 ADR）
- [frozen] DecisionRecord schema 语义（Context Foundation，ADR 0000，变更需 ADR）
- [frozen] CognitionSnapshot schema 语义（Context Foundation，ADR 0000，变更需 ADR）
- [frozen] v0.2.0 baseline

## Future Direction（未来方向，当前不开发）

- 未来方向：资本市场短线认知能力（future_direction，不开发）（来源 DEC-0004）

## References

- [Decision Registry（结构事实源）](../decisions/registry.jsonl)
- [Decision Records（人读解释 / 为什么这么决定）](../decisions/records/)
- [ADR 0000：项目元上下文架构](../../docs/架构决策记录/0000-项目元上下文架构.md)
