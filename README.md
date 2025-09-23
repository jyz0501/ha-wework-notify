# WeWork Notify 自定义组件

`wework_notify` 是一个 Home Assistant 自定义组件，帮助你在自动化或脚本中向企业微信（WeCom）发送消息。组件支持两种接入方式：企业微信自建应用以及企业微信群机器人，提供 UI 配置、默认收件人设置，以及在服务调用时覆盖收件人、选择不同消息类型（文本、Markdown、图片）等能力。

## 功能特性

- 通过 Home Assistant 前端完成配置，无需手工修改 YAML。
- 支持配置多个企业微信入口，每个入口都可以是自建应用或群机器人。
- 自建应用可设置默认通知对象（成员 / 部门 / 标签），自动化中可以再次覆盖。
- 服务调用支持发送文本、Markdown、图片消息。
- 群机器人支持 @指定成员或手机号。
- 通过 Options Flow 随时调整默认收件人。

## 安装步骤

1. 将本仓库中的 `custom_components/wework_notify` 文件夹复制到你的 Home Assistant 配置目录的 `custom_components` 下，例如：
   ```text
   /config/custom_components/wework_notify
   ```
2. 重启 Home Assistant。
3. 在“设置 → 设备与服务”页面点击右下角“添加集成”，搜索 `WeWork Notify`。

> **提示**：如果使用 HACS，可以将本仓库作为自定义仓库添加，然后从 HACS 中安装。

## 配置向导

### 1. 选择入口类型

在首次添加时需输入集成名称，并选择入口类型：
- **WeCom Custom Application**：企业微信自建应用。
- **WeCom Group Robot**：企业微信群机器人。

### 2. 自建应用字段说明

| 字段 | 说明 |
| ---- | ---- |
| Corp ID | 企业 ID（可在企业微信管理后台获取）。 |
| Corp Secret | 自建应用的 Secret。 |
| Agent ID | 自建应用的 AgentID。 |
| Default users | （可选）默认成员 ID，使用 `\|` 分隔，例如 `zhangsan\|lisi`。 |
| Default parties | （可选）默认部门 ID，同样使用 `\|` 分隔。 |
| Default tags | （可选）默认标签 ID，同样使用 `\|` 分隔。 |

> 默认收件人在发送消息时会自动生效，也可以在自动化中覆盖。

### 3. 群机器人字段说明

| 字段 | 说明 |
| ---- | ---- |
| Webhook key | 群机器人 Webhook URL 中的 `key` 值。 |

### 4. 后续调整

- 对于自建应用入口，可在“集成”卡片中点击“配置”进入 Options Flow，再次调整默认成员 / 部门 / 标签。
- 对于群机器人入口没有额外配置项。

## 服务调用

组件会注册服务：

```
wework_notify.send_message
```

常用服务字段如下：

| 字段 | 适用范围 | 说明 |
| ---- | -------- | ---- |
| `config_entry` | 通用 | 在服务 UI 中下拉选择入口（推荐）。 |
| `entry_id` / `entry_title` | 通用 | 手动指定入口（与 `config_entry` 互斥），`entry_title` 为配置时输入的名称。 |
| `message_type` | 通用 | 消息类型，可选 `text`（默认）、`markdown`、`image`。 |
| `message` | 文本/Markdown | 消息正文。 |
| `to_user` / `to_party` / `to_tag` | 自建应用 | 覆盖默认收件人，使用 `|` 分隔多个值。会与默认收件人合并去重。 |
| `mentioned_list` / `mentioned_mobile_list` | 群机器人 | 对文本消息 @ 成员或手机号，多个值使用 `|` 分隔。 |
| `image_media_id` | 自建应用 + 图片 | 发送图片时必填。需要提前调用企业微信素材接口上传，获得 `media_id`。 |
| `image_base64` / `image_md5` | 群机器人 + 图片 | 发送图片时必填。`image_base64` 为文件的 Base64，`image_md5` 为原始二进制的 MD5。 |

> **注意**：对于图片消息，企业微信不同入口的要求不同，请确保提供正确的参数。

## 自动化示例

### 文本消息（自建应用，使用默认收件人）

```yaml
alias: Alert via WeCom App
trigger:
  - platform: state
    entity_id: binary_sensor.door
    to: 'on'
action:
  - service: wework_notify.send_message
    data:
      entry_title: "运营通知"
      message_type: text
      message: "前门被打开，请确认。"
```

### 指定收件人 + Markdown（自建应用）

```yaml
service: wework_notify.send_message
data:
  entry_title: "运营通知"
  message_type: markdown
  message: "**温馨提示**\n> 新版本已在 <font color=\"warning\">生产</font> 环境发布"
  to_user: "zhangsan|lisi"
  to_party: "2"
```

### 图片消息（自建应用，需要 `media_id`）

```yaml
service: wework_notify.send_message
data:
  entry_id: "YOUR_ENTRY_ID"
  message_type: image
  image_media_id: "3FgFG9l2sJdX0abc123"
  to_user: "@all"
```

> 获取 `media_id`：调用 `https://qyapi.weixin.qq.com/cgi-bin/media/upload` 接口上传临时素材，保留返回的 `media_id`。

### 群机器人文本 + @ 指定成员

```yaml
service: wework_notify.send_message
data:
  entry_title: "研发群机器人"
  message: "发布完成，大家辛苦！"
  mentioned_list: "zhangsan|lisi"
```

### 群机器人发送图片

```yaml
service: wework_notify.send_message
data:
  entry_title: "研发群机器人"
  message_type: image
  image_base64: !secret wework_robot_sample_image_base64
  image_md5: "d41d8cd98f00b204e9800998ecf8427e"
```

> 计算 MD5：`md5sum image.jpg`。Base64 可以通过 `base64 < image.jpg` 获取。

## 常见问题

- **能否同时配置多个入口？** 可以，多次添加集成即可，每次选择不同的入口类型或凭据。
- **如何查看 `entry_id`？** 在“开发者工具 → 服务”页面，当选择服务 `wework_notify.send_message` 时下方会显示 `entry_id` 列表；也可在 `.storage/core.config_entries` 中查找。
- **默认收件人如何与临时收件人合并？** 服务调用时会把你填写的 `to_user`/`to_party`/`to_tag` 与默认值合并并去重。
- **是否会校验凭据？** 组件不会在配置阶段主动调用企业微信 API，避免网络问题导致配置失败。首次发送消息失败时可在日志中查看具体报错。

## 更新日志

- `1.0.0`：首个版本，提供自建应用和群机器人通知能力，支持文本/Markdown/图片消息、默认收件人和 Options Flow。

## 授权协议

MIT License
