import { app } from "/scripts/app.js";

const TARGET_NODE_CLASSES = new Set([
	"QwenTE_StagePromptGenerator",
	"QwenTE_UniversalStagePromptGenerator",
]);
const STAGE_DISPLAY_NAME_MARKERS = ["阶段式提示词生成器", "真男人提示词阶段生成器"];
const STAGE_WIDGET_SIGNATURE_NAMES = ["qwen模型", "模板风格", "首条正向提示词"];
const STAGE_OUTPUT_SIGNATURE_GROUPS = new Map([
	["结果全文", "full"], ["全文", "full"],
	["首条正向提示词", "positive"], ["正向", "positive"],
	["已选标签", "tags"], ["标签", "tags"],
	["JSON结果", "json"], ["JSON", "json"],
	["推荐负面词", "negative"], ["负面", "negative"],
	["正向提示词合集", "collection"], ["合集", "collection"],
	["智能文本", "smart"], ["智能", "smart"],
]);

const MINI_TOOLBAR_FLAG = "__qwenTeMiniToolbarLoaded";
const MINI_TOOLBAR_WIDGET_NAME = "qwen_te_mini_toolbar_dom";
const MINI_TITLE_SUFFIX = " [TEmini]";
const MINI_WIDGET_STASH_KEY = Symbol.for("qwenTeMiniWidgetStash");
const PANEL_KEY = Symbol.for("qwen_te.stage_prompt.panel");
const PANEL_READY_KEY = Symbol.for("qwen_te.stage_prompt.panel_ready");
const MINI_STATE_KEY = Symbol.for("qwenTeMiniState");
const MINI_TOOLBAR_KEY = Symbol.for("qwenTeMiniToolbar");
const MINI_STATUS_TEXT_KEY = Symbol.for("qwenTeMiniStatusText");
const MINI_CLEAR_CONFIRM_PENDING_KEY = Symbol.for("qwenTeMiniClearConfirmPending");
const MINI_CLEAR_CONFIRM_TIMER_KEY = Symbol.for("qwenTeMiniClearConfirmTimer");
const MINI_NODE_REMOVED_KEY = Symbol.for("qwenTeMiniNodeRemoved");
const MINI_NODE_DEF_HOOK_KEY = Symbol.for("qwenTeMiniNodeDefHook");
const MINI_GRAPH_HOOK_KEY = Symbol.for("qwenTeMiniGraphHook");
const MINI_STARTUP_SCAN_TIMER_KEY = "__qwenTeMiniToolbarStartupScanTimer";
const MINI_STARTUP_SCAN_LIMIT = 8;
const MINI_STARTUP_SCAN_INTERVAL_MS = 1200;
const MINI_WIDGET_RECONCILE_LIMIT = 64;
const MINI_WIDGET_RECONCILE_INTERVAL_MS = 160;
const MINI_CLEAR_CONFIRM_TIMEOUT_MS = 4000;
const MINI_CLEAR_CONFIRM_MESSAGE = "再次点击“清空”以确认。";
const MINI_NODE_MIN_WIDTH = 420;
const MINI_TOOLBAR_MIN_HEIGHT = 136;
const MINI_DOM_WIDGET_Z_INDEX = 10020;
const FALLBACK_WIDGET_NAMES = new Set([
	"标签",
	"随机",
	"随机跑",
	"入队",
	"连测轮",
	"连测随",
	"停连测",
	"连测报",
	"质检",
	"预设",
	"联机",
	"历史",
	"回退",
	"复制",
	"负面",
	"诊断",
	"槽位",
	"高级",
	"自负",
	"稳妥",
	"柔肤",
	"抑字",
	"清空",
	"示例",
	"NSFW",
	"状态",
	"摘要",
]);
const MAIN_STAGE_STATUS_WIDGET_NAMES = new Set(["状态", "摘要"]);
const RAW_TAG_REGEX = /标签\d+$/u;
const CUSTOM_TAG_WIDGET = "自定义补充标签";
const CLEAR_PROMPT_INPUT_WIDGET_NAMES = ["额外要求", "智能文本输入"];
const RANDOM_TOGGLE_WIDGET = "运行时随机标签";
const SOFT_SKIN_WIDGET = "优先柔和肤质";
const SUPPRESS_TEXT_WIDGET = "抑制文字伪影";
const CONTROL_WIDGET_NAMES = new Set([
	"模板风格",
	"运行时随机标签",
	"运行时随机模式",
	"核心标签锁定数量",
	"运行时随机强度",
	"随机主题池",
	"生成数量",
	"提示词语言",
	"详细度",
	"标签反推模式",
	"优先柔和肤质",
	"抑制文字伪影",
]);
const ADVANCED_WIDGET_NAMES = new Set([
	"主体类型",
	"案例输出结构",
	"风格隔离策略",
	"输出模式",
	"额外要求",
	"智能文本匹配",
	"智能文本输入",
	"智能文本风格优先",
	"图片反推生成",
	"图片反推模式",
	"图片反推最大边长",
	"锁定标签白名单",
	"随机排除标签",
	"模型来源",
	"内置模型系列",
	"内置主模型",
	"内置视觉投影mmproj",
	"内置启用思考",
	"内置上下文长度",
	"内置GPU层数",
	"内置KV缓存K类型",
	"内置KV缓存V类型",
	"API服务商",
	"API地址",
	"API密钥",
	"API模型",
	"API超时秒",
	"API额外请求头",
	"系统提示词覆盖",
	"最大生成token",
	"温度",
	"top_p",
	"top_k",
	"重复惩罚",
	"频率惩罚",
	"存在惩罚",
	"seed",
	"输出think块",
	"随机补充避重缓存",
]);
const MINI_ALWAYS_HIDDEN_WIDGET_NAMES = new Set([
	"随机补充避重缓存",
	"连续生成避重缓存",
	"运行时随机保护标签",
	"运行时随机预览令牌",
	"标签块编排启用",
	"标签块编排JSON",
]);
const MINI_PRESERVED_WIDGET_NAMES = new Set([
	"状态",
	"摘要",
	"qwen模型",
	"参考图片",
	"首条正向提示词",
	MINI_TOOLBAR_WIDGET_NAME,
	"qwen_te_tag_panel",
]);

