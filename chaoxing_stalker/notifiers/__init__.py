"""Notification interfaces and compatibility exports."""

from chaoxing_stalker.notifiers.base import Notifier
from chaoxing_stalker.notifiers.factory import create_notifiers

__all__ = ["Notifier", "create_notifiers"]
