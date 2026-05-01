#!/usr/bin/env python3
"""
ChaoXing-Stalker 定时作业提醒脚本

用法:
    python3 stalker.py                    # 守护进程模式
    python3 stalker.py --one-shot         # 单次执行
    python3 stalker.py --init-config      # 生成配置模板
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time

from chaoXingStalker import ChaoXingStalker
from notifiers import create_notifiers

CONFIG_PATH = "stalker_config.json"
STATE_PATH = "stalker_state.json"


# ── 配置 ──────────────────────────────────────────────────

CONFIG_TEMPLATE = {
    "_version": 2,
    "_comment": "超星学习通作业定时提醒配置文件 - 多用户版",
    "schedule": {
        "mode": "one_shot",
        "interval_minutes": 60,
    },
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
                "notify_on_first_run": True,
                "notify_on_no_change": False,
                "notify_on_error": True,
            },
        }
    ],
}


def load_config(path: str) -> dict:
    env_config = os.environ.get("CONFIG_JSON")
    if env_config:
        return json.loads(env_config)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"配置文件 {path} 不存在，且环境变量 CONFIG_JSON 未设置。"
            "\n在 GitHub Actions 中运行时，请在仓库 Secrets 中添加 CONFIG_JSON。"
            "\n本地运行时，请运行 python3 stalker.py --init-config 生成配置模板。"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_config_template(path: str):
    if os.path.exists(path):
        print(f"[WARN] {path} 已存在，跳过生成")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(CONFIG_TEMPLATE, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 配置模板已生成: {path}")
    print("[INFO] 请编辑该文件，填写超星账号和通知设置后重新运行")


def validate_config(config: dict):
    errors = []

    schedule = config.get("schedule", {})
    if schedule.get("interval_minutes", 0) < 1:
        errors.append("schedule.interval_minutes 必须 >= 1")
    if schedule.get("mode") not in ("one_shot", "daemon"):
        errors.append('schedule.mode 必须是 "one_shot" 或 "daemon"')

    users = config.get("users", [])
    if not users:
        errors.append("users 不能为空，至少配置一个用户")
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))

    seen_usernames = set()
    for i, user in enumerate(users):
        prefix = f"users[{i}]"
        cx = user.get("chaoxing", {})
        username = cx.get("username", "")
        if not username:
            errors.append(f"{prefix}.chaoxing.username 不能为空")
        elif username in seen_usernames:
            errors.append(f"{prefix}.chaoxing.username '{username}' 重复")
        else:
            seen_usernames.add(username)
        if not cx.get("password"):
            errors.append(f"{prefix}.chaoxing.password 不能为空")

        notifications = user.get("notifications", {})
        has_enabled = False

        email_cfg = notifications.get("email", {})
        if email_cfg.get("enabled", False):
            has_enabled = True
            for key in ("smtp_host", "smtp_port", "sender", "authorization_code", "recipients"):
                if not email_cfg.get(key):
                    errors.append(f"{prefix}.notifications.email.{key} 不能为空")

        sc_cfg = notifications.get("serverchan", {})
        if sc_cfg.get("enabled", False):
            has_enabled = True
            if not sc_cfg.get("send_key"):
                errors.append(f"{prefix}.notifications.serverchan.send_key 不能为空")

        if not has_enabled:
            errors.append(f"{prefix}: 至少启用一种通知方式（email 或 serverchan）")

    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))


# ── 状态管理 ──────────────────────────────────────────────


def load_state(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_state(path: str, state: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _load_or_init_state() -> dict:
    state = load_state(STATE_PATH)
    if state is None or state.get("_version") != 2:
        if state is not None:
            print("[INFO] 检测到旧版 state 文件，重置为新格式")
        return {"_version": 2, "users": {}}
    return state


# ── 变更检测 ──────────────────────────────────────────────


def compute_checksum(assignments: list[dict]) -> str:
    serializable = sorted(assignments, key=lambda x: x.get("work_id", ""))
    raw = json.dumps(serializable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_changed_assignments(
    new_assignments: list[dict], old_assignments: list[dict]
) -> list[dict]:
    old_by_id = {a["work_id"]: a for a in old_assignments if a.get("work_id")}
    return [a for a in new_assignments if a.get("work_id") not in old_by_id]


# ── 消息格式化 ────────────────────────────────────────────


def format_message(
    assignments: list[dict],
    changed_assignments: list[dict],
    check_time: str,
    is_first_run: bool = False,
    user_name: str = "",
) -> str:
    lines = []
    lines.append("===== 超星学习通未提交作业提醒 =====")
    if user_name:
        lines.append(f"用户: {user_name}")
    lines.append(f"检查时间: {check_time}")
    lines.append(f"未提交作业总数: {len(assignments)} 项")
    lines.append("")

    if changed_assignments and not is_first_run:
        lines.append(f"--- 新增未提交作业 ({len(changed_assignments)}项) ---")
        for i, item in enumerate(changed_assignments, 1):
            lines.append(f"{i}. [{item['course_name']}] {item['title']}")
            if item.get("deadline"):
                lines.append(f"   截止时间: {item['deadline']}")
            if item.get("url"):
                lines.append(f"   链接: {item['url']}")
            lines.append("")

    if assignments:
        lines.append("--- 全部未提交作业 ---")
        for i, item in enumerate(assignments, 1):
            lines.append(f"{i}. [{item['course_name']}] {item['title']}")
            if item.get("deadline"):
                lines.append(f"   截止: {item['deadline']}")
            if item.get("url"):
                lines.append(f"   链接: {item['url']}")
            lines.append("")

    return "\n".join(lines)


# ── 重试装饰器 ────────────────────────────────────────────


def retry(max_attempts=3, base_delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError, OSError) as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        print(f"[WARN] 第 {attempt} 次失败，{delay}s 后重试...")
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator


# ── 核心检查逻辑 ──────────────────────────────────────────


def check_and_notify(
    config: dict, notifiers: list, state: dict | None
) -> tuple[dict | None, bool]:
    """
    执行一次检查并发送通知。
    返回 (new_state, success)。
    """
    user_name = config.get("name") or config["chaoxing"]["username"]

    try:
        stalker = ChaoXingStalker(
            config["chaoxing"]["username"], config["chaoxing"]["password"]
        )

        @retry(max_attempts=3, base_delay=2)
        def fetch():
            return stalker.get_unsubmitted_assignments()

        assignments = fetch()
    except Exception as e:
        print(f"[ERROR] [{user_name}] 检查失败: {e}")
        if config.get("notification_behaviour", {}).get("notify_on_error", True):
            for n in notifiers:
                n.send(
                    f"[超星作业] {user_name} 检查失败",
                    f"用户: {user_name}\n错误信息: {e}",
                )
        return state, False

    checksum = compute_checksum(assignments)
    old_checksum = state.get("last_checksum") if state else None
    is_first_run = state is None
    notify_cfg = config.get("notification_behaviour", {})
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not assignments:
        if notify_cfg.get("notify_on_no_change", False):
            print(f"[INFO] [{user_name}] 无未完成作业，按配置发送通知")
            for n in notifiers:
                n.send(
                    f"[超星作业提醒] {user_name} 无未提交作业",
                    f"用户: {user_name}\n检查时间: {now}\n未提交作业: 0 项",
                )
        else:
            print(f"[INFO] [{user_name}] 无未完成作业，跳过通知")
        new_state = {
            "last_checksum": checksum,
            "last_check_time": datetime.datetime.now().isoformat(),
            "last_assignments": assignments,
        }
        return new_state, True

    if is_first_run:
        print(f"[INFO] [{user_name}] 首次运行，共 {len(assignments)} 项未提交作业")
        if notify_cfg.get("notify_on_first_run", True):
            body = format_message(assignments, assignments, now, is_first_run=True, user_name=user_name)
            subject = f"[超星作业提醒] {user_name} - {len(assignments)} 项未提交"
            for n in notifiers:
                n.send(subject, body)
    elif checksum != old_checksum:
        old_assignments = state.get("last_assignments", [])
        changed = get_changed_assignments(assignments, old_assignments)
        print(f"[INFO] [{user_name}] 作业列表有变化，新增 {len(changed)} 项，共 {len(assignments)} 项")
        body = format_message(assignments, changed, now, user_name=user_name)
        subject = f"[超星作业提醒] {user_name} - {len(assignments)} 项未提交"
        for n in notifiers:
            n.send(subject, body)
    else:
        print(f"[INFO] [{user_name}] 无变化，仍 {len(assignments)} 项未提交")
        if notify_cfg.get("notify_on_no_change", False):
            body = format_message(assignments, [], now, user_name=user_name)
            subject = f"[超星作业提醒] {user_name} 无变化 - 仍 {len(assignments)} 项未提交"
            for n in notifiers:
                n.send(subject, body)

    new_state = {
        "last_checksum": checksum,
        "last_check_time": datetime.datetime.now().isoformat(),
        "last_assignments": assignments,
    }
    return new_state, True


# ── 运行模式 ──────────────────────────────────────────────


def run_one_shot(config: dict):
    full_state = _load_or_init_state()
    for user in config["users"]:
        try:
            username = user["chaoxing"]["username"]
            notifiers = create_notifiers(user)
            user_state = full_state["users"].get(username)
            new_state, ok = check_and_notify(user, notifiers, user_state)
            if new_state is not None:
                full_state["users"][username] = new_state
        except Exception as e:
            print(f"[ERROR] [{user.get('chaoxing', {}).get('username', '?')}] 处理失败: {e}")
    save_state(STATE_PATH, full_state)


def run_daemon(config: dict):
    interval = config["schedule"]["interval_minutes"] * 60

    print(f"[INFO] 守护进程启动，每 {config['schedule']['interval_minutes']} 分钟检查一次")
    print(f"[INFO] 共 {len(config['users'])} 个用户")

    while True:
        full_state = _load_or_init_state()
        for user in config["users"]:
            try:
                username = user["chaoxing"]["username"]
                notifiers = create_notifiers(user)
                user_state = full_state["users"].get(username)
                new_state, ok = check_and_notify(user, notifiers, user_state)
                if new_state is not None:
                    full_state["users"][username] = new_state
            except Exception as e:
                print(f"[ERROR] [{user.get('chaoxing', {}).get('username', '?')}] 处理失败: {e}")
        save_state(STATE_PATH, full_state)
        print(f"[INFO] 下次检查在 {config['schedule']['interval_minutes']} 分钟后...")
        time.sleep(interval)


# ── CLI 入口 ──────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="超星学习通作业定时提醒")
    parser.add_argument("--config", default=CONFIG_PATH, help="配置文件路径")
    parser.add_argument("--one-shot", action="store_true", help="单次运行模式")
    parser.add_argument("--init-config", action="store_true", help="生成配置模板")
    args = parser.parse_args()

    if args.init_config:
        generate_config_template(args.config)
        return

    config = load_config(args.config)
    validate_config(config)

    if args.one_shot or config["schedule"]["mode"] == "one_shot":
        run_one_shot(config)
    else:
        run_daemon(config)


if __name__ == "__main__":
    main()
