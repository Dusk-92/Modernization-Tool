import os
import json
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

        # Discord Rich Presence detail choices are kept independently from the
        # main WowPresence checkbox so hiding/disabling the integration never
        # destroys the user's selected disclosure preferences.
        self.discord_show_character_details = tk.BooleanVar(master=root, value=True)
        self.discord_detail_vars = {
            "name": tk.BooleanVar(master=root, value=True),
            "guild": tk.BooleanVar(master=root, value=True),
            "race": tk.BooleanVar(master=root, value=True),
            "faction": tk.BooleanVar(master=root, value=True),
            "class": tk.BooleanVar(master=root, value=True),
            "level": tk.BooleanVar(master=root, value=True),
            "zone": tk.BooleanVar(master=root, value=True),
        }
        self.discord_presence_details_frame = None
        self.discord_detail_checkbuttons = {}

        self._download_window = None
        self._download_label = None
        self._download_detail = None
        self._download_percent = None
        self._download_bar = None
        self._download_indeterminate = False
        super().__init__(root)

    def _bundled_manifest_record(self, relative_path):
        """Return the expected size/hash record for one bundled payload file."""
        metadata_path = os.path.join(
            get_base_path(),
            "Payload",
            "Fallback",
            "versions.json",
        )
        wanted = relative_path.replace("\\", "/").casefold()
        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError, ValueError, TypeError) as exc:
            raise RuntimeError(
                "Could not read bundled component integrity metadata."
            ) from exc

        components = data.get("components") if isinstance(data, dict) else None
        if not isinstance(components, dict):
            raise RuntimeError("Bundled component integrity metadata is invalid.")

        for component in components.values():
            files = component.get("files") if isinstance(component, dict) else None
            if not isinstance(files, list):
                continue
            for record in files:
                if not isinstance(record, dict):
                    continue
                path = record.get("path")
                if isinstance(path, str) and path.replace("\\", "/").casefold() == wanted:
                    return record

        raise RuntimeError(
            f"No integrity record exists for bundled file {relative_path}."
        )

    def _verified_bundled_file(self, relative_path, label):
        """Validate a bundled file before it is allowed to touch the WoW folder."""
        record = self._bundled_manifest_record(relative_path)
        source = os.path.join(
            get_base_path(),
            *relative_path.replace("\\", "/").split("/"),
        )
        if not os.path.isfile(source):
            raise RuntimeError(f"Bundled file is missing: {relative_path}")

        expected_size = record.get("size")
        if not isinstance(expected_size, int) or expected_size <= 0:
            raise RuntimeError(f"Invalid bundled size metadata for {relative_path}.")
        if os.path.getsize(source) != expected_size:
            raise RuntimeError(
                f"Bundled {label} has an unexpected size and will not be installed."
            )

        expected_sha = record.get("sha256")
        if (
            not isinstance(expected_sha, str)
            or len(expected_sha) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in expected_sha)
        ):
            raise RuntimeError(f"Invalid bundled SHA-256 metadata for {relative_path}.")
        expected_sha = expected_sha.lower()

        if self._file_sha256(source).lower() != expected_sha:
            raise RuntimeError(
                f"Bundled {label} failed its SHA-256 integrity check."
            )

        if os.path.splitext(source)[1].lower() in (".dll", ".exe"):
            remote_packages._verify_x86_pe(source, f"bundled {label}")

        return source, expected_sha

    def _install_verified_bundled_file(self, relative_path, target_path, label):
        source, expected_sha = self._verified_bundled_file(relative_path, label)
        if os.path.isfile(target_path):
            try:
                if self._file_sha256(target_path).lower() == expected_sha:
                    return
            except OSError:
                pass
        remote_packages._atomic_replace_file(source, target_path)

    def copy_base_files(self, target):
        """Install only true base files; component addons are handled with their DLLs."""
        payload_dir = os.path.join(get_base_path(), "Payload")
        if not os.path.isdir(payload_dir):
            return

        if self.install_autologin.get():
            data_source = os.path.join(payload_dir, "Data")
            if os.path.isdir(data_source):
                shutil.copytree(
                    data_source,
                    os.path.join(target, "Data"),
                    dirs_exist_ok=True,
                )

        # Do not copy Payload/Interface wholesale here. Nampower and UnitXP
        # addons must stay paired with the exact DLL version selected later.
        vanilla_fixes, vf_sha = self._verified_bundled_file(
            "Payload/VanillaFixes.exe",
            "VanillaFixes.exe",
        )
        vf_patcher, patcher_sha = self._verified_bundled_file(
            "Payload/VfPatcher.dll",
            "VfPatcher.dll",
        )
        target_fixes = os.path.join(target, "VanillaFixes.exe")
        target_patcher = os.path.join(target, "VfPatcher.dll")

        already_current = False
        if os.path.isfile(target_fixes) and os.path.isfile(target_patcher):
            try:
                already_current = (
                    self._file_sha256(target_fixes).lower() == vf_sha
                    and self._file_sha256(target_patcher).lower() == patcher_sha
                )
            except OSError:
                already_current = False

        if not already_current:
            remote_packages._transactional_replace_bundle(
                [
                    ("file", vanilla_fixes, target_fixes),
                    ("file", vf_patcher, target_patcher),
                ],
                label="VanillaFixes",
            )

    def _collect_settings(self):
        settings = super()._collect_settings()
        settings["discord_presence"] = {
            "show_character_details": bool(self.discord_show_character_details.get()),
            "details": {
                name: bool(var.get())
                for name, var in self.discord_detail_vars.items()
            },
        }
        return settings

    def _apply_settings_dict(self, saved):
        super()._apply_settings_dict(saved)

        discord = saved.get("discord_presence") if isinstance(saved, dict) else None
        if not isinstance(discord, dict):
            return

        show_details = discord.get("show_character_details")
        if isinstance(show_details, bool):
            self.discord_show_character_details.set(show_details)

        details = discord.get("details")
        if isinstance(details, dict):
            for name, value in details.items():
                var = self.discord_detail_vars.get(name)
                if var is not None and isinstance(value, bool):
                    var.set(value)

    def _load_wowpresence_broadcast_preferences(self, target_dir):
        """Migrate the old six-bit mask into the new seven-choice UI."""
        mask = remote_packages.read_wowpresence_broadcast_flags(target_dir)
        if mask is None:
            return

        bits = {
            "name": remote_packages.WOWPRESENCE_SHARE_NAME,
            "guild": remote_packages.WOWPRESENCE_SHARE_GUILD,
            "faction": remote_packages.WOWPRESENCE_SHARE_FACTION,
            "class": remote_packages.WOWPRESENCE_SHARE_CLASS,
            "level": remote_packages.WOWPRESENCE_SHARE_LEVEL,
            "zone": remote_packages.WOWPRESENCE_SHARE_ZONE,
        }
        for name, bit in bits.items():
            self.discord_detail_vars[name].set(bool(mask & bit))

        # WowPresence versions before the dedicated Race flag always exposed
        # race information regardless of the six-bit mask. Treat masks <= 63
        # as legacy so the migration preserves exactly that visible behavior.
        if mask <= 63:
            self.discord_detail_vars["race"].set(True)
        else:
            self.discord_detail_vars["race"].set(
                bool(mask & remote_packages.WOWPRESENCE_SHARE_RACE)
            )

        # "Show character details" now means "show everything". Only select it
        # automatically when the existing configuration already represents the
        # full legacy/default disclosure set. Any custom mask stays custom.
        legacy_all = (
            mask <= 63
            and (mask & 63) == 63
        )
        current_all = (
            mask > 63
            and (mask & remote_packages.WOWPRESENCE_SHARE_ALL)
            == remote_packages.WOWPRESENCE_SHARE_ALL
        )
        self.discord_show_character_details.set(legacy_all or current_all)
        if self.discord_show_character_details.get():
            for var in self.discord_detail_vars.values():
                var.set(True)

    def _load_legacy_install_state(self, target_dir):
        super()._load_legacy_install_state(target_dir)
        self._load_wowpresence_broadcast_preferences(target_dir)

    def load_settings(self, target_dir):
        settings_path = self._settings_path(target_dir)
        has_saved_discord_preferences = False
        try:
            with open(settings_path, "r", encoding="utf-8") as handle:
                saved = json.load(handle)
            has_saved_discord_preferences = isinstance(
                saved.get("discord_presence") if isinstance(saved, dict) else None,
                dict,
            )
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass

        loaded = super().load_settings(target_dir)

        # Existing v2.1 settings.json files predate the detailed controls. Read
        # their actual WowPresence mask once so manual choices are not lost.
        if os.path.isfile(settings_path) and not has_saved_discord_preferences:
            self._load_wowpresence_broadcast_preferences(target_dir)

        self.update_discord_presence_controls()
        return loaded

    def _discord_broadcast_mask(self):
        if self.discord_show_character_details.get():
            return remote_packages.WOWPRESENCE_SHARE_ALL

        bits = {
            "name": remote_packages.WOWPRESENCE_SHARE_NAME,
            "guild": remote_packages.WOWPRESENCE_SHARE_GUILD,
            "race": remote_packages.WOWPRESENCE_SHARE_RACE,
            "faction": remote_packages.WOWPRESENCE_SHARE_FACTION,
            "class": remote_packages.WOWPRESENCE_SHARE_CLASS,
            "level": remote_packages.WOWPRESENCE_SHARE_LEVEL,
            "zone": remote_packages.WOWPRESENCE_SHARE_ZONE,
        }
        mask = 0
        for name, bit in bits.items():
            var = self.discord_detail_vars.get(name)
            if var is not None and var.get():
                mask |= bit
        return mask

    def _toggle_discord_all_details(self):
        show_all = bool(self.discord_show_character_details.get())
        if show_all:
            for var in self.discord_detail_vars.values():
                var.set(True)
        self.update_discord_detail_states()

    def update_discord_detail_states(self):
        state = "disabled" if self.discord_show_character_details.get() else "normal"
        for checkbox in getattr(self, "discord_detail_checkbuttons", {}).values():
            try:
                checkbox.configure(state=state)
            except tk.TclError:
                pass

    def update_discord_presence_controls(self):
        frame = getattr(self, "discord_presence_details_frame", None)
        if frame is None:
            return

        var = self.optional_plugins.get("WowPresence.dll")
        visible = bool(var is not None and var.get())
        manager = frame.winfo_manager()

        if visible and not manager:
            frame.pack(fill="x", padx=(22, 8), pady=(0, 4))
        elif not visible and manager:
            frame.pack_forget()

        if visible:
            self.update_discord_detail_states()

    def _build_discord_presence_details(self, parent):
        frame = ttk.Frame(parent)
        self.discord_presence_details_frame = frame

        show_cb = ttk.Checkbutton(
            frame,
            text="Show character details",
            variable=self.discord_show_character_details,
            command=self._toggle_discord_all_details,
        )
        show_cb.pack(anchor="w", padx=6, pady=(1, 2))
        ToolTip(
            show_cb,
            "When enabled, all character details are shown and the individual choices "
            "below are locked. Uncheck it to choose each detail separately.",
        )

        labels = {
            "name": "Character Name",
            "guild": "Guild",
            "race": "Race",
            "faction": "Faction",
            "class": "Class",
            "level": "Level",
            "zone": "Zone",
        }
        for name, label in labels.items():
            cb = ttk.Checkbutton(
                frame,
                text=label,
                variable=self.discord_detail_vars[name],
            )
            cb.pack(anchor="w", padx=24, pady=1)
            self.discord_detail_checkbuttons[name] = cb
            ToolTip(
                cb,
                f"Choose whether WowPresence may publish your {label.lower()} on Discord.",
            )

        self.update_discord_presence_controls()

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
        try:
            # Keep checkboxes and folder selection from changing underneath a
            # synchronous installation while progress callbacks pump Tk events.
            win.grab_set()
        except tk.TclError:
            pass

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
                    try:
                        self._download_window.grab_release()
                    except tk.TclError:
                        pass
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
            "weirdperformance.dll": ("WeirdPerformance", "by Dusk-92"),
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
            "WowPresence.dll": "Discord Rich Presence",
        }
        optional_attribution = {
            "WowPresence.dll": "by Dusk-92",
        }

        for dll, var in self.optional_plugins.items():
            if dll == "no1600x1200.dll":
                continue

            command = (
                self.update_discord_presence_controls
                if dll == "WowPresence.dll"
                else None
            )
            self._plugin_row(
                right_frame,
                optional_display.get(dll, os.path.splitext(dll)[0]),
                var,
                optional_attribution.get(dll, "by MarcelineVQ"),
                self.descriptions.get(dll, ""),
                command=command,
            )

            if dll == "WowPresence.dll":
                self._build_discord_presence_details(right_frame)

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

    def _valid_x86_dll(self, path, label):
        if not os.path.isfile(path):
            return False
        try:
            remote_packages._verify_x86_pe(path, label)
            return True
        except Exception:
            return False

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
        existing_complete = self._valid_x86_dll(
            target_dll,
            f"installed {dll_name}",
        ) and (
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

        self._verified_bundled_file(
            f"Payload/{dll_name}",
            f"{dll_name} fallback",
        )

        source_addon = None
        if addon_folder:
            source_addon = os.path.join(payload_base, "Interface", "Addons", addon_folder)
            if not os.path.isdir(source_addon):
                raise RuntimeError(
                    f"Could not download the latest {dll_name}, and its bundled fallback addon "
                    f"{addon_folder} is missing.\n\n{error}"
                ) from error

        if addon_folder and source_addon:
            remote_packages._transactional_replace_bundle(
                [
                    ("file", source_dll, target_dll),
                    ("dir", source_addon, target_addon),
                ],
                label=f"{dll_name} bundled fallback",
            )
        else:
            remote_packages._atomic_replace_file(source_dll, target_dll)

        self._warn_offline(
            dll_name,
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _fallback_simple_dll(self, target, dll_name, error):
        target_dll = os.path.join(target, dll_name)
        if self._valid_x86_dll(target_dll, f"installed {dll_name}"):
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

        remote_packages._verify_x86_pe(
            fallback,
            f"bundled fallback {dll_name}",
        )
        remote_packages._atomic_replace_file(fallback, target_dll)
        self._warn_offline(
            dll_name,
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _fallback_vmmfix(self, target, error):
        target_dll = os.path.join(target, "VanillaMultiMonitorFix.dll")
        if self._valid_x86_dll(
            target_dll,
            "installed VanillaMultiMonitorFix.dll",
        ):
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

        remote_packages._verify_x86_pe(
            fallback_dll,
            "bundled fallback VanillaMultiMonitorFix.dll",
        )
        remote_packages._atomic_replace_file(fallback_dll, target_dll)
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
        if (
            self._valid_x86_dll(target_dll, "installed Interact.dll")
            and os.path.isdir(target_addon)
        ):
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

        remote_packages._verify_x86_pe(
            fallback_dll,
            "bundled fallback Interact.dll",
        )
        remote_packages._transactional_replace_bundle(
            [
                ("file", fallback_dll, target_dll),
                ("dir", fallback_addon, target_addon),
            ],
            label="Interact bundled fallback",
        )
        self._warn_offline(
            "Interact",
            "The bundled known-good backup was installed instead.",
            error,
        )

    def _vanilla_tweaks_marker_path(self, target):
        return os.path.join(
            target,
            ".modernization_tool",
            "vanilla_tweaks.json",
        )

    def _bundled_vanilla_tweaks_info(self):
        info = {
            "version": "bundled",
            "source": "bundled vanilla-tweaks.exe",
        }
        metadata_path = os.path.join(
            get_base_path(),
            "Payload",
            "Fallback",
            "versions.json",
        )
        try:
            with open(metadata_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            component = data.get("components", {}).get("vanilla-tweaks fallback", {})
            if isinstance(component, dict):
                if component.get("version"):
                    info["version"] = str(component["version"])
                if component.get("source"):
                    info["source"] = str(component["source"])
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
        return info

    def _write_vanilla_tweaks_marker(
        self,
        target,
        patcher_source,
        patcher_version,
        patcher_path,
        patcher_revision=None,
    ):
        wow_exe = os.path.join(target, "WoW.exe")
        output_exe = os.path.join(target, "WoW_Modernized.exe")
        if not os.path.isfile(wow_exe) or not os.path.isfile(output_exe):
            raise RuntimeError(
                "Cannot record vanilla-tweaks state because a required WoW executable is missing."
            )

        marker_path = self._vanilla_tweaks_marker_path(target)
        os.makedirs(os.path.dirname(marker_path), exist_ok=True)
        temp_path = marker_path + ".new"
        payload = {
            "schema": 2,
            "patcher_source": patcher_source,
            "patcher_version": str(patcher_version),
            "patcher_revision": (
                str(patcher_revision) if patcher_revision is not None else None
            ),
            "patcher_sha256": (
                self._file_sha256(patcher_path)
                if patcher_path and os.path.isfile(patcher_path)
                else None
            ),
            "input_wow_sha256": self._file_sha256(wow_exe),
            "output_sha256": self._file_sha256(output_exe),
            "settings_signature": self._vanilla_tweaks_signature(),
        }

        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        os.replace(temp_path, marker_path)

    def _existing_vanilla_tweaks_output_matches(self, target):
        marker_path = self._vanilla_tweaks_marker_path(target)
        wow_exe = os.path.join(target, "WoW.exe")
        output_exe = os.path.join(target, "WoW_Modernized.exe")

        if not (
            os.path.isfile(marker_path)
            and os.path.isfile(wow_exe)
            and os.path.isfile(output_exe)
        ):
            return False, None

        try:
            with open(marker_path, "r", encoding="utf-8") as handle:
                marker = json.load(handle)
            if not isinstance(marker, dict):
                return False, None

            if marker.get("settings_signature") != self._vanilla_tweaks_signature():
                return False, marker

            if marker.get("input_wow_sha256") != self._file_sha256(wow_exe):
                return False, marker

            if marker.get("output_sha256") != self._file_sha256(output_exe):
                return False, marker

            valid_pe, _ = self._inspect_wow_executable(output_exe)
            if not valid_pe:
                return False, marker

            return True, marker
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            return False, None

    def run_vanilla_tweaks(self, target):
        # First compare the small GitHub release metadata with the patcher
        # revision already recorded for this exact WoW.exe/settings output.
        # The multi-megabyte Windows package is downloaded only when needed.
        existing_matches, marker = self._existing_vanilla_tweaks_output_matches(
            target
        )

        try:
            self._report_download_progress(
                "Checking vanilla-tweaks release...",
                None,
                None,
            )
            release_info = remote_packages.vanilla_tweaks_release_info()
        except Exception as exc:
            self._close_download_progress()

            if existing_matches:
                patcher_version = (
                    marker.get("patcher_version", "previously installed")
                    if isinstance(marker, dict)
                    else "previously installed"
                )
                messagebox.showwarning(
                    "Latest vanilla-tweaks unavailable",
                    "Could not check the latest tubtubs/vanilla-tweaks build.\n\n"
                    "Your existing WoW_Modernized.exe matches the current WoW.exe "
                    "and all executable patch settings, so it was kept unchanged.\n\n"
                    f"Existing patcher version: {patcher_version}\n\n"
                    f"Details: {exc}",
                )
                return os.path.join(target, "WoW_Modernized.exe")

            bundled = self._bundled_vanilla_tweaks_info()
            bundled_exe = os.path.join(get_base_path(), "vanilla-tweaks.exe")
            messagebox.showwarning(
                "Latest vanilla-tweaks unavailable",
                "Could not check the latest tubtubs/vanilla-tweaks build.\n\n"
                "The current WoW.exe or executable patch settings need to be "
                "repatched, so the bundled known-good vanilla-tweaks build will "
                f"be used instead ({bundled['version']}).\n\n"
                f"Details: {exc}",
            )

            result = super().run_vanilla_tweaks(
                target,
                tweaks_exe=bundled_exe,
                modern_cli=True,
            )
            self._write_vanilla_tweaks_marker(
                target,
                patcher_source="bundled",
                patcher_version=bundled["version"],
                patcher_path=bundled_exe,
            )
            return result

        remote_revision = release_info["revision"]
        remote_version = release_info["version"]
        if existing_matches and isinstance(marker, dict):
            same_online_patcher = (
                marker.get("patcher_source") == "online"
                and (
                    str(marker.get("patcher_revision")) == str(remote_revision)
                    or (
                        marker.get("patcher_revision") in (None, "")
                        and str(marker.get("patcher_version")) == str(remote_version)
                    )
                )
            )
            if same_online_patcher:
                self._report_download_progress(
                    f"vanilla-tweaks {remote_version} is already current.",
                    None,
                    None,
                )
                self._close_download_progress()
                return os.path.join(target, "WoW_Modernized.exe")

        try:
            tweaks_exe, extract_root, version, revision = (
                remote_packages.prepare_vanilla_tweaks(
                    progress=self._report_download_progress,
                    release_info=release_info,
                )
            )
        except Exception as exc:
            self._close_download_progress()

            # A remote update may exist but be temporarily unavailable. Keep a
            # valid existing output rather than downgrading or repatching it.
            if existing_matches:
                patcher_version = (
                    marker.get("patcher_version", "previously installed")
                    if isinstance(marker, dict)
                    else "previously installed"
                )
                messagebox.showwarning(
                    "Latest vanilla-tweaks unavailable",
                    "The latest vanilla-tweaks package could not be downloaded.\n\n"
                    "Your existing WoW_Modernized.exe still matches the current "
                    "WoW.exe and all executable patch settings, so it was kept unchanged.\n\n"
                    f"Existing patcher version: {patcher_version}\n\n"
                    f"Details: {exc}",
                )
                return os.path.join(target, "WoW_Modernized.exe")

            bundled = self._bundled_vanilla_tweaks_info()
            bundled_exe = os.path.join(get_base_path(), "vanilla-tweaks.exe")
            messagebox.showwarning(
                "Latest vanilla-tweaks unavailable",
                "The latest vanilla-tweaks package could not be downloaded.\n\n"
                "The current WoW.exe or executable patch settings need to be "
                "repatched, so the bundled known-good vanilla-tweaks build will "
                f"be used instead ({bundled['version']}).\n\n"
                f"Details: {exc}",
            )

            result = super().run_vanilla_tweaks(
                target,
                tweaks_exe=bundled_exe,
                modern_cli=True,
            )
            self._write_vanilla_tweaks_marker(
                target,
                patcher_source="bundled",
                patcher_version=bundled["version"],
                patcher_path=bundled_exe,
            )
            return result

        try:
            self._report_download_progress(
                f"Applying vanilla-tweaks {version}...",
                None,
                None,
            )
            result = super().run_vanilla_tweaks(
                target,
                tweaks_exe=tweaks_exe,
                modern_cli=True,
            )
            self._write_vanilla_tweaks_marker(
                target,
                patcher_source="online",
                patcher_version=version,
                patcher_path=tweaks_exe,
                patcher_revision=revision,
            )
            return result
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
            # Core plugins are refreshed from their upstream sources where supported.
            # Bundled fallbacks are used only for components whose redistribution
            # model allows it. SuperWoW/SuperAPI are upstream-only.
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

                elif dll_name == "perf_boost.dll":
                    source_dll, _ = self._verified_bundled_file(
                        "Payload/perf_boost.dll",
                        "PerfBoost",
                    )
                    source_addon = os.path.join(
                        payload_base,
                        "Interface",
                        "Addons",
                        "perfboostsettings",
                    )
                    if not os.path.isdir(source_addon):
                        raise RuntimeError(
                            "Bundled PerfBoost settings addon is missing."
                        )
                    remote_packages._transactional_replace_bundle(
                        [
                            (
                                "file",
                                source_dll,
                                os.path.join(target, "perf_boost.dll"),
                            ),
                            (
                                "dir",
                                source_addon,
                                os.path.join(
                                    target,
                                    "Interface",
                                    "AddOns",
                                    "perfboostsettings",
                                ),
                            ),
                        ],
                        label="PerfBoost",
                    )

                else:
                    self._install_verified_bundled_file(
                        f"Payload/{dll_name}",
                        os.path.join(target, dll_name),
                        dll_name,
                    )

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
                # No1600x1200 comes from an archive/mirror repository rather
                # than a maintained release channel. Use the bundled,
                # hash-verified known-good copy for predictable installs.
                self._install_verified_bundled_file(
                    "Payload/no1600x1200.dll",
                    os.path.join(target, "no1600x1200.dll"),
                    "no1600x1200.dll",
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

            # Optional WeirdUtils and WowPresence.
            for dll_name, var in self.optional_plugins.items():
                if dll_name == "no1600x1200.dll":
                    continue
                if not var.get():
                    continue

                if dll_name == "WowPresence.dll":
                    try:
                        remote_packages.install_wowpresence(
                            target,
                            progress=self._report_download_progress,
                        )
                    except Exception as exc:
                        existing_dll = os.path.join(target, "WowPresence.dll")
                        existing_exe = os.path.join(target, "WowPresence.exe")
                        if (
                            self._valid_x86_dll(existing_dll, "WowPresence.dll")
                            and self._valid_x86_dll(existing_exe, "WowPresence.exe")
                        ):
                            remote_packages.ensure_wowpresence_config(target)
                            self._warn_offline(
                                "WowPresence",
                                "Keeping the currently installed WowPresence binaries.",
                                exc,
                            )
                        else:
                            raise RuntimeError(
                                "Could not install WowPresence from "
                                "https://github.com/Dusk-92/WowPresence releases."
                            ) from exc

                    # Remove the old test-branch filenames after a successful
                    # migration. The legacy config directory is intentionally
                    # left untouched so the user can remove it manually.
                    for legacy_name in ("DiscordPresence.dll", "DiscordPresence.exe"):
                        legacy_path = os.path.join(target, legacy_name)
                        if os.path.isfile(legacy_path):
                            try:
                                os.remove(legacy_path)
                            except OSError:
                                pass

                    remote_packages.write_wowpresence_broadcast_flags(
                        target,
                        self._discord_broadcast_mask(),
                    )
                else:
                    self._install_verified_bundled_file(
                        f"Payload/WeirdUtils/{dll_name}",
                        os.path.join(target, dll_name),
                        dll_name,
                    )

                dlls_text_lines.append(dll_name)

            # Preserve user-added dlls.txt entries; replace only entries
            # managed by Modernization Tool.
            self._write_dlls_file(target, dlls_text_lines)
        finally:
            self._close_download_progress()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernWowSetupTool(root)
    root.mainloop()
