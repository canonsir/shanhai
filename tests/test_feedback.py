"""Feedback 闭环测试（见 ADR 0013 Stage 1：FailurePattern → Candidate → Lesson）。

运行：PYTHONPATH=. .venv/bin/python -m tests.test_feedback
覆盖：
  1. FailurePatternRule：失败评估 → 候选；成功评估 → 无候选
  2. CandidateRegistry：同 dedup_key 合并计数 + 阈值晋升判定
  3. FeedbackEngine：阈值前不落库 → 达阈值晋升一条 lesson 事件；不重复晋升
  4. 引用而非复制：lesson 事件经 refs 引用 run_id/evaluation_ref，payload 不含原始 metrics
  5. 端到端：Run → RunStore → Evaluation → Feedback → ExperienceStore，
     并经 MemoryTool（EXPERIENCE scope，只读）反哺读取 lesson；经 Tool 写 lesson 被拒
"""

from __future__ import annotations

from shanhai_agent_runtime.context import AgentContext
from shanhai_agent_runtime.memory import InMemoryMemory
from shanhai_agent_runtime.store import InMemoryRunStore
from shanhai_agent_runtime.types import AgentStatus, RunResult, Step, StepType
from shanhai_evaluation import RuntimeEvaluator
from shanhai_evaluation.models import EvaluationResult, Metric
from shanhai_experience import (
    ExperienceEventType,
    ExperienceStore,
    InMemoryExperienceStore,
)
from shanhai_tools.registry import ToolRegistry
from shanhai_wiki_engine import KnowledgeService

from shanhai_feedback import (
    CandidateRegistry,
    ExperienceCandidate,
    FailurePatternRule,
    FeedbackEngine,
)
from shanhai_feedback.models import CandidateKind
from shanhai_memory import (
    ExperienceReadAdapter,
    KnowledgeReadAdapter,
    MemoryScope,
    MemoryService,
    MemoryTool,
    RuntimeMemoryAdapter,
)


def _failed_eval(run_id: str, agent: str = "research", error: str = "PermissionError") -> EvaluationResult:
    return EvaluationResult(
        run_id=run_id,
        evaluator="runtime_evaluator",
        metrics=[
            Metric(name="success", value=False),
            Metric(name="error_type", value=error),
        ],
        passed=False,
        detail={"agent": agent, "status": "failed"},
    )


def test_failure_pattern_rule() -> None:
    rule = FailurePatternRule()

    cands = rule.derive(_failed_eval("run-1"))
    assert len(cands) == 1
    c = cands[0]
    assert c.kind == CandidateKind.FAILURE_PATTERN
    assert c.agent == "research"
    assert c.dedup_key == "research|failure|PermissionError"
    assert c.source_run_ids == ["run-1"]
    assert c.signals == {"passed": False, "error_type": "PermissionError"}

    # 成功评估不产候选
    ok_eval = EvaluationResult(run_id="run-x", passed=True, detail={"agent": "research"})
    assert rule.derive(ok_eval) == []
    print("[OK] FailurePatternRule：失败产候选 / 成功不产")


def test_candidate_registry_merge_and_threshold() -> None:
    reg = CandidateRegistry(promote_threshold=2)
    rule = FailurePatternRule()

    c1 = reg.add(rule.derive(_failed_eval("run-1"))[0])
    assert c1.occurrences == 1 and reg.is_promotable(c1) is False

    c2 = reg.add(rule.derive(_failed_eval("run-2"))[0])
    # 同 dedup_key 合并：计数 2、来源累加、达阈值
    assert c2.occurrences == 2
    assert c2.source_run_ids == ["run-1", "run-2"]
    assert reg.is_promotable(c2) is True
    assert len(reg.candidates()) == 1
    print("[OK] CandidateRegistry：合并计数 + 阈值晋升判定")


