# -*- coding: utf-8 -*-
"""Workspace catalog helpers for NSFW stage prompt presets."""

from __future__ import annotations

import importlib.util
import pathlib
from typing import Any

try:
    from .nsfw_presets import (
        NSFW_NEGATIVE_PRESETS,
        NSFW_QUALITY_TAGS,
        NSFW_WORKSPACE_OPTIONS,
        NSFW_WORKSPACE_PRESETS,
        build_nsfw_workspace_defaults,
    )
except ImportError:  # pragma: no cover - direct file loading in focused tests
    _MODULE_PATH = pathlib.Path(__file__).with_name("nsfw_presets.py")
    _SPEC = importlib.util.spec_from_file_location("stage_prompt_nsfw_presets_runtime", _MODULE_PATH)
    if _SPEC is None or _SPEC.loader is None:
        raise
    _MODULE = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(_MODULE)
    NSFW_NEGATIVE_PRESETS = _MODULE.NSFW_NEGATIVE_PRESETS
    NSFW_QUALITY_TAGS = _MODULE.NSFW_QUALITY_TAGS
    NSFW_WORKSPACE_OPTIONS = _MODULE.NSFW_WORKSPACE_OPTIONS
    NSFW_WORKSPACE_PRESETS = _MODULE.NSFW_WORKSPACE_PRESETS
    build_nsfw_workspace_defaults = _MODULE.build_nsfw_workspace_defaults


def build_nsfw_workspace_catalog() -> dict[str, Any]:
    """Return the catalog payload consumed by the NSFW workspace UI."""

    return {
        "defaults": build_nsfw_workspace_defaults(),
        "negative_presets": dict(NSFW_NEGATIVE_PRESETS),
        "options": {key: list(values) for key, values in NSFW_WORKSPACE_OPTIONS.items()},
        "presets": {key: dict(value) for key, value in NSFW_WORKSPACE_PRESETS.items()},
        "quality_tags": {key: list(values) for key, values in NSFW_QUALITY_TAGS.items()},
    }