let stylesInjected = false;

function hasStagePromptDisplayName(value) {
	const text = String(value ?? "");
	return STAGE_DISPLAY_NAME_MARKERS.some((marker) => text.includes(marker));
}

function isStagePromptNode(node) {
	if (!node) return false;
	if ([node.comfyClass, node.type].some((value) => TARGET_NODE_CLASSES.has(String(value ?? "")))) return true;
	if (typeof node.title === "string" && hasStagePromptDisplayName(node.title)) return true;
	const widgetNames = new Set((node.widgets ?? []).map((widget) => String(widget?.name ?? "")));
	if (STAGE_WIDGET_SIGNATURE_NAMES.every((name) => widgetNames.has(name))) return true;
	const outputSignatureGroups = new Set();
	for (const output of node.outputs ?? []) {
		const names = [output?.name, output?._qwenTeOriginalName].map((value) => String(value ?? ""));
		for (const name of names) {
			const group = STAGE_OUTPUT_SIGNATURE_GROUPS.get(name);
			if (group) outputSignatureGroups.add(group);
		}
	}
	return outputSignatureGroups.size >= 3;
}

function hasMainStagePanel(node) {
	return node?.[PANEL_READY_KEY] === true && node?.[PANEL_KEY]?.ready === true && !!node?.widgets?.some((widget) => widget?.name === "qwen_te_tag_panel");
}

function cleanupIncompleteMainPanel(node) {
	if (!node?.widgets?.some((widget) => widget?.name === "qwen_te_tag_panel")) return false;
	if (hasMainStagePanel(node)) return false;
	try {
		if (window.__QWEN_TE_STAGE_ROLLBACK__?.(node)) return true;
	} catch (_error) {}
	const orphan = getWidget(node, "qwen_te_tag_panel");
	return orphan ? removeNodeWidgetSafely(node, orphan) : false;
}

function getWidget(node, name) {
	return node?.widgets?.find((widget) => widget?.name === name) ?? null;
}

function removeNodeWidgetSafely(node, widget) {
	if (!node || !widget || !Array.isArray(node.widgets)) return false;
	if (typeof node.removeWidget === "function") {
		try {
			node.removeWidget(widget);
			if (!node.widgets.includes(widget)) return true;
		} catch (_error) {}
	}
	const index = node.widgets.indexOf(widget);
	if (index < 0) return false;
	node.widgets.splice(index, 1);
	try { widget.onRemove?.(); } catch (_error) {}
	try { widget.element?.remove?.(); } catch (_error) {}
	return true;
}

function setWidgetValue(node, name, value) {
	const widget = getWidget(node, name);
	if (!widget) return false;
	widget.value = value;
	if (widget.inputEl) widget.inputEl.value = value;
	if (widget.element && "value" in widget.element) widget.element.value = value;
	try {
		widget.callback?.(value, app, node);
	} catch (_error) {}
	return true;
}

function queueWorkflow() {
	try {
		const queueButton =
			document.querySelector("#queue-button") ||
			document.querySelector(".queue-button") ||
			document.querySelector("[data-testid='queue-button']") ||
			document.querySelector("[title*='Queue']");
		if (queueButton instanceof HTMLElement) {
			queueButton.click();
			return true;
		}
	} catch (_error) {}
	try {
		if (typeof app?.queuePrompt === "function") {
			app.queuePrompt(0, 1);
			return true;
		}
	} catch (_error) {}
	return false;
}

function scheduleNodeLayout(node) {
	requestAnimationFrame(() => requestAnimationFrame(() => {
		try {
			const size = node.computeSize?.() ?? node.size;
			const nextWidth = Math.max(MINI_NODE_MIN_WIDTH, size?.[0] ?? 0);
			const nextHeight = Math.max(size?.[1] ?? 0, 0);
			node.setSize?.([nextWidth, nextHeight]);
			app.graph?.setDirtyCanvas?.(true, true);
		} catch (_error) {}
	}));
}

function stashWidget(widget) {
	if (!widget || widget[MINI_WIDGET_STASH_KEY]) return;
	widget[MINI_WIDGET_STASH_KEY] = {
		type: widget.type,
		computeSize: widget.computeSize,
		hadHidden: Object.prototype.hasOwnProperty.call(widget, "hidden"),
		hidden: widget.hidden,
		hadOptionsHidden: !!widget.options && Object.prototype.hasOwnProperty.call(widget.options, "hidden"),
		optionsHidden: widget.options?.hidden,
		inputDisplay: widget.inputEl?.style?.display,
		elementDisplay: widget.element?.style?.display,
	};
}

function restoreStashedWidgets(node) {
	let restored = false;
	for (const widget of node?.widgets ?? []) {
		const stash = widget?.[MINI_WIDGET_STASH_KEY];
		if (!stash) continue;
		widget.type = stash.type;
		if (typeof stash.computeSize === "function") widget.computeSize = stash.computeSize;
		else delete widget.computeSize;
		if (stash.hadHidden) widget.hidden = stash.hidden;
		else delete widget.hidden;
		if (widget.options) {
			if (stash.hadOptionsHidden) widget.options.hidden = stash.optionsHidden;
			else delete widget.options.hidden;
		}
		if (widget.inputEl?.style) widget.inputEl.style.display = stash.inputDisplay ?? "";
		if (widget.element?.style) widget.element.style.display = stash.elementDisplay ?? "";
		delete widget[MINI_WIDGET_STASH_KEY];
		restored = true;
	}
	return restored;
}

function setWidgetCollapsed(widget, collapsed, suffix = "Mini") {
	if (!widget) return;
	stashWidget(widget);
	const stash = widget[MINI_WIDGET_STASH_KEY];
	widget.type = collapsed ? `easyHidden${suffix}` : stash.type;
	widget.computeSize = collapsed ? () => [0, -4] : stash.computeSize;
	widget.hidden = collapsed;
	widget.options = widget.options ?? {};
	widget.options.hidden = collapsed;
	if (widget.inputEl) widget.inputEl.style.display = collapsed ? "none" : "";
	if (widget.element) widget.element.style.display = collapsed ? "none" : "";
}

