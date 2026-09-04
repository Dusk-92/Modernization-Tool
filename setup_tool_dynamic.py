import math
import os
import struct
import sys
import tkinter as tk
import types

import setup_tool_dynamic_core as _dynamic_core
# Keep the feature-branch implementation intact and layer only the executable
# normalization policy here. This makes the B-total policy easy to audit and
# keeps every unrelated remote/fallback behavior byte-for-byte unchanged.
from setup_tool_dynamic_core import *  # noqa: F401,F403
from setup_tool_dynamic_core import ModernWowSetupTool as _ModernWowSetupToolCore


_CAMERA_REGIONS = (
    (
        0x02CCD0,
        bytes.fromhex(
            "55 8b ec 83 ec 10 8d 45 f0 50 33 c9 e8 4f 8f 00 "
            "00 50 ff 15 64 f6 7f 00 8b 45 f8 99 2b c2 8b c8 "
            "8b 45 fc 99 2b c2 d1 f8 d1 f9 50 51 89 0d 38 4e "
            "88 00 a3 3c 4e 88 00 ff 15 5c f6 7f 00 8b e5 5d "
            "c3 90 90"
        ),
        bytes.fromhex(
            "55 8b 05 48 4e 88 00 8b 0d 44 4e 88 00 e9 33 90 "
            "32 00 83 c0 32 83 c1 32 3b 0d a8 eb c4 00 7e 03 "
            "83 e9 01 3b 05 ac eb c4 00 7e 03 83 e8 01 83 e9 "
            "32 83 e8 32 89 05 48 4e 88 00 89 0d 44 4e 88 00 "
            "5d eb 0d"
        ),
    ),
    (
        0x02D326,
        bytes.fromhex("8b 45 f0 8b 15"),
        bytes.fromhex("e9 b1 8a 32 00"),
    ),
    (
        0x02D334,
        bytes.fromhex("8b 35 3c 4e 88 00"),
        bytes.fromhex("8b 35 48 4e 88 00"),
    ),
    (
        0x355D15,
        bytes.fromhex(
            "cc cc cc cc cc cc cc cc cc cc cc cc cc cc cc cc "
            "cc cc cc cc cc"
        ),
        bytes.fromhex(
            "83 f8 32 7d 03 83 c0 01 83 f9 32 7d 03 83 c1 01 "
            "e9 b8 6f cd ff"
        ),
    ),
    (
        0x355DDC,
        bytes.fromhex(
            "cc cc cc cc cc cc cc cc cc cc cc cc cc cc cc cc "
            "cc cc cc cc cc cc cc cc cc cc cc cc cc cc"
        ),
        bytes.fromhex(
            "8d 4d f0 51 ff 35 00 4e 88 00 ff 15 50 f6 7f 00 "
            "8b 45 f0 8b 15 44 4e 88 00 e9 35 75 cd ff"
        ),
    ),
)

_CUSTOM_GLUES_SITES = (
    (0x2F113A, 0x5F, 0xEB),
    (0x2F113B, 0x5E, 0x19),
    (0x2F1158, 0x01, 0x03),
    (0x2F11A7, 0x01, 0x03),
    (0x2F11F0, 0x5F, 0xEB),
    (0x2F11F1, 0x5E, 0xB2),
)


