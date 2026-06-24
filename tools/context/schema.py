"""Project Context Layer — Context Domain Model（见 ADR 0000，Commit 2：Context Schema）。

本模块冻结元上下文层的三个核心对象的**稳定语义**，并提供可逆 JSON 序列化与校验：

- ContextEvent     统一事实流的原子记录（append-only engineering record，写入 events/stream.jsonl）
- DecisionRecord   决策注册表的一条已确认工程事实（Layer 2，Decision Registry）
- ContextSnapshot  当前认知状态的派生快照（Layer 3，由 builder 重建，AI 不直接改）
- CognitionSnapshot AI Agent 启动认知契约（Commit 5A，确定性装配，写入 context/cognition.json）

边界（ADR 0000 §D6）：本目录零依赖，仅用 Python 标准库（dataclasses + enum + json）。
不引入 pydantic（那是 services/experience 的 Runtime 边界），不接 LLM、不做 importer、不做自动总结。

ContextEvent ≠ Runtime Event：它是「人 + AI 工程协作」的事实记录，不参与 Agent 运行，
严格区别于 ExperienceEvent（ADR 0014）。两个 event 不共享。

序列化契约（GPT Review 验收）：object → dict → json 可逆；每个对象带 schema_version 字段。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

# Schema 版本：任何对象结构变更必须 bump 此值并在此声明兼容版本集。
SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})


class SchemaError(ValueError):
    """schema 校验失败（缺字段 / 枚举非法 / 版本不支持）。"""


# --------------------------------------------------------------------------- #
# 枚举（校验的 enum type）
# --------------------------------------------------------------------------- #


class EventType(str, Enum):
    """ContextEvent 类型（ADR 0000 §D4，闭集）。"""

    CONVERSATION = "conversation"      # 原始对话片段（import 忠实搬运）
    DECISION = "decision"              # 一次工程决策
    REVIEW = "review"                  # 一次架构 Review 意见
    APPROVAL = "approval"              # 一次批准（Review Gate 放行）
    IMPLEMENTATION = "implementation"  # 一次实现/落地记录


class SourceKind(str, Enum):
    """事件来源（可扩展，未来支持多模型/多工具导出，ADR 0000 §原因）。"""

    CHATGPT_EXPORT = "chatgpt_export"
    CLAUDE_EXPORT = "claude_export"
    CURSOR_HISTORY = "cursor_history"
    TRAE_HISTORY = "trae_history"
    GIT_COMMIT = "git_commit"
    MANUAL = "manual"                  # 人工/脚本单条追加（append_conversation）
    UNKNOWN = "unknown"


class ActorRole(str, Enum):
    """事件归属角色。默认 unknown：宁可 unknown，不错误记忆（ADR 0000 §D5）。

    import 阶段一律 unknown（不推断 speaker）；身份由 Decision Registry 人工确认后才显式标注。
    角色名对齐 project.yaml participants（按角色建模，不绑定具体模型）。
    """

    UNKNOWN = "unknown"
    HUMAN_OWNER = "human-owner"
    ARCHITECTURE_AGENT = "architecture-agent"
    CODING_AGENT = "coding-agent"


class DecisionStatus(str, Enum):
    """决策状态（Decision Registry）。"""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


# --------------------------------------------------------------------------- #
# 校验小工具
# --------------------------------------------------------------------------- #


def _require(d: dict[str, Any], key: str, ctx: str) -> Any:
    if key not in d:
        raise SchemaError(f"{ctx}: 缺少必需字段 '{key}'")
    return d[key]


def _require_version(d: dict[str, Any], ctx: str) -> str:
    version = _require(d, "schema_version", ctx)
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaError(f"{ctx}: 不支持的 schema_version '{version}'（支持 {sorted(SUPPORTED_SCHEMA_VERSIONS)}）")
    return version


def _parse_enum(enum_cls: type[Enum], value: Any, ctx: str) -> Any:
    try:
        return enum_cls(value)
    except ValueError as exc:
        allowed = [e.value for e in enum_cls]
        raise SchemaError(f"{ctx}: 非法 {enum_cls.__name__} 值 '{value}'（允许 {allowed}）") from exc


def now_iso() -> str:
    """统一的 UTC ISO8601 时间戳（秒级），纯文本、可 diff。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- #
# ContextEvent 及其嵌套对象
# --------------------------------------------------------------------------- #


