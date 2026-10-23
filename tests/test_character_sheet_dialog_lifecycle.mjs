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

// Run the production dialog and lifecycle guards without loading ComfyUI or a browser.
const dialogSource = [
	sourceBetween("function beginNodeStateMutation(", "function applyNodeState("),
	sourceBetween("function ensureSingleModal(", "function getNodeDisplayName("),
	sourceBetween("function openCharacterSheetDialog(", "function openQualityAuditDialog("),
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
	addEventListener(name, handler) { this.listeners.set(name, handler); }
	focus() {}
	remove() {
		if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
		this.parentNode = null;
	}
}

function findElement(element, predicate) {
	if (predicate(element)) return element;
	for (const child of element.children) {
		const found = findElement(child, predicate);
		if (found) return found;
	}
	return null;
}

function makeFixture() {
	const body = new TestElement("body");
	const requests = [];
	const commits = [];
	const messages = [];
	const disposedOwners = [];
	const node = {};
	const library = {};
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
		CHARACTER_SHEET_MODE_OPTIONS: [
			{ key: "reference", label: "参考单人图", desc: "参考图模式" },
			{ key: "prompt", label: "纯提示词", desc: "文字模式" },
		],
		CHARACTER_SHEET_PROMPTS: { reference: "参考图合同", prompt: "文字合同" },
		buildNodeModalContext: () => ({ nodeName: "测试节点" }),
		collectNodeState: () => ({ customTags: [] }),
		getFreshLibraryForUi: (_node, _library, options) => new Promise((resolve) => {
			requests.push({ resolve, options });
		}),
		buildCharacterSheetState: (_node, _library, options) => ({ enabled: true, ...options }),
		buildCharacterSheetDisabledState: () => ({ enabled: false }),
		applyNodeState: (_node, _library, state, options) => {
			commits.push({ state, options });
			return true;
		},
		setNodeStatusText: (_node, message) => messages.push(message),
		refreshNodeActionButtons() {},
		abortOwnedRequests: (owner) => disposedOwners.push(owner),
		console,
	};
	vm.runInNewContext(`${dialogSource}\nglobalThis.openDialog = openCharacterSheetDialog;`, context, { filename: UI_URL.pathname });
	const open = () => {
		context.openDialog(node, library);
		const overlay = body.children.at(-1);
		return {
			overlay,
			button: (text) => findElement(overlay, (element) => element.tagName === "button" && element.textContent === text),
			input: findElement(overlay, (element) => element.tagName === "textarea"),
			promptMode: findElement(overlay, (element) => element.tagName === "button" && element.children.some((child) => child.textContent === "纯提示词")),
		};
	};
	return { open, body, requests, commits, messages, disposedOwners, context, node, library };
}

for (const action of ["启用", "停用"]) {
	for (const closeRoute of ["取消", "关闭", "backdrop", "replacement"]) {
		test(`character sheet ${action} cannot commit after ${closeRoute} while library refresh is pending`, async () => {
			const fixture = makeFixture();
			const dialog = fixture.open();
			const result = dialog.button(action).onclick();
			assert.equal(fixture.requests.length, 1);
			assert.equal(fixture.requests[0].options.commitGuard(), true);
			if (closeRoute === "backdrop") dialog.overlay.listeners.get("click")({ target: dialog.overlay });
			else if (closeRoute === "replacement") fixture.open();
			else dialog.button(closeRoute).onclick();
			assert.equal(dialog.overlay.__qwenDisposed, true);
			assert.equal(fixture.requests[0].options.commitGuard(), false);
			fixture.requests[0].resolve(fixture.library);
			assert.equal(await result, false);
			assert.equal(fixture.commits.length, 0);
			assert.equal(fixture.messages.length, 0);
			assert.deepEqual(fixture.disposedOwners, [dialog.overlay]);
			assert.equal(fixture.body.children.length, closeRoute === "replacement" ? 1 : 0);
		});
	}
}

test("character sheet enable keeps the mode and text that were submitted before the refresh", async () => {
	const fixture = makeFixture();
	const dialog = fixture.open();
	dialog.input.value = "保留铜质外壳";
	const result = dialog.button("启用").onclick();
	dialog.input.value = "稍后编辑的其他要求";
	dialog.promptMode.onclick();
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, true);
	assert.equal(fixture.commits.length, 1);
	assert.equal(fixture.commits[0].state.mode, "reference");
	assert.equal(fixture.commits[0].state.userText, "保留铜质外壳");
	assert.match(fixture.messages[0], /参考单人图/u);
	assert.equal(dialog.overlay.__qwenDisposed, true);
});

test("character sheet delayed action preserves newer node edits", async () => {
	const fixture = makeFixture();
	const dialog = fixture.open();
	const result = dialog.button("启用").onclick();
	fixture.context.beginNodeStateMutation(fixture.node);
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, false);
	assert.equal(fixture.commits.length, 0);
	assert.equal(fixture.messages.length, 0);
	assert.equal(fixture.body.children.length, 1);
});

test("character sheet disable still commits once and disposes the live dialog", async () => {
	const fixture = makeFixture();
	const dialog = fixture.open();
	const result = dialog.button("停用").onclick();
	fixture.requests[0].resolve(fixture.library);
	assert.equal(await result, true);
	assert.equal(fixture.commits.length, 1);
	assert.equal(fixture.commits[0].state.enabled, false);
	assert.equal(dialog.overlay.__qwenDisposed, true);
	assert.deepEqual(fixture.disposedOwners, [dialog.overlay]);
	assert.equal(fixture.body.children.length, 0);
});
