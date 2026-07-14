# -*- coding: utf-8 -*-
"""Runtime randomization helpers for stage prompt generation."""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Callable

_AUTO_POOL_SUBJECT_GROUPS = {"主体"}
_AUTO_POOL_SCENE_GROUPS = {"场景背景"}
_REWRITE_SUBJECT_SCENE_GROUPS = _AUTO_POOL_SUBJECT_GROUPS | _AUTO_POOL_SCENE_GROUPS
_RUNTIME_RANDOM_MODE_AUTO = "自动判断"
_RUNTIME_RANDOM_MODE_REWRITE_SUBJECT_SCENE = "重写主体与场景"


def _count_setting_tags(raw: Any) -> int:
    return len(
        [
            part.strip()
            for part in str(raw or "").replace("\n", ",").replace("，", ",").split(",")
            if part.strip()
        ]
    )


def _apply_whitelist(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    whitelist: list[str],
    resolved_tag_group_index: dict[str, str],
    group_slots: dict[str, int],
) -> None:
    for raw_tag in whitelist:
        tag = str(raw_tag).strip()
        if not tag:
            continue
        group = resolved_tag_group_index.get(tag)
        if group:
            bucket = selected.setdefault(group, [])
            if tag in bucket:
                continue
            if len(bucket) < group_slots.get(group, len(bucket) + 1):
                bucket.append(tag)
            elif tag not in custom_tags:
                custom_tags.append(tag)
            continue
        if tag not in custom_tags:
            custom_tags.append(tag)


def _clone_core_state_with_limit(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    *,
    groups: list[tuple[str, int, list[str]]],
    lock_count: int,
    whitelist: list[str],
    exclude: set[str],
    resolved_tag_group_index: dict[str, str],
    uniq: Callable[[list[str]], list[str]],
) -> tuple[OrderedDict[str, list[str]], list[str]]:
    next_selected = OrderedDict((group_name, []) for group_name, _, _ in groups)
    next_custom: list[str] = []
    whitelist_set = set(whitelist)
    group_slots = {group_name: slots for group_name, slots, _ in groups}
    used = 0

    def can_keep(tag: str) -> bool:
        return bool(tag) and (tag not in exclude or tag in whitelist_set)

    if lock_count > 0:
        for group_name, _, _ in groups:
            for raw_tag in selected.get(group_name, []):
                tag = str(raw_tag).strip()
                if used >= lock_count:
                    break
                if not can_keep(tag) or tag in next_selected[group_name]:
                    continue
                next_selected[group_name].append(tag)
                used += 1
            if used >= lock_count:
                break

        if used < lock_count:
            for raw_tag in custom_tags:
                tag = str(raw_tag).strip()
                if used >= lock_count:
                    break
                if not can_keep(tag) or tag in next_custom:
                    continue
                next_custom.append(tag)
                used += 1

    _apply_whitelist(next_selected, next_custom, whitelist, resolved_tag_group_index, group_slots)
    return next_selected, uniq(next_custom)


def _allowed_random_additions(current_count: int, slot_count: int, intensity: str) -> int:
    remaining = max(0, int(slot_count) - int(current_count))
    if remaining <= 0:
        return 0
    if intensity == "弱":
        return min(1, remaining)
    if intensity == "中":
        return min(2, remaining)
    return remaining


def _allowed_random_additions_for_group(
    group_name: str,
    current_count: int,
    slot_count: int,
    intensity: str,
    theme_pool: str,
    mode: str,
) -> int:
    additions = _allowed_random_additions(current_count, slot_count, intensity)
    return additions


def _preserve_rewrite_subject_scene_state(
    selected: OrderedDict[str, list[str]],
    *,
    groups: list[tuple[str, int, list[str]]],
    exclude: set[str],
    uniq: Callable[[list[str]], list[str]],
) -> OrderedDict[str, list[str]]:
    preserved = OrderedDict((group_name, []) for group_name, _, _ in groups)
    for group_name, slot_count, _ in groups:
        if group_name in _REWRITE_SUBJECT_SCENE_GROUPS:
            continue
        tags = [
            str(tag).strip()
            for tag in selected.get(group_name, [])
            if str(tag).strip() and str(tag).strip() not in exclude
        ]
        if not tags:
            continue
        preserved[group_name] = uniq(tags[: int(slot_count)])
    return preserved


def _preserve_rewrite_custom_tags(
    custom_tags: list[str],
    *,
    exclude: set[str],
    resolved_tag_group_index: dict[str, str],
    uniq: Callable[[list[str]], list[str]],
) -> list[str]:
    return uniq(
        [
            tag
            for raw_tag in custom_tags
            if (tag := str(raw_tag).strip())
            and tag not in exclude
            and resolved_tag_group_index.get(tag) not in _REWRITE_SUBJECT_SCENE_GROUPS
        ]
    )


def resolve_runtime_random_mode(
    mode: str,
    selected: OrderedDict[str, list[str]],
    settings: dict[str, Any],
) -> str:
    normalized_mode = str(mode or "").strip()
    if normalized_mode != _RUNTIME_RANDOM_MODE_AUTO:
        return normalized_mode or "全随机"

    subject_count = len([tag for tag in selected.get("主体", []) if str(tag).strip()])
    scene_count = len([tag for tag in selected.get("场景背景", []) if str(tag).strip()])
    composition_count = len([tag for tag in selected.get("构图视角", []) if str(tag).strip()])
    style_count = len([tag for tag in selected.get("画面风格", []) if str(tag).strip()])
    lock_count = max(0, int(settings.get("核心标签锁定数量", 0) or 0))
    whitelist_count = _count_setting_tags(settings.get("锁定标签白名单", ""))
    mainline_count = subject_count + scene_count + composition_count + style_count

    if style_count >= 1 and subject_count + scene_count >= 3:
        return _RUNTIME_RANDOM_MODE_REWRITE_SUBJECT_SCENE
    if whitelist_count > 0:
        return "保留已选核心标签"
    if (
        lock_count > 0
        and 0 < mainline_count <= max(3, min(lock_count, 4))
        and (subject_count > 0 or scene_count > 0 or composition_count > 0)
    ):
        return "保留已选核心标签"
    return "全随机"


