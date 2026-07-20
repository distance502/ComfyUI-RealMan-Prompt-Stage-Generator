from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestParameterDocumentation(unittest.TestCase):
    def test_manual_covers_current_defaults_ranges_and_recipes(self) -> None:
        manual = (ROOT / "使用说明书.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for text in (
            "## 16. 参数设置完整手册",
            "`仅Skill / 生成 3 条 / 纯中文 / 标准 / 完整结果",
            "| `生成数量` | `3` | `1-20`",
            "| `核心标签锁定数量` | `10` | `0-500`",
            "| `内置上下文长度` | `8192` | `1024-327680`",
            "| `API超时秒` | `120` | `5-600`",
            "| `最大生成token` | `1800` | `128-8192`",
            "| `温度` | `0.62` | `0-2`",
            "### 16.8 参数联动规则",
            "### 16.9 可直接使用的配置方案",
            "API 密钥、额外认证头或运行缓存",
        ):
            with self.subTest(manual_text=text):
                self.assertIn(text, manual)

        self.assertNotIn("上下文长度是否大于等于 `256`", manual)
        self.assertIn("## 参数快速开始", readme)
        self.assertIn("使用说明书：参数设置完整手册", readme)


if __name__ == "__main__":
    unittest.main()
