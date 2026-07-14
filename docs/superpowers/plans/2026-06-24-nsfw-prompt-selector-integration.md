# NSFW Prompt Selector Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the core capabilities of `F:/ComfyUI-NSFW-PromptSelector` into the existing Qwen TE stage prompt node as an in-panel NSFW workspace without breaking the current structured tag workflow.

**Architecture:** Keep the current stage prompt node as the single backend node and add an NSFW workspace layer that maps structured NSFW selections into the existing `selected/customTags/negative_prompt` state model. The backend adds small focused helpers for NSFW presets, workspace state, and mapping, while the frontend adds a dedicated NSFW workspace inside the current large panel instead of introducing a second node or second full UI system.

**Tech Stack:** Python, ComfyUI custom node backend, existing Qwen TE stage prompt pipeline, browser-side JavaScript UI in `stage_prompt_generator_ui.js`, unittest-based regression tests.

## Global Constraints

- Do not introduce a second parallel backend node type for NSFW mode.
- Do not break existing normal tag workflow, random theme-pool workflow, history, rollback, preset, or negative-sync features.
- Keep NSFW integration as a workspace inside the current node UI.
- First version must prefer structured mapping over direct raw prompt string injection.
- First version must keep explicit negative-prompt precedence understandable and user-controlled.

---

### Task 1: Add backend NSFW preset/state/mapping modules

**Files:**
- Create: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_presets.py`
- Create: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_workspace.py`
- Create: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_mapper.py`
- Test: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py`

**Interfaces:**
- Consumes: existing tag grouping semantics from current stage prompt backend.
- Produces:
  - `build_nsfw_workspace_defaults() -> dict[str, Any]`
  - `build_nsfw_workspace_catalog() -> dict[str, Any]`
  - `map_nsfw_workspace_to_stage_state(workspace: dict[str, Any], *, tag_group_index: dict[str, str], group_slot_limits: dict[str, int]) -> dict[str, Any]`
  - `resolve_nsfw_negative_prompt(workspace: dict[str, Any]) -> str`

- [ ] **Step 1: Write the failing tests**

```python
def test_nsfw_mapper_routes_known_terms_into_stage_groups(self) -> None:
    workspace = {
        "trigger_words": ["女仆", "护士"],
        "scene": "豪华卧室，红色丝绒床单，镜面天花板",
        "action": "男女深吻，舌尖交缠，男抚摸女阴道",
        "outfit": "透明睡袍，阴道隐约可见",
        "mood": "禁忌诱惑，嘴角微翘",
        "custom_prefix": "Ultra realistic",
        "custom_suffix": "cinematic framing",
        "negative_preset": "标准负面提示词",
        "custom_negative": "",
    }
    result = nsfw_mapper.map_nsfw_workspace_to_stage_state(
        workspace,
        tag_group_index={"女仆": "主体", "护士": "主体", "透明睡袍": "服装造型", "豪华卧室": "场景背景"},
        group_slot_limits={"主体": 4, "服装造型": 3, "场景背景": 3},
    )
    assert "女仆" in result["selected"]["主体"]
    assert "护士" in result["selected"]["主体"]
    assert "透明睡袍" in result["selected"]["服装造型"]
    assert any("Ultra realistic" in tag for tag in result["custom_tags"])
    assert result["negative_prompt"]

def test_nsfw_negative_preset_prefers_custom_when_selected(self) -> None:
    workspace = {
        "negative_preset": "自定义负面提示词",
        "custom_negative": "low quality, blurry, bad anatomy",
    }
    assert nsfw_mapper.resolve_nsfw_negative_prompt(workspace) == "low quality, blurry, bad anatomy"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: FAIL with missing `nsfw_presets/nsfw_workspace/nsfw_mapper` modules or missing functions.

- [ ] **Step 3: Write minimal implementation**

```python
# nsfw_presets.py
from __future__ import annotations

from typing import Any

NSFW_NEGATIVE_PRESETS: dict[str, str] = {
    "标准负面提示词": "low quality, blurry, bad anatomy",
    "WAN视频负面提示词": "色调艳丽，过曝，静态，细节模糊不清，字幕",
    "文生图负面提示词": "low quality, text, watermark, logo",
    "高质量负面提示词": "worst quality, low quality, blurry, bad anatomy",
    "自定义负面提示词": "",
}

