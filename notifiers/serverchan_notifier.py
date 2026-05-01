import requests

from notifiers import Notifier


class ServerChanNotifier(Notifier):
    """Server酱 微信推送通知"""

    SEND_URL = "https://sctapi.ftqq.com/{send_key}.send"

    def __init__(self, send_key: str):
        self.send_key = send_key

    @classmethod
    def from_config(cls, config: dict) -> "ServerChanNotifier":
        return cls(send_key=config["send_key"])

    def send(self, subject: str, message: str) -> bool:
        url = self.SEND_URL.format(send_key=self.send_key)
        payload = {"title": subject, "desp": message}
        try:
            resp = requests.post(url, data=payload, timeout=15)
            result = resp.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"[ERROR] Server酱 推送失败: {result.get('message', '未知错误')}")
                return False
        except (requests.RequestException, ValueError) as e:
            print(f"[ERROR] Server酱 请求失败: {e}")
            return False
