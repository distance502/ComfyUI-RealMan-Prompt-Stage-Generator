---
status: active
summary: 按最小改动实现 TEmini 的语义统一、反馈补齐和清空确认。
last_updated: 2026-06-21
implements: specs/2026-06-21-temini-minimal-usability-fix.md
---

# TEMini Minimal Usability Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以最小改动修正 `TEMini` 的按钮语义漂移、关键操作反馈缺失与危险清空无确认问题。

**Architecture:** 只修改 `web/stage_prompt_generator_mini_toolbar.js`，复用节点现有 widget、随机状态和输出数据通道，不改主面板、不加新按钮。先统一 mini 与主面板同名按钮的行为，再补顶部状态与操作反馈。

**Tech Stack:** ComfyUI frontend JavaScript, LiteGraph node widgets, existing stage prompt node runtime state

## Global Constraints

- 只改 `TEMini`，不改主 stage panel。
- 不新增按钮，不重做布局。
- `随机` 改为“生成随机状态但不入队”。
- `复制` 改为复制最近一次正向提示词输出，而不是已选标签。
- `清空` 只清当前标签与自定义标签，不碰其他设置。
- 当前会话环境缺少可直接使用的 `git` 命令链路，计划中的 commit 步骤仅保留为执行占位，不在本轮验证中承诺完成。

---

### Task 1: 统一 TEMini 的按钮语义

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\worktrees\comfyui-style-mode-random-pool-optimization\custom_nodes\comfyUI-qwen3_5-llama-TE\web\stage_prompt_generator_mini_toolbar.js`

**Interfaces:**
- Consumes: existing widget helpers `getWidget(...)`, `setWidgetValue(...)`
- Consumes: existing queue helper `queueWorkflow() -> boolean`
- Produces: `随机` = fresh random state without queue
- Produces: `复制` = latest positive prompt output text
- Produces: `清空` = confirmed clear of current raw/custom tag inputs only

- [ ] **Step 1: Add a failing behavior checklist in comments beside the mini button handlers**

```js
// Expected behavior after this task:
// - "随机" builds a fresh random state and does not auto-queue.
// - "复制" copies the latest positive prompt output, not selected tags.
// - "清空" asks for confirmation before clearing current selections.
```

- [ ] **Step 2: Replace mini `随机` logic so it matches the main panel semantic**

```js
random: createMiniButton("随机", "warm", async () => {
	const buildRandomState = globalThis.__QWEN_TE_STAGE_BUILD_RANDOM_STATE__;
	const applyNodeState = globalThis.__QWEN_TE_STAGE_APPLY_NODE_STATE__;
	const getFreshLibraryForUi = globalThis.__QWEN_TE_STAGE_GET_FRESH_LIBRARY__;
	if (typeof buildRandomState !== "function" || typeof applyNodeState !== "function" || typeof getFreshLibraryForUi !== "function") {
		setMiniStatus(node, "随机功能暂不可用。");
		return;
	}
	const library = await getFreshLibraryForUi(node);
	const nextState = await buildRandomState(node, library);
	applyNodeState(node, library, nextState, { recordHistory: true, historySource: "random" });
	setMiniStatus(node, "已随机生成当前标签组合。");
	refreshMiniToolbar(node);
}),
```

- [ ] **Step 3: Replace mini `复制` logic to use latest positive prompt output**

```js
copy: createMiniButton("复制", "", async () => {
	const getStagePromptOutputText = globalThis.__QWEN_TE_STAGE_GET_PROMPT_OUTPUT__;
	if (typeof getStagePromptOutputText !== "function") {
		setMiniStatus(node, "复制功能暂不可用。");
		return;
	}
	const text = getStagePromptOutputText(node);
	if (!text) {
		setMiniStatus(node, "还没有可复制的提示词，请先运行一次节点。");
		return;
	}
	const ok = await copyText(text);
	setMiniStatus(node, ok ? "已复制正向提示词。" : "复制失败，剪贴板不可用。");
}),
```

- [ ] **Step 4: Add confirmation to mini `清空`**

```js
clear: createMiniButton("清空", "danger", async () => {
	const confirmed = window.confirm("将清空当前标签选择，确定继续吗？");
	if (!confirmed) {
		setMiniStatus(node, "已取消清空。");
		return;
	}
	for (const widgetName of rawTagWidgetNames) {
		if (widgetName === CUSTOM_TAG_WIDGET) setWidgetValue(node, widgetName, "");
		else setWidgetValue(node, widgetName, "无");
	}
	setMiniStatus(node, "已清空当前标签选择。");
	refreshMiniToolbar(node);
}),
```

- [ ] **Step 5: Run a manual smoke check inside ComfyUI**

Run:

```powershell
# reload the custom node frontend in the active ComfyUI session, then manually verify:
# 1. 点击“随机”后标签变化，但不会自动入队
# 2. 点击“复制”时复制的是正向提示词输出
# 3. 未生成时点击“复制”会提示先运行
# 4. 点击“清空”会先弹确认
```

Expected: all four interactions behave exactly as the spec describes.

---

### Task 2: 收紧 TEMini 顶部状态与关键操作反馈

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\worktrees\comfyui-style-mode-random-pool-optimization\custom_nodes\comfyUI-qwen3_5-llama-TE\web\stage_prompt_generator_mini_toolbar.js`

