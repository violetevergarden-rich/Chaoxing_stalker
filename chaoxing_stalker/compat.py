#!/usr/bin/env python3
"""Compatibility entry point for the ChaoXing assignment client."""

import sys

from chaoxing_stalker.chaoxing.auth import encrypt_by_aes
from chaoxing_stalker.chaoxing.client import ChaoXingClient
from chaoxing_stalker.chaoxing.parser import is_unsubmitted, parse_task_url


class ChaoXingStalker(ChaoXingClient):
    """Backward-compatible name for :class:`ChaoXingClient`."""

    _encrypt_by_aes = staticmethod(encrypt_by_aes)
    _is_unsubmitted = staticmethod(is_unsubmitted)
    _parse_task_url = staticmethod(parse_task_url)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print("用法: python -m chaoxing_stalker.compat <用户名> <密码>")
        return 1

    username, password = args[:2]
    stalker = ChaoXingStalker(username, password)
    assignments = stalker.get_unsubmitted_assignments()

    print("\n" + "=" * 60)
    print(f"未提交作业共 {len(assignments)} 项:\n")
    for index, assignment in enumerate(assignments, 1):
        print(f"{index}. [{assignment['course_name']}]")
        print(f"   作业: {assignment['title']}")
        print(f"   截止: {assignment['deadline']}")
        print(f"   链接: {assignment['url']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
