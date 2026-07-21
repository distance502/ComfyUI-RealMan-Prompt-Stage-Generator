import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const MINI_TOOLBAR_PATH = path.join(ROOT, "web", "stage_prompt_generator_mini_toolbar.js");

class MockElement {
	constructor(tagName = "div") {
		this.tagName = String(tagName).toUpperCase();
		this.children = [];
		this.parentNode = null;
		this.style = {};
		this.style.setProperty = (name, value, priority = "") => {
			this.style[name] = String(value);
			this.style[`${name}Priority`] = String(priority);
		};
		this.dataset = {};
		this.attributes = {};
		this.className = "";
		this.textContent = "";
		this.type = "";
		this.listeners = new Map();
		this.classList = {
			toggle: (className, force) => {
				const classes = new Set(String(this.className ?? "").split(/\s+/u).filter(Boolean));
				const shouldAdd = force === undefined ? !classes.has(className) : !!force;
				if (shouldAdd) classes.add(className);
				else classes.delete(className);
				this.className = [...classes].join(" ");
				return shouldAdd;
			},
			contains: (className) => String(this.className ?? "").split(/\s+/u).includes(className),
		};
	}

	appendChild(child) {
		this.children.push(child);
		child.parentNode = this;
		child.parentElement = this;
		return child;
	}

	addEventListener(type, handler) {
		if (!this.listeners.has(type)) this.listeners.set(type, []);
		this.listeners.get(type).push(handler);
	}

	removeEventListener(type, handler) {
		const handlers = this.listeners.get(type) ?? [];
		this.listeners.set(type, handlers.filter((item) => item !== handler));
	}

	setAttribute(name, value) {
		this.attributes[name] = String(value);
	}

	remove() {
		if (!this.parentNode) return;
		this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
		this.parentNode = null;
		this.parentElement = null;
	}

	async click() {
		const event = { type: "click", stopPropagation() {}, preventDefault() {} };
		for (const handler of this.listeners.get("click") ?? []) await handler(event);
	}

	querySelector(selector) {
		return this.querySelectorAll(selector)[0] ?? null;
	}

	querySelectorAll(selector) {
		const matches = [];
		const match = (element) => {
			if (selector === "button") return element.tagName === "BUTTON";
			if (selector.startsWith(".")) {
				return String(element.className ?? "").split(/\s+/u).includes(selector.slice(1));
			}
			return element.tagName.toLowerCase() === selector.toLowerCase();
		};
		const visit = (element) => {
			if (match(element)) matches.push(element);
			for (const child of element.children ?? []) visit(child);
		};
		for (const child of this.children) visit(child);
		return matches;
	}

	getBoundingClientRect() {
		return { x: 0, y: 0, width: 420, height: 118 };
	}

	get scrollHeight() {
		return this._scrollHeight ?? 0;
	}

	set scrollHeight(value) {
		this._scrollHeight = value;
	}

	get offsetHeight() {
		return this._offsetHeight ?? 0;
	}

	set offsetHeight(value) {
		this._offsetHeight = value;
	}
}

async function loadMiniToolbarExports() {
	const rawSource = await fs.readFile(MINI_TOOLBAR_PATH, "utf8");
	const source = rawSource.replace('import { app } from "/scripts/app.js";', "const app = globalThis.__testApp;");
	const registeredExtensions = [];
	const exportTail = `
globalThis.__miniToolbarTestExports = {
	isStagePromptNode,
	ensureMiniToolbar,
	cleanupMiniToolbar,
	cleanupLegacyMiniWidgets,
	enhanceExistingNodes,
	clearMiniStartupScanTimer,
	startMiniStartupScan,
	installMiniGraphNodeAddedHook,
	installMiniNodeLifecycleHooks,
	MINI_STARTUP_SCAN_TIMER_KEY,
	MINI_STARTUP_SCAN_LIMIT,
	buildSelectedTagsText,
	buildMiniBaseStatus,
	applyMiniRandomAction,
	openMiniNsfwWorkspaceAction,
	resolveMiniCopyAction,
	clearMiniSelectionAction,
};
`;
	const context = {
		console,
		setTimeout,
		clearTimeout,
		setInterval,
		clearInterval,
		requestAnimationFrame: (fn) => {
			if (typeof fn === "function") fn();
			return 0;
		},
		globalThis: null,
		window: {},
		document: {
			head: new MockElement("head"),
			body: new MockElement("body"),
			createElement: (tagName) => new MockElement(tagName),
			querySelector() { return null; },
			querySelectorAll() { return []; },
		},
		HTMLElement: MockElement,
		ResizeObserver: class {
			observe() {}
			disconnect() {}
		},
		navigator: { clipboard: { writeText: async () => {} } },
		__testApp: {
			registerExtension(extension) { registeredExtensions.push(extension); },
			graph: { _nodes: [], setDirtyCanvas() {} },
		},
	};
	context.globalThis = context;
	context.window = context;
	vm.runInNewContext(`${source}\n${exportTail}`, context, { filename: MINI_TOOLBAR_PATH });
	return { ...context.__miniToolbarTestExports, __context: context, __extension: registeredExtensions[0] };
}

