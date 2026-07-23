import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const UI_PATH = path.join(ROOT, "web", "stage_prompt_generator_ui_v2.js");

function makeClassList(element) {
	const tokens = new Set();
	const sync = () => { element.className = [...tokens].join(" "); };
	return {
		add(...items) {
			for (const item of items) if (item) tokens.add(String(item));
			sync();
		},
		remove(...items) {
			for (const item of items) tokens.delete(String(item));
			sync();
		},
		toggle(item, force) {
			const token = String(item);
			const shouldAdd = force === undefined ? !tokens.has(token) : !!force;
			if (shouldAdd) tokens.add(token);
			else tokens.delete(token);
			sync();
			return shouldAdd;
		},
		contains(item) {
			return tokens.has(String(item));
		},
	};
}

function makeElement(tagName = "div") {
	const element = {
		tagName: String(tagName).toUpperCase(),
		style: {},
		dataset: {},
		children: [],
		className: "",
		textContent: "",
		value: "",
		isConnected: false,
		parentNode: null,
		appendChild(child) {
			this.children.push(child);
			child.parentNode = this;
			child.isConnected = this.isConnected;
			return child;
		},
		append(...children) {
			for (const child of children) this.appendChild(child);
		},
		replaceChildren(...children) {
			for (const child of this.children) {
				child.parentNode = null;
				child.isConnected = false;
			}
			this.children = [];
			for (const child of children) this.appendChild(child);
		},
		removeChild(child) {
			this.children = this.children.filter((item) => item !== child);
			child.parentNode = null;
			child.isConnected = false;
			return child;
		},
		addEventListener(type, handler) {
			this.__listeners ??= new Map();
			this.__listeners.set(type, handler);
		},
		removeEventListener() {},
		setAttribute(name, value) {
			this.attributes ??= {};
			this.attributes[String(name)] = String(value);
		},
		remove() {
			if (this.parentNode?.removeChild) this.parentNode.removeChild(this);
			this.isConnected = false;
		},
		focus() {},
		querySelector() { return null; },
		querySelectorAll() { return []; },
		getBoundingClientRect() { return { x: 0, y: 0, width: 0, height: 0 }; },
	};
	element.classList = makeClassList(element);
	return element;
}

function makeExternalModelLoaderFixture(options = {}) {
	const specs = [
		["模型系列", "Qwen3.6-VL", "combo", ["Qwen3-VL", "Qwen3.5-VL", "Qwen3.6-VL"]],
		["主模型", "model.gguf", "combo", ["model.gguf"]],
		["视觉投影mmproj", "无", "combo", ["无"]],
		["启用思考", false, "toggle"],
		["保留历史think", false, "toggle"],
		["上下文长度", 8192, "number"],
		["GPU层数", -1, "number"],
		["KV缓存K类型", "f16", "combo", ["f16", "q8_0"]],
		["KV缓存V类型", "f16", "combo", ["f16", "q8_0"]],
		["MoE专家上CPU", false, "toggle"],
		["前N层专家上CPU", 0, "number"],
	];
	let domCalls = 0;
	const widgets = specs.map(([name, value, type, values]) => ({
		name,
		value,
		type,
		hidden: false,
		options: values ? { values } : {},
		computeSize() { return [180, 24]; },
		inputEl: { style: {} },
		element: { style: {} },
	}));
	const node = {
		comfyClass: options.comfyClass ?? "QwenTE_ModelLoader",
		type: options.type ?? "QwenTE_ModelLoader",
		title: options.title ?? "Qwen TE 模型加载器",
		widgets,
		outputs: [{ name: "qwen模型", type: "QWENLLAMA" }],
		size: [420, 320],
		properties: {},
		addDOMWidget() {
			domCalls += 1;
			return null;
		},
	};
	const snapshot = widgets.map((widget) => ({
		widget,
		type: widget.type,
		hidden: widget.hidden,
		computeSize: widget.computeSize,
		inputDisplay: widget.inputEl.style.display,
		elementDisplay: widget.element.style.display,
	}));
	return {
		node,
		assertUntouched() {
			assert.equal(domCalls, 0);
			assert.deepEqual(node.widgets, widgets);
			for (let index = 0; index < snapshot.length; index += 1) {
				const before = snapshot[index];
				const widget = node.widgets[index];
				assert.equal(widget, before.widget);
				assert.equal(widget.type, before.type);
				assert.equal(widget.hidden, before.hidden);
				assert.equal(widget.computeSize, before.computeSize);
				assert.equal(widget.inputEl.style.display, before.inputDisplay);
				assert.equal(widget.element.style.display, before.elementDisplay);
			}
		},
	};
}

