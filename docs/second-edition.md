# 第二版修改与真机验证

第二版面向希望保留上游手机控制功能、同时移除第三方使用统计的用户。源码基线为上游 0.3.16，提交为 `3ce9c080534e89fab91a237bf1c53a4a7e9d80a7`。早期尝试过限制更多功能的版本；本仓库发布保留截图和预览的第二版。[上游基线](https://github.com/zhongerxin/iPhone-use/tree/3ce9c080534e89fab91a237bf1c53a4a7e9d80a7)

## 相对上游的改动

| 范围 | 第二版的行为 | 对使用者的影响 |
| --- | --- | --- |
| 使用统计 | 移除 PostHog、Google Analytics 4 发送模块、事件调用、随包统计配置和统计面板模板 | 启动 App 等操作不再触发这两个统计服务的上报，原有统计环境变量无法重新启用发送端 |
| App 查找 | 移除 Apple 在线目录查询和目录更新脚本，使用设备已安装列表和内置目录 | 未命中时返回空结果；已知 bundle ID 的 App 仍可直接启动 |
| 服务健康检查 | 本地 WDA 状态探测拒绝 HTTP 重定向 | 健康检查不会跟随跳转访问其他地址 |
| 安装与适配 | 使用独立的本地插件市场 `iphone-use-no-telemetry`，同步更新 Codex、WorkBuddy 和豆包的安装与注册逻辑 | 保留原有 MCP 名称 `iphone_use` 及 20 个工具（18 个供模型调用，2 个供预览界面使用）；安装后应核对加载的是这个版本 |
| 回归测试 | 用模拟 WDA 测试启动、截图和离线查找，拦截测试中的 DNS 与套接字连接；覆盖旧统计配置及状态探测重定向 | 可以在 Mac 上复查这些路径的行为 |

保留 USB 控制、控件树、点击、滚动、输入、批处理、截图回退、实时预览、构建及恢复。上游作者的署名、许可证和第三方声明保留在仓库中。

## 2026-11-18 安装记录

1. 在 Mac 安装第二版插件，将缓存中的服务注册为 Codex MCP，并准备固定提交的 WebDriverAgent 16.14.0 源码和 USB 转发依赖。
2. 安装完整 Xcode 并完成首次启动；通过 USB 配对 iPhone，用自己的 Apple 开发团队签名。本次使用 Apple 官方 WWDR G3 中间证书补齐本机签名链。
3. 在 iPhone 开启开发者模式，重启后确认开启。Xcode 成功构建并安装 WebDriverAgentRunner。首次启动时按手机提示信任自己的开发者证书，并在启动期间保持手机解锁。
4. 在 iPhone 17、iOS 26.7.2、Xcode 27.2 的组合上，通过 `pua_ready(recover=true, screenshot=false)` 验证会话、前台 App 和页面读取。再用 `pua_launch_app` 打开系统计算器，工具返回 `foreground_verified=true`。

在另一台 Mac 上可从这个 fork 安装，再按 README 完成自己的设备配对和签名。

```sh
git clone https://github.com/ryan-yr/iPhone-use.git
cd iPhone-use
sh scripts/install.sh
```

[安装说明](../README.md) · [数据去向](../ANALYTICS.md)

## 网络与数据边界

安装时可能访问 GitHub 和 npm 下载依赖，Xcode 会联系 Apple 完成开发签名。使用云端 Codex 时，按任务读取的控件文字或截图可进入模型会话。观察截图沿用上游的 Mac 本地缓存策略。其他手机 App 的联网行为由各 App 决定。

本次验证中，Mac 的 USB 转发监听回环地址；同一台 Mac 也能通过 iPhone 的局域网地址读取 WDA 的状态端点。第二版保留了上游手机端的监听行为。应将能访问该网络的设备纳入信任范围。这项检查只验证了状态端点的可达性。

## 同一任务的工具文本对比

两组均从主屏幕打开计算器，并核实它已在前台。USB 组用一次调用启动并验证；Mac 镜像组用 Spotlight 启动，再用关闭截图的 OCR 读取计算器按键。

| 成功复测 | 调用次数 | 参数 tokens | 返回文字 tokens | 合计 |
| --- | ---: | ---: | ---: | ---: |
| iPhone Use，经 USB | 1 | 13 | 43 | 56 |
| Mac iPhone 镜像，经 Spotlight 和 OCR | 2 | 43 | 284 | 327 |

按 `o200k_base` 对成功复测的工具参数和返回文字分词，两组均未传截图。镜像首次一键启动失败，排查时使用过截图。准备、失败重试、工具定义、对话历史及模型生成均未计入。这个样例描述工具文本开销，无法据此推算其他任务或整段对话的计费。