test("legacy mini cleanup preserves the main panel status rows", async () => {
	const exports = await loadMiniToolbarExports();
	const fallbackWidget = (name) => ({ name, serialize: false, __qwenStageFallbackWidget: true });
	const node = {
		widgets: [
			fallbackWidget("状态"),
			fallbackWidget("摘要"),
			fallbackWidget("标签"),
			fallbackWidget("随机跑"),
			{ name: "模板风格", serialize: true },
		],
	};

	assert.equal(exports.cleanupLegacyMiniWidgets(node), true);
	assert.deepEqual(Array.from(node.widgets, (widget) => widget.name), ["状态", "摘要", "模板风格"]);
});

test("buildMiniBaseStatus prefers operational state over fold state noise", async () => {
	const exports = await loadMiniToolbarExports();
	assert.equal(
		exports.buildMiniBaseStatus({
			selectedCount: 3,
			randomEnabled: true,
			suppressEnabled: true,
			hasPromptOutput: true,
		}),
		"已选 3 · 随机 ON · 抑字 ON · 可复制正向",
	);
});

test("isStagePromptNode recognizes raw widget-only stage nodes", async () => {
	const exports = await loadMiniToolbarExports();
	assert.equal(
		exports.isStagePromptNode({
			widgets: [
				{ name: "qwen模型" },
				{ name: "模板风格" },
				{ name: "首条正向提示词" },
			],
			outputs: [],
		}),
		true,
	);
});

test("isStagePromptNode rejects generic single outputs and keeps legacy output signatures", async () => {
	const exports = await loadMiniToolbarExports();
	assert.equal(exports.isStagePromptNode({
		type: "QwenTE_ModelLoader",
		title: "Qwen TE 模型加载器",
		widgets: [{ name: "模型系列" }, { name: "主模型" }],
		outputs: [{ name: "qwen模型" }],
	}), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "JSON结果" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "正向提示词合集" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "JSON结果" }, { name: "JSON" }, { name: "JSON结果" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "QwenTE_StagePromptGenerator", outputs: [] }), true);
	assert.equal(exports.isStagePromptNode({ title: "Qwen TE 阶段式提示词生成器", outputs: [] }), true);
	assert.equal(exports.isStagePromptNode({
		type: "LegacyStageNode",
		outputs: [
			{ name: "全文", _qwenTeOriginalName: "结果全文" },
			{ name: "JSON", _qwenTeOriginalName: "JSON结果" },
			{ name: "合集", _qwenTeOriginalName: "正向提示词合集" },
		],
	}), true);
});

test("resolveMiniCopyAction uses latest positive prompt output", async () => {
	const exports = await loadMiniToolbarExports();
	const copied = [];
	const okMessage = await exports.resolveMiniCopyAction(
		{ id: 7 },
		{
			getPromptOutputText: () => "PROMPT TEXT",
			copyText: async (text) => {
				copied.push(text);
				return true;
			},
		},
	);
	assert.equal(okMessage, "已复制正向提示词。");
	assert.deepEqual(copied, ["PROMPT TEXT"]);

	const emptyMessage = await exports.resolveMiniCopyAction(
		{ id: 8 },
		{
			getPromptOutputText: () => "",
			copyText: async () => true,
		},
	);
	assert.equal(emptyMessage, "还没有可复制的提示词，请先运行一次节点。");
});

