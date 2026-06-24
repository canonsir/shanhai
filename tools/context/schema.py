"""Project Context Layer — Context Domain Model（见 ADR 0000，Commit 2：Context Schema）。

本模块冻结元上下文层的三个核心对象的**稳定语义**，并提供可逆 JSON 序列化与校验：

- ContextEvent     统一事实流的原子记录（append-only engineering record，写入 events/stream.jsonl）
- DecisionRecord   决策注册表的一条已确认工程事实（Layer 2，Decision Registry）
- ContextSnapshot  当前认知状态的派生快照（Layer 3，由 builder 重建，AI 不直接改）

边界（ADR 0000 §D6）：本目录零依赖，仅用 Python 标准库（dataclasses + enum + json）。
不引入 pydantic（那是 services/experience 的 Runtime 边界），不接 LLM、不做 importer、不做自动总结。

ContextEvent ≠ Runtime Event：它是「人 + AI 工程协作」的事实记录，不参与 Agent 运行，
严格区别于 ExperienceEvent（ADR 0014）。两个 event 不共享。

序列化契约（GPT Review 验收）：object → dict → json 可逆；每个对象带 schema_version 字段。
"""

from __future__ import annotations

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
    """

    id: str
    decision: str
    status: DecisionStatus = DecisionStatus.PROPOSED
    reason: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    source: str | None = None          # 来源事件/对话引用（如 evt_id / raw#id）
    decided_at: str | None = None       # 确认时间（ISO8601）
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "decision": self.decision,
            "status": self.status.value,
            "reason": list(self.reason),
            "related": list(self.related),
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
            reason=list(d.get("reason", [])),
            related=list(d.get("related", [])),
            source=d.get("source"),
            decided_at=d.get("decided_at"),
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
    "now_iso",
]
