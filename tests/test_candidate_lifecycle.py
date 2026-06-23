"""候选经验生命周期回归测试（见 ADR 0017 Stage 2-b：Candidate Lifecycle）。

运行：PYTHONPATH=. .venv/bin/python -m tests.test_candidate_lifecycle
覆盖：
  Case 1 Producer create：Proposal → CandidateService.create() → 初始 Created
  Case 2 Validator lifecycle：Created → Evaluating → Validated/Rejected；
         apply_validation 正确回写 confidence / validation_stats / evidence_refs
  Case 3 权限边界：Producer 不能验证、Validator 不能晋升、PromotionGate 不能评估、
         无任意 status setter（状态只经 service 转移）
  Case 4 Promotion 边界：Validated → Promoted；PromotionDecision 仅 4 字段，无 artifact
  Case 5 Feedback adapter 边界：feedback → FeedbackProposalAdapter → CandidateProposal；
         只产 proposal、不创建 Candidate、不绕过 CandidateService
  Final  依赖方向：experience-evolution 不 import feedback；feedback → evolution 单向；
         experience 不 import experience-evolution
"""

from __future__ import annotations

import ast
import pathlib

from shanhai_experience_evolution import (
    Actor,
    CandidateProposal,
    CandidateService,
    CandidateSource,
    CandidateStatus,
    EvidenceRefs,
    Hypothesis,
    InMemoryCandidateRepository,
    NoopPromotionGate,
    NoopValidator,
    PromotionDecision,
    SourceRefs,
    TransitionError,
    ValidationContext,
    ValidationStats,
    ValidationVerdict,
    is_allowed_transition,
)

from shanhai_feedback import FeedbackProposalAdapter
from shanhai_feedback.models import CandidateKind
from shanhai_feedback.models import ExperienceCandidate as FeedbackCandidate

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _service() -> CandidateService:
    return CandidateService(InMemoryCandidateRepository())


def test_case1_producer_create() -> None:
    svc = _service()
    proposal = CandidateProposal(
        source=CandidateSource.FEEDBACK,
        hypothesis=Hypothesis(condition="research 反复以 TimeoutError 失败"),
        source_refs=SourceRefs(event_ids=["evt_001"]),
    )
    assert isinstance(proposal, CandidateProposal)

    candidate = svc.create(proposal)
    assert candidate.validation_status == CandidateStatus.CREATED
    assert candidate.source == CandidateSource.FEEDBACK
    assert candidate.source_refs.event_ids == ["evt_001"]
    assert candidate.lineage.source == "feedback"
    assert svc.get(candidate.candidate_id).validation_status == CandidateStatus.CREATED
    print("[OK] Case 1：Producer Proposal → create() → Created")


def test_case2_validator_lifecycle() -> None:
    svc = _service()

    # Validated 路径
    c = svc.create(CandidateProposal(source=CandidateSource.FEEDBACK))
    svc.transition(c.candidate_id, CandidateStatus.EVALUATING, Actor.VALIDATOR)
    assert svc.get(c.candidate_id).validation_status == CandidateStatus.EVALUATING

    verdict = ValidationVerdict(
        validated=True,
        confidence=0.82,
        validation_stats=ValidationStats(
            success_count=9, failure_count=2, window=11, consistency=0.82
        ),
        evidence_refs=EvidenceRefs(outcome_refs=["evt_100", "evt_101"]),
        reason="9/11 outcome 成功",
    )
    c2 = svc.apply_validation(c.candidate_id, verdict)
    assert c2.validation_status == CandidateStatus.VALIDATED
    # ValidationVerdict 正确回写三项
    assert c2.confidence == 0.82
    assert c2.validation_stats.success_count == 9 and c2.validation_stats.consistency == 0.82
    assert c2.evidence_refs.outcome_refs == ["evt_100", "evt_101"]

    # Rejected 路径
    r = svc.create(CandidateProposal(source=CandidateSource.FEEDBACK))
    svc.transition(r.candidate_id, CandidateStatus.EVALUATING, Actor.VALIDATOR)
    r2 = svc.apply_validation(
        r.candidate_id, ValidationVerdict(validated=False, reason="一致性不足")
    )
    assert r2.validation_status == CandidateStatus.REJECTED

    # 只有 Validator 能驱动评估态：Created → Evaluating 仅 Validator 合法
    assert is_allowed_transition(
        CandidateStatus.CREATED, CandidateStatus.EVALUATING, Actor.VALIDATOR
    ) is True

    # Validator 接口：NoopValidator 经只读 ValidationContext 产出 ValidationVerdict
    noop_verdict = NoopValidator().validate(c2, ValidationContext())
    assert isinstance(noop_verdict, ValidationVerdict) and noop_verdict.validated is False
    print("[OK] Case 2：Validator Created→Evaluating→Validated/Rejected + verdict 回写")


