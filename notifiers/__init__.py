from abc import ABC, abstractmethod


class Notifier(ABC):
    """通知器抽象基类"""

    @abstractmethod
    def send(self, subject: str, message: str) -> bool:
        """发送通知，成功返回 True，失败返回 False"""
        ...

    @classmethod
    @abstractmethod
    def from_config(cls, config: dict) -> "Notifier":
        """从配置字典构造通知器实例"""
        ...


def create_notifiers(config: dict) -> list[Notifier]:
    """根据配置实例化所有已启用的通知器"""
    notifiers = []

    if config.get("notifications", {}).get("email", {}).get("enabled", False):
        from notifiers.email_notifier import EmailNotifier
        notifiers.append(EmailNotifier.from_config(config["notifications"]["email"]))

    if config.get("notifications", {}).get("serverchan", {}).get("enabled", False):
        from notifiers.serverchan_notifier import ServerChanNotifier
        notifiers.append(
            ServerChanNotifier.from_config(config["notifications"]["serverchan"])
        )

    return notifiers
