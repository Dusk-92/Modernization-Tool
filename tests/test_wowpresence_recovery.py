import unittest
from unittest import mock

import remote_packages
from setup_tool_dynamic import ModernWowSetupTool


class WowPresenceRecoveryTests(unittest.TestCase):
    def _tool(self):
        tool = ModernWowSetupTool.__new__(ModernWowSetupTool)
        tool._report_download_progress = mock.Mock()
        tool._warn_offline = mock.Mock()
        tool._valid_x86_dll = mock.Mock(return_value=True)
        return tool

    def test_legacy_managed_wowpresence_is_repaired_offline(self):
        tool = self._tool()
        error = remote_packages.RemotePackageError("GitHub request failed: offline")

        with (
            mock.patch.object(
                remote_packages,
                "wowpresence_install_trust_state",
                return_value="managed_unverified",
            ),
            mock.patch.object(
                remote_packages,
                "install_cached_wowpresence",
            ) as cached,
            mock.patch.object(
                remote_packages,
                "install_bundled_wowpresence",
            ) as bundled,
            mock.patch.object(
                remote_packages,
                "ensure_wowpresence_config",
            ) as ensure_config,
            mock.patch.object(
                remote_packages,
                "cache_installed_wowpresence",
            ) as seed_cache,
        ):
            tool._recover_wowpresence_offline("C:/WoW", error)

        cached.assert_called_once_with(
            "C:/WoW",
            progress=tool._report_download_progress,
        )
        bundled.assert_not_called()
        ensure_config.assert_not_called()
        seed_cache.assert_not_called()
        tool._warn_offline.assert_called_once()

    def test_legacy_managed_state_is_marked_for_online_refresh(self):
        tool = self._tool()

        with (
            mock.patch.object(
                remote_packages,
                "wowpresence_install_trust_state",
                return_value="managed_unverified",
            ),
            mock.patch.object(
                remote_packages,
                "_set_managed_manifest_values",
            ) as update_manifest,
        ):
            state = tool._prepare_wowpresence_managed_state("C:/WoW")

        self.assertEqual(state, "managed_unverified")
        update_manifest.assert_called_once_with(
            "C:/WoW",
            remote_packages.WOWPRESENCE_MANAGED_ID,
            revision="__legacy_unverified__",
        )

    def test_unmanaged_wowpresence_is_not_marked_for_refresh(self):
        tool = self._tool()

        with (
            mock.patch.object(
                remote_packages,
                "wowpresence_install_trust_state",
                return_value="unmanaged",
            ),
            mock.patch.object(
                remote_packages,
                "_set_managed_manifest_values",
            ) as update_manifest,
        ):
            state = tool._prepare_wowpresence_managed_state("C:/WoW")

        self.assertEqual(state, "unmanaged")
        update_manifest.assert_not_called()

    def test_remote_wowpresence_failure_uses_offline_recovery(self):
        tool = self._tool()
        tool._prepare_wowpresence_managed_state = mock.Mock()
        tool._recover_wowpresence_offline = mock.Mock()
        error = remote_packages.RemotePackageError("GitHub request failed: offline")

        with mock.patch.object(
            remote_packages,
            "install_wowpresence",
            side_effect=error,
        ) as install:
            result = tool._install_wowpresence_with_fallback("C:/WoW")

        self.assertIsNone(result)
        tool._prepare_wowpresence_managed_state.assert_called_once_with("C:/WoW")
        install.assert_called_once_with(
            "C:/WoW",
            progress=tool._report_download_progress,
        )
        tool._recover_wowpresence_offline.assert_called_once_with("C:/WoW", error)

    def test_local_wowpresence_failure_is_not_hidden_by_fallback(self):
        tool = self._tool()
        tool._prepare_wowpresence_managed_state = mock.Mock()
        tool._recover_wowpresence_offline = mock.Mock()
        error = remote_packages.RemotePackageError(
            "Could not prepare C:/WoW/WowPresence.dll for replacement. Close WoW and try again."
        )

        with mock.patch.object(
            remote_packages,
            "install_wowpresence",
            side_effect=error,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "WowPresence installation failed locally",
            ):
                tool._install_wowpresence_with_fallback("C:/WoW")

        tool._recover_wowpresence_offline.assert_not_called()

    def test_wowpresence_source_failure_classifier_rejects_local_io(self):
        tool = self._tool()

        self.assertTrue(
            tool._wowpresence_source_failure(
                remote_packages.RemotePackageError("GitHub request failed: offline")
            )
        )
        self.assertTrue(
            tool._wowpresence_source_failure(
                remote_packages.RemotePackageError(
                    "SHA-256 mismatch for downloaded file (expected a, got b)."
                )
            )
        )
        self.assertTrue(
            tool._wowpresence_source_failure(
                remote_packages.RemotePackageError(
                    "WowPresence.dll is not a valid Windows PE binary (missing MZ header)."
                )
            )
        )
        self.assertFalse(
            tool._wowpresence_source_failure(
                remote_packages.RemotePackageError(
                    "Could not prepare C:/WoW/WowPresence.dll for replacement."
                )
            )
        )
        self.assertFalse(
            tool._wowpresence_source_failure(
                remote_packages.RemotePackageError(
                    "Could not validate WowPresence.dll: permission denied"
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
