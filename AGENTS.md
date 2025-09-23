# AGENTS 指南

本文档记录了本次实现 `wework_notify` 自定义组件的思路、约束与后续建议，便于未来的代理/助理快速接手。

## 目标回顾

- 在 Home Assistant 中通过 config flow 添加企业微信通知入口。
- 支持两种类型：自建应用（默认收件人可配置）与群机器人。
- 自动化调用服务时可选消息类型（文本、Markdown、图片），并允许覆盖收件人。
- 编写易于理解的安装、配置与使用文档。

## 设计要点

- **服务而非 notify 平台**：直接在 `wework_notify` 域下注册 `send_message` 服务，避免与 Home Assistant 自带的 `notify` 平台耦合，也便于在自动化中传递自定义字段（图片、@ 成员等）。
- **配置项划分**：
  - `data` 中保存凭据信息及初始默认收件人，保证在没有 options 的情况下也能发送。
  - `options` 仅覆盖默认收件人，可随时通过 Options Flow 更新。
- **Token 缓存**：自建应用类型在本地缓存 access token，并对常见的 token 错误（40014/42001/40001）进行一次刷新重试，避免频繁向企业微信接口拉取。
- **收件人合并策略**：服务调用时会把手动指定的收件人与默认值合并并去重，避免重复推送并满足“自动化中可覆盖”的需求。
- **消息类型约束**：自建应用的图片消息要求 `media_id`，群机器人则要求 `base64 + md5`，通过服务 schema 和运行时校验确保参数完整。缺失字段会抛出 `HomeAssistantError`，方便在前端提示。

## 运行约束

- 当前未在配置阶段主动验证企业微信凭据，避免因网络或权限问题阻塞 config flow。首发失败时需查看日志。
- 群机器人暂未支持文件/卡片等其他消息类型；如后续需求，可在 `SUPPORTED_MESSAGE_TYPES` 中扩展。
- 图片 `media_id` 上传流程未内置，需要外部脚本或 CI 获取后写入自动化。

## 建议的后续工作

1. **异常分类与日志增强**：为常见错误码（如 81013、60020）提供更明确的提示。
2. **更多消息类型**：支持 `news`、`file`、`textcard` 等企业微信格式，或在 service schema 中扩展字段验证。
3. **缓存持久化**：如需频繁重启 Home Assistant，可考虑把 access token 缓存在内存外部（注意安全），减少启动后第一条消息的延迟。
4. **HACS 元数据**：若计划发布到 HACS，需要补充 `hacs.json` 并满足清单要求。
5. **测试覆盖**：可补充 pytest + pytest-homeassistant-custom-component 的单元测试，对 config flow 和服务调用做回归验证。
6. **文档国际化**：当前 README 以中文为主，可追加英文版或在 README 中加语言切换，方便海外环境使用。

## 参考

- 企业微信自建应用消息接口：https://developer.work.weixin.qq.com/document/path/90236
- 企业微信群机器人接口：https://developer.work.weixin.qq.com/document/path/91770

如需扩展或调试，可从 `custom_components/wework_notify/api.py` 入手，这里集中实现了所有网络调用与参数校验逻辑。