def build_runtime_tags(
    selected: OrderedDict[str, list[str]],
    custom_tags: list[str],
    settings: dict[str, Any],
    *,
    all_tag_groups: Callable[[], list[tuple[str, int, list[str]]]],
    tag_group_index: Callable[[], dict[str, str]],
    parse_tags: Callable[[Any], list[str]],
    uniq: Callable[[list[str]], list[str]],
    seed_normalizer: Callable[[Any], int],
    history_loader: Callable[[str], list[str]],
    random_module: Any,
    empty_tag: str,
) -> tuple[OrderedDict[str, list[str]], list[str], list[str]]:
    groups = all_tag_groups()
    mode = resolve_runtime_random_mode(str(settings["运行时随机模式"]), selected, settings)
    intensity = str(settings.get("运行时随机强度", "中"))
    normalized_seed = seed_normalizer(settings["seed"])
    effective_seed = normalized_seed if normalized_seed not in {None, 0} else random_module.randint(1, 2**31 - 1)
    settings["运行时随机有效种子"] = int(effective_seed)
    rng = random_module.Random(effective_seed)
    history_key = settings.get("cache_key") if "cache_key" in settings else settings["unique_id"]
    history = history_loader(str(history_key or ""))
    resolved_tag_group_index = tag_group_index()
    raw_protected_tags = settings.get("运行时随机保护标签", [])
    if isinstance(raw_protected_tags, (list, tuple, set)):
        protected_tags = uniq([str(tag).strip() for tag in raw_protected_tags if str(tag).strip()])
    else:
        protected_tags = parse_tags(raw_protected_tags)
    whitelist = uniq([*parse_tags(settings["锁定标签白名单"]), *protected_tags])
    exclude = set(parse_tags(settings["随机排除标签"]))
    recent_supplement = set(parse_tags(settings["随机补充避重缓存"]))
    for raw_history_item in history:
        history_item = str(raw_history_item or "").strip()
        if not history_item:
            continue
        if history_item.startswith("diversity:"):
            continue
        if ":" in history_item:
            history_prefix, history_value = history_item.split(":", 1)
            if history_prefix.strip() in {"tag", "identity", "scene", "random"}:
                history_item = history_value.strip()
        recent_supplement.update(parse_tags(history_item))
    theme_pool = str(settings.get("随机主题池", "") or "").strip()
    generated: list[str] = []
    group_slots = {group_name: slots for group_name, slots, _ in groups}
    rewrite_subject_scene_mode = mode == _RUNTIME_RANDOM_MODE_REWRITE_SUBJECT_SCENE
    rewrite_group_excludes: dict[str, set[str]] = {}
    if rewrite_subject_scene_mode:
        rewrite_group_excludes = {
            "主体": {str(tag).strip() for tag in selected.get("主体", []) if str(tag).strip()},
            "场景背景": {str(tag).strip() for tag in selected.get("场景背景", []) if str(tag).strip()},
        }

    if mode == "保留已选核心标签":
        out_selected, out_custom = _clone_core_state_with_limit(
            selected,
            custom_tags,
            groups=groups,
            lock_count=max(0, int(settings.get("核心标签锁定数量", 0) or 0)),
            whitelist=whitelist,
            exclude=exclude,
            resolved_tag_group_index=resolved_tag_group_index,
            uniq=uniq,
        )
    else:
        out_selected = OrderedDict((group_name, []) for group_name, _, _ in groups)
        out_custom = []
        if rewrite_subject_scene_mode:
            preserved_selected = _preserve_rewrite_subject_scene_state(
                selected,
                groups=groups,
                exclude=exclude,
                uniq=uniq,
            )
            out_selected = OrderedDict((group_name, list(tags)) for group_name, tags in preserved_selected.items())
            out_custom = _preserve_rewrite_custom_tags(
                custom_tags,
                exclude=exclude,
                resolved_tag_group_index=resolved_tag_group_index,
                uniq=uniq,
            )
        _apply_whitelist(out_selected, out_custom, whitelist, resolved_tag_group_index, group_slots)

    for name, slot_count, options in groups:
        if rewrite_subject_scene_mode and name not in _REWRITE_SUBJECT_SCENE_GROUPS:
            continue
        pool = [
            tag
            for tag in options
            if tag != empty_tag
            and tag not in exclude
            and tag not in out_selected[name]
            and tag not in rewrite_group_excludes.get(name, set())
        ]
        if rewrite_subject_scene_mode and not pool and rewrite_group_excludes.get(name):
            pool = [
                tag
                for tag in options
                if tag != empty_tag and tag not in exclude and tag not in out_selected[name]
            ]
        if recent_supplement:
            filtered = [tag for tag in pool if tag not in recent_supplement]
            if filtered:
                pool = filtered
        additions_allowed = _allowed_random_additions_for_group(
            name,
            len(out_selected[name]),
            slot_count,
            intensity,
            theme_pool,
            mode,
        )
        additions = 0
        while len(out_selected[name]) < slot_count and pool and additions < additions_allowed:
            choice = rng.choice(pool)
            pool.remove(choice)
            if choice not in out_selected[name]:
                out_selected[name].append(choice)
                generated.append(choice)
                additions += 1

    return out_selected, uniq(out_custom), uniq(generated)
