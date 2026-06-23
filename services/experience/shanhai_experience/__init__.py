"""ShanHai Experience — Agent 经验事件基座（见 ADR 0014 / 0015）。

Stage 1（ADR 0014）：Experience Event Infrastructure。
append-only 经验事件日志（Event Log Lite 的事实基座），支持 append / get / list(filter)。
引用而非复制：经 refs 关联 run_id / evaluation / entity，不复制 RunStore/Evaluation/Knowledge 内容。

Stage 2-a（ADR 0015）：Outcome 回填基座。
新增写入编排 ingest：ExperienceRecorder（RunRecord → decision/observation）、
OutcomeIngestor（外部结果 → outcome，经 parent_event_id 挂回 decision）；
list 支持 episode_id / parent_event_id 过滤。均 service → service，Agent 不直接写。

不在范围：Episode 投影、Semantic Experience、Vector、Graph、DB、LLM。
"""

from shanhai_experience.ingest import (
    ExperienceRecorder,
    OutcomeIngestor,
    resolve_episode_id,
)
from shanhai_experience.models import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
)
from shanhai_experience.store import ExperienceStore, InMemoryExperienceStore

__all__ = [
    "ExperienceEvent",
    "ExperienceEventType",
    "ExperienceRefs",
    "ExperienceStore",
    "InMemoryExperienceStore",
    "ExperienceRecorder",
    "OutcomeIngestor",
    "resolve_episode_id",
]
