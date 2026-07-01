"""Market Intelligence 依赖边界契约测试（M3.4 S1，AST 静态守护）。

运行：
PYTHONPATH=services/market-data:services/market-intelligence:. \
    .venv/bin/python -m tests.market_intelligence.test_dependency_boundary

守护 ADR 0019 §5（R1 修订）的依赖不变量：
  Case 1  market-intelligence **禁** import runtime-kernel / reasoning-engine /
          experience*（cognition_state 只引用 id/ref，不 import experience 模块）
  Case 2  market-intelligence **禁** trading 术语（broker/place_order/position/...）
  Case 3  market-intelligence **禁** provider 判定分支（ifind/wind/akshare/
          SHANHAI_DATA_MODE）——对 provider 无感知
  Case 4  R1-1 铁律：market-data 源码**绝不** 出现任何 intelligence 概念
          （shanhai_market_intelligence / KnowledgeObject / MarketContextSnapshot）
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKET_INTELLIGENCE = ROOT / "services" / "market-intelligence" / "shanhai_market_intelligence"
MARKET_DATA = ROOT / "services" / "market-data" / "shanhai_market_data"
EVOLUTION = MARKET_INTELLIGENCE / "evolution"

# evolution/ 禁引用的 context 侧 Snapshot 概念（D9 / R4-1：Knowledge MUST NOT
# depend on MarketContextSnapshot）。反向（Context MAY consume Knowledge）不在
# 本轮落地，故不加 context 禁 import evolution 的 case。
SNAPSHOT_IDENTIFIERS = {
    "MarketContextSnapshot",
    "ContextAssembler",
    "AsOf",
    "MarketState",
    "CognitionState",
    "CognitionRef",
    "ObservationRef",
    "KnowledgeRef",
}

FORBIDDEN_IMPORTS = {
    "shanhai_runtime_kernel",
    "shanhai_reasoning_engine",
    "shanhai_experience",
    "shanhai_experience_runtime",
    "shanhai_experience_evolution",
    "shanhai_experience_artifact",
    "shanhai_memory",
    "shanhai_feedback",
}

# market-data 绝不 import / 引用的 intelligence 概念（R1-1 铁律）。
# 用 AST 识别实际代码引用（import 模块 + Name/Attribute 标识符），
# 不扫描 docstring 文本——端口 docstring 为解释边界会提及这些名字，属正常。
INTELLIGENCE_IMPORT_ROOTS = {"shanhai_market_intelligence"}
INTELLIGENCE_IDENTIFIERS = {
    "KnowledgeObject",
    "MarketContextSnapshot",
    "ContextAssembler",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def _code_identifiers(path: Path) -> set[str]:
    """代码中作为标识符出现的名字（Name.id / Attribute.attr）；不含 docstring 文本。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def _non_docstring_str_constants(path: Path) -> set[str]:
    """代码中的字符串字面量（排除 module/class/function docstring）。

    用于捕获 ``if source == "ifind"`` 之类的 provider 判定分支，同时放过
    docstring 里为说明边界而提及的 provider 名。
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    values: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            values.add(node.value)
    return values


def test_market_intelligence_no_upstream_or_sibling_dependencies() -> None:
    violations = []
    for path in MARKET_INTELLIGENCE.rglob("*.py"):
        bad = _imports(path) & FORBIDDEN_IMPORTS
        if bad:
            violations.append((path.relative_to(ROOT), sorted(bad)))

    assert not violations, f"market-intelligence forbidden imports: {violations}"
    print("[OK] market-intelligence 不依赖 runtime-kernel / reasoning-engine / experience*")


def test_market_intelligence_does_not_define_trading_surface() -> None:
    forbidden_terms = {
        "broker",
        "place_order",
        "submit_order",
        "portfolio",
    }
    violations = []
    for path in MARKET_INTELLIGENCE.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        bad = sorted(term for term in forbidden_terms if term in text)
        if bad:
            violations.append((path.relative_to(ROOT), bad))

    assert not violations, f"market-intelligence trading terms found: {violations}"
    print("[OK] market-intelligence 未暴露交易能力 surface")


def test_market_intelligence_is_provider_agnostic() -> None:
    """Context 层对 provider 无感知：无 ifind/wind/akshare 判定分支。

    AST 扫 import + 代码标识符 + 非 docstring 字符串字面量（如 ``== "ifind"``），
    放过 docstring 里为说明边界而提及的 provider 名（那正是「不接」的声明）。
    """
    provider_terms = {"ifind", "wind", "akshare", "tushare"}
    identifier_terms = {"SHANHAI_DATA_MODE", "shanhai_data_mode"}
    violations = []
    for path in MARKET_INTELLIGENCE.rglob("*.py"):
        import_roots = _imports(path)
        idents = _code_identifiers(path)
        str_lits_lower = {s.lower() for s in _non_docstring_str_constants(path)}
        bad = sorted(
            (import_roots & provider_terms)
            | (idents & identifier_terms)
            | {t for t in provider_terms if t in str_lits_lower}
        )
        if bad:
            violations.append((path.relative_to(ROOT), bad))

    assert not violations, f"market-intelligence provider-specific branches: {violations}"
    print("[OK] market-intelligence 对 provider 无感知（无 ifind/wind/akshare 分支）")


def test_market_data_never_references_intelligence() -> None:
    """R1-1 铁律：market-data 永远不知道 intelligence 存在。

    AST 识别实际 import 与代码标识符引用（不扫 docstring/注释文本，端口 docstring
    为解释边界会提及这些名字，属正常，不算越界）。
    """
    violations = []
    for path in MARKET_DATA.rglob("*.py"):
        bad_imports = _imports(path) & INTELLIGENCE_IMPORT_ROOTS
        bad_idents = _code_identifiers(path) & INTELLIGENCE_IDENTIFIERS
        bad = sorted(bad_imports | bad_idents)
        if bad:
            violations.append((path.relative_to(ROOT), bad))

    assert not violations, f"market-data leaked intelligence concepts: {violations}"
    print("[OK] market-data 源码不引用任何 intelligence 概念（R1-1 铁律）")


def test_evolution_does_not_depend_on_snapshot() -> None:
    """D9（R4-1）：Knowledge Evolution MUST NOT depend on MarketContextSnapshot。

    evolution/ 禁 import context 侧 models（``shanhai_market_intelligence.models``）
    与 assembler，禁在代码里引用 Snapshot 概念标识符（AST，不扫 docstring）。
    """
    if not EVOLUTION.exists():
        print("[SKIP] evolution/ 尚未建立")
        return
    violations = []
    for path in EVOLUTION.rglob("*.py"):
        bad_idents = _code_identifiers(path) & SNAPSHOT_IDENTIFIERS
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        bad_imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if mod in {
                    "shanhai_market_intelligence.models",
                    "shanhai_market_intelligence.assembler",
                }:
                    bad_imports.add(mod)
        bad = sorted(bad_idents | bad_imports)
        if bad:
            violations.append((path.relative_to(ROOT), bad))

    assert not violations, f"evolution/ 依赖了 context 侧 Snapshot 概念（D9 违规）：{violations}"
    print("[OK] D9：evolution/ 不依赖 MarketContextSnapshot / context 侧概念")


def test_evolution_does_not_import_reasoning_engine() -> None:
    """ADR 0020 D3：evolution/ 只依赖 ReasoningPort（Protocol），不 import reasoning-engine。"""
    if not EVOLUTION.exists():
        print("[SKIP] evolution/ 尚未建立")
        return
    forbidden = {"shanhai_reasoning_engine"}
    violations = []
    for path in EVOLUTION.rglob("*.py"):
        bad = _imports(path) & forbidden
        if bad:
            violations.append((path.relative_to(ROOT), sorted(bad)))

    assert not violations, f"evolution/ import 了 reasoning-engine：{violations}"
    print("[OK] D3：evolution/ 不 import reasoning-engine")


def test_evolution_does_not_own_observation() -> None:
    """R5-1：evolution 不拥有 Observation——禁 import 存储实现 / 内嵌 observation 值。

    evolution 触达 market-data 只经 ``ObservationReadPort``（后续步注入）；本步连
    port 都不接。断言 evolution/ 源码**不 import** 任何存储实现模块，也不 import
    ``Observation`` DTO（证据只经 EvidenceRef 引用身份）。
    """
    if not EVOLUTION.exists():
        print("[SKIP] evolution/ 尚未建立")
        return
    forbidden_modules = {
        "shanhai_market_data.sqlite_repository",
        "shanhai_market_data.ports.sqlite_observation_reader",
        "shanhai_market_data.ports.in_memory_observation_reader",
        "shanhai_market_data.ports.observation_reader",
    }
    violations = []
    for path in EVOLUTION.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        bad = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in forbidden_modules:
                bad.add(node.module)
                for alias in node.names:
                    if alias.name == "Observation":
                        bad.add("Observation")
        if bad:
            violations.append((path.relative_to(ROOT), sorted(bad)))

    assert not violations, f"evolution/ 拥有/复制了 Observation（R5-1 违规）：{violations}"
    print("[OK] R5-1：evolution/ 不拥有 Observation（不 import 存储实现 / Observation DTO）")


def main() -> None:
    test_market_intelligence_no_upstream_or_sibling_dependencies()
    test_market_intelligence_does_not_define_trading_surface()
    test_market_intelligence_is_provider_agnostic()
    test_market_data_never_references_intelligence()
    test_evolution_does_not_depend_on_snapshot()
    test_evolution_does_not_import_reasoning_engine()
    test_evolution_does_not_own_observation()
    print("\nMarket Intelligence 依赖边界契约测试全部通过 ✅")


if __name__ == "__main__":
    main()