@dataclass
class EventSource:
    """事件来源。ref 持有源内原始标识（如 raw#id），供 import 幂等去重。"""

    kind: SourceKind = SourceKind.UNKNOWN
    file: str | None = None
    ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "file": self.file, "ref": self.ref}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EventSource:
        return cls(
            kind=_parse_enum(SourceKind, d.get("kind", SourceKind.UNKNOWN.value), "EventSource.kind"),
            file=d.get("file"),
            ref=d.get("ref"),
        )


@dataclass
class EventActor:
    """事件归属。默认 unknown，不推断（ADR 0000 §D5）。"""

    role: ActorRole = ActorRole.UNKNOWN
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role.value, "name": self.name}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EventActor:
        return cls(
            role=_parse_enum(ActorRole, d.get("role", ActorRole.UNKNOWN.value), "EventActor.role"),
            name=d.get("name"),
        )


@dataclass
class EventContent:
    """事件内容。has_lost_media 如实标记客观可见的媒体丢失（ADR 0000 §D5），不臆测其余。"""

    text: str = ""
    attachments: list[Any] = field(default_factory=list)
    has_lost_media: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "attachments": list(self.attachments),
            "has_lost_media": self.has_lost_media,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> EventContent:
        return cls(
            text=d.get("text", ""),
            attachments=list(d.get("attachments", [])),
            has_lost_media=bool(d.get("has_lost_media", False)),
        )


