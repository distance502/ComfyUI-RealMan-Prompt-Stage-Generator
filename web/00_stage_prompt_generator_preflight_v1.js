import { app } from "../../scripts/app.js";

const TARGET_NODE_CLASSES = new Set([
	"QwenTE_StagePromptGenerator",
	"QwenTE_UniversalStagePromptGenerator",
]);
const DISPLAY_NAME_MARKERS = ["阶段式提示词生成器", "真男人提示词阶段生成器"];
const STAGE_WIDGET_SIGNATURE_NAMES = ["qwen模型", "模板风格", "首条正向提示词"];
const RAW_TAG_REGEX = /标签\d+$/u;
const CUSTOM_TAG_WIDGET = "自定义补充标签";
const MINI_WIDGET_STASH_KEY = Symbol.for("qwenTeMiniWidgetStash");
const PANEL_KEY = Symbol.for("qwen_te.stage_prompt.panel");
const PANEL_READY_KEY = Symbol.for("qwen_te.stage_prompt.panel_ready");
const PREFLIGHT_NODE_DEF_HOOK_KEY = Symbol.for("qwenTeStagePreflightNodeDefHookV1");
const PREFLIGHT_LAYOUT_PENDING_KEY = Symbol.for("qwenTeStagePreflightLayoutPendingV1");
const PREFLIGHT_SCAN_TIMER_KEY = "__qwenTeStagePreflightScanTimerV1";
const PREFLIGHT_SCAN_LIMIT = 8;
const PREFLIGHT_SCAN_INTERVAL_MS = 500;
const PREFLIGHT_MIN_WIDTH = 420;
const PREFLIGHT_MIN_HEIGHT = 120;
const PREFLIGHT_MAX_HEIGHT = 520;

const PREFLIGHT_VISIBLE_WIDGET_NAMES = new Set([
	"模板风格",
	"运行时随机标签",
	"运行时随机模式",
	"随机主题池",
	"生成数量",
	"提示词语言",
	"详细度",
	"输出模式",
	"状态",
	"摘要",
	"qwen模型",
	"参考图片",
	"首条正向提示词",
	"qwen_te_tag_panel",
	"qwen_te_mini_toolbar_dom",
]);

function hasStageDisplayName(value) {
	const text = String(value ?? "");
	return DISPLAY_NAME_MARKERS.some((marker) => text.includes(marker));
}

function isStageNode(node) {
	if (!node) return false;
	if ([node.comfyClass, node.type].some((value) => TARGET_NODE_CLASSES.has(String(value ?? "")))) return true;
	if (hasStageDisplayName(node.title)) return true;
	const names = new Set((node.widgets ?? []).map((widget) => String(widget?.name ?? "")));
	return STAGE_WIDGET_SIGNATURE_NAMES.every((name) => names.has(name));
}

function hasMainPanel(node) {
	return node?.[PANEL_READY_KEY] === true
		&& node?.[PANEL_KEY]?.ready === true
		&& !!node?.widgets?.some((widget) => widget?.name === "qwen_te_tag_panel");
}