test("clearMiniSelectionAction asks for confirmation before clearing", async () => {
	const exports = await loadMiniToolbarExports();
	const writes = [];
	const cancelMessage = await exports.clearMiniSelectionAction(
		{},
		["主体标签1", "自定义补充标签"],
		{
			confirmClear: () => false,
			setWidgetValue: (node, name, value) => {
				writes.push([name, value]);
				return true;
			},
		},
	);
	assert.equal(cancelMessage, "已取消清空。");
	assert.deepEqual(writes, []);

	const clearedWrites = [];
	const okMessage = await exports.clearMiniSelectionAction(
		{},
		["主体标签1", "自定义补充标签"],
		{
			confirmClear: () => true,
			setWidgetValue: (node, name, value) => {
				clearedWrites.push([name, value]);
				return true;
			},
		},
	);
	assert.equal(okMessage, "已清空当前标签与用户输入。");
	assert.deepEqual(clearedWrites, [
		["主体标签1", "无"],
		["自定义补充标签", ""],
		["额外要求", ""],
		["智能文本输入", ""],
		["智能文本匹配", false],
	]);
});

test("clearMiniSelectionAction supports explicit boolean confirm results", async () => {
	const exports = await loadMiniToolbarExports();
	const writes = [];
	const message = await exports.clearMiniSelectionAction(
		{},
		["主体标签1"],
		{
			confirmClear: () => 0,
			setWidgetValue: (_node, name, value) => {
				writes.push([name, value]);
				return true;
			},
		},
	);
	assert.equal(message, "已取消清空。");
	assert.deepEqual(writes, []);
});

test("clearMiniSelectionAction can skip native confirm when forceConfirmed is set", async () => {
	const exports = await loadMiniToolbarExports();
	const writes = [];
	const message = await exports.clearMiniSelectionAction(
		{},
		["主体标签1", "自定义补充标签"],
		{
			forceConfirmed: true,
			confirmClear: () => {
				throw new Error("confirmClear should not be called");
			},
			setWidgetValue: (_node, name, value) => {
				writes.push([name, value]);
				return true;
			},
		},
	);
	assert.equal(message, "已清空当前标签与用户输入。");
	assert.deepEqual(writes, [
		["主体标签1", "无"],
		["自定义补充标签", ""],
		["额外要求", ""],
		["智能文本输入", ""],
		["智能文本匹配", false],
	]);
});

test("applyMiniRandomAction reports success and never queues directly", async () => {
	const exports = await loadMiniToolbarExports();
	const applied = [];
	const message = await exports.applyMiniRandomAction(
		{ id: 9 },
		{
			applyRandomState: async () => {
				applied.push("randomized");
				return true;
			},
		},
	);
	assert.equal(message, "已随机生成当前标签组合。");
	assert.deepEqual(applied, ["randomized"]);
});

test("mini random and clear prefer atomic main UI bridges", async () => {
	const exports = await loadMiniToolbarExports();
	const calls = [];
	exports.__context.__QWEN_TE_STAGE_APPLY_RANDOM_STATE__ = async (node) => {
		calls.push(["random", node.id]);
		return true;
	};
	exports.__context.__QWEN_TE_STAGE_CLEAR_NODE_STATE__ = async (node) => {
		calls.push(["clear", node.id]);
		return true;
	};
	const node = { id: 19 };
	assert.equal(await exports.applyMiniRandomAction(node), "已随机生成当前标签组合。");
	assert.equal(
		await exports.clearMiniSelectionAction(node, ["主体标签1"], { forceConfirmed: true }),
		"已清空当前标签与用户输入。",
	);
	assert.deepEqual(calls, [["random", 19], ["clear", 19]]);
});

test("ensureMiniToolbar keeps a lean practical button set", async () => {
	const exports = await loadMiniToolbarExports();
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "" },
			{ name: "运行时随机标签", value: false },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) {
			this.size = size;
		},
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	const labels = addedWidgets[0].element.querySelectorAll("button").map((button) => button.textContent);
	assert.deepEqual(labels, ["标签", "随机", "入队", "槽位", "高级", "NSFW", "清空"]);
	assert.equal(labels.includes("复制"), false);
	assert.equal(labels.includes("柔肤"), false);
	assert.equal(labels.includes("抑字"), false);
});