async function loadUiExports(href = "http://127.0.0.1:8188/", contextOverrides = {}) {
	const source = await fs.readFile(UI_PATH, "utf8");
	const patchedSource = source
		.replace('import { app } from "../../scripts/app.js";', 'const app = globalThis.__testApp;')
		.replace('const STAGE_PROMPT_MODULE_URL = import.meta.url;', 'const STAGE_PROMPT_MODULE_URL = globalThis.__testModuleUrl;');
	const localStorageValues = new Map();
	const registeredExtensions = [];
const exportTail = `
globalThis.__stagePromptUiTestExports = {
	PANEL_KEY,
	PANEL_READY_KEY,
	STAGE_OUTPUT_INDEX,
	STAGE_DISPLAY_MODES,
	isStagePromptNode,
	shouldForceMiniToolbarMode,
	hasStagePromptDisplayName,
	registerStagePromptMiniBridge,
	getPromptLibrary,
	buildNativePromptLibraryFallback,
	resolveComfyRoute,
	fetchWithTimeout,
	fetchJsonWithTimeout,
	abortOwnedRequest,
	abortOwnedRequests,
	invalidatePromptLibraryCache,
	refreshLibraryOnNode,
	getFreshLibraryForUi,
	buildOnlineSearchQuery,
	chunkOnlineImportTags,
	normalizeOnlineSearchTagItems,
	normalizeOnlineSearchSamples,
	normalizeOnlinePromptItems,
	formatOnlineSearchWarning,
	resolveOnlineSearchLibraryTags,
	resolveOnlineSearchSelectedTags,
	pushOnlineSearchBrowserHistory,
	stepOnlineSearchBrowserHistory,
	resolvePromptBrowserTarget,
	requestEmbeddedPromptBrowser,
	fetchEmbeddedPromptBrowserFrame,
	mapEmbeddedBrowserPointerPoint,
	resolveEmbeddedBrowserViewport,
	getEmbeddedBrowserFrameCaptureProfile,
	getEmbeddedBrowserFramePollDelay,
	openPromptBrowserExternal,
	launchPromptCompanionBrowser,
	getModelRuntimeStatusSummary,
	getModelApiConfigValidationError,
	getModelApiEffectiveConfig,
	getModelLoaderSummary,
	clearPendingModelApiRun,
	rememberModelApiRuntimeSignature,
	invalidateModelApiRuntimeStatus,
	buildModelApiConfigSignature,
	buildModelApiConfigSignatureFromValues,
	applyModelApiProviderPreset,
	NODE_MODEL_API_RUNTIME_SIGNATURE_KEY,
	searchOnlinePromptTags,
	searchOnlinePrompts,
	openOnlinePromptSearchDialog,
	setWidgetGroupVisibility,
	reconcileStagePanelNativeWidgets,
	toggleWidget,
	scheduleNodeLayoutUpdate,
	getStageDisplayPayload,
	getStageHistoryOutputSnapshot,
	resolveHistoryPromptViewStageOutput,
	refreshStageDisplay,
	captureStageExecutionOutputsFromArgs,
	extractStageExecutionHistoryFromArgs,
	captureStageExecutionHistoryFromArgs,
	recordMissingStageExecutionHistoryFromCache,
	reconcileStageExecutionHistoryBeforeOpen,
	getStageOutputCacheLookupIds,
	syncNodeStageOutputCache,
	NODE_CACHE_NAMESPACE_KEY,
	NODE_WORKFLOW_OUTPUT_KEY,
	ensureNodeCacheNamespace,
	normalizeSerializedNodePayload,
	normalizeConfiguredWidgetValues,
	installGlobalStagePromptQueueCapture,
	normalizeStageTimestampMs,
	compactStagePromptOutputs,
	cleanupFixUiArtifacts,
	ensureStagePromptTopStatusWidgets,
	clearStageTerminalPreviewState,
	openStageOutputDialog,
	formatStageOutputForReading,
	summarizeState,
	summarizeHistoryState,
	buildNodeSummaryText,
	setPanelActionButtonState,
	setControlWidgetValue,
	getAdvancedWidgetOptions,
	createAdvancedSelect,
	getAdvancedWidgetTooltip,
	ADVANCED_WIDGET_NAMES,
	CONTROL_WIDGET_OPTIONS,
	bindSummaryRefresh,
	buildLazySlotPanel,
	populateSlotPanel,
	getSlotPanelGroupValues,
	getSlotPanelLibrarySignature,
	normalizeTagGroupSlotLimit,
	getTagGroupSlotLimit,
	toggleBoundedTagSelection,
	getRuntimeRandomAdditionCap,
	setNodeStatusText,
	openNsfwWorkspaceDialog,
	openCharacterSheetDialog,
	buildCharacterSheetState,
	buildCharacterSheetDisabledState,
	runSmartTextMatch,
	waitForNodeExecution,
	getNodeWorkflowQueueRequestedAt,
	queueWorkflowFromNode,
	beginNodeStateMutation,
	isNodeStateMutationCurrent,
	applyNodeState,
	buildAndApplyRandomState,
	applyPresetStateToNode,
	ensureStageOutputPolling,
	stopStageOutputPolling,
	scheduleStageExecutionOutputCapture,
	scheduleEnhanceStagePromptNode,
	cleanupStagePromptNodeRuntime,
	rollbackStagePromptNodeEnhancement,
	enhanceExistingStagePromptNodes,
	disposeModalOverlay,
	markNodeWorkflowQueueRequested,
	prepareStageNodeForQueueCapture,
	clonePresetState,
	createPresetBaseState,
	inferBestExamplePreset,
	inferPresetRecommendation,
	applyNsfwWorkspaceResultToNodeState,
	disableNsfwWorkspaceOnNodeState,
	persistNsfwWorkspaceToggleToNodeState,
	getNodeNsfwWorkspaceState,
	buildNsfwWorkspaceMappedState,
	buildNsfwWorkspaceNegativeSyncPlan,
	findNegativeClipTextEncodeNode,
	syncNegativePromptToGraph,
	cloneNsfwWorkspaceState,
	resolveNsfwWorkspaceCatalog,
	resolveNsfwEffectiveWorkspace,
	pickNsfwOption,
	prepareNsfwRandomNonceForWriteback,
	buildRandomStateLocal,
	parseNsfwCustomFieldLibraryEntries,
	getNsfwCustomFieldOptions,
	addNsfwCustomFieldOptions,
	removeNsfwCustomFieldOption,
	setNsfwCustomFieldLibrary,
	findLatestRollbackHistoryItem,
	buildHistoryDisplaySummaryText,
	buildHistoryStageOutputText,
	buildHistoryPromptViewText,
	getHistoryStageOutput,
	findRelatedHistoryStageOutput,
	attachStageOutputToRecentStateHistory,
	recordStageExecution,
	getNodeHistory,
	setNodeHistory,
	compactHistoryStageOutputPayload,
	buildStageOutputListFromSnapshot,
	getUserPresets,
	setUserPresets,
	saveUserPreset,
	importUserPresetFile,
	importNodeHistoryFile,
	buildClearedNodeState,
	applyClearedNodeState,
	getNodeContinuousRunReport,
	setNodeContinuousRunReport,
	clearNodeContinuousRunReport,
	parseTagBlockComposerState,
	readTagBlockComposerState,
	buildTagBlockComposerStateFromNode,
	serializeTagBlockComposerState,
	removeTagBlockComposerTag,
	normalizeLegacyWidgetValues,
	sanitizeStagePromptNode,
	collectNodeState,
	createRuntimeRandomPreviewMarker,
	PRESET_SETTING_NAMES,
	PRESET_SETTING_DEFAULTS,
	RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME,
	RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME,
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
		ResizeObserver: class {
			observe() {}
			disconnect() {}
		},
		URL,
		window: {},
		localStorage: {
			getItem(key) {
				const storageKey = String(key);
				return localStorageValues.has(storageKey) ? localStorageValues.get(storageKey) : null;
			},
			setItem(key, value) {
				localStorageValues.set(String(key), String(value));
			},
			removeItem(key) {
				localStorageValues.delete(String(key));
			},
			clear() {
				localStorageValues.clear();
			},
		},
		document: {
			body: Object.assign(makeElement("body"), {
				innerText: "",
				isConnected: true,
			}),
			head: { appendChild() {} },
			createElement: makeElement,
			querySelector() { return null; },
			querySelectorAll() { return []; },
			addEventListener() {},
		},
		navigator: { clipboard: { writeText: async () => {} } },
		HTMLElement: class {},
		__testApp: {
			registerExtension(extension) { registeredExtensions.push(extension); },
			graph: { _nodes: [] },
		},
		__testModuleUrl: "http://127.0.0.1:8188/extensions/ComfyUI-RealMan-Prompt-Stage-Generator/stage_prompt_generator_ui_v2.js",
		globalThis: null,
	};
	Object.assign(context, contextOverrides);
	context.globalThis = context;
	context.window = context;
	context.location = { href };
	vm.runInNewContext(`${patchedSource}\n${exportTail}`, context, { filename: UI_PATH });
	return { ...context.__stagePromptUiTestExports, __context: context, __extension: registeredExtensions[0] };
}

test("shouldForceMiniToolbarMode enables mini mode from query flag", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/?qwen_te_mini=1");
	assert.equal(typeof exports.shouldForceMiniToolbarMode, "function");
	assert.equal(exports.shouldForceMiniToolbarMode(), true);
});

test("shouldForceMiniToolbarMode stays off without query flag", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(exports.shouldForceMiniToolbarMode(), false);
});

test("backend requests keep the ComfyUI reverse-proxy prefix", async () => {
	const requested = [];
	const exports = await loadUiExports("https://example.test/comfy/", {
		__testModuleUrl: "https://example.test/comfy/extensions/github-zip-folder/stage_prompt_generator_ui_v2.js",
		fetch: async (url) => {
			requested.push(String(url));
			return { ok: true, status: 200, json: async () => ({ ok: true }) };
		},
	});

	assert.equal(exports.resolveComfyRoute("/qwen_te/prompt_library?refresh=1"), "/comfy/qwen_te/prompt_library?refresh=1");
	assert.equal(exports.resolveComfyRoute("https://api.example/v1"), "https://api.example/v1");
	await exports.fetchJsonWithTimeout("/qwen_te/prompt_library?refresh=1");
	assert.deepEqual(requested, ["/comfy/qwen_te/prompt_library?refresh=1"]);
});

test("embedded and companion browser routes work below a ComfyUI subpath", async () => {
	const requested = [];
	const exports = await loadUiExports("https://example.test/comfy/", {
		__testModuleUrl: "https://example.test/comfy/extensions/renamed-install/stage_prompt_generator_ui_v2.js",
		fetch: async (url) => {
			requested.push(String(url));
			if (String(url).endsWith("/frame")) {
				return {
					ok: true,
					status: 200,
					headers: { get: () => "frame-2" },
					blob: async () => ({ type: "image/jpeg" }),
				};
			}
			return {
				ok: true,
				status: 200,
				json: async () => ({ ok: true, session_id: "session-2", browser: "Edge" }),
			};
		},
	});

	await exports.requestEmbeddedPromptBrowser("start", { url: "https://example.com/" });
	await exports.fetchEmbeddedPromptBrowserFrame("session-2");
	await exports.launchPromptCompanionBrowser("example.com", { currentOrigin: "https://example.test" });
	assert.deepEqual(requested, [
		"/comfy/qwen_te/embedded_browser/start",
		"/comfy/qwen_te/embedded_browser/frame",
		"/comfy/qwen_te/companion_browser/open",
	]);
});

test("registerStagePromptMiniBridge is available without window app globals", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(typeof exports.registerStagePromptMiniBridge, "function");
});

test("renamed stage display name remains recognized alongside the legacy name", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(exports.hasStagePromptDisplayName("真男人提示词阶段生成器"), true);
	assert.equal(exports.hasStagePromptDisplayName("Qwen TE 阶段式提示词生成器"), true);
	assert.equal(exports.hasStagePromptDisplayName("其他节点"), false);
});

test("stage node detection rejects generic single outputs and preserves legacy signatures", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(exports.isStagePromptNode(makeExternalModelLoaderFixture().node), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "JSON结果" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "正向提示词合集" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "OtherNode", outputs: [{ name: "JSON结果" }, { name: "JSON" }, { name: "JSON结果" }] }), false);
	assert.equal(exports.isStagePromptNode({ type: "QwenTE_StagePromptGenerator", outputs: [] }), true);
	assert.equal(exports.isStagePromptNode({ title: "Qwen TE 阶段式提示词生成器", outputs: [] }), true);
	assert.equal(exports.isStagePromptNode({
		type: "LegacyStageNode",
		widgets: [
			{ name: "qwen模型" },
			{ name: "模板风格" },
			{ name: "首条正向提示词" },
		],
	}), true);
	assert.equal(exports.isStagePromptNode({
		type: "LegacyStageNode",
		outputs: [
			{ name: "全文", _qwenTeOriginalName: "结果全文" },
			{ name: "JSON", _qwenTeOriginalName: "JSON结果" },
			{ name: "合集", _qwenTeOriginalName: "正向提示词合集" },
		],
	}), true);
});

test("prompt library retries transient failures and preserves the last valid snapshot", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const firstLibrary = { slot_config: [{ name: "主体", slots: 1 }], tag_library: { 主体: { default: ["成年女性"] } } };
	const secondLibrary = { slot_config: [{ name: "场景背景", slots: 1 }], tag_library: { 场景背景: { default: ["街道"] } } };
	let calls = 0;
	const optionsSeen = [];
	exports.__context.fetch = async (_url, options) => {
		calls += 1;
		optionsSeen.push(options);
		if (calls === 1 || calls === 3) throw new Error("temporary unavailable");
		const payload = calls === 2 ? firstLibrary : secondLibrary;
		return { ok: true, status: 200, json: async () => payload };
	};
	const empty = await exports.getPromptLibrary();
	assert.deepEqual(Array.from(empty.slot_config), []);
	const recovered = await exports.getPromptLibrary();
	assert.equal(recovered.slot_config[0].name, "主体");
	const preserved = await exports.getPromptLibrary(true);
	assert.equal(preserved.slot_config[0].name, "主体");
	const refreshed = await exports.getPromptLibrary();
	assert.equal(refreshed.slot_config[0].name, "场景背景");
	assert.equal(calls, 4);
	assert.equal(optionsSeen.every((options) => options?.cache === "no-cache"), true);
});

test("out-of-order prompt library refreshes cannot overwrite the newest node library", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const pending = [];
	exports.__context.fetch = () => new Promise((resolve) => pending.push(resolve));
	const initialLibrary = { slot_config: [], tag_library: {} };
	const node = { widgets: [], properties: {}, [exports.PANEL_KEY]: { library: initialLibrary } };
	const firstRefresh = exports.refreshLibraryOnNode(node);
	exports.invalidatePromptLibraryCache();
	const secondRefresh = exports.refreshLibraryOnNode(node);
	assert.equal(pending.length, 2);
	const newestLibrary = { slot_config: [{ name: "场景背景", slots: 1 }], tag_library: { 场景背景: ["雨夜街道"] } };
	pending[1]({ ok: true, status: 200, json: async () => newestLibrary });
	await secondRefresh;
	assert.equal(node[exports.PANEL_KEY].library.slot_config[0].name, "场景背景");
	const staleLibrary = { slot_config: [{ name: "主体", slots: 1 }], tag_library: { 主体: ["旧人物"] } };
	pending[0]({ ok: true, status: 200, json: async () => staleLibrary });
	await firstRefresh;
	assert.equal(node[exports.PANEL_KEY].library.slot_config[0].name, "场景背景");
	const cachedLibrary = await exports.getPromptLibrary();
	assert.equal(cachedLibrary.slot_config[0].name, "场景背景");
	assert.equal(pending.length, 2);
});

test("concurrent node library refreshes share one request without aborting either caller", async () => {
	const pending = [];
	let abortCount = 0;
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		AbortController,
		fetch: (_url, options) => new Promise((resolve, reject) => {
			options.signal.addEventListener("abort", () => {
				abortCount += 1;
				reject(new Error("prompt library request aborted"));
			}, { once: true });
			pending.push(resolve);
		}),
	});
	const firstNode = { widgets: [], properties: {} };
	const secondNode = { widgets: [], properties: {} };
	const firstRefresh = exports.refreshLibraryOnNode(firstNode);
	const secondRefresh = exports.refreshLibraryOnNode(secondNode);
	assert.equal(pending.length, 1);
	const latestLibrary = { slot_config: [{ name: "光影氛围", slots: 1 }], tag_library: { 光影氛围: ["饱满色彩"] } };
	pending[0]({ ok: true, status: 200, json: async () => latestLibrary });
	const [firstLibrary, secondLibrary] = await Promise.all([firstRefresh, secondRefresh]);
	assert.equal(abortCount, 0);
	assert.equal(firstLibrary.slot_config[0].name, "光影氛围");
	assert.equal(secondLibrary.slot_config[0].name, "光影氛围");
});

test("fresh library UI actions wait for a slow refresh instead of returning the stale fallback", async () => {
	const scheduledTimers = new Map();
	let nextTimerId = 1;
	let resolveFetch = null;
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setTimeout(callback, delay) {
			const id = nextTimerId++;
			scheduledTimers.set(id, { callback, delay });
			return id;
		},
		clearTimeout(id) {
			scheduledTimers.delete(id);
		},
		fetch: () => new Promise((resolve) => { resolveFetch = resolve; }),
	});
	const staleLibrary = { slot_config: [{ name: "主体", slots: 1 }], tag_library: { 主体: ["旧人物"] } };
	const node = { widgets: [], properties: {} };
	let settled = false;
	const pendingRefresh = exports.getFreshLibraryForUi(node, staleLibrary).then((library) => {
		settled = true;
		return library;
	});
	await Promise.resolve();
	for (const timer of [...scheduledTimers.values()].filter((item) => item.delay <= 400)) timer.callback();
	await Promise.resolve();
	assert.equal(settled, false);
	assert.equal([...scheduledTimers.values()].some((item) => item.delay === 400), false);
	const freshLibrary = { slot_config: [{ name: "场景背景", slots: 1 }], tag_library: { 场景背景: ["新街道"] } };
	resolveFetch({ ok: true, status: 200, json: async () => freshLibrary });
	const resolvedLibrary = await pendingRefresh;
	assert.equal(resolvedLibrary.slot_config[0].name, "场景背景");
});

test("panel actions reuse the validated prompt library snapshot", async () => {
	let calls = 0;
	const library = { slot_config: [{ name: "主体", slots: 1 }], tag_library: { 主体: ["成年女性"] } };
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		fetch: async () => {
			calls += 1;
			return { ok: true, status: 200, json: async () => library };
		},
	});
	await exports.getPromptLibrary();
	const node = { widgets: [], properties: {} };
	const resolved = await exports.getFreshLibraryForUi(node, { slot_config: [], tag_library: {} });
	assert.equal(resolved.slot_config[0].name, "主体");
	assert.equal(calls, 1);
});

test("owned fetches abort the previous request and modal disposal aborts the current request", async () => {
	class TestElement {
		remove() {}
	}
	let callCount = 0;
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		AbortController,
		HTMLElement: TestElement,
		fetch: async (_url, options) => {
			callCount += 1;
			if (callCount === 2) return { ok: true, status: 200 };
			return await new Promise((_resolve, reject) => {
				options.signal.addEventListener("abort", () => reject(new Error("request aborted")), { once: true });
			});
		},
	});
	const overlay = new TestElement();
	const first = exports.fetchWithTimeout("/first", {}, { owner: overlay, key: "search", timeoutMs: 5000 });
	await Promise.resolve();
	const second = exports.fetchWithTimeout("/second", {}, { owner: overlay, key: "search", timeoutMs: 5000 });
	await assert.rejects(first, /aborted/u);
	assert.equal((await second).ok, true);
	const third = exports.fetchWithTimeout("/third", {}, { owner: overlay, key: "audit", timeoutMs: 5000 });
	await Promise.resolve();
	assert.equal(exports.disposeModalOverlay(overlay), true);
	await assert.rejects(third, /aborted/u);
});

test("owned JSON fetch keeps timeout and modal abort active while reading the response body", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal((source.match(/response\.json\(\)/gu) ?? []).length, 1);
	assert.equal((source.match(/fetchJsonWithTimeout\(/gu) ?? []).length >= 6, true);
	class TestElement {
		remove() {}
	}
	let bodyStartedResolve;
	const bodyStarted = new Promise((resolve) => { bodyStartedResolve = resolve; });
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		AbortController,
		HTMLElement: TestElement,
		fetch: async (_url, options) => ({
			ok: true,
			status: 200,
			json: async () => await new Promise((_resolve, reject) => {
				bodyStartedResolve();
				options.signal.addEventListener("abort", () => reject(new Error("body aborted")), { once: true });
			}),
		}),
	});
	const overlay = new TestElement();
	const pending = exports.fetchJsonWithTimeout("/slow-body", {}, { owner: overlay, key: "slow-body", timeoutMs: 5000 });
	await bodyStarted;
	assert.equal(exports.disposeModalOverlay(overlay), true);
	await assert.rejects(pending, /body aborted/u);

	let timeoutBodyStartedResolve;
	const timeoutBodyStarted = new Promise((resolve) => { timeoutBodyStartedResolve = resolve; });
	exports.__context.fetch = async (_url, options) => ({
		ok: true,
		status: 200,
		json: async () => await new Promise((_resolve, reject) => {
			timeoutBodyStartedResolve();
			options.signal.addEventListener("abort", () => reject(new Error("body timeout")), { once: true });
		}),
	});
	const timed = exports.fetchJsonWithTimeout("/timed-body", {}, { owner: {}, key: "timed-body", timeoutMs: 250 });
	await timeoutBodyStarted;
	await assert.rejects(timed, /body timeout/u);

	exports.__context.fetch = async (_url, options) => await new Promise((_resolve, reject) => {
		options.signal.addEventListener("abort", () => {
			const error = new Error("signal is aborted without reason");
			error.name = "AbortError";
			reject(error);
		}, { once: true });
	});
	const rawAbort = exports.fetchWithTimeout("/raw-abort", {}, { owner: {}, key: "raw-abort", timeoutMs: 250 });
	await assert.rejects(rawAbort, (error) => String(error?.name) === "TimeoutError");
});

test("node cache namespace is stable and regenerated for copied nodes", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const first = { id: 1, properties: {} };
	const second = {
		id: 2,
		properties: { qwen_te_workflow_output_v1: { promptText: "copied output" } },
		[exports.PANEL_KEY]: {
			modelApiRuntimeSignature: "copied-panel-signature",
			pendingModelApiConfigSignature: "copied-pending-signature",
			lastExecutionOutputs: ["copied"],
			directStageOutputCache: { promptText: "copied" },
			hydratedExecutionOutputs: ["copied"],
			previewExecutionOutputs: ["copied"],
		},
	};
	exports.__context.__testApp.graph._nodes = [first, second];
	const firstNamespace = exports.ensureNodeCacheNamespace(first);
	assert.match(firstNamespace, /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/u);
	assert.equal(exports.ensureNodeCacheNamespace(first), firstNamespace);
	second.properties[exports.NODE_MODEL_API_RUNTIME_SIGNATURE_KEY] = "copied-runtime-signature";
	second.properties[exports.NODE_CACHE_NAMESPACE_KEY] = firstNamespace;
	const secondNamespace = exports.ensureNodeCacheNamespace(second);
	assert.match(secondNamespace, /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/u);
	assert.notEqual(secondNamespace, firstNamespace);
	assert.equal(exports.NODE_MODEL_API_RUNTIME_SIGNATURE_KEY in second.properties, false);
	assert.equal(exports.NODE_WORKFLOW_OUTPUT_KEY in second.properties, false);
	assert.equal(second[exports.PANEL_KEY].modelApiRuntimeSignature, "");
	assert.equal(second[exports.PANEL_KEY].pendingModelApiConfigSignature, "");
	assert.deepEqual(Array.from(second[exports.PANEL_KEY].lastExecutionOutputs), []);
	assert.equal(second[exports.PANEL_KEY].directStageOutputCache, null);
});

test("serialized node payload always carries its cache namespace", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { id: 3, properties: {}, widgets: [] };
	exports.__context.__testApp.graph._nodes = [node];
	const serialized = exports.normalizeSerializedNodePayload(node, { properties: {} });
	assert.equal(
		serialized.properties[exports.NODE_CACHE_NAMESPACE_KEY],
		node.properties[exports.NODE_CACHE_NAMESPACE_KEY],
	);
});

test("configure uses named widget state before same-length positional values", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		widgets: [
			{ name: "设置乙", value: "current-b", serialize: true },
			{ name: "设置甲", value: "current-a", serialize: true },
		],
	};
	const config = {
		widgets_values: ["legacy-a", "legacy-b"],
		properties: {
			qwen_te_named_widget_state_v1: { 设置甲: "named-a", 设置乙: "named-b" },
		},
	};

	const values = exports.normalizeConfiguredWidgetValues(node, config);

	assert.deepEqual(Array.from(values), ["named-b", "named-a"]);
});

test("serializing a node is read-only and preserves random dedupe state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let callbackCount = 0;
	let serializerCount = 0;
	const cacheWidget = { name: "随机补充避重缓存", value: "档案甲, 档案乙", serialize: true };
	const objectValue = { nested: ["原始值"] };
	const node = {
		id: 4,
		properties: {},
		widgets: [
			{
				name: "运行时随机标签",
				value: false,
				serialize: true,
				callback() {
					callbackCount += 1;
					cacheWidget.value = "";
				},
			},
			cacheWidget,
			{
				name: "对象设置",
				value: objectValue,
				serialize: true,
				serializeValue() {
					serializerCount += 1;
					return "不应调用";
				},
			},
		],
	};
	exports.__context.__testApp.graph._nodes = [node];

	const serialized = exports.normalizeSerializedNodePayload(node, { properties: {} });

	assert.equal(callbackCount, 0);
	assert.equal(serializerCount, 0);
	assert.equal(cacheWidget.value, "档案甲, 档案乙");
	assert.equal(serialized.properties.qwen_te_named_widget_state_v1["随机补充避重缓存"], "档案甲, 档案乙");
	assert.equal(JSON.stringify(serialized.widgets_values), JSON.stringify([false, "档案甲, 档案乙", { nested: ["原始值"] }]));
	assert.notEqual(serialized.widgets_values[2], objectValue);
	assert.notEqual(serialized.properties.qwen_te_named_widget_state_v1["对象设置"], objectValue);
});

test("stage panel keeps one compact quickbar and omits duplicate side deck", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	for (const key of ["tag", "example", "random", "randomRun", "tagBlocks", "presets", "history", "nsfwWorkspace", "toggleRawSlots", "toggleAdvanced", "clearTags"]) {
		assert.equal(source.includes(`registerPanelButton("${key}"`), true, `${key} should stay available in the compact quickbar`);
	}
	assert.equal(source.includes('registerPanelButton("rollback"'), false, "rollback should stay in History restore, not as a duplicate quickbar button");
	assert.equal(source.includes("makeActionGroup("), false);
	assert.equal(source.includes('quickbar.className="qwen-te-panel__quickbar"'), true);
	assert.equal(source.includes('addTopWidget(node, "text", "状态"'), true);
	assert.equal(source.includes('addTopWidget(node, "text", "摘要"'), true);
	assert.equal(source.includes("function addBottomWidget"), false);
	for (const label of ["标签", "随机", "随机跑", "预设", "历史", "槽位", "高级", "清空", "示例"]) {
		assert.equal(source.includes(`addBottomWidget(node, "button", "${label}"`), false, `${label} must not return as a native fallback button`);
	}
	assert.equal(source.includes('"qwen_te_mini_toolbar_dom"'), true);
	assert.equal(source.includes("window.__QWEN_TE_STAGE_MAIN_UI_LOADED__ = true"), true);
	assert.equal(source.includes("window.__QWEN_TE_STAGE_MAIN_UI__ = true"), true);
});

test("legacy native action buttons are removed while top status rows remain", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let miniCleanupCalls = 0;
	exports.__context.__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__ = () => { miniCleanupCalls += 1; return true; };
	const fallbackWidget = (name) => ({ name, serialize: false, __qwenStageFallbackWidget: true });
	const node = {
		title: "阶段式提示词生成器 [UI]",
		widgets: [
			fallbackWidget("状态"),
			fallbackWidget("摘要"),
			...(["标签", "随机", "随机跑", "预设", "历史", "槽位", "高级", "清空", "示例"].map(fallbackWidget)),
			{ name: "模板风格", value: "真实感", serialize: true },
		],
	};

	exports.cleanupFixUiArtifacts(node);

	assert.deepEqual(Array.from(node.widgets, (widget) => widget.name), ["状态", "摘要", "模板风格"]);
	assert.equal(node.title, "阶段式提示词生成器");
	assert.equal(miniCleanupCalls, 1);
});

test("main enhancement cleanup preserves the mini fallback until panel ownership succeeds", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let miniCleanupCalls = 0;
	exports.__context.__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__ = () => { miniCleanupCalls += 1; return true; };
	const miniWidget = { name: "qwen_te_mini_toolbar_dom", serialize: false, __qwenStageMiniWidget: true };
	const node = { widgets: [miniWidget, { name: "模板风格", serialize: true }] };

	exports.cleanupFixUiArtifacts(node, { preserveMiniToolbar: true });

	assert.equal(miniCleanupCalls, 0);
	assert.equal(node.widgets.includes(miniWidget), true);
	exports.cleanupFixUiArtifacts(node);
	assert.equal(miniCleanupCalls, 1);
	assert.equal(node.widgets.includes(miniWidget), false);
});

test("cleanup preserves a user title ending in UI when no legacy title artifact exists", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		title: "人像工作流 [UI]",
		widgets: [{ name: "模板风格", value: "真实感", serialize: true }],
	};

	exports.cleanupFixUiArtifacts(node);

	assert.equal(node.title, "人像工作流 [UI]");
});

test("top status widgets are text-only, idempotent, and repair a partial pair", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const added = [];
	const node = {
		properties: {},
		widgets: [{ name: "模板风格", value: "真实感", serialize: true }],
		addWidget(type, name, value, callback, options) {
			const widget = { type, name, value, callback, options };
			this.widgets.push(widget);
			added.push(widget);
			return widget;
		},
	};
	const library = { slot_config: [], tag_library: {} };
	const summary = { textContent: "当前摘要" };
	node[exports.PANEL_KEY] = { summaryEl: makeElement("div"), lastPanelMessage: "" };

	exports.ensureStagePromptTopStatusWidgets(node, library, summary);
	exports.ensureStagePromptTopStatusWidgets(node, library, summary);

	assert.deepEqual(Array.from(added, (widget) => [widget.type, widget.name]), [["text", "状态"], ["text", "摘要"]]);
	assert.equal(added.every((widget) => widget.serialize === false && widget.__qwenStageFallbackWidget === true), true);
	assert.equal(node.widgets.some((widget) => widget.type === "button"), false);
	assert.deepEqual(Array.from(node.widgets.slice(0, 2), (widget) => widget.name), ["状态", "摘要"]);
	assert.equal(node[exports.PANEL_KEY].statusWidget, node.widgets[0]);
	assert.equal(node[exports.PANEL_KEY].summaryWidget, node.widgets[1]);
	assert.notEqual(String(node.widgets[1].value ?? "").trim(), "");

	node.widgets = node.widgets.filter((widget) => widget.name !== "摘要");
	exports.ensureStagePromptTopStatusWidgets(node, library, summary);
	assert.deepEqual(Array.from(node.widgets.slice(0, 2), (widget) => widget.name), ["状态", "摘要"]);
	assert.equal(added.length, 3);
});

test("top status normalization removes duplicates, fixes order, and preserves a clean widget array", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const fallbackWidget = (name, id) => ({ name, id, serialize: false, __qwenStageFallbackWidget: true });
	const node = {
		properties: {},
		widgets: [
			{ name: "模板风格", value: "真实感", serialize: true },
			fallbackWidget("摘要", "summary-first"),
			fallbackWidget("状态", "status-first"),
			fallbackWidget("摘要", "summary-duplicate"),
			fallbackWidget("状态", "status-duplicate"),
		],
		addWidget() { throw new Error("existing top widgets should be reused"); },
	};
	const library = { slot_config: [], tag_library: {} };
	const summary = { textContent: "" };
	node[exports.PANEL_KEY] = { summaryEl: makeElement("div"), lastPanelMessage: "" };

	exports.cleanupFixUiArtifacts(node);
	exports.ensureStagePromptTopStatusWidgets(node, library, summary);

	assert.deepEqual(Array.from(node.widgets, (widget) => widget.name), ["状态", "摘要", "模板风格"]);
	assert.equal(node.widgets.filter((widget) => widget.name === "状态").length, 1);
	assert.equal(node.widgets.filter((widget) => widget.name === "摘要").length, 1);
	const cleanWidgets = node.widgets;
	exports.cleanupFixUiArtifacts(node);
	assert.equal(node.widgets, cleanWidgets);
});

test("maintenance repairs missing top status rows without rebuilding the panel", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const statusWidget = { name: "状态", type: "text", serialize: false, __qwenStageFallbackWidget: true };
	const node = {
		comfyClass: "QwenTE_StagePromptGenerator",
		properties: {},
		outputs: [],
		widgets: [statusWidget, { name: "模板风格", value: "真实感", serialize: true }],
		addWidget(type, name, value, callback, options) {
			const widget = { type, name, value, callback, options };
			this.widgets.push(widget);
			return widget;
		},
	};
	node[exports.PANEL_KEY] = {
		ready: true,
		library: { slot_config: [], tag_library: {} },
		summaryEl: makeElement("div"),
		lastPanelMessage: "",
	};
	exports.__context.__testApp.graph._nodes = [node];

	exports.enhanceExistingStagePromptNodes();

	assert.deepEqual(Array.from(node.widgets.slice(0, 2), (widget) => widget.name), ["状态", "摘要"]);
	assert.equal(node[exports.PANEL_KEY].statusWidget, node.widgets[0]);
	assert.equal(node[exports.PANEL_KEY].summaryWidget, node.widgets[1]);
});

test("legacy widget cleanup runs onRemove instead of leaving DOM cleanup behind", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let onRemoveCount = 0;
	const legacyWidget = {
		name: "标签",
		serialize: false,
		__qwenStageFallbackWidget: true,
		onRemove() { onRemoveCount += 1; },
	};
	const node = { widgets: [legacyWidget, { name: "模板风格", value: "真实感", serialize: true }] };

	exports.cleanupFixUiArtifacts(node);

	assert.equal(onRemoveCount, 1);
	assert.equal(node.widgets.includes(legacyWidget), false);
});

test("retained terminal header exposes the web browser without restoring the legacy tag shortcut", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('textContent = "联网补词"'), false);
	assert.equal(source.includes("onlineSearchButton.onclick"), false);
	assert.equal(source.includes('displaySearch.textContent="浏览器"'), true);
	assert.equal(source.includes('displaySearch.setAttribute("aria-label","打开网页浏览器")'), true);
	assert.equal(source.includes("openOnlinePromptSearchDialog(node, node?.[PANEL_KEY]?.library ?? library)"), true);
	assert.equal(source.includes("const panelButtons = { onlineSearch: displaySearch };"), true);
});

test("online prompt search query removes low-value terms and deduplicates keywords", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const result = exports.buildOnlineSearchQuery("８Ｋ, cinematic portrait, 无水印, cinematic", 6);
	assert.equal(result.query, "cinematic portrait editorial portrait");
	assert.equal(result.dropped, 2);
	assert.equal(result.normalized, true);
});

test("online prompt search calls only the fixed backend route and filters transport noise", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let captured = null;
	exports.__context.fetch = async (url, options) => {
		captured = { url, payload: JSON.parse(options.body) };
		return {
			ok: true,
			status: 200,
			json: async () => ({
				source: "searxng",
				tag_items: [
					{ tag: "cinematic portrait", confidence: 0.9, group: "风格", section: "电影", count: 3 },
					{ tag: "DuckDuckGo search results", confidence: 0.8 },
				],
				samples: ["cinematic portrait, soft rim lighting"],
			}),
		};
	};

	const result = await exports.searchOnlinePromptTags(" cinematic portrait ", 12);

	assert.equal(captured.url, "/qwen_te/tag_library/online_search");
	assert.deepEqual(captured.payload, { query: "cinematic portrait", limit: 12 });
	assert.deepEqual(Array.from(result.tags), ["cinematic portrait"]);
	assert.equal(result.promptItems.length, 1);
	assert.equal(result.promptItems[0].prompt, "cinematic portrait, soft rim lighting");
	assert.equal(result.source, "searxng");
});

test("online prompt search defensively deduplicates tag and sample variants", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const items = exports.normalizeOnlineSearchTagItems([
		{ tag: "Glitch Art", confidence: 0.51, count: 1, group: "" },
		{ tag: "  glitch   art ", confidence: 0.86, count: 3, group: "风格", exists: true },
		{ tag: "DuckDuckGo search results", confidence: 0.99 },
	]);
	const samples = exports.normalizeOnlineSearchSamples([
		"Cinematic   portrait, rim light",
		"cinematic portrait, rim light",
		"Second sample",
	]);

	assert.equal(items.length, 1);
	assert.equal(items[0].tag, "Glitch Art");
	assert.equal(items[0].confidence, 0.86);
	assert.equal(items[0].count, 3);
	assert.equal(items[0].group, "风格");
	assert.equal(items[0].exists, true);
	assert.deepEqual(Array.from(samples), ["Cinematic portrait, rim light", "Second sample"]);
	const prompts = exports.normalizeOnlinePromptItems([
		{ id: "one", prompt: "Cinematic portrait, rim light", confidence: 0.8, source: "searxng" },
		{ id: "two", prompt: " cinematic   portrait, rim light ", confidence: 0.6, source: "lexica" },
	], [], 8);
	assert.equal(prompts.length, 1);
	assert.equal(prompts[0].tag, "Cinematic portrait, rim light");
	assert.equal(prompts[0].group, "searxng");
});

test("online prompt search renders sanitized diagnostics as readable status", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(
		exports.formatOnlineSearchWarning("civitai:timeout,lexica:http_500,policy:public_sources_disabled"),
		"Civitai：超时；Lexica：HTTP 500；策略：已关闭公开来源回退",
	);
	assert.equal(exports.formatOnlineSearchWarning("extract:token=secret"), "标签提取：请求失败");
});

test("online prompt search import resolution is canonical and reports partial completion", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "风格", slots: 1 }],
		tag_library: { 风格: { default: ["Glitch Art", "电影感"] } },
	};
	const resolution = exports.resolveOnlineSearchLibraryTags(
		[" glitch   art ", "电影感", "film grain", "FILM GRAIN"],
		library,
	);

	assert.deepEqual(Array.from(resolution.resolvedTags), ["glitch   art", "电影感"]);
	assert.deepEqual(Array.from(resolution.unresolvedTags), ["film grain"]);
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("拆分入库未完全完成：已确认"), true);
	assert.equal(source.includes("const resolution = resolveOnlineSearchLibraryTags(tagsToImport, refreshedLibrary);"), true);
});

test("online prompt search batches every selected import tag without truncation", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const tags = Array.from({ length: 30 }, (_, index) => `tag-${index}`);
	const batches = exports.chunkOnlineImportTags([...tags, "tag-0", ""], 12);

	assert.deepEqual(Array.from(batches, (batch) => Array.from(batch).length), [12, 12, 6]);
	assert.deepEqual(Array.from(batches, (batch) => Array.from(batch)).flat(), tags);
});

test("online prompt search actions use only explicitly selected candidates", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const candidates = [
		{ tag: "high-a", confidence: 0.92 },
		{ tag: "low-a", confidence: 0.41 },
		{ tag: "high-b", confidence: 0.81 },
	];

	assert.deepEqual(Array.from(exports.resolveOnlineSearchSelectedTags(candidates, [])), []);
	assert.deepEqual(
		Array.from(exports.resolveOnlineSearchSelectedTags(candidates, ["low-a"], { onlyHighConfidence: true })),
		[],
	);
	assert.deepEqual(
		Array.from(exports.resolveOnlineSearchSelectedTags(candidates, ["low-a", "high-b"], { onlyHighConfidence: true })),
		["high-b"],
	);
});

test("online prompt search browser history supports navigation and drops forward entries", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let state = exports.pushOnlineSearchBrowserHistory([], -1, "alpha", 3);
	state = exports.pushOnlineSearchBrowserHistory(state.items, state.index, "beta", 3);
	state = exports.pushOnlineSearchBrowserHistory(state.items, state.index, "charlie", 3);
	assert.deepEqual(Array.from(state.items), ["alpha", "beta", "charlie"]);

	const back = exports.stepOnlineSearchBrowserHistory(state.items, state.index, -1);
	assert.equal(back.query, "beta");
	state = exports.pushOnlineSearchBrowserHistory(back.items, back.index, "delta", 3);
	assert.deepEqual(Array.from(state.items), ["alpha", "beta", "delta"]);
	assert.equal(state.index, 2);

	state = exports.pushOnlineSearchBrowserHistory(state.items, state.index, "echo", 3);
	assert.deepEqual(Array.from(state.items), ["beta", "delta", "echo"]);
	const forwardAtEnd = exports.stepOnlineSearchBrowserHistory(state.items, state.index, 1);
	assert.equal(forwardAtEnd.query, "echo");
	assert.equal(forwardAtEnd.index, 2);
});

test("prompt browser resolves public websites and search text without accepting dangerous targets", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const options = { currentOrigin: "http://127.0.0.1:8188/" };
	const explicit = exports.resolvePromptBrowserTarget("https://example.com/path?q=1#part", options);
	assert.equal(explicit.ok, true);
	assert.equal(explicit.kind, "url");
	assert.equal(explicit.url, "https://example.com/path?q=1#part");

	const domain = exports.resolvePromptBrowserTarget("example.com/docs", options);
	assert.equal(domain.ok, true);
	assert.equal(domain.url, "https://example.com/docs");

	const search = exports.resolvePromptBrowserTarget("cinematic portrait lighting", options);
	assert.equal(search.ok, true);
	assert.equal(search.kind, "search");
	assert.equal(search.url, "https://www.google.com/search?igu=1&q=cinematic%20portrait%20lighting");

	for (const [target, reason] of [
		["javascript:alert(1)", "blocked_scheme"],
		["data:text/html,hello", "blocked_scheme"],
		["https://user:secret@example.com", "credentials"],
		["https://example.com:0", "invalid_port"],
		["127.1", "private_host"],
		["0x7f000001", "private_host"],
		["https://10.0.0.1", "private_host"],
		["https://169.254.169.254", "private_host"],
		["https://[::1]", "private_host"],
		["https://[::ffff:127.0.0.1]", "private_host"],
		["http://127.0.0.1:8188/queue", "private_host"],
	]) {
		const result = exports.resolvePromptBrowserTarget(target, options);
		assert.equal(result.ok, false, `${target} should be rejected`);
		assert.equal(result.reason, reason, `${target} should report ${reason}`);
	}

	const sameOrigin = exports.resolvePromptBrowserTarget("https://comfy.example.com/view", { currentOrigin: "https://comfy.example.com/" });
	assert.equal(sameOrigin.ok, false);
	assert.equal(sameOrigin.reason, "same_origin");
});

test("prompt browser external open uses noopener and never opens rejected targets", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const calls = [];
	const child = { opener: "parent" };
	const opened = exports.openPromptBrowserExternal("example.com", {
		currentOrigin: "http://127.0.0.1:8188/",
		openWindow(url, target, features) {
			calls.push({ url, target, features });
			return child;
		},
	});
	assert.equal(opened.opened, true);
	assert.deepEqual(calls, [{ url: "https://example.com/", target: "_blank", features: "noopener,noreferrer" }]);
	assert.equal(child.opener, null);

	const rejected = exports.openPromptBrowserExternal("file:///etc/passwd", {
		openWindow() { throw new Error("must not open"); },
	});
	assert.equal(rejected.opened, false);
	assert.equal(rejected.reason, "blocked_scheme");
});

test("prompt browser external open falls back to a secure anchor in browser pages", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let clicked = 0;
	let removed = 0;
	let appended = null;
	const link = {
		style: {},
		click() { clicked += 1; },
		remove() { removed += 1; },
	};
	const result = exports.openPromptBrowserExternal("example.com", {
		document: {
			body: { appendChild(value) { appended = value; } },
			createElement(tagName) {
				assert.equal(tagName, "a");
				return link;
			},
		},
	});

	assert.equal(result.opened, true);
	assert.equal(appended, link);
	assert.equal(link.href, "https://example.com/");
	assert.equal(link.target, "_blank");
	assert.equal(link.rel, "noopener noreferrer");
	assert.equal(link.style.display, "none");
	assert.equal(clicked, 1);
	assert.equal(removed, 1);
});

test("prompt companion browser sends one validated same-origin launch request", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let captured = null;
	const result = await exports.launchPromptCompanionBrowser("example.com", {
		currentOrigin: "http://127.0.0.1:8188/",
		async requestJson(url, init, options) {
			captured = { url, init, options };
			return {
				response: { ok: true, status: 200 },
				data: { ok: true, browser: "Microsoft Edge", message: "opened" },
			};
		},
	});

	assert.equal(result.ok, true);
	assert.equal(result.launched, true);
	assert.equal(result.browser, "Microsoft Edge");
	assert.equal(captured.url, "/qwen_te/companion_browser/open");
	assert.equal(captured.init.method, "POST");
	assert.equal(captured.init.headers["Content-Type"], "application/json");
	assert.equal(captured.init.headers["X-Qwen-TE-Companion-Browser"], "1");
	assert.deepEqual(JSON.parse(captured.init.body), { url: "https://example.com/" });
	assert.equal(captured.options.key, "companion-browser");

	let called = false;
	const rejected = await exports.launchPromptCompanionBrowser("https://127.0.0.1/", {
		async requestJson() { called = true; },
	});
	assert.equal(rejected.launched, false);
	assert.equal(rejected.reason, "private_host");
	assert.equal(called, false);
});

test("embedded prompt browser sends guarded session and frame requests", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let sessionRequest = null;
	const session = await exports.requestEmbeddedPromptBrowser("start", {
		url: "https://example.com/",
		width: 1360,
		height: 760,
	}, {
		owner: { id: "dialog" },
		key: "embedded-start",
		async requestJson(url, init, options) {
			sessionRequest = { url, init, options };
			return {
				response: { ok: true, status: 200 },
				data: { ok: true, session_id: "session-1", browser: "Microsoft Edge" },
			};
		},
	});
	assert.equal(session.session_id, "session-1");
	assert.equal(sessionRequest.url, "/qwen_te/embedded_browser/start");
	assert.equal(sessionRequest.init.method, "POST");
	assert.equal(sessionRequest.init.headers["X-Qwen-TE-Companion-Browser"], "1");
	assert.deepEqual(JSON.parse(sessionRequest.init.body), {
		url: "https://example.com/",
		width: 1360,
		height: 760,
	});
	assert.equal(sessionRequest.options.key, "embedded-start");

	let frameRequest = null;
	const frame = await exports.fetchEmbeddedPromptBrowserFrame("session-1", {
		owner: { id: "dialog" },
		previousFrameId: "previous-frame",
		async request(url, init, options) {
			frameRequest = { url, init, options };
			return {
				ok: true,
				status: 200,
				headers: { get(name) { return name === "X-Qwen-TE-Frame-Id" ? "next-frame" : ""; } },
				async blob() { return { type: "image/jpeg", size: 128 }; },
			};
		},
	});
	assert.equal(frame.changed, true);
	assert.equal(frame.frameId, "next-frame");
	assert.equal(frame.blob.type, "image/jpeg");
	assert.equal(frameRequest.url, "/qwen_te/embedded_browser/frame");
	assert.equal(frameRequest.init.cache, "no-store");
	assert.deepEqual(JSON.parse(frameRequest.init.body), { session_id: "session-1", previous_frame_id: "previous-frame", max_width: 1440, max_height: 810, quality: 76 });
	assert.equal(frameRequest.options.key, "embedded-browser-frame");

	const unchanged = await exports.fetchEmbeddedPromptBrowserFrame("session-1", {
		previousFrameId: "next-frame",
		async request() {
			return {
				ok: true,
				status: 204,
				headers: { get() { return "next-frame"; } },
			};
		},
	});
	assert.equal(unchanged.changed, false);
	assert.equal(unchanged.frameId, "next-frame");
	assert.equal(unchanged.blob, null);

	await assert.rejects(
		exports.requestEmbeddedPromptBrowser("status", { session_id: "missing" }, {
			async requestJson() {
				return { response: { ok: false, status: 404 }, data: { ok: false, message: "session missing" } };
			},
		}),
		/session missing/u,
	);
	await assert.rejects(
		exports.fetchEmbeddedPromptBrowserFrame("session-1", {
			async request() {
				return { ok: true, status: 200, async blob() { return { type: "text/html" }; } };
			},
		}),
		/画面格式无效/u,
	);
});

test("embedded browser frame profile switches from responsive preview to sharp settled frame", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const rect = { width: 1600, height: 900 };
	const fast = exports.getEmbeddedBrowserFrameCaptureProfile(rect, { fast: true, hasFrame: true, pageReady: true, pixelRatio: 2 });
	assert.equal(fast.maxWidth, 1600);
	assert.equal(fast.maxHeight, 900);
	assert.equal(fast.quality, 72);
	assert.equal(fast.profile, "fast");
	assert.equal(fast.pixelRatio, 1);
	const sharp = exports.getEmbeddedBrowserFrameCaptureProfile(rect, { fast: false, hasFrame: true, pageReady: true, pixelRatio: 2 });
	assert.equal(sharp.maxWidth, 2400);
	assert.equal(sharp.maxHeight, 1350);
	assert.equal(sharp.quality, 90);
	assert.equal(sharp.profile, "sharp");
	assert.equal(sharp.pixelRatio, 1.5);
	const loading = exports.getEmbeddedBrowserFrameCaptureProfile(rect, { fast: false, hasFrame: false, pageReady: false, pixelRatio: 2 });
	assert.equal(loading.maxWidth, 1600);
	assert.equal(loading.maxHeight, 900);
	assert.equal(loading.quality, 76);
	assert.equal(loading.profile, "fast");
	const motion = exports.getEmbeddedBrowserFrameCaptureProfile(rect, { mediaActive: true, fast: false, hasFrame: true, pageReady: true, pixelRatio: 2 });
	assert.equal(motion.maxWidth, 1280);
	assert.equal(motion.maxHeight, 720);
	assert.equal(motion.quality, 60);
	assert.equal(motion.profile, "motion");
	assert.equal(motion.pixelRatio, 1);
	assert.equal(exports.getEmbeddedBrowserFramePollDelay({ mediaActive: true }), 64);
	assert.equal(exports.getEmbeddedBrowserFramePollDelay({ hidden: true, mediaActive: true }), 4000);
	assert.equal(exports.getEmbeddedBrowserFramePollDelay({ pageReady: true, hasFrame: true, unchangedFrameCount: 4 }), 1600);
});

test("embedded prompt browser maps object-fit image coordinates to the CDP viewport", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const center = exports.mapEmbeddedBrowserPointerPoint(
		400,
		300,
		{ left: 0, top: 0, width: 800, height: 600 },
		1000,
		500,
		1360,
		760,
	);
	assert.equal(center.x, 680);
	assert.equal(center.y, 380);
	assert.equal(
		exports.mapEmbeddedBrowserPointerPoint(400, 50, { left: 0, top: 0, width: 800, height: 600 }, 1000, 500, 1360, 760),
		null,
	);
});

test("embedded prompt browser matches its viewport to the visible frame", async () => {
    const exports = await loadUiExports("http://127.0.0.1:8188/");
    const viewport = exports.resolveEmbeddedBrowserViewport(
        { width: 1640, height: 636 },
        { minWidth: 640, minHeight: 360, maxWidth: 1600, maxHeight: 900 },
    );
    assert.equal(viewport.width, 1600);
    assert.equal(viewport.height, 620);
    const capture = exports.resolveEmbeddedBrowserViewport(
        { width: 1640, height: 636 },
        { minWidth: 480, minHeight: 270, maxWidth: 960, maxHeight: 540 },
    );
    assert.equal(capture.width, 960);
    assert.equal(capture.height, 372);
});
test("online prompt search keeps prompt tools inside a real dual-mode web browser", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openOnlinePromptSearchDialog");
	const end = source.indexOf("\nfunction openCharacterSheetDialog", start + 1);
	const dialogSource = source.slice(start, end > start ? end : undefined);
	const initialRender = dialogSource.slice(dialogSource.lastIndexOf("document.body.appendChild(overlay)"));
	const externalOpenStart = dialogSource.indexOf("const openCurrentWebExternally =");
	const externalOpenEnd = dialogSource.indexOf("\n\tconst setBrowserMode =", externalOpenStart);
	const externalOpenSource = dialogSource.slice(externalOpenStart, externalOpenEnd);
	const companionOpenStart = dialogSource.indexOf("const openCurrentWebCompanion =");
	const companionOpenEnd = dialogSource.indexOf("\n\tconst setBrowserMode =", companionOpenStart);
	const companionOpenSource = dialogSource.slice(companionOpenStart, companionOpenEnd);

	for (const marker of [
		"qwen-te-online-search__browser",
		"qwen-te-online-search__browser-toolbar",
		"qwen-te-online-search__addressbar",
		"qwen-te-online-search__web-workspace",
		"qwen-te-online-search__web-frame",
		"qwen-te-online-search__companion-button",
		"qwen-te-online-search__filter-rail",
		"qwen-te-online-search__result-route",
		"qwen-te-online-search__selected-preview",
		'let activeBrowserMode = "web";',
		'createBrowserModeTab("web", "网页浏览器"',
		'createBrowserModeTab("tags", "提示词搜索"',
		"const navigateWebHistory = (direction) =>",
		"const openCurrentWebCompanion = async",
		'frameExternalButton.onclick = () => { void openCurrentWebCompanion(currentWebUrl); };',
		'if (activeBrowserMode === "web") navigateWebHistory(-1);',
		'if (activeBrowserMode === "web") navigateWebHistory(1);',
		"reloadButton.onclick = () =>",
	]) assert.equal(dialogSource.includes(marker), true, `${marker} should exist in the search browser`);
	assert.equal(dialogSource.includes("doneButton"), false);
	assert.equal(dialogSource.includes('footer.className = "qwen-te-modal__footer"'), false);
	assert.equal(dialogSource.includes('statusEl.setAttribute("aria-live", "polite")'), true);
	assert.equal(dialogSource.includes('dialog.setAttribute("aria-busy", (tagMode && busyState) || (!tagMode && embeddedNavigationBusy) ? "true" : "false")'), true);
	assert.equal(dialogSource.includes('if (event.key !== "Escape") return;'), true);
	assert.equal(dialogSource.includes('resultPanel.setAttribute("role", "region")'), true);
	assert.equal(dialogSource.includes('samplePanel.setAttribute("role", "region")'), true);
	assert.equal(dialogSource.includes('resultList.setAttribute("role", "group")'), true);
	assert.equal(dialogSource.includes('const webFrame = document.createElement("img");'), true);
	assert.equal(dialogSource.includes('document.createElement("iframe")'), false);
	assert.equal(dialogSource.includes('requestEmbeddedPromptBrowser("start"'), true);
	assert.equal(dialogSource.includes('requestEmbeddedPromptBrowser("navigate"'), true);
	assert.equal(dialogSource.includes('requestEmbeddedPromptBrowser("command"'), true);
	assert.equal(dialogSource.includes('requestEmbeddedPromptBrowser("input"'), true);
	assert.equal(dialogSource.includes("fetchEmbeddedPromptBrowserFrame"), true);
	assert.equal(dialogSource.includes("embeddedBrowserFallbackActive"), true);
	assert.equal(dialogSource.includes("已自动打开独立浏览器"), true);
	assert.equal(dialogSource.includes('frameExternalButton.textContent = "▣ 独立浏览器"'), true);
	assert.equal(dialogSource.includes("PROMPT_BROWSER_EMBEDDED_RETRY_DELAY_MS"), true);
	assert.equal(dialogSource.includes("getEmbeddedPointerPoint"), true);
	assert.equal(dialogSource.includes("webFrame.naturalWidth"), true);
	assert.equal(dialogSource.includes("embeddedLastFrameId"), true);
	assert.equal(dialogSource.includes("getEmbeddedBrowserFramePollDelay"), true);
	assert.equal(dialogSource.includes("isEmbeddedMotionActive"), true);
	assert.equal(dialogSource.includes("embeddedMotionHintUntil = Math.max(embeddedMotionHintUntil, Date.now() + 1500)"), true);
	assert.equal(source.includes("Number(options.unchangedFrameCount) >= 4"), true);
	assert.equal(source.includes("options.mediaActive) return 64"), true);
	assert.equal(dialogSource.includes("document.hidden"), true);
	assert.equal(dialogSource.includes("getEmbeddedFrameCaptureOptions"), true);
	assert.equal(dialogSource.includes("maxWidth: frameCapture.maxWidth"), true);
	assert.equal(dialogSource.includes('if (!message && webFrameOverlay.classList.contains("qwen-te-hidden")) return;'), true);
	assert.equal(dialogSource.includes("if (revokeTimer != null) clearTimeout(revokeTimer);"), true);
	assert.equal(dialogSource.includes("searchInput.value !== reportedUrl"), true);
	assert.equal(source.includes('webFrame.decoding = "async"'), true);
	assert.equal(dialogSource.includes("copySelectedPrompts"), true);
	assert.equal(dialogSource.includes("const startViewport = resolveEmbeddedBrowserViewport"), true);
	assert.equal(dialogSource.includes("queueEmbeddedBrowserWheel"), true);
	assert.equal(dialogSource.includes("queueEmbeddedBrowserPointerMove"), true);
	assert.equal(dialogSource.includes("queueEmbeddedBrowserText"), true);
	assert.equal(dialogSource.includes('requestEmbeddedPromptBrowser("resize"'), true);
	assert.equal(dialogSource.includes("new ResizeObserver"), true);
	assert.equal(dialogSource.includes('document.addEventListener("visibilitychange"'), true);
	assert.equal(dialogSource.includes("scheduleEmbeddedFramePoll(0)"), true);
	assert.equal(dialogSource.includes("markEmbeddedBrowserActivity"), true);
	assert.equal(dialogSource.includes("replace: false"), true);
	assert.equal(dialogSource.includes('webFrame.addEventListener("pointerdown"'), true);
	assert.equal(dialogSource.includes('dialog.addEventListener(eventName, (event) => { event.stopPropagation(); })'), true);
	assert.equal(dialogSource.includes('setWebStatus(`${data.browser || "内嵌浏览器"} 已启动，可直接点击和输入。`)'), true);
	assert.equal(dialogSource.includes('let queryHistory = [];'), true);
	assert.equal(dialogSource.includes('let webHistory = [PROMPT_BROWSER_HOME_ENTRY];'), true);
	assert.equal(dialogSource.includes('let tagAddressBadgeText = "提示词";'), true);
	assert.equal(dialogSource.includes('if (activeBrowserMode === "tags") addressBadge.textContent = tagAddressBadgeText;'), true);
	assert.equal(dialogSource.includes('const historyQuery = String(queryHistory[queryHistoryIndex] ?? "").trim();'), true);
	assert.equal(dialogSource.includes('const compacted = options.queryIsEffective'), true);
	assert.equal(dialogSource.includes('runSearch({ recordHistory: false, queryIsEffective: true })'), true);
	assert.equal(dialogSource.includes('recordHistory: !reusingHistoryQuery, queryIsEffective: reusingHistoryQuery'), true);
	assert.equal(dialogSource.includes('webFrame.removeAttribute("src");'), true);
	assert.equal(dialogSource.includes('webInputSink.addEventListener("beforeinput"'), true);
	assert.equal(dialogSource.includes('webInputSink.addEventListener("compositionend"'), true);
	assert.equal(dialogSource.includes('webFrame.addEventListener("wheel"'), true);
	assert.equal(dialogSource.includes('void closeEmbeddedBrowserSession({ revokeFrame: true });'), true);
	assert.equal(externalOpenSource.includes("pushOnlineSearchBrowserHistory"), false, "external tabs must not enter embedded browsing history");
	assert.equal(externalOpenSource.includes("currentWebUrl = result.url"), false, "external tabs must not replace the embedded current page");
	assert.equal(companionOpenSource.includes("pushOnlineSearchBrowserHistory"), false, "companion windows must not enter embedded browsing history");
	assert.equal(companionOpenSource.includes("currentWebUrl = result.url"), false, "companion windows must not replace the embedded current page");
	assert.equal(initialRender.includes('showWebHome({ recordHistory: false });'), true);
	assert.equal(initialRender.includes('setBrowserMode("web");'), true);
	assert.equal(initialRender.includes("navigateWebsite("), false, "opening the dialog must not automatically visit an external website");
	assert.equal(initialRender.includes("launchPromptCompanionBrowser("), false, "opening the dialog must not automatically launch a native browser");
	assert.equal(source.includes("grid-template-columns:210px minmax(400px,1fr) 320px"), true);
	assert.equal(source.includes("qwen-te-online-search__web-frame-shell"), true);
	assert.equal(source.includes("@media (max-width:1120px)"), true);
	assert.equal(source.includes("@media (max-width:920px)"), true);
	assert.equal(source.includes("@media (max-width:640px)"), true);
	assert.equal(source.includes("@media (max-width:640px) and (max-height:720px)"), true);
});

test("online prompt search close guard prevents a late library refresh from mutating the node", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const initialLibrary = { slot_config: [], tag_library: {} };
	const refreshedLibrary = { slot_config: [{ name: "主体", slots: 1 }], tag_library: { 主体: { default: ["成年女性"] } } };
	const node = { widgets: [], properties: {}, [exports.PANEL_KEY]: { library: initialLibrary } };
	let resolveFetch;
	let dialogOpen = true;
	exports.__context.fetch = () => new Promise((resolve) => { resolveFetch = resolve; });

	const refresh = exports.refreshLibraryOnNode(node, { commitGuard: () => dialogOpen });
	dialogOpen = false;
	resolveFetch({ ok: true, status: 200, json: async () => refreshedLibrary });
	const result = await refresh;

	assert.equal(node[exports.PANEL_KEY].library, initialLibrary);
	assert.equal(result, initialLibrary);
});

test("online prompt search keeps modal mutations blocked during continuous runs", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("if (busyState || rejectDuringContinuousRun()) return;"), true);
	assert.equal(source.includes("for (const batch of chunkOnlineImportTags(tagsToImport, 12))"), true);
	assert.equal(source.includes("candidateItems = candidateItems.map((item) => ({"), true);
	assert.equal(source.includes('document.querySelector?.(\'[data-qwen-modal="online-search"]\')'), true);
});

test("online prompt search locks interactive state and ignores IME commit enter", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("searchInput.disabled = tagMode ? interactionBlocked : embeddedNavigationBusy;"), true);
	assert.equal(source.includes("searchButton.disabled = tagMode ? interactionBlocked : embeddedNavigationBusy || !webTarget.ok;"), true);
	assert.equal(source.includes("embeddedNavigationBusy = true;"), true);
	assert.equal(source.includes("timeoutMs: 60000"), true);
	assert.equal(source.includes("card.disabled = isInteractionBlocked();"), true);
	assert.equal(source.includes('card.setAttribute("aria-pressed", selectedTags.has(tag) ? "true" : "false");'), true);
	assert.equal(source.includes('if (event.isComposing || event.key !== "Enter") return;'), true);
	assert.equal(source.includes("commitGuard: isDialogOperationCurrent"), true);
	assert.equal(source.includes("if (!isDialogOperationCurrent() || !isNodeStateMutationCurrent(node, mutationRevision)) return;"), true);
});

test("stage panel omits decorative hero theme shortcuts and status card", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	for (const text of ["STAGE PROMPT CONSOLE", "阶段式提示词控制台", "主题池捷径", "执行状态"]) {
		assert.equal(source.includes(text), false, `${text} should not render as a panel block`);
	}
	for (const className of ["qwen-te-panel__hero", "qwen-te-panel__meta-card--theme", "qwen-te-panel__signal-grid"]) {
		assert.equal(source.includes(`className=\"${className}`), false, `${className} should not be created`);
	}
});

