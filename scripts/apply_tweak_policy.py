from pathlib import Path
import re


setup_path = Path("setup_tool.py")
text = setup_path.read_text(encoding="utf-8")

controls_pattern = re.compile(
    r"    def update_superwow_managed_controls\(self\):\n.*?"
    r"(?=    def build_tweaks_tab\(self, parent\):\n)",
    re.S,
)
controls_replacement = '''    def update_superwow_managed_controls(self):
        """Keep Vanilla Tweaks controls independent from SuperWoW."""
        if hasattr(self, "superwow_notice"):
            try:
                self.superwow_notice.pack_forget()
            except tk.TclError:
                pass

        if hasattr(self, "fov_ratio_combo"):
            self.fov_ratio_combo.configure(state="readonly")
        if hasattr(self, "fov_entry"):
            self.fov_entry.configure(state="normal")
        if hasattr(self, "sound_scale"):
            self.sound_scale.configure(state="normal")
        if hasattr(self, "sound_entry"):
            self.sound_entry.configure(state="normal")
        if hasattr(self, "cb_loot"):
            self.cb_loot.configure(state="normal")
        if hasattr(self, "cb_bg"):
            self.cb_bg.configure(state="normal")

'''
text, count = controls_pattern.subn(lambda _match: controls_replacement, text, count=1)
assert count == 1, f"controls replacement count={count}"

signature_pattern = re.compile(
    r"    def _vanilla_tweaks_signature\(self\):\n.*?"
    r"(?=    def run_vanilla_tweaks\(self, target, tweaks_exe=None, modern_cli=False\):\n)",
    re.S,
)
signature_replacement = '''    def _vanilla_tweaks_signature(self):
        """Return settings that change WoW_Modernized.exe patch output."""
        return {
            "fov": round(float(self.vt_fov.get()), 4),
            "farclip": int(self.vt_farclip.get()),
            "frill": int(self.vt_frill.get()),
            "nameplate": int(self.vt_nameplate.get()),
            "sound_channels": int(self.vt_soundchan.get()),
            "max_camera": int(self.vt_maxcam.get()),
            "quickloot": bool(self.vt_quickloot.get()),
            "background_sound": bool(self.vt_bg_sound.get()),
            "large_address_aware": bool(self.vt_laa.get()),
            "camera_fix": bool(self.vt_cam_fix.get()),
            "crossfaction_res": bool(self.vt_crossfaction_res.get()),
            "custom_glues": bool(self.vt_custom_glues.get()),
            "bluemoon": bool(self.vt_bluemoon.get()),
        }

'''
text, count = signature_pattern.subn(lambda _match: signature_replacement, text, count=1)
assert count == 1, f"signature replacement count={count}"

replacements = {
    "        superwow_active = self._superwow_enabled()\n": "",
    (
        "            # tubtubs/vanilla-tweaks keeps these four patches opt-in. When\n"
        "            # SuperWoW is active, deliberately leave them unpatched.\n"
        "            if not superwow_active and abs(self.vt_fov.get() - 1.5708) >= 0.0001:\n"
    ): (
        "            # tubtubs/vanilla-tweaks keeps these patches opt-in.\n"
        "            if abs(self.vt_fov.get() - 1.5708) >= 0.0001:\n"
    ),
    "            if not superwow_active and self.vt_soundchan.get() != 12:\n":
        "            if self.vt_soundchan.get() != 12:\n",
    "            if not superwow_active and self.vt_quickloot.get():\n":
        "            if self.vt_quickloot.get():\n",
    "            if not superwow_active and self.vt_bg_sound.get():\n":
        "            if self.vt_bg_sound.get():\n",
    (
        "            if superwow_active:\n"
        "                self._reset_superwow_managed_exe_patches(staged_output)\n\n"
    ): "",
}
for old, new in replacements.items():
    assert old in text, f"missing expected setup_tool block: {old!r}"
    text = text.replace(old, new, 1)

legacy_pattern = re.compile(
    r"        else:\n"
    r"            # Legacy bundled brndd patcher enables these older patches by\n"
    r"            # default, so explicitly disable all four when SuperWoW handles them\.\n"
    r"            if superwow_active:\n.*?"
    r"(?=\n            if self\.vt_farclip\.get\(\) == 777:)",
    re.S,
)
legacy_replacement = '''        else:
            # Legacy bundled brndd patcher kept only as an offline fallback.
            if abs(self.vt_fov.get() - 1.5708) < 0.0001:
                args.append("--no-fov")
            else:
                args.extend(["--fov", str(self.vt_fov.get())])

            if self.vt_soundchan.get() == 12:
                args.append("--no-soundchannels")
            else:
                args.extend(["--soundchannels", str(self.vt_soundchan.get())])

            if not self.vt_quickloot.get():
                args.append("--no-quickloot")
            if not self.vt_bg_sound.get():
                args.append("--no-sound-in-background")
'''
text, count = legacy_pattern.subn(lambda _match: legacy_replacement, text, count=1)
assert count == 1, f"legacy replacement count={count}"

setup_path.write_text(text, encoding="utf-8", newline="\n")