test("mini clear confirmation expires, cancels on other actions, and cleans up its timer", async () => {
	const exports = await loadMiniToolbarExports();
	let nextTimerId = 1;
	const timers = new Map();
	exports.__context.setTimeout = (callback, delay) => {
		const id = nextTimerId++;
		timers.set(id, { callback, delay });
		return id;
	};
	exports.__context.clearTimeout = (id) => { timers.delete(id); };
	let clearCalls = 0;
	exports.__context.__QWEN_TE_STAGE_CLEAR_NODE_STATE__ = async () => {
		clearCalls += 1;
		return true;
	};
	exports.__context.__QWEN_TE_STAGE_APPLY_RANDOM_STATE__ = async () => true;
	const addedWidgets = [];
	const node = {
		title: "Qwen TE 阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "" },
			{ name: "运行时随机标签", value: false },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);
	const root = addedWidgets[0].element;
	const getButton = (label) => root.querySelectorAll("button").find((button) => button.textContent === label);
	const clearButton = getButton("清空");
	const randomButton = getButton("随机");

	await clearButton.click();
	assert.equal(clearCalls, 0);
	assert.equal(clearButton.textContent, "确认清空");
	assert.equal(clearButton.attributes["aria-pressed"], "true");
	assert.equal(timers.size, 1);
	const expiry = [...timers.values()][0];
	assert.equal(expiry.delay, 4000);
	expiry.callback();
	assert.equal(clearButton.textContent, "清空");
	assert.equal(clearButton.attributes["aria-pressed"], "false");
	assert.equal(timers.size, 0);
	assert.notEqual(root.querySelector(".qwen-te-mini__meta").textContent, "再次点击“清空”以确认。");

	await clearButton.click();
	assert.equal(timers.size, 1);
	await randomButton.click();
	assert.equal(clearButton.textContent, "清空");
	assert.equal(timers.size, 0);
	assert.equal(clearCalls, 0);

	await clearButton.click();
	await clearButton.click();
	assert.equal(clearCalls, 1);
	assert.equal(clearButton.textContent, "清空");
	assert.equal(timers.size, 0);

	await clearButton.click();
	assert.equal(timers.size, 1);
	assert.equal(exports.cleanupMiniToolbar(node, { scheduleLayout: false }), true);
	assert.equal(timers.size, 0);
});

test("ensureMiniToolbar renders NSFW action and opens workspace bridge", async () => {
	const exports = await loadMiniToolbarExports();
	const openedNodes = [];
	exports.__context.__QWEN_TE_STAGE_OPEN_NSFW_WORKSPACE__ = async (node) => {
		openedNodes.push(node);
		return true;
	};
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "" },
			{ name: "运行时随机标签", value: false },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) {
			this.size = size;
		},
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	assert.equal(addedWidgets.length, 1);
	const root = addedWidgets[0].element;
	const buttons = root.querySelectorAll("button");
	const nsfwButton = buttons.find((button) => button.textContent === "NSFW");
	assert.ok(nsfwButton);
	assert.equal(root.dataset.qwenTeMiniToolbar, "true");
	assert.equal(root.parentElement.dataset.qwenTeMiniToolbar, "true");
	assert.equal(root.parentElement.style["z-index"], "10020");
	assert.equal(root.parentElement.style["z-indexPriority"], "important");

	await nsfwButton.click();

	assert.deepEqual(openedNodes, [node]);
	assert.equal(root.querySelector(".qwen-te-mini__meta").textContent, "已打开 NSFW 工作台。");
});

test("main script load alone does not disable the per-node mini fallback", async () => {
	const exports = await loadMiniToolbarExports();
	exports.__context.__QWEN_TE_STAGE_MAIN_UI__ = true;
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) {
			this.size = size;
		},
		addDOMWidget(name, type, element, options) {
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	assert.equal(addedWidgets.length, 1);
	assert.equal(addedWidgets[0].name, "qwen_te_mini_toolbar_dom");
	assert.equal(node.title.endsWith(" [TEmini]"), true);
});

test("a confirmed main panel remains authoritative when the main script is loaded", async () => {
	const exports = await loadMiniToolbarExports();
	exports.__context.__QWEN_TE_STAGE_MAIN_UI__ = true;
	const addedWidgets = [];
	const panelKey = Symbol.for("qwen_te.stage_prompt.panel");
	const panelReadyKey = Symbol.for("qwen_te.stage_prompt.panel_ready");
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [{ name: "qwen_te_tag_panel", serialize: false }],
		outputs: [],
		addDOMWidget(name) {
			addedWidgets.push(name);
			return { name };
		},
	};
	node[panelKey] = { ready: true };
	node[panelReadyKey] = true;

	exports.ensureMiniToolbar(node);

	assert.deepEqual(addedWidgets, []);
	assert.equal(node.title.endsWith(" [TEmini]"), false);
});

