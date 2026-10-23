# ChaoXing Stalker

超星学习通未提交作业查询与提醒工具。程序每次启动检查一次，列出所有未提交且未截止的作业，并将清单发送到配置的通知渠道。需要定期检查时，可使用 GitHub Actions 或其他外部调度器。

This tool checks ChaoXing for unsubmitted assignments that are still before their deadlines. Each run sends the current list through the configured notification channels and then exits.

## 功能

- 支持在一个配置文件中设置多个用户及各自的通知方式。
- 支持 QQ 邮箱 SMTP、ServerChan；未启用通知渠道时将结果打印到终端。
- 每次检查发送完整未提交作业清单，按截止时间从早到晚排序；已截止作业会过滤。
- 展示固定截止时间。平台没有提供明确日期时显示“未知”。
- 可选“小纸条模式”，在 Ubuntu 或 Windows 桌面指定文件夹中为作业创建文本文件。
- 网络请求失败时自动重试，并在启动时校验配置。

## 快速开始

```bash
pip install -r requirements.txt
python3 -m chaoxing_stalker --init-config
```

编辑生成的 `stalker_config.json`，填写超星账号和通知设置，然后运行一次检查：

```bash
python3 -m chaoxing_stalker
```

也可以指定其他配置文件：

```bash
python3 -m chaoxing_stalker --config my_config.json
```

## 配置

配置文件支持多个用户。下面是主要配置项示例：

```json
{
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
          "send_key": "your_serverchan_send_key"
        }
      },
      "notification_behaviour": {
        "notify_when_empty": false,
        "notify_on_error": true
      },
      "sticky_note": {
        "enabled": false,
        "folder_name": "学习通作业"
      }
    }
  ]
}
```

- QQ 邮箱的 `authorization_code` 是 SMTP 授权码，不是邮箱登录密码。
- `serverchan.send_key` 可在 [Server酱](https://sct.ftqq.com/) 获取。
- 将 `sticky_note.enabled` 设为 `true` 可启用小纸条模式。纸条保存在桌面下的 `folder_name` 文件夹中；文件夹不存在时会自动创建，默认名称为 `学习通作业`。
- 每项作业的文件名使用两位数字前缀和作业标题；重复运行会更新对应文件。每次检查按截止时间重新从 `00` 编号。相同标题会附加课程名以区分。
- `notification_behaviour.notify_when_empty` 控制无未提交作业时是否通知；`notify_on_error` 控制检查失败时是否通知。

## 定时运行

程序不会驻留后台。仓库中的 GitHub Actions workflow 按 cron 定时运行，也支持手动触发。Fork 后，在仓库 **Settings → Secrets and variables → Actions** 添加 `CONFIG_JSON` secret，值为完整配置 JSON。workflow 中的 cron 使用 UTC 时间。

本地也可以用系统计划任务定期执行：

```bash
python3 -m chaoxing_stalker
```

## 开发

```bash
python3 -m unittest discover -v
```

Python 应用代码位于 `chaoxing_stalker/` 包中；测试位于 `tests/`。核心抓取兼容类可从 `chaoxing_stalker.compat` 导入，也可用以下命令直接查询：

```bash
python3 -m chaoxing_stalker.compat <username> <password>
```

## 安全与平台说明

- `stalker_config.json` 包含账号、密码和通知密钥，已加入 `.gitignore`，不要提交到版本库。
- 也不要提交本地 `.env`、私钥或证书文件。Git 忽略规则不能替代凭据管理；如果凭据曾经提交，应在对应服务中撤销并重新生成。
- 超星页面结构和接口可能变化，抓取失败时需要重新检查相关页面或接口。
- 登录 AES 密钥来自超星登录页脚本；若平台更新认证流程，登录实现可能需要同步调整。

## 依赖

- Python 3.9+
- requests
- beautifulsoup4
- pycryptodome

项目采用 MIT License。
