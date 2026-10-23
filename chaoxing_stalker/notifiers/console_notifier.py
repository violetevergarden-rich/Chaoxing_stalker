"""Print notifications to the terminal when no delivery channel is enabled."""

from chaoxing_stalker.notifiers.base import Notifier


class ConsoleNotifier(Notifier):
    """Write the notification subject and body to standard output."""

    def send(self, subject: str, message: str) -> bool:
        print(f"\n{subject}\n{message}")
        return True

    @classmethod
    def from_config(cls, config: dict) -> "ConsoleNotifier":
        return cls()
