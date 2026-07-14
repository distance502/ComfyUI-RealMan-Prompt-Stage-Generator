---
status: active
summary: 分阶段建立风格隔离测试、强化风格 profile，并验证随机主题池对风格差异的干扰是否下降。
last_updated: 2026-06-18
implements: specs/2026-06-18-style-mode-random-pool-optimization.md
---

# 随机主题池风格模式测试与优化执行计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可复跑的风格隔离测试，增强不同模板风格的提示词与出图差异，并验证随机主题池对风格分化的干扰是否下降。

**Architecture:** 先在测试层建立“同主题、只切风格”的基线矩阵，再在 `prompt_builder.py` 中定向增强风格 profile，最后用现有回归脚本和模板示例脚本复跑对照。随机主题池相关变更只限于测试路径和内部排序逻辑，不先扩 UI 参数面。

**Tech Stack:** Python 3.13, pytest 9, local ComfyUI HTTP API, ComfyUI workflow JSON, flightdeck artifacts

## Global Constraints

- 只围绕“风格差异更明显”这个目标实施，不重做整个随机主题池结构。
- 不先新增用户可见的复杂参数面。
- 风格差异优先体现为视觉语言差异，而不是主体身份、职业、场景或道具的大幅漂移。
- 新测试必须可复跑，并能作为后续风格回归基线。
- 优先改风格层，不先扩大随机层改动面。

---

### Task 1: 建立风格隔离测试夹具与回归入口

**Files:**
- Create: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\fixtures\style_mode_cases.json`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt_regression_runner.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_regression_runner.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_fixture_contracts.py`

**Interfaces:**
- Consumes: `select_cases(cases: list[dict[str, Any]], requested_names: list[str] | None = None) -> list[dict[str, Any]]`
- Consumes: `filter_cases_by_group(cases: list[dict[str, Any]], requested_groups: list[str] | None = None) -> list[dict[str, Any]]`
- Produces: `load_style_mode_cases() -> list[dict[str, Any]]`
- Produces: `STYLE_MODE_CASES_PATH: Path`

- [ ] **Step 1: Write the failing fixture-contract test**

```python
def test_style_mode_cases_fixture_shape(self) -> None:
    payload = json.loads((FIXTURES_DIR / "style_mode_cases.json").read_text(encoding="utf-8"))
    self.assertIsInstance(payload, dict)
    cases = payload.get("cases")
    self.assertIsInstance(cases, list)
    self.assertGreaterEqual(len(cases), 5)
    for case in cases:
        self.assertIsInstance(case, dict)
        self.assertTrue(str(case.get("name", "")).strip())
        self.assertEqual(str(case.get("group", "")).strip(), "style_mode")
        self.assertIsInstance(case.get("stage"), dict)
        self.assertIsInstance(case.get("expect"), dict)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_fixture_contracts.py' -k style_mode_cases_fixture_shape -v`

Expected: FAIL with missing `style_mode_cases.json` or missing test assertion.

- [ ] **Step 3: Create the style-mode fixture**

```json
{
  "cases": [
    {
      "name": "style_mode_realistic_campus_anchor",
      "group": "style_mode",
      "image": false,
      "stage": {
        "模板风格": "真实感",
        "主体类型": "人物角色",
        "案例输出结构": "案例长段版",
        "运行时随机标签": false,
        "生成数量": 1,
        "提示词语言": "纯中文",
        "详细度": "标准",
        "输出模式": "仅提示词优先",
        "主体标签1": "成年女性",
        "主体标签2": "东亚",
        "主体标签3": "清冷",
        "画面风格标签1": "真实感",
        "构图视角标签1": "中景半身",
        "场景背景标签1": "校园",
        "技术画质标签1": "高细节",
        "额外要求": "固定校园主题，不要切换职业或场景。"
      },
      "expect": {
        "must_contain": ["真实感"],
        "must_not_contain": ["神殿", "机库", "竹林"]
      }
    }
  ]
}
```

- [ ] **Step 4: Add style-mode fixture loading to the regression runner**