@dataclass
class ContextEvent:
    """统一事实流的一条 append-only 工程记录（ADR 0000 §D4）。

    一经写入不就地修改；修正以新事件追加。一行一条写入 events/stream.jsonl。
    """

    id: str
    type: EventType
    timestamp: str = field(default_factory=now_iso)
    source: EventSource = field(default_factory=EventSource)
    actor: EventActor = field(default_factory=EventActor)
    content: EventContent = field(default_factory=EventContent)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "source": self.source.to_dict(),
            "actor": self.actor.to_dict(),
            "content": self.content.to_dict(),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextEvent:
        ctx = "ContextEvent"
        version = _require_version(d, ctx)
        return cls(
            id=str(_require(d, "id", ctx)),
            type=_parse_enum(EventType, _require(d, "type", ctx), f"{ctx}.type"),
            timestamp=str(_require(d, "timestamp", ctx)),
            source=EventSource.from_dict(d.get("source", {})),
            actor=EventActor.from_dict(d.get("actor", {})),
            content=EventContent.from_dict(d.get("content", {})),
            metadata=dict(d.get("metadata", {})),
            schema_version=version,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> ContextEvent:
        return cls.from_dict(json.loads(s))


# --------------------------------------------------------------------------- #
# DecisionRecord（Layer 2：Decision Registry）
# --------------------------------------------------------------------------- #


@dataclass
class DecisionRecord:
    """一条已确认的工程事实（不是聊天、不是 memory，而是「为什么这么决定」的注册表）。

    回答 AI 最需要的两个问题：为什么这么设计？哪些方案已被否决？（ADR 0000 §D3 Layer 2）

    它不是 markdown 模板，而是「认知 → 行为」的桥的结构化锚点（Decision → ADR → Runtime
    Policy → Agent Behavior，Commit 4 Review 约束）。Commit 4 加法式增补可选字段
    （带默认值、from_dict 用 .get() 兜底，向后兼容，无需 bump schema_version）：

    - type                    决策分类（如 architecture/strategy/product/constraint）。
                              仅预留为自由字符串、默认 "architecture"；闭集枚举留未来 ADR，不现在冻结。
    - title                   人读短标题（DEC-XXXX 记录标题用）
    - alternatives            考虑过的备选方案（保留 trade-off 思考痕迹）
    - rejected_alternatives   被本决策**否决的方案**（避免重复犯错）。注意与 status=rejected 区分：
                              status 描述「这条决策本身的状态」，rejected_alternatives 描述「这条决策否决了哪些选项」。
    - related_context_events  指向 events/stream.jsonl 的 evt_id（或 raw#id）——可审计性桥
                              （Decision → Evidence ContextEvent → Origin raw#id 的回链）
    """

    id: str
    decision: str
    status: DecisionStatus = DecisionStatus.PROPOSED
    type: str = "architecture"          # 决策分类（预留自由字符串，闭集枚举留未来 ADR）
    reason: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    source: str | None = None          # 来源事件/对话引用（如 evt_id / raw#id）
    decided_at: str | None = None       # 确认时间（ISO8601）
    title: str | None = None            # 人读短标题（Commit 4 加法字段）
    alternatives: list[str] = field(default_factory=list)            # 考虑过的备选方案
    rejected_alternatives: list[str] = field(default_factory=list)   # 被本决策否决的方案
    related_context_events: list[str] = field(default_factory=list)  # 回链 evt_id / raw#id（可审计性桥）
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "decision": self.decision,
            "status": self.status.value,
            "reason": list(self.reason),
            "alternatives": list(self.alternatives),
            "rejected_alternatives": list(self.rejected_alternatives),
            "related": list(self.related),
            "related_context_events": list(self.related_context_events),
            "source": self.source,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DecisionRecord:
        ctx = "DecisionRecord"
        version = _require_version(d, ctx)
        return cls(
            id=str(_require(d, "id", ctx)),
            decision=str(_require(d, "decision", ctx)),
            status=_parse_enum(DecisionStatus, _require(d, "status", ctx), f"{ctx}.status"),
            type=str(d.get("type", "architecture")),
            reason=list(d.get("reason", [])),
            related=list(d.get("related", [])),
            source=d.get("source"),
            decided_at=d.get("decided_at"),
            title=d.get("title"),
            alternatives=list(d.get("alternatives", [])),
            rejected_alternatives=list(d.get("rejected_alternatives", [])),
            related_context_events=list(d.get("related_context_events", [])),
            schema_version=version,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> DecisionRecord:
        return cls.from_dict(json.loads(s))


# --------------------------------------------------------------------------- #
# ContextSnapshot（Layer 3：派生快照，AI 启动入口）
# --------------------------------------------------------------------------- #


@dataclass
class ContextSnapshot:
    """当前认知状态（不是全部历史，是「现在项目处于什么状态」，ADR 0000 §D3 Layer 3）。

    派生物：必须由 builder 从事实源重建，AI 不直接改（ADR 0000 §D9）。
    architecture 为 component -> status 的扁平映射（如 {"runtime_memory": "implemented"}）。
    """

    project_phase: str
    architecture: dict[str, str] = field(default_factory=dict)
    frozen_decisions: list[str] = field(default_factory=list)
    generated_at: str | None = None
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "project_phase": self.project_phase,
            "architecture": dict(self.architecture),
            "frozen_decisions": list(self.frozen_decisions),
            "generated_at": self.generated_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ContextSnapshot:
        ctx = "ContextSnapshot"
        version = _require_version(d, ctx)
        return cls(
            project_phase=str(_require(d, "project_phase", ctx)),
            architecture={str(k): str(v) for k, v in d.get("architecture", {}).items()},
            frozen_decisions=list(d.get("frozen_decisions", [])),
            generated_at=d.get("generated_at"),
            schema_version=version,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> ContextSnapshot:
        return cls.from_dict(json.loads(s))


# --------------------------------------------------------------------------- #
# CognitionSnapshot（Commit 5A：AI 启动认知契约）
# --------------------------------------------------------------------------- #
#
# 与 ContextSnapshot 的区别（GPT Commit 5 Review 收敛）：
#   ContextSnapshot   通用「某个 Context 状态快照」（Commit 2 既有 domain object）。
#   CognitionSnapshot 「一个 AI Agent 启动时应该加载的认知状态」——Agent cognition contract。
# 二者解耦：CognitionSnapshot 不复用 ContextSnapshot 的 schema_version，独立演化；
# 未来可派生 TradingAgentCognitionSnapshot / ResearchAgentCognitionSnapshot。
#
# 铁律：CognitionSnapshot 是事实图谱的一次**确定性投影**（deterministic cognition assembly），
# 不是 LLM 摘要。由 tools/context/builder.py 从 project.yaml + registry.jsonl 装配而成，
# 可幂等重跑、可 diff、可审计（ADR 0000 §D6 零依赖 / §D9 派生可重建）。


@dataclass
class CognitionIdentity:
    """项目身份（来自 project.yaml，不是派生认知）。"""

    project: str = ""
    mission: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"project": self.project, "mission": self.mission, "description": self.description}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionIdentity:
        return cls(
            project=str(d.get("project", "")),
            mission=str(d.get("mission", "")),
            description=str(d.get("description", "")),
        )


@dataclass
class CognitionPhase:
    """当前阶段。用 name+status 而非单串，给未来 phase history 留位。"""

    name: str = ""
    status: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionPhase:
        return cls(name=str(d.get("name", "")), status=str(d.get("status", "")))


@dataclass
class CognitionDecisionRef:
    """决策摘要引用：Agent startup 一次加载即得，无需再 lookup registry。

    source 保留 provenance（指回 registry.jsonl），便于回答「Agent 为什么知道这个」。
    """

    id: str = ""
    title: str = ""
    type: str = "architecture"
    source: str = "registry.jsonl"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "title": self.title, "type": self.type, "source": self.source}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionDecisionRef:
        return cls(
            id=str(d.get("id", "")),
            title=str(d.get("title", "")),
            type=str(d.get("type", "architecture")),
            source=str(d.get("source", "registry.jsonl")),
        )


@dataclass
class CognitionConstraint:
    """约束。type 为自由字符串（string-first）：MVP 仅 'frozen'，未来扩展不冻结 enum。"""

    type: str = "frozen"
    value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "value": self.value}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionConstraint:
        return cls(type=str(d.get("type", "frozen")), value=str(d.get("value", "")))


