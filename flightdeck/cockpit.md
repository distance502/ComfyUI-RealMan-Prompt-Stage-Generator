# Cockpit — ComfyUI-RealMan-Prompt-Stage-Generator

**Last updated**: 2026-06-21 by Codex
**Active focus**: TEmini minimal usability fix planning complete; next step is scoped frontend implementation in `stage_prompt_generator_mini_toolbar.js`

## 进行中

<!-- AUTO:inprogress -->
- [2026-06-18-style-mode-random-pool-optimization.md](specs/2026-06-18-style-mode-random-pool-optimization.md) — 隔离随机主题池与模板风格变量，建立可复跑的风格差异测试，并增强不同风格模式的提示词与出图分化。
- [2026-06-18-style-mode-random-pool-execution.md](plans/2026-06-18-style-mode-random-pool-execution.md) — 分阶段建立风格隔离测试、强化风格 profile，并验证随机主题池对风格差异的干扰是否下降。
- [2026-06-21-temini-minimal-usability-fix.md](specs/2026-06-21-temini-minimal-usability-fix.md) — 以最小改动修正 TEmini 与主面板的语义漂移、反馈缺失和危险操作不一致。
- [2026-06-21-temini-minimal-usability-fix-execution.md](plans/2026-06-21-temini-minimal-usability-fix-execution.md) — 按最小改动实现 TEmini 的语义统一、反馈补齐和清空确认。
<!-- /AUTO -->

## 下一步

- 实现 `web/stage_prompt_generator_mini_toolbar.js` 的 A 方案：统一 mini `随机/复制` 语义，补 `入队` 反馈、`清空` 确认与顶部运行状态。

## 关键上下文

- Local automated verification is green for fixtures, regression-runner helpers, and prompt-builder behavior.
- Live `style_mode` regression is green on `final_style_mode_v2`: all 5 cases completed with `stage=success` and `evaluation.ok=true`.
- `run_template_example_suite.py` completed and refreshed `template_example_suite_report.json` plus `template_example_suite_sheet.png`.
- Implementation tasks 1-6 are complete in the isolated worktree.
- `TEMini` review identified four high-value usability issues: semantic drift for `随机/复制`, missing mini feedback for `复制/入队`, missing confirm on `清空`, and low-value fold-state noise in the mini header.
- `flightdeck_new.py` could not be used directly in this session due to a local `flightdeck_index` import-path issue, so the TEmini plan artifact was authored manually in the existing deck structure.

## Hanging tasks

- (none)
