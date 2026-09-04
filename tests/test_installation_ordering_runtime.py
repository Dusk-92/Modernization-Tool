import os
import tempfile
import unittest
from unittest import mock

import setup_tool_dynamic as dynamic


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _Root:
    def configure(self, **_kwargs):
        return None

    def update_idletasks(self):
        return None


def _make_runtime_tool(target, events):
    """Create the minimum state needed to execute the real base run_installation."""
    tool = object.__new__(dynamic.ModernWowSetupTool)
    tool._install_in_progress = False
    tool.wow_dir = _Var(target)
    tool.root = _Root()
    tool._close_download_progress = lambda: None

    tool.validate_installation_dir = lambda value: (
        events.append(("validate_directory", value)) or True
    )
    tool.validate_limits = lambda: (
        events.append(("validate_limits", target)) or True
    )
    tool.validate_plugin_conflicts = lambda: (
        events.append(("preflight", target)) or True
    )

    def record_target(name):
        return lambda value: events.append((name, value))

    tool.copy_base_files = record_target("copy_base_files")
    tool.configure_dxvk = record_target("configure_dxvk")
    tool.configure_plugins = record_target("configure_plugins")
    tool.configure_autologin_encryption = lambda: events.append(
        ("configure_autologin_encryption", target)
    )
    tool.configure_visual_audio = record_target("configure_visual_audio")
    tool.configure_script_memory = record_target("configure_script_memory")
    tool.configure_wdb_cache = record_target("configure_wdb_cache")
    tool.apply_process_mitigations = record_target("apply_process_mitigations")
    tool.create_launcher_shortcut = record_target("create_launcher_shortcut")
    tool.cleanup_legacy_outputs = record_target("cleanup_legacy_outputs")
    tool.save_settings = record_target("save_settings")
    return tool


class RealInstallationOrderingTests(unittest.TestCase):
    def test_real_installation_runs_vanilla_tweaks_once_before_every_write(self):
        events = []

        with tempfile.TemporaryDirectory() as target:
            initial_entries = set(os.listdir(target))
            tool = _make_runtime_tool(target, events)

            def fake_clean(_instance, value):
                events.append(("clean_unselected_files", value))

            def fake_vanilla_tweaks(_instance, value):
                events.append(("vanilla_tweaks", value))
                return os.path.join(value, "WoW_Modernized.exe")

            with mock.patch.object(
                dynamic._ModernWowSetupToolCore,
                "clean_unselected_files",
                fake_clean,
                create=True,
            ), mock.patch.object(
                dynamic._ModernWowSetupToolCore,
                "run_vanilla_tweaks",
                fake_vanilla_tweaks,
                create=True,
            ), mock.patch(
                "setup_tool.messagebox.showinfo"
            ) as showinfo, mock.patch(
                "setup_tool.messagebox.showerror"
            ) as showerror:
                self.assertIsNone(tool.run_installation())

                self.assertEqual(
                    events,
                    [
                        ("validate_directory", target),
                        ("validate_limits", target),
                        ("preflight", target),
                        ("vanilla_tweaks", target),
                        ("clean_unselected_files", target),
                        ("copy_base_files", target),
                        ("configure_dxvk", target),
                        ("configure_plugins", target),
                        ("configure_autologin_encryption", target),
                        ("configure_visual_audio", target),
                        ("configure_script_memory", target),
                        ("configure_wdb_cache", target),
                        ("apply_process_mitigations", target),
                        ("create_launcher_shortcut", target),
                        ("cleanup_legacy_outputs", target),
                        ("save_settings", target),
                    ],
                )
                showinfo.assert_called_once()
                showerror.assert_not_called()

                # run_installation installs temporary instance wrappers. They
                # must be gone when Apply returns so a later Apply starts clean.
                self.assertNotIn("clean_unselected_files", tool.__dict__)
                self.assertNotIn("run_vanilla_tweaks", tool.__dict__)
                self.assertIs(tool.clean_unselected_files.__func__, fake_clean)
                self.assertIs(tool.run_vanilla_tweaks.__func__, fake_vanilla_tweaks)

            # All real mutators above were replaced with record-only callbacks.
            # Any newly-added direct filesystem write in run_installation would
            # make this integration-style test visibly change the temp folder.
            self.assertEqual(set(os.listdir(target)), initial_entries)
            self.assertFalse(tool._install_in_progress)

    def test_real_installation_vanilla_tweaks_failure_blocks_all_writes(self):
        events = []

        with tempfile.TemporaryDirectory() as target:
            initial_entries = set(os.listdir(target))
            tool = _make_runtime_tool(target, events)

            def fake_clean(_instance, value):
                events.append(("clean_unselected_files", value))

            def failing_vanilla_tweaks(_instance, value):
                events.append(("vanilla_tweaks_failed", value))
                raise RuntimeError("patcher failed before install writes")

            with mock.patch.object(
                dynamic._ModernWowSetupToolCore,
                "clean_unselected_files",
                fake_clean,
                create=True,
            ), mock.patch.object(
                dynamic._ModernWowSetupToolCore,
                "run_vanilla_tweaks",
                failing_vanilla_tweaks,
                create=True,
            ), mock.patch(
                "setup_tool.messagebox.showinfo"
            ) as showinfo, mock.patch(
                "setup_tool.messagebox.showerror"
            ) as showerror:
                self.assertIsNone(tool.run_installation())

                self.assertEqual(
                    events,
                    [
                        ("validate_directory", target),
                        ("validate_limits", target),
                        ("preflight", target),
                        ("vanilla_tweaks_failed", target),
                    ],
                )
                showinfo.assert_not_called()
                showerror.assert_called_once()
                self.assertEqual(showerror.call_args.args[0], "Installation Error")
                self.assertIn(
                    "patcher failed before install writes",
                    showerror.call_args.args[1],
                )

                # The temporary wrappers must also be restored on the error path.
                self.assertNotIn("clean_unselected_files", tool.__dict__)
                self.assertNotIn("run_vanilla_tweaks", tool.__dict__)
                self.assertIs(tool.clean_unselected_files.__func__, fake_clean)
                self.assertIs(
                    tool.run_vanilla_tweaks.__func__,
                    failing_vanilla_tweaks,
                )

            self.assertEqual(set(os.listdir(target)), initial_entries)
            self.assertFalse(tool._install_in_progress)


if __name__ == "__main__":
    unittest.main()
