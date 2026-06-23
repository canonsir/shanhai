"""ShanHai Feedback — Evaluation → Experience 反馈闭环（见 ADR 0013）。

Stage 1：FailurePattern → Candidate → Lesson。
把评估结果归因为候选经验（ExperienceCandidate），经去重/合并/阈值晋升后，
以 type=lesson 的 ExperienceEvent 落入 ExperienceStore（ADR 0014 事实基座）。

定位（ADR 0013）：Feedback 是「度量 → 经验」之间的归因/提炼组合层——
Evaluation 只度量、Memory 只存取、价值判断只在 Feedback。

写经验路径（决策①，Addendum）：经 ExperienceStore.append（service → service），
不经 MemoryService/MemoryTool；EXPERIENCE 对 Agent 只读。依赖单向：
feedback → evaluation + experience + agent-runtime（均只读/经抽象）。

不在 Stage 1：regression / effective_path 规则、Episode / SemanticExperience 投影、
模型在环归因、Vector / Graph / CQRS / 新增 DB。
"""

from shanhai_feedback.engine import FeedbackEngine
from shanhai_feedback.evolution_adapter import FeedbackProposalAdapter
from shanhai_feedback.models import CandidateKind, ExperienceCandidate
from shanhai_feedback.registry import CandidateRegistry
from shanhai_feedback.rules import FailurePatternRule, FeedbackRule

__all__ = [
    "CandidateKind",
    "ExperienceCandidate",
    "FeedbackRule",
    "FailurePatternRule",
    "CandidateRegistry",
    "FeedbackEngine",
    "FeedbackProposalAdapter",
]