test("stage panel layout stays single-column and content focused", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("grid-template-columns:minmax(0,1fr);gap:9px"), true);
	assert.equal(source.includes("height:clamp(170px,23vh,210px);min-height:170px;max-height:210px"), true);
	assert.equal(source.includes("qwen-te-panel__actions-shell{display:none}"), true);
	assert.equal(source.includes("qwen-te-panel__quickbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))"), true);
	assert.equal(source.includes("qwen-te-panel__summary-line"), true);
	assert.equal(source.includes("qwen-te-panel__summary-pill"), false);
	assert.equal(source.includes("sideRail"), false);
	assert.equal(source.includes("mainWorkspace.appendChild(summaryCard)"), false);
	assert.equal(source.includes("mainWorkspace.appendChild(controlSurface)"), false);
	assert.equal(source.includes("mainWorkspace.appendChild(displayCard)"), true);
	assert.equal(source.includes("mainWorkspace.appendChild(quickbar)"), true);
	assert.equal(
		source.indexOf("mainWorkspace.appendChild(displayCard)") <
			source.indexOf("mainWorkspace.appendChild(quickbar)"),
		true,
		"stage panel should render preview before bottom quickbar",
	);
});

test("stage panel keeps daily generation settings in hidden native widgets", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("const CONTROL_WIDGET_NAMES = ["), true);
	for (const text of ["生成控制", "输出基调", "随机与修饰", "场景摘要"]) {
		assert.equal(source.includes(text), false, `${text} should not render in the default panel`);
	}
	assert.equal(source.includes("const controlSurface = null"), true);
	assert.equal(source.includes("setWidgetGroupVisibility(node, CONTROL_WIDGET_NAMES, false)"), true);
	assert.equal(source.includes("refreshControlSurface(node)"), true);
});

test("stage model dialog exposes compact controls without taking over external loader nodes", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("TE MODEL DECK"), true);
	for (const family of ["Qwen3.5-VL", "Qwen3-VL", "Gemma4", "Llama", "Mistral", "DeepSeek", "通用GGUF"]) {
		assert.equal(source.includes(`value: "${family}"`), true, `${family} should be available from the model deck`);
	}
	assert.equal(source.includes("function openStageModelDialog(stageNode)"), true);
	assert.equal(source.includes("MODEL_LOADER_NODE_CLASSES"), false);
	assert.equal(source.includes("MODEL_LOADER_WIDGET_NAMES"), false);
	assert.equal(source.includes("enhanceExistingModelLoaderNodes"), false);
	assert.equal(source.includes("enhanceModelLoaderNode"), false);
	assert.equal(source.includes("qwen_te_model_panel"), false);
	assert.equal(source.includes("ensureStageModelLoaderNode"), false);
	assert.equal(source.includes('makeBtn(quickbar,"模型","MDL"'), true);
	assert.equal(source.includes("STAGE_EMBEDDED_MODEL_WIDGET_NAMES"), true);
	assert.equal(source.includes("STAGE_EMBEDDED_API_MODEL_WIDGET_NAMES"), true);
	assert.equal(source.includes("MODEL_SOURCE_BUTTONS"), true);
	assert.equal(source.includes('{ value: "本地模型", label: "本地"'), true);
	assert.equal(source.includes('return source === "本地GGUF" ? "本地模型" : source;'), true);
	assert.equal(source.includes("MODEL_API_PROVIDER_BUTTONS"), true);
	assert.equal(source.includes("内置主模型"), true);
	assert.equal(source.includes("API服务商"), true);
	assert.equal(source.includes("API密钥"), true);
	assert.equal(source.includes("OpenAI兼容"), true);
	assert.equal(source.includes("Claude Anthropic"), true);
	assert.equal(source.includes("Gemini 原生"), true);
	for (const provider of ["Groq", "Together", "Fireworks", "Perplexity", "Gemini OpenAI兼容", "自定义"]) {
		assert.equal(source.includes(`value: "${provider}"`), true, `${provider} API provider should be available`);
	}
	for (const hostHint of ["api.groq.com", "api.together.xyz", "api.fireworks.ai", "api.perplexity.ai", "v1beta/openai"]) {
		assert.equal(source.includes(hostHint), true, `${hostHint} should be inferred in API summary`);
	}
	assert.equal(source.includes('setWidgetValue(node, resolveModelWidgetName(node, "API地址"), String(item.baseUrl ?? ""));'), true);
	assert.equal(source.includes('setWidgetValue(node, resolveModelWidgetName(node, "API模型"), String(item.model ?? ""));'), true);
	assert.equal(source.includes("选择提示词增强方式：Skill、本地模型或 API。本地模型支持外接兼容对象，未连接时使用内置 GGUF；不完整时自动回退 Skill。"), true);
	assert.equal(source.includes("未完整会回退Skill"), true);
	assert.equal(source.includes("若模型名或本地文件缺失，运行时会回退 Skill 并在标签摘要里提示原因。"), true);
	assert.equal(source.includes('createModelLoaderButton(node, "底层"'), false);
	assert.equal(source.includes("createModelLoaderTextInput"), true);
	assert.equal(source.includes("qwen-te-model__api-grid"), true);
	assert.equal(source.includes("qwen-te-model__settings"), true);
	assert.equal(source.includes("qwen-te-model__section-value"), true);
	assert.equal(source.includes('createModelSection("模型来源"'), true);
	assert.equal(source.includes('createModelSection("API 服务商"'), true);
	assert.equal(source.includes('createModelSection("API 参数"'), true);
	assert.equal(source.includes('createModelSection("推理开关"'), true);
	assert.equal(source.includes('createModelSection("上下文长度"'), true);
	assert.equal(source.includes('createModelSection("KV 缓存精度"'), true);
	assert.equal(source.includes("if (panelState.panel) refreshModelLoaderDeck(panelState, node);"), true);
	assert.equal(source.includes("const connectedDecks = (panelState.modalDecks ?? []).filter((deck) => deck?.panel?.isConnected);"), true);
	assert.equal(source.includes("for (const deck of connectedDecks) refreshModelLoaderDeck(deck, node);"), true);
});

test("model API provider switching clears stale address and model values", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: { [exports.NODE_MODEL_API_RUNTIME_SIGNATURE_KEY]: "old-signature" },
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1" },
			{ name: "API模型", value: "gpt-4o-mini" },
			{ name: "API密钥", value: "literal-old-provider-key" },
			{ name: "API额外请求头", value: "Authorization: Bearer stale-header" },
		],
		[exports.PANEL_KEY]: { modelApiRuntimeSignature: "old-signature", modelApiRuntimeInvalidated: false },
	};
	exports.applyModelApiProviderPreset(node, { value: "OpenAI兼容", baseUrl: "", model: "" });
	assert.equal(node.widgets[0].value, "API接口");
	assert.equal(node.widgets[1].value, "OpenAI兼容");
	assert.equal(node.widgets[2].value, "");
	assert.equal(node.widgets[3].value, "");
	assert.equal(node.widgets[4].value, "");
	assert.equal(node.widgets[5].value, "");
	assert.equal(exports.NODE_MODEL_API_RUNTIME_SIGNATURE_KEY in node.properties, false);
	assert.equal(node[exports.PANEL_KEY].modelApiRuntimeInvalidated, true);
});

test("model runtime summary treats cloud env references as awaiting backend verification", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "仅Skill" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "gpt-4o-mini" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], directStageOutputCache: null, workflowOutputMeta: {} },
	};
	assert.match(exports.getModelRuntimeStatusSummary(node).text, /API 未启用/u);
	node.widgets[0].value = "API接口";
	const envPending = exports.getModelRuntimeStatusSummary(node);
	assert.equal(envPending.tone, "warn");
	assert.match(envPending.text, /环境变量 OPENAI_API_KEY 需后端验证/u);
	assert.doesNotMatch(envPending.text, /API 已配置/u);
	node.widgets[3].value = "";
	assert.match(exports.getModelRuntimeStatusSummary(node).text, /未填写 API Key.*标准环境变量/u);
	node.widgets[1].value = "自定义";
	node.widgets[2].value = "https://proxy.example.test/v1";
	const customNoKey = exports.getModelRuntimeStatusSummary(node);
	assert.equal(customNoKey.tone, "ready");
	assert.match(customNoKey.text, /允许无 Key/u);
});

test("model runtime summary only reuses JSON status for the matching API config signature", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1/" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "gpt-4o-mini" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], directStageOutputCache: null, workflowOutputMeta: {} },
	};
	node[exports.PANEL_KEY].lastExecutionOutputs[exports.STAGE_OUTPUT_INDEX.jsonResult] = JSON.stringify({
		model_source: "API接口",
		model_call_status: "调用失败：1 次，已回退 Skill",
		model_call_success_count: 0,
		model_call_failure_count: 1,
		model_fallback_note: "HTTP 401 Unauthorized",
	});
	assert.match(exports.getModelRuntimeStatusSummary(node).text, /旧运行结果没有配置签名/u);
	const currentSignature = exports.buildModelApiConfigSignature(node);
	node[exports.PANEL_KEY].lastExecutionOutputs[exports.STAGE_OUTPUT_INDEX.jsonResult] = JSON.stringify({
		model_source: "API接口",
		model_config_signature: currentSignature,
		model_call_status: "调用失败：1 次，已回退 Skill",
		model_call_success_count: 0,
		model_call_failure_count: 1,
		model_fallback_note: "HTTP 401 Unauthorized",
	});
	const failed = exports.getModelRuntimeStatusSummary(node);
	assert.equal(failed.tone, "error");
	assert.match(failed.text, /401 Unauthorized/u);
	node.widgets[4].value = "gpt-4.1-mini";
	assert.match(exports.getModelRuntimeStatusSummary(node).text, /配置已变更，等待新运行/u);
	node.widgets[4].value = "gpt-4o-mini";
	exports.applyModelApiProviderPreset(node, {
		value: "OpenAI",
		baseUrl: "https://api.openai.com/v1",
		model: "gpt-4o-mini",
	});
	assert.match(exports.getModelRuntimeStatusSummary(node).text, /配置已变更，等待新运行/u);
});

test("model API effective config applies provider defaults when legacy fields are blank", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "" },
			{ name: "API额外请求头", value: "" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], directStageOutputCache: null },
	};
	const config = exports.getModelApiEffectiveConfig(node);
	assert.equal(config.baseUrl, "https://api.openai.com/v1");
	assert.equal(config.model, "gpt-4o-mini");
	assert.match(exports.getModelLoaderSummary(node), /gpt-4o-mini/u);
	assert.doesNotMatch(exports.getModelLoaderSummary(node), /未完整会回退Skill/u);
	assert.match(exports.buildModelApiConfigSignature(node), /^model-api-v1:[0-9a-f]{16}$/u);
});

test("model API config signatures track key and header revisions without exposing plaintext", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const makeNode = (apiKey, model = "deepseek-v4-flash", extraHeaders = "") => ({
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "DeepSeek" },
			{ name: "API地址", value: "https://api.deepseek.com/" },
			{ name: "API密钥", value: apiKey },
			{ name: "API模型", value: model },
			{ name: "API额外请求头", value: extraHeaders },
		],
	});
	const first = exports.buildModelApiConfigSignature(makeNode("secret-alpha"));
	const same = exports.buildModelApiConfigSignature(makeNode("secret-alpha"));
	const changedKey = exports.buildModelApiConfigSignature(makeNode("secret-beta"));
	const changedModel = exports.buildModelApiConfigSignature(makeNode("secret-alpha", "deepseek-reasoner"));
	const changedHeaders = exports.buildModelApiConfigSignature(makeNode("secret-alpha", "deepseek-v4-flash", "X-Title: revised"));
	const sharedVector = exports.buildModelApiConfigSignatureFromValues(
		"OpenAI",
		"https://api.openai.com/v1",
		"gpt-4o-mini",
		"env:OPENAI_API_KEY",
		"X-Title: Demo",
	);
	assert.equal(sharedVector, "model-api-v1:53518f0821f655b6");
	assert.equal(first, same);
	assert.notEqual(first, changedKey);
	assert.notEqual(first, changedModel);
	assert.notEqual(first, changedHeaders);
	assert.match(first, /^model-api-v1:[0-9a-f]{16}$/u);
	for (const signature of [first, changedKey, changedHeaders]) {
		assert.doesNotMatch(signature, /secret-alpha|secret-beta|revised/u);
	}
});

test("model API validation rejects credential URLs query fragments and noncanonical paths", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "自定义" },
			{ name: "API地址", value: "https://user:pass@proxy.example.test/v1" },
			{ name: "API密钥", value: "" },
			{ name: "API模型", value: "demo-model" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], directStageOutputCache: null },
	};
	assert.match(exports.getModelApiConfigValidationError(node), /用户名或密码/u);
	assert.equal(exports.getModelRuntimeStatusSummary(node).tone, "error");
	node.widgets[2].value = "https://proxy.example.test/v1?api_key=secret";
	assert.match(exports.getModelApiConfigValidationError(node), /查询参数/u);
	node.widgets[2].value = "https://proxy.example.test/a/../v1";
	assert.match(exports.getModelApiConfigValidationError(node), /路径必须规范/u);
	node.widgets[2].value = "https://proxy.example.test/a/%2e%2e/v1";
	assert.match(exports.getModelApiConfigValidationError(node), /转义点段/u);
	node.widgets[2].value = "https://proxy.example.test/a/%5c/v1";
	assert.match(exports.getModelApiConfigValidationError(node), /转义点段/u);
	node.widgets[2].value = "https://proxy.example.test/模型/v1";
	assert.match(exports.getModelApiConfigValidationError(node), /ASCII/u);
	node.widgets[2].value = "https://user:pass@proxy.example.test/v1";
	node.widgets[4].value = "";
	const invalidWithoutModel = exports.getModelRuntimeStatusSummary(node);
	assert.equal(invalidWithoutModel.tone, "error");
	assert.match(invalidWithoutModel.text, /用户名或密码/u);
});

test("model runtime summary renders configuration failures as errors even without call counts", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "gpt-4o-mini" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], directStageOutputCache: null },
	};
	const signature = exports.buildModelApiConfigSignature(node);
	node[exports.PANEL_KEY].lastExecutionOutputs[exports.STAGE_OUTPUT_INDEX.jsonResult] = JSON.stringify({
		model_source: "API接口",
		model_config_signature: signature,
		model_call_status: "配置或加载失败，已回退 Skill",
		model_call_success_count: 0,
		model_call_failure_count: 0,
		model_active_fallback_count: 1,
		model_fallback_note: "未找到 API Key",
	});
	const status = exports.getModelRuntimeStatusSummary(node);
	assert.equal(status.tone, "error");
	assert.match(status.text, /未找到 API Key/u);
});

test("model runtime summary ignores history preview JSON", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "gpt-4o-mini" },
		],
		[exports.PANEL_KEY]: { lastExecutionOutputs: [], previewExecutionOutputs: [], displayPreviewSource: "历史记录" },
	};
	node[exports.PANEL_KEY].previewExecutionOutputs[exports.STAGE_OUTPUT_INDEX.jsonResult] = JSON.stringify({
		model_source: "API接口",
		model_config_signature: exports.buildModelApiConfigSignature(node),
		model_call_status: "调用失败：1 次",
		model_call_failure_count: 1,
		model_fallback_note: "HTTP 401 preview only",
	});
	const status = exports.getModelRuntimeStatusSummary(node);
	assert.doesNotMatch(status.text, /401 preview only|最近运行/u);
	assert.match(status.text, /环境变量 OPENAI_API_KEY 需后端验证/u);
});

test("model runtime signatures reject stale in-flight results after invalidation", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "API接口" },
			{ name: "API服务商", value: "OpenAI" },
			{ name: "API地址", value: "https://api.openai.com/v1" },
			{ name: "API密钥", value: "env:OPENAI_API_KEY" },
			{ name: "API模型", value: "gpt-4o-mini" },
		],
		[exports.PANEL_KEY]: { modelApiRuntimeInvalidated: true, pendingModelApiConfigSignature: "" },
	};
	const signature = exports.buildModelApiConfigSignature(node);
	const slots = [];
	slots[exports.STAGE_OUTPUT_INDEX.jsonResult] = JSON.stringify({
		model_source: "API接口",
		model_config_signature: signature,
		model_call_status: "调用成功：1 次，采纳 1 次",
	});
	assert.equal(exports.rememberModelApiRuntimeSignature(node, slots), false);
	node[exports.PANEL_KEY].pendingModelApiConfigSignature = signature;
	assert.equal(exports.rememberModelApiRuntimeSignature(node, slots), true);
	node[exports.PANEL_KEY].pendingModelApiConfigSignature = signature;
	exports.invalidateModelApiRuntimeStatus(node);
	assert.equal(node[exports.PANEL_KEY].pendingModelApiConfigSignature, "");
});

test("beforeRegisterNodeDef leaves external model loader prototypes untouched", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	for (const nodeData of [
		{
			name: "QwenTE_ModelLoader",
			display_name: "Qwen TE 模型加载器",
			python_module: "custom_nodes.comfyUI-llama-TE-main",
		},
		{
			name: "Gemma4TE_ModelLoader",
			display_name: "Gemma4 TE 模型加载器",
			python_module: "custom_nodes.comfyUI-llama-TE-main",
		},
		{
			name: "Foreign_ModelLoader",
			display_name: "其他模型加载器",
			python_module: "custom_nodes.foreign-model-plugin",
		},
	]) {
		function ExternalLoader() {}
		const created = function () { return "external"; };
		const removed = function () { return "removed"; };
		ExternalLoader.prototype.onNodeCreated = created;
		ExternalLoader.prototype.onRemoved = removed;
		const prototypeKeys = Reflect.ownKeys(ExternalLoader.prototype);

		await exports.__extension.beforeRegisterNodeDef(ExternalLoader, nodeData);

		assert.equal(ExternalLoader.prototype.onNodeCreated, created);
		assert.equal(ExternalLoader.prototype.onRemoved, removed);
		assert.deepEqual(Reflect.ownKeys(ExternalLoader.prototype), prototypeKeys);
	}
});

test("setup and graph hooks leave existing external Qwen loader UI unchanged", async () => {
	const queuedTimeouts = [];
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setTimeout(callback) {
			queuedTimeouts.push(callback);
			return queuedTimeouts.length;
		},
		setInterval() {
			return { unref() {} };
		},
		clearInterval() {},
	});
	const fixtures = [
		makeExternalModelLoaderFixture(),
		makeExternalModelLoaderFixture({
			comfyClass: "Gemma4TE_ModelLoader",
			type: "Gemma4TE_ModelLoader",
			title: "Gemma4 TE 模型加载器",
		}),
	];
	exports.__context.__testApp.graph._nodes = fixtures.map((fixture) => fixture.node);
	assert.equal(exports.__context.__QWEN_TE_STAGE_COLLECT_NODE_STATE__(fixtures[0].node, { slot_config: [] }), null);
	assert.equal(exports.__context.__QWEN_TE_STAGE_RECORD_HISTORY__(fixtures[0].node, {}, "test"), false);
	assert.equal(exports.__context.__QWEN_TE_STAGE_GET_PROMPT_OUTPUT__(fixtures[0].node), "");

	await exports.__extension.setup();
	while (queuedTimeouts.length) queuedTimeouts.shift()?.();
	for (const fixture of fixtures) fixture.assertUntouched();

	for (const fixture of fixtures) exports.__context.__testApp.graph.onNodeAdded?.(fixture.node);
	while (queuedTimeouts.length) queuedTimeouts.shift()?.();
	for (const fixture of fixtures) fixture.assertUntouched();
});

test("nodeCreated leaves newly added external Qwen loader UI unchanged", async () => {
	const queuedTimeouts = [];
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setTimeout(callback) {
			queuedTimeouts.push(callback);
			return queuedTimeouts.length;
		},
	});
	const fixtures = [
		makeExternalModelLoaderFixture(),
		makeExternalModelLoaderFixture({
			comfyClass: "Gemma4TE_ModelLoader",
			type: "Gemma4TE_ModelLoader",
			title: "Gemma4 TE 模型加载器",
		}),
	];

	for (const fixture of fixtures) await exports.__extension.nodeCreated(fixture.node);
	while (queuedTimeouts.length) queuedTimeouts.shift()?.();

	for (const fixture of fixtures) fixture.assertUntouched();
});

test("stage panel quickbar uses short text labels without noisy glyph icons", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("TE MINI CONSOLE"), false);
	for (const badge of ['"TAG"', '"EX"', '"RD"', '"RUN"', '"AI"', '"BLK"', '"MDL"', '"CS"', '"PRE"', '"HIS"', '"NS"', '"SL"', '"ADV"', '"CLR"']) {
		assert.equal(source.includes(badge), true, `${badge} badge should be present`);
	}
	assert.equal(source.includes('"BK"'), false, "rollback badge should not return to the primary quickbar");
	for (const noisyIcon of ['"⌘"', '"✦"', '"↺"', '"▷"', '"◈"', '"🕘"', '"◌"', '"↶"', '"▤"', '"⚙"', '"⌫"']) {
		assert.equal(source.includes(noisyIcon), false, `${noisyIcon} should not be used as an action icon`);
	}
	assert.equal(source.includes("qwen-te-panel__quickbar .qwen-te-panel__button-icon{display:none}"), true);
	assert.equal(source.includes("qwen-te-panel__button--primary"), true);
	assert.equal(source.includes('makeBtn(quickbar,"标签","TAG"'), true);
	assert.equal(source.includes('makeBtn(quickbar,"随机跑","RUN"'), true);
	assert.equal(source.includes('makeBtn(quickbar,"编排","BLK"'), true);
	assert.equal(source.includes('makeBtn(quickbar,"设定图","CS"'), true);
	assert.equal(source.includes('addBottomWidget(node, "button", "匹配"'), false);
	assert.equal(source.includes('addBottomWidget(node, "button", "模型"'), false);
	assert.equal(
		source.indexOf('makeBtn(quickbar,"标签","TAG"') < source.indexOf('makeBtn(quickbar,"随机跑","RUN"') &&
			source.indexOf('makeBtn(quickbar,"随机跑","RUN"') < source.indexOf('makeBtn(quickbar,"编排","BLK"') &&
			source.indexOf('makeBtn(quickbar,"编排","BLK"') < source.indexOf('makeBtn(quickbar,"模型","MDL"') &&
			source.indexOf('makeBtn(quickbar,"模型","MDL"') < source.indexOf('makeBtn(quickbar,"随机","RD"'),
		true,
		"primary tag random-run and model actions should lead the quickbar",
	);
});

test("character sheet button writes a focused multi-view prompt state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "自动" },
			{ name: "案例输出结构", value: "自动" },
			{ name: "提示词语言", value: "纯中文" },
			{ name: "详细度", value: "标准" },
			{ name: "输出模式", value: "完整结果" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "图片反推生成", value: false },
			{ name: "图片反推模式", value: "仅反推描述" },
			{ name: "图片反推最大边长", value: 640 },
			{ name: "额外要求", value: "" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const state = exports.buildCharacterSheetState(node, library, { mode: "reference", userText: "机甲角色，红黑配色，城市背景" });
	assert.equal(state.settings["模板风格"], "真实感");
	assert.equal(state.settings["主体类型"], "人物角色");
	assert.equal(state.settings["优先柔和肤质"], true);
	assert.equal(state.settings["抑制文字伪影"], true);
	assert.equal(state.settings["图片反推生成"], true);
	assert.equal(state.settings["图片反推模式"], "角色设定图");
	assert.equal(state.settings["图片反推最大边长"], 960);
	assert.match(state.settings["额外要求"], /接入单人参考图/u);
	assert.match(state.settings["额外要求"], /机甲角色/u);
	assert.match(state.settings["额外要求"], /风格、服装和色彩跟随参考图与用户补充/u);
	assert.match(state.settings["额外要求"], /正面全身、90度标准侧面全身、背面全身/u);
	assert.match(state.settings["额外要求"], /三栏等宽且比例为1:1:1/u);
	assert.match(state.settings["额外要求"], /相同人物高度、同一头顶线和脚底基线、统一镜头高度与正交投影/u);
	assert.equal(state.settings["额外要求"].includes("粉色汉服"), false);
	assert.equal(state.settings["额外要求"].includes("白底棚拍"), false);
	for (const tag of [
		"角色设定图", "角色三视图", "正面视图", "侧面视图", "背面视图", "正面全身", "标准侧面全身", "背面全身",
		"横向三栏等宽布局", "视图比例1:1:1", "相同人物高度", "同一头顶线", "同一地面基线", "正交投影视角",
		"统一镜头高度", "中性自然站姿", "全身完整入镜", "参考图一致性",
	]) {
		assert.equal(state.customTags.includes(tag), true, `${tag} should be added`);
	}
	assert.equal(state.customTags.includes("头像特写"), false, "headshot should be opt-in instead of shrinking the three primary views");
	for (const tag of ["古风", "汉服", "粉色汉服", "白底棚拍"]) {
		assert.equal(state.customTags.includes(tag), false, `${tag} should not be locked by default`);
	}
});

test("character sheet prompt mode enables sheet strategy without forcing language", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "提示词语言", value: "纯英文" },
			{ name: "主体类型", value: "自动" },
			{ name: "案例输出结构", value: "自动" },
			{ name: "图片反推生成", value: false },
			{ name: "图片反推模式", value: "仅反推描述" },
			{ name: "图片反推最大边长", value: 640 },
			{ name: "额外要求", value: "银发角色，黑色礼服，雾夜街道" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const state = exports.buildCharacterSheetState(node, library, { mode: "prompt", userText: "保留暗色调" });
	assert.equal(state.settings["图片反推生成"], true);
	assert.equal(state.settings["图片反推模式"], "角色设定图");
	assert.equal(state.settings["提示词语言"], "纯英文");
	assert.match(state.settings["额外要求"], /根据当前文字生成同一成年角色的标准三视图/u);
	assert.match(state.settings["额外要求"], /正面全身、90度标准侧面全身、背面全身/u);
	assert.match(state.settings["额外要求"], /相同人物高度/u);
	assert.equal(state.customTags.includes("纯提示词角色设计"), true);
	assert.equal(state.customTags.includes("参考图一致性"), false);
});

test("switching character sheet mode removes the previous automatic mode state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "图片反推生成", value: false },
			{ name: "图片反推模式", value: "仅反推描述" },
			{ name: "图片反推最大边长", value: 640 },
			{ name: "额外要求", value: "" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const referenceState = exports.buildCharacterSheetState(node, library, { mode: "reference", userText: "银发黑衣" });
	exports.applyNodeState(node, library, referenceState);
	const promptState = exports.buildCharacterSheetState(node, library, { mode: "prompt", userText: "保留红色围巾" });
	assert.equal(promptState.customTags.includes("参考图一致性"), false);
	assert.equal(promptState.customTags.includes("纯提示词角色设计"), true);
	assert.equal(promptState.settings["额外要求"].includes("接入单人参考图作为角色来源"), false);
	assert.equal((promptState.settings["额外要求"].match(/角色设定图模式：/gu) ?? []).length, 1);
});

test("character sheet dialog uses enable and disable actions", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openCharacterSheetDialog");
	const end = source.indexOf("function openQualityAuditDialog", start);
	const dialogSource = source.slice(start, end);
	assert.equal(dialogSource.includes('applyButton.textContent = "启用"'), true);
	assert.equal(dialogSource.includes('disableButton.textContent = "停用"'), true);
	assert.equal(dialogSource.includes("buildCharacterSheetDisabledState"), true);
	assert.equal(dialogSource.includes("refreshNodeActionButtons(node);"), true);
	assert.equal(dialogSource.includes('applyRunButton.textContent = "应用并运行"'), false);
	assert.equal(dialogSource.includes('applyButton.textContent = "应用到节点"'), false);
});

test("character sheet quickbar button syncs active color from enabled widget", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("function syncCharacterSheetButton(node)"), true);
	assert.equal(source.includes('panelButtons?.characterSheet'), true);
	assert.equal(source.includes('labelEl.textContent = enabled ? "设定图开" : "设定图"'), true);
	assert.equal(source.includes('button.classList.toggle("is-active", enabled)'), true);
	assert.equal(source.includes("syncCharacterSheetButton(node);"), true);
});