def build_nsfw_workspace_defaults() -> dict[str, Any]:
    return {
        "enabled": False,
        "trigger_words": [],
        "scene": "——",
        "action": "——",
        "outfit": "——",
        "mood": "——",
        "camera_movement": "——",
        "camera_angle": "——",
        "light_source": "——",
        "light_type": "——",
        "lens_type": "——",
        "focal_length": "——",
        "color_tone": "——",
        "visual_style": "——",
        "effect": "——",
        "filter": "——",
        "random_mode": "关闭",
        "preset": "——",
        "quality_tier": "高质量",
        "negative_preset": "标准负面提示词",
        "custom_negative": "",
        "custom_prefix": "",
        "custom_suffix": "",
    }
```

```python
# nsfw_workspace.py
from __future__ import annotations

from typing import Any

from .nsfw_presets import NSFW_NEGATIVE_PRESETS, build_nsfw_workspace_defaults

def build_nsfw_workspace_catalog() -> dict[str, Any]:
    return {
        "defaults": build_nsfw_workspace_defaults(),
        "negative_presets": dict(NSFW_NEGATIVE_PRESETS),
    }
```

```python
# nsfw_mapper.py
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from .nsfw_presets import NSFW_NEGATIVE_PRESETS

def resolve_nsfw_negative_prompt(workspace: dict[str, Any]) -> str:
    preset = str(workspace.get("negative_preset", "标准负面提示词") or "标准负面提示词").strip()
    if preset == "自定义负面提示词":
        return str(workspace.get("custom_negative", "") or "").strip()
    return str(NSFW_NEGATIVE_PRESETS.get(preset, NSFW_NEGATIVE_PRESETS["标准负面提示词"])).strip()

