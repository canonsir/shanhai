"""Experience 领域写入编排（ingest，见 ADR 0015 Stage 2-a：Outcome 回填基座）。

把「事件生产者」补齐：除已有 Feedback（lesson）外，新增
- ExperienceRecorder：RunRecord → decision / observation 事件
- OutcomeIngestor：外部真实结果 → outcome 事件（经 parent_event_id 挂回 decision）

均为 service 层写入编排，经 ExperienceStore.append（service → service）落库；
不进入 agent-runtime，Agent 不直接写 Experience（守 ADR 0012 / 0014 不变量）。
"""

from shanhai_experience.ingest.episode import resolve_episode_id
from shanhai_experience.ingest.outcome import OutcomeIngestor
from shanhai_experience.ingest.recorder import ExperienceRecorder

__all__ = [
    "resolve_episode_id",
    "ExperienceRecorder",
    "OutcomeIngestor",
]
