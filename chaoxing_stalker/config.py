"""Configuration template, loading, and validation."""

import json
import os


DEFAULT_CONFIG_PATH = "stalker_config.json"

CONFIG_TEMPLATE = {
    "_version": 2,
    "_comment": "超星学习通作业定时提醒配置文件 - 多用户版",
    "users": [
        {
            "name": "你的名字",
            "chaoxing": {
                "username": "your_phone_or_username",
                "password": "your_password",
            },
            "notifications": {
                "email": {
                    "enabled": True,
                    "smtp_host": "smtp.qq.com",
                    "smtp_port": 465,
                    "use_ssl": True,
                    "sender": "your_email@qq.com",
                    "authorization_code": "your_smtp_auth_code",
                    "recipients": ["receiver@qq.com"],
                },
                "serverchan": {
                    "enabled": False,
                    "send_key": "your_send_key_from_sct_ftqq_com",
                },
            },
            "notification_behaviour": {
                "notify_when_empty": False,
                "notify_on_error": True,
            },
            "sticky_note": {
                "enabled": False,
                "folder_name": "学习通作业",
            },
        }
    ],
}


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    env_config = os.environ.get("CONFIG_JSON")
    if env_config:
        return json.loads(env_config)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"配置文件 {path} 不存在，且环境变量 CONFIG_JSON 未设置。"
            "\n在 GitHub Actions 中运行时，请在仓库 Secrets 中添加 CONFIG_JSON。"
            "\n本地运行时，请运行 python3 -m chaoxing_stalker --init-config 生成配置模板。"
        )
    with open(path, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def generate_config_template(path: str = DEFAULT_CONFIG_PATH) -> None:
    if os.path.exists(path):
        print(f"[WARN] {path} 已存在，跳过生成")
        return
    with open(path, "w", encoding="utf-8") as config_file:
        json.dump(CONFIG_TEMPLATE, config_file, ensure_ascii=False, indent=2)
    print(f"[INFO] 配置模板已生成: {path}")
    print("[INFO] 请编辑该文件，填写超星账号和通知设置后重新运行")


def validate_config(config: dict) -> None:
    errors = []
    users = config.get("users", [])
    if not users:
        errors.append("users 不能为空，至少配置一个用户")
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors))

    seen_usernames = set()
    for index, user in enumerate(users):
        prefix = f"users[{index}]"
        chaoxing_config = user.get("chaoxing", {})
        username = chaoxing_config.get("username", "")
        if not username:
            errors.append(f"{prefix}.chaoxing.username 不能为空")
        elif username in seen_usernames:
            errors.append(f"{prefix}.chaoxing.username '{username}' 重复")
        else:
            seen_usernames.add(username)
        if not chaoxing_config.get("password"):
            errors.append(f"{prefix}.chaoxing.password 不能为空")

        notifications = user.get("notifications", {})

        email_config = notifications.get("email", {})
        if email_config.get("enabled", False):
            required_fields = (
                "smtp_host",
                "smtp_port",
                "sender",
                "authorization_code",
                "recipients",
            )
            for field in required_fields:
                if not email_config.get(field):
                    errors.append(f"{prefix}.notifications.email.{field} 不能为空")

        serverchan_config = notifications.get("serverchan", {})
        if serverchan_config.get("enabled", False):
            if not serverchan_config.get("send_key"):
                errors.append(f"{prefix}.notifications.serverchan.send_key 不能为空")

    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {error}" for error in errors))
