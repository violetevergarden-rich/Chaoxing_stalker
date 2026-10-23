#!/usr/bin/env python3
"""Command-line entry point for a single ChaoXing assignment check."""

import argparse

from chaoxing_stalker.app import run_from_config
from chaoxing_stalker.config import DEFAULT_CONFIG_PATH, generate_config_template


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="超星学习通作业提醒")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--init-config", action="store_true", help="生成配置模板")
    args = parser.parse_args(argv)

    if args.init_config:
        generate_config_template(args.config)
        return

    run_from_config(args.config)


if __name__ == "__main__":
    main()
