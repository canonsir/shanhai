"""事实源 → context/ 派生快照（幂等可重跑）。

Commit 1 占位骨架，真正实现见 Commit 5（Context Builder）。
约定（ADR 0000 §D9）：从事实源重建 context/*.md；AI 不直接改 snapshot。
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.build_context",
        description="事实源 → context/ 派生快照（Commit 5 实现）",
    )
    parser.parse_args(argv)
    print("[build_context] 占位骨架：真正实现见 Commit 5（Context Builder）。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
