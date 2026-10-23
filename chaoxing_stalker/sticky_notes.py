"""Write one atomically updated text note per assignment to the desktop."""

import hashlib
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from chaoxing_stalker.assignment_types import Assignment

DEFAULT_STICKY_NOTE_FOLDER = "学习通作业"


def desktop_directory(
    home: str | Path | None = None,
    system: str | None = None,
    environ: dict[str, str] | None = None,
) -> Path:
    """Resolve the user's desktop on Windows and XDG-based Linux desktops."""
    env = os.environ if environ is None else environ
    home_path = Path(home or env.get("USERPROFILE") or env.get("HOME") or Path.home())
    platform = system or os.name

    if platform == "nt":
        candidates = [home_path / "Desktop"]
        for key in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
            if env.get(key):
                candidates.insert(0, Path(env[key]) / "Desktop")
        return next((path for path in candidates if path.is_dir()), candidates[0])

    xdg_file = Path(env.get("XDG_CONFIG_HOME", home_path / ".config")) / "user-dirs.dirs"
    try:
        for line in xdg_file.read_text(encoding="utf-8").splitlines():
            match = re.match(r'^\s*XDG_DESKTOP_DIR\s*=\s*"(.*)"\s*$', line)
            if match:
                configured = match.group(1).replace("${HOME}", str(home_path)).replace(
                    "$HOME", str(home_path)
                )
                return Path(configured).expanduser()
    except OSError:
        pass
    return home_path / "Desktop"


def write_sticky_notes(
    user_name: str,
    assignments: list[Assignment],
    directory: str | Path | None = None,
    folder_name: str = DEFAULT_STICKY_NOTE_FOLDER,
) -> None:
    """Create or replace notes for current assignments without duplicate files."""
    desktop = Path(directory) if directory is not None else desktop_directory()
    safe_folder_name = _safe_component(folder_name) or DEFAULT_STICKY_NOTE_FOLDER
    target_directory = desktop / _limit_filename(safe_folder_name)
    del user_name  # User identity does not form part of the assignment's filename.
    if len(assignments) > 100:
        raise ValueError("小纸条最多支持 100 项作业，无法保持两位数字前缀")

    prefixes = _validate_prefixes(f"{index:02d}" for index in range(len(assignments)))

    title_counts = Counter(assignment.get("title", "").strip() for assignment in assignments)
    same_title_course_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for assignment in assignments:
        title = assignment.get("title", "").strip()
        if title_counts[title] > 1:
            same_title_course_counts[title][assignment.get("course_name", "")] += 1
    seen_title_course: Counter[tuple[str, str]] = Counter()

    entries = []
    filenames = set()
    for prefix, assignment in zip(prefixes, assignments):
        title = assignment.get("title", "").strip() or "未命名作业"
        filename = _safe_component(title)
        if title_counts[title] > 1:
            course = _safe_component(assignment.get("course_name", "")) or "未命名课程"
            filename = f"{filename} - {course}"
            course_key = (title, course)
            seen_title_course[course_key] += 1
            if same_title_course_counts[title][assignment.get("course_name", "")] > 1:
                filename += f" ({seen_title_course[course_key]})"
        filename = _limit_filename(filename)
        note_filename = f"{prefix}_{filename}.txt"
        if note_filename in filenames:
            raise ValueError(f"生成的小纸条文件名重复: {note_filename}")
        filenames.add(note_filename)
        path = target_directory / note_filename
        content = "\n".join(
            (
                f"课程: {assignment.get('course_name') or '未知'}",
                f"作业: {assignment.get('title') or '未知'}",
                f"截止时间: {assignment.get('deadline') or '未知'}",
                f"链接: {assignment.get('url') or '未知'}",
                "",
            )
        )
        entries.append((path, content))

    target_directory.mkdir(parents=True, exist_ok=True)
    for path, content in entries:
        _atomic_write(path, content)

    for old_note in target_directory.glob("*.txt"):
        if old_note.name not in filenames and _is_generated_note(old_note):
            old_note.unlink()


def _is_generated_note(path: Path) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return False
    return (
        len(lines) >= 4
        and lines[0].startswith("课程:")
        and lines[1].startswith("作业:")
        and lines[2].startswith("截止时间:")
        and lines[3].startswith("链接:")
    )


def _safe_component(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" .")
    if cleaned.upper() in {
        "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))
    }:
        cleaned = f"_{cleaned}"
    return cleaned


def _validate_prefixes(prefixes) -> list[str]:
    prefixes = list(prefixes)
    if len(prefixes) != len(set(prefixes)):
        raise ValueError("生成的小纸条编号重复")
    return prefixes


def _limit_filename(value: str) -> str:
    if len(value) <= 150:
        return value
    suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
    return f"{value[:135]}-{suffix}"


def _atomic_write(path: Path, content: str) -> None:
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
