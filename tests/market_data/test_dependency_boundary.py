"""Market Data dependency boundary tests.

Run:
PYTHONPATH=services/market-data:. .venv/bin/python -m tests.market_data.test_dependency_boundary
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKET_DATA = ROOT / "services" / "market-data" / "shanhai_market_data"

FORBIDDEN_IMPORTS = {
    "shanhai_runtime_kernel",
    "shanhai_experience_runtime",
    "shanhai_memory",
    "shanhai_experience_evolution",
    "shanhai_feedback",
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


def test_market_data_has_no_runtime_experience_memory_dependencies() -> None:
    violations = []
    for path in MARKET_DATA.rglob("*.py"):
        bad = _imports(path) & FORBIDDEN_IMPORTS
        if bad:
            violations.append((path.relative_to(ROOT), sorted(bad)))

    assert not violations, f"market-data forbidden imports: {violations}"
    print("[OK] market-data 无 Runtime / Experience / Memory / Evolution 依赖")


def test_market_data_does_not_define_trading_surface() -> None:
    forbidden_terms = {
        "broker",
        "place_order",
        "submit_order",
        "position",
        "portfolio",
        "buy",
        "sell",
    }
    violations = []
    for path in MARKET_DATA.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        bad = sorted(term for term in forbidden_terms if term in text)
        if bad:
            violations.append((path.relative_to(ROOT), bad))

    assert not violations, f"market-data trading terms found: {violations}"
    print("[OK] market-data 未暴露交易能力 surface")


def main() -> None:
    test_market_data_has_no_runtime_experience_memory_dependencies()
    test_market_data_does_not_define_trading_surface()
    print("\nMarket Data dependency boundary 测试全部通过 ✅")


if __name__ == "__main__":
    main()
