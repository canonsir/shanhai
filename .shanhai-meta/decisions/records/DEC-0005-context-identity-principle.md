# DEC-0005：Context Identity Principle（稳定身份归标识符，可变属性归元数据）

- 状态：accepted
- 关联：[ADR 0000](../../../docs/架构决策记录/0000-项目元上下文架构.md)、[DEC-0002](DEC-0002-runtime-meta-boundary.md)
- 结构记录：见 [registry.jsonl](../registry.jsonl) 同 id 条目

## 背景

5D Conversation Ingestion 的 raw 文件早期命名为 `20260624-chatgpt-山海架构.json`：日期前缀把
**可变信息**（导入日期）编码进了**文件名**。同一 conversation 若日后再导入，日期会变 → 要么
产生重复副本、要么改名后与权威元数据（`index.jsonl`）漂移不一致。这暴露出一个尚未被显式固化、
却在 Context Foundation 多处隐含遵循的原则。

## 决定

确立 **Context Identity Principle**：

> Stable identity belongs to immutable identifiers.
> Mutable attributes must live in metadata registries.
>
> 稳定身份归不可变标识符；可变属性归可更新的元数据注册表。

落到工程：

- **文件路径 / 标识符 = identity locator**：只编码稳定身份
  （`conversation_id` / `cognition_id` / `decision_id` / `artifact_id`）。
- **可更新数据结构 = mutable metadata registry**：时间戳 / 标题 / 状态 / 置信度等可变信息
  归 `index.jsonl` 这类 catalog 或 `status` / `confidence` 字段，**不得编码进路径 / 文件名**。

## Rules

- filename must not encode mutable metadata（文件名不得编码可变元数据）
- timestamp is metadata, not identity（时间戳是元数据，不是身份）
- title is human hint, not identity（标题是人读提示，不是身份）
- generated content must not redefine identity（生成内容不得重新定义身份）

## Examples

| 对象 | identity（→ 路径 / 标识符） | metadata（→ 注册表 / 字段） |
|---|---|---|
| Conversation | `conversation_id` → 文件名 | `title` / `update_time` → `index.jsonl` |
| CognitionSnapshot | `cognition_id` → identity | `generated_at` → metadata |
| DecisionRecord | `decision_id` → identity | `status` → metadata |
| ExperienceArtifact | `artifact_id` → identity | `confidence` → metadata |

> 注：`ExperienceArtifact` 属 Runtime 世界（ADR 0014），此处仅作为同一原则在另一层的**类比示例**，
> 不代表 Meta 层消费或依赖它（Runtime 与 Meta 分离见 [DEC-0002](DEC-0002-runtime-meta-boundary.md)）。

## 原因

- 可变信息一旦编码进路径 / 文件名，改名即破坏身份，且与权威元数据漂移（**文件名不是数据库**）。
- 稳定身份天然是 identity locator，可变属性天然属于 mutable metadata registry，分层职责清晰。
- 与业界范式一致：Git `commit hash` + metadata、Docker `image digest` + tag、Kubernetes `uid` + labels。
- ShanHai 已有同构实践：`cognition_id` 排除 `generated_at`、raw 文件名锚定 `conversation_id`、
  DecisionRecord 以 `status` 演进而非改 `id`。本决策只是把这条隐含铁律显式固化。

## 备选方案（已考虑）

- 文件名 / 路径编码日期或标题等可变 metadata（如 `20260624-chatgpt-标题.json`）。
- 把可变状态（`status` / `confidence`）也写进标识符本身。

## 已否决

- 用文件名编码时间戳 / 标题作为身份（改名即失联、与 catalog 漂移）。
- 用 `project_memory` 命名此原则（与 Runtime AI Memory 概念混淆，故采用 Context Identity
  Principle，固化进 Decision Registry 而非另起术语）。

## 证据回链（related_context_events）

- 无（本原则源自 5D naming adjustment 的设计讨论，未单独落入 [events/stream.jsonl](../../events/stream.jsonl)；
  其依据是工程推理而非某条 conversation 片段，故回链留空，符合 health 校验）。