test("an orphan main panel cannot suppress the compact mini fallback", async () => {
	const exports = await loadMiniToolbarExports();
	const rawWidget = { name: "主体标签20", value: "无", type: "combo", options: {}, inputEl: { style: {} }, element: { style: {} } };
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [{ name: "qwen_te_tag_panel", serialize: false }, rawWidget],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, element, options) {
			const widget = { name, type, element, options, serialize: true };
			this.widgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	assert.equal(node.widgets.some((widget) => widget.name === "qwen_te_tag_panel"), false);
	assert.equal(node.widgets.some((widget) => widget.name === "qwen_te_mini_toolbar_dom"), true);
	assert.equal(rawWidget.hidden, true);
	assert.deepEqual(Array.from(rawWidget.computeSize()), [0, -4]);
});

test("explicit mini mode remains available when the main script is loaded", async () => {
	const exports = await loadMiniToolbarExports();
	exports.__context.__QWEN_TE_STAGE_MAIN_UI__ = true;
	exports.__context.location = { href: "http://127.0.0.1:8188/?qwen_te_mini=1" };
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, element, options) {
			const widget = { name, type, element, options, serialize: true };
			this.widgets.push(widget);
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	assert.equal(addedWidgets.length, 1);
	assert.equal(addedWidgets[0].name, "qwen_te_mini_toolbar_dom");
});

test("mini fallback collapses slots 11-20, future raw controls, and internal state", async () => {
	const exports = await loadMiniToolbarExports();
	exports.__context.__QWEN_TE_STAGE_MAIN_UI__ = true;
	const makeWidget = (name, value = "") => ({
		name,
		value,
		type: "combo",
		serialize: true,
		hidden: false,
		options: { hidden: false },
		computeSize: () => [240, 24],
		inputEl: { style: {} },
		element: { style: {} },
	});
	const tag11 = makeWidget("主体标签11", "无");
	const tag20 = makeWidget("画面风格标签20", "无");
	const styleIsolation = makeWidget("风格隔离策略", "平衡收敛");
	const modelSource = makeWidget("模型来源", "仅Skill");
	const futureControl = makeWidget("未来新增参数", "默认");
	const internalCache = makeWidget("连续生成避重缓存", "内部值");
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			tag11,
			tag20,
			styleIsolation,
			modelSource,
			futureControl,
			internalCache,
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, element, options) {
			const widget = { name, type, element, options, serialize: false };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	for (const widget of [tag11, tag20, styleIsolation, modelSource, futureControl, internalCache]) {
		assert.equal(widget.hidden, true, `${widget.name} should start collapsed`);
		assert.equal(widget.inputEl.style.display, "none");
	}
	const root = addedWidgets[0].element;
	const getButton = (label) => root.querySelectorAll("button").find((button) => button.textContent === label);
	await getButton("高级").click();
	for (const widget of [styleIsolation, modelSource, futureControl]) assert.equal(widget.hidden, false);
	assert.equal(internalCache.hidden, true);
	await getButton("槽位").click();
	assert.equal(tag11.hidden, false);
	assert.equal(tag20.hidden, false);
});

test("failed mini DOM registration restores native widgets and remains retryable", async () => {
	const exports = await loadMiniToolbarExports();
	const originalComputeSize = () => [240, 24];
	const rawWidget = {
		name: "主体标签20",
		value: "无",
		type: "combo",
		serialize: true,
		hidden: false,
		options: { hidden: false },
		computeSize: originalComputeSize,
		inputEl: { style: { display: "grid" } },
		element: { style: { display: "flex" } },
	};
	let addCalls = 0;
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [rawWidget],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget() {
			addCalls += 1;
			return null;
		},
	};

	assert.equal(exports.ensureMiniToolbar(node), false);
	assert.equal(exports.ensureMiniToolbar(node), false);

	assert.equal(addCalls, 2);
	assert.equal(node.title.endsWith(" [TEmini]"), false);
	assert.equal(rawWidget.type, "combo");
	assert.equal(rawWidget.computeSize, originalComputeSize);
	assert.equal(rawWidget.hidden, false);
	assert.equal(rawWidget.inputEl.style.display, "grid");
	assert.equal(rawWidget.element.style.display, "flex");
});