tests_path = Path("tests/test_safety.py")
tests_text = tests_path.read_text(encoding="utf-8")
tests_pattern = re.compile(
    r"    def test_superwow_reset_removes_inherited_vanilla_tweaks_patches\(self\):\n.*?"
    r"(?=    def test_vanilla_tweaks_skips_package_when_output_and_revision_match\(self\):\n)",
    re.S,
)
tests_replacement = '''    def test_superwow_does_not_change_vanilla_tweaks_signature(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.core_plugins = {"SuperWoWhook.dll": FakeVar(True)}
        tool.vt_fov = FakeVar(1.919862)
        tool.vt_farclip = FakeVar(3000)
        tool.vt_frill = FakeVar(300)
        tool.vt_nameplate = FakeVar(41)
        tool.vt_soundchan = FakeVar(64)
        tool.vt_maxcam = FakeVar(100)
        tool.vt_quickloot = FakeVar(True)
        tool.vt_bg_sound = FakeVar(True)
        tool.vt_laa = FakeVar(True)
        tool.vt_cam_fix = FakeVar(True)
        tool.vt_crossfaction_res = FakeVar(False)
        tool.vt_custom_glues = FakeVar(True)
        tool.vt_bluemoon = FakeVar(False)

        signature_with_superwow = tool._vanilla_tweaks_signature()
        tool.core_plugins["SuperWoWhook.dll"].set(False)
        signature_without_superwow = tool._vanilla_tweaks_signature()

        self.assertEqual(signature_with_superwow, signature_without_superwow)
        self.assertEqual(signature_with_superwow["fov"], 1.9199)
        self.assertEqual(signature_with_superwow["sound_channels"], 64)
        self.assertTrue(signature_with_superwow["quickloot"])
        self.assertTrue(signature_with_superwow["background_sound"])

    def test_superwow_keeps_vanilla_tweaks_controls_enabled(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.superwow_notice = mock.Mock()
        tool.fov_ratio_combo = mock.Mock()
        tool.fov_entry = mock.Mock()
        tool.sound_scale = mock.Mock()
        tool.sound_entry = mock.Mock()
        tool.cb_loot = mock.Mock()
        tool.cb_bg = mock.Mock()

        tool.update_superwow_managed_controls()

        tool.superwow_notice.pack_forget.assert_called_once()
        tool.fov_ratio_combo.configure.assert_called_once_with(state="readonly")
        tool.fov_entry.configure.assert_called_once_with(state="normal")
        tool.sound_scale.configure.assert_called_once_with(state="normal")
        tool.sound_entry.configure.assert_called_once_with(state="normal")
        tool.cb_loot.configure.assert_called_once_with(state="normal")
        tool.cb_bg.configure.assert_called_once_with(state="normal")

    def test_superwow_modern_cli_keeps_selected_fov_sound_loot_and_background(self):
        tool = WowSetupTool.__new__(WowSetupTool)
        tool.core_plugins = {"SuperWoWhook.dll": FakeVar(True)}
        tool.vt_fov = FakeVar(1.919862)
        tool.vt_farclip = FakeVar(777)
        tool.vt_frill = FakeVar(70)
        tool.vt_nameplate = FakeVar(20)
        tool.vt_soundchan = FakeVar(64)
        tool.vt_maxcam = FakeVar(50)
        tool.vt_quickloot = FakeVar(True)
        tool.vt_bg_sound = FakeVar(True)
        tool.vt_laa = FakeVar(True)
        tool.vt_cam_fix = FakeVar(True)
        tool.vt_crossfaction_res = FakeVar(False)
        tool.vt_custom_glues = FakeVar(True)
        tool.vt_bluemoon = FakeVar(False)
        tool._inspect_wow_executable = mock.Mock(return_value=(True, ""))

        captured = {}
        with tempfile.TemporaryDirectory() as root:
            wow = os.path.join(root, "WoW.exe")
            patcher = os.path.join(root, "vanilla-tweaks.exe")
            with open(wow, "wb") as handle:
                handle.write(b"MZ" + b"\\x00" * (2 * 1024 * 1024))
            with open(patcher, "wb") as handle:
                handle.write(b"patcher")

            def fake_run(args, check):
                captured["args"] = list(args)
                staged = args[args.index("-o") + 1]
                with open(staged, "wb") as handle:
                    handle.write(b"MZ" + b"\\x00" * (2 * 1024 * 1024))

            with mock.patch("setup_tool.subprocess.run", side_effect=fake_run):
                tool.run_vanilla_tweaks(root, tweaks_exe=patcher, modern_cli=True)

        args = captured["args"]
        self.assertIn("--fov", args)
        self.assertIn("--fov-patch", args)
        self.assertIn("--soundchannels", args)
        self.assertIn("--soundchannels-patch", args)
        self.assertIn("--quickloot", args)
        self.assertIn("--sound-in-background", args)

'''
tests_text, count = tests_pattern.subn(lambda _match: tests_replacement, tests_text, count=1)
assert count == 1, f"tests replacement count={count}"
tests_path.write_text(tests_text, encoding="utf-8", newline="\n")