test("character sheet disable state removes only character sheet automation", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 2 }],
		tag_library: { 主体: { default: ["角色设定图", "用户主体"] } },
	};
	const node = {
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "角色设定图" },
			{ name: "主体标签2", value: "用户主体" },
			{ name: "图片反推生成", value: true },
			{ name: "图片反推模式", value: "角色设定图" },
			{ name: "额外要求", value: `用户保留描述\n${"角色设定图模式：根据当前文字生成角色设定展示，可包含头像特写、正面全身、侧面全身、背面全身等视角；角色身份、服装、风格、配色、背景和材质完全跟随用户输入与当前节点标签，不要额外锁定白底、古风、汉服、粉色或固定题材；重点表现服装结构、发型轮廓、材质层次和角色一致性，不要文字标注。"}` },
			{ name: "自定义补充标签", value: "头像特写, 用户自定义, 参考图一致性" },
		],
	};
	const state = exports.buildCharacterSheetDisabledState(node, library);
	assert.equal(state.settings["图片反推生成"], false);
	assert.equal(state.settings["图片反推模式"], "仅反推描述");
	assert.equal(state.settings["额外要求"], "用户保留描述");
	assert.equal(JSON.stringify(state.selected["主体"]), JSON.stringify(["用户主体"]));
	assert.equal(state.customTags.includes("头像特写"), false);
	assert.equal(state.customTags.includes("参考图一致性"), false);
	assert.equal(state.customTags.includes("用户自定义"), true);
});

test("character sheet preserves preexisting common tags and restores untouched settings", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "技术画质", slots: 1 }],
		tag_library: { 技术画质: { default: ["高细节"] } },
	};
	const node = {
		properties: {},
		widgets: [
			{ name: "技术画质标签1", value: "高细节" },
			{ name: "主体类型", value: "自动" },
			{ name: "案例输出结构", value: "自动" },
			{ name: "详细度", value: "标准" },
			{ name: "输出模式", value: "完整结果" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "图片反推生成", value: false },
			{ name: "图片反推模式", value: "仅反推描述" },
			{ name: "图片反推最大边长", value: 640 },
			{ name: "额外要求", value: "用户原始要求" },
			{ name: "自定义补充标签", value: "全身, 用户自定义" },
		],
	};
	const enabledState = exports.buildCharacterSheetState(node, library, { mode: "reference", userText: "银发黑衣" });
	exports.applyNodeState(node, library, enabledState);
	node.widgets.find((widget) => widget.name === "详细度").value = "简洁";
	const disabledState = exports.buildCharacterSheetDisabledState(node, library);
	assert.deepEqual(Array.from(disabledState.selected["技术画质"]), ["高细节"]);
	assert.equal(disabledState.customTags.includes("全身"), true);
	assert.equal(disabledState.customTags.includes("用户自定义"), true);
	assert.equal(disabledState.customTags.includes("角色设定图"), false);
	assert.equal(disabledState.settings["主体类型"], "自动");
	assert.equal(disabledState.settings["案例输出结构"], "自动");
	assert.equal(disabledState.settings["详细度"], "简洁");
	assert.equal(disabledState.settings["优先柔和肤质"], false);
	assert.equal(disabledState.settings["抑制文字伪影"], false);
	assert.equal(disabledState.settings["图片反推生成"], false);
	assert.equal(disabledState.settings["图片反推模式"], "仅反推描述");
	assert.equal(disabledState.settings["图片反推最大边长"], 640);
	assert.equal(Object.prototype.hasOwnProperty.call(disabledState, "characterSheetRestore"), false);
});

test("runtime random preview preserves UI provenance metadata", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		id: 31,
		properties: {
			qwen_te_character_sheet_restore_v1: {
				settings: { original: { "主体类型": "自动" }, applied: { "主体类型": "人物角色" } },
				addedTags: ["角色设定图"],
			},
			qwen_te_smart_text_auto_extra_v1: "自动描述",
		},
		widgets: [
			{ name: "自定义补充标签", value: "角色设定图" },
			{ name: "运行时随机标签", value: true },
			{ name: "运行时随机模式", value: "全随机" },
			{ name: "运行时随机强度", value: "中" },
			{ name: "核心标签锁定数量", value: 0 },
			{ name: "锁定标签白名单", value: "" },
			{ name: "随机排除标签", value: "" },
			{ name: "seed", value: 1 },
		],
	};
	const state = exports.buildRandomStateLocal(node, { slot_config: [], tag_library: {} });
	assert.deepEqual(Array.from(state.characterSheetRestore.addedTags), ["角色设定图"]);
	assert.equal(state.characterSheetRestore.settings.original["主体类型"], "自动");
	assert.equal(state.smartTextAutoExtra, "自动描述");
});

test("built-in example base state preserves active UI provenance", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: { default: ["成年女性"] } },
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				generation_profile_restore: {
					original: { "主体类型": "自动" },
					applied: { "主体类型": "人物角色" },
				},
			},
			qwen_te_character_sheet_restore_v1: {
				settings: { original: { "详细度": "标准" }, applied: { "详细度": "详细" } },
				addedTags: ["角色设定图"],
			},
			qwen_te_smart_text_auto_extra_v1: "自动描述",
		},
		widgets: [
			{ name: "主体标签1", value: "成年女性" },
			{ name: "主体类型", value: "人物角色" },
			{ name: "详细度", value: "详细" },
			{ name: "额外要求", value: "自动描述" },
			{ name: "自定义补充标签", value: "角色设定图" },
		],
	};
	const state = exports.createPresetBaseState(node, library, { mergeWithCurrent: false });
	assert.deepEqual(Array.from(state.selected["主体"]), []);
	assert.deepEqual(Array.from(state.customTags), []);
	assert.equal(state.nsfwWorkspace.generation_profile_restore.original["主体类型"], "自动");
	assert.deepEqual(Array.from(state.characterSheetRestore.addedTags), ["角色设定图"]);
	assert.equal(state.smartTextAutoExtra, "自动描述");
});

test("smart text mode uses inline input instead of browser prompt or fallback buttons", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("qwen-te-panel__smart-input"), true);
	assert.equal(source.includes("匹配启用"), true);
	assert.equal(source.includes("NSFW 开启时会自动切到成人向成熟策略"), true);
	assert.equal(source.includes("输入后点匹配启用，或 Ctrl+Enter 快速匹配；节点会自动匹配标签并调用模型生成连贯文本。"), true);
	assert.equal(source.includes("这里会显示模型生成的连贯提示词预览。"), true);
	assert.equal(source.includes("modeKey === \"smart\""), true);
	assert.equal(source.includes("镜头近距离"), true);
	assert.equal(source.includes("成年女性|年轻成年女性|人物主体|杂志感人像|近景"), true);
	assert.equal(source.includes("window.prompt"), false);
	assert.equal(source.includes("renderInlineSmartTextDisplay"), true);
	assert.equal(source.includes("stopCanvasTextInputEvent"), true);
	for (const eventName of ["keydown", "compositionstart", "compositionend", "wheel"]) {
		assert.equal(source.includes(`"${eventName}"`), true, `smart text input should isolate ${eventName} from the canvas`);
	}
});

test("stage panel height measurement stays stable under canvas zoom and wheel", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("function getUnscaledElementHeight"), true);
	assert.equal(source.includes("Number(element.offsetHeight ?? 0)"), true);
	assert.equal(source.includes("Number(element.scrollHeight ?? 0)"), true);
	assert.equal(source.includes("total += getUnscaledElementHeight(child)"), true);
	assert.equal(source.includes("resize:none;box-sizing:border-box"), true);
});

test("history manager keeps only practical history filters visible", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openHistoryManager");
	const end = source.indexOf("function openExampleDialog", start);
	const historyManager = source.slice(start, end);
	for (const label of ["连续测试报告", "单预设报告", "历史聚合报告", "单预设快照", "预设载入", "示例模板", "手动应用", "历史载入"]) {
		assert.equal(historyManager.includes(`label: "${label}"`), false, `${label} should not be a visible history filter`);
	}
	for (const key of ["continuous-report", "single-preset-report", "history-aggregate-report", "single-preset"]) {
		assert.equal(historyManager.includes(`"${key}"`), true, `${key} should still be hidden from daily history`);
	}
	for (const text of ["riskBar", "全部风险", "历史报告聚合", "aggregateList", "success_rate_desc", "success_rate_asc", "preset_name_asc"]) {
		assert.equal(historyManager.includes(text), false, `${text} should be removed from the simplified history manager`);
	}
	for (const label of ["全部", "随机结果", "运行结果", "整理预览"]) {
		assert.equal(historyManager.includes(`label: "${label}"`), true, `${label} should stay visible`);
	}
	assert.equal(historyManager.includes('clearAllButton.textContent="一键删除历史"'), true);
	assert.equal(historyManager.includes("qwen-te-modal__footer-button--danger"), true);
	assert.equal(historyManager.includes("包括置顶项"), true);
	assert.equal(historyManager.includes("此操作不可撤销"), true);
	assert.equal(historyManager.includes("已导出当前节点历史"), true);
	assert.equal(historyManager.includes("随机历史"), false);
});

test("stage output indexes and display modes match the backend output contract", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.deepEqual(Object.fromEntries(Object.entries(exports.STAGE_OUTPUT_INDEX)), {
		fullText: 0,
		promptText: 1,
		selectedTags: 2,
		jsonResult: 3,
		negativePrompt: 4,
		promptCollection: 5,
		smartText: 6,
		videoPrompt: 7,
	});
	assert.deepEqual(Array.from(exports.STAGE_DISPLAY_MODES, (item) => item.key), ["prompt", "negative", "tags", "blocks", "json", "smart", "video"]);
});

test("stage canvas output labels stay compact while output slots remain compatible", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		outputs: [
			{ name: "结果全文" },
			{ name: "首条正向提示词" },
			{ name: "已选标签" },
			{ name: "JSON结果" },
			{ name: "推荐负面词" },
			{ name: "正向提示词合集" },
			{ name: "智能文本" },
			{ name: "视频提示词" },
		],
	};
	assert.equal(exports.compactStagePromptOutputs(node), true);
	assert.deepEqual(node.outputs.map((output) => output.name), ["全文", "正向", "标签", "JSON", "负面", "合集", "智能", "视频"]);
	assert.equal(node.outputs[1]._qwenTeOriginalName, "首条正向提示词");
	assert.equal(node.outputs[5]._qwenTeOriginalName, "正向提示词合集");
});

test("legacy widget values insert embedded model controls before stage settings", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const widgetNames = [
		"模型来源",
		"内置模型系列", "内置主模型", "内置视觉投影mmproj", "内置启用思考", "内置上下文长度", "内置GPU层数", "内置KV缓存K类型", "内置KV缓存V类型",
		"API服务商", "API地址", "API密钥", "API模型", "API超时秒", "API额外请求头",
		"模板风格", "主体类型", "案例输出结构", "运行时随机标签", "运行时随机模式", "核心标签锁定数量", "运行时随机强度", "随机主题池", "提示词语言",
	];
	const node = { properties: {}, widgets: widgetNames.map((name) => ({ name, value: name.includes("内置") || name.startsWith("API") || name === "模型来源" ? `default:${name}` : `current:${name}` })) };
	const legacyValues = ["真实感", "人物角色", "案例长段版", false, "全随机", 10, "中", "自动", "纯中文"];
	const normalized = exports.normalizeLegacyWidgetValues(node, legacyValues);
	assert.equal(normalized.length, widgetNames.length);
	assert.equal(normalized[0], "default:模型来源");
	assert.equal(normalized[8], "default:内置KV缓存V类型");
	assert.equal(normalized[14], "default:API额外请求头");
	assert.equal(normalized[15], "真实感");
	assert.equal(normalized[22], "自动");
	assert.equal(normalized[23], "纯中文");
});

test("legacy widget values append runtime random internals after existing caches", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const widgetNames = [
		"模板风格",
		"随机补充避重缓存",
		"连续生成避重缓存",
		exports.RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME,
		exports.RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME,
	];
	const node = {
		properties: {},
		widgets: widgetNames.map((name) => ({ name, value: name === "模板风格" ? "自动" : "" })),
	};
	const normalized = exports.normalizeLegacyWidgetValues(node, ["真实感", "tag-cache", "prompt-cache"]);
	assert.equal(JSON.stringify(normalized), JSON.stringify(["真实感", "tag-cache", "prompt-cache", "", ""]));
});

test("runtime random preview token stays out of preset and history settings", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(exports.PRESET_SETTING_NAMES.includes(exports.RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME), false);
	const token = exports.createRuntimeRandomPreviewMarker({ id: 42 }, { settings: { seed: 123, "运行时随机模式": "全随机" } });
	assert.equal(JSON.parse(token).source, "ui");
});

test("preset state keeps reproducible generation settings without credentials or runtime caches", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	for (const name of [
		"风格隔离策略", "智能文本匹配", "智能文本输入", "内置模型系列", "内置主模型",
		"内置上下文长度", "内置GPU层数", "系统提示词覆盖", "最大生成token", "温度",
		"top_p", "top_k", "重复惩罚", "频率惩罚", "存在惩罚", "输出think块",
	]) {
		assert.equal(exports.PRESET_SETTING_NAMES.includes(name), true, `${name} should be saved in presets`);
	}
	for (const name of ["API密钥", "API额外请求头", "随机补充避重缓存", "连续生成避重缓存", exports.RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME]) {
		assert.equal(exports.PRESET_SETTING_NAMES.includes(name), false, `${name} should stay out of presets`);
	}
	assert.equal(exports.PRESET_SETTING_DEFAULTS["生成数量"], 3);
	assert.equal(exports.PRESET_SETTING_DEFAULTS["详细度"], "标准");
	assert.equal(exports.PRESET_SETTING_DEFAULTS["运行时随机模式"], "自动判断");
	assert.equal(exports.PRESET_SETTING_DEFAULTS["风格隔离策略"], "平衡收敛");
	assert.equal(exports.PRESET_SETTING_DEFAULTS["最大生成token"], 1800);
	assert.equal(exports.PRESET_SETTING_DEFAULTS["温度"], 0.62);
});

test("random mode options expose rewrite subject and scene mode", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /value:\s*"自动判断"/u);
	assert.match(source, /value:\s*"重写主体与场景"/u);
});

test("random theme pool options expose richer production tracks", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	for (const themePool of ["商业摄影", "时尚大片", "海岸假日", "武侠江湖", "东方赛博", "机甲科幻", "废土荒原"]) {
		assert.match(source, new RegExp(`"${themePool}"`, "u"));
	}
	assert.match(source, /label:\s*"商业"/u);
	assert.match(source, /label:\s*"机甲"/u);
});

test("template style options expose production subtracks", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	for (const templateStyle of ["商业摄影", "时尚编辑", "电影写实", "私房写实", "复古动画", "东方赛博", "硬表面科幻", "国风电影", "武侠电影", "暗黑奇幻"]) {
		assert.match(source, new RegExp(`value:\\s*"${templateStyle}"`, "u"));
	}
	assert.match(source, /label:\s*"商业"/u);
	assert.match(source, /label:\s*"东方赛博"/u);
});

test("smart text style priority options expose auto node and text modes", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /"智能文本风格优先"/u);
	assert.match(source, /value:\s*"节点优先"/u);
	assert.match(source, /value:\s*"文本优先"/u);
});

test("reverse mode chips keep only auto balance and adult mature options", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /value:\s*"自动平衡"/u);
	assert.match(source, /value:\s*"成人向成熟"/u);
	assert.match(source, /label:\s*"成人策略"/u);
	assert.match(source, /联动 NSFW 标签识别/u);
});

test("stage sanitize keeps language value out of random theme pool", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "随机主题池", value: "纯中文", options: { values: ["自动", "写实生活", "糖水写真"] } },
			{ name: "提示词语言", value: "纯中文", options: { values: ["纯中文", "英文提示词+中文说明", "纯英文"] } },
		],
	};
	exports.sanitizeStagePromptNode(node, { slot_config: [] });
	assert.equal(node.widgets[0].value, "自动");
	assert.equal(node.widgets[1].value, "纯中文");
});

test("stage sanitize collapses legacy reverse mode values to auto balance", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "标签反推模式", value: "高密度站点", options: { values: ["自动平衡", "商业摄影", "高密度站点", "成人向成熟"] } },
		],
	};
	exports.sanitizeStagePromptNode(node, { slot_config: [] });
	assert.equal(node.widgets[0].value, "自动平衡");
});

test("stage sanitize repairs embedded model and image reverse stale values", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [
			{ name: "模型来源", value: "本地GGUF", options: { values: ["仅Skill", "本地模型", "API接口", "本地GGUF"] } },
			{ name: "内置模型系列", value: "旧系列", options: { values: ["Qwen3.5-VL", "通用GGUF"] } },
			{ name: "内置主模型", value: "", options: { values: ["Qwen3.6-35B-A3B-IQ2_M.gguf"] } },
			{ name: "内置视觉投影mmproj", value: "旧mmproj", options: { values: ["无", "mmproj-Qwen3.6-35B-A3B-f16.gguf"] } },
			{ name: "内置KV缓存K类型", value: "旧KV", options: { values: ["默认(F16)", "q8_0"] } },
			{ name: "内置KV缓存V类型", value: "旧KV", options: { values: ["默认(F16)", "q8_0"] } },
			{ name: "API服务商", value: "人物角色", options: { values: ["OpenAI兼容", "智谱GLM"] } },
			{ name: "API模型", value: "重写主体与场景" },
			{ name: "内置上下文长度", value: 0 },
			{ name: "图片反推最大边长", value: 0 },
			{ name: "核心标签锁定数量", value: 999 },
		],
	};
	exports.sanitizeStagePromptNode(node, { slot_config: [] });
	assert.equal(node.widgets[0].value, "本地模型");
	assert.equal(node.widgets[1].value, "Qwen3.5-VL");
	assert.equal(node.widgets[2].value, "Qwen3.6-35B-A3B-IQ2_M.gguf");
	assert.equal(node.widgets[3].value, "无");
	assert.equal(node.widgets[4].value, "默认(F16)");
	assert.equal(node.widgets[5].value, "默认(F16)");
	assert.equal(node.widgets[6].value, "OpenAI兼容");
	assert.equal(node.widgets[7].value, "");
	assert.equal(node.widgets[8].value, 1024);
	assert.equal(node.widgets[9].value, 256);
	assert.equal(node.widgets[10].value, 500);
});

test("panel status messages are folded into the compact summary", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "自动" },
			{ name: "主体类型", value: "自动" },
			{ name: "案例输出结构", value: "自动" },
			{ name: "运行时随机标签", value: false },
			{ name: "运行时随机模式", value: "全随机" },
			{ name: "核心标签锁定数量", value: 10 },
			{ name: "运行时随机强度", value: "中" },
			{ name: "随机主题池", value: "自动" },
			{ name: "锁定标签白名单", value: "" },
			{ name: "随机排除标签", value: "" },
			{ name: "标签反推模式", value: "自动平衡" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "智能文本风格优先", value: "自动判断" },
		],
		[exports.PANEL_KEY]: {
			lastPanelMessage: "已展开高级参数。",
			lastExecutionOutputs: ["", "", "", JSON.stringify({ runtime_random_mode_resolved: "重写主体与场景", smart_text_style_priority_resolved: "自动判断→节点优先", smart_text_style_resolved: "古风" }), "", "", ""],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
	};
	const summary = exports.buildNodeSummaryText(node, library);
	assert.match(summary, /最近：已展开高级参数。/u);
	assert.match(summary, /解析：随机 全随机->重写主体与场景 \| 智能 自动判断→节点优先\/古风/u);
});

test("busy panel action buttons stay disabled during refresh", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const button = makeElement("button");
	button.dataset.qwenHint = "可点击";
	button.disabled = false;
	button.classList.add("is-busy");
	exports.setPanelActionButtonState(button, true, "不可点击");
	assert.equal(button.disabled, true);
	assert.equal(button.title, "处理中...");
	assert.equal(button.style.opacity, "0.72");
	button.classList.remove("is-busy");
	exports.setPanelActionButtonState(button, true, "不可点击");
	assert.equal(button.disabled, false);
	assert.equal(button.title, "可点击");
});

test("terminal preview modes read positive negative tags and json from the correct slots", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [
				"full text",
				"positive prompt",
				"tag summary",
				'{"prompt":"positive prompt","count":1}',
				"negative prompt",
				"prompt A\\nprompt B",
			],
			directStageOutputCache: null,
			workflowOutputMeta: {},
		},
		outputs: [],
	};
	assert.equal(exports.getStageDisplayPayload(node, "prompt").text, "positive prompt");
	assert.equal(exports.getStageDisplayPayload(node, "negative").text, "negative prompt");
	assert.equal(exports.getStageDisplayPayload(node, "tags").text, "tag summary");
	assert.equal(exports.getStageDisplayPayload(node, "json").text, '{\n  "prompt": "positive prompt",\n  "count": 1\n}');
});

test("terminal preview falls back to linked display text node output", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const displayInput = { value: "来自展示文本节点的正向提示词" };
	const displayNode = {
		id: 200,
		type: "ShowText|pysssss",
		title: "展示文本",
		widgets: [{ name: "text", value: "", inputEl: displayInput }],
		widgets_values: [],
	};
	exports.__context.__testApp.graph = {
		_nodes: [],
		links: { 100: { target_id: 200, target_slot: 0 } },
		getNodeById(id) { return Number(id) === 200 ? displayNode : null; },
	};
	const node = {
		id: 100,
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
		},
		outputs: [
			{ links: [] },
			{ links: [100] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
		],
	};
	const payload = exports.getStageDisplayPayload(node, "prompt");
	assert.equal(payload.text, "来自展示文本节点的正向提示词");
	assert.equal(payload.source, "下游文本节点");
});

test("terminal preview reads linked display text from tuple links and nested widget values", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const displayNode = {
		id: 202,
		type: "ShowText|pysssss",
		title: "展示文本",
		widgets: [{ name: "text_1", value: { text: ["来自元组链接的完整正向提示词"] } }],
		widgets_values: [],
	};
	exports.__context.__testApp.graph = {
		_nodes: [displayNode],
		links: [[102, 100, 1, 202, 0, "STRING"]],
		getNodeById() { return null; },
	};
	const node = {
		id: 100,
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
		},
		outputs: [
			{ links: [] },
			{ link: 102 },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
		],
	};
	const payload = exports.getStageDisplayPayload(node, "prompt");
	assert.equal(payload.text, "来自元组链接的完整正向提示词");
	assert.equal(payload.source, "下游文本节点");
});

test("terminal clear suppresses old linked output but accepts a changed downstream prompt", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const displayInput = { value: "旧提示词" };
	const displayNode = {
		id: 201,
		type: "ShowText|pysssss",
		title: "展示文本",
		widgets: [{ name: "text", value: "", inputEl: displayInput }],
		widgets_values: [],
	};
	exports.__context.__testApp.graph = {
		_nodes: [],
		links: { 101: { target_id: 201, target_slot: 0 } },
		getNodeById(id) { return Number(id) === 201 ? displayNode : null; },
	};
	const node = {
		id: 101,
		properties: {},
		widgets: [],
		[exports.PANEL_KEY]: {
			lastExecutedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			displayMode: "prompt",
		},
		outputs: [
			{ links: [] },
			{ links: [101] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
		],
	};
	assert.equal(exports.getStageDisplayPayload(node, "prompt").text, "旧提示词");
	assert.equal(exports.clearStageTerminalPreviewState(node), true);
	assert.match(exports.getStageDisplayPayload(node, "prompt").text, /还没有正向提示词/u);
	displayInput.value = "新提示词";
	const payload = exports.getStageDisplayPayload(node, "prompt");
	assert.equal(payload.text, "新提示词");
	assert.equal(payload.source, "下游文本节点");
});

test("recordStageExecution stores linked display prompt output into history", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const displayNode = {
		id: 203,
		type: "ShowText|pysssss",
		title: "展示文本",
		widgets: [],
		widgets_values: [{ text: "展示文本节点里的完整生成提示词，会被写入历史查看。" }],
	};
	exports.__context.__testApp.graph = {
		_nodes: [displayNode],
		links: { 103: { id: 103, target_id: 203, target_slot: 0 } },
		getNodeById(id) { return Number(id) === 203 ? displayNode : null; },
	};
	const node = {
		id: 100,
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [
			{ links: [] },
			{ links: [103] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
		],
	};
	assert.equal(exports.recordStageExecution(node, library, null), true);
	const history = exports.getNodeHistory(node);
	assert.match(history[0].meta.stageOutput.promptText, /完整生成提示词/u);
	assert.match(exports.buildHistoryPromptViewText(history[0]), /展示文本节点里的完整生成提示词/u);
});

test("terminal preview prefers live cache and can open the expanded output dialog", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const sourceEl = makeElement("div");
	const promptTab = makeElement("button");
	const node = {
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: {
				status: "running",
				outputs: ["full", "live positive", "live tags", '{"live":true}', "live negative", "collection"],
			},
			workflowOutputMeta: {},
			displayMode: "negative",
			displayBodyEl: bodyEl,
			displaySourceEl: sourceEl,
			displayTabButtons: new Map([["negative", promptTab]]),
			expandedDisplayOverlay: null,
		},
		outputs: [],
	};
	exports.refreshStageDisplay(node);
	assert.equal(bodyEl.textContent, "live negative");
	assert.equal(sourceEl.textContent, "实时生成中");
	assert.equal(promptTab.classList.contains("is-active"), true);
	exports.openStageOutputDialog(node);
	assert.equal(node[exports.PANEL_KEY].expandedDisplayOverlay?.dataset.qwenModal, "stage-output");
	assert.equal(node[exports.PANEL_KEY].expandedDisplayBodyEl?.textContent, "live negative");
});

test("terminal preview reads own cache without downstream links", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: {
				status: "done",
				updated_at: Date.now(),
				outputs: ["完整结果", "无连线也能显示的正向提示词", "标签摘要", "{}", "负面词", "合集", "智能文本"],
			},
			workflowOutputMeta: {},
		},
		outputs: [],
	};
	const payload = exports.getStageDisplayPayload(node, "prompt");
	assert.equal(payload.text, "无连线也能显示的正向提示词");
	assert.equal(payload.source, "实时缓存");
	assert.equal(payload.empty, false);
});

test("terminal preview captures API style executed output payloads", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const sourceEl = makeElement("div");
	const node = {
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			displayMode: "prompt",
			displayBodyEl: bodyEl,
			displaySourceEl: sourceEl,
			displayTabButtons: new Map(),
		},
		outputs: [],
	};
	const captured = exports.captureStageExecutionOutputsFromArgs(node, [{
		output: {
			outputs: [
				"完整结果全文",
				"一位气质高智的东亚成年女性国潮模特，留着干练中分短发，身着修身礼服。",
				"模型与Skill链路：Skill前置 + API模型后置润色",
				'{"model_source":"API接口","model_skill_pipeline":"Skill前置 + API模型后置润色"}',
				"low quality, blurry",
				"提示词合集全文",
				"智能文本提示词",
			],
		},
	}]);
	assert.equal(captured, true);
	exports.refreshStageDisplay(node);
	assert.match(bodyEl.textContent, /东亚成年女性国潮模特/u);
	assert.equal(sourceEl.textContent, "本次执行");
});

test("rapid batch execution records every generated prompt before the next result clears it", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: 88,
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		outputs: [],
		[exports.PANEL_KEY]: {
			library,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			stageOutputRecordSignature: "",
		},
	};
	node[exports.PANEL_READY_KEY] = true;
	exports.__context.__testApp.graph._nodes = [node];
	const executedPayload = (prompt) => [{ qwen_te_stage_output: ["完整结果", prompt, "标签摘要", "{}", "负面词", prompt, ""] }];

	assert.equal(exports.captureStageExecutionHistoryFromArgs(node, library, executedPayload("批次一生成的完整提示词")), true);
	node[exports.PANEL_KEY].stageOutputRecordSignature = "";
	assert.equal(exports.captureStageExecutionHistoryFromArgs(node, library, executedPayload("批次二生成的完整提示词")), true);
	node[exports.PANEL_KEY].stageOutputRecordSignature = "";
	assert.equal(exports.captureStageExecutionHistoryFromArgs(node, library, executedPayload("批次二生成的完整提示词")), true);

	const prompts = exports.getNodeHistory(node).map((item) => item.meta.stageOutput.promptText);
	assert.deepEqual(Array.from(prompts), [
		"批次二生成的完整提示词",
		"批次二生成的完整提示词",
		"批次一生成的完整提示词",
	]);
});

test("batch cache reconciliation restores executions omitted by ComfyUI callbacks", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: 89,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library,
			lastWorkflowQueueRequestedAt: 1000,
			lastExecutionOutputs: [],
			stageOutputEventRecordCount: 1,
			stageOutputCacheProcessedIds: [],
			stageOutputRecordSignature: "",
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	const entry = (id, updatedAt, prompt) => ({
		execution_id: id,
		updated_at: updatedAt,
		status: "done",
		prompt_text: prompt,
		prompt_collection: prompt,
		negative_prompt: "负面词",
	});
	const latest = entry("run-3", 1300, "第三批提示词");
	assert.equal(exports.captureStageExecutionHistoryFromArgs(node, library, [{ qwen_te_stage_output: ["", latest.prompt_text, "", "{}", "负面词", latest.prompt_text, ""] }]), true);
	// The simulated callback above increments the counter; reproduce ComfyUI's one-callback batch state.
	node[exports.PANEL_KEY].stageOutputEventRecordCount = 1;
	const recovered = exports.recordMissingStageExecutionHistoryFromCache(node, library, {
		...latest,
		execution_history: [latest, entry("run-2", 1200, "第二批提示词"), entry("run-1", 1100, "第一批提示词")],
	}, { executionStartedAt: 1300 });
	assert.equal(recovered, 2);
	assert.deepEqual(Array.from(exports.getNodeHistory(node).map((item) => item.meta.stageOutput.promptText)), [
		"第二批提示词",
		"第一批提示词",
		"第三批提示词",
	]);
	assert.equal(exports.recordMissingStageExecutionHistoryFromCache(node, library, {
		...latest,
		execution_history: [latest, entry("run-2", 1200, "第二批提示词"), entry("run-1", 1100, "第一批提示词")],
	}, { executionStartedAt: 1300 }), 0);
});

test("single executed callback restores the full backend batch history", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: 90,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library,
			lastWorkflowQueueRequestedAt: 1000,
			lastExecutionOutputs: [],
			stageOutputEventRecordCount: 0,
			stageOutputCacheProcessedIds: [],
			stageOutputRecordSignature: "",
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	const entry = (id, updatedAt, prompt) => ({
		execution_id: id,
		updated_at: updatedAt,
		status: "done",
		prompt_text: prompt,
		prompt_collection: prompt,
	});
	const history = [entry("run-3", 1300, "第三批"), entry("run-2", 1200, "第二批"), entry("run-1", 1100, "第一批")];
	const args = [{
		qwen_te_stage_output: ["", "第三批", "", "{}", "", "第三批", ""],
		qwen_te_stage_output_history: history,
	}];
	assert.deepEqual(Array.from(exports.extractStageExecutionHistoryFromArgs(args)), history);
	assert.equal(exports.captureStageExecutionHistoryFromArgs(node, library, args), true);
	assert.deepEqual(Array.from(exports.getNodeHistory(node).map((item) => item.meta.stageOutput.promptText)), ["第二批", "第一批", "第三批"]);
});

test("opening history reconciles batch outputs that arrived after the executed callback", async () => {
	const entry = (id, updatedAt, prompt) => ({
		execution_id: id,
		updated_at: updatedAt,
		status: "done",
		prompt_text: prompt,
		prompt_collection: prompt,
	});
	const latest = entry("run-3", 1300, "第三批");
	const history = [latest, entry("run-2", 1200, "第二批"), entry("run-1", 1100, "第一批")];
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		fetch: async () => ({
			ok: true,
			json: async () => ({ ok: true, output: { ...latest, execution_history: history } }),
		}),
	});
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: 91,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library,
			lastWorkflowQueueRequestedAt: 1000,
			lastExecutionOutputs: [],
			stageOutputEventRecordCount: 1,
			stageOutputCacheProcessedIds: [],
			stageOutputRecordSignature: "",
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.captureStageExecutionHistoryFromArgs(node, library, [{
		qwen_te_stage_output: ["", latest.prompt_text, "", "{}", "", latest.prompt_text, ""],
	}]);
	node[exports.PANEL_KEY].stageOutputEventRecordCount = 1;

	assert.equal(await exports.reconcileStageExecutionHistoryBeforeOpen(node, library), 2);
	assert.equal(await exports.reconcileStageExecutionHistoryBeforeOpen(node, library), 0);
	assert.deepEqual(Array.from(exports.getNodeHistory(node).map((item) => item.meta.stageOutput.promptText)), [
		"第二批",
		"第一批",
		"第三批",
	]);
});

