# DEC-0002：Runtime Memory 与 Meta Context 分离

- 状态：accepted
- 关联：[ADR 0000](../../../docs/架构决策记录/0000-项目元上下文架构.md)、ADR 0014（Experience Memory）
- 结构记录：见 [registry.jsonl](../registry.jsonl) 同 id 条目

## 背景

ShanHai 同时存在两层世界：

```
        Meta Layer（给 人 + AI 协作）        Runtime Layer（给 Agent）
        ContextEvent / Decision / Snapshot    ExperienceEvent / Memory / Agent Runtime
        项目认知如何形成（reasoning history）  Agent 执行了什么（execution history）
```

## 决定

ContextEvent（Meta 层）与 ExperienceEvent（Runtime 层）**严格分离**：不共享、不转换、
不互相消费。系统级名称**不使用 "Memory"**，该词保留给 Runtime 世界（Experience Memory）。

## 原因

- 两层正交对称，目的与生命周期不同：Meta 长期版本化、不进 services；Runtime 运行时积累、参与 Agent 运行。
- ContextEvent 是 append-only 工程记录，混用会污染语义、误把元上下文升为业务能力。
- 类比人类：「人为什么这么想」属 Meta，「人做了什么」属 Runtime，二者不能混。

## 备选方案（已考虑）

- 把 ContextEvent 与 ExperienceEvent 合并为同一事件流。
- 在 Meta 层复用 services/experience 的 Runtime schema（pydantic）。

## 已否决

- 未来合并 ContextEvent 与 ExperienceEvent。
- 在 Meta 层引入第三种 Memory。

## 证据回链（related_context_events）

- `evt_0fd87b61d82cdd3e`、`evt_a0171f29632b3003`
  （见 [events/stream.jsonl](../../events/stream.jsonl)）
