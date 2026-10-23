"""Format assignment notifications as readable plain text."""

from chaoxing_stalker.assignment_types import Assignment


def sort_assignments_by_deadline(assignments: list[Assignment]) -> list[Assignment]:
    """Sort known deadlines first, with unknown dates at the end."""
    return sorted(
        assignments,
        key=lambda assignment: (
            not bool(assignment.get("deadline", "").strip()),
            assignment.get("deadline", "").strip(),
            assignment.get("course_name", "").casefold(),
            assignment.get("title", "").casefold(),
        ),
    )


def format_message(
    assignments: list[Assignment],
    check_time: str,
    user_name: str = "",
) -> str:
    lines = ["===== 超星学习通未提交作业提醒 ====="]
    if user_name:
        lines.append(f"用户: {user_name}")
    lines.append(f"检查时间: {check_time}")
    lines.append(f"未提交作业总数: {len(assignments)} 项")
    lines.append("")

    if assignments:
        lines.append("--- 全部未提交作业 ---")
        _append_assignments(lines, sort_assignments_by_deadline(assignments))

    return "\n".join(lines)


def _append_assignments(lines: list[str], assignments: list[Assignment]) -> None:
    for index, assignment in enumerate(assignments, 1):
        lines.append(f"{index}. [{assignment['course_name']}] {assignment['title']}")
        lines.append(f"   截止时间: {assignment.get('deadline') or '未知'}")
        if assignment.get("url"):
            lines.append(f"   链接: {assignment['url']}")
        lines.append("")