function setWidgetGroupCollapsed(node, names, collapsed, suffix = "Mini") {
	for (const name of names) {
		setWidgetCollapsed(getWidget(node, name), collapsed, suffix);
	}
	scheduleNodeLayout(node);
}

function collectRawTagWidgetNames(node) {
	return (node?.widgets ?? [])
		.map((widget) => String(widget?.name ?? ""))
		.filter((name) => RAW_TAG_REGEX.test(name) || name === CUSTOM_TAG_WIDGET);
}

function collectAdvancedWidgetNames(node) {
	return (node?.widgets ?? [])
		.filter((widget) => {
			const name = String(widget?.name ?? "");
			if (!name || RAW_TAG_REGEX.test(name) || name === CUSTOM_TAG_WIDGET) return false;
			if (MINI_ALWAYS_HIDDEN_WIDGET_NAMES.has(name) || MINI_PRESERVED_WIDGET_NAMES.has(name)) return false;
			if (widget?.__qwenStageFallbackWidget || widget?.__qwenStageMiniWidget) return false;
			return CONTROL_WIDGET_NAMES.has(name) || ADVANCED_WIDGET_NAMES.has(name) || widget?.serialize !== false;
		})
		.map((widget) => String(widget?.name ?? ""));
}

function collectAlwaysHiddenWidgetNames(node) {
	return (node?.widgets ?? [])
		.map((widget) => String(widget?.name ?? ""))
		.filter((name) => MINI_ALWAYS_HIDDEN_WIDGET_NAMES.has(name));
}

function reconcileLateMiniWidgets(node, state) {
	if (!node || !state?.initialized) return false;
	let changed = false;
	const applyUntracked = (names, collapsed, suffix) => {
		for (const name of names) {
			const widget = getWidget(node, name);
			if (!widget || widget[MINI_WIDGET_STASH_KEY]) continue;
			setWidgetCollapsed(widget, collapsed, suffix);
			changed = true;
		}
	};
	applyUntracked(collectRawTagWidgetNames(node), !state.rawExpanded, "MiniRaw");
	applyUntracked(collectAdvancedWidgetNames(node), !state.advancedExpanded, "MiniAdvanced");
	applyUntracked(collectAlwaysHiddenWidgetNames(node), true, "MiniInternal");
	if (changed) scheduleNodeLayout(node);
	return changed;
}

function clearMiniWidgetReconcile(node, expectedTimer = null) {
	const state = node?.[MINI_STATE_KEY];
	const timer = state?.reconcileTimer;
	if (expectedTimer != null && timer !== expectedTimer) return false;
	if (timer == null) return false;
	clearInterval(timer);
	state.reconcileTimer = null;
	state.reconcilePassCount = 0;
	return true;
}

function startMiniWidgetReconcile(node, state = node?.[MINI_STATE_KEY]) {
	if (!node || !state?.initialized || state.reconcileTimer != null) return state?.reconcileTimer ?? null;
	state.reconcilePassCount = 0;
	let timer = null;
	timer = setInterval(() => {
		if (state.reconcileTimer !== timer) return;
		if (
			node[MINI_NODE_REMOVED_KEY]
			|| node[MINI_STATE_KEY] !== state
			|| !node[MINI_TOOLBAR_FLAG]
			|| hasMainStagePanel(node)
		) {
			clearMiniWidgetReconcile(node, timer);
			return;
		}
		reconcileLateMiniWidgets(node, state);
		state.reconcilePassCount = Math.max(0, Number(state.reconcilePassCount ?? 0) || 0) + 1;
		if (state.reconcilePassCount >= MINI_WIDGET_RECONCILE_LIMIT) clearMiniWidgetReconcile(node, timer);
	}, MINI_WIDGET_RECONCILE_INTERVAL_MS);
	state.reconcileTimer = timer;
	timer?.unref?.();
	return timer;
}

function buildSelectedTagsText(node) {
	const tags = [];
	for (const widget of node.widgets ?? []) {
		const name = String(widget?.name ?? "");
		if (RAW_TAG_REGEX.test(name)) {
			const value = String(widget.value ?? "").trim();
			if (value && value !== "无" && !tags.includes(value)) tags.push(value);
		}
	}
	const custom = String(getWidget(node, CUSTOM_TAG_WIDGET)?.value ?? "")
		.split(/[,，\n\r\t]+/u)
		.map((item) => item.trim())
		.filter(Boolean);
	for (const tag of custom) if (!tags.includes(tag)) tags.push(tag);
	return tags.join(", ");
}

async function copyText(text) {
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch (_error) {
		return false;
	}
}

function getNodeStagePanelState(node) {
	const symbol = Object.getOwnPropertySymbols(node ?? {}).find((item) => String(item).includes("qwen_te_panel"));
	return symbol ? node?.[symbol] ?? null : null;
}

function getLatestPositivePromptText(node) {
	const panelState = getNodeStagePanelState(node);
	const fromLastExecution = Array.isArray(panelState?.lastExecutionOutputs)
		? String(panelState.lastExecutionOutputs[1] ?? "").trim()
		: "";
	if (fromLastExecution) return fromLastExecution;
	const directCache = panelState?.directStageOutputCache;
	if (directCache && typeof directCache === "object") {
		const outputList = Array.isArray(directCache.outputs)
			? directCache.outputs
			: [
				directCache.full_text,
				directCache.prompt_text,
				directCache.selected_tags_text,
				directCache.json_result,
				directCache.negative_prompt,
				directCache.prompt_collection,
			];
		const directPrompt = String(outputList?.[1] ?? "").trim();
		if (directPrompt) return directPrompt;
	}
	const hydratedPrompt = Array.isArray(panelState?.hydratedExecutionOutputs)
		? String(panelState.hydratedExecutionOutputs[1] ?? "").trim()
		: "";
	if (hydratedPrompt) return hydratedPrompt;
	const widgetValue = String(getWidget(node, "首条正向提示词")?.value ?? "").trim();
	return widgetValue;
}

