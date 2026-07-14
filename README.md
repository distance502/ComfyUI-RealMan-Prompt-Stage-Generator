# 真男人提示词阶段生成器

`ComfyUI-RealMan-Prompt-Stage-Generator` 是一个面向 ComfyUI 的阶段式提示词生成节点。它将标签选择、随机主题、模板风格、智能文本、Skill、本地/API 模型、设定图反推、标签块编排、NSFW 工作台、历史记录和严格去重整合到同一节点中。

## 主要功能

- 随机主题池、模板风格和运行时随机组合。
- 自然语言智能匹配与 Skill 提示词整理。
- 本地 GGUF、API 接口和仅 Skill 三种生成路径。
- 参考图片反推与角色设定图工作流。
- 标签块编排、用户标签库和预设/历史管理。
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

## 测试

```powershell
python -m unittest discover -s tests -p "test_*.py"
node --test tests/test_stage_prompt_ui_contracts.mjs
node --test tests/test_mini_toolbar_contracts.mjs
```

当前完整回归覆盖 Python 后端、安装迁移、主界面和迷你工具栏。

## 文档

完整中文说明参见 [使用说明书.md](./使用说明书.md)。
