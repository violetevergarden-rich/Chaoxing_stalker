# ChaoXing Stalker

超星学习通未提交作业查询与提醒工具，支持多用户、多通知渠道、定时执行。

查询超星学习通平台的所有课程，检查尚未提交且仍有剩余时间的作业，并通过邮件或 ServerChan 推送通知。已截止的作业会被自动过滤。支持单次执行、守护进程轮询，以及 GitHub Actions 定时运行。

A homework stalker for the ChaoXing (超星学习通) platform. It checks all courses for unsubmitted assignments that still have remaining time and sends notifications via email or ServerChan (WeChat push). Past-deadline assignments are automatically filtered out. Supports one-shot mode, daemon polling, and scheduled GitHub Actions.

## Features / 功能

- 多用户支持 — 一个配置文件管理多个超星账号，每个用户独立通知设置
- 多种通知渠道 — QQ 邮箱 SMTP、ServerChan 微信推送
- 截止过滤 — 自动过滤已截止作业，只提醒仍有剩余时间的未提交作业
- 变更检测 — SHA256 校验和，只在新增作业时通知
- 灵活调度 — 支持 cron 精确定时或 `run_hours` 窗口过滤两种模式
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
    "interval_minutes": 60,
    "window_minutes": 30
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
      },
      "run_hours": [8, 20]
    }
  ]
}
```

- `schedule.mode` — `"one_shot"` 运行一次后退出；`"daemon"` 按间隔持续轮询
- `schedule.window_minutes` — 时间窗口容差，当前北京时间距离目标小时在 ±N 分钟内则执行（默认 30）
- `run_hours` — 该用户的通知目标小时（北京时间 0-23），不配则每次唤醒都执行
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

通过 GitHub Actions 定时运行，无需常驻服务器。有两种调度模式可选。

### 部署步骤

1. Fork 本仓库
2. 在 Settings → Secrets → Actions 中添加 `CONFIG_JSON` secret（内容为 `stalker_config.json` 的完整 JSON）
3. 选择一种调度模式（见下方），修改 `.github/workflows/stalk.yml` 中的 cron 和 secret 中的 `run_hours`

也可以通过 `workflow_dispatch` 在 GitHub Actions 页面手动触发。

### 调度模式对比

项目支持两种调度方式，按需选择：

#### 模式 A：Cron 精确定时（推荐大多数用户）

cron 直接设在目标时刻，不配置 `run_hours`，每次触发必定执行。

```yaml
# .github/workflows/stalk.yml — 每天北京时间 12:03 和 18:03
- cron: "3 4,10 * * *"
```

```json
// stalker_config.json — 不配 run_hours 字段
{ "users": [{ "name": "张三", ... }] }
```

| 优点 | 缺点 |
|---|---|
| 简单直接，cron 时间 = 通知时间 | 改时间需要 commit + push workflow |
| 不会因窗口参数配错而漏通知 | 所有用户共用同一组触发时刻 |
| 无额外心智负担 | 高峰期可能延迟 10-50 分钟才执行（见下方说明） |

#### 模式 B：Run_hours 窗口过滤

cron 设为高频唤醒（如每小时），由每用户的 `run_hours` + `window_minutes` 在代码层面判断是否实际执行。

```yaml
# .github/workflows/stalk.yml — 每小时唤醒一次
- cron: "13 * * * *"
```

```json
// stalker_config.json — 每用户独立 run_hours
{ "users": [
    { "name": "张三", "run_hours": [8, 20] },
    { "name": "李四", "run_hours": [12, 18, 22] }
] }
```

| 优点 | 缺点 |
|---|---|
| 每用户独立通知时间 | 设计复杂，参数需要配合（cron 分钟数 + window_minutes + run_hours） |
| 改时间只需更新 Secret，不用 commit | 窗口判断依赖北京时间，cron 延迟太大会导致滑出窗口而漏通知 |
| 容忍 GitHub Actions 调度延迟 | `last_notify_slot` 去重依赖 `actions/cache`，跨 run 不一定持久 |
| 多用户场景灵活 | 高于实际需要的 run 次数 |

> **注意**: 模式 B 依赖 `cron 分钟数`、`window_minutes` 和 `run_hours` 三者配合。例如 `cron: "43 * * * *"` 配合 `window_minutes: 30` 和 `run_hours: [8]`，若 GitHub 延迟 40 分钟，实际运行时间可能滑出窗口导致漏通知。建议 `window_minutes` 不小于 45，或改用模式 A。

### 关于 GitHub Actions Cron 延迟

GitHub 官方文档明确说明 scheduled workflows 在负载高峰期间可能被推迟执行，且不提供准时 SLA。延迟原因：

- **共享 runner 池** — 免费版 public repo 的 job 需要排队，高负载时延迟加长
- **最低优先级** — `schedule` 触发事件的优先级低于 `push`、`PR`、`workflow_dispatch`
- **无 SLA** — GitHub 只保证"最终会执行"，不保证准时

实测中延迟 10-50 分钟属于正常范围，极端情况下可达数小时。这也是模式 B 存在的核心理由——用高频唤醒 + 宽窗口容忍不可控的调度延迟。模式 A 的用户需接受通知时间可能有半小时左右的偏差。

### 时间窗口机制（仅模式 B）

```text
cron 触发 07:13, 实际运行 07:15, run_hours=[8], window_minutes=30
  → 距 08:00 差 45min → 不在窗口内 → 跳过

cron 触发 07:43, 实际运行 07:46, run_hours=[8], window_minutes=30
  → 距 08:00 差 14min → 在窗口内 → 执行检查

cron 触发 08:13, 实际运行 08:15, run_hours=[8], window_minutes=30
  → 距 08:00 差 15min → 在窗口内 → 但已发过 → 跳过
```

每用户 `run_hours` 独立，不同用户可以配不同的通知时段。

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
