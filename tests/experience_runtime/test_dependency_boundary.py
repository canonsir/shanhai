"""Experience Runtime 依赖边界契约测试（PR-4.1）。

运行：PYTHONPATH=. .venv/bin/python -m tests.experience_runtime.test_dependency_boundary
覆盖：
  Case 1 experience-runtime 不依赖 agent-runtime / memory / evaluation / feedback / evolution
  Case 2 experience-runtime 不依赖 Artifact persistence / service / repository
  Case 3 experience-artifact 不反向依赖 experience-runtime
"""

from __future__ import annotations

import ast
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
PKG_DIR = REPO_ROOT / "services/experience-runtime/shanhai_experience_runtime"
ARTIFACT_DIR = REPO_ROOT / "services/experience-artifact/shanhai_experience_artifact"


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


def test_case1_no_forbidden_runtime_dependencies() -> None:
    imports = _imports_of(PKG_DIR)
    forbidden_prefixes = (
        "shanhai_agent_runtime",
        "shanhai_memory",
        "shanhai_evaluation",
        "shanhai_feedback",
        "shanhai_experience_evolution",
    )

    leaked = sorted(
        module for module in imports if module.startswith(forbidden_prefixes)
    )

    assert not leaked, f"experience-runtime 不应依赖横向/后置模块: {leaked}"
    print("[OK] Case 1：无 agent-runtime / memory / evaluation / feedback / evolution 依赖")


def test_case2_no_artifact_persistence_dependency() -> None:
    imports = _imports_of(PKG_DIR)
    forbidden = {
        "shanhai_experience_artifact.repository",
        "shanhai_experience_artifact.service",
    }
    leaked = sorted(module for module in imports if module in forbidden)

    assert not leaked, f"PR-4.1 不应依赖 Artifact persistence/service: {leaked}"
    print("[OK] Case 2：无 Artifact repository / service 依赖")


def test_case3_artifact_does_not_depend_on_experience_runtime() -> None:
    imports = _imports_of(ARTIFACT_DIR)

    assert not any(
        module.startswith("shanhai_experience_runtime") for module in imports
    ), f"experience-artifact 不应反向依赖 experience-runtime: {imports}"
    print("[OK] Case 3：experience-artifact 不反向依赖 experience-runtime")


def main() -> None:
    test_case1_no_forbidden_runtime_dependencies()
    test_case2_no_artifact_persistence_dependency()
    test_case3_artifact_does_not_depend_on_experience_runtime()
    print("\nExperience Runtime 依赖边界契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
