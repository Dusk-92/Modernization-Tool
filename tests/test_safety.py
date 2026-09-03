import hashlib
import json
import os
import struct
import tempfile
import unittest
import urllib.error
import zipfile
from unittest import mock

import remote_packages
import setup_tool
import setup_tool_dynamic
from setup_tool import WowSetupTool
from setup_tool_dynamic import ModernWowSetupTool


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

    def test_current_package_cleans_stale_transaction_backup(self):
        with tempfile.TemporaryDirectory() as root:
            dll = os.path.join(root, "UnitXP_SP3.dll")
            with open(dll, "wb") as handle:
                handle.write(b"current-unitxp")

            remote_packages._record_package_state(
                root,
                "unitxp_sp3",
                "v90",
                ["UnitXP_SP3.dll"],
            )

            stale_backup = dll + ".modernization-backup-941614e28c62"
            with open(stale_backup, "wb") as handle:
                handle.write(b"old-unitxp")

            self.assertTrue(
                remote_packages._package_state_is_current(
                    root,
                    "unitxp_sp3",
                    "v90",
                )
            )
            self.assertFalse(os.path.exists(stale_backup))
            self.assertTrue(os.path.isfile(dll))

    def test_non_current_package_keeps_transaction_backup_for_recovery(self):
        with tempfile.TemporaryDirectory() as root:
            dll = os.path.join(root, "UnitXP_SP3.dll")
            with open(dll, "wb") as handle:
                handle.write(b"current-unitxp")

            remote_packages._record_package_state(
                root,
                "unitxp_sp3",
                "v90",
                ["UnitXP_SP3.dll"],
            )

            stale_backup = dll + ".modernization-backup-recovery"
            with open(stale_backup, "wb") as handle:
                handle.write(b"old-unitxp")

            with open(dll, "wb") as handle:
                handle.write(b"modified-after-state")

            self.assertFalse(
                remote_packages._package_state_is_current(
                    root,
                    "unitxp_sp3",
                    "v90",
                )
            )
            self.assertTrue(os.path.exists(stale_backup))

    def test_release_asset_revision_detects_replaced_asset_under_same_tag(self):
        release_a = {
            "tag_name": "Release",
            "assets": [
                {
                    "id": 1,
                    "name": "package.zip",
                    "updated_at": "2026-09-01T10:00:00Z",
                    "size": 100,
                }
            ],
        }
        release_b = {
            "tag_name": "Release",
            "assets": [
                {
                    "id": 2,
                    "name": "package.zip",
                    "updated_at": "2026-09-02T10:00:00Z",
                    "size": 120,
                }
            ],
        }

        self.assertNotEqual(
            remote_packages._release_asset_revision(
                release_a,
                release_a["assets"][0],
            ),
            remote_packages._release_asset_revision(
                release_b,
                release_b["assets"][0],
            ),
        )

    def test_release_component_skips_download_when_revision_and_hashes_match(self):
        with tempfile.TemporaryDirectory() as root:
            target = os.path.join(root, "ClassicAPI.dll")
            with open(target, "wb") as handle:
                handle.write(b"already-installed")

            release = {
                "tag_name": "v-test",
                "assets": [
                    {
                        "name": "ClassicAPI.dll",
                        "browser_download_url": "https://example.invalid/ClassicAPI.dll",
                    }
                ],
            }
            revision = remote_packages._release_asset_revision(
                release,
                release["assets"][0],
            )
            remote_packages._record_package_state(
                root,
                "classicapi",
                revision,
                ["ClassicAPI.dll"],
            )

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
                self.assertEqual(handle.read().strip(), "127")

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
            ) as latest_release, mock.patch(
                "remote_packages._download_asset",
                return_value=zip_path,
            ) as download:
                self.assertEqual(
                    remote_packages.install_wowpresence(root),
                    "v-test",
                )

            latest_release.assert_called_once_with(
                remote_packages.WOWPRESENCE_REPO,
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


class WowPresenceDetailPreferenceTests(unittest.TestCase):
    def make_tool(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool.discord_show_character_details = FakeVar(True)
        tool.discord_detail_vars = {
            "name": FakeVar(True),
            "guild": FakeVar(True),
            "race": FakeVar(True),
            "faction": FakeVar(True),
            "class": FakeVar(True),
            "level": FakeVar(True),
            "zone": FakeVar(True),
        }
        return tool

    def test_detail_mask_supports_race_and_all_details_switch(self):
        tool = self.make_tool()
        self.assertEqual(
            tool._discord_broadcast_mask(),
            remote_packages.WOWPRESENCE_SHARE_ALL,
        )

        # The master switch always means "show all" even if a variable is
        # changed programmatically while its checkbox would be disabled.
        tool.discord_detail_vars["race"].set(False)
        self.assertEqual(
            tool._discord_broadcast_mask(),
            remote_packages.WOWPRESENCE_SHARE_ALL,
        )

        # Once the master is off, the individual choices become authoritative.
        tool.discord_show_character_details.set(False)
        self.assertEqual(tool._discord_broadcast_mask(), 63)
        self.assertFalse(tool.discord_detail_vars["race"].get())
        self.assertTrue(tool.discord_detail_vars["zone"].get())

    def test_legacy_six_bit_mask_keeps_race_enabled(self):
        tool = self.make_tool()
        with tempfile.TemporaryDirectory() as root:
            data_dir = remote_packages.ensure_wowpresence_config(root)
            flags = os.path.join(data_dir, "discord_broadcast_flags")
            with open(flags, "w", encoding="ascii") as handle:
                handle.write("31\n")

            tool._load_wowpresence_broadcast_preferences(root)

            self.assertFalse(tool.discord_show_character_details.get())
            self.assertTrue(tool.discord_detail_vars["name"].get())
            self.assertTrue(tool.discord_detail_vars["guild"].get())
            self.assertTrue(tool.discord_detail_vars["faction"].get())
            self.assertTrue(tool.discord_detail_vars["class"].get())
            self.assertTrue(tool.discord_detail_vars["level"].get())
            self.assertFalse(tool.discord_detail_vars["zone"].get())
            self.assertTrue(tool.discord_detail_vars["race"].get())

    def test_legacy_default_mask_selects_all_details(self):
        tool = self.make_tool()
        with tempfile.TemporaryDirectory() as root:
            data_dir = remote_packages.ensure_wowpresence_config(root)
            flags = os.path.join(data_dir, "discord_broadcast_flags")
            with open(flags, "w", encoding="ascii") as handle:
                handle.write("63\n")

            tool._load_wowpresence_broadcast_preferences(root)

            self.assertTrue(tool.discord_show_character_details.get())
            self.assertTrue(all(var.get() for var in tool.discord_detail_vars.values()))
            self.assertEqual(
                tool._discord_broadcast_mask(),
                remote_packages.WOWPRESENCE_SHARE_ALL,
            )

    def test_broadcast_flag_writer_preserves_other_config(self):
        with tempfile.TemporaryDirectory() as root:
            data_dir = remote_packages.ensure_wowpresence_config(root)
            app_id = os.path.join(data_dir, "discord_application_id")
            with open(app_id, "w", encoding="ascii") as handle:
                handle.write("123456789012345678\n")

            path = remote_packages.write_wowpresence_broadcast_flags(
                root,
                remote_packages.WOWPRESENCE_SHARE_ALL,
            )
            self.assertEqual(
                remote_packages.read_wowpresence_broadcast_flags(root),
                127,
            )
            with open(path, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "127")
            with open(app_id, "r", encoding="ascii") as handle:
                self.assertEqual(handle.read().strip(), "123456789012345678")

            with self.assertRaises(ValueError):
                remote_packages.write_wowpresence_broadcast_flags(root, 128)

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


class BundledComponentSafetyTests(unittest.TestCase):
    def test_bundled_integrity_uses_recorded_sha256_and_size(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)

        with tempfile.TemporaryDirectory() as root:
            payload = os.path.join(root, "Payload")
            fallback = os.path.join(payload, "Fallback")
            os.makedirs(fallback)
            source = os.path.join(payload, "component.bin")
            with open(source, "wb") as handle:
                handle.write(b"known bundled component")

            expected_sha = hashlib.sha256(
                b"known bundled component"
            ).hexdigest()

            with open(
                os.path.join(fallback, "versions.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "components": {
                            "test": {
                                "files": [
                                    {
                                        "path": "Payload/component.bin",
                                        "size": os.path.getsize(source),
                                        "sha256": expected_sha,
                                    }
                                ]
                            }
                        }
                    },
                    handle,
                )

            with mock.patch("setup_tool_dynamic.get_base_path", return_value=root):
                verified, digest = tool._verified_bundled_file(
                    "Payload/component.bin",
                    "test component",
                )
                self.assertEqual(verified, source)
                self.assertEqual(digest, expected_sha)

                with open(source, "ab") as handle:
                    handle.write(b"!")

                with self.assertRaises(RuntimeError):
                    tool._verified_bundled_file(
                        "Payload/component.bin",
                        "test component",
                    )

    def test_copy_base_files_does_not_copy_component_addons(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool.install_autologin = FakeVar(False)

        with tempfile.TemporaryDirectory() as root:
            payload = os.path.join(root, "Payload")
            os.makedirs(os.path.join(payload, "Interface", "Addons", "nampowersettings"))
            vanilla_fixes = os.path.join(payload, "VanillaFixes.exe")
            vf_patcher = os.path.join(payload, "VfPatcher.dll")
            for path in (vanilla_fixes, vf_patcher):
                with open(path, "wb") as handle:
                    handle.write(b"test")

            tool._verified_bundled_file = mock.Mock(
                side_effect=[
                    (vanilla_fixes, "a" * 64),
                    (vf_patcher, "b" * 64),
                ]
            )

            target = os.path.join(root, "game")
            os.makedirs(target)

            with (
                mock.patch("setup_tool_dynamic.get_base_path", return_value=root),
                mock.patch.object(
                    remote_packages,
                    "_transactional_replace_bundle",
                ) as transaction,
            ):
                tool.copy_base_files(target)

            self.assertFalse(os.path.exists(os.path.join(target, "Interface")))
            transaction.assert_called_once()
            items = transaction.call_args.args[0]
            self.assertEqual(
                [os.path.basename(item[2]) for item in items],
                ["VanillaFixes.exe", "VfPatcher.dll"],
            )

    def test_no1600_uses_bundled_copy_without_online_update(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool.rendering_mode = FakeVar("directx9")
        tool.core_plugins = {}
        tool.classicapi_enabled = FakeVar(False)
        tool.auction_throttle_enabled = FakeVar(False)
        tool.addon_dependencies = {}
        tool.optional_plugins = {
            "no1600x1200.dll": FakeVar(True),
        }
        tool.vmmfix_enabled = FakeVar(False)
        tool.interact_enabled = FakeVar(False)
        tool._install_verified_bundled_file = mock.Mock()
        tool._write_dlls_file = mock.Mock()
        tool._close_download_progress = mock.Mock()
        tool._report_download_progress = mock.Mock()

        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(
                remote_packages,
                "install_no1600x1200",
            ) as online_installer:
                tool.configure_plugins(root)

        online_installer.assert_not_called()
        tool._install_verified_bundled_file.assert_called_once_with(
            "Payload/no1600x1200.dll",
            mock.ANY,
            "no1600x1200.dll",
        )
        self.assertEqual(
            os.path.basename(
                tool._install_verified_bundled_file.call_args.args[1]
            ),
            "no1600x1200.dll",
        )

    def test_superapi_tracks_master_revision(self):
        release = {
            "name": "SuperWoW 2.2",
            "tag_name": "Release",
            "id": 1,
            "assets": [
                {
                    "name": "SuperWoW.zip",
                    "id": 2,
                    "updated_at": "2026-07-16T00:00:00Z",
                    "size": 123,
                }
            ],
        }

        with (
            mock.patch.object(remote_packages, "_latest_release", return_value=release),
            mock.patch.object(
                remote_packages,
                "_package_state_is_current",
                return_value=True,
            ) as state,
            mock.patch.object(
                remote_packages,
                "_branch_head_sha",
                return_value="abc1234",
            ) as branch_head,
        ):
            remote_packages.install_superwow("C:/WoW")

        branch_head.assert_called_once_with("balakethelock/SuperAPI", "master")
        revision = state.call_args.args[2]
        self.assertIn("superapi:abc1234", revision)

    def test_package_cache_rejects_tampered_artifact(self):
        with tempfile.TemporaryDirectory() as root:
            source = os.path.join(root, "source.bin")
            with open(source, "wb") as handle:
                handle.write(b"validated fallback payload")

            cached_path = remote_packages._store_cached_file(
                root,
                "example",
                source,
                "payload.bin",
                revision="rev1",
            )

            loaded = remote_packages._load_cached_file(
                root,
                "example",
                "payload.bin",
                expected_revision="rev1",
            )
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded[0], cached_path)

            with open(cached_path, "ab") as handle:
                handle.write(b"!")

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    "example",
                    "payload.bin",
                    expected_revision="rev1",
                )
            )

    def test_superwow_bundled_fallback_keeps_dll_and_superapi_paired(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool.addon_dependencies = {
            "SuperWoWhook.dll": "SuperAPI",
        }
        tool._valid_x86_dll = mock.Mock(return_value=False)
        tool._verified_bundled_file = mock.Mock()
        tool._verified_bundled_tree = mock.Mock()
        tool._warn_offline = mock.Mock()

        with tempfile.TemporaryDirectory() as root:
            payload = os.path.join(root, "Payload")
            addon = os.path.join(
                payload,
                "Interface",
                "Addons",
                "SuperAPI",
            )
            os.makedirs(addon)
            dll = os.path.join(payload, "SuperWoWhook.dll")
            with open(dll, "wb") as handle:
                handle.write(b"fallback")
            with open(os.path.join(addon, "SuperAPI.toc"), "w", encoding="utf-8") as handle:
                handle.write("## Interface: 11200\n")

            target = os.path.join(root, "game")
            os.makedirs(target)
            tool._verified_bundled_file.return_value = (dll, "a" * 64)
            tool._verified_bundled_tree.return_value = addon

            with mock.patch.object(
                remote_packages,
                "_transactional_replace_bundle",
            ) as transaction:
                tool._fallback_core_dll(
                    payload,
                    target,
                    "SuperWoWhook.dll",
                    RuntimeError("offline"),
                )

            transaction.assert_called_once()
            items = transaction.call_args.args[0]
            self.assertEqual([item[0] for item in items], ["file", "dir"])
            self.assertEqual(os.path.basename(items[0][2]), "SuperWoWhook.dll")
            self.assertEqual(os.path.basename(items[1][2]), "SuperAPI")
            tool._verified_bundled_file.assert_called_once_with(
                "Payload/SuperWoWhook.dll",
                "SuperWoWhook.dll fallback",
            )

    def test_cached_wowpresence_can_install_without_online_release(self):
        with tempfile.TemporaryDirectory() as root:
            package = os.path.join(root, "WowPresence.zip")
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("WowPresence.dll", b"dummy-dll")
                archive.writestr("WowPresence.exe", b"dummy-exe")

            remote_packages._store_cached_file(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                package,
                "WowPresence.zip",
                revision="v1.3",
            )

            with (
                mock.patch.object(remote_packages, "_verify_x86_pe"),
                mock.patch.object(
                    remote_packages,
                    "_install_managed_files_transactional",
                ) as install,
                mock.patch.object(
                    remote_packages,
                    "_set_managed_manifest_values",
                ),
            ):
                revision = remote_packages.install_cached_wowpresence(root)

            self.assertEqual(revision, "v1.3")
            install.assert_called_once()
            mappings = install.call_args.args[2]
            self.assertEqual(
                sorted(relative for _, relative in mappings),
                ["WowPresence.dll", "WowPresence.exe"],
            )

    def test_cache_metadata_wrong_type_is_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = remote_packages._package_cache_dir(root, "example")
            os.makedirs(cache_dir)
            with open(os.path.join(cache_dir, "metadata.json"), "w", encoding="utf-8") as handle:
                json.dump([], handle)

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    "example",
                    "payload.bin",
                )
            )

    def test_cache_metadata_cannot_escape_cache_directory(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = remote_packages._package_cache_dir(root, "example")
            os.makedirs(cache_dir)
            outside = os.path.join(root, "outside.bin")
            with open(outside, "wb") as handle:
                handle.write(b"outside")
            with open(os.path.join(cache_dir, "metadata.json"), "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "filename": "../outside.bin",
                        "size": os.path.getsize(outside),
                        "sha256": hashlib.sha256(b"outside").hexdigest(),
                        "revision": "rev1",
                    },
                    handle,
                )

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    "example",
                )
            )

    def test_visual_mpq_cache_cleanup_does_not_touch_installed_file(self):
        with tempfile.TemporaryDirectory() as root:
            cache_dir = remote_packages._package_cache_dir(
                root,
                "visual_example",
            )
            os.makedirs(cache_dir)
            with open(os.path.join(cache_dir, "payload.mpq"), "wb") as handle:
                handle.write(b"MPQcached")

            installed = os.path.join(root, "Data", "patch-X.mpq")
            os.makedirs(os.path.dirname(installed))
            with open(installed, "wb") as handle:
                handle.write(b"MPQinstalled")

            remote_packages.remove_package_cache(root, "visual_example")

            self.assertFalse(os.path.exists(cache_dir))
            self.assertTrue(os.path.isfile(installed))

    def test_managed_mpq_usable_rejects_corrupt_file(self):
        with tempfile.TemporaryDirectory() as root:
            relative = os.path.join("Data", "patch-X.mpq")
            target = os.path.join(root, relative)
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as handle:
                handle.write(b"not-an-mpq")

            remote_packages._write_managed_manifest(
                root,
                "visual_example",
                [relative],
                revision="1",
            )

            self.assertFalse(
                remote_packages.managed_mpq_is_usable(
                    root,
                    "visual_example",
                )
            )

            with open(target, "wb") as handle:
                handle.write(b"MPQvalid")

            self.assertTrue(
                remote_packages.managed_mpq_is_usable(
                    root,
                    "visual_example",
                )
            )

    def test_remote_mpq_has_no_offline_fallback(self):
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(
                remote_packages,
                "_download",
                side_effect=urllib.error.URLError("offline"),
            ):
                with self.assertRaises(remote_packages.RemoteSourceUnavailable):
                    remote_packages._install_remote_mpq(
                        root,
                        "visual_example",
                        "https://example.invalid/visual.mpq",
                        os.path.join("Data", "patch-X.mpq"),
                        revision="1",
                    )

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    "visual_example",
                    "payload.mpq",
                )
            )

    def test_remote_mpq_local_install_error_is_not_source_failure(self):
        with tempfile.TemporaryDirectory() as root:
            downloaded = os.path.join(root, "downloaded.mpq")
            with open(downloaded, "wb") as handle:
                handle.write(b"MPQvalid")

            with (
                mock.patch.object(
                    remote_packages,
                    "_download",
                    return_value=downloaded,
                ),
                mock.patch.object(
                    remote_packages,
                    "_install_managed_files",
                    side_effect=OSError("file locked"),
                ),
            ):
                with self.assertRaises(OSError):
                    remote_packages._install_remote_mpq(
                        root,
                        "visual_example",
                        "https://example.invalid/visual.mpq",
                        os.path.join("Data", "patch-X.mpq"),
                        revision="1",
                    )

    def test_remote_mpq_invalid_download_is_source_failure(self):
        with tempfile.TemporaryDirectory() as root:
            downloaded = os.path.join(root, "downloaded.mpq")
            with open(downloaded, "wb") as handle:
                handle.write(b"not-an-mpq")

            with mock.patch.object(
                remote_packages,
                "_download",
                return_value=downloaded,
            ):
                with self.assertRaises(remote_packages.RemoteSourceUnavailable):
                    remote_packages._install_remote_mpq(
                        root,
                        "visual_example",
                        "https://example.invalid/visual.mpq",
                        os.path.join("Data", "patch-X.mpq"),
                        revision="1",
                    )

    def test_pink_herbs_keeps_valid_installed_revision_when_update_download_fails(self):
        with tempfile.TemporaryDirectory() as root:
            relative = os.path.join("Data", "patch-V.mpq")
            target = os.path.join(root, relative)
            os.makedirs(os.path.dirname(target))
            with open(target, "wb") as handle:
                handle.write(b"MPQinstalled-old")

            remote_packages._record_package_state(
                root,
                "visual_pink_herbs",
                "oldrev123",
                [relative],
            )

            with (
                mock.patch.object(
                    remote_packages,
                    "_branch_head_sha",
                    return_value="newrev456",
                ),
                mock.patch.object(
                    remote_packages,
                    "_download",
                    side_effect=urllib.error.URLError("offline"),
                ),
                mock.patch.object(
                    remote_packages,
                    "_install_managed_files",
                ) as install,
            ):
                result = remote_packages.install_pink_herbs(root)

            install.assert_not_called()
            self.assertIn("oldrev1", result)
            with open(target, "rb") as handle:
                self.assertEqual(handle.read(), b"MPQinstalled-old")

    def test_installed_wowpresence_can_seed_offline_cache(self):
        with tempfile.TemporaryDirectory() as root:
            hashes = {}
            for filename in ("WowPresence.dll", "WowPresence.exe"):
                path = os.path.join(root, filename)
                with open(path, "wb") as handle:
                    handle.write(filename.encode("ascii"))
                hashes[filename] = remote_packages._file_sha256(path)

            remote_packages._write_managed_manifest(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                ["WowPresence.dll", "WowPresence.exe"],
                revision="v1.3",
            )
            remote_packages._set_managed_manifest_values(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                file_sha256=hashes,
            )

            with mock.patch.object(remote_packages, "_verify_x86_pe"):
                self.assertTrue(
                    remote_packages.cache_installed_wowpresence(
                        root,
                        revision="v1.3",
                    )
                )

            cached = remote_packages._load_cached_file(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                "WowPresence.zip",
                expected_revision="v1.3",
            )
            self.assertIsNotNone(cached)

    def test_manual_wowpresence_is_not_promoted_to_validated_cache(self):
        with tempfile.TemporaryDirectory() as root:
            for filename in ("WowPresence.dll", "WowPresence.exe"):
                with open(os.path.join(root, filename), "wb") as handle:
                    handle.write(filename.encode("ascii"))

            with mock.patch.object(remote_packages, "_verify_x86_pe"):
                self.assertFalse(
                    remote_packages.cache_installed_wowpresence(
                        root,
                        revision="v1.3",
                    )
                )

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    remote_packages.WOWPRESENCE_MANAGED_ID,
                    "WowPresence.zip",
                )
            )

    def test_modified_managed_wowpresence_is_not_cached(self):
        with tempfile.TemporaryDirectory() as root:
            hashes = {}
            for filename in ("WowPresence.dll", "WowPresence.exe"):
                path = os.path.join(root, filename)
                with open(path, "wb") as handle:
                    handle.write(filename.encode("ascii"))
                hashes[filename] = remote_packages._file_sha256(path)

            remote_packages._write_managed_manifest(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                ["WowPresence.dll", "WowPresence.exe"],
                revision="v1.3",
            )
            remote_packages._set_managed_manifest_values(
                root,
                remote_packages.WOWPRESENCE_MANAGED_ID,
                file_sha256=hashes,
            )

            with open(os.path.join(root, "WowPresence.dll"), "ab") as handle:
                handle.write(b"modified")

            with mock.patch.object(remote_packages, "_verify_x86_pe"):
                self.assertFalse(
                    remote_packages.cache_installed_wowpresence(root)
                )

            self.assertIsNone(
                remote_packages._load_cached_file(
                    root,
                    remote_packages.WOWPRESENCE_MANAGED_ID,
                    "WowPresence.zip",
                )
            )

    def test_superapi_bundled_tree_rejects_tampering(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)

        with tempfile.TemporaryDirectory() as root:
            fallback = os.path.join(root, "Payload", "Fallback")
            addon = os.path.join(root, "Payload", "Interface", "Addons", "SuperAPI")
            os.makedirs(fallback)
            os.makedirs(addon)

            first = os.path.join(addon, "SuperAPI.toc")
            second = os.path.join(addon, "SuperAPI.lua")
            with open(first, "wb") as handle:
                handle.write(b"## Interface: 11200\nSuperAPI.lua\n")
            with open(second, "wb") as handle:
                handle.write(b"print('ok')\n")

            records = []
            for path in (first, second):
                relative = os.path.relpath(path, root).replace(os.sep, "/")
                records.append(
                    {
                        "path": relative,
                        "size": os.path.getsize(path),
                        "git_blob_sha1": remote_packages._git_blob_sha1(path),
                    }
                )

            with open(
                os.path.join(fallback, "versions.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    {
                        "components": {
                            "test tree": {
                                "superapi_files": records,
                            }
                        }
                    },
                    handle,
                )

            with mock.patch("setup_tool_dynamic.get_base_path", return_value=root):
                verified = tool._verified_bundled_tree(
                    "test tree",
                    "superapi_files",
                    "Payload/Interface/Addons/SuperAPI",
                    "test SuperAPI",
                )
                self.assertEqual(verified, addon)

                with open(second, "ab") as handle:
                    handle.write(b"tampered")

                with self.assertRaises(RuntimeError):
                    tool._verified_bundled_tree(
                        "test tree",
                        "superapi_files",
                        "Payload/Interface/Addons/SuperAPI",
                        "test SuperAPI",
                    )

    def test_real_superwow_superapi_fallback_matches_manifest(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)

        dll_path, _ = tool._verified_bundled_file(
            "Payload/SuperWoWhook.dll",
            "SuperWoW fallback",
        )
        self.assertTrue(os.path.isfile(dll_path))

        addon_path = tool._verified_bundled_tree(
            "SuperWoW fallback",
            "superapi_files",
            "Payload/Interface/Addons/SuperAPI",
            "SuperAPI fallback",
        )
        self.assertTrue(
            tool._valid_superapi_addon(addon_path)
        )

    def test_superapi_existing_folder_must_be_complete(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)

        with tempfile.TemporaryDirectory() as addon:
            self.assertFalse(tool._valid_superapi_addon(addon))

            with open(os.path.join(addon, "SuperAPI.lua"), "w", encoding="utf-8") as handle:
                handle.write("-- test\n")
            with open(os.path.join(addon, "SuperAPIOptions.lua"), "w", encoding="utf-8") as handle:
                handle.write("-- test\n")
            with open(os.path.join(addon, "SuperAPI.toc"), "w", encoding="utf-8") as handle:
                handle.write("SuperAPI.lua\nlibs\\Needed.lua\n")

            self.assertFalse(tool._valid_superapi_addon(addon))

            os.makedirs(os.path.join(addon, "libs"))
            with open(os.path.join(addon, "libs", "Needed.lua"), "w", encoding="utf-8") as handle:
                handle.write("-- lib\n")

            self.assertTrue(tool._valid_superapi_addon(addon))

    def test_bundled_wowpresence_can_install_without_cache(self):
        with tempfile.TemporaryDirectory() as runtime_root, tempfile.TemporaryDirectory() as game:
            fallback_dir = os.path.join(
                runtime_root,
                "Payload",
                "Fallback",
                "Remote",
                remote_packages.WOWPRESENCE_MANAGED_ID,
            )
            os.makedirs(fallback_dir)
            package = os.path.join(fallback_dir, "WowPresence.zip")
            with zipfile.ZipFile(package, "w") as archive:
                archive.writestr("WowPresence.dll", b"dummy-dll")
                archive.writestr("WowPresence.exe", b"dummy-exe")

            manifest_path = os.path.join(
                runtime_root,
                "Payload",
                "Fallback",
                "remote_fallbacks.json",
            )
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "fallbacks": {
                            remote_packages.WOWPRESENCE_MANAGED_ID: {
                                "filename": "WowPresence.zip",
                                "revision": "v1.3",
                                "size": os.path.getsize(package),
                                "sha256": remote_packages._file_sha256(package),
                            }
                        }
                    },
                    handle,
                )

            with (
                mock.patch.object(
                    remote_packages,
                    "_runtime_base_path",
                    return_value=runtime_root,
                ),
                mock.patch.object(remote_packages, "_verify_x86_pe"),
                mock.patch.object(
                    remote_packages,
                    "_install_managed_files_transactional",
                ) as install,
                mock.patch.object(
                    remote_packages,
                    "_set_managed_manifest_values",
                ),
            ):
                revision = remote_packages.install_bundled_wowpresence(game)

            self.assertEqual(revision, "v1.3")
            install.assert_called_once()

    def test_branch_archive_download_can_be_pinned_to_resolved_revision(self):
        with (
            mock.patch.object(remote_packages, "_download", return_value="archive.zip") as download,
            mock.patch.object(remote_packages, "_branch_head_sha") as branch_head,
        ):
            result = remote_packages._download_github_branch_archive(
                "owner/repo",
                "main",
                revision="abc1234",
            )

        self.assertEqual(result, "archive.zip")
        branch_head.assert_not_called()
        self.assertEqual(
            download.call_args.args[0],
            "https://codeload.github.com/owner/repo/zip/abc1234",
        )


if __name__ == "__main__":
    unittest.main()