function setMiniStatus(node, message) {
	if (!node || node[MINI_NODE_REMOVED_KEY]) return;
	node[MINI_STATUS_TEXT_KEY] = String(message ?? "").trim();
	refreshMiniToolbar(node);
}

function clearMiniStatus(node) {
	if (!node || node[MINI_NODE_REMOVED_KEY]) return;
	delete node[MINI_STATUS_TEXT_KEY];
	refreshMiniToolbar(node);
}

function cancelMiniClearConfirmation(node, options = {}) {
	if (!node) return false;
	const timer = node[MINI_CLEAR_CONFIRM_TIMER_KEY];
	const hadConfirmation = node[MINI_CLEAR_CONFIRM_PENDING_KEY] != null || timer != null;
	if (timer != null) clearTimeout(timer);
	delete node[MINI_CLEAR_CONFIRM_TIMER_KEY];
	delete node[MINI_CLEAR_CONFIRM_PENDING_KEY];
	if (options.clearStatus !== false && node[MINI_STATUS_TEXT_KEY] === MINI_CLEAR_CONFIRM_MESSAGE) {
		delete node[MINI_STATUS_TEXT_KEY];
	}
	if (hadConfirmation && options.refresh !== false) refreshMiniToolbar(node);
	return hadConfirmation;
}

function isMiniClearConfirmationPending(node) {
	const deadline = Number(node?.[MINI_CLEAR_CONFIRM_PENDING_KEY] ?? 0) || 0;
	if (deadline > Date.now()) return true;
	if (deadline > 0 || node?.[MINI_CLEAR_CONFIRM_TIMER_KEY] != null) {
		cancelMiniClearConfirmation(node, { refresh: false });
	}
	return false;
}

function beginMiniClearConfirmation(node) {
	if (!node || node[MINI_NODE_REMOVED_KEY]) return false;
	cancelMiniClearConfirmation(node, { refresh: false });
	const deadline = Date.now() + MINI_CLEAR_CONFIRM_TIMEOUT_MS;
	node[MINI_CLEAR_CONFIRM_PENDING_KEY] = deadline;
	node[MINI_STATUS_TEXT_KEY] = MINI_CLEAR_CONFIRM_MESSAGE;
	const timer = setTimeout(() => {
		if (node[MINI_CLEAR_CONFIRM_PENDING_KEY] !== deadline) return;
		cancelMiniClearConfirmation(node);
	}, MINI_CLEAR_CONFIRM_TIMEOUT_MS);
	node[MINI_CLEAR_CONFIRM_TIMER_KEY] = timer;
	timer?.unref?.();
	refreshMiniToolbar(node);
	return true;
}

function buildMiniBaseStatus({ selectedCount, randomEnabled, suppressEnabled, hasPromptOutput }) {
	const bits = [`已选 ${Math.max(0, Number(selectedCount) || 0)}`];
	if (randomEnabled) bits.push("随机 ON");
	if (suppressEnabled) bits.push("抑字 ON");
	bits.push(hasPromptOutput ? "可复制正向" : "未生成");
	return bits.join(" · ");
}

async function resolveMiniCopyAction(node, helpers = {}) {
	const getPromptOutputText = typeof helpers.getPromptOutputText === "function"
		? helpers.getPromptOutputText
		: getLatestPositivePromptText;
	const copy = typeof helpers.copyText === "function" ? helpers.copyText : copyText;
	const text = String(getPromptOutputText(node) ?? "").trim();
	if (!text) return "还没有可复制的提示词，请先运行一次节点。";
	const ok = await copy(text);
	return ok ? "已复制正向提示词。" : "复制失败，剪贴板不可用。";
}

async function clearMiniSelectionAction(node, rawTagWidgetNames, helpers = {}) {
	const confirmClear = typeof helpers.confirmClear === "function"
		? helpers.confirmClear
		: () => window.confirm("将清空当前标签选择，确定继续吗？");
	const writeValue = typeof helpers.setWidgetValue === "function" ? helpers.setWidgetValue : setWidgetValue;
	const confirmed = helpers.forceConfirmed ? true : confirmClear();
	if (!confirmed) return "已取消清空。";
	const clearNodeState = globalThis.__QWEN_TE_STAGE_CLEAR_NODE_STATE__;
	if (typeof helpers.setWidgetValue !== "function" && typeof clearNodeState === "function") {
		const ok = await clearNodeState(node);
		return ok ? "已清空当前标签与用户输入。" : "清空操作已被更新的节点操作取消。";
	}
	for (const widgetName of rawTagWidgetNames) {
		if (widgetName === CUSTOM_TAG_WIDGET) writeValue(node, widgetName, "");
		else writeValue(node, widgetName, "无");
	}
	for (const widgetName of CLEAR_PROMPT_INPUT_WIDGET_NAMES) writeValue(node, widgetName, "");
	writeValue(node, "智能文本匹配", false);
	return "已清空当前标签与用户输入。";
}

async function openMiniNsfwWorkspaceAction(node) {
	const openDialog = globalThis.__QWEN_TE_STAGE_OPEN_NSFW_WORKSPACE__;
	if (typeof openDialog !== "function") return "NSFW 工作台暂不可用。";
	const ok = await openDialog(node);
	return ok ? "已打开 NSFW 工作台。" : "NSFW 工作台暂不可用。";
}

