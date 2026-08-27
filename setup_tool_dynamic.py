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
        self.classicapi_enabled = tk.BooleanVar(master=root, value=True)
        self.auction_throttle_enabled = tk.BooleanVar(master=root, value=True)
        self.vmmfix_enabled = tk.BooleanVar(master=root, value=False)
        self.interact_enabled = tk.BooleanVar(master=root, value=False)
        self._download_window = None
        self._download_label = None
        self._download_detail = None
        self._download_percent = None
        self._download_bar = None
        self._download_indeterminate = False
        super().__init__(root)

    def _show_download_progress(self):
        if self._download_window is not None and self._download_window.winfo_exists():
            return

        win = tk.Toplevel(self.root)
        win.title("Updating components")
        win.resizable(False, False)
        win.transient(self.root)
        win.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = ttk.Frame(win, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        title = ttk.Label(
            frame,
            text="Updating selected components",
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        )
        title.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        self._download_label = ttk.Label(
            frame,
            text="Preparing updates...",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self._download_label.grid(row=1, column=0, sticky="w", pady=(0, 4))

        self._download_percent = ttk.Label(
            frame,
            text="",
            font=("Segoe UI", 9, "bold"),
            anchor="e",
            width=6,
        )
        self._download_percent.grid(row=1, column=1, sticky="e", pady=(0, 4))

        self._download_detail = ttk.Label(
            frame,
            text="Please wait while files are downloaded and installed.",
            anchor="w",
            foreground="#666666",
        )
        self._download_detail.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self._download_bar = ttk.Progressbar(
            frame,
            orient="horizontal",
            mode="indeterminate",
            length=460,
        )
        self._download_bar.grid(row=3, column=0, columnspan=2, sticky="ew")

        self._download_window = win

        win.update_idletasks()
        width = max(win.winfo_reqwidth(), 520)
        height = max(win.winfo_reqheight(), 155)
        x = self.root.winfo_rootx() + max((self.root.winfo_width() - width) // 2, 0)
        y = self.root.winfo_rooty() + max((self.root.winfo_height() - height) // 2, 0)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.lift()

        # update(), not only update_idletasks(), is intentional here: downloads
        # run synchronously on the main thread, so Windows otherwise paints an
        # empty Toplevel until the operation completes.
        win.update()

    def _report_download_progress(self, message, current=None, total=None):
        self._show_download_progress()

        if self._download_window is None or not self._download_window.winfo_exists():
            return

        self._download_label.configure(text=message)

        if total is not None and total > 0 and current is not None:
            if self._download_indeterminate:
                self._download_bar.stop()
                self._download_indeterminate = False

            self._download_bar.configure(mode="determinate", maximum=total)
            self._download_bar["value"] = min(current, total)
            percent = int(min(current, total) * 100 / total)
            self._download_percent.configure(text=f"{percent}%")

            downloaded_mb = current / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self._download_detail.configure(
                text=f"{downloaded_mb:.1f} MB / {total_mb:.1f} MB"
            )
        else:
            self._download_percent.configure(text="")
            self._download_detail.configure(
                text="Checking, extracting or installing..."
            )
            if not self._download_indeterminate:
                self._download_bar.configure(mode="indeterminate")
                self._download_bar.start(12)
                self._download_indeterminate = True

        # Process paint/timer events while the synchronous network operation is
        # running so the status text and progress bar remain visible.
        try:
            self._download_window.update()
        except tk.TclError:
            pass

    def _close_download_progress(self):
        if self._download_bar is not None and self._download_indeterminate:
            try:
                self._download_bar.stop()
            except tk.TclError:
                pass

        if self._download_window is not None:
            try:
                if self._download_window.winfo_exists():
                    self._download_window.destroy()
            except tk.TclError:
                pass

        self._download_window = None
        self._download_label = None
        self._download_detail = None
        self._download_percent = None
        self._download_bar = None
        self._download_indeterminate = False

    def _plugin_row(self, parent, text, variable, attribution, tooltip, command=None):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=10, pady=2)

        cb = ttk.Checkbutton(row, text=text, variable=variable, command=command)
        cb.pack(side="left")
        ToolTip(cb, tooltip)

        byline = ttk.Label(
            row,
            text=attribution,
            font=("Segoe UI", 7, "italic"),
        )
        byline.pack(side="right", padx=(6, 0))

        return cb

    def _select_no1600(self):
        if self.optional_plugins["no1600x1200.dll"].get():
            self.vmmfix_enabled.set(False)

    def _select_vmmfix(self):
        if self.vmmfix_enabled.get():
            self.optional_plugins["no1600x1200.dll"].set(False)

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

        core_display = {
            "nampower.dll": ("Nampower", "by brues-code"),
            "UnitXP_SP3.dll": ("UnitXP SP3", "by brues-code"),
            "SuperWoWhook.dll": ("SuperWoW", "by balakethelock"),
            "transmogfix.dll": ("TransmogFix", "by MarcelineVQ"),
            "perf_boost.dll": ("PerfBoost", "by avitasia"),
            "weirdperformance.dll": ("WeirdPerformance", "Dusk92 build 0.7.3"),
            "VanillaHelpers.dll": ("VanillaHelpers", "by isfir"),
        }

        for dll, var in self.core_plugins.items():
            display_name, attribution = core_display.get(
                dll,
                (os.path.splitext(dll)[0], "")
            )
            command = (
                self.update_superwow_managed_controls
                if dll == "SuperWoWhook.dll"
                else None
            )
            self._plugin_row(
                left_frame,
                display_name,
                var,
                attribution,
                self.descriptions.get(dll, ""),
                command=command,
            )

        self._plugin_row(
            left_frame,
            "ClassicAPI",
            self.classicapi_enabled,
            "by brues-code",
            "Adds newer WoW API functions to the Vanilla client so more modern addons can work.",
        )

        self._plugin_row(
            left_frame,
            "AuctionQueryThrottle",
            self.auction_throttle_enabled,
            "by brues-code",
            "Makes Auction House searches much faster by removing the fixed 5-second wait between queries.",
        )

        right_frame = ttk.LabelFrame(container, text="Optional")
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ttk.Label(
            right_frame,
            text="Optional client-side fixes and quality-of-life enhancements.",
            font=("", 8, "italic"),
            wraplength=260,
        ).pack(anchor="w", padx=10, pady=10)

        no1600_var = self.optional_plugins["no1600x1200.dll"]
        self._plugin_row(
            right_frame,
            "No1600x1200",
            no1600_var,
            "source: RetroCro",
            self.descriptions.get("no1600x1200.dll", ""),
            command=self._select_no1600,
        )

        self._plugin_row(
            right_frame,
            "VanillaMultiMonitorFix",
            self.vmmfix_enabled,
            "by Mates1500",
            "Fixes resolution and refresh-rate detection on multi-monitor setups with different display modes. Uses VMMFix_preferred_monitor.txt to select the preferred display.",
            command=self._select_vmmfix,
        )

        self._plugin_row(
            right_frame,
            "Interact",
            self.interact_enabled,
            "by lookino",
            "Adds a modern Interact key for nearby objects, gathering nodes and loot without precise mouse clicking.",
        )

        optional_display = {
            "bigcursor.dll": "BigCursor",
            "customassets.dll": "CustomAssets",
            "logsessions.dll": "LogSessions",
            "minimapicons.dll": "MinimapIcons",
            "pngscreenshots.dll": "PNG Screenshots",
            "worldmarkers.dll": "WorldMarkers",
        }

        for dll, var in self.optional_plugins.items():
            if dll == "no1600x1200.dll":
                continue
            self._plugin_row(
                right_frame,
                optional_display.get(dll, os.path.splitext(dll)[0]),
                var,
                "by MarcelineVQ",
                self.descriptions.get(dll, ""),
            )

    def clean_unselected_files(self, target):
        super().clean_unselected_files(target)

        managed = {
            "ClassicAPI.dll": self.classicapi_enabled,
            "AuctionQueryThrottle.dll": self.auction_throttle_enabled,
            "VanillaMultiMonitorFix.dll": self.vmmfix_enabled,
            "Interact.dll": self.interact_enabled,
        }

        # Remove each live core DLL independently when its checkbox is off.
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

        if not self.interact_enabled.get():
            addon_path = os.path.join(target, "Interface", "AddOns", "Interact")
            if os.path.exists(addon_path):
                shutil.rmtree(addon_path, ignore_errors=True)

    def _warn_offline(self, component, action, error):
        self._close_download_progress()
        messagebox.showwarning(
            "Online update unavailable",
            f"Could not download the latest {component}.\n\n"
            f"{action}\n\nDetails: {error}",
        )

    def _fallback_core_dll(self, payload_base, target, dll_name, error):
        source_dll = os.path.join(payload_base, dll_name)
        target_dll = os.path.join(target, dll_name)
        addon_folder = self.addon_dependencies.get(dll_name)
        target_addon = (
            os.path.join(target, "Interface", "AddOns", addon_folder)
            if addon_folder
            else None
        )

        # Never downgrade a complete existing install because an upstream link
        # happens to be unavailable during an update.
        existing_complete = os.path.isfile(target_dll) and (
            target_addon is None or os.path.isdir(target_addon)
        )
        if existing_complete:
            self._warn_offline(
                dll_name,
                "The version already installed in your WoW folder was kept unchanged.",
                error,
            )
            return

        if not os.path.isfile(source_dll):
            raise RuntimeError(
                f"Could not download the latest {dll_name}, and no bundled fallback exists.\n\n{error}"
            ) from error

        source_addon = None
        if addon_folder:
            source_addon = os.path.join(payload_base, "Interface", "Addons", addon_folder)
            if not os.path.isdir(source_addon):
                raise RuntimeError(
                    f"Could not download the latest {dll_name}, and its bundled fallback addon "
                    f"{addon_folder} is missing.\n\n{error}"
                ) from error

        shutil.copy2(source_dll, target_dll)
        if addon_folder and source_addon:
            remote_packages._replace_directory(source_addon, target_addon)

        self._warn_offline(
            dll_name,
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _fallback_simple_dll(self, target, dll_name, error):
        target_dll = os.path.join(target, dll_name)
        if os.path.isfile(target_dll):
            self._warn_offline(
                dll_name,
                "The version already installed in your WoW folder was kept unchanged.",
                error,
            )
            return

        fallback = os.path.join(get_base_path(), "Payload", "Fallback", dll_name)
        if not os.path.isfile(fallback):
            raise RuntimeError(
                f"Could not download the latest {dll_name}, and its bundled backup is missing.\n\n{error}"
            ) from error

        shutil.copy2(fallback, target_dll)
        self._warn_offline(
            dll_name,
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _fallback_vmmfix(self, target, error):
        target_dll = os.path.join(target, "VanillaMultiMonitorFix.dll")
        if os.path.isfile(target_dll):
            self._warn_offline(
                "VanillaMultiMonitorFix",
                "The version already installed in your WoW folder was kept unchanged.",
                error,
            )
            return

        fallback_dir = os.path.join(
            get_base_path(), "Payload", "Fallback", "VanillaMultiMonitorFix"
        )
        fallback_dll = os.path.join(fallback_dir, "VanillaMultiMonitorFix.dll")
        fallback_config = os.path.join(fallback_dir, "VMMFix_preferred_monitor.txt")
        if not os.path.isfile(fallback_dll):
            raise RuntimeError(
                f"VanillaMultiMonitorFix update failed and its bundled backup is missing.\n\n{error}"
            ) from error

        shutil.copy2(fallback_dll, target_dll)
        target_config = os.path.join(target, "VMMFix_preferred_monitor.txt")
        if not os.path.exists(target_config) and os.path.isfile(fallback_config):
            shutil.copy2(fallback_config, target_config)

        self._warn_offline(
            "VanillaMultiMonitorFix",
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _fallback_interact(self, target, error):
        target_dll = os.path.join(target, "Interact.dll")
        target_addon = os.path.join(target, "Interface", "AddOns", "Interact")
        if os.path.isfile(target_dll) and os.path.isdir(target_addon):
            self._warn_offline(
                "Interact",
                "The version already installed in your WoW folder was kept unchanged.",
                error,
            )
            return

        fallback_dir = os.path.join(get_base_path(), "Payload", "Fallback", "Interact")
        fallback_dll = os.path.join(fallback_dir, "Interact.dll")
        fallback_addon = os.path.join(fallback_dir, "Addon")
        if not os.path.isfile(fallback_dll) or not os.path.isdir(fallback_addon):
            raise RuntimeError(
                f"Interact update failed and its bundled backup is incomplete.\n\n{error}"
            ) from error

        shutil.copy2(fallback_dll, target_dll)
        remote_packages._replace_directory(fallback_addon, target_addon)
        self._warn_offline(
            "Interact",
            "The bundled known-good backup was installed instead.",
            error,
        )

    def run_vanilla_tweaks(self, target):
        # Prefer the latest stable tubtubs build on every Apply. A known-good
        # tubtubs build is bundled as the offline fallback.
        try:
            tweaks_exe, extract_root, version = remote_packages.prepare_vanilla_tweaks(
                progress=self._report_download_progress,
            )
        except Exception as exc:
            self._close_download_progress()
            messagebox.showwarning(
                "Latest vanilla-tweaks unavailable",
                "Could not download the latest tubtubs/vanilla-tweaks build.\n\n"
                "The bundled known-good tubtubs build will be used instead, so "
                "the same modern patch options remain available.\n\n"
                f"Details: {exc}",
            )
            return super().run_vanilla_tweaks(target, modern_cli=True)

        try:
            self._report_download_progress(
                f"Applying vanilla-tweaks {version}...",
                None,
                None,
            )
            return super().run_vanilla_tweaks(
                target,
                tweaks_exe=tweaks_exe,
                modern_cli=True,
            )
        finally:
            shutil.rmtree(extract_root, ignore_errors=True)
            self._close_download_progress()

    def configure_plugins(self, target):
        payload_base = os.path.join(get_base_path(), "Payload")
        payload_weirdu = os.path.join(payload_base, "WeirdUtils")

        dlls_text_lines = []
        if self.rendering_mode.get() == "dxvk":
            dlls_text_lines.append("dxvk")

        try:
            # Core plugins. UnitXP and SuperWoW are refreshed from their upstream
            # sources every time setup is applied. Their bundled copies remain an
            # offline fallback so this feature does not reduce current reliability.
            for dll_name, var in self.core_plugins.items():
                if not var.get():
                    continue

                if dll_name == "nampower.dll":
                    try:
                        remote_packages.install_nampower(
                            target,
                            progress=self._report_download_progress,
                        )
                    except Exception as exc:
                        self._fallback_core_dll(payload_base, target, dll_name, exc)

                elif dll_name == "VanillaHelpers.dll":
                    try:
                        remote_packages.install_vanillahelpers(
                            target,
                            progress=self._report_download_progress,
                        )
                    except Exception as exc:
                        self._fallback_core_dll(payload_base, target, dll_name, exc)

                elif dll_name == "UnitXP_SP3.dll":
                    try:
                        remote_packages.install_unitxp(
                            target,
                            progress=self._report_download_progress,
                        )
                    except Exception as exc:
                        self._fallback_core_dll(payload_base, target, dll_name, exc)

                elif dll_name == "SuperWoWhook.dll":
                    try:
                        remote_packages.install_superwow(
                            target,
                            progress=self._report_download_progress,
                        )
                    except Exception as exc:
                        self._fallback_core_dll(payload_base, target, dll_name, exc)

                else:
                    source_dll = os.path.join(payload_base, dll_name)
                    if os.path.exists(source_dll):
                        shutil.copy2(source_dll, target)

                dlls_text_lines.append(dll_name)

            # Live core plugins. Both checkboxes are independent and can be
            # installed together.
            if self.classicapi_enabled.get():
                try:
                    remote_packages.install_classicapi(
                        target,
                        progress=self._report_download_progress,
                    )
                except Exception as exc:
                    self._fallback_simple_dll(target, "ClassicAPI.dll", exc)
                dlls_text_lines.append("ClassicAPI.dll")

            if self.auction_throttle_enabled.get():
                try:
                    remote_packages.install_auction_query_throttle(
                        target,
                        progress=self._report_download_progress,
                    )
                except Exception as exc:
                    self._fallback_simple_dll(target, "AuctionQueryThrottle.dll", exc)
                dlls_text_lines.append("AuctionQueryThrottle.dll")

            # Clean dependent addons when the matching core DLL is disabled.
            for dll_name, addon_folder in self.addon_dependencies.items():
                core_var = self.core_plugins.get(dll_name)
                if core_var is not None and not core_var.get():
                    addon_path = os.path.join(target, "Interface", "AddOns", addon_folder)
                    if os.path.exists(addon_path):
                        shutil.rmtree(addon_path, ignore_errors=True)

            # Optional client fixes, in the same order as the UI.
            no1600_var = self.optional_plugins["no1600x1200.dll"]
            if no1600_var.get():
                try:
                    remote_packages.install_no1600x1200(
                        target,
                        progress=self._report_download_progress,
                    )
                except Exception as exc:
                    self._fallback_core_dll(
                        payload_base,
                        target,
                        "no1600x1200.dll",
                        exc,
                    )
                dlls_text_lines.append("no1600x1200.dll")

            if self.vmmfix_enabled.get():
                try:
                    remote_packages.install_vanilla_multimonitor_fix(
                        target,
                        progress=self._report_download_progress,
                    )
                except Exception as exc:
                    self._fallback_vmmfix(target, exc)
                dlls_text_lines.append("VanillaMultiMonitorFix.dll")

            if self.interact_enabled.get():
                try:
                    remote_packages.install_interact(
                        target,
                        progress=self._report_download_progress,
                    )
                except Exception as exc:
                    self._fallback_interact(target, exc)
                dlls_text_lines.append("Interact.dll")

            # Optional WeirdUtils.
            for dll_name, var in self.optional_plugins.items():
                if dll_name == "no1600x1200.dll":
                    continue
                if var.get():
                    source_dll = os.path.join(payload_weirdu, dll_name)
                    if os.path.exists(source_dll):
                        shutil.copy2(source_dll, target)
                    dlls_text_lines.append(dll_name)

            with open(os.path.join(target, "dlls.txt"), "w") as f:
                f.write("\n".join(dlls_text_lines))
        finally:
            self._close_download_progress()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
