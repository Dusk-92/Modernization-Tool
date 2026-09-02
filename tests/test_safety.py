import json
import os
import struct
import tempfile
import unittest
from unittest import mock

import remote_packages
import setup_tool
import setup_tool_dynamic
from setup_tool import WowSetupTool


class FakeVar:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class DllsTxtTests(unittest.TestCase):
    def make_tool(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.core_plugins = {
            "CorePlugin.dll": FakeVar(True),
        }
        tool.optional_plugins = {
            "OptionalPlugin.dll": FakeVar(False),
            "no1600x1200.dll": FakeVar(False),
        }
        return tool

    def test_preserves_manual_entries_comments_and_replaces_managed_entries(self):
        tool = self.make_tool()
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "dlls.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(
                    "# user comment\n"
                    "CorePlugin.dll\n"
                    "MyCustomPlugin.dll\n"
                    "mycustomplugin.dll\n"
                    "; another comment\n"
                    "dxvk\n"
                )

            tool._write_dlls_file(
                root,
                ["dxvk", "CorePlugin.dll", "COREPLUGIN.DLL"],
            )

            with open(path, "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()

            self.assertEqual(
                lines,
                [
                    "dxvk",
                    "CorePlugin.dll",
                    "",
                    "# user comment",
                    "MyCustomPlugin.dll",
                    "; another comment",
                ],
            )

    def test_removes_unchecked_tool_owned_entry_without_removing_manual_dll(self):
        tool = self.make_tool()
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "dlls.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("OptionalPlugin.dll\nManual.dll\n")

            tool._write_dlls_file(root, [])

            with open(path, "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "Manual.dll\n")


class PluginConflictTests(unittest.TestCase):
    def test_vmmfix_wins_over_no1600_during_normalization(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        no1600 = FakeVar(True)
        tool.optional_plugins = {"no1600x1200.dll": no1600}
        tool.vmmfix_enabled = FakeVar(True)

        changed = tool._normalize_plugin_conflicts()

        self.assertTrue(changed)
        self.assertFalse(no1600.get())
        self.assertTrue(tool.vmmfix_enabled.get())


class WdbBlockerTests(unittest.TestCase):
    def make_tool(self, enabled):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.vt_clear_wdb = FakeVar(enabled)
        return tool

    def test_enabled_replaces_cache_directory_with_owned_empty_blocker(self):
        tool = self.make_tool(True)
        with tempfile.TemporaryDirectory() as root:
            wdb = os.path.join(root, "WDB")
            os.makedirs(wdb)
            with open(os.path.join(wdb, "cache.bin"), "wb") as handle:
                handle.write(b"cache")

            tool.configure_wdb_cache(root)

            self.assertTrue(os.path.isfile(wdb))
            self.assertEqual(os.path.getsize(wdb), 0)
            marker = tool._wdb_marker_path(root)
            self.assertTrue(os.path.isfile(marker))
            with open(marker, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            self.assertEqual(data["type"], "empty_file_blocker")

    def test_disabled_preserves_unowned_empty_wdb_file(self):
        tool = self.make_tool(False)
        with tempfile.TemporaryDirectory() as root:
            wdb = os.path.join(root, "WDB")
            open(wdb, "wb").close()

            with mock.patch("setup_tool.messagebox.showwarning") as warning:
                tool.configure_wdb_cache(root)

            self.assertTrue(os.path.isfile(wdb))
            warning.assert_called_once()

    def test_disabled_removes_owned_empty_blocker(self):
        tool = self.make_tool(False)
        with tempfile.TemporaryDirectory() as root:
            wdb = os.path.join(root, "WDB")
            open(wdb, "wb").close()
            tool._write_wdb_marker(root)

            tool.configure_wdb_cache(root)

            self.assertFalse(os.path.exists(wdb))
            self.assertFalse(os.path.exists(tool._wdb_marker_path(root)))

    def test_enabled_refuses_non_empty_foreign_wdb_file(self):
        tool = self.make_tool(True)
        with tempfile.TemporaryDirectory() as root:
            wdb = os.path.join(root, "WDB")
            with open(wdb, "wb") as handle:
                handle.write(b"foreign")

            with self.assertRaises(RuntimeError):
                tool.configure_wdb_cache(root)

            with open(wdb, "rb") as handle:
                self.assertEqual(handle.read(), b"foreign")


class DxvkOwnershipTests(unittest.TestCase):
    def make_tool(self, mode):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.rendering_mode = FakeVar(mode)
        return tool

    def make_payload(self, root):
        payload = os.path.join(root, "Payload")
        dxvk = os.path.join(payload, "DXVK_Standard")
        os.makedirs(dxvk)
        with open(os.path.join(dxvk, "d3d9.dll"), "wb") as handle:
            handle.write(b"bundled-dxvk")
        with open(os.path.join(payload, "dxvk.conf"), "wb") as handle:
            handle.write(b"bundled-conf")

    def test_enable_then_disable_parks_preexisting_renderer_files(self):
        tool = self.make_tool("dxvk")
        with tempfile.TemporaryDirectory() as bundle, tempfile.TemporaryDirectory() as target:
            self.make_payload(bundle)
            d3d9 = os.path.join(target, "d3d9.dll")
            conf = os.path.join(target, "dxvk.conf")
            with open(d3d9, "wb") as handle:
                handle.write(b"user-d3d9")
            with open(conf, "wb") as handle:
                handle.write(b"user-conf")

            with mock.patch("setup_tool.get_base_path", return_value=bundle):
                tool.configure_dxvk(target)
                with open(d3d9, "rb") as handle:
                    self.assertEqual(handle.read(), b"bundled-dxvk")
                with open(conf, "rb") as handle:
                    self.assertEqual(handle.read(), b"bundled-conf")

                tool.rendering_mode.set("directx9")
                tool.configure_dxvk(target)

            self.assertFalse(os.path.exists(d3d9))
            self.assertFalse(os.path.exists(conf))
            backup = tool._external_renderer_backup_dir(target)
            with open(os.path.join(backup, "d3d9.dll"), "rb") as handle:
                self.assertEqual(handle.read(), b"user-d3d9")
            with open(os.path.join(backup, "dxvk.conf"), "rb") as handle:
                self.assertEqual(handle.read(), b"user-conf")

    def test_directx9_parks_unowned_renderer_files(self):
        tool = self.make_tool("directx9")
        with tempfile.TemporaryDirectory() as target:
            d3d9 = os.path.join(target, "d3d9.dll")
            conf = os.path.join(target, "dxvk.conf")
            with open(d3d9, "wb") as handle:
                handle.write(b"manual-d3d9")
            with open(conf, "wb") as handle:
                handle.write(b"manual-conf")

            tool.configure_dxvk(target)

            self.assertFalse(os.path.exists(d3d9))
            self.assertFalse(os.path.exists(conf))
            backup = tool._external_renderer_backup_dir(target)
            with open(os.path.join(backup, "d3d9.dll"), "rb") as handle:
                self.assertEqual(handle.read(), b"manual-d3d9")
            with open(os.path.join(backup, "dxvk.conf"), "rb") as handle:
                self.assertEqual(handle.read(), b"manual-conf")


class StrictCleanupTests(unittest.TestCase):
    def test_locked_managed_plugin_removal_is_not_silently_ignored(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.install_autologin = FakeVar(True)
        tool.core_plugins = {"CorePlugin.dll": FakeVar(False)}
        tool.optional_plugins = {}
        tool.addon_dependencies = {}

        with tempfile.TemporaryDirectory() as target:
            dll_path = os.path.join(target, "CorePlugin.dll")
            with open(dll_path, "wb") as handle:
                handle.write(b"dll")

            with mock.patch("setup_tool.os.remove", side_effect=PermissionError("locked")):
                with self.assertRaises(RuntimeError):
                    tool.clean_unselected_files(target)


class ManagedPackageTests(unittest.TestCase):
    def test_mpq_revision_and_magic_are_both_checked(self):
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "Data", "patch-N.mpq")
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as handle:
                handle.write(b"MPQ test payload")

            remote_packages._write_managed_manifest(
                root,
                "visual_darker_nights",
                [os.path.join("Data", "patch-N.mpq")],
                revision="1",
            )

            self.assertTrue(
                remote_packages.managed_mpq_is_current(
                    root,
                    "visual_darker_nights",
                    "1",
                )
            )
            self.assertFalse(
                remote_packages.managed_mpq_is_current(
                    root,
                    "visual_darker_nights",
                    "2",
                )
            )

            with open(target, "wb") as handle:
                handle.write(b"BAD")
            self.assertFalse(
                remote_packages.managed_mpq_is_current(
                    root,
                    "visual_darker_nights",
                    "1",
                )
            )

    def test_pink_herbs_v2_migration_restores_original_patch_h(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as src:
            mod_id = "visual_pink_herbs"
            legacy_rel = os.path.join("Data", "patch-H.mpq")
            new_rel = os.path.join("Data", "patch-V.mpq")
            legacy_target = os.path.join(root, legacy_rel)
            source = os.path.join(src, "pink-herbs.mpq")

            os.makedirs(os.path.dirname(legacy_target))
            with open(source, "wb") as handle:
                handle.write(b"MPQ pink-herbs")
            with open(legacy_target, "wb") as handle:
                handle.write(b"MPQ pink-herbs")

            _, _, backup_root = remote_packages._managed_locations(root, mod_id)
            backup_h = os.path.join(backup_root, legacy_rel)
            os.makedirs(os.path.dirname(backup_h))
            with open(backup_h, "wb") as handle:
                handle.write(b"MPQ faithful-upscale")

            remote_packages._write_managed_manifest(
                root, mod_id, [legacy_rel], revision="1"
            )
            remote_packages._migrate_legacy_pink_herbs_patch(root, source)
            remote_packages._install_managed_files(
                root, mod_id, [(source, new_rel)], revision="2"
            )

            with open(legacy_target, "rb") as handle:
                self.assertEqual(handle.read(), b"MPQ faithful-upscale")
            with open(os.path.join(root, new_rel), "rb") as handle:
                self.assertEqual(handle.read(), b"MPQ pink-herbs")

    def test_pink_herbs_v2_migration_preserves_replaced_patch_h(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as src:
            mod_id = "visual_pink_herbs"
            legacy_rel = os.path.join("Data", "patch-H.mpq")
            new_rel = os.path.join("Data", "patch-V.mpq")
            legacy_target = os.path.join(root, legacy_rel)
            source = os.path.join(src, "pink-herbs.mpq")

            os.makedirs(os.path.dirname(legacy_target))
            with open(source, "wb") as handle:
                handle.write(b"MPQ pink-herbs")
            with open(legacy_target, "wb") as handle:
                handle.write(b"MPQ replacement-patch-h")

            _, _, backup_root = remote_packages._managed_locations(root, mod_id)
            backup_h = os.path.join(backup_root, legacy_rel)
            os.makedirs(os.path.dirname(backup_h))
            with open(backup_h, "wb") as handle:
                handle.write(b"MPQ older-original-patch-h")

            remote_packages._write_managed_manifest(
                root, mod_id, [legacy_rel], revision="1"
            )
            remote_packages._migrate_legacy_pink_herbs_patch(root, source)
            remote_packages._install_managed_files(
                root, mod_id, [(source, new_rel)], revision="2"
            )

            with open(legacy_target, "rb") as handle:
                self.assertEqual(handle.read(), b"MPQ replacement-patch-h")
            with open(os.path.join(root, new_rel), "rb") as handle:
                self.assertEqual(handle.read(), b"MPQ pink-herbs")

    def test_transactional_sound_pack_rolls_back_all_files_and_manifest(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as src:
            mod_id = "audio_test"
            target_a = os.path.join(root, "Sound", "a.wav")
            target_b = os.path.join(root, "Sound", "b.wav")
            os.makedirs(os.path.dirname(target_a))
            with open(target_a, "wb") as handle:
                handle.write(b"old-a")
            with open(target_b, "wb") as handle:
                handle.write(b"old-b")

            remote_packages._write_managed_manifest(
                root,
                mod_id,
                [os.path.join("Sound", "a.wav"), os.path.join("Sound", "b.wav")],
            )
            _, manifest_path, _ = remote_packages._managed_locations(root, mod_id)
            with open(manifest_path, "rb") as handle:
                old_manifest = handle.read()

            source_a = os.path.join(src, "a.wav")
            source_b = os.path.join(src, "b.wav")
            with open(source_a, "wb") as handle:
                handle.write(b"new-a")
            with open(source_b, "wb") as handle:
                handle.write(b"new-b")

            original_replace = remote_packages._atomic_replace_file
            failure_triggered = False

            def fail_once(source, target):
                nonlocal failure_triggered
                if (
                    not failure_triggered
                    and os.path.abspath(source) == os.path.abspath(source_b)
                    and os.path.abspath(target) == os.path.abspath(target_b)
                ):
                    failure_triggered = True
                    raise OSError("simulated locked file")
                return original_replace(source, target)

            with mock.patch(
                "remote_packages._atomic_replace_file",
                side_effect=fail_once,
            ):
                with self.assertRaises(remote_packages.RemotePackageError):
                    remote_packages._install_managed_files_transactional(
                        root,
                        mod_id,
                        [
                            (source_a, os.path.join("Sound", "a.wav")),
                            (source_b, os.path.join("Sound", "b.wav")),
                        ],
                    )

            with open(target_a, "rb") as handle:
                self.assertEqual(handle.read(), b"old-a")
            with open(target_b, "rb") as handle:
                self.assertEqual(handle.read(), b"old-b")
            with open(manifest_path, "rb") as handle:
                self.assertEqual(handle.read(), old_manifest)


class AutoLoginEncryptionTests(unittest.TestCase):
    class FakeKey:
        def __init__(self, registry):
            self.registry = registry

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeWinreg:
        HKEY_CURRENT_USER = object()
        KEY_READ = 0x20019
        KEY_SET_VALUE = 0x0002
        REG_SZ = 1

        def __init__(self, values=None):
            self.values = dict(values or {})

        def OpenKey(self, root, path, reserved, access):
            if path != "Environment":
                raise FileNotFoundError(path)
            return AutoLoginEncryptionTests.FakeKey(self)

        def QueryValueEx(self, key, name):
            if name not in self.values:
                raise FileNotFoundError(name)
            return self.values[name], self.REG_SZ

        def CreateKeyEx(self, root, path, reserved, access):
            self.created_path = path
            return AutoLoginEncryptionTests.FakeKey(self)

        def SetValueEx(self, key, name, reserved, value_type, value):
            self.values[name] = value

    def make_tool(self, autologin=True, nampower=True):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.install_autologin = FakeVar(autologin)
        tool.core_plugins = {"nampower.dll": FakeVar(nampower)}
        tool._broadcast_environment_change = mock.Mock()
        return tool

    def test_skips_key_creation_when_feature_pair_is_not_enabled(self):
        fake_registry = self.FakeWinreg()
        tool = self.make_tool(autologin=False, nampower=True)

        with mock.patch.object(setup_tool, "winreg", fake_registry):
            result = tool.configure_autologin_encryption()

        self.assertEqual(result, "not-needed")
        self.assertEqual(fake_registry.values, {})
        tool._broadcast_environment_change.assert_not_called()

    def test_preserves_existing_inherited_key(self):
        fake_registry = self.FakeWinreg()
        tool = self.make_tool()

        with mock.patch.object(setup_tool, "winreg", fake_registry), mock.patch.dict(
            os.environ,
            {"WOW_ENCRYPTION_KEY": "already-present"},
            clear=False,
        ):
            result = tool.configure_autologin_encryption()

        self.assertEqual(result, "existing")
        self.assertEqual(fake_registry.values, {})
        tool._broadcast_environment_change.assert_not_called()

    def test_reuses_existing_registry_key_without_rotating_it(self):
        fake_registry = self.FakeWinreg(
            {"WOW_ENCRYPTION_KEY": "persisted-secret"}
        )
        tool = self.make_tool()

        original = os.environ.pop("WOW_ENCRYPTION_KEY", None)
        try:
            with mock.patch.object(setup_tool, "winreg", fake_registry):
                result = tool.configure_autologin_encryption()

            self.assertEqual(result, "existing")
            self.assertEqual(
                fake_registry.values["WOW_ENCRYPTION_KEY"],
                "persisted-secret",
            )
            self.assertEqual(
                os.environ["WOW_ENCRYPTION_KEY"],
                "persisted-secret",
            )
            tool._broadcast_environment_change.assert_called_once()
        finally:
            if original is None:
                os.environ.pop("WOW_ENCRYPTION_KEY", None)
            else:
                os.environ["WOW_ENCRYPTION_KEY"] = original

    def test_creates_256_bit_user_key_once(self):
        fake_registry = self.FakeWinreg()
        tool = self.make_tool()
        generated = "ab" * 32

        original = os.environ.pop("WOW_ENCRYPTION_KEY", None)
        try:
            with mock.patch.object(setup_tool, "winreg", fake_registry), mock.patch.object(
                setup_tool.secrets,
                "token_hex",
                return_value=generated,
            ) as token_hex:
                result = tool.configure_autologin_encryption()

            self.assertEqual(result, "created")
            token_hex.assert_called_once_with(32)
            self.assertEqual(
                fake_registry.values["WOW_ENCRYPTION_KEY"],
                generated,
            )
            self.assertEqual(os.environ["WOW_ENCRYPTION_KEY"], generated)
            tool._broadcast_environment_change.assert_called_once()
        finally:
            if original is None:
                os.environ.pop("WOW_ENCRYPTION_KEY", None)
            else:
                os.environ["WOW_ENCRYPTION_KEY"] = original


class DepElevationTests(unittest.TestCase):
    def test_quotes_script_path_when_game_folder_contains_spaces(self):
        tool = WowSetupTool.__new__(WowSetupTool)

        with tempfile.TemporaryDirectory(prefix="01 OctoWoW ") as root:
            captured = {}

            def fake_run(args, **kwargs):
                captured["args"] = args
                script_path = os.path.join(
                    root,
                    ".modernization_tool",
                    "process_mitigation.ps1",
                )
                self.assertIn(" ", script_path)
                self.assertTrue(os.path.isfile(script_path))
                return mock.Mock(returncode=0, stdout="", stderr="")

            with mock.patch("setup_tool.subprocess.run", side_effect=fake_run):
                tool._run_elevated_powershell(
                    root,
                    "Set-ProcessMitigation -Name 'WoW_Modernized.exe' "
                    "-Disable DEP, EmulateAtlThunks",
                    "Disabling DEP for WoW_Modernized.exe",
                )

            launcher = captured["args"][-1]
            escaped_script = os.path.join(
                root,
                ".modernization_tool",
                "process_mitigation.ps1",
            ).replace("'", "''")

            self.assertIn(
                f"$scriptPath = '{escaped_script}';",
                launcher,
            )
            self.assertIn(
                "'-NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"' "
                "+ $scriptPath + '\"'",
                launcher,
            )
            self.assertFalse(
                os.path.exists(
                    os.path.join(
                        root,
                        ".modernization_tool",
                        "process_mitigation.ps1",
                    )
                )
            )


class PeValidationTests(unittest.TestCase):
    def write_minimal_x86_pe(self, path):
        data = bytearray(2048)
        data[0:2] = b"MZ"
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<H", data, 0x84, 0x014C)
        struct.pack_into("<H", data, 0x84 + 16, 0xE0)
        struct.pack_into("<H", data, 0x84 + 20, 0x010B)
        with open(path, "wb") as handle:
            handle.write(data)

    def test_accepts_x86_pe_and_rejects_non_pe_download(self):
        with tempfile.TemporaryDirectory() as root:
            good = os.path.join(root, "good.dll")
            bad = os.path.join(root, "bad.dll")
            self.write_minimal_x86_pe(good)
            with open(bad, "wb") as handle:
                handle.write(b"<html>not a dll</html>" * 100)

            remote_packages._verify_x86_pe(good, "good.dll")
            with self.assertRaises(remote_packages.RemotePackageError):
                remote_packages._verify_x86_pe(bad, "bad.dll")


class SmartUpdateTests(unittest.TestCase):
    def test_package_state_tracks_revision_and_local_integrity(self):
        with tempfile.TemporaryDirectory() as root:
            dll = os.path.join(root, "Example.dll")
            addon = os.path.join(root, "Interface", "AddOns", "Example")
            os.makedirs(addon)
            with open(dll, "wb") as handle:
                handle.write(b"dll-v1")
            with open(os.path.join(addon, "Example.toc"), "wb") as handle:
                handle.write(b"addon-v1")

            remote_packages._record_package_state(
                root,
                "example",
                "v1",
                ["Example.dll", os.path.join("Interface", "AddOns", "Example")],
            )

            self.assertTrue(
                remote_packages._package_state_is_current(root, "example", "v1")
            )
            self.assertFalse(
                remote_packages._package_state_is_current(root, "example", "v2")
            )

            with open(os.path.join(addon, "Example.toc"), "wb") as handle:
                handle.write(b"modified")
            self.assertFalse(
                remote_packages._package_state_is_current(root, "example", "v1")
            )

    def test_release_component_skips_download_when_revision_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "ClassicAPI.dll")
            with open(target, "wb") as handle:
                handle.write(b"already-installed")

            remote_packages._record_package_state(
                root,
                "classicapi",
                "v-test",
                ["ClassicAPI.dll"],
            )
            release = {
                "tag_name": "v-test",
                "assets": [
                    {
                        "name": "ClassicAPI.dll",
                        "browser_download_url": "https://example.invalid/ClassicAPI.dll",
                    }
                ],
            }

            with mock.patch(
                "remote_packages._latest_release",
                return_value=release,
            ), mock.patch(
                "remote_packages._download_asset",
                side_effect=AssertionError("unchanged component was downloaded"),
            ) as download:
                self.assertEqual(
                    remote_packages.install_classicapi(root),
                    "v-test",
                )

            download.assert_not_called()

    def test_branch_component_skips_archive_when_commit_and_files_match(self):
        with tempfile.TemporaryDirectory() as root:
            sound = os.path.join(root, "Sound", "example.wav")
            os.makedirs(os.path.dirname(sound))
            with open(sound, "wb") as handle:
                handle.write(b"sound")

            remote_packages._record_package_state(
                root,
                "audio_example",
                "abcdef1234567890",
                [os.path.join("Sound", "example.wav")],
            )

            with mock.patch(
                "remote_packages._branch_head_sha",
                return_value="abcdef1234567890",
            ), mock.patch(
                "remote_packages._download_github_branch_archive",
                side_effect=AssertionError("unchanged branch archive was downloaded"),
            ) as download:
                revision = remote_packages._install_github_sound_pack(
                    root,
                    "audio_example",
                    "owner/repo",
                    "main",
                    "Sound",
                    "Sound",
                )

            self.assertEqual(revision, "abcdef1234567890")
            download.assert_not_called()

    def test_vanilla_tweaks_skips_package_when_output_and_revision_match(self):
        tool = setup_tool_dynamic.ModernWowSetupTool.__new__(
            setup_tool_dynamic.ModernWowSetupTool
        )
        tool._existing_vanilla_tweaks_output_matches = mock.Mock(
            return_value=(
                True,
                {
                    "patcher_source": "online",
                    "patcher_version": "Vanilla Tweaks v1",
                    "patcher_revision": "v1",
                },
            )
        )
        tool._report_download_progress = mock.Mock()
        tool._close_download_progress = mock.Mock()

        release_info = {
            "release": {},
            "asset": {},
            "revision": "v1",
            "version": "Vanilla Tweaks v1",
        }

        with tempfile.TemporaryDirectory() as root, mock.patch(
            "setup_tool_dynamic.remote_packages.vanilla_tweaks_release_info",
            return_value=release_info,
        ), mock.patch(
            "setup_tool_dynamic.remote_packages.prepare_vanilla_tweaks",
            side_effect=AssertionError("unchanged vanilla-tweaks was downloaded"),
        ) as prepare:
            result = tool.run_vanilla_tweaks(root)

        self.assertEqual(result, os.path.join(root, "WoW_Modernized.exe"))
        prepare.assert_not_called()
        tool._close_download_progress.assert_called_once()


class WowPresenceIntegrationTests(unittest.TestCase):
    def make_tool(self, selected=False):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.install_autologin = FakeVar(False)
        tool.core_plugins = {}
        tool.addon_dependencies = {}
        tool.optional_plugins = {
            "WowPresence.dll": FakeVar(selected),
        }
        return tool

    def test_config_defaults_migrate_placeholder_and_preserve_custom_id(self):
        with tempfile.TemporaryDirectory() as root:
            data_dir = remote_packages.ensure_wowpresence_config(root)
            app_id = os.path.join(data_dir, "discord_application_id")
            flags = os.path.join(data_dir, "discord_broadcast_flags")

            with open(app_id, "r", encoding="ascii") as handle:
                self.assertEqual(
                    handle.read().strip(),
                    remote_packages.WOWPRESENCE_DEFAULT_APPLICATION_ID,
                )
            with open(flags, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "63")

            with open(app_id, "w", encoding="ascii") as handle:
                handle.write(
                    remote_packages.WOWPRESENCE_APPLICATION_ID_PLACEHOLDER + "\n"
                )
            remote_packages.ensure_wowpresence_config(root)
            with open(app_id, "r", encoding="ascii") as handle:
                self.assertEqual(
                    handle.read().strip(),
                    remote_packages.WOWPRESENCE_DEFAULT_APPLICATION_ID,
                )

            with open(app_id, "w", encoding="ascii") as handle:
                handle.write("123456789012345678\n")
            with open(flags, "w", encoding="ascii") as handle:
                handle.write("31\n")
            remote_packages.ensure_wowpresence_config(root)
            with open(app_id, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "123456789012345678")
            with open(flags, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "31")

    def test_install_wowpresence_from_zip_preserves_user_config(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as package_root:
            data_dir = remote_packages.ensure_wowpresence_config(root)
            app_id = os.path.join(data_dir, "discord_application_id")
            flags = os.path.join(data_dir, "discord_broadcast_flags")
            with open(app_id, "w", encoding="ascii") as handle:
                handle.write("123456789012345678\n")
            with open(flags, "w", encoding="ascii") as handle:
                handle.write("31\n")

            dll = os.path.join(package_root, "WowPresence.dll")
            exe = os.path.join(package_root, "WowPresence.exe")
            PeValidationTests().write_minimal_x86_pe(dll)
            PeValidationTests().write_minimal_x86_pe(exe)

            zip_path = os.path.join(package_root, "WowPresence.zip")
            with remote_packages.zipfile.ZipFile(zip_path, "w") as archive:
                archive.write(dll, "WowPresence.dll")
                archive.write(exe, "WowPresence.exe")
                archive.writestr(
                    "WowPresence/discord_application_id",
                    "999999999999999999\n",
                )
                archive.writestr("WowPresence/discord_broadcast_flags", "0\n")

            release = {
                "tag_name": "v-test",
                "assets": [
                    {
                        "name": "WowPresence.zip",
                        "browser_download_url": "https://example.invalid/WowPresence.zip",
                    }
                ],
            }

            with mock.patch(
                "remote_packages._latest_release",
                return_value=release,
            ), mock.patch(
                "remote_packages._download_asset",
                return_value=zip_path,
            ) as download:
                self.assertEqual(
                    remote_packages.install_wowpresence(root),
                    "v-test",
                )

            download.assert_called_once()
            remote_packages._verify_x86_pe(
                os.path.join(root, "WowPresence.dll"),
                "WowPresence.dll",
            )
            remote_packages._verify_x86_pe(
                os.path.join(root, "WowPresence.exe"),
                "WowPresence.exe",
            )

            with open(app_id, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "123456789012345678")
            with open(flags, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "31")

            manifest = remote_packages._load_managed_manifest_data(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
            )
            self.assertEqual(manifest.get("revision"), "v-test")
            self.assertEqual(
                set((manifest.get("file_sha256") or {}).keys()),
                {"WowPresence.dll", "WowPresence.exe"},
            )

    def test_unchecked_manual_wowpresence_is_untouched(self):
        tool = self.make_tool(selected=False)
        with tempfile.TemporaryDirectory() as root:
            dll = os.path.join(root, "WowPresence.dll")
            exe = os.path.join(root, "WowPresence.exe")
            dlls = os.path.join(root, "dlls.txt")
            with open(dll, "wb") as handle:
                handle.write(b"manual-dll")
            with open(exe, "wb") as handle:
                handle.write(b"manual-exe")
            with open(dlls, "w", encoding="utf-8") as handle:
                handle.write("WowPresence.dll\nManual.dll\n")

            tool.clean_unselected_files(root)
            tool._write_dlls_file(root, [])

            self.assertTrue(os.path.isfile(dll))
            self.assertTrue(os.path.isfile(exe))
            with open(dlls, "r", encoding="utf-8") as handle:
                self.assertIn("WowPresence.dll", handle.read().splitlines())

    def test_unchecked_tool_owned_wowpresence_is_removed_but_config_survives(self):
        tool = self.make_tool(selected=False)
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as src:
            source_dll = os.path.join(src, "WowPresence.dll")
            source_exe = os.path.join(src, "WowPresence.exe")
            with open(source_dll, "wb") as handle:
                handle.write(b"tool-dll")
            with open(source_exe, "wb") as handle:
                handle.write(b"tool-exe")

            remote_packages._install_managed_files_transactional(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                [
                    (source_dll, "WowPresence.dll"),
                    (source_exe, "WowPresence.exe"),
                ],
                revision="v-test",
            )
            remote_packages._set_managed_manifest_values(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                dlls_entry_preexisting=False,
            )
            data_dir = remote_packages.ensure_wowpresence_config(root)
            with open(os.path.join(root, "dlls.txt"), "w", encoding="utf-8") as handle:
                handle.write("WowPresence.dll\nManual.dll\n")

            tool.clean_unselected_files(root)
            tool._write_dlls_file(root, [])

            self.assertFalse(os.path.exists(os.path.join(root, "WowPresence.dll")))
            self.assertFalse(os.path.exists(os.path.join(root, "WowPresence.exe")))
            self.assertTrue(os.path.isdir(data_dir))
            with open(os.path.join(root, "dlls.txt"), "r", encoding="utf-8") as handle:
                lines = handle.read().splitlines()
            self.assertNotIn("WowPresence.dll", lines)
            self.assertIn("Manual.dll", lines)

    def test_manual_wowpresence_is_restored_after_tool_ownership(self):
        tool = self.make_tool(selected=False)
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as src:
            live_dll = os.path.join(root, "WowPresence.dll")
            live_exe = os.path.join(root, "WowPresence.exe")
            with open(live_dll, "wb") as handle:
                handle.write(b"manual-dll")
            with open(live_exe, "wb") as handle:
                handle.write(b"manual-exe")
            with open(os.path.join(root, "dlls.txt"), "w", encoding="utf-8") as handle:
                handle.write("WowPresence.dll\n")

            source_dll = os.path.join(src, "WowPresence.dll")
            source_exe = os.path.join(src, "WowPresence.exe")
            with open(source_dll, "wb") as handle:
                handle.write(b"managed-dll")
            with open(source_exe, "wb") as handle:
                handle.write(b"managed-exe")

            remote_packages._install_managed_files_transactional(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                [
                    (source_dll, "WowPresence.dll"),
                    (source_exe, "WowPresence.exe"),
                ],
                revision="v-test",
            )
            remote_packages._set_managed_manifest_values(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                dlls_entry_preexisting=True,
            )

            tool.clean_unselected_files(root)
            tool._write_dlls_file(root, [])

            with open(live_dll, "rb") as handle:
                self.assertEqual(handle.read(), b"manual-dll")
            with open(live_exe, "rb") as handle:
                self.assertEqual(handle.read(), b"manual-exe")
            with open(os.path.join(root, "dlls.txt"), "r", encoding="utf-8") as handle:
                self.assertIn("WowPresence.dll", handle.read().splitlines())

    def test_installed_asset_integrity_detects_corruption(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "WowPresence.dll")
            payload = b"A" * 2048
            with open(path, "wb") as handle:
                handle.write(payload)
            digest = __import__("hashlib").sha256(payload).hexdigest()
            asset = {
                "size": len(payload),
                "digest": "sha256:" + digest,
            }
            self.assertTrue(
                remote_packages._installed_asset_is_current(
                    path,
                    asset,
                    "WowPresence.dll",
                )
            )

            with open(path, "r+b") as handle:
                handle.seek(100)
                handle.write(b"B")
            self.assertFalse(
                remote_packages._installed_asset_is_current(
                    path,
                    asset,
                    "WowPresence.dll",
                )
            )


class SettingsRecoveryTests(unittest.TestCase):
    def test_corrupt_settings_are_left_untouched_and_legacy_state_is_recovered(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool._loading_settings = False
        tool._reset_settings_to_defaults = mock.Mock()
        tool._load_legacy_install_state = mock.Mock()
        tool._normalize_plugin_conflicts = mock.Mock(return_value=False)
        tool.toggle_safety_limits = mock.Mock()
        tool.update_superwow_managed_controls = mock.Mock()

        with tempfile.TemporaryDirectory() as root:
            settings_path = tool._settings_path(root)
            os.makedirs(os.path.dirname(settings_path))
            damaged = b"{ this is not valid json"
            with open(settings_path, "wb") as handle:
                handle.write(damaged)

            with mock.patch("setup_tool.messagebox.showwarning") as warning:
                loaded = tool.load_settings(root)

            self.assertFalse(loaded)
            self.assertFalse(tool._loading_settings)
            self.assertEqual(tool._reset_settings_to_defaults.call_count, 2)
            tool._load_legacy_install_state.assert_called_once_with(root)
            warning.assert_called_once()

            with open(settings_path, "rb") as handle:
                self.assertEqual(handle.read(), damaged)


if __name__ == "__main__":
    unittest.main()