class ModernWowSetupTool(_ModernWowSetupToolCore):
    """Remote-fallback tool with authoritative, fail-safe Vanilla Tweaks output."""

    def _vanilla_tweaks_signature(self):
        signature = super()._vanilla_tweaks_signature()
        # v2 expands normalization from the original selected subset to every
        # executable tweak exposed by the Tool except the two intentionally
        # legacy upstream-only patches (Blue Moon and Cross-faction Res).
        signature["selected_patch_normalization"] = 2
        return signature

    @staticmethod
    def _validate_float_field(data, offset, label, minimum, maximum):
        current = struct.unpack_from("<f", data, offset)[0]
        if not math.isfinite(current) or not minimum <= current <= maximum:
            raise RuntimeError(
                f"Unexpected {label} value at 0x{offset:X}; "
                "refusing to alter an unknown client."
            )

    def _normalize_selected_vanilla_tweaks_output(self, output_exe):
        """Make Tool-owned executable tweaks authoritative on pre-patched clients.

        Blue Moon and Cross-faction Resurrection deliberately keep the previous
        vanilla-tweaks behavior because their complete pristine restoration
        signatures are not part of this policy.
        """
        try:
            with open(output_exe, "rb") as handle:
                data = bytearray(handle.read())
        except OSError as exc:
            raise RuntimeError(
                "Could not inspect WoW_Modernized.exe for Vanilla Tweaks normalization."
            ) from exc

        required_size = 0x46795C
        if len(data) < required_size:
            raise RuntimeError(
                "WoW_Modernized.exe is too small for Vanilla Tweaks normalization."
            )

        # Validate all code-patch signatures before changing anything. Scalar
        # fields below are data constants, so they are validated by type/range
        # rather than by one exact preset value.
        quickloot_sites = (
            (0x0C1ECF, 0x10),
            (0x0C2B25, 0x0B),
        )
        for offset, displacement in quickloot_sites:
            current = bytes(data[offset:offset + 2])
            known = (
                bytes((0x74, displacement)),
                bytes((0x75, displacement)),
                b"\x90\x90",
            )
            if current not in known:
                raise RuntimeError(
                    f"Unexpected QuickLoot bytes at 0x{offset:X}; "
                    "refusing to alter an unknown client."
                )

        if data[0x3A4869] not in (0x14, 0x27):
            raise RuntimeError(
                "Unexpected Background Sound byte; refusing to alter an unknown client."
            )

        laa_current = bytes(data[0x126:0x128])
        if laa_current not in (b"\x0F\x01", b"\x2F\x01"):
            raise RuntimeError(
                "Unexpected Large Address Aware bytes; refusing to alter an unknown client."
            )

        for offset, original, patched in _CAMERA_REGIONS:
            current = bytes(data[offset:offset + len(original)])
            if current not in (original, patched):
                raise RuntimeError(
                    f"Unexpected Camera Skip Fix bytes at 0x{offset:X}; "
                    "refusing to alter an unknown client."
                )

        custom_state = tuple(data[offset] for offset, _original, _patched in _CUSTOM_GLUES_SITES)
        custom_original = tuple(original for _offset, original, _patched in _CUSTOM_GLUES_SITES)
        custom_patched = tuple(patched for _offset, _original, patched in _CUSTOM_GLUES_SITES)
        if custom_state not in (custom_original, custom_patched):
            raise RuntimeError(
                "Unexpected Custom GlueXML bytes; refusing to alter an unknown client."
            )

        self._validate_float_field(data, 0x4089B4, "FoV", 0.5, 3.5)
        self._validate_float_field(data, 0x40FED8, "Farclip", 100.0, 50000.0)
        self._validate_float_field(data, 0x467958, "Frill Distance", 0.0, 10000.0)
        self._validate_float_field(data, 0x40C448, "Nameplate Distance", 1.0, 500.0)
        self._validate_float_field(data, 0x4089A4, "Max Camera Distance", 1.0, 1000.0)

        sound_field = bytes(data[0x435D38:0x435D3C])
        sound_text, separator, sound_tail = sound_field.partition(b"\x00")
        if (
            not separator
            or not sound_text.isdigit()
            or any(sound_tail)
            or not 1 <= int(sound_text) <= 256
        ):
            raise RuntimeError(
                "Unexpected Sound Channels field; refusing to alter an unknown client."
            )

        desired_fov = float(self.vt_fov.get())
        desired_farclip = float(self.vt_farclip.get())
        desired_frill = float(self.vt_frill.get())
        desired_nameplate = float(self.vt_nameplate.get())
        desired_maxcam = float(self.vt_maxcam.get())
        desired_sound = int(self.vt_soundchan.get())

        desired_values = (
            ("FoV", desired_fov, 0.5, 3.5),
            ("Farclip", desired_farclip, 100.0, 50000.0),
            ("Frill Distance", desired_frill, 0.0, 10000.0),
            ("Nameplate Distance", desired_nameplate, 1.0, 500.0),
            ("Max Camera Distance", desired_maxcam, 1.0, 1000.0),
        )
        for label, value, minimum, maximum in desired_values:
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise RuntimeError(f"{label} value is outside the supported WoW 1.12.1 range.")

        sound_channels = str(desired_sound).encode("ascii") + b"\x00"
        if not 1 <= desired_sound <= 256 or len(sound_channels) > 4:
            raise RuntimeError("Sound Channels value is outside the supported WoW 1.12.1 range.")

        # All validation passed. Apply the exact Tool selections in memory.
        desired_quickloot_opcode = 0x75 if self.vt_quickloot.get() else 0x74
        for offset, displacement in quickloot_sites:
            data[offset:offset + 2] = bytes(
                (desired_quickloot_opcode, displacement)
            )

        data[0x3A4869] = 0x27 if self.vt_bg_sound.get() else 0x14
        data[0x126:0x128] = b"\x2F\x01" if self.vt_laa.get() else b"\x0F\x01"

        desired_camera_patched = bool(self.vt_cam_fix.get())
        for offset, original, patched in _CAMERA_REGIONS:
            desired = patched if desired_camera_patched else original
            data[offset:offset + len(desired)] = desired

        desired_custom_patched = bool(self.vt_custom_glues.get())
        for offset, original, patched in _CUSTOM_GLUES_SITES:
            data[offset] = patched if desired_custom_patched else original

        struct.pack_into("<f", data, 0x4089B4, desired_fov)
        struct.pack_into("<f", data, 0x40FED8, desired_farclip)
        struct.pack_into("<f", data, 0x467958, desired_frill)
        struct.pack_into("<f", data, 0x40C448, desired_nameplate)
        struct.pack_into("<f", data, 0x4089A4, desired_maxcam)
        data[0x435D38:0x435D3C] = sound_channels.ljust(4, b"\x00")

        # Blue Moon (0x3E5B83) and Cross-faction Res (0x2067DE) are intentionally
        # not normalized here. vanilla-tweaks keeps exactly the previous behavior
        # for those two options.

        staged = output_exe + ".modernization-normalized"
        try:
            with open(staged, "wb") as handle:
                handle.write(data)
            os.replace(staged, output_exe)
        except OSError as exc:
            raise RuntimeError(
                "Could not write the normalized WoW_Modernized.exe."
            ) from exc
        finally:
            if os.path.exists(staged):
                try:
                    os.remove(staged)
                except OSError:
                    pass


class _DynamicModuleProxy(types.ModuleType):
    """Keep legacy module-level monkey patches visible to the preserved core."""

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name == "get_base_path":
            setattr(_dynamic_core, name, value)


# Existing tests and external callers historically patched
# setup_tool_dynamic.get_base_path. Preserve that behavior after splitting the
# untouched implementation into setup_tool_dynamic_core.py.
sys.modules[__name__].__class__ = _DynamicModuleProxy


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
