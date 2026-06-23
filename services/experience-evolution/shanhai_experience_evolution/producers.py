"""候选经验生产者协议（见 ADR 0017 Decision B / 修正 2，Stage 2-b）。

Producer 是「候选来源」的统一抽象：把各自来源信号归约为 CandidateProposal，
再经 CandidateService.create() 产出 Candidate。多来源（feedback / outcome / mining /
human / agent_discovery）复用同一入口（ADR 0017 修正 2）。

边界：本协议只声明 to_proposal() 输出 CandidateProposal——Producer 不直接生成
ExperienceCandidate、不绕过 CandidateService。具体 Producer 实现（如 feedback adapter）
位于各自来源包内，依赖方向 feedback → experience-evolution，本包不反向依赖。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shanhai_experience_evolution.proposals import CandidateProposal


@runtime_checkable
class CandidateProducer(Protocol):
    """候选生产者协议：来源信号 → CandidateProposal（非 Candidate）。"""

    def to_proposal(self, signal) -> CandidateProposal: ...