test("opening history falls back to workflow history when the direct cache namespace misses", async () => {
	const nodeId = 92;
	const cacheNamespace = "node-workflow-history";
	const stageOutput = (prompt) => ["", prompt, "", "{}", "", prompt, ""];
	const historyEntry = (promptId, createdAt, prompt) => ({
		prompt: [0, promptId, { [nodeId]: { inputs: {} } }, {
			create_time: createdAt,
			extra_pnginfo: { workflow: { nodes: [{ id: nodeId, properties: { qwen_te_cache_namespace_v1: cacheNamespace } }] } },
		}],
		outputs: { [nodeId]: { qwen_te_stage_output: stageOutput(prompt) } },
	});
	const workflowHistory = {
		"prompt-1": historyEntry("prompt-1", 1100, "第一批"),
		"prompt-2": historyEntry("prompt-2", 1200, "第二批"),
		"prompt-3": historyEntry("prompt-3", 1300, "第三批"),
	};
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		fetch: async (url) => String(url).includes("/history?")
			? { ok: true, json: async () => workflowHistory }
			: { ok: false, status: 404, json: async () => ({}) },
	});
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: nodeId,
		properties: { [exports.NODE_CACHE_NAMESPACE_KEY]: cacheNamespace },
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library,
			lastWorkflowQueueRequestedAt: 1000,
			lastExecutionOutputs: stageOutput("第三批"),
			stageOutputEventRecordCount: 1,
			stageOutputCacheProcessedIds: [],
			stageOutputWorkflowProcessedIds: [],
			stageOutputRecordSignature: "",
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.captureStageExecutionHistoryFromArgs(node, library, [{ qwen_te_stage_output: stageOutput("第三批") }]);
	node[exports.PANEL_KEY].stageOutputEventRecordCount = 1;

	assert.equal(await exports.reconcileStageExecutionHistoryBeforeOpen(node, library), 2);
	assert.equal(await exports.reconcileStageExecutionHistoryBeforeOpen(node, library), 0);
	assert.deepEqual(Array.from(exports.getNodeHistory(node).map((item) => item.meta.stageOutput.promptText)), [
		"第二批",
		"第一批",
		"第三批",
	]);
});

test("terminal preview accepts cache written before delayed onExecuted event", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const prompt = "缓存先写入但执行事件稍后才到的正向提示词，人物完整入镜，光影稳定。";
	exports.__context.fetch = async () => ({
		ok: true,
		json: async () => ({
			ok: true,
			output: {
				status: "done",
				updated_at: 2500,
				outputs: ["完整结果", prompt, "标签摘要", "{}", "负面词", "合集", "智能文本"],
			},
		}),
	});
	const node = {
		id: 42,
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutedAt: 120000,
			lastWorkflowQueueRequestedAt: 1000,
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	await exports.syncNodeStageOutputCache(node);
	assert.equal(node[exports.PANEL_KEY].directStageOutputCache._qwenStaleForCurrentRun, false);
	assert.equal(exports.getStageDisplayPayload(node, "prompt").text, prompt);
	assert.equal(exports.recordStageExecution(node, library, null), true);
	assert.match(exports.buildHistoryPromptViewText(exports.getNodeHistory(node)[0]), /缓存先写入/u);
});

test("stage output cache tries unique id aliases when node id misses", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const calls = [];
	const prompt = "通过 unique_id 别名命中的即时缓存提示词，终端预览无需刷新。";
	exports.__context.fetch = async (url) => {
		calls.push(String(url));
		const hit = String(url).includes("backend-node-88");
		return {
			ok: hit,
			json: async () => ({
				ok: true,
				output: {
					status: "done",
					updated_at: 3600,
					outputs: ["完整结果", prompt, "标签摘要", "{}", "负面词", "合集", "智能文本"],
				},
			}),
		};
	};
	const node = {
		id: 42,
		properties: {
			unique_id: "backend-node-88",
			[exports.NODE_CACHE_NAMESPACE_KEY]: "node-cache-namespace-0001",
		},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutedAt: 120000,
			lastWorkflowQueueRequestedAt: 1000,
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	assert.deepEqual(Array.from(exports.getStageOutputCacheLookupIds(node)).slice(0, 2), ["42", "backend-node-88"]);
	await exports.syncNodeStageOutputCache(node);
	assert.equal(calls.length, 2);
	assert.equal(calls.every((url) => url.includes("namespace=node-cache-namespace-0001")), true);
	assert.equal(node[exports.PANEL_KEY].directStageOutputCacheId, "backend-node-88");
	assert.equal(exports.getStageDisplayPayload(node, "prompt").text, prompt);
});

test("runtime random preview request includes the node cache namespace", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("requestState.cache_namespace = ensureNodeCacheNamespace(node);"), true);
});

test("stage output cache handles second and millisecond timestamps", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(exports.normalizeStageTimestampMs(2500), 2500000);
	assert.equal(exports.normalizeStageTimestampMs(1760000000000), 1760000000000);
});

test("stage output cache rejects pre-queue millisecond results without rejecting legacy second timestamps", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const queuedAt = 1760000000900;
	let updatedAt = queuedAt - 100;
	exports.__context.fetch = async () => ({
		ok: true,
		json: async () => ({
			ok: true,
			output: { status: "done", updated_at: updatedAt, outputs: ["全文", "旧结果", "", "{}", "", "", ""] },
		}),
	});
	const node = {
		id: 92,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			lastWorkflowQueueRequestedAt: queuedAt,
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
		},
	};
	await exports.syncNodeStageOutputCache(node);
	assert.equal(node[exports.PANEL_KEY].directStageOutputCache._qwenStaleForCurrentRun, true);
	updatedAt = Math.floor(queuedAt / 1000);
	await exports.syncNodeStageOutputCache(node);
	assert.equal(node[exports.PANEL_KEY].directStageOutputCache._qwenStaleForCurrentRun, false);
});

test("queue workflow starts polling and defers capture until onExecuted", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("async function queueWorkflowFromNode");
	const end = source.indexOf("async function runSmartTextMatch", start);
	const queueWorkflowSource = source.slice(start, end);
	assert.match(queueWorkflowSource, /markNodeWorkflowQueueRequested\(node, requestedAt\)/u);
	assert.doesNotMatch(queueWorkflowSource, /scheduleStageExecutionOutputCapture\(node/u);
	const executedStart = source.indexOf("const originalOnExecuted=node.onExecuted");
	const executedEnd = source.indexOf("bindSummaryRefresh(node, library)", executedStart);
	const executedSource = source.slice(executedStart, executedEnd);
	assert.ok(executedSource.indexOf("stopStageOutputPolling(node)") < executedSource.indexOf("scheduleStageExecutionOutputCapture(node"));
	assert.match(executedSource, /stageOutputRecordSignature\s*=\s*""/u);
	assert.ok(executedSource.indexOf("captureStageExecutionHistoryFromArgs(node") < executedSource.indexOf("scheduleStageExecutionOutputCapture(node"));
	const prepareStart = source.indexOf("function prepareStageNodeForQueueCapture");
	const prepareEnd = source.indexOf("function scheduleStageOutputCaptureForAllNodes", prepareStart);
	assert.match(source.slice(prepareStart, prepareEnd), /stageOutputRecordSignature\s*=\s*""/u);
});

test("disabled queue button does not report a successful queue", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const queueButton = new exports.__context.HTMLElement();
	let clickCount = 0;
	queueButton.disabled = true;
	queueButton.click = () => { clickCount += 1; };
	queueButton.getAttribute = () => null;
	queueButton.classList = { contains: () => false };
	exports.__context.document.querySelector = (selector) => selector === "#queue-button" ? queueButton : null;
	delete exports.__context.__testApp.queuePrompt;
	assert.equal(await exports.queueWorkflowFromNode(), false);
	assert.equal(clickCount, 0);
});

test("background stage output polling refreshes and records completed cache", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function ensureStageOutputPolling");
	const end = source.indexOf("function getStageOutputValueFromList", start);
	const pollingSource = source.slice(start, end);
	assert.equal(pollingSource.includes("document.hidden"), false);
	assert.match(pollingSource, /refreshStageDisplay\(node\)/u);
	assert.match(pollingSource, /recordStageExecution\(node/u);
	assert.match(pollingSource, /outputStatus === "done"/u);
	assert.match(pollingSource, /stopStageOutputPolling\(node\)/u);
	assert.match(pollingSource, /STAGE_OUTPUT_POLL_IDLE_LIMIT/u);
});

test("stage output polling stops while idle and queue requests restart and reset it", async () => {
	let nextTimerId = 0;
	const timers = new Map();
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setInterval: (callback) => {
			const timerId = ++nextTimerId;
			timers.set(timerId, callback);
			return timerId;
		},
		clearInterval: (timerId) => { timers.delete(timerId); },
	});
	exports.__context.fetch = async () => ({ ok: true, json: async () => ({ ok: true, output: null }) });
	const node = {
		id: 91,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			stageOutputPollTimer: null,
			stageOutputPollIdleCount: 0,
			stageOutputPollActiveCount: 0,
			lastWorkflowQueueRequestedAt: 0,
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.ensureStageOutputPolling(node, { idleLimit: 3, activeLimit: 10 });
	const firstTimerId = node[exports.PANEL_KEY].stageOutputPollTimer;
	const firstTick = timers.get(firstTimerId);
	for (let index = 0; index < 3; index += 1) await firstTick();
	assert.equal(node[exports.PANEL_KEY].stageOutputPollTimer, null);
	assert.equal(timers.has(firstTimerId), false);

	exports.markNodeWorkflowQueueRequested(node, Date.now());
	const resumedTimerId = node[exports.PANEL_KEY].stageOutputPollTimer;
	assert.notEqual(resumedTimerId, null);
	assert.notEqual(resumedTimerId, firstTimerId);
	const resumedTick = timers.get(resumedTimerId);
	for (let index = 0; index < 11; index += 1) await resumedTick();
	assert.equal(node[exports.PANEL_KEY].stageOutputPollTimer, resumedTimerId);
	exports.markNodeWorkflowQueueRequested(node, Date.now() + 1);
	await resumedTick();
	assert.equal(node[exports.PANEL_KEY].stageOutputPollTimer, resumedTimerId);
	exports.stopStageOutputPolling(node);
});

test("stale stage cache counts toward the idle polling limit", async () => {
	let nextTimerId = 0;
	const timers = new Map();
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setInterval: (callback) => {
			const timerId = ++nextTimerId;
			timers.set(timerId, callback);
			return timerId;
		},
		clearInterval: (timerId) => { timers.delete(timerId); },
	});
	const queuedAt = Date.now();
	exports.__context.fetch = async () => ({
		ok: true,
		status: 200,
		json: async () => ({
			ok: true,
			output: { status: "done", updated_at: queuedAt - 1000, outputs: ["旧全文", "旧提示词", "", "{}", "", "", ""] },
		}),
	});
	const node = {
		id: 191,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			stageOutputPollTimer: null,
			stageOutputPollIdleCount: 0,
			stageOutputPollActiveCount: 0,
			lastWorkflowQueueRequestedAt: queuedAt,
			pendingModelApiConfigSignature: "pending-stale-run",
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.ensureStageOutputPolling(node, { idleLimit: 3, activeLimit: 20 });
	const timerId = node[exports.PANEL_KEY].stageOutputPollTimer;
	const tick = timers.get(timerId);
	for (let index = 0; index < 3; index += 1) await tick();
	assert.equal(node[exports.PANEL_KEY].stageOutputPollTimer, null);
	assert.equal(timers.has(timerId), false);
	assert.equal(node[exports.PANEL_KEY].pendingModelApiConfigSignature, "");
});

test("failed and timed-out stage polling clear pending API runtime state", async () => {
	let nextTimerId = 0;
	const timers = new Map();
	const responses = [
		{ ok: true, output: { status: "failed", updated_at: Date.now() } },
		{ ok: true, output: { status: "running", updated_at: Date.now() } },
	];
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setInterval: (callback) => {
			const timerId = ++nextTimerId;
			timers.set(timerId, callback);
			return timerId;
		},
		clearInterval: (timerId) => { timers.delete(timerId); },
		fetch: async () => ({
			ok: true,
			status: 200,
			json: async () => responses.shift() ?? { ok: true, output: { status: "running" } },
		}),
	});
	const makeNode = (id) => ({
		id,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			pendingModelApiConfigSignature: "pending-api-run",
			stageOutputPollTimer: null,
			stageOutputPollIdleCount: 0,
			stageOutputPollActiveCount: 0,
			lastWorkflowQueueRequestedAt: Date.now(),
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
		},
	});
	const failedNode = makeNode(194);
	exports.__context.__testApp.graph._nodes = [failedNode];
	exports.ensureStageOutputPolling(failedNode, { idleLimit: 1, activeLimit: 2 });
	await timers.get(failedNode[exports.PANEL_KEY].stageOutputPollTimer)();
	assert.equal(failedNode[exports.PANEL_KEY].pendingModelApiConfigSignature, "");
	assert.equal(failedNode[exports.PANEL_KEY].stageOutputPollTimer, null);

	const timeoutNode = makeNode(195);
	exports.__context.__testApp.graph._nodes = [timeoutNode];
	exports.ensureStageOutputPolling(timeoutNode, { idleLimit: 1, activeLimit: 1 });
	const timeoutTick = timers.get(timeoutNode[exports.PANEL_KEY].stageOutputPollTimer);
	await timeoutTick();
	await timeoutTick();
	assert.equal(timeoutNode[exports.PANEL_KEY].pendingModelApiConfigSignature, "");
	assert.equal(timeoutNode[exports.PANEL_KEY].stageOutputPollTimer, null);
});

test("stopping stage polling invalidates an in-flight body before it can commit", async () => {
	let nextTimerId = 0;
	const timers = new Map();
	let resolveBody;
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setInterval: (callback) => {
			const timerId = ++nextTimerId;
			timers.set(timerId, callback);
			return timerId;
		},
		clearInterval: (timerId) => { timers.delete(timerId); },
		fetch: async () => ({
			ok: true,
			status: 200,
			json: async () => await new Promise((resolve) => { resolveBody = resolve; }),
		}),
	});
	const node = {
		id: 192,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			stageOutputPollTimer: null,
			stageOutputPollIdleCount: 0,
			stageOutputPollActiveCount: 0,
			lastWorkflowQueueRequestedAt: 0,
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.ensureStageOutputPolling(node, { idleLimit: 3, activeLimit: 20 });
	const tick = timers.get(node[exports.PANEL_KEY].stageOutputPollTimer);
	const pendingTick = tick();
	while (!resolveBody) await Promise.resolve();
	exports.stopStageOutputPolling(node);
	resolveBody({ ok: true, output: { status: "done", updated_at: Date.now(), outputs: ["全文", "不应提交", "", "{}", "", "", ""] } });
	await pendingTick;
	assert.equal(node[exports.PANEL_KEY].directStageOutputCache, null);
	assert.deepEqual(Array.from(node[exports.PANEL_KEY].lastExecutionOutputs), []);
});

test("a queued callback from an old poll cannot stop its replacement timer", async () => {
	let nextTimerId = 0;
	const timers = new Map();
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setInterval: (callback) => {
			const timerId = ++nextTimerId;
			timers.set(timerId, callback);
			return timerId;
		},
		clearInterval: (timerId) => { timers.delete(timerId); },
	});
	const node = {
		id: 193,
		properties: {},
		widgets: [],
		outputs: [],
		[exports.PANEL_KEY]: {
			library: { slot_config: [], tag_library: {} },
			stageOutputPollTimer: null,
			stageOutputPollIdleCount: 0,
			stageOutputPollActiveCount: 0,
			lastWorkflowQueueRequestedAt: Date.now(),
			displayClearedAt: 0,
			lastExecutionOutputs: [],
			directStageOutputCache: null,
		},
	};
	exports.__context.__testApp.graph._nodes = [node];
	exports.ensureStageOutputPolling(node, { idleLimit: 3, activeLimit: 20 });
	const oldTimerId = node[exports.PANEL_KEY].stageOutputPollTimer;
	const oldTick = timers.get(oldTimerId);
	exports.stopStageOutputPolling(node);
	exports.ensureStageOutputPolling(node, { idleLimit: 3, activeLimit: 20 });
	const replacementTimerId = node[exports.PANEL_KEY].stageOutputPollTimer;
	assert.notEqual(replacementTimerId, oldTimerId);

	await oldTick();

	assert.equal(node[exports.PANEL_KEY].stageOutputPollTimer, replacementTimerId);
	assert.equal(timers.has(replacementTimerId), true);
	exports.stopStageOutputPolling(node);
});

test("final output capture persists strict prompt dedupe cache from fresh payloads", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /const PROMPT_DEDUPE_CACHE_WIDGET_NAME = "连续生成避重缓存"/u);
	assert.match(source, /function syncNodePromptDedupeCacheFromResult/u);
	assert.match(source, /data\.prompt_dedupe_cache/u);
	assert.match(source, /directStageOutput\?\.jsonPayload \?\? null/u);
	assert.match(source, /_qwenStaleForCurrentRun/u);
});

test("global queue prompt capture is installed during setup for refresh-free output", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /function installGlobalStagePromptQueueCapture/u);
	assert.match(source, /app\.queuePrompt = async function/u);
	assert.match(source, /prepareStageNodeForQueueCapture\(node, requestedAt\)/u);
	const queueStart = source.indexOf("function installGlobalStagePromptQueueCapture");
	const queueEnd = source.indexOf("function applyPreset", queueStart);
	assert.doesNotMatch(source.slice(queueStart, queueEnd), /scheduleStageOutputCaptureForAllNodes\(/u);
	const setupStart = source.indexOf("async setup()");
	const setupEnd = source.indexOf("const originalOnNodeAdded", setupStart);
	const setupSource = source.slice(setupStart, setupEnd);
	assert.match(setupSource, /installGlobalStagePromptQueueCapture\(\)/u);
});

test("queue preparation does not report execution before onExecuted", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function prepareStageNodeForQueueCapture");
	const end = source.indexOf("function scheduleStageOutputCaptureForAllNodes", start);
	assert.equal(source.slice(start, end).includes("lastExecutedAt = requestedAt"), false);
	const node = { [exports.PANEL_KEY]: { lastExecutedAt: 100 } };
	let settled = false;
	const pending = exports.waitForNodeExecution(node, 100, 500, 10).then((value) => {
		settled = true;
		return value;
	});
	await new Promise((resolve) => setTimeout(resolve, 35));
	assert.equal(settled, false);
	node[exports.PANEL_KEY].lastExecutedAt = 101;
	assert.equal(await pending, true);
	node[exports.PANEL_KEY].lastWorkflowQueueRequestedAt = 4567;
	assert.equal(exports.getNodeWorkflowQueueRequestedAt(node, 9999), 4567);
	assert.equal(exports.getNodeWorkflowQueueRequestedAt({ [exports.PANEL_KEY]: {} }, 9999), 9999);
	assert.equal((source.match(/const queueRequestedAt = getNodeWorkflowQueueRequestedAt\(node\)/gu) ?? []).length, 2);
	assert.equal(source.includes("const queueRequestedAt = Date.now();"), false);
});

test("recordStageExecution stores full generated prompt for history cards", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [
				"完整结果全文",
				"一位气质高智的东亚成年女性国潮模特，留着干练中分短发，身着修身礼服。",
				"模型与Skill链路：Skill前置 + API模型后置润色",
				'{"runtime_random_style_track":"商业摄影","model_source":"API接口"}',
				"low quality, blurry",
				"提示词合集全文",
				"智能文本提示词",
			],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	assert.equal(exports.recordStageExecution(node, library, null), true);
	const history = exports.getNodeHistory(node);
	assert.equal(history.length, 1);
	const stageOutput = history[0].meta.stageOutput;
	assert.match(stageOutput.promptText, /国潮模特/u);
	assert.equal(stageOutput.promptCollection, "提示词合集全文");
	assert.match(exports.buildHistoryDisplaySummaryText(history[0]), /国潮模特/u);
	assert.match(exports.buildHistoryStageOutputText(stageOutput), /正向提示词合集/u);
	assert.equal(exports.recordStageExecution(node, library, null), false);
	assert.equal(exports.getNodeHistory(node).length, 1);
});

test("history stage output removes duplicate JSON and enforces item and total byte budgets", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const compact = exports.compactHistoryStageOutputPayload({
		promptText: "可查看的正向提示词",
		jsonResult: JSON.stringify({
			runtime_random_style_track: "商业摄影",
			prompt_dedupe_cache: "不应进入历史",
			full_prompt: "也不应复制进历史 JSON",
		}),
	});
	assert.equal(Object.hasOwn(compact, "jsonResult"), false);
	assert.equal(compact.jsonPayload.runtime_random_style_track, "商业摄影");
	assert.equal(JSON.stringify(compact).includes("prompt_dedupe_cache"), false);
	assert.equal(JSON.stringify(compact).includes("不应进入历史"), false);
	const restoredSlots = exports.buildStageOutputListFromSnapshot(compact);
	const restoredJson = JSON.parse(restoredSlots[exports.STAGE_OUTPUT_INDEX.jsonResult]);
	assert.equal(restoredJson.runtime_random_style_track, "商业摄影");
	assert.equal(Object.hasOwn(restoredJson, "prompt_dedupe_cache"), false);

	const node = { properties: {} };
	const history = Array.from({ length: 50 }, (_, index) => ({
		id: `bounded_${index}`,
		source: "executed",
		updatedAt: index,
		state: { selected: {}, customTags: [], settings: {} },
		meta: { stageOutput: { promptText: `${index}:${"长提示".repeat(20000)}`, jsonResult: '{"prompt_dedupe_cache":"large"}' } },
	}));
	exports.setNodeHistory(node, history);
	const bounded = exports.getNodeHistory(node);
	assert.ok(bounded.length < 50);
	assert.ok(Buffer.byteLength(JSON.stringify(bounded), "utf8") <= 1024 * 1024);
	assert.equal(JSON.stringify(bounded).includes("prompt_dedupe_cache"), false);
});

test("history and preset imports reject oversized files before reading them", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let readCount = 0;
	const file = { size: 2 * 1024 * 1024 + 1, async text() { readCount += 1; return "{}"; } };
	await assert.rejects(exports.importNodeHistoryFile({ properties: {} }, file), /2 MiB/u);
	await assert.rejects(exports.importUserPresetFile(file), /2 MiB/u);
	assert.equal(readCount, 0);
});

test("user presets enforce storage bounds and report localStorage quota failures", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const smallState = { selected: {}, customTags: [], settings: {} };
	const presets = Array.from({ length: 40 }, (_, index) => ({ name: `预设${index}`, state: smallState, updatedAt: index }));
	assert.equal(exports.setUserPresets(presets), true);
	assert.equal(exports.getUserPresets().length, 30);
	assert.equal(exports.saveUserPreset("超大预设", { ...smallState, settings: { huge: "x".repeat(200000) } }), false);
	const oversizedText = JSON.stringify({ presets: [{ name: "超大导入", state: { ...smallState, settings: { huge: "x".repeat(200000) } } }] });
	const importResult = await exports.importUserPresetFile({ size: oversizedText.length, async text() { return oversizedText; } });
	assert.equal(importResult.ok, false);
	assert.match(importResult.message, /超过单项/u);
	exports.__context.localStorage.setItem = () => { throw new Error("QuotaExceededError"); };
	assert.equal(exports.saveUserPreset("无法落盘", smallState), false);
});

test("preset import reports only retained items and never evicts existing presets for capacity", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const smallState = { selected: {}, customTags: [], settings: {} };
	const existing = Array.from({ length: 30 }, (_, index) => ({
		id: `existing_${index}`,
		name: `现有预设${index}`,
		state: smallState,
		updatedAt: index + 1,
	}));
	assert.equal(exports.setUserPresets(existing), true);
	const payload = JSON.stringify({
		presets: [
			{ name: "现有预设0", state: { ...smallState, settings: { replaced: true } }, updatedAt: 1000 },
			{ name: "容量外新增", state: smallState, updatedAt: 2000 },
		],
	});
	const result = await exports.importUserPresetFile({ size: payload.length, async text() { return payload; } });
	assert.equal(result.ok, true);
	assert.equal(result.imported, 1);
	assert.equal(result.merged, 1);
	assert.match(result.message, /另有 1 个因容量限制跳过/u);
	const stored = exports.getUserPresets();
	assert.equal(stored.length, 30);
	assert.equal(stored.some((item) => item.name === "容量外新增"), false);
	assert.equal(stored.every((item) => /^现有预设\d+$/u.test(item.name)), true);
	assert.equal(stored.find((item) => item.name === "现有预设0")?.state?.settings?.replaced, true);
});

test("recordStageExecution falls back to full text when prompt slot is missing", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [
				"一段只写在完整结果里的正向提示词，人物完整入镜，光影稳定，场景清晰。",
			],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	assert.equal(exports.recordStageExecution(node, library, null), true);
	const history = exports.getNodeHistory(node);
	assert.match(history[0].meta.stageOutput.promptText, /只写在完整结果/u);
	assert.match(exports.buildHistoryPromptViewText(history[0]), /正向提示词/u);
	assert.doesNotMatch(exports.buildHistoryPromptViewText(history[0]), /没有保存完整生成提示词/u);
});

test("recordStageExecution reads nested direct cache text for history prompt view", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: {
				status: "done",
				output: {
					text: "来自 API 缓存嵌套字段的正向提示词，商业摄影，全身构图，主体清晰。",
				},
			},
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	assert.equal(exports.recordStageExecution(node, library, null), true);
	const history = exports.getNodeHistory(node);
	assert.match(history[0].meta.stageOutput.promptText, /API 缓存嵌套字段/u);
	assert.match(exports.buildHistoryPromptViewText(history[0]), /API 缓存嵌套字段/u);
});

test("clear action clears smart terminal preview and blocks stale hydrated output", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const sourceEl = makeElement("div");
	const smartTab = makeElement("button");
	const node = {
		id: 42,
		properties: {
			qwen_te_workflow_output_v1: {
				stageOutputs: ["", "", "", "", "", "", "old smart from png"],
			},
		},
		widgets: [
			{ name: "智能文本输入", value: "一个女孩", inputEl: { value: "一个女孩" } },
			{ name: "智能文本匹配", value: true },
		],
		[exports.PANEL_KEY]: {
			lastExecutedAt: 0,
			lastExecutionOutputs: ["", "", "", "", "", "", "old smart from session"],
			directStageOutputCache: {
				status: "done",
				updated_at: 1,
				outputs: ["", "", "", "", "", "", "old smart from cache"],
			},
			workflowOutputMeta: {
				stageOutputs: ["", "", "", "", "", "", "old smart from meta"],
			},
			hydratedExecutionOutputs: ["", "", "", "", "", "", "old smart from hydrate"],
			previewExecutionOutputs: ["", "", "", "", "", "", "old smart from preview"],
			displayPreviewSource: "历史预览",
			displayMode: "smart",
			displayBodyEl: bodyEl,
			displaySourceEl: sourceEl,
			displayTabButtons: new Map([["smart", smartTab]]),
		},
	};

	assert.equal(exports.getStageDisplayPayload(node, "smart").text, "old smart from preview");
	assert.equal(exports.clearStageTerminalPreviewState(node), true);
	assert.equal(node[exports.PANEL_KEY].lastExecutionOutputs.length, 0);
	assert.equal(node[exports.PANEL_KEY].directStageOutputCache, null);
	assert.equal(node[exports.PANEL_KEY].workflowOutputMeta, null);
	assert.equal(node.properties.qwen_te_workflow_output_v1, null);
	assert.equal(node.widgets[0].value, "");
	assert.equal(node.widgets[1].value, false);
	assert.match(exports.getStageDisplayPayload(node, "smart").text, /还没有智能文本/u);
	assert.equal(sourceEl.textContent, "等待匹配");
});

test("clear state also clears prompt input widgets from advanced panel", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const extraInput = { value: "保留粉色古风" };
	const smartInput = { value: "一个女孩" };
	const node = {
		id: 77,
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "成年女性" },
			{ name: "自定义补充标签", value: "额外标签" },
			{ name: "额外要求", value: "保留粉色古风", inputEl: extraInput },
			{ name: "智能文本输入", value: "一个女孩", inputEl: smartInput },
			{ name: "智能文本匹配", value: true },
			{ name: "标签块编排启用", value: true },
			{ name: "标签块编排JSON", value: "{\"enabled\":true,\"blocks\":[{\"type\":\"text\",\"text\":\"保留蓝色\"}]}" },
		],
	};
	const library = { slot_config: [{ name: "主体", slots: 1 }] };
	const cleared = exports.buildClearedNodeState(node, library);
	assert.equal(JSON.stringify(cleared.selected), JSON.stringify({ 主体: [] }));
	assert.equal(JSON.stringify(cleared.customTags), JSON.stringify([]));
	assert.equal(cleared.settings["额外要求"], "");
	assert.equal(cleared.settings["智能文本输入"], "");
	assert.equal(cleared.settings["智能文本匹配"], false);
	assert.equal(cleared.settings["标签块编排启用"], false);
	assert.equal(cleared.settings["标签块编排JSON"], "");
	assert.equal(node.widgets.find((widget) => widget.name === "额外要求").value, "");
	assert.equal(extraInput.value, "");
	assert.equal(node.widgets.find((widget) => widget.name === "智能文本输入").value, "");
	assert.equal(smartInput.value, "");
	assert.equal(node.widgets.find((widget) => widget.name === "智能文本匹配").value, false);
	assert.equal(node.widgets.find((widget) => widget.name === "标签块编排启用").value, false);
	assert.equal(node.widgets.find((widget) => widget.name === "标签块编排JSON").value, "");
});

test("clearing a node records both the recoverable snapshot and cleared result", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: ["成年女性"] },
	};
	const node = {
		id: 78,
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "成年女性" },
			{ name: "自定义补充标签", value: "保留红围巾" },
			{ name: "智能文本输入", value: "红围巾女孩" },
			{ name: "智能文本匹配", value: true },
		],
		outputs: [],
		[exports.PANEL_KEY]: { library },
	};
	exports.applyClearedNodeState(node, library);
	const history = exports.getNodeHistory(node);
	assert.deepEqual(Array.from(history.slice(0, 2), (item) => item.source), ["clear", "before-clear"]);
	assert.deepEqual(Array.from(history[0].state.selected["主体"]), []);
	assert.equal(history[1].state.selected["主体"][0], "成年女性");
	assert.equal(history[1].state.customTags.includes("保留红围巾"), true);
	assert.equal(exports.findLatestRollbackHistoryItem(node)?.source, "before-clear");
});

test("a delayed random result cannot overwrite a newer clear action", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: ["初始人物", "旧随机人物"] },
	};
	const node = {
		id: 79,
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "初始人物" },
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "自动" },
			{ name: "运行时随机标签", value: true },
			{ name: "运行时随机模式", value: "全随机" },
			{ name: "运行时随机强度", value: "中" },
			{ name: "核心标签锁定数量", value: 0 },
			{ name: "锁定标签白名单", value: "" },
			{ name: "随机排除标签", value: "" },
			{ name: "随机补充避重缓存", value: "" },
			{ name: "运行时随机保护标签", value: "" },
			{ name: "运行时随机预览令牌", value: "" },
			{ name: "seed", value: 1 },
		],
		outputs: [],
		[exports.PANEL_KEY]: { library },
	};
	exports.__context.__testApp.graph._nodes = [node];
	let releaseRandom;
	exports.__context.fetch = () => new Promise((resolve) => { releaseRandom = resolve; });
	const pendingRandom = exports.buildAndApplyRandomState(node, library);
	assert.equal(typeof releaseRandom, "function");
	exports.applyClearedNodeState(node, library);
	releaseRandom({
		ok: true,
		status: 200,
		json: async () => ({
			state: { selected: { 主体: ["旧随机人物"] }, customTags: [], settings: { "运行时随机标签": true, seed: 2 } },
		}),
	});
	assert.equal(await pendingRandom, false);
	assert.equal(node.widgets.find((widget) => widget.name === "主体标签1").value, "无");
	assert.equal(exports.getNodeHistory(node).some((item) => item.source === "random"), false);

	const pendingControlRandom = exports.buildAndApplyRandomState(node, library);
	exports.setControlWidgetValue(node, "模板风格", "真实感");
	releaseRandom({
		ok: true,
		status: 200,
		json: async () => ({
			state: { selected: { 主体: ["旧随机人物"] }, customTags: [], settings: { "模板风格": "自动" } },
		}),
	});
	assert.equal(await pendingControlRandom, false);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "真实感");

	exports.bindSummaryRefresh(node, library);
	const programmaticRevision = exports.beginNodeStateMutation(node);
	assert.equal(exports.applyNodeState(node, library, {
		selected: { 主体: [] },
		customTags: [],
		settings: { "模板风格": "真实感" },
	}, { mutationRevision: programmaticRevision }), true);
	assert.equal(exports.isNodeStateMutationCurrent(node, programmaticRevision), true);
	const pendingNativeRandom = exports.buildAndApplyRandomState(node, library);
	const templateWidget = node.widgets.find((widget) => widget.name === "模板风格");
	templateWidget.value = "商业摄影";
	templateWidget.callback("商业摄影");
	releaseRandom({
		ok: true,
		status: 200,
		json: async () => ({
			state: { selected: { 主体: ["旧随机人物"] }, customTags: [], settings: { "模板风格": "自动" } },
		}),
	});
	assert.equal(await pendingNativeRandom, false);
	assert.equal(templateWidget.value, "商业摄影");
});

