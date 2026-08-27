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
        )
        cb_classicapi.pack(anchor="w", padx=10, pady=4)
        ToolTip(
            cb_classicapi,
            "Adds newer WoW API functions to the Vanilla client so more modern addons can work.",
        )

        cb_auction = ttk.Checkbutton(
            left_frame,
            text="AuctionQueryThrottle.dll",
            variable=self.auction_throttle_enabled,
        )
        cb_auction.pack(anchor="w", padx=10, pady=4)
        ToolTip(
            cb_auction,
            "Makes Auction House searches much faster by removing the fixed 5-second wait between queries.",
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

    def clean_unselected_files(self, target):
        super().clean_unselected_files(target)

        managed = {
            "ClassicAPI.dll": self.classicapi_enabled,
            "AuctionQueryThrottle.dll": self.auction_throttle_enabled,
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

        self._close_download_progress()
        messagebox.showwarning(
            "Online update unavailable",
            f"Could not download the latest {dll_name}.\n\n"
            f"The bundled version will be used instead.\n\nDetails: {error}",
        )

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

                elif dll_name == "no1600x1200.dll":
                    try:
                        remote_packages.install_no1600x1200(
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
                    raise RuntimeError(f"ClassicAPI update failed:\n{exc}") from exc
                dlls_text_lines.append("ClassicAPI.dll")

            if self.auction_throttle_enabled.get():
                try:
                    remote_packages.install_auction_query_throttle(
                        target,
                        progress=self._report_download_progress,
                    )
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
        finally:
            self._close_download_progress()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