function shouldCollapseWidget(widget) {
	const name = String(widget?.name ?? "");
	if (!name || PREFLIGHT_VISIBLE_WIDGET_NAMES.has(name) || name.startsWith("TE·")) return false;
	if (widget?.__qwenStageMiniWidget || widget?.__qwenStageFallbackWidget || widget?.serialize === false) return false;
	if (String(widget?.type ?? "").toLowerCase() === "button") return false;
	return RAW_TAG_REGEX.test(name) || name === CUSTOM_TAG_WIDGET || widget?.serialize !== false;
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

function collapseWidget(widget) {
	if (!shouldCollapseWidget(widget)) return false;
	stashWidget(widget);
	widget.type = "easyHiddenPreflightV1";
	widget.computeSize = () => [0, -4];
	widget.hidden = true;
	widget.options = widget.options ?? {};
	widget.options.hidden = true;
	if (widget.inputEl?.style) widget.inputEl.style.display = "none";
	if (widget.element?.style) widget.element.style.display = "none";
	return true;
}

function applyCompactNodeSize(node) {
	if (!node || hasMainPanel(node)) return false;
	let computed = null;
	try {
		computed = node.computeSize?.() ?? node.size;
	} catch (_error) {
		computed = node.size;
	}
	const width = Math.max(PREFLIGHT_MIN_WIDTH, Number(computed?.[0] ?? node.size?.[0] ?? 0) || 0);
	const measuredHeight = Number(computed?.[1] ?? node.size?.[1] ?? PREFLIGHT_MIN_HEIGHT) || PREFLIGHT_MIN_HEIGHT;
	const height = Math.min(PREFLIGHT_MAX_HEIGHT, Math.max(PREFLIGHT_MIN_HEIGHT, measuredHeight));
	try {
		node.setSize?.([width, height]);
		app.graph?.setDirtyCanvas?.(true, true);
		return true;
	} catch (_error) {
		return false;
	}
}

function scheduleCompactNodeSize(node) {
	if (!node || node[PREFLIGHT_LAYOUT_PENDING_KEY] != null) return false;
	const timer = setTimeout(() => {
		if (node[PREFLIGHT_LAYOUT_PENDING_KEY] !== timer) return;
		delete node[PREFLIGHT_LAYOUT_PENDING_KEY];
		const apply = () => applyCompactNodeSize(node);
		if (typeof requestAnimationFrame === "function") requestAnimationFrame(apply);
		else apply();
	}, 0);
	node[PREFLIGHT_LAYOUT_PENDING_KEY] = timer;
	timer?.unref?.();
	return true;
}

function compactStageNode(node) {
	if (!isStageNode(node) || hasMainPanel(node)) return false;
	let changed = false;
	for (const widget of node.widgets ?? []) changed = collapseWidget(widget) || changed;
	if (changed) scheduleCompactNodeSize(node);
	return changed;
}

function installPreflightNodeHooks(nodeType) {
	const prototype = nodeType?.prototype;
	if (!prototype || prototype[PREFLIGHT_NODE_DEF_HOOK_KEY]) return false;
	const originalAddWidget = prototype.addWidget;
	if (typeof originalAddWidget === "function") {
		prototype.addWidget = function () {
			const widget = originalAddWidget.apply(this, arguments);
			if (!hasMainPanel(this) && collapseWidget(widget)) scheduleCompactNodeSize(this);
			return widget;
		};
	}
	const originalOnNodeCreated = prototype.onNodeCreated;
	prototype.onNodeCreated = function () {
		const result = originalOnNodeCreated?.apply(this, arguments);
		compactStageNode(this);
		return result;
	};
	prototype[PREFLIGHT_NODE_DEF_HOOK_KEY] = true;
	return true;
}

function compactExistingStageNodes() {
	for (const node of app.graph?._nodes ?? []) compactStageNode(node);
}

function startPreflightScan() {
	if (globalThis[PREFLIGHT_SCAN_TIMER_KEY] != null) clearInterval(globalThis[PREFLIGHT_SCAN_TIMER_KEY]);
	let passes = 0;
	let timer = null;
	timer = setInterval(() => {
		if (globalThis[PREFLIGHT_SCAN_TIMER_KEY] !== timer) return;
		compactExistingStageNodes();
		passes += 1;
		if (passes >= PREFLIGHT_SCAN_LIMIT) {
			clearInterval(timer);
			if (globalThis[PREFLIGHT_SCAN_TIMER_KEY] === timer) globalThis[PREFLIGHT_SCAN_TIMER_KEY] = null;
		}
	}, PREFLIGHT_SCAN_INTERVAL_MS);
	globalThis[PREFLIGHT_SCAN_TIMER_KEY] = timer;
	timer?.unref?.();
	return timer;
}

app.registerExtension({
	name: "QwenTE.StagePromptPreflightV1",
	async beforeRegisterNodeDef(nodeType, nodeData) {
		const isTarget = TARGET_NODE_CLASSES.has(String(nodeData?.name ?? ""))
			|| hasStageDisplayName(nodeData?.display_name ?? nodeData?.displayName);
		if (isTarget) installPreflightNodeHooks(nodeType);
	},
	async setup() {
		compactExistingStageNodes();
		startPreflightScan();
	},
	async nodeCreated(node) {
		compactStageNode(node);
	},
});
