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
	let reject;
	const promise = new Promise((done, fail) => { resolve = done; reject = fail; });
	return { promise, resolve, reject };
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

function makeQualityAuditFixture() {
	const response = deferred();
	const requested = deferred();
	const writes = [];
	const refreshes = [];
	const context = {
		PANEL_KEY: Symbol("panel"),
		NODE_QUALITY_AUDIT_REVISION_KEY: Symbol("auditRevision"),
		NODE_REMOVED_KEY: Symbol("removed"),
		resolveNodeWorkflowAuditPromptIds: async () => ["completed-prompt"],
		requestQualityAudit(payload) {
			requested.resolve(payload);
			return response.promise;
		},
		formatQualityAuditSummary: (summary) => `Images ${summary.total_images}`,
		setNodeQualityAuditMeta: (_node, meta) => { writes.push(meta); },
		refreshNodeSummary: (node, library) => { refreshes.push({ node, library }); },
	};
	const helperSource = sourceBetween("async function runNodeQualityAudit(", "function readNodeRandomDedupeCache(");
	vm.runInNewContext(`${helperSource}\nglobalThis.runNodeQualityAudit = runNodeQualityAudit;`, context, { filename: UI_PATH.pathname });
	const node = { [context.PANEL_KEY]: { library: { slot_config: [] } } };
	return { context, node, response, requested, writes, refreshes };
}

for (const cancellation of ["stopped", "disposed"]) {
	test(`${cancellation} continuous quality audit cannot write a late successful response`, async () => {
		const fixture = makeQualityAuditFixture();
		const lifecycle = { token: 1, disposed: false };
		const pending = fixture.context.runNodeQualityAudit(fixture.node, { shouldCancel: () => lifecycle.token !== 1 || lifecycle.disposed });
		await fixture.requested.promise;
		if (cancellation === "stopped") lifecycle.token += 1;
		else lifecycle.disposed = true;
		fixture.response.resolve({ ok: true, result: { summary: { total_images: 2 } }, markdown: "Old audit" });

		const result = await pending;
		assert.equal(result.stale, true);
		assert.equal(result.ok, false);
		assert.equal(fixture.writes.length, 0);
		assert.equal(fixture.refreshes.length, 0);
	});
}

test("cancelled quality audit returns stale when its in-flight request rejects", async () => {
	const fixture = makeQualityAuditFixture();
	let cancelled = false;
	const pending = fixture.context.runNodeQualityAudit(fixture.node, { shouldCancel: () => cancelled });
	await fixture.requested.promise;
	cancelled = true;
	fixture.response.reject(new Error("Request aborted"));

	assert.equal((await pending).stale, true);
	assert.equal(fixture.writes.length, 0);
	assert.equal(fixture.refreshes.length, 0);
});

test("active quality audit retains its result and refreshes the node once", async () => {
	const fixture = makeQualityAuditFixture();
	const pending = fixture.context.runNodeQualityAudit(fixture.node, { shouldCancel: () => false });
	const payload = await fixture.requested.promise;
	assert.deepEqual(Array.from(payload.history_prompt_ids), ["completed-prompt"]);
	fixture.response.resolve({ ok: true, message: "Audit ready", result: { summary: { total_images: 2 } }, markdown: "Current audit" });

	const result = await pending;
	assert.equal(result.ok, true);
	assert.equal(result.message, "Audit ready");
	assert.equal(result.summaryText, "Images 2");
	assert.equal(fixture.writes.length, 1);
	assert.equal(fixture.writes[0].markdown, "Current audit");
	assert.equal(fixture.refreshes.length, 1);
});

test("active quality audit preserves request failures for the caller", async () => {
	const fixture = makeQualityAuditFixture();
	const pending = fixture.context.runNodeQualityAudit(fixture.node, { shouldCancel: () => false });
	await fixture.requested.promise;
	const error = new Error("Quality audit service unavailable");
	fixture.response.reject(error);

	await assert.rejects(pending, (actual) => actual === error);
	assert.equal(fixture.writes.length, 0);
	assert.equal(fixture.refreshes.length, 0);
});