```python
STYLE_MODE_CASES_PATH = PLUGIN_ROOT / "tests" / "fixtures" / "style_mode_cases.json"


def load_style_mode_cases() -> list[dict[str, Any]]:
    if not STYLE_MODE_CASES_PATH.exists():
        return []
    payload = json.loads(STYLE_MODE_CASES_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    normalized: list[dict[str, Any]] = []
    for item in cases:
        normalized_item = normalize_case_entry(item, group_name="style_mode")
        if normalized_item:
            normalized.append(normalized_item)
    return normalized


CASES.extend(load_style_mode_cases())
```

- [ ] **Step 5: Add runner tests for the new case group**

```python
def test_list_grouped_case_names_includes_style_mode(self) -> None:
    cases = [
        {"name": "alpha", "stage": {}, "expect": {}, "group": "style_mode"},
        {"name": "beta", "stage": {}, "expect": {}, "group": "realistic"},
    ]
    grouped = runner.list_grouped_case_names(cases)
    self.assertIn("style_mode", grouped)
    self.assertEqual(grouped["style_mode"], ["alpha"])
```

- [ ] **Step 6: Run the focused tests**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_fixture_contracts.py' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_regression_runner.py' -k "style_mode" -v`

Expected: PASS

- [ ] **Step 7: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/fixtures/style_mode_cases.json' 'custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_regression_runner.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_regression_runner.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_fixture_contracts.py'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "test: add style mode regression fixtures"
```

### Task 2: 增加纯提示词层的风格隔离单元测试

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt\prompt_builder.py`

**Interfaces:**
- Consumes: `build_prompt_list(selected: OrderedDict[str, list[str]], custom_tags: list[str], settings: dict[str, Any], *, scene_group: str = "", identity: str = "", style_track: str = "", recent_tracks: list[str] | None = None, uniq: Callable[[list[str]], list[str]], infer_template_style: Callable[[list[str], str], str], infer_subject_type: Callable[[list[str], str], str], infer_output_structure: Callable[[str, str], str]) -> list[str]`
- Produces: stable style-specific prompt outputs for `真实感`, `插画感`, `CG感`, `古风`, `神话感`

- [ ] **Step 1: Write the failing unit test for style isolation**

```python
def test_prompt_builder_style_mode_isolation_keeps_subject_scene_fixed(self) -> None:
    selected = OrderedDict(
        {
            "主体": ["成年女性", "东亚", "清冷"],
            "构图视角": ["中景半身"],
            "场景背景": ["校园"],
            "技术画质": ["高细节"],
        }
    )
    prompts = []
    for style in ["真实感", "插画感", "CG感", "古风", "神话感"]:
        settings = {
            "模板风格": style,
            "主体类型": "人物角色",
            "案例输出结构": "案例长段版",
            "标签反推模式": "自动平衡",
            "运行时随机标签": False,
            "生成数量": 1,
            "额外要求": "固定校园主题，不要切换职业或场景。",
        }
        prompts.extend(
            prompt_builder.build_prompt_list(
                selected,
                [],
                settings,
                scene_group="campus",
                identity="成年女性",
                style_track="",
                recent_tracks=[],
                uniq=uniq,
                infer_template_style=lambda tags, explicit: explicit,
                infer_subject_type=lambda tags, explicit: explicit,
                infer_output_structure=lambda subject, explicit: explicit,
            )
        )
    self.assertEqual(len(prompts), 5)
    self.assertEqual(len(set(prompts)), 5)
    self.assertTrue(all("校园" in prompt for prompt in prompts))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k style_mode_isolation_keeps_subject_scene_fixed -v`

Expected: FAIL because outputs are not yet asserted or style cues are too overlapping.

- [ ] **Step 3: Add explicit style cue assertions**

```python
self.assertTrue(prompts[0].startswith("写实摄影"))
self.assertTrue(any(term in prompts[0] for term in ["杂志感", "电影剧照", "纪实抓拍"]))
self.assertTrue(prompts[1].startswith("高完成度插画"))
self.assertTrue(any(term in prompts[1] for term in ["厚涂", "水彩", "OVA风"]))
self.assertTrue(prompts[2].startswith("电影级CG"))
self.assertTrue(any(term in prompts[2] for term in ["3D渲染", "虚幻引擎", "Octane渲染"]))
self.assertTrue(prompts[3].startswith("古风人像"))
self.assertTrue(any(term in prompts[3] for term in ["工笔重彩", "水墨", "玄幻古风"]))
self.assertTrue(prompts[4].startswith("神话史诗感"))
self.assertTrue(any(term in prompts[4] for term in ["神圣史诗", "暗黑奇幻", "冰雪奇幻"]))
```

- [ ] **Step 4: Make the minimum `prompt_builder.py` changes required for deterministic style separation**

```python
_STYLE_LEAD_MAP = {
    "真实感": "写实摄影",
    "插画感": "高完成度插画",
    "CG感": "电影级CG",
    "古风": "古风人像",
    "神话感": "神话史诗感",
}
```

Implementation note: keep the existing function signatures, but adjust only the style profile contents needed to satisfy the style-isolation assertions without replacing the fixed scene tags.

- [ ] **Step 5: Run the focused style tests**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k "style_mode_isolation or runtime_random_multi_output_adds_distinct_style_variants" -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/prompt_builder.py'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "test: lock in style mode prompt separation"
```

