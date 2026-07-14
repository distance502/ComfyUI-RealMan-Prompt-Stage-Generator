# NSFW Prompt Selector 并入阶段节点设计

## 目标

把 `F:/ComfyUI-NSFW-PromptSelector` 的核心能力整合进当前 `comfyUI-qwen3_5-llama-TE` 节点体系，让用户在同一个节点面板内完成：

- NSFW 触发词多选
- 场景 / 动作 / 服饰 / 情绪 / 运镜等结构化选择
- 负面提示词预设切换
- 结果一键写回当前阶段节点

同时保持现有普通标签工作流、随机主题池、历史、连测、示例和在线扩展能力不被破坏。

## 成功标准

- 用户不需要再单独放置 `NSFWPromptSelector` 节点，也能在当前阶段节点里完成等价核心操作。
- NSFW 工作流与现有普通标签工作流共存，但默认界面与状态清晰隔离。
- NSFW 选择结果能稳定映射到当前节点的 `selected/custom_tags/negative_prompt` 结构。
- 推荐负面词与 NSFW 负面预设可以共存，并有明确优先级。
- 现有普通模式、随机主题池和五模式优化逻辑不回归。

## 非目标

- 不原样复制 `ComfyUI-NSFW-PromptSelector` 的全部文件和全部输入控件。
- 不把当前阶段节点改成两套完全独立的后端节点。
- 不在第一版里重做现有标签库的数据格式。
- 不在第一版里做“自动混合普通标签库和 NSFW 结构化词库”的复杂推荐系统。

## 推荐方案

采用“工作台并入”方案：

### 1. 后端保留单节点

继续使用当前 `QwenTE_StagePromptGenerator / QwenTE_UniversalStagePromptGenerator`。

新增一层 `nsfw_workspace` 状态模型，但不新增一套平行节点类型。

### 2. 前端新增 NSFW 工作台

在当前大面板内部新增一个 `NSFW` 工作台，而不是新增独立节点或完全独立弹窗体系。

该工作台负责：

- 多选触发词
- 场景 / 动作 / 服饰 / 情绪 / 运镜 / 光线 / 镜头等结构化选择
- 随机选择与预设配置
- 负面提示词预设选择
- 一键“写回当前节点”

### 3. 建立映射层而不是硬拼字符串

不直接把 `PromptSelector` 拼出来的整段 prompt 当成最终结果写死。

而是先把选择结果映射为：

- 可归组标签：回填进 `selected`
- 非归组语义：写入 `customTags`
- 负面词：写入独立 NSFW 负面状态，再决定是否覆盖推荐负面词

这样可以继续复用当前节点已有的：

- 标签摘要
- JSON结果
- 历史
- 随机与回退
- 负面词同步

## 结构设计

### 后端数据结构

新增一个轻量 NSFW 工作台状态，建议形态：

- `nsfw_workspace.enabled: bool`
- `nsfw_workspace.trigger_words: list[str]`
- `nsfw_workspace.scene: str`
- `nsfw_workspace.action: str`
- `nsfw_workspace.outfit: str`
- `nsfw_workspace.mood: str`
- `nsfw_workspace.camera_movement: str`
- `nsfw_workspace.camera_angle: str`
- `nsfw_workspace.light_source: str`
- `nsfw_workspace.light_type: str`
- `nsfw_workspace.lens_type: str`
- `nsfw_workspace.focal_length: str`
- `nsfw_workspace.color_tone: str`
- `nsfw_workspace.visual_style: str`
- `nsfw_workspace.effect: str`
- `nsfw_workspace.filter: str`
- `nsfw_workspace.random_mode: str`
- `nsfw_workspace.preset: str`
- `nsfw_workspace.quality_tier: str`
- `nsfw_workspace.negative_preset: str`
- `nsfw_workspace.custom_negative: str`

### 映射职责

新增一层 `nsfw_mapper` 负责三件事：

1. 解析 `ComfyUI-NSFW-PromptSelector` 的词库与预设
2. 把结构化选择转换为当前节点可消费的标签/补充词
3. 产出负面提示词候选与完整摘要

### 前端职责

前端 `stage_prompt_generator_ui.js` 负责：

- 展示 NSFW 工作台
- 保存/恢复 NSFW 工作台状态
- 调用映射层预览结果
- 把预览结果回写到当前节点主状态

## 数据流

### 从 NSFW 工作台到当前节点

1. 用户在 `NSFW` 工作台选择触发词、场景、动作等
2. 前端把选择结果组织成 `nsfw_workspace`
3. 映射层把可识别项写入当前节点：
   - 能归组的词进入 `selected`
   - 不能归组的词进入 `customTags`
4. 负面提示词预设单独保存
5. 用户可以选择：
   - 只预览
   - 写回当前节点
   - 写回并同步负面词

### 与现有推荐负面词的关系

第一版采用明确优先级：

1. 若开启 `NSFW 负面预设覆盖`，则优先使用 NSFW 负面预设
2. 否则保留现有推荐负面词
3. 若两者都存在，可选择追加合并，但默认不自动混合

## 功能分期

### Phase 1

- 引入 NSFW 词库和预设
- 增加 NSFW 工作台
- 支持结构化选择、预览、写回当前节点
- 支持负面词预设切换

### Phase 2

- NSFW 工作台结果进入历史/回退
- 支持批量预设、示例、连测使用 NSFW 工作台结果

### Phase 3

- 如有必要，再考虑普通标签库与 NSFW 词库的联合推荐

## 需要修改的文件

- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_generator.py`
- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/web/stage_prompt_generator_ui.js`
- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py`
- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_regression_runner.py`

建议新增：

- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_workspace.py`
- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_mapper.py`
- `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_presets.py`

## 测试策略

### 后端

- 映射层能把结构化 NSFW 选择正确分配到 `selected/customTags`
- 负面提示词预设选择正确
- 不影响现有普通模式和随机主题池链路

### 前端

- NSFW 工作台状态可保存/恢复
- 写回当前节点后摘要、历史、JSON结果一致
- 不破坏现有普通标签弹窗、示例、预设、联机与回退

### Live

- 在当前阶段节点内完成一次 NSFW 结构化选择
- 写回节点后成功生成正向/负向
- 负面词同步链路正常

## 风险

- 当前节点前端已经很大，直接平铺全部 NSFW 控件会让 UI 失控
- `NSFWPromptSelector` 原本是“拼字符串导出”，而当前节点是“结构化状态 -> 生成”，两者直接硬拼会导致状态不一致
- 负面词优先级如果不设计清楚，容易和现有推荐负面词互相覆盖

## 风险控制

- 第一版只做工作台，不做全局平铺
- 第一版优先做“结构化映射”，不直接把完整 prompt 拼接结果塞回主节点
- 第一版给负面词覆盖逻辑设置显式开关，默认不静默覆盖
