# -*- coding: utf-8 -*-
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载测试模块：{filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


embed = load_module("embed_into_comfyui.py", "realman_embed_packaging_test")
dependency_probe = load_module("dependency_probe.py", "realman_dependency_probe_packaging_test")
dependency_installer = load_module("install_dependencies.py", "realman_dependency_installer_packaging_test")


def make_comfy_root(base: Path) -> Path:
    comfy_root = base / "Comfy UI 中文"
    (comfy_root / "custom_nodes").mkdir(parents=True)
    (comfy_root / "folder_paths.py").write_text("# test comfy root\n", encoding="utf-8")
    return comfy_root


def make_plugin(path: Path, *, marker: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "__init__.py").write_text(f"PLUGIN_MARKER = {marker!r}\n", encoding="utf-8")
    (path / "regular.txt").write_text(marker, encoding="utf-8")
    return path


def run_embed(source: Path, comfy_root: Path) -> tuple[int, str]:
    output = io.StringIO()
    with (
        mock.patch.object(embed, "NODE_DIR", source),
        mock.patch.object(sys, "argv", ["embed_into_comfyui.py", str(comfy_root)]),
        contextlib.redirect_stdout(output),
    ):
        result = embed.main()
    return result, output.getvalue()


class TestEmbeddedInstaller(unittest.TestCase):
    def test_update_preserves_existing_target_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            comfy_root = make_comfy_root(base)
            source = make_plugin(base / "分享 包", marker="source")
            target = make_plugin(
                comfy_root / "custom_nodes" / embed.TARGET_DIR_NAME,
                marker="target-old",
            )
            (source / "prompt_tag_library_custom.json").write_text("source-custom", encoding="utf-8")
            (source / "online_search_config.json").write_text("source-config", encoding="utf-8")
            (target / "prompt_tag_library_custom.json").write_text("target-custom", encoding="utf-8")
            (target / "online_search_config.json").write_text("target-config", encoding="utf-8")

            result, _output = run_embed(source, comfy_root)

            self.assertEqual(result, 0)
            self.assertEqual((target / "prompt_tag_library_custom.json").read_text(encoding="utf-8"), "target-custom")
            self.assertEqual((target / "online_search_config.json").read_text(encoding="utf-8"), "target-config")
            self.assertEqual((target / "regular.txt").read_text(encoding="utf-8"), "source")

    def test_legacy_user_files_migrate_and_collision_safe_backup_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            comfy_root = make_comfy_root(base)
            custom_nodes = comfy_root / "custom_nodes"
            source = make_plugin(base / "share", marker="source")
            legacy = make_plugin(custom_nodes / embed.LEGACY_DIR_NAMES[0], marker="legacy")
            (source / "prompt_tag_library_custom.json").write_text("source-custom", encoding="utf-8")
            (source / "online_search_config.json").write_text("source-config", encoding="utf-8")
            (legacy / "prompt_tag_library_custom.json").write_text("legacy-custom", encoding="utf-8")
            (legacy / "online_search_config.json").write_text("legacy-config", encoding="utf-8")
            occupied_backup = custom_nodes / f"{legacy.name}.backup.disabled"
            occupied_backup.mkdir()
            (occupied_backup / "marker.txt").write_text("keep", encoding="utf-8")

            result, _output = run_embed(source, comfy_root)

            target = custom_nodes / embed.TARGET_DIR_NAME
            self.assertEqual(result, 0)
            self.assertEqual((target / "prompt_tag_library_custom.json").read_text(encoding="utf-8"), "legacy-custom")
            self.assertEqual((target / "online_search_config.json").read_text(encoding="utf-8"), "legacy-config")
            self.assertFalse(legacy.exists())
            backups = sorted(custom_nodes.glob(f"{legacy.name}.backup*.disabled"))
            self.assertEqual(len(backups), 2)
            migrated_backup = next(path for path in backups if path != occupied_backup)
            self.assertTrue(migrated_backup.name.endswith(".disabled"))
            self.assertEqual((migrated_backup / "regular.txt").read_text(encoding="utf-8"), "legacy")
            self.assertEqual((occupied_backup / "marker.txt").read_text(encoding="utf-8"), "keep")

    def test_already_installed_target_still_migrates_and_disables_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            comfy_root = make_comfy_root(base)
            custom_nodes = comfy_root / "custom_nodes"
            target = make_plugin(custom_nodes / embed.TARGET_DIR_NAME, marker="installed")
            legacy = make_plugin(custom_nodes / embed.LEGACY_DIR_NAMES[0], marker="legacy")
            (target / "prompt_tag_library_custom.json").write_text("target-custom", encoding="utf-8")
            (legacy / "prompt_tag_library_custom.json").write_text("legacy-custom", encoding="utf-8")
            (legacy / "online_search_config.json").write_text("legacy-config", encoding="utf-8")

            result, output = run_embed(target, comfy_root)

            self.assertEqual(result, 0)
            self.assertIn("无需复制代码文件", output)
            self.assertEqual((target / "prompt_tag_library_custom.json").read_text(encoding="utf-8"), "target-custom")
            self.assertEqual((target / "online_search_config.json").read_text(encoding="utf-8"), "legacy-config")
            self.assertFalse(legacy.exists())
            backups = list(custom_nodes.glob(f"{legacy.name}.backup*.disabled"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(backups[0].name.endswith(".disabled"))

    def test_legacy_disable_failure_is_reported_as_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            comfy_root = make_comfy_root(base)
            source = make_plugin(base / "share", marker="source")
            legacy = make_plugin(
                comfy_root / "custom_nodes" / embed.LEGACY_DIR_NAMES[0],
                marker="legacy",
            )

            with mock.patch.object(embed, "disable_legacy_directory", side_effect=PermissionError("locked")):
                result, output = run_embed(source, comfy_root)

            self.assertEqual(result, 1)
            self.assertIn("安装或旧目录迁移失败", output)
            self.assertTrue(legacy.exists())


class TestDependencyProbe(unittest.TestCase):
    def test_probe_plugin_entry_restores_preexisting_alias_modules(self) -> None:
        alias = "qwen_te_dependency_probe_pkg"
        old_package = types.ModuleType(alias)
        old_child = types.ModuleType(f"{alias}.child")
        previous = {
            key: value
            for key, value in sys.modules.items()
            if key == alias or key.startswith(f"{alias}.")
        }
        for key in list(previous):
            sys.modules.pop(key, None)
        sys.modules[alias] = old_package
        sys.modules[f"{alias}.child"] = old_child
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                plugin_dir = Path(temp_dir)
                (plugin_dir / "__init__.py").write_text(
                    "import sys\n"
                    "if 'qwen_te_dependency_probe_pkg.child' in sys.modules:\n"
                    "    raise RuntimeError('preexisting alias child leaked into probe')\n"
                    "NODE_CLASS_MAPPINGS = {'QwenTE_StagePromptGenerator': object}\n",
                    encoding="utf-8",
                )
                with mock.patch.object(dependency_probe, "NODE_DIR", plugin_dir):
                    ok, _detail = dependency_probe.probe_plugin_entry()

            self.assertTrue(ok)
            self.assertIs(sys.modules.get(alias), old_package)
            self.assertIs(sys.modules.get(f"{alias}.child"), old_child)
        finally:
            for key in [key for key in list(sys.modules) if key == alias or key.startswith(f"{alias}.")]:
                sys.modules.pop(key, None)
            sys.modules.update(previous)

    def test_explicit_invalid_root_does_not_fall_back_to_another_comfy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            invalid_root = base / "not-comfy"
            invalid_root.mkdir()
            other_root = make_comfy_root(base / "other")
            output = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["dependency_probe.py", str(invalid_root)]),
                mock.patch.object(sys, "path", list(sys.path)),
                mock.patch.object(dependency_probe, "find_comfy_root_from_module_path", return_value=other_root),
                mock.patch.object(dependency_probe, "check_files") as check_files,
                contextlib.redirect_stdout(output),
            ):
                result = dependency_probe.main()

            self.assertEqual(result, 1)
            self.assertIn("不会回退", output.getvalue())
            check_files.assert_not_called()


class TestDependencyInstaller(unittest.TestCase):
    def test_invalid_root_exits_before_any_pip_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_root = Path(temp_dir) / "not-comfy"
            invalid_root.mkdir()
            with (
                mock.patch.object(sys, "argv", ["install_dependencies.py", str(invalid_root)]),
                mock.patch.object(dependency_installer, "run_command") as run_command,
                mock.patch.object(dependency_installer, "run_probe") as run_probe,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = dependency_installer.main()

            self.assertEqual(result, 1)
            run_command.assert_not_called()
            run_probe.assert_not_called()

    def test_required_upgrade_failure_forces_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            comfy_root = make_comfy_root(Path(temp_dir))
            commands = [("升级 pip", ["python", "-m", "pip"], True)]
            with (
                mock.patch.object(sys, "argv", ["install_dependencies.py", str(comfy_root), "--upgrade-pip"]),
                mock.patch.object(dependency_installer, "build_install_commands", return_value=commands),
                mock.patch.object(dependency_installer, "run_command", return_value=False),
                mock.patch.object(dependency_installer, "run_probe", return_value=0),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = dependency_installer.main()

            self.assertEqual(result, 1)

    def test_optional_install_failure_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            comfy_root = make_comfy_root(Path(temp_dir))
            commands = [("质检依赖", ["python", "-m", "pip"], False)]
            with (
                mock.patch.object(sys, "argv", ["install_dependencies.py", str(comfy_root)]),
                mock.patch.object(dependency_installer, "build_install_commands", return_value=commands),
                mock.patch.object(dependency_installer, "run_command", return_value=False),
                mock.patch.object(dependency_installer, "run_probe", return_value=0),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result = dependency_installer.main()

            self.assertEqual(result, 1)

    def test_install_batch_has_no_machine_specific_default_and_balances_pushd(self) -> None:
        source = (ROOT / "内嵌安装到ComfyUI.bat").read_text(encoding="utf-8")
        self.assertNotIn("DEFAULT_COMFY_ROOT", source)
        self.assertNotIn(r"F:\ComfyUI_portable_TE v251130\ComfyUI", source)
        self.assertIn(r'call :TryComfyRoot "%NODE_DIR%\..\.."', source)
        self.assertIn(r'pushd "%COMFY_ROOT%"', source)
        self.assertIn("popd", source)


if __name__ == "__main__":
    unittest.main()