async function applyMiniRandomAction(node, helpers = {}) {
	if (typeof helpers.applyRandomState === "function") {
		const ok = await helpers.applyRandomState(node);
		return ok ? "已随机生成当前标签组合。" : "随机功能暂不可用。";
	}
	const applyRandomState = globalThis.__QWEN_TE_STAGE_APPLY_RANDOM_STATE__;
	if (typeof applyRandomState === "function") {
		const ok = await applyRandomState(node);
		return ok ? "已随机生成当前标签组合。" : "随机操作已被更新的节点操作取消。";
	}
	const builder = globalThis.__QWEN_TE_STAGE_BUILD_RANDOM_STATE__;
	const getLibrary = globalThis.__QWEN_TE_STAGE_GET_FRESH_LIBRARY__;
	const applyState = globalThis.__QWEN_TE_STAGE_APPLY_NODE_STATE__;
	const collectState = globalThis.__QWEN_TE_STAGE_COLLECT_NODE_STATE__;
	const recordHistory = globalThis.__QWEN_TE_STAGE_RECORD_HISTORY__;
	if (typeof builder !== "function" || typeof getLibrary !== "function" || typeof applyState !== "function") {
		return "随机功能暂不可用。";
	}
	const library = await getLibrary(node);
	if (!library) return "随机功能暂不可用。";
	if (typeof recordHistory === "function" && typeof collectState === "function") {
		recordHistory(node, collectState(node, library), "before-random");
	}
	const nextState = await builder(node, library);
	if (node?.[MINI_NODE_REMOVED_KEY] || !nextState) return "随机操作已被节点删除取消。";
	applyState(node, library, nextState, { recordHistory: true, historySource: "random" });
	return "已随机生成当前标签组合。";
}

function injectStyles() {
	if (stylesInjected) return;
	stylesInjected = true;
	const style = document.createElement("style");
	style.textContent = `
	.dom-widget:has(> .qwen-te-mini),.dom-widget[data-qwen-te-mini-toolbar="true"]{z-index:${MINI_DOM_WIDGET_Z_INDEX}!important;pointer-events:auto!important}
	.qwen-te-mini{width:100%;box-sizing:border-box;padding:6px 0 2px}
	.qwen-te-mini__shell{display:flex;flex-direction:column;gap:8px;padding:8px 10px 9px;border:1px solid rgba(84,104,131,.58);border-radius:15px;background:linear-gradient(135deg,rgba(112,152,205,.08),rgba(112,152,205,0) 26%),radial-gradient(120% 150% at 100% 0%,rgba(200,152,70,.08),rgba(200,152,70,0) 26%),linear-gradient(180deg,#151c24,#10161d);box-shadow:inset 0 1px 0 rgba(255,255,255,.03),0 12px 22px rgba(0,0,0,.16)}
	.qwen-te-mini__head{display:flex;align-items:center;justify-content:space-between;gap:10px}
	.qwen-te-mini__title{font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:#8fa6c2;font-family:Consolas,"Cascadia Code","SFMono-Regular",monospace}
	.qwen-te-mini__meta{font-size:10px;line-height:1.3;color:#a7b5c7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
	.qwen-te-mini__grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(76px,1fr));gap:6px;align-items:stretch}
	.qwen-te-mini__button{border:1px solid rgba(91,113,141,.82);background:linear-gradient(180deg,rgba(47,61,77,.98),rgba(31,41,52,.99));color:#edf4ff;border-radius:11px;padding:8px 9px;min-height:36px;display:flex;align-items:center;justify-content:center;text-align:center;font-size:11px;font-weight:600;line-height:1.12;cursor:pointer;transition:background .12s ease,border-color .12s ease,transform .08s ease,box-shadow .12s ease;box-shadow:inset 0 1px 0 rgba(255,255,255,.03)}
	.qwen-te-mini__button:hover{background:linear-gradient(180deg,rgba(57,74,93,.99),rgba(35,46,58,.99));border-color:#7a96ba;box-shadow:0 8px 14px rgba(0,0,0,.18),inset 0 1px 0 rgba(255,255,255,.05);transform:translateY(-1px)}
	.qwen-te-mini__button:active{transform:translateY(1px)}
	.qwen-te-mini__button--primary{background:linear-gradient(180deg,rgba(42,65,87,.98),rgba(27,47,66,.99));border-color:#6286ad}
	.qwen-te-mini__button--warm{background:linear-gradient(180deg,rgba(82,61,28,.98),rgba(55,40,17,.99));border-color:#a27a3f;color:#f7dfac}
	.qwen-te-mini__button--danger{background:linear-gradient(180deg,rgba(69,40,46,.98),rgba(42,24,29,.99));border-color:#9d6670;color:#f2d7dc}
	.qwen-te-mini__button.is-active{border-color:#d2a85d;background:linear-gradient(180deg,#654b1f,#473415);color:#fff1cc;box-shadow:0 0 0 1px rgba(255,214,140,.16),0 10px 16px rgba(0,0,0,.20)}
	@media (max-width:560px){
		.qwen-te-mini__head{flex-direction:column;align-items:flex-start}
	}
	`;
	document.head.appendChild(style);
}

function buildToolbarStatus(node, state) {
	const transient = String(node?.[MINI_STATUS_TEXT_KEY] ?? "").trim();
	if (transient) return transient;
	const selectedText = buildSelectedTagsText(node);
	const count = selectedText ? selectedText.split(/\s*,\s*/u).filter(Boolean).length : 0;
	const randomEnabled = !!getWidget(node, RANDOM_TOGGLE_WIDGET)?.value;
	const suppressEnabled = !!getWidget(node, SUPPRESS_TEXT_WIDGET)?.value;
	const hasPromptOutput = !!String(getLatestPositivePromptText(node) ?? "").trim();
	return buildMiniBaseStatus({
		selectedCount: count,
		randomEnabled,
		suppressEnabled,
		hasPromptOutput,
	});
}

function measureToolbarHeight(root, minHeight = 86) {
	if (!(root instanceof HTMLElement)) return minHeight;
	const shell = root.querySelector?.(".qwen-te-mini__shell");
	const contentHeights = [root, shell]
		.filter((element) => element instanceof HTMLElement)
		.flatMap((element) => [
			Number(element.scrollHeight ?? 0),
			Number(element.offsetHeight ?? 0),
			Number(element.getBoundingClientRect?.().height ?? 0),
		]);
	const contentHeight = Math.max(0, ...contentHeights);
	return Math.max(minHeight, Math.ceil(contentHeight + 12));
}

