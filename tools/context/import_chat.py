"""Raw conversation export → ContextEvent 流。

Commit 1 占位骨架，真正实现见 Commit 3（Raw Import）。
约定（ADR 0000 §D5）：actor 默认 unknown，不推断 speaker；raw#id 幂等去重。
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.context.import_chat",
        description="Raw conversation export → ContextEvent 流（Commit 3 实现）",
    )
    parser.add_argument("--source", help="原始导出文件路径（.shanhai-meta/conversations/raw/*.json）")
    parser.parse_args(argv)
    print("[import_chat] 占位骨架：真正实现见 Commit 3（Raw Import）。", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