test("mini cleanup restores every stashed native widget field", async () => {
	const exports = await loadMiniToolbarExports();
	const originalComputeSize = () => [240, 24];
	const inputEl = { style: { display: "grid" } };
	const element = { style: { display: "flex" } };
	const rawWidget = {
		name: "主体标签1",
		type: "combo",
		computeSize: originalComputeSize,
		hidden: false,
		options: { hidden: false },
		inputEl,
		element,
	};
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			rawWidget,
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, domElement, options) {
			const widget = { name, type, element: domElement, options, serialize: true, __qwenStageMiniWidget: true };
			this.widgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);
	assert.match(rawWidget.type, /^easyHidden/u);
	assert.equal(rawWidget.hidden, true);
	assert.equal(inputEl.style.display, "none");
	assert.equal(element.style.display, "none");

	assert.equal(exports.cleanupMiniToolbar(node, { scheduleLayout: false }), true);
	assert.equal(rawWidget.type, "combo");
	assert.equal(rawWidget.computeSize, originalComputeSize);
	assert.equal(rawWidget.hidden, false);
	assert.equal(rawWidget.options.hidden, false);
	assert.equal(inputEl.style.display, "grid");
	assert.equal(element.style.display, "flex");
});

test("ensureMiniToolbar removes stale DOM toolbar when main panel is present", async () => {
	const exports = await loadMiniToolbarExports();
	const addedWidgets = [];
	const disconnected = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "" },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) {
			this.size = size;
		},
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};
	exports.__context.ResizeObserver = class {
		observe() {}
		disconnect() {
			disconnected.push(true);
		}
	};

	exports.ensureMiniToolbar(node);
	const root = addedWidgets[0].element;
	const wrapper = root.parentElement;
	assert.equal(wrapper.children.includes(root), true);
	assert.equal(node.title.endsWith(" [TEmini]"), true);

	node.widgets.push({ name: "qwen_te_tag_panel", serialize: false });
	node[Symbol.for("qwen_te.stage_prompt.panel")] = { ready: true };
	node[Symbol.for("qwen_te.stage_prompt.panel_ready")] = true;
	exports.ensureMiniToolbar(node);

	assert.equal(wrapper.children.includes(root), false);
	assert.equal(disconnected.length, 1);
	assert.equal(node.widgets.some((widget) => widget.name === "qwen_te_mini_toolbar_dom"), false);
	assert.equal(node.title.endsWith(" [TEmini]"), false);
});

test("ensureMiniToolbar computeSize keeps DOM hit box tall enough for buttons", async () => {
	const exports = await loadMiniToolbarExports();
	const addedWidgets = [];
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "" },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) {
			this.size = size;
		},
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true };
			addedWidgets.push(widget);
			return widget;
		},
	};

	exports.ensureMiniToolbar(node);

	const root = addedWidgets[0].element;
	const shell = root.querySelector(".qwen-te-mini__shell");
	root.getBoundingClientRect = () => ({ x: 0, y: 0, width: 420, height: 40 });
	shell.getBoundingClientRect = () => ({ x: 0, y: 0, width: 420, height: 40 });
	root.scrollHeight = 40;
	root.offsetHeight = 40;
	shell.scrollHeight = 156;
	shell.offsetHeight = 156;

	const [, height] = addedWidgets[0].computeSize(420);

	assert.ok(height >= 168);
});

test("clean main-panel nodes do not trigger repeated mini cleanup layouts", async () => {
	const exports = await loadMiniToolbarExports();
	let setSizeCalls = 0;
	let dirtyCalls = 0;
	const node = {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [{ name: "qwen_te_tag_panel", serialize: false }],
		computeSize: () => [420, 280],
		setSize() { setSizeCalls += 1; },
	};
	node[Symbol.for("qwen_te.stage_prompt.panel")] = { ready: true };
	node[Symbol.for("qwen_te.stage_prompt.panel_ready")] = true;
	exports.__context.__testApp.graph = {
		_nodes: [node],
		setDirtyCanvas() { dirtyCalls += 1; },
	};

	for (let index = 0; index < 10; index += 1) exports.enhanceExistingNodes();

	assert.equal(exports.cleanupMiniToolbar(node), false);
	assert.equal(setSizeCalls, 0);
	assert.equal(dirtyCalls, 0);
});