test("clearing the continuous report also removes its persisted event log", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, [exports.PANEL_KEY]: {} };
	exports.setNodeContinuousRunReport(node, [{ at: 1, level: "完成", message: "第 1 轮完成" }]);
	assert.equal(exports.getNodeContinuousRunReport(node).length, 1);
	exports.clearNodeContinuousRunReport(node);
	assert.deepEqual(Array.from(exports.getNodeContinuousRunReport(node)), []);
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("reportClearButton.onclick");
	const end = source.indexOf("searchInput.addEventListener", start);
	assert.match(source.slice(start, end), /clearNodeContinuousRunReport\(node\)/u);
});

test("continuous quality audit callbacks cannot overwrite a newer stop action", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const sharedStart = source.indexOf("async function runNodeContinuousPresetSequence");
	const sharedEnd = source.indexOf("async function startNodeContinuousPresetRun", sharedStart);
	const sharedSource = source.slice(sharedStart, sharedEnd);
	assert.match(sharedSource, /await runNodeQualityAudit[\s\S]*token !== ensureNodeContinuousRuntime\(node\)\.token/u);
	const managerStart = source.indexOf("const startContinuousPresetRun = async");
	const managerEnd = source.indexOf("const applyPresetToNode = async", managerStart);
	const managerSource = source.slice(managerStart, managerEnd);
	assert.match(managerSource, /await runNodeQualityAudit[\s\S]*token !== continuousRunToken/u);
});

test("continuous preset history polling is owned and aborted by the modal", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const helperStart = source.indexOf("async function waitForNodeContinuousWorkflowOutput");
	const helperEnd = source.indexOf("function formatQualityAuditSummary", helperStart);
	const helperSource = source.slice(helperStart, helperEnd);
	assert.match(helperSource, /requestOwner:\s*options\.requestOwner/u);
	assert.match(helperSource, /requestKey:\s*options\.requestKey \?\? "continuous-workflow-history"/u);
	const managerStart = source.indexOf("const stopContinuousRun =");
	const managerEnd = source.indexOf("const applyPresetToNode = async", managerStart);
	const managerSource = source.slice(managerStart, managerEnd);
	assert.match(managerSource, /abortOwnedRequest\(overlay, "continuous-workflow-history"\)/u);
	assert.match(managerSource, /requestOwner:\s*overlay/u);
	assert.match(managerSource, /requestKey:\s*"continuous-workflow-history"/u);
});

test("tag block composer packs selected tags and preserves block state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [{ name: "主体", slots: 2 }, { name: "场景背景", slots: 2 }] };
	const node = {
		id: 88,
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "成年女性" },
			{ name: "主体标签2", value: "银白长发" },
			{ name: "场景背景标签1", value: "湖畔夕照" },
			{ name: "场景背景标签2", value: "无" },
			{ name: "自定义补充标签", value: "冷色调, 逆光" },
			{ name: "标签块编排启用", value: false },
			{ name: "标签块编排JSON", value: "" },
		],
	};
	const state = exports.buildTagBlockComposerStateFromNode(node, library);
	assert.equal(state.enabled, true);
	assert.equal(JSON.stringify(state.blocks.map((block) => block.label)), JSON.stringify(["主体", "场景背景", "自定义"]));
	assert.equal(JSON.stringify(state.blocks[0].tags), JSON.stringify(["成年女性", "银白长发"]));
	const serialized = exports.serializeTagBlockComposerState(state);
	const parsed = exports.parseTagBlockComposerState(serialized);
	assert.equal(parsed.blocks.length, 3);
	assert.equal(parsed.blocks[2].tags.includes("逆光"), true);
});

test("tag block composer imports nsfw workspace selector and camera blocks", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [{ name: "画面风格", slots: 2 }, { name: "构图视角", slots: 2 }] };
	const node = {
		id: 188,
		properties: {
			nsfw_workspace: {
				enabled: true,
				selector_character: "兔女郎",
				selector_outfit: "项圈",
				selector_action: "女上位姿态",
				selector_scene: "按摩场景",
				selector_expression: "喘息感",
				selector_prop: "绳索",
				camera_movement: "晃动镜头，营造紧张挑逗氛围",
				camera_angle: "低角度，突出臀部与腿部线条",
				light_source: "红色烛光，摇曳氛围",
				lens_type: "近景半身，脸部和服装上半身清楚",
				color_tone: "深红挑逗调，浓烈感官",
				visual_style: "东方赛博武侠朋克",
				effect: "胶片颗粒，复古质感",
				filter: "颗粒滤镜，复古质感",
			},
		},
		widgets: [
			{ name: "画面风格标签1", value: "东方赛博武侠朋克" },
			{ name: "画面风格标签2", value: "无" },
			{ name: "构图视角标签1", value: "低角度" },
			{ name: "构图视角标签2", value: "无" },
			{ name: "自定义补充标签", value: "" },
			{ name: "标签块编排启用", value: false },
			{ name: "标签块编排JSON", value: "" },
		],
	};
	const state = exports.buildTagBlockComposerStateFromNode(node, library);
	const labels = state.blocks.map((block) => block.label);
	assert.equal(labels.includes("NSFW选择器"), true);
	assert.equal(labels.includes("NSFW镜头"), true);
	const selectorBlock = state.blocks.find((block) => block.label === "NSFW选择器");
	const cameraBlock = state.blocks.find((block) => block.label === "NSFW镜头");
	assert.equal(selectorBlock.tags.includes("兔女郎"), true);
	assert.equal(selectorBlock.tags.includes("按摩场景"), true);
	assert.equal(cameraBlock.tags.includes("晃动镜头"), true);
	assert.equal(cameraBlock.tags.includes("营造紧张挑逗氛围"), true);
	assert.equal(cameraBlock.tags.includes("红色烛光"), true);
	assert.equal(cameraBlock.tags.includes("摇曳氛围"), true);
});

test("tag block composer can delete a single chip without clearing the block", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const initial = {
		version: 1,
		enabled: true,
		blocks: [{ id: "subject", type: "tag_group", group: "主体", label: "主体", tags: ["清冷", "奢暖", "商业"], text: "", locked: false }],
	};
	const node = {
		id: 89,
		properties: {},
		widgets: [
			{ name: "标签块编排启用", value: true },
			{ name: "标签块编排JSON", value: exports.serializeTagBlockComposerState(initial) },
		],
	};
	exports.removeTagBlockComposerTag(node, 0, 1);
	const next = exports.readTagBlockComposerState(node);
	assert.equal(next.enabled, true);
	assert.equal(JSON.stringify(next.blocks[0].tags), JSON.stringify(["清冷", "商业"]));
	assert.equal(node.widgets.find((widget) => widget.name === "标签块编排JSON").value.includes("奢暖"), false);
});

test("tag block composer gives custom tags a readable wrapped container", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("qwen-te-panel__block-card--custom"), true);
	assert.equal(source.includes("block.label === \"自定义\" || block.group === \"自定义补充\""), true);
	assert.equal(source.includes(".qwen-te-panel__block-card--custom .qwen-te-panel__block-chip-list{grid-column:1/-1;grid-row:2"), true);
	assert.equal(source.includes("grid-template-columns:repeat(auto-fill,minmax(128px,1fr))"), true);
	assert.equal(source.includes("max-height:132px;overflow:auto"), true);
});

test("expanded tag block composer uses the output screen as the scroll container", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('.qwen-te-modal[data-qwen-modal="stage-output"] .qwen-te-modal__stage-output-body{flex:1 1 auto;overflow:hidden}'), true);
	assert.equal(source.includes(".qwen-te-modal__stage-output-screen.qwen-te-panel__display-screen--blocks"), true);
	assert.equal(source.includes(".qwen-te-modal__stage-output-screen.qwen-te-panel__display-screen--blocks .qwen-te-panel__block-list{overflow:visible"), true);
	assert.equal(source.includes("padding-bottom:42px"), true);
});

test("tag block composer run switches terminal back to positive prompt preview", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("async function runTagBlockComposer");
	const end = source.indexOf("function renderInlineTagBlockComposer", start);
	const runBlock = source.slice(start, end);
	assert.match(runBlock, /displayMode = "prompt"/u);
	assert.match(runBlock, /refreshStageDisplay\(node\)/u);
	assert.match(runBlock, /queueWorkflowFromNode\(node\)/u);
});

test("smart terminal preview rebuilds inline input after switching away and back", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const sourceEl = makeElement("div");
	const smartTab = makeElement("button");
	const jsonTab = makeElement("button");
	const node = {
		widgets: [{ name: "智能文本输入", value: "一个女孩", inputEl: { value: "一个女孩" } }],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			displayBodyEl: bodyEl,
			displaySourceEl: sourceEl,
			displayMode: "smart",
			displayTabButtons: new Map([["smart", smartTab], ["json", jsonTab]]),
		},
		outputs: [],
	};

	exports.refreshStageDisplay(node);
	assert.equal(bodyEl.__qwenSmartUi?.input?.parentNode, bodyEl);
	node[exports.PANEL_KEY].displayMode = "json";
	exports.refreshStageDisplay(node);
	assert.equal(bodyEl.__qwenSmartUi, undefined);
	assert.match(bodyEl.textContent, /JSON 输出/u);
	node[exports.PANEL_KEY].displayMode = "smart";
	exports.refreshStageDisplay(node);
	assert.equal(bodyEl.__qwenSmartUi?.input?.parentNode, bodyEl);
	assert.equal(bodyEl.__qwenSmartUi?.input?.value, "一个女孩");
	assert.match(bodyEl.__qwenSmartUi?.resultLead?.textContent ?? "", /还没有可显示的智能文本预览/u);
	assert.equal(typeof bodyEl.__qwenSmartUi?.resultBody, "object");
	assert.equal(smartTab.classList.contains("is-active"), true);
});

test("smart terminal preview lead reflects nsfw strategy when workspace is enabled", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const node = {
		properties: {
			nsfwWorkspace: { enabled: true },
		},
		widgets: [{ name: "智能文本输入", value: "一个女孩", inputEl: { value: "一个女孩" } }],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			displayBodyEl: bodyEl,
			displaySourceEl: makeElement("div"),
			displayMode: "smart",
			library: {
				slot_config: [],
			},
		},
		outputs: [],
	};

	exports.refreshStageDisplay(node);
	assert.match(bodyEl.__qwenSmartUi?.resultLead?.textContent ?? "", /还没有可显示的智能文本预览 · 成人向成熟 · 上下文 0/u);
});

test("smart terminal preview renders readable brief lines for structured output", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const bodyEl = makeElement("div");
	const node = {
		properties: {},
		widgets: [{ name: "智能文本输入", value: "一个女孩", inputEl: { value: "一个女孩" } }],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			previewExecutionOutputs: [
				"",
				"",
				"",
				"",
				"",
				"",
				"主体：成年女性，湿发\n场景：浴室蒸汽\n镜头：中景半身\n光影：柔和高光",
			],
			displayPreviewSource: "历史预览",
			displayBodyEl: bodyEl,
			displaySourceEl: makeElement("div"),
			displayMode: "smart",
			library: { slot_config: [] },
		},
		outputs: [],
	};
	exports.refreshStageDisplay(node);
	assert.match(bodyEl.__qwenSmartUi?.resultLead?.textContent ?? "", /智能文本预览/u);
	const formatted = exports.formatStageOutputForReading("主体：成年女性，湿发\n场景：浴室蒸汽\n镜头：中景半身\n光影：柔和高光", "smart");
	assert.match(formatted, /主体：/u);
	assert.match(formatted, /场景：/u);
	assert.match(formatted, /镜头：/u);
	assert.match(formatted, /光影：/u);
});

test("main stage UI avoids lookbehind syntax and derives a native fallback library", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("(?<!"), false);
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		widgets: [
			{ name: "主体标签1", value: "成年女性", options: { values: ["无", "成年女性", "成年男性"] } },
			{ name: "主体标签20", value: "无", options: { values: ["无", "成年女性", "成年男性"] } },
			{ name: "场景背景标签1", value: "雨夜站台", options: { values: ["无", "雨夜站台"] } },
		],
	};
	const library = exports.buildNativePromptLibraryFallback(node);
	assert.equal(JSON.stringify(library.slot_config), JSON.stringify([
		{ name: "主体", slots: 20 },
		{ name: "场景背景", slots: 1 },
	]));
	assert.equal(JSON.stringify(library.tag_library["主体"]["当前节点"]), JSON.stringify(["成年女性", "成年男性"]));
	assert.equal(JSON.stringify(library.tag_library["场景背景"]["当前节点"]), JSON.stringify(["雨夜站台"]));
	assert.equal(library.__native_fallback, true);
});

test("history summary prefers saved prompt text over tag summary when stage output exists", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const item = {
		summary: "标签 12 | 真实感 | 人物角色",
		meta: {
			stageOutput: {
				promptText: "一位成年女性站在雨夜站台，穿着长款大衣与白衬衫，霓虹和冷雾交织在她的轮廓边缘。",
				selectedTags: "模板风格：真实感",
			},
		},
	};
	assert.equal(
		exports.buildHistoryDisplaySummaryText(item),
		"一位成年女性站在雨夜站台，穿着长款大衣与白衬衫，霓虹和冷雾交织在她的轮廓边缘。",
	);
});

test("history summary prepends detected style track when stage output carries it", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const item = {
		summary: "标签 12 | 真实感 | 人物角色",
		meta: {
			stageOutput: {
				promptText: "一位成年女性站在城市天台，晚风拂过发丝，日落逆光勾出侧脸轮廓。",
				styleTrack: "城市天台纪实",
			},
		},
	};
	assert.equal(
		exports.buildHistoryDisplaySummaryText(item),
		"[轨道:城市天台纪实] 一位成年女性站在城市天台，晚风拂过发丝，日落逆光勾出侧脸轮廓。",
	);
});

test("history stage output text includes smart prompt section when available", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const text = exports.buildHistoryStageOutputText({
		promptText: "primary prompt",
		smartText: "smart prompt",
		selectedTags: "标签摘要",
	});
	assert.match(text, /正向提示词/u);
	assert.match(text, /智能文本/u);
	assert.match(text, /smart prompt/u);
});

test("history stage output text includes detected style track when available", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const text = exports.buildHistoryStageOutputText({
		promptText: "primary prompt",
		styleTrack: "山谷圣城史诗",
		selectedTags: "标签摘要",
	});
	assert.match(text, /当前轨道：山谷圣城史诗/u);
});

test("history prompt view reads generated prompt aliases outside meta stage output", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const item = {
		source: "random",
		summary: "随机结果 | 真实感 | 人物角色",
		state: { selected: {}, customTags: [], settings: {} },
		promptText: "一位成年女性站在雨夜站台，霓虹冷雾勾出清晰轮廓。",
		negativePrompt: "low quality",
	};
	const stageOutput = exports.getHistoryStageOutput(item);
	assert.match(stageOutput.promptText, /雨夜站台/u);
	const text = exports.buildHistoryPromptViewText(item);
	assert.match(text, /本次生成提示词/u);
	assert.match(text, /雨夜站台/u);
	assert.doesNotMatch(text, /没有保存完整生成提示词/u);
});

test("history prompt view can borrow related executed prompt for the same state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const state = {
		selected: { "画面风格": ["商业摄影"], "构图视角": ["全景全身"] },
		customTags: ["宝石色调"],
		settings: { "模板风格": "真实感", "主体类型": "人物角色" },
	};
	const node = {
		properties: {
			qwen_te_history_v1: [
				{
					id: "executed-1",
					source: "executed",
					updatedAt: 200,
					favorite: false,
					summary: "运行结果",
					state: exports.clonePresetState(state),
					meta: {
						stageOutput: {
							promptText: "一位成年女性在宝石色调影棚中完成全身商业摄影，姿态稳定，服装轮廓清晰。",
							selectedTags: "商业摄影 | 全景全身",
						},
					},
				},
				{
					id: "random-1",
					source: "random",
					updatedAt: 180,
					favorite: false,
					summary: "随机结果 | 商业摄影 | 人物角色",
					state: exports.clonePresetState(state),
					meta: {},
				},
			],
		},
	};
	const randomItem = exports.getNodeHistory(node).find((item) => item.id === "random-1");
	const related = exports.findRelatedHistoryStageOutput(node, randomItem);
	assert.match(related.promptText, /全身商业摄影/u);
	const text = exports.buildHistoryPromptViewText(randomItem, related);
	assert.match(text, /本次生成提示词/u);
	assert.match(text, /全身商业摄影/u);
});

test("history prompt view can use current linked output when legacy item has only a summary", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const displayNode = {
		id: 204,
		type: "ShowText|pysssss",
		title: "展示文本",
		widgets: [{ name: "text", value: "当前画布展示文本节点里的完整正向提示词。" }],
		widgets_values: [],
	};
	exports.__context.__testApp.graph = {
		_nodes: [displayNode],
		links: { 104: { id: 104, target_id: 204, target_slot: 0 } },
		getNodeById(id) { return Number(id) === 204 ? displayNode : null; },
	};
	const node = {
		id: 100,
		properties: {},
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [],
			directStageOutputCache: null,
			workflowOutputMeta: {},
		},
		outputs: [
			{ links: [] },
			{ links: [104] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
			{ links: [] },
		],
	};
	const item = {
		id: "legacy-summary",
		source: "random",
		updatedAt: 10,
		summary: "随机结果 | 真实感 | 人物角色",
		state: { selected: { "画面风格": ["真实感"] }, customTags: [], settings: {} },
		meta: {},
	};
	const resolved = exports.resolveHistoryPromptViewStageOutput(node, item);
	assert.equal(resolved.sourceKey, "live");
	assert.match(resolved.stageOutput.promptText, /当前画布展示文本节点里的完整正向提示词/u);
	const text = exports.buildHistoryPromptViewText(item, resolved.stageOutput);
	assert.match(text, /本次生成提示词/u);
	assert.doesNotMatch(text, /没有保存完整生成提示词/u);
});

test("recorded execution attaches prompt output to recent matching state history", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "自定义补充标签", value: "" },
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
		],
		[exports.PANEL_KEY]: {
			lastExecutionOutputs: [
				"完整结果全文",
				"一位成年女性在清晨书店门口回望，长外套与柔光形成稳定商业摄影画面。",
				"标签摘要",
				'{"runtime_random_style_track":"商业摄影"}',
				"low quality",
				"提示词合集全文",
				"智能文本提示词",
			],
			directStageOutputCache: null,
			workflowOutputMeta: {},
			library,
		},
		outputs: [],
	};
	assert.equal(exports.recordStageExecution(node, library, null), true);
	const executed = exports.getNodeHistory(node)[0];
	node.properties.qwen_te_history_v1 = [
		{
			id: "random-before-output",
			source: "random",
			updatedAt: 1,
			favorite: false,
			summary: "随机结果 | 真实感 | 人物角色",
			state: exports.clonePresetState(executed.state),
			meta: {},
		},
		...exports.getNodeHistory(node),
	];
	assert.equal(
		exports.attachStageOutputToRecentStateHistory(node, executed.state, executed.meta.stageOutput),
		true,
	);
	const random = exports.getNodeHistory(node).find((item) => item.id === "random-before-output");
	assert.match(random.meta.stageOutput.promptText, /清晨书店/u);
});

test("history prompt view text falls back to state summary for legacy records", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const text = exports.buildHistoryPromptViewText({
		source: "random",
		summary: "随机结果 | 真实感 | 人物角色",
		state: { selected: { "画面风格": ["巴洛克"], "构图视角": ["全景全身"] }, customTags: ["宝石色调"], settings: {} },
		meta: {},
	});
	assert.match(text, /历史记录摘要/u);
	assert.match(text, /随机结果/u);
	assert.match(text, /真实感/u);
	assert.match(text, /没有保存完整生成提示词/u);
});

test("history manager exposes a compact view button for every card", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openHistoryManager");
	const end = source.indexOf("function openExampleDialog", start);
	const historyManager = source.slice(start, end);
	assert.match(historyManager, /viewPrompt\.textContent = "查看"/u);
	assert.match(historyManager, /openHistoryPromptViewDialog\(node, displayItem\)/u);
	assert.match(historyManager, /qwen-te-preset-card__action-row qwen-te-preset-card__action-row--primary/u);
	assert.equal(historyManager.includes("toggleStageDetail"), false);
});

test("history search source includes smart text content", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /stageOutput\?\.\s*smartText/u);
});

test("smart terminal preview highlights structured value chips", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /qwen-te-panel__smart-preview-chip/u);
	assert.match(source, /appendSmartPreviewValue/u);
	assert.match(source, /split\(\s*\/\[，,\s*、\]\//u);
});

test("smart terminal preview gives semantic tone to key brief fields", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /data-smart-key="subject"/u);
	assert.match(source, /data-smart-key="scene"/u);
	assert.match(source, /data-smart-key="lens"/u);
	assert.match(source, /data-smart-key="light"/u);
	assert.match(source, /getSmartPreviewKeyType/u);
});

test("smart text input supports ctrl enter quick match without extra buttons", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /Ctrl\+Enter 快速匹配/u);
	assert.match(source, /event\.key !== "Enter"/u);
	assert.match(source, /runSmartTextMatch\(node, input\.value\)/u);
});

test("smart text match button prevents duplicate queue submissions", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /smartTextMatchRunning/u);
	assert.match(source, /匹配中/u);
	assert.match(source, /button\.disabled = running/u);
	assert.match(source, /if \(node\?\.\[PANEL_KEY\]\?\.smartTextMatchRunning\) return false/u);
	assert.match(source, /const mutationRevision = beginNodeStateMutation\(node\);/u);
	assert.match(source, /if \(!isNodeStateMutationCurrent\(node, mutationRevision\)\) return false;/u);
});

test("smart text automatic extra requirement follows new matches but preserves manual edits", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		id: 19,
		properties: {},
		widgets: [
			{ name: "智能文本匹配", value: false },
			{ name: "智能文本输入", value: "" },
			{ name: "额外要求", value: "" },
		],
	};
	await exports.runSmartTextMatch(node, "第一主题");
	assert.equal(node.widgets.find((widget) => widget.name === "额外要求").value, "第一主题");
	await exports.runSmartTextMatch(node, "第二主题");
	assert.equal(node.widgets.find((widget) => widget.name === "额外要求").value, "第二主题");
	node.widgets.find((widget) => widget.name === "额外要求").value = "人工保留约束";
	await exports.runSmartTextMatch(node, "第三主题");
	assert.equal(node.widgets.find((widget) => widget.name === "额外要求").value, "人工保留约束");
	const sameTextNode = {
		id: 20,
		properties: {},
		widgets: [
			{ name: "智能文本匹配", value: false },
			{ name: "智能文本输入", value: "人工同文" },
			{ name: "额外要求", value: "人工同文" },
		],
	};
	await exports.runSmartTextMatch(sameTextNode, "新主题");
	assert.equal(sameTextNode.widgets.find((widget) => widget.name === "额外要求").value, "人工同文");
});

test("smart text hint reflects running queue state", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /正在写入智能文本并加入队列/u);
	assert.match(source, /updateSmartTextMatchButtonState\(node, ui\.button, ui\.hint\)/u);
	assert.match(source, /hint\.textContent = running/u);
});

test("slot and advanced widget groups restore widgets and request layout refresh", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const dirtyCalls = [];
	exports.__context.__testApp.graph.setDirtyCanvas = (...args) => dirtyCalls.push(args);
	const originalComputeSize = () => [180, 24];
	const widget = {
		name: "主体标签1",
		type: "combo",
		computeSize: originalComputeSize,
		inputEl: { style: {} },
		element: { style: {} },
		hidden: false,
	};
	const node = {
		widgets: [widget],
		size: [240, 100],
		computeSize: () => [360, 180],
		setSize(size) {
			this.size = size;
		},
	};

	assert.equal(exports.setWidgetGroupVisibility(node, ["主体标签1"], false, "Advanced"), 1);
	assert.equal(widget.hidden, true);
	assert.equal(widget.type, "easyHiddenAdvanced");
	assert.deepEqual(Array.from(widget.computeSize()), [0, -4]);
	assert.equal(widget.inputEl.style.display, "none");
	assert.equal(widget.element.style.display, "none");
	assert.equal(widget.options.hidden, true);

	assert.equal(exports.setWidgetGroupVisibility(node, ["主体标签1"], true, "Advanced"), 1);
	assert.equal(widget.hidden, false);
	assert.equal(widget.type, "combo");
	assert.equal(widget.computeSize, originalComputeSize);
	assert.equal(widget.inputEl.style.display, "");
	assert.equal(widget.element.style.display, "");
	assert.equal(Object.prototype.hasOwnProperty.call(widget.options, "hidden"), false);
	assert.deepEqual(Array.from(node.size), [360, 180]);
	assert.equal(dirtyCalls.length > 0, true);
});

test("main panel reconciles native widgets inserted after panel initialization", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const makeWidget = (name) => ({
		name,
		type: "combo",
		value: "无",
		options: {},
		hidden: false,
		computeSize: () => [180, 24],
		inputEl: { style: {} },
		element: { style: {} },
	});
	const lateRaw = makeWidget("主体标签15");
	const lateAdvanced = makeWidget("模型来源");
	const preserved = makeWidget("首条正向提示词");
	const node = {
		widgets: [lateRaw, lateAdvanced, preserved],
		size: [560, 240],
		computeSize: () => [560, 240],
		setSize(size) { this.size = size; },
	};
	node[exports.PANEL_KEY] = {
		ready: true,
		library: { slot_config: [{ name: "主体", slots: 20 }] },
		rawTagWidgetNames: Array.from({ length: 20 }, (_, index) => `主体标签${index + 1}`),
	};

	assert.equal(exports.reconcileStagePanelNativeWidgets(node), 2);
	for (const widget of [lateRaw, lateAdvanced]) {
		assert.equal(widget.hidden, true);
		assert.equal(widget.options.hidden, true);
		assert.equal(widget.inputEl.style.display, "none");
		assert.deepEqual(Array.from(widget.computeSize()), [0, -4]);
	}
	assert.equal(preserved.hidden, false);
	assert.equal(exports.reconcileStagePanelNativeWidgets(node), 0);
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /if \(panelState\) reconcileStagePanelNativeWidgets\(node\);/u);
	assert.match(source, /if \(this\[PANEL_KEY\]\?\.ready && !this\[NODE_REMOVED_KEY\]\) reconcileStagePanelNativeWidgets\(this\);/u);
});

test("quickbar slot toggle uses compact slot panel instead of raw widget stack", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('const slotPanel = buildLazySlotPanel(library); mainWorkspace.appendChild(slotPanel);'), true);
	assert.equal(source.includes('setWidgetGroupVisibility(node, node[PANEL_KEY]?.rawTagWidgetNames ?? rawTagWidgetNames, false, "Raw")'), true);
	assert.equal(source.includes("setSlotPanelVisible(node, hiddenState.showRawTags)"), true);
	assert.equal(source.includes('setPanelToggleButtonState(rawToggleButton, hiddenState.showRawTags, "收槽位", "槽位")'), true);
	assert.equal(source.includes("已展开槽位设置面板。"), true);
	assert.equal(source.includes("没有找到可展开的槽位设置面板。"), true);
});

test("slot panel groups raw tag widgets into compact cards", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("function buildSlotPanel(node, library)"), true);
	assert.equal(source.includes('panel.className = "qwen-te-panel__slots qwen-te-hidden"'), true);
	assert.equal(source.includes("qwen-te-panel__slot-card"), true);
	assert.equal(source.includes("qwen-te-panel__slot-select"), true);
	assert.equal(source.includes("qwen-te-panel__slot-custom"), true);
	assert.equal(source.includes("refreshSlotPanel(node)"), true);
});

test("slot inputs use shared datalists while model selects keep dark menus", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes(".qwen-te-panel__slot-select,.qwen-te-model__select{color-scheme:dark}"), true);
	assert.equal(source.includes(".qwen-te-model__select option,.qwen-te-model__select optgroup{background-color:#101923!important;color:#e6f0ff!important}"), true);
	assert.equal(source.includes("function createSlotDatalist(options, listId)"), true);
	assert.equal(source.includes('input.setAttribute("list", listId)'), true);
});

test("slot panel defers DOM creation and shares one option list per group", async () => {
	const ElementLike = class {
		static [Symbol.hasInstance](value) {
			return !!value?.tagName;
		}
	};
	const exports = await loadUiExports("http://127.0.0.1:8188/", { HTMLElement: ElementLike });
	const library = {
		slot_config: [{ name: "主体", slots: 2 }],
		tag_library: { 主体: ["成年女性", "成年男性"] },
	};
	const node = {
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "主体标签2", value: "成年女性" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const panel = exports.buildLazySlotPanel(library);
	assert.equal(panel.children.length, 0);
	exports.populateSlotPanel(panel, node, library);

	const allElements = [];
	const visit = (element) => {
		allElements.push(element);
		for (const child of element.children ?? []) visit(child);
	};
	visit(panel);
	assert.equal(allElements.filter((element) => element.tagName === "DATALIST").length, 1);
	assert.equal(allElements.filter((element) => element.tagName === "OPTION").length, 3);
	const inputs = allElements.filter((element) => element.tagName === "INPUT");
	assert.equal(inputs.length, 2);
	assert.equal(allElements.filter((element) => element.tagName === "SELECT").length, 0);
	inputs[0].value = "成年男性";
	inputs[0].__listeners.get("input")();
	assert.equal(node.widgets[0].value, "成年男性");
	inputs[0].value = "不在库里的标签";
	inputs[0].__listeners.get("input")();
	assert.equal(node.widgets[0].value, "成年男性");
});

test("slot panel library signatures and options track tag additions and deletions", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const initial = { slot_config: [{ name: "光影氛围", slots: 1 }], tag_library: { 光影氛围: ["柔光"] } };
	const added = { slot_config: [{ name: "光影氛围", slots: 1 }], tag_library: { 光影氛围: ["柔光", "饱满色彩"] } };
	const removed = { slot_config: [{ name: "光影氛围", slots: 1 }], tag_library: { 光影氛围: ["饱满色彩"] } };
	assert.deepEqual(Array.from(exports.getSlotPanelGroupValues(initial, "光影氛围")), ["无", "柔光"]);
	assert.deepEqual(Array.from(exports.getSlotPanelGroupValues(added, "光影氛围")), ["无", "柔光", "饱满色彩"]);
	assert.deepEqual(Array.from(exports.getSlotPanelGroupValues(removed, "光影氛围")), ["无", "饱满色彩"]);
	assert.notEqual(exports.getSlotPanelLibrarySignature(initial), exports.getSlotPanelLibrarySignature(added));
	assert.notEqual(exports.getSlotPanelLibrarySignature(added), exports.getSlotPanelLibrarySignature(removed));
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.match(source, /function replaceSlotPanelForLibrary/u);
	assert.match(source, /panel = replaceSlotPanelForLibrary\(node, panelState\?\.library/u);
	assert.match(source, /if \(!hasPromptLibraryContent\(library\)\)/u);
});

test("slot panel uses compact one-row group layout", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes(".qwen-te-panel__slots{display:flex;flex-direction:column"), true);
	assert.equal(source.includes("max-height:clamp(280px,52vh,480px);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain"), true);
	assert.equal(source.includes(".qwen-te-panel__slot-card{border:1px solid rgba(83,103,130,.44);border-radius:12px"), true);
	assert.equal(source.includes(".qwen-te-panel__slot-card{border:1px solid rgba(83,103,130,.44);border-radius:12px;background:linear-gradient(180deg,rgba(25,35,47,.88),rgba(16,23,32,.94));padding:7px;display:flex;flex-direction:column"), true);
	assert.equal(source.includes(".qwen-te-panel__slot-body{display:grid;grid-template-columns:repeat(auto-fit,minmax(82px,1fr))"), true);
	assert.equal(source.includes(".qwen-te-panel__slot-label{display:none}"), true);
	assert.equal(source.includes("input.title = widgetName;"), true);
	assert.equal(source.includes('panel.addEventListener("wheel", stopCanvasWheelEvent, { passive: true })'), true);
	assert.equal(source.includes('child.classList?.contains("qwen-te-panel__slots")'), true);
	assert.equal(source.includes('label.textContent = `槽 ${index}`'), false);
});

