import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

import remote_packages
from setup_tool import WowSetupTool, ToolTip, get_base_path


class ModernWowSetupTool(WowSetupTool):
    """Feature-branch entry point adding live GitHub package updates."""

    def __init__(self, root):
        # Define these before WowSetupTool.__init__ because the parent constructor
        # calls self.build_ui(), which dispatches to our overridden Plugins tab.
        self.classicapi_enabled = tk.BooleanVar(master=root, value=False)
        self.auction_throttle_enabled = tk.BooleanVar(master=root, value=False)
        super().__init__(root)

    def _enforce_live_core_exclusivity(self, selected):
        """Keep ClassicAPI and AuctionQueryThrottle mutually exclusive."""
        if selected == "classicapi" and self.classicapi_enabled.get():
            self.auction_throttle_enabled.set(False)
        elif selected == "auction" and self.auction_throttle_enabled.get():
            self.classicapi_enabled.set(False)

    def build_plugins_tab(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.LabelFrame(container, text="Recommended Core")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ttk.Label(
            left_frame,
            text="These are highly recommended for performance\nand client stability.",
            font=("", 8, "italic"),
        ).pack(anchor="w", padx=10, pady=10)

        for dll, var in self.core_plugins.items():
            cb = ttk.Checkbutton(left_frame, text=dll, variable=var)
            cb.pack(anchor="w", padx=10, pady=4)
            ToolTip(cb, self.descriptions.get(dll, ""))

        cb_classicapi = ttk.Checkbutton(
            left_frame,
            text="ClassicAPI.dll",
            variable=self.classicapi_enabled,
            command=lambda: self._enforce_live_core_exclusivity("classicapi"),
        )
        cb_classicapi.pack(anchor="w", padx=10, pady=4)
        ToolTip(
            cb_classicapi,
            "Downloads and installs the latest stable ClassicAPI.dll release from "
            "brues-code/ClassicAPI when setup is applied. Mutually exclusive with "
            "AuctionQueryThrottle.dll.",
        )

        cb_auction = ttk.Checkbutton(
            left_frame,
            text="AuctionQueryThrottle.dll",
            variable=self.auction_throttle_enabled,
            command=lambda: self._enforce_live_core_exclusivity("auction"),
        )
        cb_auction.pack(anchor="w", padx=10, pady=4)
        ToolTip(
            cb_auction,
            "Downloads and installs the latest stable AuctionQueryThrottle.dll release "
            "from brues-code/AuctionQueryThrottle when setup is applied. Mutually "
            "exclusive with ClassicAPI.dll.",
        )

        right_frame = ttk.LabelFrame(container, text="Optional WeirdUtils")
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ttk.Label(
            right_frame,
            text="Additional quality-of-life adjustments.",
            font=("", 8, "italic"),
        ).pack(anchor="w", padx=10, pady=10)

        for dll, var in self.optional_plugins.items():
            cb = ttk.Checkbutton(right_frame, text=dll, variable=var)
            cb.pack(anchor="w", padx=10, pady=4)
            ToolTip(cb, self.descriptions.get(dll, ""))

    def _normalize_live_core_selection(self):
        """Safety net: never allow both mutually-exclusive live core DLLs."""
        if self.classicapi_enabled.get() and self.auction_throttle_enabled.get():
            # The UI callback prevents this during normal use. If state is ever
            # changed programmatically, prefer ClassicAPI and disable Auction.
            self.auction_throttle_enabled.set(False)

    def clean_unselected_files(self, target):
        super().clean_unselected_files(target)
        self._normalize_live_core_selection()

        managed = {
            "ClassicAPI.dll": self.classicapi_enabled,
            "AuctionQueryThrottle.dll": self.auction_throttle_enabled,
        }

        # Remove whichever live core DLL is not selected. This also guarantees
        # that switching from one to the other never leaves both in the WoW root.
        for filename, var in managed.items():
            if not var.get():
                path = os.path.join(target, filename)
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as exc:
                        raise RuntimeError(
                            f"Could not remove {filename}. Close WoW and any tool using the file, then try again."
                        ) from exc

    def _fallback_core_dll(self, payload_base, target, dll_name, error):
        source_dll = os.path.join(payload_base, dll_name)
        if not os.path.exists(source_dll):
            raise RuntimeError(
                f"Could not download the latest {dll_name}, and no bundled fallback exists.\n\n{error}"
            ) from error

        addon_folder = self.addon_dependencies.get(dll_name)
        source_addon = None
        if addon_folder:
            source_addon = os.path.join(payload_base, "Interface", "Addons", addon_folder)
            if not os.path.isdir(source_addon):
                raise RuntimeError(
                    f"Could not download the latest {dll_name}, and its bundled fallback addon "
                    f"{addon_folder} is missing.\n\n{error}"
                ) from error

        shutil.copy2(source_dll, target)

        if addon_folder and source_addon:
            remote_packages._replace_directory(
                source_addon,
                os.path.join(target, "Interface", "AddOns", addon_folder),
            )

        messagebox.showwarning(
            "Online update unavailable",
            f"Could not download the latest {dll_name}.\n\n"
            f"The bundled version will be used instead.\n\nDetails: {error}",
        )

    def configure_plugins(self, target):
        payload_base = os.path.join(get_base_path(), "Payload")
        payload_weirdu = os.path.join(payload_base, "WeirdUtils")

        self._normalize_live_core_selection()

        dlls_text_lines = []
        if self.gpu_type.get() != "AMD":
            dlls_text_lines.append("dxvk")

        # Core plugins. UnitXP and SuperWoW are refreshed from their upstream
        # sources every time setup is applied. Their bundled copies remain an
        # offline fallback so this feature does not reduce current reliability.
        for dll_name, var in self.core_plugins.items():
            if not var.get():
                continue

            if dll_name == "UnitXP_SP3.dll":
                try:
                    remote_packages.install_unitxp(target)
                except Exception as exc:
                    self._fallback_core_dll(payload_base, target, dll_name, exc)

            elif dll_name == "SuperWoWhook.dll":
                try:
                    remote_packages.install_superwow(target)
                except Exception as exc:
                    self._fallback_core_dll(payload_base, target, dll_name, exc)

            else:
                source_dll = os.path.join(payload_base, dll_name)
                if os.path.exists(source_dll):
                    shutil.copy2(source_dll, target)

            dlls_text_lines.append(dll_name)

        # Live core plugins. They are displayed in Recommended Core like the
        # bundled core DLLs, but are downloaded from their upstream releases.
        if self.classicapi_enabled.get():
            try:
                remote_packages.install_classicapi(target)
            except Exception as exc:
                raise RuntimeError(f"ClassicAPI update failed:\n{exc}") from exc
            dlls_text_lines.append("ClassicAPI.dll")

        elif self.auction_throttle_enabled.get():
            try:
                remote_packages.install_auction_query_throttle(target)
            except Exception as exc:
                raise RuntimeError(f"Auction Query Throttle update failed:\n{exc}") from exc
            dlls_text_lines.append("AuctionQueryThrottle.dll")

        # Clean dependent addons when the matching core DLL is disabled.
        for dll_name, addon_folder in self.addon_dependencies.items():
            core_var = self.core_plugins.get(dll_name)
            if core_var is not None and not core_var.get():
                addon_path = os.path.join(target, "Interface", "AddOns", addon_folder)
                if os.path.exists(addon_path):
                    shutil.rmtree(addon_path, ignore_errors=True)

        # Optional WeirdUtils.
        for dll_name, var in self.optional_plugins.items():
            if var.get():
                source_dll = os.path.join(payload_weirdu, dll_name)
                if os.path.exists(source_dll):
                    shutil.copy2(source_dll, target)
                dlls_text_lines.append(dll_name)

        with open(os.path.join(target, "dlls.txt"), "w") as f:
            f.write("\n".join(dlls_text_lines))


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