test("setup keeps a bounded fallback scan even when the main script is loaded", async () => {
	const exports = await loadMiniToolbarExports();
	const cleared = [];
	let started = 0;
	exports.__context.clearInterval = (timer) => { cleared.push(timer); };
	exports.__context.setInterval = () => { started += 1; return 202; };
	exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY] = 101;
	exports.__context.__QWEN_TE_STAGE_MAIN_UI__ = true;

	await exports.__extension.setup();

	assert.deepEqual(cleared, [101]);
	assert.equal(started, 1);
	assert.equal(exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY], 202);
});

test("setup keeps one bounded startup scan and graph hook across repeated setup", async () => {
	const exports = await loadMiniToolbarExports();
	const timers = new Map();
	const cleared = [];
	let nextTimerId = 300;
	exports.__context.setInterval = (callback, intervalMs) => {
		const timerId = ++nextTimerId;
		timers.set(timerId, { callback, intervalMs });
		return timerId;
	};
	exports.__context.clearInterval = (timerId) => {
		cleared.push(timerId);
		timers.delete(timerId);
	};
	exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY] = 299;

	await exports.__extension.setup();
	const firstTimerId = exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY];
	const firstGraphHook = exports.__context.__testApp.graph.onNodeAdded;
	await exports.__extension.setup();
	const activeTimerId = exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY];

	assert.deepEqual(cleared.slice(0, 2), [299, firstTimerId]);
	assert.notEqual(activeTimerId, firstTimerId);
	assert.equal(timers.size, 1);
	assert.equal(exports.__context.__testApp.graph.onNodeAdded, firstGraphHook);
	assert.equal(timers.get(activeTimerId).intervalMs, 1200);

	const activeCallback = timers.get(activeTimerId).callback;
	for (let index = 0; index < exports.MINI_STARTUP_SCAN_LIMIT; index += 1) activeCallback();

	assert.equal(timers.size, 0);
	assert.equal(exports.__context[exports.MINI_STARTUP_SCAN_TIMER_KEY], null);
	assert.equal(cleared.at(-1), activeTimerId);
});

test("node lifecycle hooks are idempotent and onRemoved disposes the toolbar", async () => {
	const exports = await loadMiniToolbarExports();
	let originalRemovedCalls = 0;
	let disconnected = 0;
	function StageNode() {}
	StageNode.prototype.onNodeCreated = function () { return "created"; };
	StageNode.prototype.onRemoved = function () {
		originalRemovedCalls += 1;
		return "removed";
	};
	const nodeData = { name: "QwenTE_StagePromptGenerator" };

	await exports.__extension.beforeRegisterNodeDef(StageNode, nodeData);
	const createdHook = StageNode.prototype.onNodeCreated;
	const removedHook = StageNode.prototype.onRemoved;
	await exports.__extension.beforeRegisterNodeDef(StageNode, nodeData);

	assert.equal(StageNode.prototype.onNodeCreated, createdHook);
	assert.equal(StageNode.prototype.onRemoved, removedHook);

	exports.__context.ResizeObserver = class {
		observe() {}
		disconnect() { disconnected += 1; }
	};
	const node = Object.assign(new StageNode(), {
		title: "阶段式提示词生成器",
		comfyClass: "QwenTE_StagePromptGenerator",
		size: [420, 280],
		widgets: [
			{ name: "qwen模型", value: "" },
			{ name: "模板风格", value: "" },
			{ name: "首条正向提示词", value: "" },
		],
		outputs: [],
		computeSize: () => [420, 280],
		setSize(size) { this.size = size; },
		addDOMWidget(name, type, element, options) {
			const wrapper = new MockElement("div");
			wrapper.appendChild(element);
			const widget = { name, type, element, options, serialize: true, __qwenStageMiniWidget: true };
			this.widgets.push(widget);
			return widget;
		},
	});

	exports.ensureMiniToolbar(node);
	const miniWidget = node.widgets.find((widget) => widget.name === "qwen_te_mini_toolbar_dom");
	const root = miniWidget.element;
	assert.equal(StageNode.prototype.onRemoved.call(node), "removed");

	assert.equal(originalRemovedCalls, 1);
	assert.equal(disconnected, 1);
	assert.equal(root.parentElement, null);
	assert.equal(node.widgets.some((widget) => widget.name === "qwen_te_mini_toolbar_dom"), false);
	assert.equal(node.title.endsWith(" [TEmini]"), false);

	exports.ensureMiniToolbar(node);
	assert.equal(node.widgets.some((widget) => widget.name === "qwen_te_mini_toolbar_dom"), false);
});
