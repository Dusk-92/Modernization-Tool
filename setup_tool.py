import os
import sys
import shutil
import subprocess
import math
import re
import stat
import tkinter as tk
import webbrowser
from tkinter import ttk, filedialog, messagebox

def get_base_path():
    """Gets the correct directory whether running as a script or a compiled .exe"""
    if getattr(sys, 'frozen', False):
        # Running as a compiled PyInstaller executable
        return sys._MEIPASS
    # Running as a normal Python script
    return os.path.dirname(os.path.abspath(__file__))

class ToolTip:
    """Creates a hover-tooltip for a given tkinter widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        self.id = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(400, self.showtip) # 400ms delay before showing

    def unschedule(self):
        if self.id:
            self.widget.after_cancel(self.id)
            self.id = None

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("Segoe UI", "9", "normal"), wraplength=350)
        label.pack(ipadx=6, ipady=4)

    def leave(self, event=None):
        self.unschedule()
        if self.tw:
            self.tw.destroy()
            self.tw = None

class WowSetupTool:
    def __init__(self, root):
        self.root = root
        self.root.title("WoW Vanilla 1.12 Modernization Tool")
        
        # Lock window size exactly as requested
        self.root.geometry("680x610") 
        self.root.resizable(False, False)

        icon_path = os.path.join(get_base_path(), "PurpleWowLogo.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        # Dictionary containing all tooltip explanations
        self.descriptions = {
            # Setup & General
            "autologin": "Automates the authentication process. Bypasses the standard login screen by securely passing your credentials so you drop directly into the character selection screen.",
            "render_directx9": "Uses VanillaFixes with the game's native DirectX 9 renderer. Choose this if you do not want DXVK/Vulkan.",
            "render_dxvk": "Uses VanillaFixes with DXVK, translating DirectX 9 to Vulkan for smoother frame pacing on many modern systems.",

            # Core DLLs
            "nampower.dll": "Improves spell input responsiveness by adding modern spell queueing and latency compensation to the Vanilla client.",
            "no1600x1200.dll": "Removes the hardcoded 1600x1200 resolution limit. Natively unlocks widescreen and ultrawidescreen resolutions in the game settings.",
            "perf_boost.dll": "Provides dynamic render distance controls (culling). Stabilizes framerates in crowded environments by lowering the rendering priority of non-essential entities.",
            "UnitXP_SP3.dll": "Engine-level optimizations replacing legacy assembly. Introduces improved network handling, better Tab-targeting, true line-of-sight checks via Lua, and modern nameplate support.",
            "VanillaHelpers.dll": "Expands engine limits. Raises the client memory allocator from 2GB to 4GB to prevent Out-of-Memory crashes and introduces modern high-resolution texture support.",
            "SuperWoWhook.dll": "Injects a massively expanded Lua API. Increases macro limit, enables castbars on nameplates, and provides hooks for modern UI addons.",
            "transmogfix.dll": "Eliminates FPS drops caused by rapid equipment visual updates when transmogged items lose durability.",
            "weirdperformance.dll": "Engine-level optimizations: SIMD math replacements, faster data decompression (modern zlib), MPQ file caching, timer calibration, and Lua runtime GC improvements.",

            # WeirdUtils
            "bigcursor.dll": "Upscales the hardware cursor for improved visibility on modern resolutions without losing sharpness (up to 4.0x scale via CVar).",
            "customassets.dll": "Enables loading loose game asset files from the Data/ directory mirroring internal paths without needing to repack MPQ archives.",
            "logsessions.dll": "Organizes combat and chat logs into clean, per-character, per-day files automatically upon login.",
            "minimapicons.dll": "Adds TBC/WotLK-style minimap tracking icons for NPCs and objects, combined into a new native tracking dropdown.",
            "pngscreenshots.dll": "Saves screenshots as compressed PNG files on a background thread to completely eliminate frame drops when taking pictures.",
            "worldmarkers.dll": "Place up to 5 animated colored markers (Cataclysm style) in the world for raid positioning. Syncs automatically with other users.",

            # Tweaks Tab
            "fov": "Calculates horizontal Field of View mathematically scaled to maintain vertical aspect space based on your screen ratio.",
            "farclip": "Increases the maximum terrain render distance. Vanilla default is 777. Tweaks default is 1500.",
            "frill": "Changes the ground clutter (grass) render distance. Vanilla default is 70. Tweaks default is 300.",
            "nameplate": "Increases the distance at which enemy nameplates become visible. Vanilla default is 20. Tweaks default is 41.",
            "cam": "Increases the maximum camera zoom-out distance. Vanilla default is 50. Max safe limit is 100.",
            "sound": "Increases the maximum number of simultaneous audio channels. Values above 64 may cause crashes.",
            "loot": "Reverses the auto-loot behavior so you always auto-loot, and hold Shift for manual looting.",
            "bg_sound": "Allows game sounds to continue playing while the game is minimized or in the background.",
            "laa": "Patches the executable to be Large Address Aware, allowing the 32-bit client to utilize up to 4GB of RAM (Essential for HD Mods).",
            "cam_fix": "Fixes a bug where right-clicking and dragging to rotate the camera occasionally snaps your view in a random direction.",
            "dep_fix": "Disables Data Execution Prevention (DEP) and EmulateAtlThunks for WoW_Modernized.exe. Prevents Windows from force-closing the game due to memory hooks. (Prompts for Admin Privileges).",
            "script_memory": "Sets WoW's AddOn Script Memory to 0 (unlimited). When disabled, the tool leaves your existing Config.wtf value unchanged.",
            "crossfaction_res": "Allows the client to attempt resurrection of released cross-faction players.",
            "custom_glues": "Enables custom GlueXML frames and XML on the login and character-selection screens.",
            "bluemoon": "Restores the rare blue moon visual effect that appears around 1 AM on some nights."
        }

        # Basic Setup Variables
        self.wow_dir = tk.StringVar()
        self.rendering_mode = tk.StringVar(value="directx9")
        self.install_autologin = tk.BooleanVar(value=True)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.detected_ratio = self.screen_w / self.screen_h

        self.ratio_options = {
            f"Auto-detected ({self.screen_w}x{self.screen_h})": self.detected_ratio,
            "4:3 (Standard)": 4.0/3.0,
            "16:9 (Widescreen)": 16.0/9.0,
            "16:10 (Widescreen)": 16.0/10.0,
            "21:9 (Ultrawide)": 21.0/9.0,
            "32:9 (Super Ultrawide)": 32.0/9.0
        }

        # Recommended core plugins, kept in the same order as the UI.
        self.core_plugins = {
            "nampower.dll": tk.BooleanVar(value=True),
            "UnitXP_SP3.dll": tk.BooleanVar(value=True),
            "SuperWoWhook.dll": tk.BooleanVar(value=True),
            "transmogfix.dll": tk.BooleanVar(value=True),
            "perf_boost.dll": tk.BooleanVar(value=True),
            "weirdperformance.dll": tk.BooleanVar(value=True),
            "VanillaHelpers.dll": tk.BooleanVar(value=True)
        }

        # Optional client fixes and WeirdUtils.
        self.optional_plugins = {
            "no1600x1200.dll": tk.BooleanVar(value=False),
            "bigcursor.dll": tk.BooleanVar(value=False),
            "customassets.dll": tk.BooleanVar(value=False),
            "logsessions.dll": tk.BooleanVar(value=False),
            "minimapicons.dll": tk.BooleanVar(value=False),
            "pngscreenshots.dll": tk.BooleanVar(value=False),
            "worldmarkers.dll": tk.BooleanVar(value=False)
        }

        self.addon_dependencies = {
            "nampower.dll": "nampowersettings",
            "perf_boost.dll": "perfboostsettings",
            "UnitXP_SP3.dll": "UnitXP_SP3_Addon",
            "SuperWoWhook.dll": "SuperAPI"
        }

        # Vanilla Tweaks Variables 
        self.vt_fov = tk.DoubleVar()
        self.ratio_var = tk.StringVar(value=list(self.ratio_options.keys())[0]) 
        self.vt_farclip = tk.IntVar(value=777)
        self.vt_frill = tk.IntVar(value=300)
        self.vt_nameplate = tk.IntVar(value=41)
        self.vt_soundchan = tk.IntVar(value=64)
        self.vt_maxcam = tk.IntVar(value=100)
        
        # Tweak Toggles 
        self.vt_quickloot = tk.BooleanVar(value=True)
        self.vt_bg_sound = tk.BooleanVar(value=True)
        self.vt_laa = tk.BooleanVar(value=True)
        self.vt_cam_fix = tk.BooleanVar(value=True)
        self.vt_dep_fix = tk.BooleanVar(value=True)
        self.vt_script_memory = tk.BooleanVar(value=True)
        self.vt_crossfaction_res = tk.BooleanVar(value=False)
        self.vt_custom_glues = tk.BooleanVar(value=True)
        self.vt_bluemoon = tk.BooleanVar(value=False)
        
        # Safety Limit Toggle
        self.safety_override = tk.BooleanVar(value=False)
        self.slider_widgets =[] 

        self.on_ratio_change() 
        self.build_ui()

    def on_ratio_change(self, event=None):
        selection = self.ratio_var.get()
        ratio = self.ratio_options.get(selection, 4.0/3.0)
        default_ar, default_fov = 4.0 / 3.0, 1.570796
        fov = 2 * math.atan((ratio / default_ar) * math.tan(default_fov / 2))
        self.vt_fov.set(round(fov, 4))

    def toggle_safety_limits(self):
        override = self.safety_override.get()
        for scale, safe_max, extreme_max, var in self.slider_widgets:
            if override:
                scale.configure(to=extreme_max)
            else:
                scale.configure(to=safe_max)
                try:
                    if var.get() > safe_max:
                        var.set(safe_max)
                except tk.TclError:
                    pass

    def create_slider_row(self, parent, row, label_text, var, min_val, safe_max, extreme_max, desc_key):
        lbl = ttk.Label(parent, text=label_text)
        lbl.grid(row=row, column=0, sticky='w', pady=5)
        ToolTip(lbl, self.descriptions[desc_key])
        
        current_max = extreme_max if self.safety_override.get() else safe_max

        scale = ttk.Scale(parent, from_=min_val, to=current_max, orient='horizontal', variable=var,
                          command=lambda s, v=var: v.set(int(float(s))))
        scale.grid(row=row, column=1, sticky='ew', padx=15, pady=5)
        
        entry = ttk.Entry(parent, textvariable=var, width=8)
        entry.grid(row=row, column=2, sticky='e', pady=5)

        self.slider_widgets.append((scale, safe_max, extreme_max, var))
        return lbl, scale, entry

    def build_ui(self):
        help_banner = tk.Label(
            self.root,
            text="💡  HOVER FOR HELP — Move your mouse over any setting or plugin to see what it does.",
            background="#EAF4FF",
            foreground="#005A9E",
            font=("Segoe UI", 10, "bold"),
            relief="solid",
            borderwidth=1,
            padx=10,
            pady=6,
        )
        help_banner.pack(fill="x", padx=10, pady=(8, 2))

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=(5, 10))

        tab_main = ttk.Frame(notebook)
        tab_plugins = ttk.Frame(notebook)
        tab_tweaks = ttk.Frame(notebook)
        tab_credits = ttk.Frame(notebook)

        notebook.add(tab_main, text="Setup & Rendering")
        notebook.add(tab_plugins, text="Plugins")
        notebook.add(tab_tweaks, text="Vanilla Tweaks")
        notebook.add(tab_credits, text="Credits & Sources")

        self.build_main_tab(tab_main)
        self.build_plugins_tab(tab_plugins)
        self.build_tweaks_tab(tab_tweaks)
        self.build_credits_tab(tab_credits)

        ttk.Button(self.root, text="Apply Setup & Tweaks", command=self.run_installation, style="Accent.TButton").pack(pady=10, fill='x', padx=20)

    def build_main_tab(self, parent):
        ttk.Label(parent, text="Vanilla 1.12 Installation Directory:").pack(anchor='w', pady=(10, 0), padx=10)
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill='x', padx=10, pady=5)
        ttk.Entry(dir_frame, textvariable=self.wow_dir).pack(side='left', fill='x', expand=True)
        ttk.Button(dir_frame, text="Browse...", command=lambda: self.wow_dir.set(filedialog.askdirectory())).pack(side='left', padx=(5,0))

        ttk.Label(parent, text="Rendering Mode:").pack(anchor='w', pady=(20, 0), padx=10)
        
        rb_directx9 = ttk.Radiobutton(
            parent,
            text="VanillaFixes (DirectX 9)",
            variable=self.rendering_mode,
            value="directx9"
        )
        rb_directx9.pack(anchor='w', padx=20, pady=2)
        ToolTip(rb_directx9, self.descriptions["render_directx9"])

        rb_dxvk = ttk.Radiobutton(
            parent,
            text="VanillaFixes + DXVK (Vulkan)",
            variable=self.rendering_mode,
            value="dxvk"
        )
        rb_dxvk.pack(anchor='w', padx=20, pady=2)
        ToolTip(rb_dxvk, self.descriptions["render_dxvk"])

        ttk.Label(parent, text="Optional Mods:").pack(anchor='w', pady=(20, 0), padx=10)
        
        cb_login = ttk.Checkbutton(parent, text="Install Auto Login Mod (Data/Interface/GlueXML)", variable=self.install_autologin)
        cb_login.pack(anchor='w', padx=20, pady=2)
        ToolTip(cb_login, self.descriptions["autologin"])

    def build_plugins_tab(self, parent):
        container = ttk.Frame(parent)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        left_frame = ttk.LabelFrame(container, text="Recommended Core")
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="These are highly recommended for performance\nand client stability.", font=("", 8, "italic")).pack(anchor='w', padx=10, pady=10)
        
        for dll, var in self.core_plugins.items():
            cb = ttk.Checkbutton(left_frame, text=dll, variable=var)
            cb.pack(anchor='w', padx=10, pady=4)
            ToolTip(cb, self.descriptions.get(dll, "")) 

        right_frame = ttk.LabelFrame(container, text="Optional")
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))

        ttk.Label(right_frame, text="Optional client-side fixes and quality-of-life enhancements.", font=("", 8, "italic")).pack(anchor='w', padx=10, pady=10)
        
        for dll, var in self.optional_plugins.items():
            cb = ttk.Checkbutton(right_frame, text=dll, variable=var)
            cb.pack(anchor='w', padx=10, pady=4)
            ToolTip(cb, self.descriptions.get(dll, "")) 

    def _superwow_enabled(self):
        var = self.core_plugins.get("SuperWoWhook.dll")
        return bool(var is not None and var.get())

    def update_superwow_managed_controls(self):
        """Disable vanilla-tweaks controls that SuperWoW already handles."""
        active = self._superwow_enabled()

        if hasattr(self, "superwow_notice"):
            if active:
                self.superwow_notice.configure(
                    text="✓ SuperWoW enabled — FoV, Sound Channels, Auto-loot and Background sounds are handled by SuperWoW. Their vanilla-tweaks patches are skipped.",
                    background="#EAF4FF",
                    foreground="#005A9E",
                )
            else:
                self.superwow_notice.configure(
                    text="SuperWoW disabled — FoV, Sound Channels, Auto-loot and Background sounds are controlled by vanilla-tweaks.",
                    background="#F4F4F4",
                    foreground="#444444",
                )

        if hasattr(self, "fov_ratio_combo"):
            self.fov_ratio_combo.configure(state="disabled" if active else "readonly")
        if hasattr(self, "fov_entry"):
            self.fov_entry.configure(state="disabled" if active else "normal")
        if hasattr(self, "sound_scale"):
            self.sound_scale.configure(state="disabled" if active else "normal")
        if hasattr(self, "sound_entry"):
            self.sound_entry.configure(state="disabled" if active else "normal")
        if hasattr(self, "cb_loot"):
            self.cb_loot.configure(state="disabled" if active else "normal")
        if hasattr(self, "cb_bg"):
            self.cb_bg.configure(state="disabled" if active else "normal")

    def build_tweaks_tab(self, parent):
        self.superwow_notice = tk.Label(
            parent,
            text="",
            background="#EAF4FF",
            foreground="#005A9E",
            font=("Segoe UI", 9, "bold"),
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
            anchor="w",
            justify="left",
            wraplength=620,
        )
        self.superwow_notice.pack(fill="x", padx=10, pady=(5, 2))

        fov_frame = ttk.LabelFrame(parent, text="Field of View (FoV) Calculator")
        fov_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(fov_frame, text="Screen Aspect Ratio:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.fov_ratio_combo = ttk.Combobox(
            fov_frame,
            textvariable=self.ratio_var,
            values=list(self.ratio_options.keys()),
            state="readonly",
            width=28
        )
        self.fov_ratio_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.fov_ratio_combo.bind("<<ComboboxSelected>>", self.on_ratio_change)

        fov_lbl = ttk.Label(fov_frame, text="Calculated FoV (Radians) [Safe Max: 2.268]:")
        fov_lbl.grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ToolTip(fov_lbl, self.descriptions["fov"])
        
        self.fov_entry = ttk.Entry(fov_frame, textvariable=self.vt_fov, width=15)
        self.fov_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

        style = ttk.Style()
        style.configure("Warning.TCheckbutton", foreground="red")
        ttk.Checkbutton(parent, text="Disable Safety Limits (Warning: Exceeding max limits may cause game instability)", 
                        variable=self.safety_override, style="Warning.TCheckbutton",
                        command=self.toggle_safety_limits).pack(anchor='w', padx=15, pady=(0, 5))

        frame_nums = ttk.Frame(parent)
        frame_nums.pack(fill='x', padx=15, pady=0)
        frame_nums.columnconfigure(1, weight=1) 
        
        self.create_slider_row(frame_nums, 0, "Render distance (Farclip) [Safe Max: 1500]:", self.vt_farclip, 777, 1500, 10000, "farclip")
        self.create_slider_row(frame_nums, 1, "Ground clutter (Frilldistance) [Safe Max: 300]:", self.vt_frill, 70, 300, 1000, "frill")
        self.create_slider_row(frame_nums, 2, "Nameplate range [Safe Max: 41]:", self.vt_nameplate, 20, 41, 150, "nameplate")
        self.create_slider_row(frame_nums, 3, "Camera distance [Safe Max: 100]:", self.vt_maxcam, 50, 100, 250, "cam")
        _, self.sound_scale, self.sound_entry = self.create_slider_row(
            frame_nums, 4, "Sound Channels [Safe Max: 64]:",
            self.vt_soundchan, 12, 64, 128, "sound"
        )

        ttk.Label(parent, text="Patch Toggles:").pack(anchor='w', pady=(5,0), padx=10)
        
        toggles_frame = ttk.Frame(parent)
        toggles_frame.pack(fill='x', padx=10)
        
        self.cb_loot = ttk.Checkbutton(toggles_frame, text="Always auto-loot", variable=self.vt_quickloot)
        self.cb_loot.grid(row=0, column=0, sticky='w', padx=10, pady=2)
        ToolTip(self.cb_loot, self.descriptions["loot"])

        self.cb_bg = ttk.Checkbutton(toggles_frame, text="Background sounds", variable=self.vt_bg_sound)
        self.cb_bg.grid(row=0, column=1, sticky='w', padx=10, pady=2)
        ToolTip(self.cb_bg, self.descriptions["bg_sound"])
        
        cb_laa = ttk.Checkbutton(toggles_frame, text="Large Address Aware (LAA)", variable=self.vt_laa)
        cb_laa.grid(row=1, column=0, sticky='w', padx=10, pady=2)
        ToolTip(cb_laa, self.descriptions["laa"])
        
        cb_cam = ttk.Checkbutton(toggles_frame, text="Fix Camera Skip Glitch", variable=self.vt_cam_fix)
        cb_cam.grid(row=1, column=1, sticky='w', padx=10, pady=2)
        ToolTip(cb_cam, self.descriptions["cam_fix"])

        cb_dep = ttk.Checkbutton(toggles_frame, text="Disable DEP (Requires Admin)", variable=self.vt_dep_fix)
        cb_dep.grid(row=2, column=0, sticky='w', padx=10, pady=2)
        ToolTip(cb_dep, self.descriptions["dep_fix"])

        cb_script_memory = ttk.Checkbutton(
            toggles_frame,
            text="Unlimited AddOn Script Memory",
            variable=self.vt_script_memory
        )
        cb_script_memory.grid(row=2, column=1, sticky='w', padx=10, pady=2)
        ToolTip(cb_script_memory, self.descriptions["script_memory"])

        cb_crossfaction = ttk.Checkbutton(
            toggles_frame,
            text="Cross-faction Res Fix",
            variable=self.vt_crossfaction_res
        )
        cb_crossfaction.grid(row=3, column=0, sticky='w', padx=10, pady=2)
        ToolTip(cb_crossfaction, self.descriptions["crossfaction_res"])

        cb_custom_glues = ttk.Checkbutton(
            toggles_frame,
            text="Custom Glues Patch",
            variable=self.vt_custom_glues
        )
        cb_custom_glues.grid(row=3, column=1, sticky='w', padx=10, pady=2)
        ToolTip(cb_custom_glues, self.descriptions["custom_glues"])

        cb_bluemoon = ttk.Checkbutton(
            toggles_frame,
            text="Bluemoon Patch",
            variable=self.vt_bluemoon
        )
        cb_bluemoon.grid(row=4, column=0, sticky='w', padx=10, pady=2)
        ToolTip(cb_bluemoon, self.descriptions["bluemoon"])

        self.update_superwow_managed_controls()


    def build_credits_tab(self, parent):
        # Create a frame with a scrollbar
        frame = ttk.Frame(parent)
        frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side='right', fill='y')

        bg_color = self.root.cget('bg')
        text_area = tk.Text(
            frame,
            wrap='word',
            yscrollcommand=scrollbar.set,
            bg=bg_color,
            relief='flat',
            font=("Segoe UI", 9)
        )
        text_area.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text_area.yview)

        # Configure Text Tags for formatting
        text_area.tag_configure(
            "header",
            font=("Segoe UI", 10, "bold"),
            spacing1=10,
            spacing3=5,
            foreground="#333333"
        )
        text_area.tag_configure("bold", font=("Segoe UI", 9, "bold"))

        # Helper function to create clickable links
        def insert_link(text, url):
            tag_name = f"link_{url}"
            text_area.tag_configure(tag_name, foreground="#005A9E", underline=True)
            text_area.tag_bind(tag_name, "<Button-1>", lambda e, u=url: webbrowser.open_new(u))
            text_area.tag_bind(tag_name, "<Enter>", lambda e: text_area.config(cursor="hand2"))
            text_area.tag_bind(tag_name, "<Leave>", lambda e: text_area.config(cursor="arrow"))
            text_area.insert("end", text, tag_name)

        text_area.insert(
            "end",
            "This modernization tool brings together work from several community projects and developers. "
            "Use the links below to view the original sources, documentation and releases.\n",
            ""
        )

        # Rendering & executable patching
        text_area.insert("end", "\nRendering & Client Patching\n", "header")
        text_area.insert("end", "• VanillaFixes: ", "bold")
        insert_link("Source Repository", "https://github.com/hannesmann/vanillafixes")

        text_area.insert("end", "\n• DXVK: ", "bold")
        insert_link("Source Repository", "https://github.com/doitsujin/dxvk")

        text_area.insert("end", "\n• Vanilla Tweaks: ", "bold")
        insert_link("Source Repository", "https://github.com/tubtubs/vanilla-tweaks")

        # Core engine & API plugins
        text_area.insert("end", "\n\nCore Engine & API Plugins\n", "header")
        text_area.insert("end", "• VanillaHelpers: ", "bold")
        insert_link("Source Repository", "https://github.com/isfir/VanillaHelpers")

        text_area.insert("end", "\n• PerfBoost: ", "bold")
        text_area.insert("end", "by avitasia | ")
        insert_link("Addon Source", "https://gitea.com/avitasia/PerfBoostSettings")

        text_area.insert("end", "\n• UnitXP_SP3: ", "bold")
        insert_link("Source Repository", "https://github.com/brues-code/UnitXP_SP3")
        text_area.insert("end", "  (DLL + UnitXP_SP3_Addon are distributed together in releases)")

        text_area.insert("end", "\n• SuperWoW: ", "bold")
        insert_link("Mod Source", "https://github.com/balakethelock/SuperWoW")
        text_area.insert("end", " | ")
        insert_link("SuperAPI Addon", "https://github.com/balakethelock/SuperAPI")

        text_area.insert("end", "\n• ClassicAPI: ", "bold")
        insert_link("Source Repository", "https://github.com/brues-code/ClassicAPI")

        text_area.insert("end", "\n• AuctionQueryThrottle: ", "bold")
        insert_link("Source Repository", "https://github.com/brues-code/AuctionQueryThrottle")

        text_area.insert("end", "\n• Nampower: ", "bold")
        insert_link("Mod Source", "https://github.com/brues-code/nampower")
        text_area.insert("end", " | ")
        insert_link("Addon Source", "https://github.com/brues-code/NampowerSettings")

        text_area.insert("end", "\n• No1600x1200: ", "bold")
        insert_link("Source / Backup", "https://github.com/RetroCro/TurtleWoW-Mods#no1600x1200")

        text_area.insert("end", "\n• VanillaMultiMonitorFix: ", "bold")
        insert_link("Source Repository", "https://github.com/Mates1500/VanillaMultiMonitorFix")

        text_area.insert("end", "\n• Interact: ", "bold")
        insert_link("Source Repository", "https://github.com/lookino/Interact")

        # Other bundled enhancements
        text_area.insert("end", "\n\nOther Bundled Enhancements\n", "header")
        text_area.insert("end", "• Vanilla-Autologin: ", "bold")
        insert_link("Source Repository", "https://github.com/MarcelineVQ/turtle-autologin")

        # WeirdUtils
        text_area.insert("end", "\n\nWeirdUtils Suite\n", "header")
        text_area.insert(
            "end",
            "The tool bundles or exposes these WeirdUtils modules: "
            "weirdperformance.dll, transmogfix.dll, bigcursor.dll, customassets.dll, "
            "logsessions.dll, minimapicons.dll, pngscreenshots.dll and worldmarkers.dll.\n"
        )
        text_area.insert(
            "end",
            "Some WeirdUtils components are distributed as pre-compiled binaries; see the project page "
            "for documentation and releases.\n\n"
        )
        text_area.insert("end", "• WeirdUtils Documentation & Releases: ", "bold")
        insert_link("Project Repository", "https://codeberg.org/MarcelineVQ/WeirdUtils")

        # This tool
        text_area.insert("end", "\n\nModernization Tool\n", "header")
        text_area.insert("end", "• WoW Modernization Tool: ", "bold")
        insert_link("Project Repository", "https://github.com/Dusk-92/Modernization-Tool")
        text_area.insert("end", "\n")

        # Lock text area to prevent editing
        text_area.config(state='disabled')


    def validate_installation_dir(self, target_dir):
        """Checks if the directory exists and contains necessary WoW components."""
        if not target_dir:
            messagebox.showerror("Directory Error", "Please select a Vanilla 1.12 installation directory.")
            return False

        if not os.path.exists(os.path.join(target_dir, "WoW.exe")) or \
           not os.path.isdir(os.path.join(target_dir, "Data")) or \
           not os.path.isdir(os.path.join(target_dir, "Interface")):
            
            msg = ("This does not look like a valid Vanilla 1.12 installation directory.\n\n"
                   "Please make sure you are selecting the directory that has the WoW.exe in it.")
            messagebox.showerror("Invalid Directory", msg)
            return False
            
        return True

    def validate_limits(self):
        if self.safety_override.get():
            return True 
            
        try:
            if self.vt_farclip.get() > 1500:
                messagebox.showerror("Limit Exceeded", "Render distance (Farclip) exceeds the safe limit of 1500.\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
            if self.vt_frill.get() > 300:
                messagebox.showerror("Limit Exceeded", "Ground clutter (Frilldistance) exceeds the safe limit of 300.\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
            if self.vt_nameplate.get() > 41:
                messagebox.showerror("Limit Exceeded", "Nameplate range exceeds the safe limit of 41.\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
            if self.vt_maxcam.get() > 100:
                messagebox.showerror("Limit Exceeded", "Camera distance exceeds the safe limit of 100.\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
            if self.vt_soundchan.get() > 64:
                messagebox.showerror("Limit Exceeded", "Sound Channels exceed the safe limit of 64.\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
            if self.vt_fov.get() > 2.2689: 
                messagebox.showerror("Limit Exceeded", "Field of View exceeds the safe limit of 130 degrees (2.2689 radians).\n\nPlease lower it, or check 'Disable Safety Limits' to bypass.")
                return False
        except tk.TclError:
            messagebox.showerror("Input Error", "Please ensure all Tweak fields contain valid numbers.")
            return False
            
        return True

    def clean_unselected_files(self, target):
        """Removes managed files/folders if they were explicitly unselected by the user."""
        
        # 1. Clean AutoLogin files if unselected
        if not self.install_autologin.get():
            glue_dir = os.path.join(target, "Data", "Interface", "GlueXML")
            for file_name in ["AutoLogin.lua", "AutoLogin.xml", "GlueXML.toc"]:
                file_path = os.path.join(glue_dir, file_name)
                if os.path.exists(file_path):
                    try: os.remove(file_path)
                    except: pass
            if os.path.exists(glue_dir) and not os.listdir(glue_dir):
                try: os.rmdir(glue_dir)
                except: pass

        # 2. Clean unselected Core Plugins and their dependent AddOns
        for dll_name, var in self.core_plugins.items():
            if not var.get():
                dll_path = os.path.join(target, dll_name)
                if os.path.exists(dll_path):
                    try: os.remove(dll_path)
                    except: pass
                
                addon_folder = self.addon_dependencies.get(dll_name)
                if addon_folder:
                    addon_path = os.path.join(target, "Interface", "AddOns", addon_folder)
                    if os.path.exists(addon_path):
                        shutil.rmtree(addon_path, ignore_errors=True)

        # 3. Clean unselected Optional plugins
        for dll_name, var in self.optional_plugins.items():
            if not var.get():
                dll_path = os.path.join(target, dll_name)
                if os.path.exists(dll_path):
                    try: os.remove(dll_path)
                    except: pass

    def configure_script_memory(self, target):
        """Optionally set AddOn Script Memory to 0 (unlimited) in WTF/Config.wtf."""
        if not self.vt_script_memory.get():
            return

        wtf_dir = os.path.join(target, "WTF")
        config_path = os.path.join(wtf_dir, "Config.wtf")
        original_mode = None
        restore_readonly = False

        try:
            os.makedirs(wtf_dir, exist_ok=True)

            if os.path.exists(config_path):
                original_mode = os.stat(config_path).st_mode
                if not (original_mode & stat.S_IWRITE):
                    os.chmod(config_path, original_mode | stat.S_IWRITE)
                    restore_readonly = True

            existing = ""
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                    existing = f.read()

            setting = 'SET scriptMemory "0"'
            pattern = re.compile(
                r'^\s*SET\s+scriptMemory\s+"[^"]*"\s*$',
                re.IGNORECASE | re.MULTILINE
            )

            if pattern.search(existing):
                updated = pattern.sub(setting, existing)
            else:
                if existing and not existing.endswith(("\n", "\r")):
                    existing += "\n"
                updated = existing + setting + "\n"

            with open(config_path, "w", encoding="utf-8", newline="") as f:
                f.write(updated)

        except PermissionError as exc:
            raise RuntimeError(
                "Windows denied access to WTF\\Config.wtf. Close WoW and any "
                "program using the file. If your WoW folder is protected, run "
                "the Modernization Tool as administrator and try again."
            ) from exc
        finally:
            if restore_readonly and original_mode is not None and os.path.exists(config_path):
                try:
                    os.chmod(config_path, original_mode)
                except OSError:
                    pass


    def apply_process_mitigations(self):
        """Runs the Set-ProcessMitigation PowerShell command with a UAC prompt if needed."""
        if not self.vt_dep_fix.get():
            return
            
        ps_cmd = "Set-ProcessMitigation -Name WoW_Modernized.exe -Disable DEP, EmulateAtlThunks"
        
        # Start-Process with '-Verb RunAs' triggers the Windows Administrator UAC prompt automatically
        full_cmd = f"Start-Process powershell -WindowStyle Hidden -Verb RunAs -ArgumentList \"-Command {ps_cmd}\""
        
        try:
            # Execute the elevation request
            subprocess.run(["powershell", "-Command", full_cmd], creationflags=0x08000000)
        except Exception:
            pass # Fail silently if the user clicks "No" on the Administrator prompt

    def run_installation(self):
        target_dir = self.wow_dir.get()
        
        # 1. Validate Directory
        if not self.validate_installation_dir(target_dir):
            return

        # 2. Validate Bounds
        if not self.validate_limits():
            return

        try:
            self.clean_unselected_files(target_dir)
            self.copy_base_files(target_dir)
            self.configure_dxvk(target_dir)
            self.configure_plugins(target_dir)
            self.run_vanilla_tweaks(target_dir)
            self.configure_script_memory(target_dir)
            self.apply_process_mitigations()
            
            # Generate the seamless launcher shortcut
            self.create_launcher_shortcut(target_dir)
            self.cleanup_legacy_outputs(target_dir)
            
            messagebox.showinfo("Success", "Installation and patching complete!\n\nUse the new 'Play Modernized WoW' shortcut in your directory to launch the game.")
        except PermissionError as e:
            messagebox.showerror(
                "Permission Error",
                "Windows denied access to a file or folder in the selected WoW directory.\n\n"
                "Close WoW and any program using the files. If the folder is protected, "
                "run the Modernization Tool as administrator and try again.\n\n"
                f"Details: {e}"
            )
        except Exception as e:
            messagebox.showerror("Installation Error", str(e))

    def cleanup_legacy_outputs(self, target_dir):
        """Remove executable names produced by older Modernization Tool builds."""
        modernized = os.path.join(target_dir, "WoW_Modernized.exe")
        if not os.path.exists(modernized):
            return

        old_path = os.path.join(target_dir, "WoW_Tweaked.exe")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                # A stale executable being locked should not make an otherwise
                # successful modernization fail.
                pass

    def create_launcher_shortcut(self, target_dir):
        """Automates creating the VanillaFixes shortcut targeting WoW_Modernized.exe"""
        shortcut_path = os.path.join(target_dir, "Play Modernized WoW.lnk")
        vanilla_fixes_exe = os.path.join(target_dir, "VanillaFixes.exe")
        
        # Check for the icon in the setup tool's root directory
        source_icon = os.path.join(get_base_path(), "PurpleWowLogo.ico")
        target_icon = os.path.join(target_dir, "PurpleWowLogo.ico")
        icon_vbs_line = ""
        
        # If the icon exists, copy it to the WoW folder and add it to the shortcut
        if os.path.exists(source_icon):
            try:
                shutil.copy2(source_icon, target_icon)
                icon_vbs_line = f'oLink.IconLocation = "{target_icon}, 0"'
            except Exception:
                pass # Fail silently on icon copy if there's a permission issue

        vbs_script = f"""
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{vanilla_fixes_exe}"
oLink.Arguments = "WoW_Modernized.exe"
oLink.WorkingDirectory = "{target_dir}"
oLink.Description = "Launch Vanilla WoW with VanillaFixes and Tweaks"
{icon_vbs_line}
oLink.Save
"""
        vbs_path = os.path.join(target_dir, "create_shortcut.vbs")
        with open(vbs_path, "w") as f:
            f.write(vbs_script)
            
        try:
            subprocess.run(["cscript", "//nologo", vbs_path], creationflags=0x08000000)
        finally:
            if os.path.exists(vbs_path):
                os.remove(vbs_path)

    def copy_base_files(self, target):
        payload_dir = os.path.join(get_base_path(), "Payload")
        if not os.path.exists(payload_dir): return 
        
        if self.install_autologin.get() and os.path.exists(os.path.join(payload_dir, "Data")):
            shutil.copytree(os.path.join(payload_dir, "Data"), os.path.join(target, "Data"), dirs_exist_ok=True)
        
        if os.path.exists(os.path.join(payload_dir, "Interface")):
            shutil.copytree(os.path.join(payload_dir, "Interface"), os.path.join(target, "Interface"), dirs_exist_ok=True)
            
        # Removed SuperWoWhook.dll from this list!
        for file in ["VanillaFixes.exe", "VfPatcher.dll"]:
            source_file = os.path.join(payload_dir, file)
            if os.path.exists(source_file): shutil.copy2(source_file, target)


    def configure_dxvk(self, target):
        payload_dir = os.path.join(get_base_path(), "Payload")
        d3d9_target = os.path.join(target, "d3d9.dll")
        conf_target = os.path.join(target, "dxvk.conf")

        if self.rendering_mode.get() == "dxvk":
            d3d9_src = os.path.join(payload_dir, "DXVK_Standard", "d3d9.dll")
            conf_src = os.path.join(payload_dir, "dxvk.conf")

            if os.path.exists(d3d9_src):
                shutil.copy2(d3d9_src, d3d9_target)
            if os.path.exists(conf_src):
                shutil.copy2(conf_src, conf_target)
        else:
            for path in (d3d9_target, conf_target):
                if os.path.exists(path):
                    os.remove(path)

    def configure_plugins(self, target):
        payload_base = os.path.join(get_base_path(), "Payload")
        payload_weirdu = os.path.join(payload_base, "WeirdUtils")
        
        dlls_text_lines = []
        if self.rendering_mode.get() == "dxvk":
            dlls_text_lines.append("dxvk")

        # Process Core Plugins
        for dll_name, var in self.core_plugins.items():
            if var.get():
                source_dll = os.path.join(payload_base, dll_name)
                if os.path.exists(source_dll): 
                    shutil.copy2(source_dll, target)
                dlls_text_lines.append(dll_name) 

        # Clean up corresponding addons if their core DLL was UNCHECKED
        for dll_name, addon_folder in self.addon_dependencies.items():
            if not self.core_plugins.get(dll_name, tk.BooleanVar(value=True)).get():
                addon_path = os.path.join(target, "Interface", "AddOns", addon_folder)
                if os.path.exists(addon_path):
                    shutil.rmtree(addon_path, ignore_errors=True)

        # Process Optional Plugins - installed to the game root.
        for dll_name, var in self.optional_plugins.items():
            if var.get():
                source_base = payload_base if dll_name == "no1600x1200.dll" else payload_weirdu
                source_dll = os.path.join(source_base, dll_name)
                if os.path.exists(source_dll):
                    shutil.copy2(source_dll, target)
                dlls_text_lines.append(dll_name)

        # Write active dlls to dlls.txt
        with open(os.path.join(target, "dlls.txt"), "w") as f:
            f.write("\n".join(dlls_text_lines))

    def run_vanilla_tweaks(self, target, tweaks_exe=None, modern_cli=False):
        """Patch a copy of WoW.exe while preserving the original executable."""
        wow_exe = os.path.join(target, "WoW.exe")
        if tweaks_exe is None:
            tweaks_exe = os.path.join(get_base_path(), "vanilla-tweaks.exe")

        if not os.path.exists(tweaks_exe):
            raise FileNotFoundError("vanilla-tweaks.exe was not found.")

        args = [tweaks_exe]
        superwow_active = self._superwow_enabled()

        if modern_cli:
            # tubtubs/vanilla-tweaks keeps these four patches opt-in. When
            # SuperWoW is active, deliberately leave them unpatched.
            if not superwow_active and abs(self.vt_fov.get() - 1.5708) >= 0.0001:
                args.extend(["--fov", str(self.vt_fov.get()), "--fov-patch"])

            if self.vt_farclip.get() == 777:
                args.append("--no-farclip")
            else:
                args.extend(["--farclip", str(self.vt_farclip.get())])

            if self.vt_frill.get() == 70:
                args.append("--no-frilldistance")
            else:
                args.extend(["--frilldistance", str(self.vt_frill.get())])

            if self.vt_nameplate.get() == 20:
                args.append("--no-nameplatedistance")
            else:
                args.extend(["--nameplatedistance", str(self.vt_nameplate.get())])

            if not superwow_active and self.vt_soundchan.get() != 12:
                args.extend([
                    "--soundchannels",
                    str(self.vt_soundchan.get()),
                    "--soundchannels-patch",
                ])

            if self.vt_maxcam.get() != 50:
                args.extend(["--maxcameradistance", str(self.vt_maxcam.get())])

            if not superwow_active and self.vt_quickloot.get():
                args.append("--quickloot")
            if not superwow_active and self.vt_bg_sound.get():
                args.append("--sound-in-background")
            if not self.vt_laa.get():
                args.append("--no-largeaddressaware")
            if not self.vt_cam_fix.get():
                args.append("--no-cameraskipfix")
            if self.vt_crossfaction_res.get():
                args.append("--crossfactionresfix")
            if not self.vt_custom_glues.get():
                args.append("--no-customgluespatch")
            if not self.vt_bluemoon.get():
                args.append("--no-bluemoonpatch")
        else:
            # Legacy bundled brndd patcher enables these older patches by
            # default, so explicitly disable all four when SuperWoW handles them.
            if superwow_active:
                args.extend([
                    "--no-fov",
                    "--no-soundchannels",
                    "--no-quickloot",
                    "--no-sound-in-background",
                ])
            else:
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

            if self.vt_farclip.get() == 777:
                args.append("--no-farclip")
            else:
                args.extend(["--farclip", str(self.vt_farclip.get())])

            if self.vt_frill.get() == 70:
                args.append("--no-frilldistance")
            else:
                args.extend(["--frilldistance", str(self.vt_frill.get())])

            if self.vt_nameplate.get() == 20:
                args.append("--no-nameplatedistance")
            else:
                args.extend(["--nameplatedistance", str(self.vt_nameplate.get())])

            if self.vt_maxcam.get() != 50:
                args.extend(["--maxcameradistance", str(self.vt_maxcam.get())])

            if not self.vt_laa.get():
                args.append("--no-largeaddressaware")
            if not self.vt_cam_fix.get():
                args.append("--no-cameraskipfix")

        args.extend(["-o", os.path.join(target, "WoW_Modernized.exe")])
        args.append(wow_exe)
        subprocess.run(args, check=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = WowSetupTool(root)
    root.mainloop()
