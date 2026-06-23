"""ExperienceRecorder — RunRecord → decision / observation 事件（ADR 0015 §4.1）。

把一次运行转写为经验事件：核心是 decision（Agent 当时作出的判断），可选 observation
（运行过程中的关键观察）。从 RunStore 的 RunRecord 取稳定 run_id，不依赖无 run_id 的
RunResult，不修改 AgentRunner —— 守住 agent-runtime 不依赖 experience。

引用而非复制：经 refs.run_id 引用 RunStore，payload 只存决策摘要，不复制 Step 全量。
append-only：只新增事件，不修改历史。
"""

from __future__ import annotations

from shanhai_agent_runtime.store import RunRecord
from shanhai_agent_runtime.types import StepType

from shanhai_experience.ingest.episode import resolve_episode_id
from shanhai_experience.models import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
)
from shanhai_experience.store import ExperienceStore


class ExperienceRecorder:
    """运行记录 → 决策/观察事件。service 层写入编排，离线/按需运行。"""

    def __init__(self, store: ExperienceStore) -> None:
        self._store = store

    def record_decision(
        self,
        record: RunRecord,
        *,
        episode_id: str | None = None,
        summary: str | None = None,
        payload: dict | None = None,
    ) -> ExperienceEvent:
        """把一次运行的判断结论记为 decision 事件并 append。

        - episode_id：显式指定研究主题；缺省回退 run_id（跨 run 语义，ADR 0015）。
        - summary：决策摘要文本；缺省取运行 output 的字符串形式。
        - payload：额外结构化内容；与默认字段合并。
        """
        result = record.result
        body = {
            "summary": summary if summary is not None else _output_text(result.output),
            "status": result.status.value,
        }
        if payload:
            body.update(payload)
        event = ExperienceEvent(
            episode_id=resolve_episode_id(episode_id, record.run_id),
            agent=result.agent,
            type=ExperienceEventType.DECISION,
            payload=body,
            refs=ExperienceRefs(run_id=record.run_id),
        )
        self._store.append(event)
        return event

    def record_observations(
        self,
        record: RunRecord,
        *,
        episode_id: str | None = None,
    ) -> list[ExperienceEvent]:
        """把运行中的 observe 步骤记为 observation 事件（可选）。"""
        eid = resolve_episode_id(episode_id, record.run_id)
        events: list[ExperienceEvent] = []
        for step in record.result.steps:
            if step.type is not StepType.OBSERVE:
                continue
            event = ExperienceEvent(
                episode_id=eid,
                agent=record.result.agent,
                type=ExperienceEventType.OBSERVATION,
                payload={"content": step.content, "step_index": step.index},
                refs=ExperienceRefs(run_id=record.run_id),
            )
            self._store.append(event)
            events.append(event)
        return events


def _output_text(output: object) -> str:
    return "" if output is None else str(output)
