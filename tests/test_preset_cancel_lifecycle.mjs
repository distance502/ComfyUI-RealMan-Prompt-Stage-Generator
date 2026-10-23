import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import vm from "node:vm";

const UI_PATH = new URL("../web/stage_prompt_generator_ui_v2.js", import.meta.url);
const source = await fs.readFile(UI_PATH, "utf8");

function sourceBetween(startMarker, endMarker) {
	const start = source.indexOf(startMarker);
	const end = source.indexOf(endMarker, start);
	assert.ok(start >= 0 && end > start, `Cannot find source between ${startMarker} and ${endMarker}`);
	return source.slice(start, end);
}

function deferred() {
	let resolve;
	const promise = new Promise((done) => { resolve = done; });
	return { promise, resolve };
}

function makeFixture() {
	const refresh = deferred();
	const applied = [];
	const queued = [];
	const context = {
		PANEL_KEY: Symbol("panel"),
		NODE_STATE_MUTATION_REVISION_KEY: Symbol("mutationRevision"),
		NODE_REMOVED_KEY: Symbol("removed"),
		beginNodeStateMutation(node) {
			node[this.NODE_STATE_MUTATION_REVISION_KEY] = Number(node[this.NODE_STATE_MUTATION_REVISION_KEY] ?? 0) + 1;
			return node[this.NODE_STATE_MUTATION_REVISION_KEY];
		},
		isNodeStateMutationCurrent(node, revision) {
			return !node[this.NODE_REMOVED_KEY] && node[this.NODE_STATE_MUTATION_REVISION_KEY] === revision;
		},
		getFreshLibraryForUi: () => refresh.promise,
		clonePresetState: (state) => ({ ...state }),
		applyNodeState: (_node, _library, state, options) => { applied.push({ state, options }); return true; },
		buildAndApplyRandomState: async (_node, _library, options) => options.commitGuard(),
		queueWorkflowFromNode: async () => { queued.push(true); return true; },
	};
	const helperSource = [
		sourceBetween("function beginNodeStateMutation(", "function applyNodeState("),
		sourceBetween("async function applyPresetStateToNode(", "async function runNodeContinuousPresetSequence("),
	].join("\n");
	vm.runInNewContext(`${helperSource}\nglobalThis.applyPresetStateToNode = applyPresetStateToNode;`, context, { filename: UI_PATH.pathname });
	return { context, refresh, applied, queued, node: {} };
}

test("stopping continuous presets during library refresh prevents apply, history, and queue", async () => {
	const fixture = makeFixture();
	let running = true;
	const result = fixture.context.applyPresetStateToNode(fixture.node, {}, { settings: {} }, {
		queue: true,
		commitGuard: () => running,
	});
	running = false;
	fixture.refresh.resolve({ slot_config: [] });

	assert.equal((await result).stale, true);
	assert.equal(fixture.applied.length, 0);
	assert.equal(fixture.queued.length, 0);
});

test("closing preset manager during library refresh prevents apply, history, and queue", async () => {
	const fixture = makeFixture();
	const overlay = { __qwenDisposed: false };
	const commitGuard = () => !overlay.__qwenDisposed;
	const result = fixture.context.applyPresetStateToNode(fixture.node, {}, { settings: {} }, {
		queue: true,
		commitGuard,
	});
	overlay.__qwenDisposed = true;
	fixture.refresh.resolve({ slot_config: [] });

	assert.equal((await result).stale, true);
	assert.equal(fixture.applied.length, 0);
	assert.equal(fixture.queued.length, 0);
});

test("active preset apply retains one node commit and one requested queue", async () => {
	const fixture = makeFixture();
	const result = fixture.context.applyPresetStateToNode(fixture.node, {}, { settings: {} }, { queue: true });
	fixture.refresh.resolve({ slot_config: [] });

	const outcome = await result;
	assert.equal(outcome.ok, true);
	assert.equal(outcome.queued, true);
	assert.equal(outcome.library.slot_config.length, 0);
	assert.equal(fixture.applied.length, 1);
	assert.equal(fixture.queued.length, 1);
});

test("preset manager wires disposed and continuous-run guards into async apply", () => {
	const wrapperStart = source.indexOf("const applyPresetToNode = async");
	const wrapperEnd = source.indexOf("batchFavoriteButton.onclick", wrapperStart);
	const wrapper = source.slice(wrapperStart, wrapperEnd);
	assert.match(wrapper, /!overlay\.__qwenDisposed/u);
	assert.match(wrapper, /options\.commitGuard\(\)/u);
	const runStart = source.indexOf("const startContinuousPresetRun = async");
	const runEnd = source.indexOf("const applyPresetToNode = async", runStart);
	assert.match(source.slice(runStart, runEnd), /commitGuard:\s*\(\)\s*=>\s*token\s*===\s*continuousRunToken/u);
});
