"""RuntimeState 生命周期契约测试（v0.7 §0.C G5 / Q5.4，PR-1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_lifecycle_contract
覆盖（state transition）：
  Case 1 合法链：CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED 逐步通过
  Case 2 非法迁移抛错：RUNNING→READY（明确禁止）、RUNNING→ASSEMBLING（逆向）等
  Case 3 终态 CLOSED 无出边；自迁移 / 跳跃迁移非法
"""

from __future__ import annotations

from shanhai_runtime_kernel import RuntimeState, assert_transition, can_transition

_LEGAL_CHAIN = [
    RuntimeState.CREATED,
    RuntimeState.ASSEMBLING,
    RuntimeState.READY,
    RuntimeState.RUNNING,
    RuntimeState.COMPLETED,
    RuntimeState.CLOSED,
]


def test_case1_legal_chain() -> None:
    for src, dst in zip(_LEGAL_CHAIN, _LEGAL_CHAIN[1:]):
        assert can_transition(src, dst), f"{src} → {dst} 应合法"
        assert assert_transition(src, dst) is dst
    print("[OK] Case 1：CREATED→ASSEMBLING→READY→RUNNING→COMPLETED→CLOSED 合法链通过")


def test_case2_illegal_transitions_rejected() -> None:
    illegal = [
        (RuntimeState.RUNNING, RuntimeState.READY),        # 明确禁止
        (RuntimeState.RUNNING, RuntimeState.ASSEMBLING),   # 逆向
        (RuntimeState.READY, RuntimeState.CREATED),        # 逆向
        (RuntimeState.CREATED, RuntimeState.RUNNING),      # 跳跃
        (RuntimeState.ASSEMBLING, RuntimeState.RUNNING),   # 跳跃
        (RuntimeState.COMPLETED, RuntimeState.RUNNING),    # 逆向
    ]
    for src, dst in illegal:
        assert not can_transition(src, dst), f"{src} → {dst} 应非法"
        try:
            assert_transition(src, dst)
            raise AssertionError(f"{src} → {dst} 不应通过校验")
        except ValueError:
            pass
    print("[OK] Case 2：非法迁移（含 RUNNING→READY / 逆向 / 跳跃）抛 ValueError")


def test_case3_terminal_and_self_transition() -> None:
    # 终态无出边
    for dst in RuntimeState:
        assert not can_transition(RuntimeState.CLOSED, dst), f"CLOSED → {dst} 应非法"
    # 自迁移非法
    for s in RuntimeState:
        assert not can_transition(s, s), f"{s} → {s}（自迁移）应非法"
    print("[OK] Case 3：CLOSED 为终态无出边；自迁移非法")


def main() -> None:
    test_case1_legal_chain()
    test_case2_illegal_transitions_rejected()
    test_case3_terminal_and_self_transition()
    print("\nRuntimeState 生命周期契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
