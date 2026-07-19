# -*- coding: utf-8 -*-
from __future__ import annotations

import pathlib
import tempfile
import threading
import types
import unittest
import urllib.error
import urllib.request
from unittest import mock

from test_stage_prompt_modules import load_plugin_init_for_integration_test


def build_stub_tag_recommendation(raw_tags, *, max_items=12):
    tags = []
    seen = set()
    for raw_tag in str(raw_tags or "").replace("，", ",").split(","):
        tag = raw_tag.strip()
        key = tag.casefold()
        if not tag or key in seen:
            continue
        seen.add(key)
        tags.append(
            {
                "tag": tag,
                "recommended_group": "画面风格",
                "recommended_section": "在线候选",
                "exists": False,
                "score": 0,
            }
        )
        if len(tags) >= max_items:
            break
    return {"summary": {"total": len(tags)}, "tags": tags}


class TestOnlineSearchInput(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def test_query_is_nfkc_normalized_and_whitespace_is_collapsed(self) -> None:
        query, error = self.module._规范化在线搜索查询("  ｃｉｎｅｍａｔｉｃ   portrait  ")

        self.assertEqual(query, "cinematic portrait")
        self.assertEqual(error, "")

    def test_query_rejects_oversized_text_and_term_lists(self) -> None:
        query, error = self.module._规范化在线搜索查询(
            "x" * (self.module._ONLINE_SEARCH_QUERY_MAX_CHARS + 1)
        )
        self.assertEqual(query, "")
        self.assertIn(str(self.module._ONLINE_SEARCH_QUERY_MAX_CHARS), error)

        query, error = self.module._规范化在线搜索查询(
            " ".join(f"term{index}" for index in range(self.module._ONLINE_SEARCH_QUERY_MAX_TERMS + 1))
        )
        self.assertEqual(query, "")
        self.assertIn(str(self.module._ONLINE_SEARCH_QUERY_MAX_TERMS), error)

    def test_searxng_config_accepts_only_clean_https_base_urls(self) -> None:
        valid = self.module._标准化在线搜索配置(
            {
                "searxng_base_url": "https://search.example.com/private/",
                "searxng_timeout_seconds": 12,
            }
        )
        self.assertEqual(valid["searxng_base_url"], "https://search.example.com/private")
        self.assertEqual(valid["searxng_timeout_seconds"], 12)

        for invalid_url in (
            "http://search.example.com",
            "https://user:secret@search.example.com",
            "https://exa mple.com",
            "https://search.example.com/path;variant",
            "https://search.example.com:0",
            "https://search.example.com/my%20search",
            "https://search.example.com?token=secret",
        ):
            normalized = self.module._标准化在线搜索配置({"searxng_base_url": invalid_url})
            self.assertEqual(normalized["searxng_base_url"], "")

    def test_searxng_url_is_built_from_server_config_not_request_data(self) -> None:
        with mock.patch.object(
            self.module,
            "_SearXNG搜索配置",
            return_value=("https://search.example.com/private", 8),
        ):
            url, host = self.module._构建SearXNG搜索URL("古风 神女", limit=30)

        parsed = self.module.urllib.parse.urlparse(url)
        params = self.module.urllib.parse.parse_qs(parsed.query)
        self.assertEqual(host, "search.example.com")
        self.assertEqual(parsed.path, "/private/search")
        self.assertEqual(params["q"], ["古风 神女"])
        self.assertEqual(params["format"], ["json"])
        self.assertEqual(params["limit"], ["30"])

    def test_public_source_fallback_defaults_on_and_accepts_only_booleans(self) -> None:
        self.assertTrue(self.module._标准化在线搜索配置({})["public_source_fallback_enabled"])
        self.assertFalse(
            self.module._标准化在线搜索配置(
                {"public_source_fallback_enabled": False}
            )["public_source_fallback_enabled"]
        )
        self.assertTrue(
            self.module._标准化在线搜索配置(
                {"public_source_fallback_enabled": "false"}
            )["public_source_fallback_enabled"]
        )


class TestOnlineSearchTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def test_only_fixed_https_sources_are_allowed(self) -> None:
        for url in (
            "https://civitai.com/api/v1/images",
            "https://lexica.art/api/v1/search?q=portrait",
            "https://www.civitai.com/api/v1/images",
        ):
            self.module._校验在线搜索URL(url)

        for url in (
            "http://civitai.com/api/v1/images",
            "https://127.0.0.1/internal",
            "https://example.com/search",
        ):
            with self.assertRaisesRegex(ValueError, "未授权来源"):
                self.module._校验在线搜索URL(url)

        with self.assertRaisesRegex(ValueError, "未授权来源"):
            self.module._校验在线搜索URL("https://search.example.com/search?q=portrait")
        self.module._校验在线搜索URL(
            "https://search.example.com/search?q=portrait",
            allowed_hosts={"search.example.com"},
        )

    def test_redirects_must_remain_on_the_same_allowed_host(self) -> None:
        handler = self.module._在线搜索重定向处理器()
        request = urllib.request.Request("https://lexica.art/api/v1/search?q=portrait")

        redirected = handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://lexica.art/api/v1/search?q=cinematic",
        )
        self.assertEqual(self.module._在线搜索URL主机(redirected.full_url), "lexica.art")

        with self.assertRaisesRegex(urllib.error.HTTPError, "跨站重定向"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://civitai.com/api/v1/images",
            )

        with self.assertRaisesRegex(urllib.error.HTTPError, "跨站重定向"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://lexica.art:8443/api/v1/search?q=portrait",
            )

        with self.assertRaisesRegex(ValueError, "未授权来源"):
            handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://localhost/internal",
            )

    def test_portable_python_prefers_an_existing_ca_bundle(self) -> None:
        sentinel = object()
        with tempfile.TemporaryDirectory() as temp_dir:
            ca_path = pathlib.Path(temp_dir) / "cacert.pem"
            ca_path.write_text("test-ca", encoding="utf-8")
            with (
                mock.patch.dict(
                    self.module.os.environ,
                    {"SSL_CERT_FILE": str(ca_path), "REQUESTS_CA_BUNDLE": ""},
                    clear=False,
                ),
                mock.patch.object(
                    self.module.ssl,
                    "create_default_context",
                    return_value=sentinel,
                ) as create_context,
            ):
                context = self.module._创建在线SSL上下文()

        self.assertIs(context, sentinel)
        create_context.assert_called_once_with(cafile=str(ca_path))

    def test_open_request_validates_source_and_preserves_timeout(self) -> None:
        captured = {}

        class Opener:
            def open(_self, request, timeout):
                captured["url"] = request.full_url
                captured["timeout"] = timeout
                return "response"

        with mock.patch.object(self.module, "_构建在线搜索打开器", return_value=Opener()):
            response = self.module._打开在线搜索请求(
                urllib.request.Request("https://civitai.com/api/v1/images"),
                timeout=3.5,
            )

        self.assertEqual(response, "response")
        self.assertEqual(captured, {"url": "https://civitai.com/api/v1/images", "timeout": 3.5})

    def test_json_request_shares_one_timeout_budget_between_connect_and_read(self) -> None:
        class Headers(dict):
            def get_content_charset(self):
                return "utf-8"

        class Response:
            headers = Headers()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        with (
            mock.patch.object(self.module, "_打开在线搜索请求", return_value=Response()),
            mock.patch.object(self.module.time, "monotonic", side_effect=[10.0, 12.0]),
            mock.patch.object(self.module, "_读取受限在线响应", return_value=b"{}") as read_response,
        ):
            data = self.module._在线JSON请求(
                "https://civitai.com/api/v1/images",
                timeout=3.0,
            )

        self.assertEqual(data, {})
        self.assertEqual(read_response.call_args.kwargs["timeout"], 1.0)


class TestOnlineSearchRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def _register_search_handler(self):
        handlers = {}

        class Routes:
            def get(self, path):
                return lambda handler: handlers.setdefault(("GET", path), handler)

            def post(self, path):
                return lambda handler: handlers.setdefault(("POST", path), handler)

        prompt_server = types.SimpleNamespace(routes=Routes())
        self.module._get_prompt_server_class = lambda: types.SimpleNamespace(instance=prompt_server)
        self.assertTrue(self.module._register_tag_routes())
        return handlers[("POST", "/qwen_te/tag_library/online_search")]

    def setUp(self) -> None:
        self.module._清空在线搜索样本缓存()

    def test_route_rejects_oversized_query_before_starting_network_work(self) -> None:
        module = self.module

        class Request:
            async def json(self):
                return {
                    "query": "x" * (module._ONLINE_SEARCH_QUERY_MAX_CHARS + 1),
                    "limit": 24,
                }

        handler = self._register_search_handler()

        with mock.patch.object(
            self.module,
            "_联网抓取提示词样本",
            side_effect=AssertionError("network search must not start"),
        ):
            response = self.module.asyncio.run(handler(Request()))

        self.assertEqual(response.status, 400)
        self.assertIn(str(self.module._ONLINE_SEARCH_QUERY_MAX_CHARS), response.text)

    def test_route_marks_local_tags_when_online_samples_cannot_produce_tags(self) -> None:
        class Request:
            async def json(self):
                return {"query": "cinematic portrait", "limit": 12}

        handler = self._register_search_handler()
        local_items = [
            {
                "tag": "电影人像",
                "count": 2,
                "confidence": 0.8,
                "group": "风格",
                "section": "电影",
                "exists": True,
                "source": "local_fallback",
            }
        ]
        with (
            mock.patch.object(
                self.module,
                "_联网抓取提示词样本",
                return_value=(["cinematic portrait result"], "searxng", ""),
            ),
            mock.patch.object(self.module, "_从在线提示词提取标签", return_value=([], [])),
            mock.patch.object(self.module, "_本地回退联想标签", return_value=["电影人像"]),
            mock.patch.object(self.module, "_构建本地回退标签条目", return_value=local_items),
        ):
            response = self.module.asyncio.run(handler(Request()))

        payload = self.module.json.loads(response.text)
        self.assertEqual(response.status, 200)
        self.assertEqual(payload["source"], "searxng+local_fallback")
        self.assertEqual(payload["tags"], ["电影人像"])
        self.assertTrue(payload["prompt_items"])
        self.assertEqual(payload["prompts"], [item["prompt"] for item in payload["prompt_items"]])
        self.assertEqual(payload["count"], len(payload["prompt_items"]))
        self.assertEqual(payload["tag_count"], 1)

    def test_repeated_route_query_reuses_raw_samples_but_rebuilds_tag_items(self) -> None:
        class Request:
            async def json(self):
                return {"query": "cache portrait", "limit": 12}

        handler = self._register_search_handler()
        network_calls = 0
        extraction_calls = 0

        def fetch_samples(_query, *, limit):
            nonlocal network_calls
            del limit
            network_calls += 1
            return ["cache portrait, dramatic lighting"], "searxng", ""

        def extract_tags(_samples, *, query, limit):
            nonlocal extraction_calls
            del query, limit
            extraction_calls += 1
            return (
                [
                    {
                        "tag": "cache portrait",
                        "count": extraction_calls,
                        "confidence": 0.8,
                        "group": "风格",
                        "section": "缓存",
                        "exists": extraction_calls > 1,
                        "source": "online_extracted",
                    }
                ],
                ["cache portrait, dramatic lighting"],
            )

        with (
            mock.patch.object(self.module, "_联网抓取提示词样本", side_effect=fetch_samples),
            mock.patch.object(self.module, "_从在线提示词提取标签", side_effect=extract_tags),
        ):
            first = self.module.asyncio.run(handler(Request()))
            second = self.module.asyncio.run(handler(Request()))

        first_payload = self.module.json.loads(first.text)
        second_payload = self.module.json.loads(second.text)
        self.assertEqual(network_calls, 1)
        self.assertEqual(extraction_calls, 2)
        self.assertFalse(first_payload["cached"])
        self.assertTrue(second_payload["cached"])
        self.assertFalse(first_payload["tag_items"][0]["exists"])
        self.assertTrue(second_payload["tag_items"][0]["exists"])
        self.assertEqual(first_payload["prompts"], ["cache portrait, dramatic lighting"])
        self.assertEqual(second_payload["prompt_items"][0]["prompt"], "cache portrait, dramatic lighting")

    def test_concurrent_identical_queries_share_one_network_worker(self) -> None:
        class Request:
            async def json(self):
                return {"query": "singleflight portrait", "limit": 12}

        handler = self._register_search_handler()
        started = threading.Event()
        release = threading.Event()
        network_calls = 0

        def fetch_samples(_query, *, limit):
            nonlocal network_calls
            del limit
            network_calls += 1
            started.set()
            self.assertTrue(release.wait(timeout=5.0))
            return ["singleflight portrait, film grain"], "searxng", ""

        async def run_pair():
            first = self.module.asyncio.create_task(handler(Request()))
            while not started.is_set():
                await self.module.asyncio.sleep(0.01)
            second = self.module.asyncio.create_task(handler(Request()))
            await self.module.asyncio.sleep(0.05)
            release.set()
            return await self.module.asyncio.gather(first, second)

        tag_items = [
            {
                "tag": "singleflight portrait",
                "count": 2,
                "confidence": 0.8,
                "group": "风格",
                "section": "缓存",
                "exists": False,
                "source": "online_extracted",
            }
        ]
        with (
            mock.patch.object(self.module, "_联网抓取提示词样本", side_effect=fetch_samples),
            mock.patch.object(
                self.module,
                "_从在线提示词提取标签",
                return_value=(tag_items, ["singleflight portrait, film grain"]),
            ),
        ):
            responses = self.module.asyncio.run(run_pair())

        payloads = [self.module.json.loads(response.text) for response in responses]
        self.assertEqual(network_calls, 1)
        self.assertEqual(sorted(bool(payload["cached"]) for payload in payloads), [False, True])

    def test_extraction_failures_are_redacted_and_keep_provider_attribution(self) -> None:
        class Request:
            async def json(self):
                return {"query": "redacted portrait", "limit": 12}

        handler = self._register_search_handler()
        local_items = [
            {
                "tag": "电影人像",
                "count": 1,
                "confidence": 0.7,
                "group": "风格",
                "section": "电影",
                "exists": False,
                "source": "local_fallback",
            }
        ]
        with (
            mock.patch.object(
                self.module,
                "_联网抓取提示词样本",
                return_value=(["redacted portrait sample"], "searxng", ""),
            ),
            mock.patch.object(
                self.module,
                "_从在线提示词提取标签",
                side_effect=RuntimeError("token=secret private-path"),
            ),
            mock.patch.object(self.module.logging, "exception"),
            mock.patch.object(self.module, "_本地回退联想标签", return_value=["电影人像"]),
            mock.patch.object(self.module, "_构建本地回退标签条目", return_value=local_items),
        ):
            response = self.module.asyncio.run(handler(Request()))

        payload = self.module.json.loads(response.text)
        self.assertEqual(payload["source"], "searxng+local_fallback")
        self.assertEqual(payload["warning"], "extract:failed")
        self.assertNotIn("secret", response.text)
        self.assertNotIn("private-path", response.text)


class TestOnlineSearchQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def _extract(self, samples, *, query, limit=12):
        with mock.patch.object(
            self.module,
            "推荐自定义标签归类",
            side_effect=build_stub_tag_recommendation,
        ):
            return self.module._从在线提示词提取标签(samples, query=query, limit=limit)

    def test_common_english_phrases_are_not_treated_as_model_codes(self) -> None:
        phrases = {
            "cinematic portrait",
            "dramatic lighting",
            "film grain",
            "volumetric lighting",
        }
        for phrase in phrases:
            self.assertFalse(self.module._是在线模型噪声(phrase), phrase)
        for model_code in ("85mm", "abc123", "sdxl10"):
            self.assertTrue(self.module._是在线模型噪声(model_code), model_code)

        tag_items, _cleaned = self._extract(
            ["cinematic portrait, dramatic lighting, film grain, volumetric lighting"],
            query="cinematic portrait",
        )
        extracted = {str(item["tag"]).casefold() for item in tag_items}
        self.assertTrue(phrases.issubset(extracted))

    def test_ascii_query_terms_require_word_boundaries(self) -> None:
        false_pairs = (
            ("male portrait", "female portrait studio"),
            ("cat portrait", "vacation portrait photo"),
            ("red dress", "rendered dress in blue"),
            ("oil painting", "spoiler digital painting"),
        )
        for query, sample in false_pairs:
            self.assertFalse(self.module._在线样本可接受(query, sample), (query, sample))

        true_pairs = (
            ("male portrait", "male portrait studio"),
            ("cat portrait", "cat portrait photo"),
            ("red dress", "red dress fabric"),
            ("oil painting", "oil painting on canvas"),
        )
        for query, sample in true_pairs:
            self.assertTrue(self.module._在线样本可接受(query, sample), (query, sample))

    def test_samples_and_tags_are_canonically_deduplicated(self) -> None:
        samples = []
        for sample in (
            "Cinematic portrait, Photorealistic",
            " cinematic   portrait ,  photorealistic ",
            "Ｃｉｎｅｍａｔｉｃ portrait，PHOTOREALISTIC",
        ):
            self.module._收集在线样本(samples, sample, limit=12)
        self.assertEqual(len(samples), 1)

        tag_items, cleaned = self._extract(
            [
                "Photorealistic, 第一场景",
                " photorealistic , 第一场景 ",
            ],
            query="portrait",
        )
        matches = [item for item in tag_items if str(item["tag"]).casefold() == "photorealistic"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["count"], 1)
        self.assertEqual(len(cleaned), 1)

    def test_candidates_are_split_cleanly_and_count_once_per_sample(self) -> None:
        tag_items, _cleaned = self._extract(
            ["photorealistic, chromatic aberration"],
            query="portrait",
        )
        by_tag = {str(item["tag"]).casefold(): item for item in tag_items}
        self.assertEqual(by_tag["photorealistic"]["count"], 1)
        self.assertEqual(by_tag["chromatic aberration"]["count"], 1)
        self.assertFalse(
            any(any(separator in str(item["tag"]) for separator in (",", "，", ";", "；", "|", "\n")) for item in tag_items)
        )

    def test_filtering_happens_before_limit_is_applied(self) -> None:
        tag_items, _cleaned = self._extract(
            [
                "甲乙 丙丁 戊己",
                "丙丁 甲乙 戊己",
                "高动态范围电影级真实质感",
                "精细自然皮肤纹理表现",
                "柔和自然环境光照层次",
            ],
            query="甲乙",
            limit=6,
        )
        tags = {str(item["tag"]) for item in tag_items}
        self.assertEqual(len(tag_items), 6)
        self.assertTrue(
            {
                "高动态范围电影级真实质感",
                "精细自然皮肤纹理表现",
                "柔和自然环境光照层次",
            }.issubset(tags)
        )
        self.assertFalse(any(len(tag.split()) >= 3 for tag in tags))

    def test_new_candidate_needs_multiple_independent_samples_for_high_confidence(self) -> None:
        single_items, _cleaned = self._extract(
            ["Photorealistic, 第一场景"],
            query="portrait",
        )
        single = next(item for item in single_items if str(item["tag"]).casefold() == "photorealistic")
        self.assertLess(single["confidence"], 0.72)

        repeated_items, _cleaned = self._extract(
            ["Photorealistic, 第一场景", "photorealistic, 第二场景"],
            query="portrait",
        )
        repeated = next(item for item in repeated_items if str(item["tag"]).casefold() == "photorealistic")
        self.assertEqual(repeated["count"], 2)
        self.assertGreaterEqual(repeated["confidence"], 0.72)


class TestOnlineSearchSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def test_source_label_only_includes_providers_that_contributed_samples(self) -> None:
        civitai_payload = {
            "items": [
                {
                    "meta": {
                        "prompt": "cinematic portrait, adult woman, dramatic lighting, detailed face"
                    }
                }
            ]
        }

        def json_request(url, *, timeout):
            del timeout
            if "civitai.com" in url:
                return civitai_payload
            return {"images": []}

        with (
            mock.patch.object(self.module, "_SearXNG搜索配置", return_value=("", 8)),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
            mock.patch.object(self.module, "_在线搜索剩余超时", return_value=1.0),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=6,
            )

        self.assertEqual(len(samples), 1)
        self.assertEqual(source, "civitai")
        self.assertEqual(warning, "")

    def test_empty_civitai_does_not_claim_searxng_samples(self) -> None:
        searxng_payload = {
            "results": [
                {
                    "title": "Cinematic portrait prompt",
                    "content": "cinematic portrait, soft rim lighting",
                }
            ]
        }

        def json_request(url, *, timeout, allowed_hosts=None):
            del timeout, allowed_hosts
            if "search.example.com" in url:
                return searxng_payload
            if "civitai.com" in url:
                return {"items": []}
            return {"images": []}

        with (
            mock.patch.object(
                self.module,
                "_SearXNG搜索配置",
                return_value=("https://search.example.com", 7),
            ),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
            mock.patch.object(self.module, "_在线搜索剩余超时", return_value=7.0),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=6,
            )

        self.assertEqual(len(samples), 1)
        self.assertEqual(source, "searxng")
        self.assertEqual(warning, "")

    def test_searxng_parser_uses_title_and_content_but_not_result_urls(self) -> None:
        payload = {
            "results": [
                {
                    "title": "<b>Cinematic portrait</b> prompt",
                    "content": "cinematic portrait, soft rim lighting, 85mm lens",
                    "url": "https://untrusted.example/private-token",
                },
                {
                    "title": "Unrelated result",
                    "content": "weather forecast and sports scores",
                    "url": "https://untrusted.example/ignored",
                },
            ]
        }

        samples = self.module._解析SearXNG提示词样本(
            payload,
            query="cinematic portrait",
            limit=6,
        )

        self.assertEqual(len(samples), 1)
        self.assertIn("Cinematic portrait", samples[0])
        self.assertNotIn("private-token", samples[0])

    def test_configured_searxng_is_used_before_opportunistic_sources(self) -> None:
        payload = {
            "results": [
                {
                    "title": f"Cinematic portrait prompt {index}",
                    "content": f"cinematic portrait, rim lighting, portrait detail {index}",
                }
                for index in range(12)
            ]
        }
        captured = {}

        def json_request(url, *, timeout, allowed_hosts=None):
            captured["url"] = url
            captured["timeout"] = timeout
            captured["allowed_hosts"] = set(allowed_hosts or set())
            return payload

        with (
            mock.patch.object(
                self.module,
                "_SearXNG搜索配置",
                return_value=("https://search.example.com", 7),
            ),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
            mock.patch.object(self.module, "_在线搜索剩余超时", return_value=7.0),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=6,
            )

        self.assertEqual(len(samples), 12)
        self.assertEqual(source, "searxng")
        self.assertEqual(warning, "")
        self.assertEqual(captured["allowed_hosts"], {"search.example.com"})
        self.assertIn("format=json", captured["url"])

    def test_any_searxng_match_stops_before_public_sources(self) -> None:
        calls = []

        def json_request(url, *, timeout, allowed_hosts=None):
            del timeout, allowed_hosts
            calls.append(url)
            if "search.example.com" not in url:
                raise AssertionError("public source must not run after a SearXNG match")
            return {
                "results": [
                    {
                        "title": "Cinematic portrait",
                        "content": "cinematic portrait, dramatic lighting",
                    }
                ]
            }

        with (
            mock.patch.object(
                self.module,
                "_SearXNG搜索配置",
                return_value=("https://search.example.com", 7),
            ),
            mock.patch.object(self.module, "_公开来源回退已启用", return_value=True),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=30,
            )

        self.assertEqual(len(calls), 1)
        self.assertTrue(samples)
        self.assertEqual(source, "searxng")
        self.assertEqual(warning, "")

    def test_public_fallback_can_be_disabled(self) -> None:
        with (
            mock.patch.object(self.module, "_SearXNG搜索配置", return_value=("", 8)),
            mock.patch.object(self.module, "_公开来源回退已启用", return_value=False),
            mock.patch.object(
                self.module,
                "_在线JSON请求",
                side_effect=AssertionError("public sources must stay disabled"),
            ),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=12,
            )

        self.assertEqual(samples, [])
        self.assertEqual(source, "none")
        self.assertEqual(warning, "policy:public_sources_disabled")

    def test_provider_schema_errors_are_reported_without_response_details(self) -> None:
        def json_request(url, *, timeout, allowed_hosts=None):
            del timeout, allowed_hosts
            if "civitai.com" in url:
                return {"error": "token=secret"}
            return {}

        with (
            mock.patch.object(self.module, "_SearXNG搜索配置", return_value=("", 8)),
            mock.patch.object(self.module, "_公开来源回退已启用", return_value=True),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
            mock.patch.object(self.module, "_在线搜索剩余超时", return_value=1.0),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=6,
            )

        self.assertEqual(samples, [])
        self.assertEqual(source, "none")
        self.assertEqual(warning, "civitai:provider_error,lexica:invalid_schema")
        self.assertNotIn("secret", warning)

    def test_provider_diagnostics_expose_only_source_and_error_code(self) -> None:
        def json_request(url, *, timeout, allowed_hosts=None):
            del timeout, allowed_hosts
            if "search.example.com" in url:
                raise urllib.error.HTTPError(
                    "https://search.example.com/search?token=secret",
                    401,
                    "private response body",
                    {},
                    None,
                )
            if "civitai.com" in url:
                return {"items": []}
            return {"images": []}

        with (
            mock.patch.object(
                self.module,
                "_SearXNG搜索配置",
                return_value=("https://search.example.com", 7),
            ),
            mock.patch.object(self.module, "_在线JSON请求", side_effect=json_request),
            mock.patch.object(self.module, "_在线搜索剩余超时", return_value=7.0),
        ):
            samples, source, warning = self.module._联网抓取提示词样本(
                "cinematic portrait",
                limit=6,
            )

        self.assertEqual(samples, [])
        self.assertEqual(source, "none")
        self.assertEqual(warning, "searxng:http_401")
        self.assertNotIn("secret", warning)
        self.assertNotIn("private", warning)

    def test_online_samples_enforce_per_item_and_total_character_budgets(self) -> None:
        samples = []
        oversized = "cinematic portrait," * self.module._ONLINE_SAMPLE_MAX_CHARS
        for index in range(64):
            self.module._收集在线样本(samples, f"{index},{oversized}", limit=60)

        self.assertTrue(samples)
        self.assertLessEqual(max(map(len, samples)), self.module._ONLINE_SAMPLE_MAX_CHARS)
        self.assertLessEqual(sum(map(len, samples)), self.module._ONLINE_SAMPLES_TOTAL_MAX_CHARS)

        tag_items, cleaned = self.module._从在线提示词提取标签(
            samples + [oversized],
            query="cinematic portrait",
            limit=12,
        )
        self.assertIsInstance(tag_items, list)
        self.assertLessEqual(sum(map(len, cleaned)), self.module._ONLINE_SAMPLES_TOTAL_MAX_CHARS)

    def test_total_timeout_helper_rejects_expired_deadlines(self) -> None:
        with mock.patch.object(self.module.time, "monotonic", return_value=20.0):
            self.assertEqual(self.module._在线搜索剩余超时(25.0, 3.0), 3.0)
            with self.assertRaisesRegex(TimeoutError, "总时限"):
                self.module._在线搜索剩余超时(19.0, 3.0)


class TestOnlineSearchCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_plugin_init_for_integration_test()

    def setUp(self) -> None:
        self.module._清空在线搜索样本缓存()

    def test_cache_is_defensive_ttl_bound_and_config_scoped(self) -> None:
        key = ("portrait", 12, "https://search.example.com", 8, False)
        self.module._写入在线搜索样本缓存(
            key,
            ["cinematic portrait"],
            "searxng",
            "",
            now=10.0,
        )
        cached = self.module._读取在线搜索样本缓存(key, now=11.0)
        self.assertIsNotNone(cached)
        cached[0].append("mutated")
        self.assertEqual(
            self.module._读取在线搜索样本缓存(key, now=12.0)[0],
            ["cinematic portrait"],
        )
        self.assertIsNone(
            self.module._读取在线搜索样本缓存(
                ("portrait", 12, "https://search.example.com", 8, True),
                now=12.0,
            )
        )
        self.assertIsNone(self.module._读取在线搜索样本缓存(key, now=191.0))

        for index in range(self.module._ONLINE_SEARCH_CACHE_MAX_ENTRIES + 5):
            next_key = (f"query-{index}", 12, "", 8, True)
            self.module._写入在线搜索样本缓存(
                next_key,
                [f"sample-{index}"],
                "civitai",
                "",
                now=200.0 + index,
            )
        self.assertLessEqual(
            len(self.module._在线搜索样本缓存),
            self.module._ONLINE_SEARCH_CACHE_MAX_ENTRIES,
        )


if __name__ == "__main__":
    unittest.main()
