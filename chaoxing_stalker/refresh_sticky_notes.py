"""Refresh the sticky-note folder without sending notifications."""

import argparse
import shutil
import sys
from pathlib import Path

from chaoxing_stalker.assignment_types import Assignment
from chaoxing_stalker.chaoxing.client import ChaoXingClient
from chaoxing_stalker.config import DEFAULT_CONFIG_PATH, load_config, validate_config
from chaoxing_stalker.message_formatter import sort_assignments_by_deadline
from chaoxing_stalker.retry import retry
from chaoxing_stalker.sticky_notes import (
    DEFAULT_STICKY_NOTE_FOLDER,
    REFRESH_SHELL_SCRIPT,
    REFRESH_WINDOWS_SCRIPT,
    _limit_filename,
    _safe_component,
    write_sticky_notes,
)


def refresh_sticky_notes(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    notes_directory: str | Path | None = None,
) -> None:
    """Clear the target note folder and recreate notes for its configured users."""
    config = load_config(str(config_path), use_environment=False)
    validate_config(config)

    if notes_directory is None:
        raise ValueError("必须指定小纸条文件夹路径")
    target_directory = Path(notes_directory).resolve()
    folder_name = target_directory.name
    users = [
        user
        for user in config["users"]
        if _user_targets_folder(user, folder_name)
    ]
    if not users:
        raise ValueError(
            f"配置中没有启用目标文件夹“{folder_name}”的小纸条用户"
        )

    target_directory.mkdir(parents=True, exist_ok=True)
    _clear_note_directory(target_directory)

    for user in users:
        username = user.get("name") or user["chaoxing"]["username"]
        provider = ChaoXingClient(
            user["chaoxing"]["username"], user["chaoxing"]["password"]
        )

        @retry(max_attempts=3, base_delay=2)
        def fetch_assignments() -> list[Assignment]:
            return provider.get_unsubmitted_assignments()

        assignments = sort_assignments_by_deadline(fetch_assignments())
        write_sticky_notes(
            username,
            assignments,
            directory=target_directory.parent,
            folder_name=folder_name,
        )


def _user_targets_folder(user: dict, folder_name: str) -> bool:
    sticky_note = user.get("sticky_note", {})
    if not sticky_note.get("enabled", False):
        return False
    configured_name = sticky_note.get("folder_name", DEFAULT_STICKY_NOTE_FOLDER)
    safe_name = _limit_filename(
        _safe_component(configured_name) or DEFAULT_STICKY_NOTE_FOLDER
    )
    return safe_name == folder_name


def _clear_note_directory(directory: Path) -> None:
    keep = {REFRESH_SHELL_SCRIPT, REFRESH_WINDOWS_SCRIPT}
    for child in directory.iterdir():
        if child.name in keep and child.is_file() and not child.is_symlink():
            continue
        if child.is_symlink() or not child.is_dir():
            child.unlink()
        else:
            shutil.rmtree(child)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只刷新超星作业小纸条")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--notes-directory", required=True, help="小纸条文件夹路径")
    args = parser.parse_args(argv)
    try:
        refresh_sticky_notes(args.config, args.notes_directory)
    except Exception as error:
        print(f"[ERROR] 小纸条刷新失败: {error}", file=sys.stderr)
        return 1
    print("[INFO] 小纸条已刷新")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
