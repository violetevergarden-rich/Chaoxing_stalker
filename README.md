# ChaoXing Stalker

超星学习通未提交作业查询与提醒工具，支持多用户、多通知渠道、定时执行。

查询超星学习通平台的所有课程，检查未提交的作业，并通过邮件或 ServerChan 推送通知。支持单次执行、守护进程轮询，以及 GitHub Actions 定时运行。

A homework stalker for the ChaoXing (超星学习通) platform. It checks all courses for unsubmitted assignments and sends notifications via email or ServerChan (WeChat push). Supports one-shot mode, daemon polling, and scheduled GitHub Actions.

## Features / 功能

- 多用户支持 — 一个配置文件管理多个超星账号
- 多种通知渠道 — QQ 邮箱 SMTP、ServerChan 微信推送
- 变更检测 — SHA256 校验和，只在新增作业时通知
- 运行模式 — 单次检查 / 守护进程轮询 / GitHub Actions 定时
- 配置验证 — 启动时检查配置完整性
- 容错重试 — 网络异常自动重试（指数退避）

## Quick Start / 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成配置文件
python3 stalker.py --init-config

# 编辑 stalker_config.json，填写账号和通知设置
vim stalker_config.json

# 单次运行
python3 stalker.py --one-shot
```

## Configuration / 配置文件

`stalker_config.json`:

```json
{
  "schedule": {
    "mode": "one_shot",
    "interval_minutes": 60
  },
  "users": [
    {
      "name": "张三",
      "chaoxing": {
        "username": "your_phone_number",
        "password": "your_password"
      },
      "notifications": {
        "email": {
          "enabled": true,
          "smtp_host": "smtp.qq.com",
          "smtp_port": 465,
          "use_ssl": true,
          "sender": "sender@qq.com",
          "authorization_code": "your_smtp_auth_code",
          "recipients": ["receiver@qq.com"]
        },
        "serverchan": {
          "enabled": false,
          "send_key": "SCT..."
        }
      },
      "notification_behaviour": {
        "notify_on_first_run": true,
        "notify_on_no_change": false,
        "notify_on_error": true
      }
    }
  ]
}
```

- `schedule.mode` — `"one_shot"` 运行一次后退出；`"daemon"` 按间隔持续轮询
- Email `authorization_code` 是 QQ 邮箱 SMTP 授权码，不是邮箱密码
- ServerChan `send_key` 从 [sct.ftqq.com](https://sct.ftqq.com) 获取

## Usage / 用法

```bash
# 生成配置模板
python3 stalker.py --init-config

# 单次执行（从配置文件读取模式）
python3 stalker.py --one-shot

# 守护进程模式
python3 stalker.py

# 指定配置文件
python3 stalker.py --config my_config.json --one-shot

# 直接使用核心库
python3 chaoXingStalker.py <username> <password>
```

## GitHub Actions

通过 GitHub Actions 每天定时运行，无需常驻服务器。

1. Fork 本仓库
2. 在 Settings → Secrets → Actions 中添加 `CONFIG_JSON` secret（内容为 `stalker_config.json` 的完整 JSON）
3. GitHub Actions 将在北京时间 8:00 和 20:00 自动运行

修改 `.github/workflows/stalk.yml` 中的 cron 表达式可调整执行时间（UTC 时区）。

## Notification Behaviour / 通知行为

| 配置项 | 说明 |
|---|---|
| `notify_on_first_run` | 首次运行时发送通知 |
| `notify_on_no_change` | 无变化时也发送通知 |
| `notify_on_error` | 检查出错时发送通知 |

## Architecture / 架构

```
chaoXingStalker.py     核心库：登录、课程/作业抓取
stalker.py             调度器：轮询循环、变更检测、CLI
notifiers/
  __init__.py          通知器抽象基类 + 工厂函数
  email_notifier.py    QQ 邮箱 SMTP 通知
  serverchan_notifier.py  ServerChan 微信推送
stalker_config.json    用户配置
stalker_state.json     持久化状态（校验和、作业列表）
```

## Dependencies / 依赖

- Python 3.9+
- requests
- beautifulsoup4
- pycryptodome

## Important Notes / 注意事项

- `stalker_config.json` 包含真实密码和授权码，不要提交到 Git（已在 `.gitignore` 中）
- 超星平台 HTML 结构和 API 可能随时变化，如遇到抓取失败请检查页面结构
- AES 密钥 (`u2oh6Vu^HWe4_AES`) 提取自超星登录页 JS，若超星更新需同步修改

## License

MIT
