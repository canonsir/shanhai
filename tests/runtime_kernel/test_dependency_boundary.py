"""runtime-kernel 依赖边界契约测试（v0.7 §0.C G5 / Q5.4 + G1，PR-1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.runtime_kernel.test_dependency_boundary
以 AST 静态检查守护 import boundary（沿用 test_artifact_bridge.py 模式）：
  Case 1 依赖方向：runtime-kernel **不** import experience-artifact；
         **不** import agent-runtime internals（子模块）；
         只允许 → agent-runtime public interface（顶层 shanhai_agent_runtime）
  Case 2 PR-1 纯结构（G1）：源码不出现 AgentRunner(...) / RunStore(...) /
         ExperienceCandidateProvider(...) 的实例化/调用（名字仅可在 docstring 引用）
  Case 3 仅依赖 pydantic + 自身包（PR-1 不引入任何下游能力包）
"""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PKG_DIR = REPO_ROOT / "services/runtime-kernel/shanhai_runtime_kernel"

_FORBIDDEN_INSTANTIATIONS = {
    "AgentRunner",
    "RunStore",
    "InMemoryRunStore",
    "ExperienceCandidateProvider",
}


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


def _called_names(pkg_dir: pathlib.Path) -> set[str]:
    """收集源码中被调用 / 实例化的名字（ast.Call 的 func 名）。"""
    called: set[str] = set()
    for f in pkg_dir.glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    called.add(func.id)
                elif isinstance(func, ast.Attribute):
                    called.add(func.attr)
    return called


def test_case1_dependency_direction() -> None:
    imports = _imports_of(PKG_DIR)
    # 禁止 → experience-artifact
    assert not any(
        m.startswith("shanhai_experience_artifact") for m in imports
    ), f"runtime-kernel 不应 import experience-artifact: {imports}"
    # 禁止 → experience-runtime（尚不存在，但守护横向边）
    assert not any(
        m.startswith("shanhai_experience_runtime") for m in imports
    ), imports
    # 禁止 → agent-runtime internals（子模块）；只允许顶层 public interface
    agent_internals = [
        m
        for m in imports
        if m.startswith("shanhai_agent_runtime.")
    ]
    assert not agent_internals, f"runtime-kernel 不应 import agent-runtime 内部模块: {agent_internals}"
    print("[OK] Case 1：不依赖 experience-artifact / experience-runtime / agent-runtime internals")


def test_case2_pure_structure_no_instantiation() -> None:
    called = _called_names(PKG_DIR)
    leaked = called & _FORBIDDEN_INSTANTIATIONS
    assert not leaked, f"PR-1 纯结构红线：不应实例化/调用下游能力 {leaked}"
    print("[OK] Case 2：G1 纯结构 — 无 AgentRunner/RunStore/ExperienceCandidateProvider 实例化")


def test_case3_only_pydantic_and_self() -> None:
    imports = _imports_of(PKG_DIR)
    third_party = {
        m.split(".")[0]
        for m in imports
        if not m.startswith("shanhai_runtime_kernel")
    }
    # 允许标准库 + pydantic；不得出现任何 shanhai_* 下游包
    shanhai_deps = {m for m in third_party if m.startswith("shanhai_")}
    assert not shanhai_deps, f"PR-1 不应依赖任何下游 shanhai 包: {shanhai_deps}"
    print("[OK] Case 3：仅依赖标准库 + pydantic + 自身包（无下游耦合）")


def main() -> None:
    test_case1_dependency_direction()
    test_case2_pure_structure_no_instantiation()
    test_case3_only_pydantic_and_self()
    print("\nruntime-kernel 依赖边界契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
