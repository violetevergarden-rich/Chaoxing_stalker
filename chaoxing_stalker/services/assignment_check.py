"""Run one user's assignment check and decide which notifications to send."""

import datetime
from collections.abc import Callable
from typing import Protocol

from chaoxing_stalker.assignment_types import Assignment
from chaoxing_stalker.message_formatter import format_message, sort_assignments_by_deadline
from chaoxing_stalker.notifiers.base import Notifier
from chaoxing_stalker.retry import retry
from chaoxing_stalker.sticky_notes import write_sticky_notes


class AssignmentProvider(Protocol):
    def get_unsubmitted_assignments(self) -> list[Assignment]: ...


AssignmentProviderFactory = Callable[[str, str], AssignmentProvider]


def check_and_notify(
    config: dict,
    notifiers: list[Notifier],
    assignment_provider_factory: AssignmentProviderFactory,
) -> bool:
    """Fetch assignments and send the full current list when work is pending."""
    user_name = config.get("name") or config["chaoxing"]["username"]

    try:
        provider = assignment_provider_factory(
            config["chaoxing"]["username"], config["chaoxing"]["password"]
        )

        @retry(max_attempts=3, base_delay=2)
        def fetch_assignments() -> list[Assignment]:
            return provider.get_unsubmitted_assignments()

        assignments = sort_assignments_by_deadline(fetch_assignments())
    except Exception as error:
        print(f"[ERROR] [{user_name}] 检查失败: {error}")
        if config.get("notification_behaviour", {}).get("notify_on_error", True):
            for notifier in notifiers:
                notifier.send(
                    f"[超星作业] {user_name} 检查失败",
                    f"用户: {user_name}\n错误信息: {error}",
                )
        return False

    notification_config = config.get("notification_behaviour", {})
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if config.get("sticky_note", {}).get("enabled", False):
        try:
            write_sticky_notes(
                user_name,
                assignments,
                folder_name=config.get("sticky_note", {}).get(
                    "folder_name", "学习通作业"
                ),
            )
        except OSError as error:
            print(f"[WARN] [{user_name}] 写入桌面纸条失败: {error}")

    if not assignments:
        notify_when_empty = notification_config.get(
            "notify_when_empty",
            notification_config.get("notify_on_no_change", False),
        )
        if notify_when_empty:
            print(f"[INFO] [{user_name}] 无未完成作业，按配置发送通知")
            for notifier in notifiers:
                notifier.send(
                    f"[超星作业提醒] {user_name} 无未提交作业",
                    f"用户: {user_name}\n检查时间: {now}\n未提交作业: 0 项",
                )
        else:
            print(f"[INFO] [{user_name}] 无未完成作业，跳过通知")
        return True

    print(f"[INFO] [{user_name}] 共 {len(assignments)} 项未提交作业，发送完整清单")
    body = format_message(assignments, now, user_name=user_name)
    subject = f"[超星作业提醒] {user_name} - {len(assignments)} 项未提交"
    _send_all(notifiers, subject, body)
    return True


def _send_all(notifiers: list[Notifier], subject: str, body: str) -> None:
    for notifier in notifiers:
        notifier.send(subject, body)