function liftMiniToolbarDomWidget(root) {
	if (!(root instanceof HTMLElement)) return;
	root.dataset.qwenTeMiniToolbar = "true";
	const liftParent = () => {
		const parent = root.parentElement;
		if (!(parent instanceof HTMLElement)) return;
		parent.dataset.qwenTeMiniToolbar = "true";
		parent.style.setProperty?.("z-index", String(MINI_DOM_WIDGET_Z_INDEX), "important");
		parent.style.setProperty?.("pointer-events", "auto", "important");
	};
	liftParent();
	requestAnimationFrame?.(liftParent);
}

function isLegacyMiniWidget(widget) {
	const name = String(widget?.name ?? "");
	if (widget?.__qwenStageFallbackWidget && MAIN_STAGE_STATUS_WIDGET_NAMES.has(name)) return false;
	return (
		widget?.name === MINI_TOOLBAR_WIDGET_NAME ||
		widget?.__qwenStageMiniWidget ||
		(widget?.__qwenStageFallbackWidget && name.startsWith("TE·")) ||
		(widget?.serialize === false && FALLBACK_WIDGET_NAMES.has(name))
	);
}

function cleanupLegacyMiniWidgets(node) {
	if (!Array.isArray(node?.widgets)) return false;
	let changed = false;
	node.widgets = node.widgets.filter((widget) => {
		const remove = isLegacyMiniWidget(widget);
		if (remove) changed = true;
		return !remove;
	});
	return changed;
}

function refreshMiniToolbar(node) {
	const toolbar = node?.[MINI_TOOLBAR_KEY];
	const state = node?.[MINI_STATE_KEY];
	if (!toolbar || !state) return;
	if (toolbar.metaEl instanceof HTMLElement) {
		toolbar.metaEl.textContent = buildToolbarStatus(node, state);
	}
	const randomEnabled = !!getWidget(node, RANDOM_TOGGLE_WIDGET)?.value;
	toolbar.buttons.raw?.classList.toggle("is-active", state.rawExpanded);
	toolbar.buttons.advanced?.classList.toggle("is-active", state.advancedExpanded);
	toolbar.buttons.random?.classList.toggle("is-active", randomEnabled);
	const clearConfirmPending = isMiniClearConfirmationPending(node);
	if (toolbar.buttons.clear) {
		toolbar.buttons.clear.textContent = clearConfirmPending ? "确认清空" : "清空";
		toolbar.buttons.clear.classList.toggle("is-active", clearConfirmPending);
		toolbar.buttons.clear.setAttribute("aria-pressed", clearConfirmPending ? "true" : "false");
		toolbar.buttons.clear.title = clearConfirmPending ? "4 秒内再次点击以确认清空。" : "清空当前标签与用户输入。";
	}
}

function createMiniButton(label, variant, handler) {
	const button = document.createElement("button");
	button.type = "button";
	button.className = `qwen-te-mini__button${variant ? ` qwen-te-mini__button--${variant}` : ""}`;
	button.textContent = label;
	button.addEventListener("pointerdown", (event) => event.stopPropagation());
	button.addEventListener("mousedown", (event) => event.stopPropagation());
	button.addEventListener("click", async (event) => {
		event.stopPropagation();
		await handler();
	});
	return button;
}

function cleanupMiniToolbar(node, options = {}) {
	if (!node) return false;
	const toolbar = node?.[MINI_TOOLBAR_KEY];
	const hasLegacyWidgets = Array.isArray(node?.widgets) && node.widgets.some(isLegacyMiniWidget);
	const hasTitleSuffix = typeof node?.title === "string" && node.title.endsWith(MINI_TITLE_SUFFIX);
	const hasState = !!(
		toolbar ||
		node[MINI_STATE_KEY] ||
		node[MINI_TOOLBAR_FLAG] ||
		node[MINI_STATUS_TEXT_KEY] ||
		node[MINI_CLEAR_CONFIRM_PENDING_KEY] != null ||
		node[MINI_CLEAR_CONFIRM_TIMER_KEY] != null ||
		hasLegacyWidgets ||
		hasTitleSuffix
	);
	if (!hasState) return false;
	cancelMiniClearConfirmation(node, { refresh: false });
	clearMiniWidgetReconcile(node);
	let layoutChanged = hasLegacyWidgets || hasTitleSuffix;
	try {
		toolbar?.resizeObserver?.disconnect?.();
	} catch (_error) {}
	try {
		const root = toolbar?.root;
		const parent = root?.parentElement;
		if (parent) layoutChanged = true;
		root?.remove?.();
		if (parent?.dataset?.qwenTeMiniToolbar === "true" && !parent?.children?.length) {
			parent.remove?.();
		}
	} catch (_error) {}
	layoutChanged = restoreStashedWidgets(node) || layoutChanged;
	layoutChanged = cleanupLegacyMiniWidgets(node) || layoutChanged;
	delete node[MINI_TOOLBAR_KEY];
	delete node[MINI_STATE_KEY];
	delete node[MINI_STATUS_TEXT_KEY];
	delete node[MINI_CLEAR_CONFIRM_PENDING_KEY];
	delete node[MINI_CLEAR_CONFIRM_TIMER_KEY];
	delete node[MINI_TOOLBAR_FLAG];
	if (hasTitleSuffix) {
		node.title = node.title.slice(0, -MINI_TITLE_SUFFIX.length);
	}
	if (layoutChanged && options.scheduleLayout !== false) scheduleNodeLayout(node);
	return true;
}

function sendMiniDecisionProbe(marker, node) {
	const nodeLabel = String(node?.title ?? node?.comfyClass ?? node?.id ?? "unknown");
	sendFrontendProbe(`${marker}:${nodeLabel}`);
}