def test_case3_permission_boundary() -> None:
    svc = _service()
    c = svc.create(CandidateProposal(source=CandidateSource.FEEDBACK))

    # Producer 不能验证
    try:
        svc.transition(c.candidate_id, CandidateStatus.EVALUATING, Actor.PRODUCER)
        raise AssertionError("Producer 不应能进入 Evaluating")
    except TransitionError:
        pass
    try:
        svc.transition(c.candidate_id, CandidateStatus.VALIDATED, Actor.PRODUCER)
        raise AssertionError("Producer 不应能直接 Validated")
    except TransitionError:
        pass

    # 推进到 Validated 以测试后续越权
    svc.transition(c.candidate_id, CandidateStatus.EVALUATING, Actor.VALIDATOR)
    svc.apply_validation(c.candidate_id, ValidationVerdict(validated=True))

    # Validator 不能晋升
    try:
        svc.transition(c.candidate_id, CandidateStatus.PROMOTED, Actor.VALIDATOR)
        raise AssertionError("Validator 不应能晋升")
    except TransitionError:
        pass

    # PromotionGate 不能评估（无权驱动 Created→Evaluating / Evaluating→Validated）
    assert is_allowed_transition(
        CandidateStatus.CREATED, CandidateStatus.EVALUATING, Actor.PROMOTION_GATE
    ) is False
    assert is_allowed_transition(
        CandidateStatus.EVALUATING, CandidateStatus.VALIDATED, Actor.PROMOTION_GATE
    ) is False

    # 无任意 status setter：service 公共面只有生命周期方法，不存在直接置位入口
    assert not hasattr(svc, "set_status")
    public = {m for m in dir(svc) if not m.startswith("_")}
    assert public == {"create", "transition", "apply_validation", "get", "list"}
    print("[OK] Case 3：越权转移被拒 + 无任意 status setter")


def test_case4_promotion_boundary() -> None:
    svc = _service()
    c = svc.create(CandidateProposal(source=CandidateSource.FEEDBACK))
    svc.transition(c.candidate_id, CandidateStatus.EVALUATING, Actor.VALIDATOR)
    svc.apply_validation(c.candidate_id, ValidationVerdict(validated=True, confidence=0.9))

    # Validated → Promoted（仅 PromotionGate）
    promoted = svc.transition(c.candidate_id, CandidateStatus.PROMOTED, Actor.PROMOTION_GATE)
    assert promoted.validation_status == CandidateStatus.PROMOTED

    # PromotionDecision 仅 4 字段，无 artifact/summary/embedding
    fields = set(PromotionDecision.model_fields.keys())
    assert fields == {"approved", "reason", "candidate_id", "validation_snapshot_ref"}
    forbidden = {"artifact", "artifact_content", "summary", "knowledge_document", "embedding"}
    assert not (fields & forbidden)

    decision = NoopPromotionGate().evaluate(promoted)
    assert isinstance(decision, PromotionDecision)
    assert decision.candidate_id == promoted.candidate_id and decision.approved is False
    print("[OK] Case 4：Validated→Promoted + PromotionDecision 仅 4 字段无 artifact")


def test_case5_feedback_adapter_boundary() -> None:
    adapter = FeedbackProposalAdapter()
    fc = FeedbackCandidate(
        kind=CandidateKind.FAILURE_PATTERN,
        agent="research",
        summary="research 反复以 PermissionError 失败",
        dedup_key="research|failure|PermissionError",
        source_run_ids=["run-1", "run-2"],
    )

    proposal = adapter.to_proposal(fc)
    # 只产 proposal，不产 Candidate
    assert isinstance(proposal, CandidateProposal)
    assert proposal.source == CandidateSource.FEEDBACK
    assert proposal.source_refs.event_ids == ["run-1", "run-2"]
    assert proposal.lineage.source == "feedback:research|failure|PermissionError"

    # 不绕过 Service：adapter 不暴露 create_candidate，也不持有 service
    assert not hasattr(adapter, "create_candidate")
    assert not any("service" in a.lower() for a in vars(adapter))

    # 统一入口：Candidate 必须经 CandidateService.create() 产出
    svc = _service()
    candidate = svc.create(proposal)
    assert candidate.validation_status == CandidateStatus.CREATED
    assert candidate.source == CandidateSource.FEEDBACK
    print("[OK] Case 5：feedback → Adapter → Proposal → CandidateService.create()")


def _imports_of(pkg_dir: pathlib.Path) -> set[str]:
    modules: set[str] = set()
    for f in pkg_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(n.name for n in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
    return modules


def test_final_dependency_direction() -> None:
    evo = _imports_of(
        REPO_ROOT / "services/experience-evolution/shanhai_experience_evolution"
    )
    assert not any(m.startswith("shanhai_feedback") for m in evo), evo
    # experience 不依赖 experience-evolution（事实层不反向依赖演化层）
    exp = _imports_of(REPO_ROOT / "services/experience/shanhai_experience")
    assert not any(m.startswith("shanhai_experience_evolution") for m in exp), exp
    # feedback 适配层引用 evolution（单向 feedback → evolution，允许）
    fb = _imports_of(REPO_ROOT / "services/feedback/shanhai_feedback")
    assert any(m.startswith("shanhai_experience_evolution") for m in fb)
    print("[OK] Final：evolution 不依赖 feedback / experience 不依赖 evolution / feedback→evolution 单向")


def main() -> None:
    test_case1_producer_create()
    test_case2_validator_lifecycle()
    test_case3_permission_boundary()
    test_case4_promotion_boundary()
    test_case5_feedback_adapter_boundary()
    test_final_dependency_direction()
    print("\nCandidate 生命周期回归测试全部通过 ✅")


if __name__ == "__main__":
    main()
