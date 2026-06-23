"""OutcomeIngestor — 外部真实结果 → outcome 事件（ADR 0015 §4.2）。

延迟结果回填：T 日的 decision，T+N 日才知道真实结果。本组件把调用方注入的结构化结果
写成 outcome 事件，经 refs.parent_event_id 挂回对应 decision，不修改 decision 本身
（append-only，守 ADR 0014 不可变铁律）。

Stage 2-a 不接真实数据源：调用方负责提供 decision_event_id / outcome 数据 / 发生时间。
不做股票 API / 数据同步 / 定时任务 / 市场数据 pipeline。

occurred_at（结果真实发生时间，T+N）与 recorded_at（回填时刻）分离，由模型默认
recorded_at=now 自动记录写入时间，调用方只需给出 occurred_at。
"""

from __future__ import annotations

from datetime import datetime

from shanhai_experience.models import (
    ExperienceEvent,
    ExperienceEventType,
    ExperienceRefs,
)
from shanhai_experience.store import ExperienceStore


class OutcomeIngestor:
    """外部结果 → outcome 事件。service 层写入编排，离线/按需运行。"""

    def __init__(self, store: ExperienceStore) -> None:
        self._store = store

    def ingest(
        self,
        decision_event_id: str,
        outcome: dict,
        occurred_at: datetime,
    ) -> ExperienceEvent:
        """把一项外部真实结果回填为 outcome 事件并 append。

        - decision_event_id：被回填的历史 decision 事件 id。
        - outcome：结构化结果（如 {"return": 0.12, "direction": "up", "correct": True}）。
        - occurred_at：结果真实发生时间（T+N），与写入时间分离。
        """
        decision = self._store.get(decision_event_id)
        if decision is None:
            raise ValueError(f"被回填的 decision 事件不存在：{decision_event_id}")
        if decision.type is not ExperienceEventType.DECISION:
            raise ValueError(
                f"parent 事件类型必须为 decision，实际为 {decision.type.value}"
            )

        event = ExperienceEvent(
            episode_id=decision.episode_id,
            agent=decision.agent,
            type=ExperienceEventType.OUTCOME,
            payload={"outcome": dict(outcome)},
            refs=ExperienceRefs(
                run_id=decision.refs.run_id,
                parent_event_id=decision.event_id,
            ),
            occurred_at=occurred_at,
        )
        self._store.append(event)
        return event