def test_engine_promotes_once_at_threshold() -> None:
    store = InMemoryExperienceStore()
    engine = FeedbackEngine(store=store)  # 默认阈值 2

    # 第一次失败：未达阈值，不落库
    assert engine.process(_failed_eval("run-1")) == []
    assert store.list(type=ExperienceEventType.LESSON) == []

    # 第二次同类失败：达阈值，晋升一条 lesson
    promoted = engine.process(_failed_eval("run-2"))
    assert len(promoted) == 1
    lessons = store.list(type=ExperienceEventType.LESSON)
    assert len(lessons) == 1

    # 第三次：已晋升，不重复落库
    assert engine.process(_failed_eval("run-3")) == []
    assert len(store.list(type=ExperienceEventType.LESSON)) == 1
    print("[OK] FeedbackEngine：阈值前不落 / 达阈值晋升一条 / 不重复晋升")


def test_lesson_references_not_copies() -> None:
    store = InMemoryExperienceStore()
    engine = FeedbackEngine(store=store)
    engine.process(_failed_eval("run-1"))
    engine.process(_failed_eval("run-2"))

    lesson = store.list(type=ExperienceEventType.LESSON)[0]
    # 引用而非复制：refs 指向来源，payload 不内嵌原始 Metric 对象
    assert lesson.refs.run_id == "run-2"
    assert lesson.refs.evaluation_ref == "run-2:runtime_evaluator"
    assert "metrics" not in lesson.payload
    assert lesson.payload["signals"]["error_type"] == "PermissionError"
    assert set(lesson.payload["source_run_ids"]) == {"run-1", "run-2"}
    print("[OK] lesson 事件只引用 run_id/evaluation_ref，不复制原始度量")


def test_end_to_end_run_to_lesson_and_readback() -> None:
    # 1) 两次失败运行落 RunStore
    run_store = InMemoryRunStore()
    failed = RunResult(
        agent="research",
        status=AgentStatus.FAILED,
        steps=[Step(index=0, type=StepType.THINK, content="plan")],
        error="PermissionError: 工具未授权",
    )
    rid1 = run_store.save_run(failed)
    rid2 = run_store.save_run(failed)

    # 2) Evaluation：经 RunStore 取数评估（绑定真实 run_id）
    evaluator = RuntimeEvaluator()
    exp_store: ExperienceStore = InMemoryExperienceStore()
    engine = FeedbackEngine(store=exp_store)

    for rid in (rid1, rid2):
        record = run_store.get_run(rid)
        result = evaluator.evaluate(record)
        engine.process(result, record)

    lessons = exp_store.list(type=ExperienceEventType.LESSON)
    assert len(lessons) == 1 and lessons[0].agent == "research"

    # 3) 读侧反哺：Agent 经 MemoryTool（EXPERIENCE，只读）检索 lesson
    mem = MemoryService(
        runtime=RuntimeMemoryAdapter(InMemoryMemory()),
        knowledge=KnowledgeReadAdapter(KnowledgeService()),
        experience=ExperienceReadAdapter(exp_store),
    )
    registry = ToolRegistry()
    registry.register(MemoryTool(mem))
    ctx = AgentContext(
        agent_name="research",
        router=None,
        tool_registry=registry,
        memory=InMemoryMemory(),
        granted_tools=["memory"],
    )
    res = ctx.use_tool("memory", action="search", scope="experience", agent="research", type="lesson")
    assert res.ok and len(res.data) == 1
    assert res.data[0].content.type == ExperienceEventType.LESSON

    # Agent 不能经 Tool 写 lesson（EXPERIENCE 只读）
    bad = ctx.use_tool("memory", action="write", scope="experience", key="x", content={})
    assert bad.ok is False and bad.error
    print("[OK] 端到端 Run→Eval→Feedback→Lesson + 经 MemoryTool 只读反哺")


def main() -> None:
    test_failure_pattern_rule()
    test_candidate_registry_merge_and_threshold()
    test_engine_promotes_once_at_threshold()
    test_lesson_references_not_copies()
    test_end_to_end_run_to_lesson_and_readback()
    print("\nFeedback 闭环测试全部通过 ✅")


if __name__ == "__main__":
    main()
