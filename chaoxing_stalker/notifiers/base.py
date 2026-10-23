"""Notifier interface shared by all delivery channels."""

from abc import ABC, abstractmethod


class Notifier(ABC):
    """Common interface for notification delivery implementations."""

    @abstractmethod
    def send(self, subject: str, message: str) -> bool:
        """Send a notification; return whether delivery succeeded."""

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "Notifier":
        """Build a notifier from its channel-specific configuration."""
