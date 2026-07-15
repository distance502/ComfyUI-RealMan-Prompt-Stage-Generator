# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "prompt_config_audit_online_search_test",
        ROOT / "prompt_config_audit.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("prompt_config_audit.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestOnlineSearchConfigAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_audit_module()

    def audit(self, payload):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = pathlib.Path(temp_dir)
            (root / "online_search_config.json").write_text(
                json.dumps(payload, ensure_ascii=False),
                encoding="utf-8",
            )
            with mock.patch.object(self.module, "ROOT", root):
                return self.module._审核在线搜索配置()

    def base_payload(self):
        return {
            "fallback_generic_downweight_tags": ["cinematic"],
            "long_query_term_threshold": 16,
            "generic_penalty_score": 6,
            "searxng_base_url": "https://search.example.com/private",
            "searxng_timeout_seconds": 8,
        }

    def test_legacy_config_without_public_fallback_key_remains_valid(self) -> None:
        self.assertEqual(self.audit(self.base_payload()), {})

    def test_public_fallback_must_be_boolean(self) -> None:
        payload = self.base_payload()
        payload["public_source_fallback_enabled"] = "false"

        issues = self.audit(payload)

        self.assertIn("public_source_fallback_enabled", issues)

    def test_searxng_url_and_timeout_constraints_match_runtime_contract(self) -> None:
        for invalid_url in (
            "http://search.example.com",
            "https://user:secret@search.example.com",
            "https://search.example.com:0",
            "https://search.example.com/private%20path",
            "https://search.example.com?token=secret",
        ):
            payload = self.base_payload()
            payload["searxng_base_url"] = invalid_url
            self.assertIn("searxng_base_url", self.audit(payload), invalid_url)

        payload = self.base_payload()
        payload["searxng_timeout_seconds"] = 2
        self.assertIn("searxng_timeout_seconds", self.audit(payload))


if __name__ == "__main__":
    unittest.main()
