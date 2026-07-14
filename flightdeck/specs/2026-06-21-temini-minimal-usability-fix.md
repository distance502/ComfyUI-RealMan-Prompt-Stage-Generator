---
status: active
summary: 以最小改动修正 TEmini 与主面板的语义漂移、反馈缺失和危险操作不一致。
last_updated: 2026-06-21
---

# TEmini Minimal Usability Fix

## Goal

Improve the `TEMini` toolbar without changing the overall layout or expanding scope beyond the highest-value usability issues.

## Problem

The current `TEMini` toolbar is fast to use, but several high-frequency actions no longer match the main panel:

- `随机` in mini toggles runtime random mode, while `随机` in the main panel generates a fresh random state.
- `复制` in mini copies selected tags, while `复制` in the main panel copies the latest positive prompt output.
- `入队` has no explicit success/failure feedback.
- `清空` clears all current tag selections without a confirmation step.
- The mini header status prioritizes UI fold state (`槽位收起 / 参数收起`) over operational state.

These mismatches increase relearning cost and make the mini panel feel less trustworthy than the main panel.

## Scope

This fix is intentionally minimal.

Included:

- Align mini `随机` with the main panel semantic: generate a fresh random state without auto-queue.
- Align mini `复制` with the main panel semantic: copy the latest positive prompt output.
- Keep mini `入队` in place, but add explicit success/failure feedback.
- Keep mini `清空` limited to current tag/custom-tag clearing, but add confirmation.
- Rework the mini header status text to prefer operational state over fold-state noise.

Excluded:

- No layout redesign.
- No new buttons.
- No removal of existing `柔肤 / 抑字 / 槽位 / 高级`.
- No full cross-panel wording redesign.
- No changes to the main stage panel behavior.

## Proposed behavior

### Button semantics

- `随机`
  - Generates a fresh random state using the same random-state path as the main panel.
  - Does not queue automatically.
  - Produces a short success status.

- `复制`
  - Copies the latest positive prompt output.
  - If no output exists yet, shows a clear “run first” message.
  - If clipboard access fails, shows a failure status.

- `入队`
  - Keeps current placement and purpose.
  - Always reports whether queueing succeeded.

- `清空`
  - Keeps current data scope: clear current raw tag slots and custom tag input only.
  - Requires confirmation before destructive action.
  - Reports cancel/success state explicitly.

### Header/meta status

Replace the current status line pattern:

- `已选 X · 槽位收起 · 参数收起`

With a more operational summary:

- `已选 X · 随机 ON · 抑字 ON`
- `已选 X · 未生成`
- `已选 X · 可复制正向`

Short-lived action feedback may temporarily replace the base summary, then the base summary can be recomputed on refresh.

## Files expected to change

- `web/stage_prompt_generator_mini_toolbar.js`

No other file is required for the minimal fix unless implementation reuse from the main panel is needed.

## Validation

Manual validation is enough for this scoped fix:

1. `随机` updates tags/state and does not auto-queue.
2. `复制` copies positive prompt output, not selected tags.
3. `复制` shows a “run first” message when no output exists.
4. `入队` reports success/failure.
5. `清空` asks for confirmation and supports cancel.
6. Header/meta line reflects operational state rather than fold-state only.

## Notes

- This repository currently lacks `git` in the active environment, so this spec can be written locally but not committed from the current session.
- If this minimal fix works well, the next follow-up can be a broader terminology unification pass across mini and main surfaces.