test("active quality audit preserves a server failure diagnostic", async () => {
	const fixture = makeQualityAuditFixture();
	const pending = fixture.context.runNodeQualityAudit(fixture.node, { shouldCancel: () => false });
	await fixture.requested.promise;
	fixture.response.resolve({ ok: false, message: "No output images found" });

	const result = await pending;
	assert.equal(result.ok, false);
	assert.equal(result.stale, undefined);
	assert.equal(result.message, "No output images found");
	assert.equal(fixture.writes.length, 1);
	assert.equal(fixture.refreshes.length, 1);
});

test("continuous quality audit passes cancellation through both run entry points", () => {
	const sharedRun = sourceBetween("async function runNodeContinuousPresetSequence(", "async function startNodeContinuousPresetRun(");
	const sharedAudit = sharedRun.slice(sharedRun.indexOf("await runNodeQualityAudit("));
	assert.match(sharedAudit, /shouldCancel:\s*\(\)\s*=>\s*token\s*!==\s*ensureNodeContinuousRuntime\(node\)\.token/u);
	const managerRun = sourceBetween("const startContinuousPresetRun = async", "const applyPresetToNode = async");
	const managerAudit = managerRun.slice(managerRun.indexOf("await runNodeQualityAudit("));
	assert.match(managerAudit, /shouldCancel:\s*\(\)\s*=>\s*token\s*!==\s*continuousRunToken\s*\|\|\s*overlay\.__qwenDisposed/u);
});

function makeReportActionFixture({ queueResult = true } = {}) {
	const fixture = makeFixture();
	const handlers = new Map();
	const reports = [];
	const randomized = [];
	const execution = deferred();
	const waitRequested = deferred();
	const overlay = { isConnected: true, __qwenDisposed: false };
	const statusEl = { textContent: "Report ready" };
	const initialLibrary = { version: "initial" };
	Object.assign(fixture.context, {
		node: fixture.node,
		library: initialLibrary,
		targetPreset: { name: "Report preset", state: { settings: { template: "report" } } },
		overlay,
		statusEl,
		document: { createElement: () => ({}) },
		actionBar: {
			appendChild(button) {
				handlers.set(button.textContent, () => button.onclick({ stopPropagation() {} }));
			},
		},
		render() {},
		pushNodeContinuousRunReport: (_node, _library, level, message) => { reports.push({ level, message }); },
		getNodeExecutionStamp: () => 123,
		buildAndApplyRandomState: async (_node, library, options) => {
			randomized.push({ library, options });
			return options.commitGuard();
		},
		queueWorkflowFromNode: async () => { fixture.queued.push(true); return queueResult; },
		waitForNodeExecution: (_node, _stamp, _timeout, _poll, options) => {
			waitRequested.resolve(options);
			return execution.promise;
		},
	});
	const actionWrapperSource = sourceBetween("const isReportActionCurrent =", 'makeAction("复制单预设", async () => {');
	const actionsSource = sourceBetween('makeAction("载入预设", async () => {', 'makeAction("连测轮流", async () => {');
	vm.runInNewContext(`${actionWrapperSource}\n${actionsSource}`, fixture.context, { filename: UI_PATH.pathname });
	return { ...fixture, handlers, reports, randomized, execution, waitRequested, overlay, statusEl, initialLibrary };
}

