"""Create the configured notification delivery channels."""

from chaoxing_stalker.notifiers.base import Notifier
from chaoxing_stalker.notifiers.console_notifier import ConsoleNotifier


def create_notifiers(config: dict) -> list[Notifier]:
    notifiers = []
    notification_config = config.get("notifications", {})

    if notification_config.get("email", {}).get("enabled", False):
        from chaoxing_stalker.notifiers.email_notifier import EmailNotifier

        notifiers.append(EmailNotifier.from_config(notification_config["email"]))

    if notification_config.get("serverchan", {}).get("enabled", False):
        from chaoxing_stalker.notifiers.serverchan_notifier import ServerChanNotifier

        notifiers.append(
            ServerChanNotifier.from_config(notification_config["serverchan"])
        )

    if not notifiers:
        return [ConsoleNotifier()]
    return notifiers
