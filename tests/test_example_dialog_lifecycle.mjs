import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import vm from "node:vm";

const UI_URL = new URL("../web/stage_prompt_generator_ui_v2.js", import.meta.url);
const source = await fs.readFile(UI_URL, "utf8");

function sourceBetween(startMarker, endMarker) {
	const start = source.indexOf(startMarker);
	const end = source.indexOf(endMarker, start);
	assert.ok(start >= 0 && end > start, `Cannot find source between ${startMarker} and ${endMarker}`);
	return source.slice(start, end);
}

// Exercise the production dialog and guards with delayed library/queue responses.
const dialogSource = [
	sourceBetween("function beginNodeStateMutation(", "function applyNodeState("),
	sourceBetween("function ensureSingleModal(", "function getNodeDisplayName("),
	sourceBetween("function openExampleDialog(", "function openTagManager("),
].join("\n");

class TestElement {
	constructor(tagName) {
		this.tagName = tagName;
		this.children = [];
		this.dataset = {};
		this.style = {};
		this.classList = { toggle() {} };
		this.listeners = new Map();
	}
	appendChild(child) {
		this.children.push(child);
		child.parentNode = this;
		return child;
	}
	append(...children) { for (const child of children) this.appendChild(child); }
	replaceChildren(...children) {
		for (const child of this.children) child.parentNode = null;
		this.children = [];
		this.append(...children);
	}
	addEventListener(name, handler) { this.listeners.set(name, handler); }
	focus() {}
	remove() {
		if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
		this.parentNode = null;
	}
}

function findElements(element, predicate) {
	return [
		...(predicate(element) ? [element] : []),
		...element.children.flatMap((child) => findElements(child, predicate)),
	];
}

function makeFixture(options = {}) {
	const body = new TestElement("body");
	const requests = [];
	const commits = [];
	const history = [];
	const queues = [];
	const messages = [];
	const node = {};
	const library = { slot_config: [] };
	const presets = [
		{ name: "示例A", tags: [], meta: {} },
		{ name: "示例B", tags: [], meta: {} },
	];
	const context = {
		HTMLElement: TestElement,
		NODE_STATE_MUTATION_REVISION_KEY: Symbol("mutationRevision"),
		NODE_REMOVED_KEY: Symbol("removed"),
		document: {
			body,
			createElement: (tagName) => new TestElement(tagName),
			querySelectorAll: (selector) => {
				const key = /data-qwen-modal="([^"]+)"/u.exec(selector)?.[1];
				return body.children.filter((element) => element.dataset.qwenModal === key);
			},
		},
		EXAMPLE_PRESET_MAP: { 自动: "示例A" },
		PRESET_USE_CASE_ORDER: [],
		buildNodeModalContext: () => ({ nodeName: "测试节点" }),
		getWidget: () => ({ value: "自动" }),
		buildDedupedPresets: () => presets,
		collectNodeState: () => ({ customTags: [] }),
		inferBestExamplePreset: () => presets[0],
		inferPresetRecommendation: () => [],
		getFreshLibraryForUi: (_node, _library, requestOptions) => new Promise((resolve) => {
			requests.push({ resolve, options: requestOptions });
		}),
		createPresetBaseState: () => ({ customTags: [], selected: {}, settings: {} }),
		applyPreset: (state, _library, preset) => { state.preset = preset.name; },
		parseCustomTags: (text) => String(text ?? "").split(/[,，]/u).filter(Boolean),
		buildTagGroupIndex: () => new Map(),
		addUniqueTag: (tags, tag) => { if (!tags.includes(tag)) tags.push(tag); },
		recordNodeHistory: () => { history.push("before-apply"); },
		applyNodeState: (_node, _library, state) => {
			commits.push(state);
			options.onApply?.(context, body);
			return true;
		},
		queueWorkflowFromNode: () => {
			const queue = { dialogWasClosed: body.children.every((element) => element.__qwenDisposed) };
			queues.push(queue);
			if (options.delayQueue) return new Promise((resolve) => { queue.resolve = resolve; });
			return Promise.resolve(options.queueResult !== false);
		},
		setNodeStatusText: (_node, message) => messages.push(message),
		abortOwnedRequests() {},
		console,
	};
	vm.runInNewContext(`${dialogSource}\nglobalThis.openDialog = openExampleDialog;`, context, { filename: UI_URL.pathname });
	const open = () => {
		context.openDialog(node, library);
		const overlay = body.children.at(-1);
		return {
			overlay,
			buttons: (text) => findElements(overlay, (element) => element.tagName === "button" && element.textContent === text),
			input: findElements(overlay, (element) => element.tagName === "textarea")[0],
		};
	};
	return { open, body, requests, commits, history, queues, messages, context, node, library };
}