test("quickbar advanced toggle uses stable Advanced hiding state", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('const advancedPanel = buildAdvancedPanel(node); mainWorkspace.appendChild(advancedPanel);'), true);
	assert.equal(source.includes('setWidgetGroupVisibility(node, [...CONTROL_WIDGET_NAMES, ...ADVANCED_WIDGET_NAMES], false, "Advanced")'), true);
	assert.equal(source.includes("setAdvancedPanelVisible(node, hiddenState.showAdvanced)"), true);
	assert.equal(source.includes('setPanelToggleButtonState(advancedToggleButton, hiddenState.showAdvanced, "收高级", "高级")'), true);
	assert.equal(source.includes("已展开高级设置面板。"), true);
	assert.equal(source.includes("没有找到可展开的高级设置面板。"), true);
	const advancedStart = source.indexOf("const ADVANCED_WIDGET_NAMES = [");
	const advancedEnd = source.indexOf("];", advancedStart);
	const advancedList = source.slice(advancedStart, advancedEnd);
	assert.equal(advancedList.includes("STAGE_EMBEDDED_MODEL_WIDGET_NAMES"), false);
	const hiddenStart = source.indexOf("const ALWAYS_HIDDEN_WIDGET_NAMES = [");
	const hiddenEnd = source.indexOf("];", hiddenStart);
	const hiddenList = source.slice(hiddenStart, hiddenEnd);
	for (const hiddenName of [
		"RANDOM_DEDUPE_CACHE_WIDGET_NAME",
		"PROMPT_DEDUPE_CACHE_WIDGET_NAME",
		"RUNTIME_RANDOM_PROTECTED_TAGS_WIDGET_NAME",
		"RUNTIME_RANDOM_PREVIEW_TOKEN_WIDGET_NAME",
		"STAGE_EMBEDDED_MODEL_WIDGET_NAMES",
	]) assert.equal(hiddenList.includes(hiddenName), true, `${hiddenName} should stay hidden`);
});

test("advanced panel groups expert controls into compact cards", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("const ADVANCED_PANEL_SECTIONS = ["), true);
	for (const title of ["生成策略", "随机控制", "智能文本", "模型采样"]) {
		assert.equal(source.includes(`title: "${title}"`), true, `${title} section should exist`);
	}
	assert.equal(source.includes('className = "qwen-te-panel__advanced qwen-te-hidden"'), true);
	assert.equal(source.includes("qwen-te-panel__advanced-card--wide"), true);
	assert.equal(source.includes("qwen-te-panel__advanced-input"), true);
	assert.equal(source.includes("refreshAdvancedPanel(node)"), true);
});

test("legacy ten-slot workflows insert expanded tag defaults without shifting later settings", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const widgetNames = [
		"模板风格",
		...Array.from({ length: 20 }, (_value, index) => `主体标签${index + 1}`),
		...Array.from({ length: 20 }, (_value, index) => `场景背景标签${index + 1}`),
		"提示词语言",
	];
	const node = { properties: {}, widgets: widgetNames.map((name) => ({ name, value: /标签\d+$/u.test(name) ? "无" : `默认:${name}` })) };
	const legacyValues = [
		"真实感",
		...Array.from({ length: 10 }, (_value, index) => index === 0 ? "成年女性" : "无"),
		...Array.from({ length: 10 }, (_value, index) => index === 0 ? "雨夜街道" : "无"),
		"纯中文",
	];
	const normalized = exports.normalizeLegacyWidgetValues(node, legacyValues);
	assert.equal(normalized.length, widgetNames.length);
	assert.equal(normalized[1], "成年女性");
	assert.equal(normalized[11], "无");
	assert.equal(normalized[21], "雨夜街道");
	assert.equal(normalized.at(-1), "纯中文");
});

test("tag selection capacity is bounded, removable, and reported per group", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [{ name: "主体", slots: 20 }] };
	const selected = { 主体: Array.from({ length: 20 }, (_value, index) => `标签${index + 1}`) };
	assert.equal(exports.getTagGroupSlotLimit(library, "主体"), 20);
	assert.equal(exports.normalizeTagGroupSlotLimit(500, 0), 32);
	assert.deepEqual(
		Object.fromEntries(Object.entries(exports.toggleBoundedTagSelection(selected, "主体", "超额标签", 20))),
		{ changed: false, reason: "full", count: 20, limit: 20 },
	);
	assert.equal(exports.toggleBoundedTagSelection(selected, "主体", "标签20", 20).reason, "removed");
	assert.equal(exports.toggleBoundedTagSelection(selected, "主体", "替补标签", 20).reason, "added");
	assert.equal(selected.主体.length, 20);
	assert.equal(exports.getRuntimeRandomAdditionCap(0, 20, "强"), 10);
	assert.equal(exports.getRuntimeRandomAdditionCap(0, 20, "强 / 极限拉开"), 10);
});

test("advanced panel merges full backend catalogs and renders long enums as selects", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const backendStyles = [
		"自动",
		...Array.from({ length: 90 }, (_value, index) => `扩展风格${index + 1}`),
		"宇宙神话",
	];
	const node = {
		widgets: [{ name: "模板风格", value: "宇宙神话", options: { values: backendStyles } }],
	};
	const options = exports.getAdvancedWidgetOptions(node, "模板风格");
	assert.equal(options.some((option) => option.value === "商业摄影"), true);
	assert.equal(options.some((option) => option.value === "宇宙神话"), true);
	assert.ok(options.length >= 90);

	const select = exports.createAdvancedSelect(node, "模板风格", options);
	assert.equal(select.tagName, "SELECT");
	assert.equal(select.className, "qwen-te-panel__advanced-select");
	assert.equal(select.value, "宇宙神话");
	assert.ok(select.children.length >= 90);
	node.widgets[0].options.tooltip = "选择整体视觉风格";
	const describedSelect = exports.createAdvancedSelect(node, "模板风格", options);
	assert.equal(exports.getAdvancedWidgetTooltip(node, "模板风格"), "选择整体视觉风格");
	assert.equal(describedSelect.title, "选择整体视觉风格");
	assert.equal(exports.ADVANCED_WIDGET_NAMES.includes("风格隔离策略"), true);
	assert.equal(exports.ADVANCED_WIDGET_NAMES.includes("智能文本风格优先"), true);
	assert.deepEqual(Array.from(exports.CONTROL_WIDGET_OPTIONS["输出模式"]), ["完整结果", "仅提示词优先"]);
	assert.equal(
		exports.CONTROL_WIDGET_OPTIONS["运行时随机强度"].some((option) => option.value === "强 / 极限拉开"),
		true,
	);
});

test("advanced panel stays readable in narrow node width", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes(".qwen-te-panel__advanced{display:flex;flex-direction:column"), true);
	assert.equal(source.includes("max-height:clamp(260px,52vh,520px)"), true);
	assert.equal(source.includes(".qwen-te-panel__advanced-scroll{display:flex;flex-direction:column;gap:9px"), true);
	assert.equal(source.includes("overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain"), true);
	assert.equal(source.includes('scroll.className = "qwen-te-panel__advanced-scroll"'), true);
	assert.equal(source.includes('scroll.addEventListener("wheel", stopCanvasWheelEvent, { passive: true })'), true);
	assert.equal(source.includes('scroll.appendChild(card)'), true);
	assert.equal(source.includes(".qwen-te-panel__advanced-row{display:flex;flex-direction:column"), true);
	assert.equal(source.includes("function getAdvancedOptionColumnCount"), true);
	assert.equal(source.includes("getAdvancedOptionColumnCount(name, options)"), true);
	assert.equal(source.includes("grid-template-columns:repeat(var(--qwen-te-advanced-cols,2),minmax(0,1fr))"), true);
	assert.equal(source.includes("grid-template-columns:repeat(var(--qwen-te-advanced-cols,4),minmax(0,1fr))"), false);
});

test("advanced panel collapses secondary groups by default", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("for (const [sectionIndex, section] of ADVANCED_PANEL_SECTIONS.entries())"), true);
	assert.equal(source.includes('if (sectionIndex > 0) card.classList.add("is-collapsed")'), true);
	assert.equal(source.includes('toggle.textContent = sectionIndex > 0 ? "展开" : "收起"'), true);
	assert.equal(source.includes('const collapsed = card.classList.toggle("is-collapsed")'), true);
	assert.equal(source.includes(".qwen-te-panel__advanced-card.is-collapsed .qwen-te-panel__advanced-body{display:none}"), true);
});

test("tag preset and history dialogs keep secondary tools out of the primary flow", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('presetTitle.textContent = "生产模板"'), false);
	assert.equal(source.includes('const batchBar = document.createElement("details")'), true);
	assert.equal(source.includes('batchSummary.textContent = "预设工具（可选）"'), true);
	assert.equal(source.includes('continuousCountWrap.classList.add("qwen-te-hidden")'), true);
	assert.equal(source.includes('batchCycleButton.classList.add("qwen-te-hidden")'), false);
	assert.equal(source.includes('for (const button of [batchCycleButton, batchCycleQueueButton, batchRandomLoadButton, batchRandomQueueButton, batchRandomRunButton])'), true);
	assert.equal(source.includes('const historyTools = document.createElement("details")'), true);
	assert.equal(source.includes('historyToolsSummary.textContent = "历史工具（可选）"'), true);
	assert.equal(source.includes('addBatch.classList.add("qwen-te-hidden")'), true);
	assert.equal(source.includes('clearButton.textContent="清空历史"'), false);
	assert.equal(source.includes("标签面板里的生产模板"), false);
});

test("preset manager keeps the default flow focused on reusable production presets", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openPresetManager");
	const end = source.indexOf("function openHistoryManager", start);
	const presetManager = source.slice(start, end);
	assert.equal(presetManager.includes('savePanelDesc.textContent = "把当前标签与参数存成常用方案，后续一键载入或直接运行。"'), true);
	assert.equal(presetManager.includes('saveButton.textContent = "保存为预设"'), true);
	assert.equal(presetManager.includes('quickImportButton.textContent = "导入预设"'), true);
	assert.equal(presetManager.includes('batchBar.classList.toggle("qwen-te-hidden", !hasAnyPreset)'), true);
	assert.equal(presetManager.includes('filterSurface.classList.toggle("qwen-te-hidden", !hasAnyPreset)'), true);
	assert.equal(presetManager.includes('searchInput.placeholder = "搜索预设名称 / 来源 / 摘要"'), true);
	assert.equal(presetManager.includes('loadRun.textContent = "载入并运行"'), true);
	assert.equal(presetManager.includes('const visiblePresetFilterKeys = ["all", "favorites", "manual", "arrange-preview"]'), true);
	assert.equal(presetManager.includes('const hiddenPresetSourceKinds = new Set(["history-aggregate", "single-preset"])'), true);
	assert.equal(presetManager.includes('reportSurface.classList.add("qwen-te-hidden")'), true);
	assert.equal(presetManager.includes('batchContinuousSection.classList.add("qwen-te-hidden")'), true);
	assert.equal(presetManager.includes('exportHistoryAggregateButton.classList.add("qwen-te-hidden")'), true);
	for (const text of ['"history_aggregate_rate_desc"', '"history_aggregate_risk_desc"', '"source_then_updated"', 'runExclusive.textContent = "唯一并开跑"', 'saveReportHistory.textContent = "报告入历史"']) {
		assert.equal(presetManager.includes(text), false, `${text} should not be in the simplified preset manager`);
	}
});

test("example dialog uses direct practical cards with apply and run actions", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	const start = source.indexOf("function openExampleDialog");
	const end = source.indexOf("function openTagManager", start);
	const exampleDialog = source.slice(start, end);
	assert.equal(exampleDialog.includes('title.textContent = "示例锚点"'), true);
	assert.equal(exampleDialog.includes('listTitle.textContent = "可用示例"'), true);
	assert.equal(exampleDialog.includes('const renderPresetCard = (preset, options = {})'), true);
	assert.equal(exampleDialog.includes('applyNowButton.textContent = "应用"'), true);
	assert.equal(exampleDialog.includes('runButton.textContent = "应用并运行"'), true);
	assert.equal(exampleDialog.includes('applyButton.textContent = "应用选中"'), true);
	assert.equal(exampleDialog.includes('applyRunButton.textContent = "选中并运行"'), true);
	assert.equal(exampleDialog.includes("const applySelectedExample = async (options = {})"), true);
	assert.equal(exampleDialog.includes("queueWorkflowFromNode(node)"), true);
	assert.equal(exampleDialog.includes('recommendedCard'), false);
	assert.equal(exampleDialog.includes('title.textContent = "当前推荐"'), false);
	assert.equal(exampleDialog.includes('filterSummary.textContent = "高级筛选（可选）"'), false);
	assert.equal(exampleDialog.includes('variantTitle.textContent = "同家族变体"'), false);
});

test("example dialog includes role scene and colossus example anchors", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	for (const name of ["城市天台晚风纪实", "山谷圣城巨构", "工业树灵巨像"]) {
		assert.equal(source.includes(name), true, `${name} should be available as an example anchor`);
	}
	assert.equal(source.includes('"场景"'), true);
	assert.equal(source.includes('"巨物"'), true);
});

test("example recommendation prefers non-human scene and colossus anchors", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const availablePresets = [
		{ name: "中画幅通勤大片", tags: ["真实感", "成年女性"], meta: { use_cases: ["人像", "女性向"] } },
		{ name: "山谷圣城巨构", tags: ["神话感", "山谷圣城", "巨构神殿"], meta: { use_cases: ["场景", "神话"] } },
		{ name: "工业树灵巨像", tags: ["CG感", "树灵巨像", "工业舱室"], meta: { use_cases: ["巨物", "CG科幻"] } },
	];
	const scenePick = exports.inferBestExamplePreset(availablePresets, "神话感", {
		selected: { 主体: ["非人物主体"], 场景背景: ["山谷圣城"], 画面风格: ["神话感"] },
		customTags: ["巨构神殿"],
		settings: { "主体类型": "非人物主体" },
	});
	assert.equal(scenePick?.name, "山谷圣城巨构");
	const colossusPick = exports.inferBestExamplePreset(availablePresets, "CG感", {
		selected: { 主体: ["树灵巨像"], 场景背景: ["工业舱室"], 画面风格: ["CG感"] },
		customTags: ["朽木树皮纹理"],
		settings: { "主体类型": "非人物主体" },
	});
	assert.equal(colossusPick?.name, "工业树灵巨像");
});

test("example recommendation gives scene and colossus dedicated sampling hints", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const sceneHints = exports.inferPresetRecommendation({
		name: "山谷圣城巨构",
		tags: ["神话感", "山谷圣城", "巨构神殿", "超广角全景"],
		meta: { use_cases: ["场景", "神话"] },
	});
	const monsterHints = exports.inferPresetRecommendation({
		name: "工业树灵巨像",
		tags: ["CG感", "树灵巨像", "工业舱室", "巨物压迫近景"],
		meta: { use_cases: ["巨物", "CG科幻"] },
	});
	assert.equal(sceneHints.find((item) => item.label === "建议步数")?.value, "32-40");
	assert.match(sceneHints.find((item) => item.label === "稳定提醒")?.value ?? "", /空间尺度/u);
	assert.equal(monsterHints.find((item) => item.label === "建议步数")?.value, "30-38");
	assert.match(monsterHints.find((item) => item.label === "稳定提醒")?.value ?? "", /巨物体量/u);
});

test("nsfw workspace helpers are exposed in stage UI module", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(typeof exports.applyNodeState, "function");
	assert.equal(typeof exports.openNsfwWorkspaceDialog, "function");
	assert.equal(typeof exports.applyNsfwWorkspaceResultToNodeState, "function");
	assert.equal(typeof exports.persistNsfwWorkspaceToggleToNodeState, "function");
	assert.equal(typeof exports.getNodeNsfwWorkspaceState, "function");
	assert.equal(typeof exports.buildNsfwWorkspaceMappedState, "function");
	assert.equal(typeof exports.buildNsfwWorkspaceNegativeSyncPlan, "function");
	assert.equal(typeof exports.addNsfwCustomFieldOptions, "function");
});

test("nsfw presets fill empty fields without replacing manual selections", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const catalog = {
		presets: {
			测试预设: {
				scene: "预设场景",
				action: "预设动作",
				outfit: "预设服装",
			},
		},
		options: {},
	};
	const effective = exports.resolveNsfwEffectiveWorkspace({
		preset: "测试预设",
		random_mode: "关闭",
		scene: "手工场景",
		action: "——",
		outfit: "手工服装",
	}, catalog);
	assert.equal(effective.scene, "手工场景");
	assert.equal(effective.action, "预设动作");
	assert.equal(effective.outfit, "手工服装");
});

test("nsfw random nonce is cloned, deterministic, and rotates frontend selection", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const catalog = {
		presets: {},
		options: { scene: ["——", "甲", "乙", "丙", "丁"] },
	};
	const workspace = {
		preset: "——",
		quality_tier: "高质量",
		negative_preset: "标准负面提示词",
		random_mode: "场景随机",
		trigger_words: ["护士", "女仆", "护士"],
		random_nonce: "nonce-1",
	};
	const cloned = exports.cloneNsfwWorkspaceState(workspace);
	const first = exports.resolveNsfwEffectiveWorkspace(cloned, catalog).scene;
	const second = exports.resolveNsfwEffectiveWorkspace(exports.cloneNsfwWorkspaceState(workspace), catalog).scene;
	const rotated = new Set();
	for (let index = 0; index < 12; index += 1) {
		rotated.add(exports.resolveNsfwEffectiveWorkspace({ ...workspace, random_nonce: `nonce-${index}` }, catalog).scene);
	}
	assert.equal(cloned.random_nonce, "nonce-1");
	assert.equal(first, "丁");
	assert.equal(second, first);
	assert.ok(rotated.size > 1);
});

test("nsfw workspace migrates legacy camelCase fields and preserves workspace custom tags", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const cloned = exports.cloneNsfwWorkspaceState({
		randomMode: "全部随机",
		randomNonce: "legacy-nonce",
		qualityTier: "大师级",
		negativePreset: "高质量负面提示词",
		negativeApplyMode: "append",
		cameraAngle: "低角度",
		workspaceCustomTags: ["自定义氛围", "自定义氛围", "镜面材质"],
	});
	assert.equal(cloned.random_mode, "全部随机");
	assert.equal(cloned.random_nonce, "legacy-nonce");
	assert.equal(cloned.quality_tier, "大师级");
	assert.equal(cloned.negative_preset, "高质量负面提示词");
	assert.equal(cloned.negative_apply_mode, "append");
	assert.equal(cloned.camera_angle, "低角度");
	assert.deepEqual(Array.from(cloned.workspace_custom_tags), ["自定义氛围", "镜面材质"]);
	const mapped = exports.buildNsfwWorkspaceMappedState(
		{ properties: {}, widgets: [] },
		{ slot_config: [], tag_library: {} },
		cloned,
		{ 高质量负面提示词: "low quality" },
	);
	assert.equal(mapped.custom_tags.includes("自定义氛围"), true);
	assert.equal(mapped.custom_tags.includes("镜面材质"), true);
});

test("nsfw workspace clone whitelists and bounds untrusted workflow state", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const hugeTerms = Array.from({ length: 700 }, (_, index) => `词-${index}-${"长".repeat(600)}`);
	const appliedSelection = Object.fromEntries(Array.from({ length: 100 }, (_, index) => [
		`超长分组-${index}-${"组".repeat(180)}`,
		hugeTerms,
	]));
	const cloned = exports.cloneNsfwWorkspaceState({
		enabled: "true",
		trigger_words: hugeTerms,
		workspace_custom_tags: hugeTerms,
		custom_negative: "负".repeat(40000),
		custom_prefix: "前".repeat(1000),
		custom_suffix: "后".repeat(1000),
		scene: "场".repeat(3000),
		applied_custom_tags: hugeTerms.slice(0, 10),
		manual_custom_tags: hugeTerms.slice(10, 20),
		applied_selected_tags: appliedSelection,
		unknown_blob: "x".repeat(300000),
		unknown_object: { nested: hugeTerms },
	});
	assert.equal(cloned.enabled, true);
	assert.equal(Object.hasOwn(cloned, "unknown_blob"), false);
	assert.equal(Object.hasOwn(cloned, "unknown_object"), false);
	assert.ok(cloned.custom_negative.length <= 32768);
	assert.ok(cloned.custom_prefix.length <= 512);
	assert.ok(cloned.custom_suffix.length <= 512);
	assert.ok(cloned.scene.length <= 2048);
	for (const field of ["trigger_words", "workspace_custom_tags", "applied_custom_tags", "manual_custom_tags"]) {
		assert.ok((cloned[field] ?? []).length <= 128, `${field} should be bounded`);
		assert.equal((cloned[field] ?? []).every((term) => term.length <= 512), true);
	}
	const selectedGroups = Object.entries(cloned.applied_selected_tags ?? {});
	assert.ok(selectedGroups.length <= 64);
	assert.ok(selectedGroups.reduce((count, [, tags]) => count + tags.length, 0) <= 256);
	for (const [groupName, tags] of selectedGroups) {
		assert.ok(groupName.length <= 128);
		assert.ok(tags.length <= 128);
		assert.equal(tags.every((term) => term.length <= 512), true);
	}
	assert.ok(Buffer.byteLength(JSON.stringify(cloned), "utf8") <= 128 * 1024);

	const restore = exports.cloneNsfwWorkspaceState({
		generationProfileRestore: {
			original: { "模板风格": "风".repeat(5000), 未知设置: "不得保留" },
			applied: { "模板风格": "真实感", 未知设置: "不得保留" },
		},
		user_custom_tags: hugeTerms,
	});
	assert.ok(restore.generation_profile_restore.original["模板风格"].length <= 2048);
	assert.equal(Object.hasOwn(restore.generation_profile_restore.original, "未知设置"), false);
	assert.equal(Object.hasOwn(restore, "user_custom_tags"), false);
	assert.ok(restore.manual_custom_tags.length <= 128);
	assert.ok(Buffer.byteLength(JSON.stringify(restore), "utf8") <= 128 * 1024);

	const source = await fs.readFile(UI_PATH, "utf8");
	const cloneStart = source.indexOf("function cloneNsfwWorkspaceState");
	const cloneEnd = source.indexOf("function resolveNsfwWorkspaceCatalog", cloneStart);
	const cloneSource = source.slice(cloneStart, cloneEnd);
	assert.doesNotMatch(cloneSource, /source\s*=\s*\{\s*\.\.\.rawSource/u);
	assert.doesNotMatch(cloneSource, /value\.join\(/u);
});

test("nsfw writeback nonce reuses a preview once and rotates on the next direct action", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const workspace = { random_mode: "场景随机", random_nonce: "" };
	const previewNonce = exports.prepareNsfwRandomNonceForWriteback(workspace, false);
	const writebackNonce = exports.prepareNsfwRandomNonceForWriteback(workspace, true);
	const nextDirectNonce = exports.prepareNsfwRandomNonceForWriteback(workspace, false);
	assert.ok(previewNonce);
	assert.equal(writebackNonce, previewNonce);
	assert.notEqual(nextDirectNonce, previewNonce);
});

test("nsfw custom field library stores deduped local options", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	exports.setNsfwCustomFieldLibrary({});
	const added = exports.addNsfwCustomFieldOptions("scene", "浴室\n浴室\n镜前");
	assert.equal(added.ok, true);
	assert.equal(added.added, 2);
	assert.equal(added.skipped, 0);
	assert.deepEqual(Array.from(exports.getNsfwCustomFieldOptions("scene")), ["浴室", "镜前"]);
	const removed = exports.removeNsfwCustomFieldOption("scene", "浴室");
	assert.equal(removed.removed, true);
	assert.deepEqual(Array.from(exports.getNsfwCustomFieldOptions("scene")), ["镜前"]);
});

test("nsfw custom field library enforces entry limits and reports quota failures", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	exports.setNsfwCustomFieldLibrary({});
	const manyEntries = Array.from({ length: 100 }, (_, index) => `场景-${index}`).join("\n");
	const bounded = exports.addNsfwCustomFieldOptions("scene", `${manyEntries}\n${"过长".repeat(200)}`);
	assert.equal(bounded.ok, true);
	assert.equal(bounded.added, 80);
	assert.ok(bounded.skipped >= 21);
	assert.equal(exports.getNsfwCustomFieldOptions("scene").length, 80);
	exports.__context.localStorage.setItem = () => { throw new Error("QuotaExceededError"); };
	const failed = exports.addNsfwCustomFieldOptions("action", "新的动作");
	assert.equal(failed.ok, false);
	assert.equal(failed.reason, "storage");
	assert.equal(failed.added, 0);
});

test("nsfw workspace enable toggle persists and syncs quickbar button", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const button = makeElement("button");
	const label = makeElement("span");
	button.attributes = {};
	button.querySelector = (selector) => selector === ".qwen-te-panel__button-label" ? label : null;
	button.setAttribute = (name, value) => { button.attributes[name] = String(value); };
	const node = {
		properties: {},
		widgets: [],
		[exports.PANEL_KEY]: {
			library,
			panelButtons: { nsfwWorkspace: button },
		},
	};
	const ok = exports.persistNsfwWorkspaceToggleToNodeState(node, library, { scene: "浴室" }, true);
	assert.equal(ok, true);
	assert.equal(node.properties.nsfw_workspace.enabled, true);
	assert.equal(node.properties.nsfwWorkspace.enabled, true);
	assert.equal(exports.getNodeNsfwWorkspaceState(node, library).enabled, true);
	assert.equal(label.textContent, "NSFW开");
	assert.equal(button.classList.contains("is-active"), true);
	assert.equal(button.attributes["aria-pressed"], "true");
});

test("mini toolbar bridge exposes nsfw workspace action", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/?qwen_te_mini=1");
	assert.equal(typeof exports.registerStagePromptMiniBridge, "function");
	exports.registerStagePromptMiniBridge();
	assert.equal(typeof exports.__context.__QWEN_TE_STAGE_OPEN_NSFW_WORKSPACE__, "function");
});

test("applyNsfwWorkspaceResultToNodeState replaces prior NSFW-derived custom tags", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 2 }, { name: "场景背景", slots: 2 }],
		tag_library: {
			主体: { default: ["女仆", "护士"] },
			场景背景: { default: ["卧室", "摄影棚"] },
		},
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["女仆"],
				scene: "卧室",
				negative_preset: "标准负面提示词",
			},
		},
		widgets: [
			{ name: "主体标签1", value: "女仆" },
			{ name: "主体标签2", value: "无" },
			{ name: "场景背景标签1", value: "卧室" },
			{ name: "场景背景标签2", value: "无" },
			{ name: "自定义补充标签", value: "女仆, 卧室" },
		],
	};
	const firstMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["女仆"],
		scene: "卧室",
		custom_prefix: "红色灯光",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	const appliedFirst = exports.applyNsfwWorkspaceResultToNodeState(node, library, firstMapped);
	assert.equal(appliedFirst, true);
	assert.equal(node.widgets.find((widget) => widget.name === "自定义补充标签").value.includes("红色灯光"), true);
	const secondMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["护士"],
		scene: "摄影棚",
		custom_prefix: "蓝色布景",
		negative_preset: "WAN视频负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
		"WAN视频负面提示词": "色调艳丽，过曝，静态，细节模糊不清，字幕",
	});
	const appliedSecond = exports.applyNsfwWorkspaceResultToNodeState(node, library, secondMapped);
	assert.equal(appliedSecond, true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("红色灯光"), false);
	assert.equal(customText.includes("蓝色布景"), true);
	assert.equal(customText.includes("女仆"), false);
	assert.equal(customText.includes("护士"), true);
});

test("applyNsfwWorkspaceResultToNodeState enables workspace on writeback", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [],
		tag_library: {},
		nsfw_workspace_catalog: {
			defaults: {
				enabled: false,
				negative_apply_mode: "preview",
				negative_preset: "标准负面提示词",
			},
			negative_presets: {},
		},
	};
	const node = { properties: {}, widgets: [] };
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: false,
		trigger_words: ["女仆"],
		negative_preset: "标准负面提示词",
	});
	assert.equal(mapped.nsfw_workspace.enabled, false);
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	assert.equal(node.properties.nsfw_workspace.enabled, true);
	assert.equal(node.properties.nsfwWorkspace.enabled, true);
});

test("repeated nsfw writeback preserves selected-tag provenance for disable", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 2 }],
		tag_library: { 主体: { default: ["女仆", "护士"] } },
	};
	const node = {
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "主体标签2", value: "无" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	for (let index = 0; index < 2; index += 1) {
		const mapped = exports.buildNsfwWorkspaceMappedState(node, library, { enabled: true, trigger_words: ["女仆"] });
		assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	}
	assert.deepEqual(Array.from(node.properties.nsfw_workspace.applied_selected_tags["主体"]), ["女仆"]);
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	assert.equal(node.widgets.some((widget) => widget.name.startsWith("主体标签") && widget.value === "女仆"), false);
});

test("nsfw writeback replaces prior workspace-owned selected tags", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 2 }],
		tag_library: { 主体: { default: ["女仆", "护士"] } },
	};
	const node = {
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "主体标签2", value: "无" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	let mapped = exports.buildNsfwWorkspaceMappedState(node, library, { enabled: true, trigger_words: ["女仆"] });
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	mapped = exports.buildNsfwWorkspaceMappedState(node, library, { enabled: true, trigger_words: ["护士"] });
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	const subjectValues = node.widgets.filter((widget) => widget.name.startsWith("主体标签")).map((widget) => widget.value);
	assert.equal(subjectValues.includes("女仆"), false);
	assert.equal(subjectValues.includes("护士"), true);
	assert.deepEqual(Array.from(node.properties.nsfw_workspace.applied_selected_tags["主体"]), ["护士"]);
});

test("local rewrite subject-scene random fallback leaves unrelated groups empty", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [
			{ name: "主体", slots: 1 },
			{ name: "场景背景", slots: 1 },
			{ name: "画面风格", slots: 1 },
			{ name: "光影氛围", slots: 1 },
		],
		tag_library: {
			主体: { default: ["旧主体", "新主体"] },
			场景背景: { default: ["旧场景", "新场景"] },
			画面风格: { default: ["真实感"] },
			光影氛围: { default: ["柔光"] },
		},
	};
	const node = {
		id: 77,
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "旧主体" },
			{ name: "场景背景标签1", value: "旧场景" },
			{ name: "画面风格标签1", value: "无" },
			{ name: "光影氛围标签1", value: "无" },
			{ name: "自定义补充标签", value: "保留要求, 旧主体, 旧场景" },
			{ name: "运行时随机模式", value: "重写主体与场景" },
			{ name: "运行时随机强度", value: "强" },
			{ name: "核心标签锁定数量", value: 0 },
			{ name: "锁定标签白名单", value: "" },
			{ name: "随机排除标签", value: "" },
			{ name: "随机补充避重缓存", value: "" },
			{ name: "运行时随机保护标签", value: "" },
			{ name: "运行时随机标签", value: true },
			{ name: "seed", value: 1 },
		],
	};
	const state = exports.buildRandomStateLocal(node, library);
	assert.deepEqual(Array.from(state.selected["画面风格"]), []);
	assert.deepEqual(Array.from(state.selected["光影氛围"]), []);
	assert.deepEqual(Array.from(state.customTags), ["保留要求"]);
});

test("applyNsfwWorkspaceResultToNodeState syncs adult generation profile", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "模板风格", value: "自动" },
			{ name: "主体类型", value: "自动" },
			{ name: "标签反推模式", value: "自动平衡" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: false,
		trigger_words: ["女仆"],
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "真实感");
	assert.equal(node.widgets.find((widget) => widget.name === "主体类型").value, "人物角色");
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "成人向成熟");
	assert.equal(node.widgets.find((widget) => widget.name === "优先柔和肤质").value, true);
	assert.equal(node.widgets.find((widget) => widget.name === "抑制文字伪影").value, true);
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "自动");
	assert.equal(node.widgets.find((widget) => widget.name === "主体类型").value, "自动");
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "自动平衡");
	assert.equal(node.widgets.find((widget) => widget.name === "优先柔和肤质").value, false);
	assert.equal(node.widgets.find((widget) => widget.name === "抑制文字伪影").value, false);
});