for (const [label, queue, randomize] of [["载入预设", false, false], ["重跑并入队", true, false], ["随机跑", true, true]]) {
	test(`continuous report ${label} uses the shared preset path without an out-of-scope helper`, async () => {
		const fixture = makeReportActionFixture();
		const freshLibrary = { version: "fresh" };
		fixture.refresh.resolve(freshLibrary);
		fixture.execution.resolve(true);

		await fixture.handlers.get(label)();

		assert.equal(fixture.applied.length, 1);
		assert.equal(fixture.applied[0].options.recordHistory, true);
		assert.equal(fixture.context.library, freshLibrary);
		assert.equal(fixture.queued.length, Number(queue));
		assert.equal(fixture.randomized.length, Number(randomize));
		assert.equal(fixture.reports.at(-1)?.level, queue ? "完成" : "手动载入");
	});

	for (const cancellation of ["closed", "superseded"]) {
		test(`continuous report ${label} cannot commit after ${cancellation} while refreshing`, async () => {
			const fixture = makeReportActionFixture();
			const pending = fixture.handlers.get(label)();
			const initialReportCount = fixture.reports.length;
			if (cancellation === "closed") {
				fixture.overlay.__qwenDisposed = true;
				fixture.overlay.isConnected = false;
			} else fixture.context.beginNodeStateMutation(fixture.node);
			fixture.refresh.resolve({ version: "late" });
			await pending;

			assert.equal(fixture.applied.length, 0);
			assert.equal(fixture.queued.length, 0);
			assert.equal(fixture.randomized.length, 0);
			assert.equal(fixture.reports.length, initialReportCount);
			assert.equal(fixture.statusEl.textContent, "Report ready");
		});
	}

	test(`continuous report ${label} shows a thrown preset error without an unhandled rejection`, async () => {
		const fixture = makeReportActionFixture();
		const pending = fixture.handlers.get(label)();
		fixture.refresh.reject(new Error("Preset refresh unavailable"));
		await pending;

		assert.equal(fixture.applied.length, 0);
		assert.equal(fixture.queued.length, 0);
		assert.equal(fixture.reports.at(-1)?.level, "失败");
		assert.match(fixture.statusEl.textContent, /Preset refresh unavailable/u);
	});

	test(`continuous report ${label} ignores a late refresh error after close`, async () => {
		const fixture = makeReportActionFixture();
		const pending = fixture.handlers.get(label)();
		const reportCount = fixture.reports.length;
		fixture.overlay.__qwenDisposed = true;
		fixture.overlay.isConnected = false;
		fixture.refresh.reject(new Error("Request aborted"));
		await pending;

		assert.equal(fixture.applied.length, 0);
		assert.equal(fixture.queued.length, 0);
		assert.equal(fixture.reports.length, reportCount);
		assert.equal(fixture.statusEl.textContent, "Report ready");
	});
}

for (const label of ["重跑并入队", "随机跑"]) {
	test(`continuous report ${label} does not report an in-flight queue as failed after close`, async () => {
		const fixture = makeReportActionFixture();
		const queueResponse = deferred();
		const queueRequested = deferred();
		fixture.context.queueWorkflowFromNode = () => {
			fixture.queued.push(true);
			queueRequested.resolve(true);
			return queueResponse.promise;
		};
		fixture.refresh.resolve({ version: "fresh" });
		const pending = fixture.handlers.get(label)();
		assert.equal(await Promise.race([queueRequested.promise, pending.then(() => false)]), true);
		fixture.overlay.__qwenDisposed = true;
		fixture.overlay.isConnected = false;
		const reportCount = fixture.reports.length;
		queueResponse.resolve(true);
		await pending;

		assert.equal(fixture.queued.length, 1);
		assert.equal(fixture.reports.length, reportCount);
		assert.equal(fixture.reports.some((entry) => entry.level === "失败"), false);
	});

	test(`continuous report ${label} preserves a real queue failure diagnostic`, async () => {
		const fixture = makeReportActionFixture({ queueResult: false });
		fixture.refresh.resolve({ version: "fresh" });

		await fixture.handlers.get(label)();

		assert.equal(fixture.applied.length, 1);
		assert.equal(fixture.queued.length, 1);
		assert.equal(fixture.reports.at(-1)?.level, "失败");
		assert.match(fixture.statusEl.textContent, /未能自动入队/u);
	});

	test(`continuous report ${label} does not record a timeout after the report is closed`, async () => {
		const fixture = makeReportActionFixture();
		fixture.refresh.resolve({ version: "fresh" });
		const pending = fixture.handlers.get(label)();
		const waitOptions = await Promise.race([fixture.waitRequested.promise, pending.then(() => null)]);
		assert.equal(typeof waitOptions?.shouldCancel, "function");
		fixture.overlay.__qwenDisposed = true;
		fixture.overlay.isConnected = false;
		const reportCount = fixture.reports.length;
		assert.equal(waitOptions.shouldCancel(), true);
		fixture.execution.resolve(false);
		await pending;

		assert.equal(fixture.queued.length, 1);
		assert.equal(fixture.reports.length, reportCount);
		assert.equal(fixture.reports.at(-1)?.level, "入队");
	});
}
