import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox

import remote_packages
from setup_tool import WowSetupTool, ToolTip, get_base_path


class ModernWowSetupTool(WowSetupTool):
    """Feature-branch entry point adding live GitHub package updates."""

    def __init__(self, root):
        # Define this before WowSetupTool.__init__ because the parent constructor
        # calls self.build_ui(), which dispatches to our overridden Plugins tab.
        self.client_tweak = tk.StringVar(master=root, value="none")
        super().__init__(root)

    def build_plugins_tab(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.Frame(container)
        top.pack(fill="both", expand=True)

        left_frame = ttk.LabelFrame(top, text="Recommended Core")
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

        right_frame = ttk.LabelFrame(top, text="Optional WeirdUtils")
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

        tweaks_frame = ttk.LabelFrame(container, text="Tweaks")
        tweaks_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(
            tweaks_frame,
            text="Choose one. ClassicAPI and Auction Query Throttle are mutually exclusive.",
            font=("", 8, "italic"),
        ).pack(anchor="w", padx=10, pady=(7, 3))

        choices = ttk.Frame(tweaks_frame)
        choices.pack(fill="x", padx=10, pady=(0, 8))

        rb_none = ttk.Radiobutton(
            choices, text="None", variable=self.client_tweak, value="none"
        )
        rb_none.pack(side="left", padx=(0, 16))

        rb_classicapi = ttk.Radiobutton(
            choices,
            text="ClassicAPI",
            variable=self.client_tweak,
            value="classicapi",
        )
        rb_classicapi.pack(side="left", padx=(0, 16))
        ToolTip(
            rb_classicapi,
            "Downloads and installs the latest stable ClassicAPI.dll release from "
            "brues-code/ClassicAPI when setup is applied.",
        )

        rb_auction = ttk.Radiobutton(
            choices,
            text="Auction Query Throttle",
            variable=self.client_tweak,
            value="auction",
        )
        rb_auction.pack(side="left")
        ToolTip(
            rb_auction,
            "Downloads and installs the latest stable AuctionQueryThrottle.dll release "
            "from brues-code/AuctionQueryThrottle when setup is applied.",
        )

    def clean_unselected_files(self, target):
        super().clean_unselected_files(target)

        choice = self.client_tweak.get()
        managed = {
            "classicapi": "ClassicAPI.dll",
            "auction": "AuctionQueryThrottle.dll",
        }

        # Always remove the non-selected alternative. Selecting None removes both.
        # A failed removal is fatal: silently leaving both DLLs behind would defeat
        # the mutual-exclusion guarantee.
        for key, filename in managed.items():
            if choice != key:
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

        # Mutually-exclusive live Tweaks.
        choice = self.client_tweak.get()
        if choice == "classicapi":
            try:
                remote_packages.install_classicapi(target)
            except Exception as exc:
                raise RuntimeError(f"ClassicAPI update failed:\n{exc}") from exc
            dlls_text_lines.append("ClassicAPI.dll")

        elif choice == "auction":
            try:
                remote_packages.install_auction_query_throttle(target)
            except Exception as exc:
                raise RuntimeError(f"Auction Query Throttle update failed:\n{exc}") from exc
            dlls_text_lines.append("AuctionQueryThrottle.dll")

        with open(os.path.join(target, "dlls.txt"), "w") as f:
            f.write("\n".join(dlls_text_lines))


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