**Interfaces:**
- Consumes: `copyText(text: string) -> Promise<boolean>`
- Consumes: `queueWorkflow() -> boolean`
- Produces: base status summary driven by operational state instead of fold-state noise
- Produces: transient feedback messages for `随机 / 复制 / 入队 / 清空`

- [ ] **Step 1: Introduce a mini status cache for transient feedback**

```js
const MINI_STATUS_TEXT_KEY = Symbol("qwenTeMiniStatusText");

function setMiniStatus(node, message) {
	node[MINI_STATUS_TEXT_KEY] = String(message ?? "").trim();
	refreshMiniToolbar(node);
}
```

- [ ] **Step 2: Replace the current header summary builder**

```js
function buildToolbarStatus(node, state) {
	if (node?.[MINI_STATUS_TEXT_KEY]) return node[MINI_STATUS_TEXT_KEY];
	const selectedText = buildSelectedTagsText(node);
	const count = selectedText ? selectedText.split(/\s*,\s*/u).filter(Boolean).length : 0;
	const randomEnabled = !!getWidget(node, RANDOM_TOGGLE_WIDGET)?.value;
	const suppressEnabled = !!getWidget(node, SUPPRESS_TEXT_WIDGET)?.value;
	const getStagePromptOutputText = globalThis.__QWEN_TE_STAGE_GET_PROMPT_OUTPUT__;
	const hasPrompt = typeof getStagePromptOutputText === "function" ? !!String(getStagePromptOutputText(node) ?? "").trim() : false;
	const bits = [`已选 ${count}`];
	if (randomEnabled) bits.push("随机 ON");
	if (suppressEnabled) bits.push("抑字 ON");
	bits.push(hasPrompt ? "可复制正向" : "未生成");
	return bits.join(" · ");
}
```

- [ ] **Step 3: Add explicit feedback to mini `入队`**

```js
queue: createMiniButton("入队", "primary", async () => {
	const ok = queueWorkflow();
	setMiniStatus(node, ok ? "已加入队列。" : "入队失败，请检查队列按钮。");
}),
```

- [ ] **Step 4: Clear transient status during passive refresh when appropriate**

```js
function refreshMiniToolbar(node) {
	const toolbar = node?.[MINI_TOOLBAR_KEY];
	const state = node?.[MINI_STATE_KEY];
	if (!toolbar || !state) return;
	if (toolbar.metaEl instanceof HTMLElement) {
		toolbar.metaEl.textContent = buildToolbarStatus(node, state);
	}
	// existing active-state sync remains below
}
```

Implementation note: keep this simple. The first version can leave the latest status visible until the next meaningful interaction, as long as the base summary is recomputed when no transient status is set.

- [ ] **Step 5: Run a second manual smoke check**

Run:

```powershell
# In the active ComfyUI session, verify:
# 1. 顶部状态不再显示“槽位收起 / 参数收起”作为主信息
# 2. “入队”显示成功/失败反馈
# 3. “复制 / 随机 / 清空”执行后顶部状态会即时变化
```

Expected: top meta line reflects operational state and last action feedback.

- [ ] **Step 6: Prepare local diff review**

Run:

```powershell
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\worktrees\comfyui-style-mode-random-pool-optimization\custom_nodes\comfyUI-qwen3_5-llama-TE' diff -- web/stage_prompt_generator_mini_toolbar.js
```

Expected: diff is limited to `web/stage_prompt_generator_mini_toolbar.js` and reflects the scoped `A`-plan changes only.