test("nsfw profile restore follows loaded state and preserves later manual edits", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "模板风格", value: "自动" },
			{ name: "主体类型", value: "自动" },
			{ name: "标签反推模式", value: "自动平衡" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const buildMapped = () => exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: false,
		trigger_words: ["女仆"],
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, buildMapped()), true);
	exports.applyNodeState(node, library, {
		selected: {},
		customTags: [],
		settings: {
			"模板风格": "自动",
			"主体类型": "自动",
			"标签反推模式": "自动平衡",
			"优先柔和肤质": false,
			"抑制文字伪影": false,
		},
	});
	assert.equal(Object.prototype.hasOwnProperty.call(node.properties, "nsfw_workspace"), false);
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "自动平衡");
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, buildMapped()), true);
	assert.equal(node.properties.nsfw_workspace.generation_profile_restore.original["标签反推模式"], "自动平衡");
	node.widgets.find((widget) => widget.name === "模板风格").value = "CG感";
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "CG感");
	assert.equal(node.widgets.find((widget) => widget.name === "主体类型").value, "自动");
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "自动平衡");
	assert.equal(node.widgets.find((widget) => widget.name === "优先柔和肤质").value, false);
	assert.equal(node.widgets.find((widget) => widget.name === "抑制文字伪影").value, false);
});

test("legacy nsfw profile restore survives random state application", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		id: 41,
		properties: {
			nsfw_workspace: { enabled: true, negative_preset: "标准负面提示词" },
			qwen_te_nsfw_profile_restore_v1: {
				"模板风格": "自动",
				"主体类型": "自动",
				"标签反推模式": "自动平衡",
				"优先柔和肤质": false,
				"抑制文字伪影": false,
			},
		},
		widgets: [
			{ name: "模板风格", value: "真实感" },
			{ name: "主体类型", value: "人物角色" },
			{ name: "标签反推模式", value: "成人向成熟" },
			{ name: "优先柔和肤质", value: true },
			{ name: "抑制文字伪影", value: true },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const randomState = exports.buildRandomStateLocal(node, library);
	exports.applyNodeState(node, library, randomState);
	assert.equal(Object.prototype.hasOwnProperty.call(node.properties, "qwen_te_nsfw_profile_restore_v1"), false);
	assert.equal(node.properties.nsfw_workspace.generation_profile_restore.original["标签反推模式"], "自动平衡");
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "自动");
	assert.equal(node.widgets.find((widget) => widget.name === "主体类型").value, "自动");
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "自动平衡");
	assert.equal(node.widgets.find((widget) => widget.name === "优先柔和肤质").value, false);
	assert.equal(node.widgets.find((widget) => widget.name === "抑制文字伪影").value, false);
});

test("applyNsfwWorkspaceResultToNodeState preserves explicit template style", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {},
		widgets: [
			{ name: "模板风格", value: "CG感" },
			{ name: "主体类型", value: "人物角色" },
			{ name: "标签反推模式", value: "商业摄影" },
			{ name: "优先柔和肤质", value: false },
			{ name: "抑制文字伪影", value: false },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["女仆"],
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	assert.equal(node.widgets.find((widget) => widget.name === "模板风格").value, "CG感");
	assert.equal(node.widgets.find((widget) => widget.name === "标签反推模式").value, "成人向成熟");
});

test("summarizeState reflects effective NSFW profile without mutating widgets", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const state = {
		selected: { 主体: ["成年女性"] },
		customTags: ["卧室"],
		settings: {
			"模板风格": "自动",
			"主体类型": "自动",
			"案例输出结构": "自动",
			"运行时随机标签": false,
			"运行时随机模式": "全随机",
			"核心标签锁定数量": 10,
			"运行时随机强度": "中",
			"随机主题池": "自动",
			"锁定标签白名单": "",
			"随机排除标签": "",
			"标签反推模式": "自动平衡",
			"优先柔和肤质": false,
			"抑制文字伪影": false,
		},
		nsfwWorkspace: { enabled: true },
	};
	const summary = exports.summarizeState(state);
	assert.match(summary, /NSFW开/u);
	assert.match(summary, /真实感/u);
	assert.match(summary, /人物角色/u);
	assert.match(summary, /反推:成人向成熟/u);
	assert.match(summary, /柔肤优先/u);
	assert.match(summary, /抑字优先/u);
	assert.equal(state.settings["模板风格"], "自动");
	assert.equal(state.settings["主体类型"], "自动");
	assert.equal(state.settings["标签反推模式"], "自动平衡");
	assert.equal(state.settings["优先柔和肤质"], false);
	assert.equal(state.settings["抑制文字伪影"], false);
});

test("summarizeState keeps explicit NSFW template while applying adult reverse mode", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const state = {
		selected: {},
		customTags: [],
		settings: {
			"模板风格": "CG感",
			"主体类型": "人物角色",
			"案例输出结构": "案例长段版",
			"运行时随机标签": false,
			"运行时随机模式": "全随机",
			"核心标签锁定数量": 10,
			"运行时随机强度": "中",
			"随机主题池": "自动",
			"锁定标签白名单": "",
			"随机排除标签": "",
			"标签反推模式": "商业摄影",
			"优先柔和肤质": false,
			"抑制文字伪影": false,
		},
		nsfw_workspace: { enabled: true },
	};
	const summary = exports.summarizeState(state);
	assert.match(summary, /NSFW开/u);
	assert.match(summary, /CG感/u);
	assert.doesNotMatch(summary, /真实感/u);
	assert.match(summary, /反推:成人向成熟/u);
	assert.equal(state.settings["模板风格"], "CG感");
	assert.equal(state.settings["标签反推模式"], "商业摄影");
});

test("disableNsfwWorkspaceOnNodeState disables branch and removes applied NSFW terms only", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = { slot_config: [], tag_library: {} };
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["旧NSFW词"],
				applied_custom_tags: ["旧NSFW词", "工作台前缀"],
				manual_custom_tags: ["用户保留词"],
				negative_preset: "标准负面提示词",
			},
		},
		widgets: [
			{ name: "自定义补充标签", value: "旧NSFW词, 用户保留词, 工作台前缀" },
		],
	};
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("旧NSFW词"), false);
	assert.equal(customText.includes("工作台前缀"), false);
	assert.equal(customText.includes("用户保留词"), true);
	assert.equal(node.properties.nsfw_workspace.enabled, false);
	assert.equal(node.properties.nsfwWorkspace.enabled, false);
	assert.equal(node.properties.nsfw_workspace.applied_custom_tags.length, 0);
});

test("disableNsfwWorkspaceOnNodeState removes only workspace-added slot tags", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 2 }, { name: "场景背景", slots: 2 }],
		tag_library: {
			主体: { default: ["成年女性", "女仆"] },
			场景背景: { default: ["卧室"] },
		},
	};
	const node = {
		properties: {},
		widgets: [
			{ name: "主体标签1", value: "成年女性" },
			{ name: "主体标签2", value: "无" },
			{ name: "场景背景标签1", value: "无" },
			{ name: "场景背景标签2", value: "无" },
			{ name: "自定义补充标签", value: "" },
		],
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["女仆"],
		scene: "卧室",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	assert.deepEqual(JSON.parse(JSON.stringify(node.properties.nsfw_workspace.applied_selected_tags)), {
		主体: ["女仆"],
		场景背景: ["卧室"],
	});
	assert.equal(exports.disableNsfwWorkspaceOnNodeState(node, library), true);
	assert.equal(node.widgets.find((widget) => widget.name === "主体标签1").value, "成年女性");
	assert.equal(node.widgets.find((widget) => widget.name === "主体标签2").value, "无");
	assert.equal(node.widgets.find((widget) => widget.name === "场景背景标签1").value, "无");
	assert.deepEqual(JSON.parse(JSON.stringify(node.properties.nsfw_workspace.applied_selected_tags)), {});
});

test("applyNodeState clears stale NSFW workspace state when incoming state omits it", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		nsfw_workspace_catalog: {
			defaults: {
				enabled: true,
				trigger_words: ["默认词"],
				negative_apply_mode: "preview",
				negative_preset: "标准负面提示词",
			},
			negative_presets: {},
		},
		slot_config: [],
		tag_library: {},
	};
	const node = {
		properties: {},
		widgets: [],
	};
	exports.applyNodeState(node, library, {
		selected: {},
		customTags: [],
		settings: {},
		nsfwWorkspace: {
			enabled: true,
			trigger_words: ["保存词"],
			negative_preset: "标准负面提示词",
		},
	});
	assert.equal(exports.getNodeNsfwWorkspaceState(node, library).trigger_words.includes("保存词"), true);
	exports.applyNodeState(node, library, {
		selected: {},
		customTags: [],
		settings: {},
	});
	const workspace = exports.getNodeNsfwWorkspaceState(node, library);
	assert.equal(JSON.stringify(workspace.trigger_words), JSON.stringify(["默认词"]));
	assert.equal(node.properties.nsfw_workspace, undefined);
	assert.equal(node.properties.nsfwWorkspace, undefined);
});

test("clonePresetState preserves snake_case nsfw workspace when camelCase is absent", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	assert.equal(typeof exports.clonePresetState, "function");
	const cloned = exports.clonePresetState({
		selected: {},
		customTags: [],
		settings: {},
		nsfw_workspace: {
			enabled: true,
			trigger_words: ["保存词"],
			negative_preset: "标准负面提示词",
		},
	});
	assert.equal(cloned.nsfwWorkspace?.enabled, true);
	assert.equal(JSON.stringify(cloned.nsfwWorkspace?.trigger_words), JSON.stringify(["保存词"]));
	assert.equal(cloned.nsfwWorkspace?.negative_preset, "标准负面提示词");
});

test("getNodeNsfwWorkspaceState prefers catalog defaults when node state is absent", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, widgets: [] };
	const library = {
		nsfw_workspace_catalog: {
			defaults: {
				enabled: true,
				trigger_words: ["默认词"],
				negative_apply_mode: "append",
				negative_preset: "文生图负面提示词",
			},
			negative_presets: {},
		},
		slot_config: [],
		tag_library: {},
	};
	const workspace = exports.getNodeNsfwWorkspaceState(node, library);
	assert.equal(workspace.enabled, true);
	assert.equal(JSON.stringify(workspace.trigger_words), JSON.stringify(["默认词"]));
	assert.equal(workspace.negative_apply_mode, "append");
	assert.equal(workspace.negative_preset, "文生图负面提示词");
});

test("getNodeNsfwWorkspaceState preserves custom catalog negative preset names", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, widgets: [] };
	const library = {
		nsfw_workspace_catalog: {
			defaults: {
				enabled: true,
				trigger_words: ["自定义词"],
				negative_apply_mode: "override",
				negative_preset: "MyPreset",
			},
			negative_presets: {
				MyPreset: "custom negative prompt",
			},
		},
		slot_config: [],
		tag_library: {},
	};
	const workspace = exports.getNodeNsfwWorkspaceState(node, library);
	assert.equal(workspace.negative_preset, "MyPreset");
	assert.equal(workspace.negative_apply_mode, "override");
	assert.equal(JSON.stringify(workspace.trigger_words), JSON.stringify(["自定义词"]));
});

test("buildNsfwWorkspaceMappedState preserves negative_apply_mode", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, widgets: [] };
	const library = { slot_config: [], tag_library: {} };
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["女仆"],
		negative_apply_mode: "append",
		negative_preset: "高质量负面提示词",
	}, {
		"高质量负面提示词": "worst quality, low quality, blurry, bad anatomy",
	});
	assert.equal(mapped.negative_apply_mode, "append");
	assert.equal(mapped.negative.prompt, "worst quality, low quality, blurry, bad anatomy");
});

test("buildNsfwWorkspaceMappedState applies nsfw preset and quality catalog terms", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [{ name: "自定义补充标签", value: "用户保留词" }],
	};
	const library = {
		slot_config: [{ name: "场景背景", slots: 2 }, { name: "构图视角", slots: 2 }],
		tag_library: {
			场景背景: { default: ["豪华卧室", "红色丝绒床单"] },
			构图视角: { default: ["床边视角"] },
		},
		nsfw_workspace_catalog: {
			presets: {
				经典情色: {
					scene: "豪华卧室，红色丝绒床单",
					action: "男女深吻",
					camera_angle: "床边视角，捕捉明暗动作",
				},
			},
			quality_tags: {
				大师级: ["masterpiece", "professional photography"],
			},
		},
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		preset: "经典情色",
		quality_tier: "大师级",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality",
	});
	assert.equal(mapped.custom_tags.includes("用户保留词"), true);
	assert.equal(mapped.custom_tags.includes("masterpiece"), true);
	assert.equal(mapped.custom_tags.includes("professional photography"), true);
	assert.equal(mapped.custom_tags.includes("男女深吻"), true);
	assert.ok(mapped.custom_tags.indexOf("男女深吻") < mapped.custom_tags.indexOf("masterpiece"));
	assert.equal(mapped.custom_tags.includes("捕捉明暗动作"), true);
	assert.equal(mapped.generated_terms.includes("用户保留词"), false);
	assert.equal(mapped.generated_terms.includes("masterpiece"), true);
	assert.equal(mapped.generated_terms.includes("红色丝绒床单"), true);
	assert.equal(mapped.selected["场景背景"].includes("红色丝绒床单"), true);
	assert.equal(mapped.selected["构图视角"].includes("床边视角"), true);
	assert.equal(mapped.custom_tags.includes("豪华卧室，红色丝绒床单"), false);
	assert.equal(mapped.nsfw_workspace.scene, "——");
	assert.equal(mapped.effective_workspace.scene, "豪华卧室，红色丝绒床单");
});

test("buildNsfwWorkspaceMappedState maps explicit anatomy terms as opt-in NSFW terms", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, widgets: [] };
	const library = {
		slot_config: [],
		tag_library: {},
		nsfw_workspace_catalog: {
			options: {
				anatomy_terms: ["——", "阴道", "乳头"],
				explicit_terms: ["——", "性交", "插入", "自慰", "潮吹"],
				adult_action_style: ["——", "双人亲密互动，动作连续，镜头克制不直白"],
			},
			presets: {
				高强度成人氛围: {
					anatomy_terms: "乳房、乳头、阴道",
					explicit_terms: "性交、插入、自慰、潮吹",
					adult_action_style: "双人亲密互动，动作连续，镜头克制不直白",
				},
			},
			quality_tags: {},
			negative_presets: {
				"标准负面提示词": "low quality",
			},
		},
	};
	const manual = exports.buildNsfwWorkspaceMappedState(node, library, {
		anatomy_terms: "阴道，乳头",
		explicit_terms: "性交，插入，自慰，潮吹",
		adult_action_style: "双人亲密互动，动作连续，镜头克制不直白",
		negative_preset: "标准负面提示词",
	});
	assert.equal(manual.custom_tags.includes("阴道"), true);
	assert.equal(manual.custom_tags.includes("乳头"), true);
	assert.equal(manual.custom_tags.includes("性交"), true);
	assert.equal(manual.custom_tags.includes("插入"), true);
	assert.equal(manual.custom_tags.includes("自慰"), true);
	assert.equal(manual.custom_tags.includes("潮吹"), true);
	assert.equal(manual.custom_tags.includes("双人亲密互动"), true);
	assert.equal(manual.custom_tags.includes("镜头克制不直白"), true);
	const preset = exports.buildNsfwWorkspaceMappedState(node, library, {
		preset: "高强度成人氛围",
		negative_preset: "标准负面提示词",
	});
	assert.equal(preset.custom_tags.includes("乳房"), true);
	assert.equal(preset.custom_tags.includes("阴道"), true);
	assert.equal(preset.custom_tags.includes("性交"), true);
	assert.equal(preset.custom_tags.includes("潮吹"), true);
	assert.equal(preset.custom_tags.includes("双人亲密互动"), true);
});

test("buildNsfwWorkspaceMappedState includes embedded prompt selector fields globally", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = { properties: {}, widgets: [] };
	const library = {
		slot_config: [{ name: "主体", slots: 2 }, { name: "动作姿态", slots: 2 }],
		tag_library: {
			主体: { default: ["女仆"] },
			动作姿态: { default: ["接吻"] },
		},
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		selector_character: "女仆 maid",
		selector_outfit: "内衣 lingerie",
		selector_action: "接吻 kissing",
		selector_scene: "温泉 onsen hot spring",
		selector_expression: "诱惑视线 seductive gaze",
		selector_prop: "项圈 collar",
		negative_preset: "标准负面提示词",
	});
	for (const term of ["内衣", "温泉", "诱惑视线", "项圈"]) {
		assert.equal(mapped.custom_tags.includes(term), true);
		assert.equal(mapped.generated_terms.includes(term), true);
	}
	for (const term of ["女仆 maid", "内衣 lingerie", "接吻 kissing", "温泉 onsen hot spring", "诱惑视线 seductive gaze", "项圈 collar"]) {
		assert.equal(mapped.custom_tags.includes(term), false);
		assert.equal(mapped.generated_terms.includes(term), false);
	}
	assert.equal(mapped.selected["主体"].includes("女仆"), true);
	assert.equal(mapped.selected["动作姿态"].includes("接吻"), true);
	assert.equal(mapped.nsfw_workspace.selector_character, "女仆");
});

test("buildNsfwWorkspaceNegativeSyncPlan maps negative_apply_mode into sync branch input", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {},
		widgets: [],
	};
	const library = { slot_config: [], tag_library: {} };
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		negative_apply_mode: "append",
		negative_preset: "高质量负面提示词",
		custom_negative: "custom negative",
	}, {
		"高质量负面提示词": "worst quality, low quality, blurry, bad anatomy",
	});
	const plan = exports.buildNsfwWorkspaceNegativeSyncPlan(node, mapped, {
		"高质量负面提示词": "worst quality, low quality, blurry, bad anatomy",
	}, "base negative");
	assert.equal(plan.mode, "append");
	assert.equal(plan.syncText, "base negative, worst quality, low quality, blurry, bad anatomy");
	assert.equal(plan.negativeText, "worst quality, low quality, blurry, bad anatomy");
});

test("nsfw append plan preserves target text and dedupes repeated negative terms", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const mapped = {
		negative_apply_mode: "append",
		nsfw_workspace: { negative_preset: "测试负面" },
	};
	const plan = exports.buildNsfwWorkspaceNegativeSyncPlan(
		{},
		mapped,
		{ 测试负面: "low quality, blurry" },
		"manual anatomy guard, low quality",
	);
	assert.equal(plan.syncText, "manual anatomy guard, low quality, blurry");
	const empty = exports.buildNsfwWorkspaceNegativeSyncPlan(
		{},
		{ negative_apply_mode: "override", nsfw_workspace: { negative_preset: "自定义负面提示词", custom_negative: "" } },
		{ 自定义负面提示词: "" },
		"manual anatomy guard",
	);
	assert.equal(empty.syncText, null);
	assert.equal(empty.reason, "empty");
});

test("negative sync follows the stage negative output link instead of nearest unrelated node", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const source = { id: 10, type: "QwenTE_StagePromptGenerator", outputs: Array.from({ length: 7 }, () => ({ links: [] })) };
	source.outputs[4] = { links: [101] };
	const linkedNegative = { id: 20, type: "CLIPTextEncode", pos: [900, 900], widgets: [{ name: "text", value: "linked manual negative" }], outputs: [{ links: [] }] };
	const nearbyUnrelated = { id: 21, type: "CLIPTextEncode", pos: [0, 0], widgets: [{ name: "text", value: "unrelated negative" }], outputs: [{ links: [] }] };
	const nodes = new Map([[10, source], [20, linkedNegative], [21, nearbyUnrelated]]);
	exports.__context.__testApp.graph = {
		_nodes: [...nodes.values()],
		links: { 101: { target_id: 20, target_slot: 0 } },
		getNodeById(id) { return nodes.get(Number(id)); },
		setDirtyCanvas() {},
	};
	assert.equal(exports.findNegativeClipTextEncodeNode(source), linkedNegative);
	const syncResult = exports.syncNegativePromptToGraph(source, "linked manual negative, blurry", linkedNegative);
	assert.equal(syncResult.ok, true);
	assert.equal(linkedNegative.widgets[0].value, "linked manual negative, blurry");
	assert.equal(nearbyUnrelated.widgets[0].value, "unrelated negative");
});

test("negative sync refuses ambiguous multi-workflow fallback", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const source = { id: 10, type: "QwenTE_StagePromptGenerator", outputs: Array.from({ length: 7 }, () => ({ links: [] })) };
	const first = { id: 20, type: "CLIPTextEncode", widgets: [{ name: "text", value: "first" }], outputs: [{ links: [201] }] };
	const second = { id: 21, type: "CLIPTextEncode", widgets: [{ name: "text", value: "second" }], outputs: [{ links: [202] }] };
	const samplerA = { id: 30, type: "KSampler" };
	const samplerB = { id: 31, type: "KSampler" };
	const nodes = new Map([[10, source], [20, first], [21, second], [30, samplerA], [31, samplerB]]);
	exports.__context.__testApp.graph = {
		_nodes: [...nodes.values()],
		links: {
			201: { target_id: 30, target_slot: 2 },
			202: { target_id: 31, target_slot: 2 },
		},
		getNodeById(id) { return nodes.get(Number(id)); },
	};
	assert.equal(exports.findNegativeClipTextEncodeNode(source), null);
});

test("applyNsfwWorkspaceResultToNodeState preserves unrelated custom tags with old NSFW text", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: { default: ["女仆"] } },
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["旧NSFW词"],
				applied_custom_tags: ["旧NSFW词"],
			},
		},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "旧NSFW词, 用户保留词" },
		],
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["新NSFW词"],
		custom_prefix: "新前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("旧NSFW词"), false);
	assert.equal(customText.includes("用户保留词"), true);
});

test("applyNsfwWorkspaceResultToNodeState preserves user-owned tags marked in provenance even when text collides", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: { default: ["女仆"] } },
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["旧NSFW词"],
				applied_custom_tags: ["旧NSFW词"],
				user_custom_tags: ["旧NSFW词", "用户保留词"],
			},
		},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "旧NSFW词, 用户保留词" },
		],
	};
	const mapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["新NSFW词"],
		custom_prefix: "新前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, mapped), true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("旧NSFW词"), true);
	assert.equal(customText.includes("用户保留词"), true);
	assert.equal(customText.includes("新NSFW词"), true);
});

test("applyNsfwWorkspaceResultToNodeState seeds manual provenance on first write for later collision-safe rewrites", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: { default: ["旧NSFW词", "新NSFW词"] } },
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["旧NSFW词"],
				applied_custom_tags: ["旧NSFW词"],
			},
		},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "旧NSFW词, 用户保留词" },
		],
	};
	const firstMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["旧NSFW词"],
		custom_prefix: "第一次前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, firstMapped), true);
	assert.equal(JSON.stringify(node.properties.nsfw_workspace?.manual_custom_tags), JSON.stringify(["用户保留词"]));
	const secondMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["新NSFW词"],
		custom_prefix: "第二次前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, secondMapped), true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("用户保留词"), true);
	assert.equal(customText.includes("旧NSFW词"), false);
	assert.equal(customText.includes("新NSFW词"), true);
	assert.equal(customText.includes("第二次前缀"), true);
});

test("applyNsfwWorkspaceResultToNodeState preserves user edits added after the first provenance seed", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const library = {
		slot_config: [{ name: "主体", slots: 1 }],
		tag_library: { 主体: { default: ["女仆"] } },
	};
	const node = {
		properties: {
			nsfw_workspace: {
				enabled: true,
				trigger_words: ["旧NSFW词"],
				applied_custom_tags: ["旧NSFW词"],
			},
		},
		widgets: [
			{ name: "主体标签1", value: "无" },
			{ name: "自定义补充标签", value: "旧NSFW词, 用户保留词" },
		],
	};
	const firstMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["旧NSFW词"],
		custom_prefix: "第一次前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, firstMapped), true);
	const edited = node.widgets.find((widget) => widget.name === "自定义补充标签");
	edited.value = "用户保留词, 用户新词, 旧NSFW词, 第一次前缀";
	node.properties.nsfw_workspace.manual_custom_tags = ["用户保留词"];
	const secondMapped = exports.buildNsfwWorkspaceMappedState(node, library, {
		enabled: true,
		trigger_words: ["新NSFW词"],
		custom_prefix: "第二次前缀",
		negative_preset: "标准负面提示词",
	}, {
		"标准负面提示词": "low quality, blurry, bad anatomy",
	});
	assert.equal(exports.applyNsfwWorkspaceResultToNodeState(node, library, secondMapped), true);
	const customText = node.widgets.find((widget) => widget.name === "自定义补充标签").value;
	assert.equal(customText.includes("用户保留词"), true);
	assert.equal(customText.includes("用户新词"), true);
	assert.equal(customText.includes("旧NSFW词"), false);
	assert.equal(customText.includes("第一次前缀"), false);
	assert.equal(customText.includes("新NSFW词"), true);
	assert.equal(customText.includes("第二次前缀"), true);
});

test("findLatestRollbackHistoryItem includes nsfw-workspace entries", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	const node = {
		properties: {
			qwen_te_history_v1: [
				{ id: "history_nsfw", source: "nsfw-workspace", updatedAt: 200, state: { selected: {}, customTags: ["旧词"], settings: {}, nsfwWorkspace: { enabled: true, trigger_words: ["旧词"] } } },
				{ id: "history_keep", source: "random", updatedAt: 100, state: { selected: {}, customTags: [], settings: {} } },
			],
		},
		widgets: [],
	};
	assert.equal(typeof exports.findLatestRollbackHistoryItem, "function");
	const rollback = exports.findLatestRollbackHistoryItem(node);
	assert.equal(rollback?.source, "nsfw-workspace");
	assert.equal(rollback?.state?.customTags?.includes("旧词"), true);
});

test("stage enhancement retries are singleflight and node cleanup cancels the only timer", async () => {
	let nextTimerId = 1;
	let fetchCount = 0;
	const timers = new Map();
	const exports = await loadUiExports("http://127.0.0.1:8188/", {
		setTimeout(callback, delay) {
			const id = nextTimerId++;
			timers.set(id, { callback, delay });
			return id;
		},
		clearTimeout(id) {
			timers.delete(id);
		},
		fetch: async () => {
			fetchCount += 1;
			return { ok: false, status: 503, json: async () => ({}) };
		},
	});
	const node = { addWidget() {}, addDOMWidget() { return null; }, widgets: [] };
	for (let index = 0; index < 100; index += 1) exports.scheduleEnhanceStagePromptNode(node);
	for (let index = 0; index < 24; index += 1) await Promise.resolve();
	assert.equal(fetchCount, 1);
	assert.equal(timers.size, 1);
	exports.cleanupStagePromptNodeRuntime(node);
	assert.equal(timers.size, 0);
	exports.scheduleEnhanceStagePromptNode(node);
	for (let index = 0; index < 4; index += 1) await Promise.resolve();
	assert.equal(fetchCount, 1);
});

test("stage cleanup restores onExecuted and disposes its panel widget exactly once", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	let disconnectCount = 0;
	let widgetRemoveCount = 0;
	let panelRemoveCount = 0;
	const originalOnExecuted = () => "original";
	const onExecutedWrapper = () => "wrapped";
	const panelWidget = {
		name: "qwen_te_tag_panel",
		onRemove() { widgetRemoveCount += 1; },
	};
	const panel = { remove() { panelRemoveCount += 1; } };
	const node = {
		widgets: [panelWidget, { name: "模板风格", value: "真实感" }],
		onExecuted: onExecutedWrapper,
		removeWidget(widget) {
			const index = this.widgets.indexOf(widget);
			if (index >= 0) this.widgets.splice(index, 1);
			widget.onRemove?.();
		},
	};
	node[exports.PANEL_KEY] = {
		panel,
		panelWidget,
		originalOnExecuted,
		onExecutedWrapper,
		continuousRuntime: { running: false, token: 0 },
		resizeObserver: { disconnect() { disconnectCount += 1; } },
	};
	node[exports.PANEL_READY_KEY] = true;

	exports.cleanupStagePromptNodeRuntime(node);
	exports.cleanupStagePromptNodeRuntime(node);

	assert.equal(node.onExecuted, originalOnExecuted);
	assert.equal(node.widgets.includes(panelWidget), false);
	assert.equal(disconnectCount, 1);
	assert.equal(widgetRemoveCount, 1);
	assert.equal(panelRemoveCount, 1);
	assert.equal(node[exports.PANEL_READY_KEY], undefined);
});

test("stage node creation assigns a clone-safe cache namespace synchronously", async () => {
	const exports = await loadUiExports("http://127.0.0.1:8188/");
	function StageNode() {}
	StageNode.prototype.onNodeCreated = function () { return "created"; };
	StageNode.prototype.onRemoved = function () {};
	StageNode.prototype.configure = function () {};
	StageNode.prototype.serialize = function () { return { properties: {} }; };
	const original = {
		properties: { [exports.NODE_CACHE_NAMESPACE_KEY]: "namespace-original-1234" },
	};
	const clone = Object.assign(new StageNode(), {
		comfyClass: "QwenTE_StagePromptGenerator",
		properties: { [exports.NODE_CACHE_NAMESPACE_KEY]: "namespace-original-1234" },
		widgets: [],
	});
	exports.__context.__testApp.graph._nodes = [original];
	await exports.__extension.beforeRegisterNodeDef(StageNode, { name: "QwenTE_StagePromptGenerator" });

	assert.equal(StageNode.prototype.onNodeCreated.call(clone), "created");

	assert.equal(original.properties[exports.NODE_CACHE_NAMESPACE_KEY], "namespace-original-1234");
	assert.notEqual(clone.properties[exports.NODE_CACHE_NAMESPACE_KEY], "namespace-original-1234");
	assert.match(clone.properties[exports.NODE_CACHE_NAMESPACE_KEY], /^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$/u);
});

test("main panel does not commit lifecycle state when DOM widgets are unavailable", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes('if (typeof node.addDOMWidget !== "function") return false;'), true);
	assert.equal(source.includes("cleanupFixUiArtifacts(node, { preserveMiniToolbar: true })"), true);
	assert.equal(source.includes('?? getWidget(node, "qwen_te_tag_panel")'), true);
	assert.equal(source.includes("if (!panelWidget)"), true);
	assert.equal(source.includes("__QWEN_TE_STAGE_CLEANUP_MINI_TOOLBAR__?.(node, { scheduleLayout: false })"), true);
	assert.equal(source.includes("rollbackStagePromptNodeEnhancement(node)"), true);
	assert.equal(source.includes('Symbol.for("qwen_te.stage_prompt.panel_ready")'), true);
	assert.equal(source.includes("node[PANEL_KEY].ready = true"), true);
	assert.equal(source.includes("node[PANEL_READY_KEY] = true"), true);
	assert.equal(source.includes("__QWEN_TE_STAGE_ROLLBACK__"), true);
	assert.equal(source.includes("__QWEN_TE_STAGE_ENSURE_MINI_TOOLBAR__?.(node)"), true);
	assert.equal(source.includes("else scheduleRetry();"), true);
	assert.equal(source.includes("panelWidget,summaryEl:summary"), true);
	assert.equal(source.includes("originalOnExecuted: null, onExecutedWrapper: null"), true);
});

test("modal disposal runs cleanup exactly once even across replacement-style repeated closes", async () => {
	class TestElement {
		remove() { this.removeCount = (this.removeCount ?? 0) + 1; }
	}
	const exports = await loadUiExports("http://127.0.0.1:8188/", { HTMLElement: TestElement });
	const overlay = new TestElement();
	let disposeCount = 0;
	overlay.__qwenDispose = () => { disposeCount += 1; };
	assert.equal(exports.disposeModalOverlay(overlay), true);
	assert.equal(exports.disposeModalOverlay(overlay), true);
	assert.equal(disposeCount, 1);
	assert.equal(overlay.removeCount, 2);
});

test("stage lifecycle source cancels stale async work and bounds startup scans", async () => {
	const source = await fs.readFile(UI_PATH, "utf8");
	assert.equal(source.includes("nodeType.prototype.onRemoved = function ()"), true);
	assert.equal(source.includes("cleanupStagePromptNodeRuntime(this)"), true);
	assert.equal(source.includes("clearStageNodeEnhanceRetry(node)"), true);
	assert.equal(source.includes("maintenancePasses >= 30"), true);
	assert.equal(source.includes("clearInterval(window.__qwenTeStagePromptTimer)"), true);
	assert.equal(source.includes("retryCount >= STAGE_EXTENSION_REGISTER_RETRY_LIMIT"), true);
	assert.equal(source.includes("clearStagePromptRegisterTimer(timer)"), true);
	assert.equal(source.includes("window[STAGE_EXTENSION_REGISTER_TIMER_KEY] = timer"), true);
	assert.equal(source.includes("syncNodeStageOutputCache(node, { shouldCommit: isCaptureCurrent })"), true);
	assert.equal(source.includes("if (!isCaptureCurrent()) return false;"), true);
	assert.equal(source.includes('filterInput.addEventListener("input", () => { void render({ refresh: false }); });'), true);
	assert.equal(source.includes("customArrangeRequestId"), true);
});