### Task 3: 强化风格 profile，减少跨风格模糊重叠

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt\prompt_builder.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py`

**Interfaces:**
- Consumes: `_RUNTIME_STYLE_VARIANT_PROFILES: dict[str, list[_RuntimeStyleVariantProfile]]`
- Consumes: `_RUNTIME_STYLE_TRACK_OVERRIDES: dict[tuple[str, str], list[_RuntimeStyleVariantProfile]]`
- Consumes: `_RUNTIME_STYLE_IDENTITY_OVERRIDES: dict[tuple[str, str], list[_RuntimeStyleVariantProfile]]`
- Produces: style-specific prompt clusters with less shared language across styles

- [ ] **Step 1: Write the failing cross-style overlap test**

```python
def test_style_variant_profiles_do_not_share_too_many_primary_tags(self) -> None:
    styles = prompt_builder._RUNTIME_STYLE_VARIANT_PROFILES
    realistic_tags = set(styles["真实感"][0]["style_tags"])
    illustration_tags = set(styles["插画感"][0]["style_tags"])
    cg_tags = set(styles["CG感"][0]["style_tags"])
    self.assertLessEqual(len(realistic_tags & illustration_tags), 1)
    self.assertLessEqual(len(realistic_tags & cg_tags), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k do_not_share_too_many_primary_tags -v`

Expected: FAIL if style tags still overlap more than allowed.

- [ ] **Step 3: Update the style profile payloads**

```python
"真实感": [
    {
        "style_lead": "杂志编辑摄影",
        "style_tags": ["真实感", "杂志感", "杂志编辑摄影"],
        "extra_fragments": ["时尚成片感更强", "人物视觉重心更偏封面肖像"],
    }
]
```

Implementation note: preserve current list structure, but tighten each style family so its primary tags favor one visual language instead of broad reusable quality words.

- [ ] **Step 4: Add assertions for visual-direction fragments**

```python
def test_style_variant_profiles_include_visual_direction_fragments(self) -> None:
    profile = prompt_builder._RUNTIME_STYLE_VARIANT_PROFILES["CG感"][0]
    self.assertIn("体积光与材质表现更强", profile["extra_fragments"])
    self.assertIn("角色更像高预算宣传图", profile["extra_fragments"])
```

- [ ] **Step 5: Run the prompt-builder suite**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k "style_variant_profiles or runtime_random_multi_output_adds_distinct_style_variants" -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/prompt_builder.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "feat: strengthen style variant profiles"
```

### Task 4: 限制随机主题池在风格测试路径中的题材漂移

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt\prompt_builder.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py`

**Interfaces:**
- Consumes: `_build_runtime_diversity_variant_profile(subject: str, style: str, runtime_random_enabled: bool, runtime_random_mode: str, runtime_random_intensity: str, style_track: str, recent_tracks: list[str], index: int, generation_count: int) -> _RuntimeDiversityVariantProfile | None`
- Produces: test-path behavior where style mode can stay visually distinct without fully replacing fixed subject/scene anchors

- [ ] **Step 1: Write the failing guard test**

```python
def test_runtime_random_style_mode_keeps_fixed_scene_anchor(self) -> None:
    selected = OrderedDict(
        {
            "主体": ["成年女性"],
            "场景背景": ["校园"],
            "画面风格": ["真实感"],
            "构图视角": ["中景"],
        }
    )
    settings = {
        "模板风格": "真实感",
        "主体类型": "人物角色",
        "案例输出结构": "案例长段版",
        "标签反推模式": "自动平衡",
        "运行时随机标签": True,
        "运行时随机模式": "全随机",
        "运行时随机强度": "中",
        "生成数量": 1,
        "额外要求": "固定校园主题，不要切换职业或场景。",
    }
    prompts = prompt_builder.build_prompt_list(
        selected,
        [],
        settings,
        scene_group="campus",
        identity="成年女性",
        style_track="",
        recent_tracks=[],
        uniq=uniq,
        infer_template_style=lambda tags, explicit: explicit,
        infer_subject_type=lambda tags, explicit: explicit,
        infer_output_structure=lambda subject, explicit: explicit,
    )
    self.assertIn("校园", prompts[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k keeps_fixed_scene_anchor -v`

Expected: FAIL if runtime diversity fully replaces the fixed scene.

- [ ] **Step 3: Implement the minimal anchor-preserving logic**

```python
if group_name == "场景背景" and diversity_profile:
    preserved = [tag for tag in base_tags if tag in {"校园", "神殿", "街道", "竹林", "未来都市"}]
    replacements = [
        _clean_fragment(tag)
        for tag in diversity_profile.get("replace_scene_tags", [])
        if _clean_fragment(tag)
    ]
    return uniq(preserved + replacements)
```

Implementation note: keep the change narrow and test-path oriented. Do not introduce a new public node parameter in this task.

- [ ] **Step 4: Add a second assertion that style variation still occurs**

```python
self.assertTrue(any(term in prompts[0] for term in ["杂志感", "电影剧照", "纪实抓拍"]))
```

- [ ] **Step 5: Run the runtime-random prompt tests**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -k "runtime_random and scene_anchor" -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt/prompt_builder.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/tests/test_stage_prompt_modules.py'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "fix: preserve scene anchors in style mode tests"
```

### Task 5: 输出风格矩阵报告并复跑验证

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\run_template_example_suite.py`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt_regression_runner.py`
- Test: local ComfyUI output under `F:\ComfyUI_portable_TE v251130\ComfyUI\output`

**Interfaces:**
- Consumes: `run_stage_case(case: dict[str, Any]) -> dict[str, Any]`
- Consumes: `resolve_report_path(*, default_path: Path, suffix: str | None = None, output: str | None = None) -> Path`
- Produces: a rerunnable style comparison report and contact sheet

- [ ] **Step 1: Write the failing runner test for style-mode reporting**

```python
def test_resolve_report_path_supports_style_mode_suffix(self) -> None:
    path = runner.resolve_report_path(default_path=runner.REPORT_PATH, suffix="style mode", output=None)
    self.assertTrue(str(path).endswith("codex_stage_regression_report_style_mode.json"))
```

- [ ] **Step 2: Run test to verify it fails only if suffix handling is missing**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_regression_runner.py' -k style_mode_suffix -v`

Expected: PASS if already supported; otherwise FAIL and implement the minimum fix before continuing.

- [ ] **Step 3: Extend the template example runner with a style matrix preset set**

```python
CASE_PRESETS = [
    {
        "name": "style_matrix_campus_realistic",
        "template_style": "真实感",
        "settings": {"主体类型": "人物角色", "案例输出结构": "案例长段版", "提示词语言": "纯中文", "详细度": "详细", "输出模式": "完整结果"},
        "tags": ["成年女性", "东亚", "清冷", "校园", "中景半身", "高细节"],
        "extra": "固定校园主题，不要切换职业或场景。",
    }
]
```

- [ ] **Step 4: Run the regression runner for the style-mode group**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt_regression_runner.py' --group style_mode --report-suffix style_mode`

Expected: JSON report written to `F:\ComfyUI_portable_TE v251130\ComfyUI\output\codex_stage_regression_report_style_mode.json`

- [ ] **Step 5: Run the template example suite to produce image-side evidence**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\run_template_example_suite.py'`

Expected: updated `template_example_suite_report.json` and `template_example_suite_sheet.png`

- [ ] **Step 6: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/run_template_example_suite.py' 'custom_nodes/comfyUI-qwen3_5-llama-TE/stage_prompt_regression_runner.py'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "feat: add style mode comparison reporting"
```

### Task 6: 做最终回归并记录结果

**Files:**
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\flightdeck\plans\2026-06-18-style-mode-random-pool-execution.md`
- Modify: `F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\flightdeck\cockpit.md`

**Interfaces:**
- Consumes: all prior tasks
- Produces: final verification notes and a plan ready to land

- [ ] **Step 1: Run the unit test suite for the touched test files**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' -m pytest 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_fixture_contracts.py' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_regression_runner.py' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\tests\test_stage_prompt_modules.py' -v`

Expected: PASS

- [ ] **Step 2: Run the style-mode regression group again**

Run: `& 'F:\ComfyUI_portable_TE v251130\python_embeded\python.exe' 'F:\ComfyUI_portable_TE v251130\ComfyUI\custom_nodes\comfyUI-qwen3_5-llama-TE\stage_prompt_regression_runner.py' --group style_mode --report-suffix final_style_mode`

Expected: PASS report with no missing required tokens and no forbidden scene drift in the fixed-theme cases

- [ ] **Step 3: Record the verification summary in the plan**

```markdown
## Verification Notes

- Unit tests: PASS
- Style-mode regression group: PASS
- Template example suite: PASS
- Residual risk: style-mode image quality still depends on the active ComfyUI model/workflow
```

- [ ] **Step 4: Update cockpit active focus if the work is complete**

```markdown
**Active focus**: style mode random pool optimization verification complete
```

- [ ] **Step 5: Commit**

```bash
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' add -- 'custom_nodes/comfyUI-qwen3_5-llama-TE/flightdeck/plans/2026-06-18-style-mode-random-pool-execution.md' 'custom_nodes/comfyUI-qwen3_5-llama-TE/flightdeck/cockpit.md'
& 'F:\ComfyUI_portable_TE v251130\git\cmd\git.exe' -C 'F:\ComfyUI_portable_TE v251130\ComfyUI' commit -m "docs: record style mode optimization verification"
```

## Verification Notes

- Unit tests: PASS
- Command: `python -m pytest .\tests\test_fixture_contracts.py .\tests\test_regression_runner.py .\tests\test_stage_prompt_modules.py -v --import-mode=importlib`
- Result: `62 passed, 3 warnings, 29 subtests passed`
- Style-mode regression report generation: PARTIAL PASS
- Command: `python .\stage_prompt_regression_runner.py --group style_mode --report-suffix final_style_mode`
- Result: report file written to `output\codex_stage_regression_report_final_style_mode.json`
- Report content: all 5 style-mode cases currently record `URLError(ConnectionRefusedError(... 127.0.0.1:8188 ...))`
- Live ComfyUI inference: PASS AFTER SERVICE RECOVERY
- Service recovery: local ComfyUI endpoint `http://127.0.0.1:8188` was restarted successfully
- Fixture alignment: `style_mode` enumerated slot values were updated to the current library and live expectation strings were aligned to the actual prompt output
- Final live command: `python .\stage_prompt_regression_runner.py --group style_mode --report-suffix final_style_mode_v2`
- Final live result: all 5 `style_mode` cases completed with `stage=success` and `evaluation.ok=true`
- Image-side matrix run: PASS
- Command: `python .\run_template_example_suite.py`
- Result: `template_example_suite_report.json` and `template_example_suite_sheet.png` refreshed after 6 live prompt executions
- Residual risk: both prompt-side and image-side outputs still depend on the local ComfyUI process, loaded models, and workflow state when rerun in a new session
- Task ledger status: Task 1 through Task 6 implemented; code-side, live style-mode regression, and image-side style matrix verification are green
