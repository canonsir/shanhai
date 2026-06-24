"""单条追加 ContextEvent（持续同步入口）。

Commit 1 占位骨架，真正实现见 Commit 4（Decision Registry）。
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.append_conversation",
        description="单条追加 ContextEvent（Commit 4 实现）",
    )
    parser.add_argument("--type", help="conversation|decision|review|approval|implementation")
    parser.add_argument("--source", help="chatgpt|claude|trae|human|git")
    parser.add_argument("--body", help="记录正文")
    parser.parse_args(argv)
    print("[append_conversation] 占位骨架：真正实现见 Commit 4（Decision Registry）。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