for (const action of ["应用选中", "选中并运行"]) {
	for (const closeRoute of ["header", "footer", "backdrop", "replacement"]) {
		test(`example ${action} cannot apply or queue after ${closeRoute} during library refresh`, async () => {
			const fixture = makeFixture();
			const dialog = fixture.open();
			const result = dialog.buttons(action)[0].onclick();
			assert.equal(fixture.requests.length, 1);
			assert.equal(fixture.requests[0].options.commitGuard(), true);
			if (closeRoute === "replacement") fixture.open();
			else if (closeRoute === "backdrop") dialog.overlay.listeners.get("click")({ target: dialog.overlay });
			else dialog.buttons("关闭")[closeRoute === "header" ? 0 : 1].onclick();
			assert.equal(dialog.overlay.__qwenDisposed, true);
			assert.equal(fixture.requests[0].options.commitGuard(), false);
			fixture.requests[0].resolve(fixture.library);
			assert.equal(await result, false);
			assert.equal(fixture.commits.length, 0);
			assert.equal(fixture.history.length, 0);
			assert.equal(fixture.queues.length, 0);
			assert.equal(fixture.messages.length, 0);
			assert.equal(fixture.body.children.length, closeRoute === "replacement" ? 1 : 0);
		});
	}
}

test("example application keeps submitted preset and extra tags while the library refreshes", async () => {
	const fixture = makeFixture();
	const dialog = fixture.open();
	dialog.input.value = "铜质外壳,磨砂玻璃";
	const result = dialog.buttons("应用选中")[0].onclick();
	dialog.input.value = "稍后编辑的其他要求";
	dialog.buttons("选中")[1].onclick({ stopPropagation() {} });
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, true);
	assert.equal(fixture.commits.length, 1);
	assert.equal(fixture.commits[0].preset, "示例A");
	assert.deepEqual(Array.from(fixture.commits[0].customTags), ["铜质外壳", "磨砂玻璃"]);
	assert.equal(fixture.queues.length, 0);
	assert.equal(dialog.overlay.__qwenDisposed, true);
});

test("successful example application closes its dialog and queues the submitted workflow once", async () => {
	const fixture = makeFixture({ delayQueue: true });
	const dialog = fixture.open();
	const result = dialog.buttons("选中并运行")[0].onclick();
	fixture.requests[0].resolve(fixture.library);
	for (let tick = 0; tick < 4; tick += 1) await Promise.resolve();
	assert.equal(fixture.commits.length, 1);
	assert.equal(fixture.queues.length, 1);
	assert.equal(fixture.queues[0].dialogWasClosed, true);
	assert.equal(dialog.overlay.__qwenDisposed, true);
	assert.equal(fixture.body.children.length, 0);
	fixture.queues[0].resolve(true);
	assert.equal(await result, true);
	assert.match(fixture.messages[0], /已应用示例锚点并加入队列：示例A/u);
});

test("a newer node edit cancels a pending example before history, application or queue", async () => {
	const fixture = makeFixture();
	const dialog = fixture.open();
	const result = dialog.buttons("选中并运行")[0].onclick();
	fixture.context.beginNodeStateMutation(fixture.node);
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, false);
	assert.equal(fixture.history.length, 0);
	assert.equal(fixture.commits.length, 0);
	assert.equal(fixture.queues.length, 0);
});

test("a synchronous dialog cancellation during example application prevents queue submission", async () => {
	const fixture = makeFixture({ onApply: (context, body) => context.disposeModalOverlay(body.children[0]) });
	const dialog = fixture.open();
	const result = dialog.buttons("选中并运行")[0].onclick();
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, false);
	assert.equal(fixture.commits.length, 1);
	assert.equal(fixture.queues.length, 0);
});

test("a replacement node action during queue acknowledgement keeps its newer status", async () => {
	const fixture = makeFixture({ delayQueue: true });
	const dialog = fixture.open();
	const result = dialog.buttons("选中并运行")[0].onclick();
	fixture.requests[0].resolve(fixture.library);
	for (let tick = 0; tick < 4; tick += 1) await Promise.resolve();
	assert.equal(fixture.queues.length, 1);
	fixture.context.beginNodeStateMutation(fixture.node);
	fixture.queues[0].resolve(true);
	assert.equal(await result, false);
	assert.equal(fixture.messages.length, 0);
	assert.equal(fixture.queues.length, 1);
});