function ensureMiniToolbar(node) {
	if (node?.[MINI_NODE_REMOVED_KEY]) return;
	if (!isStagePromptNode(node)) {
		const widgetPreview = (node?.widgets ?? [])
			.slice(0, 6)
			.map((widget) => String(widget?.name ?? ""))
			.filter(Boolean)
			.join("|");
		sendFrontendProbe(
			`skip_not_stage:title=${encodeURIComponent(String(node?.title ?? ""))}` +
			`&class=${encodeURIComponent(String(node?.comfyClass ?? ""))}` +
			`&widgets=${encodeURIComponent(widgetPreview)}`
		);
		return;
	}
	if (hasMainStagePanel(node)) {
		sendMiniDecisionProbe("skip_has_main_panel", node);
		cleanupMiniToolbar(node);
		return;
	}
	cleanupIncompleteMainPanel(node);
	if (node[MINI_TOOLBAR_FLAG]) {
		reconcileLateMiniWidgets(node, node[MINI_STATE_KEY]);
		startMiniWidgetReconcile(node, node[MINI_STATE_KEY]);
		sendMiniDecisionProbe("skip_already_loaded", node);
		return true;
	}
	if (typeof node.addDOMWidget !== "function") {
		sendMiniDecisionProbe("skip_no_addDOMWidget", node);
		return;
	}

	cleanupLegacyMiniWidgets(node);
	injectStyles();

	const rawTagWidgetNames = collectRawTagWidgetNames(node);
	const advancedWidgetNames = collectAdvancedWidgetNames(node);
	const alwaysHiddenWidgetNames = collectAlwaysHiddenWidgetNames(node);
	const state = node[MINI_STATE_KEY] ?? { rawExpanded: false, advancedExpanded: false, initialized: false };
	node[MINI_STATE_KEY] = state;

	if (!state.initialized) {
		setWidgetGroupCollapsed(node, rawTagWidgetNames, true, "MiniRaw");
		setWidgetGroupCollapsed(node, advancedWidgetNames, true, "MiniAdvanced");
		setWidgetGroupCollapsed(node, alwaysHiddenWidgetNames, true, "MiniInternal");
		state.rawExpanded = false;
		state.advancedExpanded = false;
		state.initialized = true;
	}

	const root = document.createElement("div");
	root.className = "qwen-te-mini";
	root.style.pointerEvents = "auto";
	liftMiniToolbarDomWidget(root);
	root.addEventListener("pointerdown", (event) => event.stopPropagation());
	root.addEventListener("mousedown", (event) => event.stopPropagation());
	root.addEventListener("click", (event) => event.stopPropagation());

	const shell = document.createElement("div");
	shell.className = "qwen-te-mini__shell";
	root.appendChild(shell);

	const head = document.createElement("div");
	head.className = "qwen-te-mini__head";
	shell.appendChild(head);

	const title = document.createElement("div");
	title.className = "qwen-te-mini__title";
	title.textContent = "TE MINI CONSOLE";
	head.appendChild(title);

	const meta = document.createElement("div");
	meta.className = "qwen-te-mini__meta";
	head.appendChild(meta);

	const grid = document.createElement("div");
	grid.className = "qwen-te-mini__grid";
	shell.appendChild(grid);

	const makeActionButton = (label, variant, handler) => createMiniButton(label, variant, async () => {
		cancelMiniClearConfirmation(node, { refresh: false });
		await handler();
	});

	const buttons = {
		tag: makeActionButton("标签", "primary", async () => {
			const openTagDialog = globalThis.__QWEN_TE_STAGE_OPEN_TAG_DIALOG__;
			if (typeof openTagDialog === "function") await openTagDialog(node);
			clearMiniStatus(node);
		}),
		random: makeActionButton("随机", "warm", async () => {
			setMiniStatus(node, await applyMiniRandomAction(node));
		}),
		queue: makeActionButton("入队", "primary", async () => {
			const ok = queueWorkflow();
			setMiniStatus(node, ok ? "已加入队列。" : "入队失败，请检查队列按钮。");
		}),
		raw: makeActionButton("槽位", "", async () => {
			state.rawExpanded = !state.rawExpanded;
			setWidgetGroupCollapsed(node, collectRawTagWidgetNames(node), !state.rawExpanded, "MiniRaw");
			clearMiniStatus(node);
			refreshMiniToolbar(node);
		}),
		advanced: makeActionButton("高级", "", async () => {
			state.advancedExpanded = !state.advancedExpanded;
			setWidgetGroupCollapsed(node, collectAdvancedWidgetNames(node), !state.advancedExpanded, "MiniAdvanced");
			setWidgetGroupCollapsed(node, collectAlwaysHiddenWidgetNames(node), true, "MiniInternal");
			clearMiniStatus(node);
			refreshMiniToolbar(node);
		}),
		nsfw: makeActionButton("NSFW", "warm", async () => {
			setMiniStatus(node, await openMiniNsfwWorkspaceAction(node));
		}),
		clear: createMiniButton("清空", "danger", async () => {
			if (!isMiniClearConfirmationPending(node)) {
				beginMiniClearConfirmation(node);
				return;
			}
			cancelMiniClearConfirmation(node, { refresh: false });
			setMiniStatus(node, await clearMiniSelectionAction(node, collectRawTagWidgetNames(node), { forceConfirmed: true }));
		}),
	};

	for (const button of Object.values(buttons)) grid.appendChild(button);

	let domWidget = null;
	try {
		domWidget = node.addDOMWidget(MINI_TOOLBAR_WIDGET_NAME, "div", root, {
			serialize: false,
			hideOnZoom: false,
			getValue() {
				return undefined;
			},
			setValue() {},
		}) ?? getWidget(node, MINI_TOOLBAR_WIDGET_NAME);
	} catch (_error) {
		domWidget = getWidget(node, MINI_TOOLBAR_WIDGET_NAME);
	}
	if (!domWidget) {
		restoreStashedWidgets(node);
		delete node[MINI_STATE_KEY];
		root.remove?.();
		sendMiniDecisionProbe("failed_addDOMWidget", node);
		scheduleNodeLayout(node);
		return false;
	}
	node[MINI_TOOLBAR_FLAG] = true;
	if (typeof node.title === "string" && !node.title.endsWith(MINI_TITLE_SUFFIX)) {
		node.title += MINI_TITLE_SUFFIX;
	}
	if (domWidget) {
		domWidget.serialize = false;
		domWidget.__qwenStageMiniWidget = true;
		domWidget.computeSize = (width) => [Math.max(MINI_NODE_MIN_WIDTH, Math.min(width ?? node.size?.[0] ?? 0, 720)), measureToolbarHeight(root, MINI_TOOLBAR_MIN_HEIGHT)];
		liftMiniToolbarDomWidget(root);
	}

	const resizeObserver = typeof ResizeObserver === "function"
		? new ResizeObserver(() => scheduleNodeLayout(node))
		: null;
	try {
		resizeObserver?.observe(root);
	} catch (_error) {}

	node[MINI_TOOLBAR_KEY] = {
		root,
		domWidget,
		metaEl: meta,
		buttons,
		resizeObserver,
	};
	startMiniWidgetReconcile(node, state);
	sendMiniDecisionProbe("created", node);
	refreshMiniToolbar(node);
	scheduleNodeLayout(node);
}

