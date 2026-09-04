import os
import struct
import tempfile
import unittest

from setup_tool import WowSetupTool
from setup_tool_dynamic import ModernWowSetupTool


class FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class VanillaTweaksNormalizationTests(unittest.TestCase):
    def _tool(self, *, fov, sound, quickloot, background):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool.vt_fov = FakeVar(fov)
        tool.vt_soundchan = FakeVar(sound)
        tool.vt_quickloot = FakeVar(quickloot)
        tool.vt_bg_sound = FakeVar(background)

        # Remaining values are required by the executable settings signature.
        tool.vt_farclip = FakeVar(777)
        tool.vt_frill = FakeVar(300)
        tool.vt_nameplate = FakeVar(41)
        tool.vt_maxcam = FakeVar(100)
        tool.vt_laa = FakeVar(True)
        tool.vt_cam_fix = FakeVar(True)
        tool.vt_crossfaction_res = FakeVar(False)
        tool.vt_custom_glues = FakeVar(True)
        tool.vt_bluemoon = FakeVar(False)
        tool.core_plugins = {"SuperWoWhook.dll": FakeVar(True)}
        return tool

    def _write_exe(self, root, quick1, quick2, background, fov, sound):
        data = bytearray(0x435D3C + 16)
        data[0x0C1ECF:0x0C1ED1] = quick1
        data[0x0C2B25:0x0C2B27] = quick2
        data[0x3A4869] = background
        data[0x4089B4:0x4089B8] = struct.pack("<f", fov)
        data[0x435D38:0x435D3C] = sound
        path = os.path.join(root, "WoW_Modernized.exe")
        with open(path, "wb") as handle:
            handle.write(data)
        return path

    def test_disabled_selections_restore_inherited_patches(self):
        tool = self._tool(
            fov=1.5708,
            sound=12,
            quickloot=False,
            background=False,
        )

        with tempfile.TemporaryDirectory() as root:
            path = self._write_exe(
                root,
                b"\x75\x10",
                b"\x75\x0B",
                0x27,
                1.919862,
                b"64\x00\x00",
            )
            tool._normalize_selected_vanilla_tweaks_output(path)
            with open(path, "rb") as handle:
                result = handle.read()

        self.assertEqual(result[0x0C1ECF:0x0C1ED1], b"\x74\x10")
        self.assertEqual(result[0x0C2B25:0x0C2B27], b"\x74\x0B")
        self.assertEqual(result[0x3A4869], 0x14)
        self.assertAlmostEqual(
            struct.unpack("<f", result[0x4089B4:0x4089B8])[0],
            1.5708,
            places=4,
        )
        self.assertEqual(result[0x435D38:0x435D3C], b"12\x00\x00")

    def test_enabled_selections_override_vanilla_or_nop_input(self):
        tool = self._tool(
            fov=1.9199,
            sound=64,
            quickloot=True,
            background=True,
        )

        with tempfile.TemporaryDirectory() as root:
            path = self._write_exe(
                root,
                b"\x90\x90",
                b"\x90\x90",
                0x14,
                1.5708,
                b"12\x00\x00",
            )
            tool._normalize_selected_vanilla_tweaks_output(path)
            with open(path, "rb") as handle:
                result = handle.read()

        self.assertEqual(result[0x0C1ECF:0x0C1ED1], b"\x75\x10")
        self.assertEqual(result[0x0C2B25:0x0C2B27], b"\x75\x0B")
        self.assertEqual(result[0x3A4869], 0x27)
        self.assertAlmostEqual(
            struct.unpack("<f", result[0x4089B4:0x4089B8])[0],
            1.9199,
            places=4,
        )
        self.assertEqual(result[0x435D38:0x435D3C], b"64\x00\x00")

    def test_unknown_quickloot_bytes_fail_safe(self):
        tool = self._tool(
            fov=1.9199,
            sound=64,
            quickloot=True,
            background=True,
        )

        with tempfile.TemporaryDirectory() as root:
            path = self._write_exe(
                root,
                b"\xEB\x10",
                b"\x74\x0B",
                0x14,
                1.5708,
                b"12\x00\x00",
            )
            with self.assertRaisesRegex(RuntimeError, "Unexpected QuickLoot bytes"):
                tool._normalize_selected_vanilla_tweaks_output(path)

    def test_normalization_policy_forces_one_marker_refresh(self):
        tool = self._tool(
            fov=1.9199,
            sound=64,
            quickloot=True,
            background=True,
        )

        old_signature = WowSetupTool._vanilla_tweaks_signature(tool)
        new_signature = tool._vanilla_tweaks_signature()

        self.assertNotIn("selected_patch_normalization", old_signature)
        self.assertEqual(new_signature["selected_patch_normalization"], 1)

        tool.core_plugins["SuperWoWhook.dll"].set(False)
        self.assertEqual(new_signature, tool._vanilla_tweaks_signature())


if __name__ == "__main__":
    unittest.main()