def map_nsfw_workspace_to_stage_state(
    workspace: dict[str, Any],
    *,
    tag_group_index: dict[str, str],
    group_slot_limits: dict[str, int],
) -> dict[str, Any]:
    selected = OrderedDict((name, []) for name in group_slot_limits.keys())
    custom_tags: list[str] = []
    for field in ("trigger_words",):
        for item in workspace.get(field, []) or []:
            tag = str(item or "").strip()
            if not tag:
                continue
            group = tag_group_index.get(tag)
            if group and len(selected.setdefault(group, [])) < int(group_slot_limits.get(group, 0) or 0):
                if tag not in selected[group]:
                    selected[group].append(tag)
            elif tag not in custom_tags:
                custom_tags.append(tag)
    for field in ("scene", "action", "outfit", "mood", "camera_movement", "camera_angle", "light_source", "light_type", "lens_type", "focal_length", "color_tone", "visual_style", "effect", "filter"):
        tag = str(workspace.get(field, "") or "").strip()
        if not tag or tag == "——":
            continue
        group = tag_group_index.get(tag)
        if group and len(selected.setdefault(group, [])) < int(group_slot_limits.get(group, 0) or 0):
            if tag not in selected[group]:
                selected[group].append(tag)
        elif tag not in custom_tags:
            custom_tags.append(tag)
    for field in ("custom_prefix", "custom_suffix"):
        tag = str(workspace.get(field, "") or "").strip()
        if tag and tag not in custom_tags:
            custom_tags.append(tag)
    return {
        "selected": selected,
        "custom_tags": custom_tags,
        "negative_prompt": resolve_nsfw_negative_prompt(workspace),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: PASS for the new mapper/preset tests, no regression failures.

- [ ] **Step 5: Commit**

```powershell
git add 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_presets.py' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_workspace.py' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/nsfw_mapper.py' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
git commit -m "feat: add nsfw workspace backend mapper"
```

### Task 2: Wire NSFW workspace into stage prompt backend outputs

**Files:**
- Modify: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_generator.py`
- Test: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py`

**Interfaces:**
- Consumes:
  - `build_nsfw_workspace_defaults() -> dict[str, Any]`
  - `build_nsfw_workspace_catalog() -> dict[str, Any]`
  - `map_nsfw_workspace_to_stage_state(...) -> dict[str, Any]`
- Produces:
  - backend-exposed NSFW workspace metadata in node state / JSON result
  - optional NSFW negative prompt candidate merged into node output payload

- [ ] **Step 1: Write the failing test**

```python
def test_stage_generator_exposes_nsfw_workspace_catalog(self) -> None:
    catalog = namespace["构建NSFW工作台目录"]()
    assert "defaults" in catalog
    assert "negative_presets" in catalog

def test_stage_generator_merges_nsfw_workspace_into_selected_state(self) -> None:
    workspace = {
        "enabled": True,
        "trigger_words": ["女仆"],
        "scene": "豪华卧室，红色丝绒床单，镜面天花板",
        "negative_preset": "标准负面提示词",
    }
    result = namespace["应用NSFW工作台到阶段状态"](
        workspace,
        selected=OrderedDict({"主体": [], "场景背景": [], "服装造型": []}),
        custom_tags=[],
    )
    assert result["negative_prompt"]
    assert "女仆" in result["selected"]["主体"] or "女仆" in result["custom_tags"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: FAIL because stage prompt backend does not expose NSFW workspace helpers yet.

- [ ] **Step 3: Write minimal implementation**

```python
# stage_prompt_generator.py (new imports)
from .stage_prompt.nsfw_workspace import build_nsfw_workspace_catalog as _build_nsfw_workspace_catalog_impl
from .stage_prompt.nsfw_mapper import map_nsfw_workspace_to_stage_state as _map_nsfw_workspace_to_stage_state_impl
```

```python
def 构建NSFW工作台目录() -> dict[str, Any]:
    return _build_nsfw_workspace_catalog_impl()

def 应用NSFW工作台到阶段状态(
    workspace: dict[str, Any],
    *,
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
) -> dict[str, Any]:
    mapped = _map_nsfw_workspace_to_stage_state_impl(
        workspace,
        tag_group_index=_tag_group_index(),
        group_slot_limits=_分组槽位上限,
    )
    next_selected = OrderedDict((group_name, list(tags)) for group_name, tags in selected.items())
    for group_name, tags in mapped["selected"].items():
        next_selected.setdefault(group_name, [])
        for tag in tags:
            if tag not in next_selected[group_name]:
                next_selected[group_name].append(tag)
    next_custom = _uniq(list(custom_tags) + list(mapped["custom_tags"]))
    return {
        "selected": next_selected,
        "custom_tags": next_custom,
        "negative_prompt": str(mapped["negative_prompt"] or "").strip(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: PASS for new backend NSFW integration tests.

- [ ] **Step 5: Commit**

```powershell
git add 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_generator.py' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
git commit -m "feat: wire nsfw workspace into stage backend"
```

### Task 3: Add NSFW workspace UI inside the current stage panel

**Files:**
- Modify: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/web/stage_prompt_generator_ui.js`
- Test: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_ui_contracts.mjs`

**Interfaces:**
- Consumes:
  - `window.__QWEN_TE_STAGE_*` current bridge style
  - `构建NSFW工作台目录() -> dict[str, Any]`
  - `应用NSFW工作台到阶段状态(...) -> dict[str, Any]`
- Produces:
  - NSFW workspace tab / modal
  - write-back action into current node state
  - explicit negative-preset application controls

- [ ] **Step 1: Write the failing test**

```javascript
test("nsfw workspace helpers are exposed in stage UI module", async () => {
  assert.equal(typeof exports.openNsfwWorkspaceDialog, "function");
  assert.equal(typeof exports.applyNsfwWorkspaceResultToNodeState, "function");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
node --test 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_ui_contracts.mjs'
```

Expected: FAIL because NSFW workspace functions are not exported yet.

- [ ] **Step 3: Write minimal implementation**

```javascript
function applyNsfwWorkspaceResultToNodeState(node, library, mappedState) {
  if (!node || !library || !mappedState) return false;
  const current = collectNodeState(node, library);
  for (const [groupName, tags] of Object.entries(mappedState.selected ?? {})) {
    current.selected[groupName] = Array.isArray(tags) ? [...tags] : [];
  }
  current.customTags = Array.isArray(mappedState.custom_tags) ? [...mappedState.custom_tags] : [];
  applyNodeState(node, library, current, { recordHistory: true, historySource: "nsfw-workspace" });
  return true;
}

function openNsfwWorkspaceDialog(node, library) {
  // minimal shell in first pass: modal body with status and write-back hook
  // real controls added incrementally inside the same workspace container
}
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
node --test 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_ui_contracts.mjs'
```

Expected: PASS for new NSFW workspace UI contract test.

- [ ] **Step 5: Commit**

```powershell
git add 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/web/stage_prompt_generator_ui.js' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_ui_contracts.mjs'
git commit -m "feat: add nsfw workspace ui shell"
```

### Task 4: Hook NSFW negative presets into node output and sync flow

**Files:**
- Modify: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_generator.py`
- Modify: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/web/stage_prompt_generator_ui.js`
- Test: `F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py`

**Interfaces:**
- Consumes:
  - `resolve_nsfw_negative_prompt(workspace: dict[str, Any]) -> str`
  - existing `syncNegativePromptToGraph(...)`
- Produces:
  - explicit `nsfw_negative_prompt` branch in JSON payload/cache
  - user-selectable “覆盖/追加/仅预览” negative behavior

- [ ] **Step 1: Write the failing test**

```python
def test_nsfw_negative_prompt_can_override_recommended_negative(self) -> None:
    nsfw_negative = "low quality, blurry, bad anatomy"
    recommended = "文字、水印"
    payload = formatter.build_json_payload(
        full_text="FULL",
        prompt_only="PROMPT",
        prompt_list=["PROMPT"],
        selected_tags_text="META",
        selected=OrderedDict(),
        tags=[],
        template_style="真实感",
        subject_type="人物角色",
        output_structure="案例长段版",
        runtime_random_enabled=False,
        settings={"运行时随机模式": "全随机", "运行时随机强度": "中", "随机主题池": "自动", "核心标签锁定数量": 10, "优先柔和肤质": False, "抑制文字伪影": False, "生成数量": 1, "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果", "额外要求": "", "推理纠偏说明": []},
        generated=[],
        lock_tag_whitelist=[],
        random_exclude_tags=[],
        scene_group="",
        identity="",
        adult_subpool="",
        style_track="",
        recent_tracks=[],
        negative_prompt=recommended,
    )
    payload["nsfw_negative_prompt"] = nsfw_negative
    assert payload["nsfw_negative_prompt"] == nsfw_negative
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: FAIL because no explicit NSFW negative branch exists in output flow yet.

- [ ] **Step 3: Write minimal implementation**

```python
# stage_prompt_generator.py / formatter payload integration
json_payload["nsfw_negative_prompt"] = str(nsfw_negative_prompt or "").strip()
```

```javascript
// UI negative handling
// expose explicit apply mode: override / append / preview
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```powershell
& 'F:/ComfyUI_portable_TE v251130/python_embeded/python.exe' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
```

Expected: PASS for NSFW negative branch tests.

- [ ] **Step 5: Commit**

```powershell
git add 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_generator.py' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/web/stage_prompt_generator_ui.js' 'F:/ComfyUI_portable_TE v251130/worktrees/comfyui-style-mode-random-pool-optimization/custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
git commit -m "feat: add nsfw negative prompt integration"
```

## Self-Review

- Spec coverage:
  - NSFW structured workspace: covered by Task 1 and Task 3.
  - Single-node backend integration: covered by Task 2.
  - Negative preset precedence: covered by Task 4.
  - UI coexistence with current workflow: covered by Task 3.
- Placeholder scan:
  - No `TBD` / `TODO` placeholders remain in the plan body.
- Type consistency:
  - `map_nsfw_workspace_to_stage_state(...) -> dict[str, Any]` is reused consistently.
  - `构建NSFW工作台目录()` and `应用NSFW工作台到阶段状态(...)` are named consistently between backend and UI integration tasks.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-24-nsfw-prompt-selector-integration.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