function enhanceExistingNodes() {
	for (const node of app.graph?._nodes ?? []) {
		if (!isStagePromptNode(node)) continue;
		if (hasMainStagePanel(node)) {
			cleanupMiniToolbar(node);
			continue;
		}
		ensureMiniToolbar(node);
		refreshMiniToolbar(node);
	}
}

function clearMiniStartupScanTimer(expectedTimer = null) {
	const timer = globalThis[MINI_STARTUP_SCAN_TIMER_KEY];
	if (expectedTimer != null && timer !== expectedTimer) return false;
	if (timer == null) return false;
	clearInterval(timer);
	globalThis[MINI_STARTUP_SCAN_TIMER_KEY] = null;
	return true;
}

function startMiniStartupScan() {
	clearMiniStartupScanTimer();
	let scanCount = 0;
	let timer = null;
	timer = setInterval(() => {
		if (globalThis[MINI_STARTUP_SCAN_TIMER_KEY] !== timer) return;
		enhanceExistingNodes();
		scanCount += 1;
		if (scanCount >= MINI_STARTUP_SCAN_LIMIT) clearMiniStartupScanTimer(timer);
	}, MINI_STARTUP_SCAN_INTERVAL_MS);
	globalThis[MINI_STARTUP_SCAN_TIMER_KEY] = timer;
	timer?.unref?.();
	return timer;
}

function installMiniGraphNodeAddedHook() {
	const graph = app.graph;
	if (!graph || graph[MINI_GRAPH_HOOK_KEY]) return false;
	const originalOnNodeAdded = graph.onNodeAdded;
	graph.onNodeAdded = function (node) {
		const result = originalOnNodeAdded?.apply(this, arguments);
		if (!isStagePromptNode(node)) return result;
		delete node[MINI_NODE_REMOVED_KEY];
		setTimeout(() => {
			if (node?.[MINI_NODE_REMOVED_KEY]) return;
			ensureMiniToolbar(node);
			refreshMiniToolbar(node);
		}, 0);
		return result;
	};
	graph[MINI_GRAPH_HOOK_KEY] = true;
	return true;
}

function installMiniNodeLifecycleHooks(nodeType) {
	const prototype = nodeType?.prototype;
	if (!prototype || prototype[MINI_NODE_DEF_HOOK_KEY]) return false;
	const originalOnNodeCreated = prototype.onNodeCreated;
	const originalOnRemoved = prototype.onRemoved;
	const originalAddWidget = prototype.addWidget;
	if (typeof originalAddWidget === "function") {
		prototype.addWidget = function () {
			const result = originalAddWidget.apply(this, arguments);
			if (this[MINI_TOOLBAR_FLAG] && !this[MINI_NODE_REMOVED_KEY] && !hasMainStagePanel(this)) {
				reconcileLateMiniWidgets(this, this[MINI_STATE_KEY]);
			}
			return result;
		};
	}
	prototype.onNodeCreated = function () {
		delete this[MINI_NODE_REMOVED_KEY];
		const result = originalOnNodeCreated?.apply(this, arguments);
		setTimeout(() => {
			if (!this[MINI_NODE_REMOVED_KEY]) ensureMiniToolbar(this);
		}, 0);
		return result;
	};
	prototype.onRemoved = function () {
		this[MINI_NODE_REMOVED_KEY] = true;
		try {
			return originalOnRemoved?.apply(this, arguments);
		} finally {
			cleanupMiniToolbar(this, { scheduleLayout: false });
		}
	};
	prototype[MINI_NODE_DEF_HOOK_KEY] = true;
	return true;
}

function sendFrontendProbe(marker) {
	try {
		fetch(`/qwen_te/frontend_probe?kind=mini_toolbar&marker=${encodeURIComponent(String(marker ?? ""))}`, {
			method: "GET",
			cache: "no-store",
		}).catch(() => {});
	} catch (_error) {}
}

globalThis.__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__ = cleanupMiniToolbar;
globalThis.__QWEN_TE_STAGE_ENSURE_MINI_TOOLBAR__ = ensureMiniToolbar;

app.registerExtension({
	name: "QwenTE.StagePromptGeneratorMiniToolbar",
	async beforeRegisterNodeDef(nodeType, nodeData) {
		const isTarget =
			TARGET_NODE_CLASSES.has(nodeData?.name) ||
		hasStagePromptDisplayName(nodeData?.display_name ?? nodeData?.displayName ?? "");
		if (!isTarget) return;
		installMiniNodeLifecycleHooks(nodeType);
	},
	async setup() {
		sendFrontendProbe("setup");
		clearMiniStartupScanTimer();
		enhanceExistingNodes();
		installMiniGraphNodeAddedHook();
		startMiniStartupScan();
	},
	async nodeCreated(node) {
		if (!isStagePromptNode(node)) return;
		delete node[MINI_NODE_REMOVED_KEY];
		sendFrontendProbe("nodeCreated");
		ensureMiniToolbar(node);
		refreshMiniToolbar(node);
	},
});