@dataclass
class CognitionFutureDirection:
    """未来方向（非已有能力）。source 指回提出它的决策（如 DEC-0004）。"""

    title: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "source": self.source}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionFutureDirection:
        return cls(title=str(d.get("title", "")), source=str(d.get("source", "")))


@dataclass
class CognitionSnapshot:
    """AI Agent 启动认知契约（Commit 5A）。由 builder 确定性装配，AI 不直接改（§D9）。

    metadata 携带 provenance（generated_by / inputs），属带外信息、不影响 schema_version。
    序列化时 `_metadata` 还会带上 generated_at 与 cognition_id（Commit 5C content identity）：
    - generated_at  本次装配时间（带外，不参与内容指纹）。
    - cognition_id  对**内容**（identity/phase/decisions/constraints/future_directions）排序后
                    取 sha256 —— 它不是 version，而是 **content identity**：答「这次启动认知 == 上次?」。
                    排除 generated_at（否则同一认知因时间不同而 hash 不同，无意义）。
    """

    identity: CognitionIdentity = field(default_factory=CognitionIdentity)
    phase: CognitionPhase = field(default_factory=CognitionPhase)
    decisions: list[CognitionDecisionRef] = field(default_factory=list)
    constraints: list[CognitionConstraint] = field(default_factory=list)
    future_directions: list[CognitionFutureDirection] = field(default_factory=list)
    generated_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    def _content_dict(self) -> dict[str, Any]:
        """参与 content identity 的部分（语义内容，排除 generated_at / provenance / schema_version）。"""
        return {
            "identity": self.identity.to_dict(),
            "phase": self.phase.to_dict(),
            "decisions": [d.to_dict() for d in self.decisions],
            "constraints": [c.to_dict() for c in self.constraints],
            "future_directions": [f.to_dict() for f in self.future_directions],
        }

    def content_fingerprint(self) -> str:
        """内容指纹（sha256:...）。确定性：同内容必得同值，与时间/构建机器无关。"""
        blob = json.dumps(self._content_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        # _metadata 为带外信息：provenance（builder 写入）+ generated_at + 计算得到的 cognition_id。
        meta = dict(self.metadata)
        meta["generated_at"] = self.generated_at
        meta["cognition_id"] = self.content_fingerprint()
        out = self._content_dict()
        out["schema_version"] = self.schema_version
        out["_metadata"] = meta
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CognitionSnapshot:
        ctx = "CognitionSnapshot"
        version = _require_version(d, ctx)
        meta = dict(d.get("_metadata", {}))
        # generated_at 现位于 _metadata；兼容历史顶层 generated_at。
        generated_at = meta.pop("generated_at", d.get("generated_at"))
        # cognition_id 是派生计算值，不回存进 metadata 字段（每次 to_dict 重算，避免漂移）。
        meta.pop("cognition_id", None)
        return cls(
            identity=CognitionIdentity.from_dict(d.get("identity", {})),
            phase=CognitionPhase.from_dict(d.get("phase", {})),
            decisions=[CognitionDecisionRef.from_dict(x) for x in d.get("decisions", [])],
            constraints=[CognitionConstraint.from_dict(x) for x in d.get("constraints", [])],
            future_directions=[CognitionFutureDirection.from_dict(x) for x in d.get("future_directions", [])],
            generated_at=generated_at,
            metadata=meta,
            schema_version=version,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_json(cls, s: str) -> CognitionSnapshot:
        return cls.from_dict(json.loads(s))


__all__ = [
    "SCHEMA_VERSION",
    "SUPPORTED_SCHEMA_VERSIONS",
    "SchemaError",
    "EventType",
    "SourceKind",
    "ActorRole",
    "DecisionStatus",
    "EventSource",
    "EventActor",
    "EventContent",
    "ContextEvent",
    "DecisionRecord",
    "ContextSnapshot",
    "CognitionIdentity",
    "CognitionPhase",
    "CognitionDecisionRef",
    "CognitionConstraint",
    "CognitionFutureDirection",
    "CognitionSnapshot",
    "now_iso",
]
