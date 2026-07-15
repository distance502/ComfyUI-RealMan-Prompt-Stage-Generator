# 真男人提示词阶段生成器

`ComfyUI-RealMan-Prompt-Stage-Generator` 是一个面向 ComfyUI 的阶段式提示词生成节点。它将标签选择、随机主题、模板风格、智能文本、Skill、本地/API 模型、设定图反推、标签块编排、NSFW 工作台、历史记录和严格去重整合到同一节点中。

## 主要功能

- 随机主题池、模板风格和运行时随机组合。
- 自然语言智能匹配与 Skill 提示词整理。
- 本地 GGUF、API 接口和仅 Skill 三种生成路径。
- 参考图片反推与角色设定图工作流。
- 标签块编排、用户标签库和预设/历史管理。
- 内嵌网页浏览器与显式提示词联网搜索；候选标签可回填当前节点或加入标签库。
- 可选 NSFW 工作台及负面提示词同步。
- 连续生成避重、最终提示词严格去重和缓存隔离。
- 主界面与紧凑工具栏两种前端交互模式。

## 安装

将整个目录放入：

```text
ComfyUI/custom_nodes/ComfyUI-RealMan-Prompt-Stage-Generator
```

也可以在 Windows 上运行：

```text
内嵌安装到ComfyUI.bat
```

安装或更新后，请完全重启 ComfyUI，并在浏览器中按 `Ctrl+F5` 刷新前端缓存。

## 节点兼容性

- 显示名称：`真男人提示词阶段生成器`
- 内部节点类型：`QwenTE_StagePromptGenerator`

内部类型保持不变，因此旧工作流仍可继续加载。

## 依赖

主节点界面和仅 Skill 模式不要求额外模型依赖。以下功能按需安装：

- `llama-cpp-python`：本地 GGUF 模型。
- `opencv-python`、`rapidocr-onnxruntime`：图像质检与 OCR。

可使用 `一键检查依赖.bat` 和 `自动补装依赖.bat` 检查或补装可选依赖。

## 网页浏览器与提示词搜索

点击终端预览标题栏中的 `浏览器`。弹窗默认打开 `网页浏览器` 页签，可输入 `example.com`、完整 HTTPS 地址或普通搜索词，再点击 `打开`。弹窗打开时只显示本地主页，不会自动访问外部网站。

网页会在受限 iframe 中尽力加载。部分网站会通过安全策略禁止内嵌、登录或下载，此时使用地址栏右侧或网页内的 `外部打开`。地址栏会拒绝危险协议、带账号密码的网址、当前 ComfyUI 页面以及直接输入的本机/内网地址；这只是输入过滤，不是网络隔离，已打开的网页仍可能自行发起其他网络请求。

返回、前进和刷新只管理由地址栏或书签手动打开的网址。受浏览器同源限制，iframe 内点击链接后的真实 URL 无法同步到父页面；需要完整的站内导航、登录或下载时，请使用 `外部打开`。

切换到 `标签搜索` 页签，输入画面主题或风格关键词，再点击 `搜索`。节点会从公开提示词来源提取候选标签，并在在线来源不可用时回退到本地标签库。

标签搜索结果不会自动参与生成。勾选后可选择 `回填到自定义`，或明确执行批量入库。网页只在手动打开后访问；标签关键词只在点击 `搜索` 后发送到第三方来源，普通生成和仅 Skill 模式不会自动联网。

要启用通用网页搜索，请打开现有的 `online_search_config.json`，只修改其中的 SearXNG 地址和公开回退开关，不要用下面的片段覆盖整个文件：

```text
"searxng_base_url": "https://search.example.com",
"searxng_timeout_seconds": 8,
"public_source_fallback_enabled": false
```

也可在启动 ComfyUI 前设置环境变量 `QWEN_TE_SEARXNG_URL` 临时覆盖配置。SearXNG 返回有效结果后不会继续访问 Civitai 或 Lexica。将 `public_source_fallback_enabled` 设为 `false` 后，SearXNG 不可用或无结果时也不会访问公开来源，而是直接使用本地标签库回退；未配置 SearXNG 时该开关同样适用。

相同关键词的原始搜索样本会短时缓存，重复点击不会反复访问外部来源；标签是否已入库仍会按当前标签库重新计算。成功结果缓存约 3 分钟，全源失败只短暂缓存约 20 秒，网络恢复后无需长时间等待缓存失效。

SearXNG 实例必须启用 JSON 输出（`format=json`），当前只接受无账号信息的 HTTPS 地址，也不发送自定义认证头。本机自签名或企业 CA 可通过 `SSL_CERT_FILE` 或 `REQUESTS_CA_BUNDLE` 指定证书包；纯 HTTP 的 localhost 实例不会连接。公开仓库建议使用环境变量保存私有实例地址，避免误提交内部域名。

## 测试

```powershell
python -m unittest discover -s tests -p "test_*.py"
node --test tests/test_stage_prompt_ui_contracts.mjs
node --test tests/test_mini_toolbar_contracts.mjs
```

当前完整回归覆盖 Python 后端、安装迁移、主界面和迷你工具栏。

## 文档

完整中文说明参见 [使用说明书.md](./使用说明书.md)。
