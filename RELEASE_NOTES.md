# 🛠️ WoW Modernization Tool v2.0

This is a major update focused on **easier setup, safer updates, automatic component refreshes and new optional client improvements**.

Existing users do **not** need to reinstall WoW. Select your current game folder, review your options and click **Apply Setup & Tweaks**.

## 🔄 Automatic Updates & Offline Protection

Supported components can now be refreshed directly from their upstream releases when you apply the setup.

If an online update is unavailable, the tool will keep a valid installed version or use a bundled known-good fallback when available. Existing working files are preserved whenever possible instead of being replaced unnecessarily.

## 🎮 Rendering & DXVK

Renderer selection is now simpler:

- **VanillaFixes — DirectX 9** *(default)* — uses WoW's native DirectX 9 renderer.
- **VanillaFixes + DXVK — Vulkan** — translates DirectX 9 to Vulkan and may provide smoother frame pacing on modern systems.

The bundled DXVK version is now **2.6.1 x86** with a configuration aligned with VanillaFixes.

Switching back to DirectX 9 now safely moves unknown existing D3D9 wrapper files out of the WoW root instead of deleting them.

## 🧩 New & Updated Plugins

- **ClassicAPI** — adds newer WoW API functions so compatible modern addons can work on the Vanilla client.
- **AuctionQueryThrottle** — removes the fixed Auction House query delay for much faster searches.
- **VanillaMultiMonitorFix** — improves resolution, refresh-rate and monitor detection on multi-monitor setups.
- **Interact** — adds a modern interaction key for nearby NPCs, objects, gathering nodes and loot.
- **WorldMarkers 0.7.1** — updated optional world-marker support.
- **WeirdPerformance 0.7.3** — updated engine/runtime optimizations for client smoothness and reduced overhead.

## ⚙️ New Client Tweaks

- **Unlimited AddOn Script Memory** — removes WoW's AddOn memory limit.
- **Cross-Faction Resurrection Fix** — improves resurrection handling for released cross-faction players.
- **Custom Glues Patch** — enables custom login and character-selection interface modifications.
- **Automatically Clear WDB** — clears stale WDB cache data and safely manages the WDB blocker.
- **SuperWoW conflict prevention** — equivalent vanilla-tweaks patches are automatically skipped when SuperWoW already handles FoV, Sound Channels, Auto-Loot or Background Sound.

## 🌙 New Visual Mods

All visual mods are optional and disabled by default.

- **Bluemoon Patch** — restores the rare blue moon visual effect.
- **Darker Nights** — makes nighttime environments darker and more atmospheric.
- **Pretty Night Sky** — replaces the Vanilla night sky with a more detailed starry sky.
- **Epoch Water** — replaces the original Vanilla water textures.
- **Fog Pushback** — pushes environmental fog farther away for clearer long-distance visibility.
- **Pink Herbs** — makes herb nodes bright pink/purple so they are easier to spot.

## 🔊 New Audio Mods

All audio mods are optional and disabled by default.

- **NoErrorSounds** — removes many repetitive spell fizzle/error and interface sounds.
- **FishPing** — replaces the fishing bite sound with a much easier-to-hear ping.
- **Warlock Muted Demons** — mutes many repetitive Warlock demon voice lines.

## 🔐 AutoLogin Security Improvements

When **AutoLogin + Nampower** are enabled together, Modernization Tool now automatically creates or reuses the Windows user encryption key required by Nampower.

AutoLogin also enables password encryption by default when encryption is available. Existing user encryption keys are never replaced, and an explicit user choice to disable AutoLogin encryption is preserved.

## 💾 Installer & Safety Improvements

- Settings are remembered separately for each WoW installation.
- Manually added entries and comments in `dlls.txt` are preserved.
- Downloaded/bundled DLLs are validated before installation.
- Important replacements are performed transactionally to reduce the risk of partial installs.
- Existing valid files are kept when an upstream download fails.
- Large visual mods are not re-downloaded when the installed revision is already current.
- Legacy Modernization Tool files are cleaned up safely.
- The selected game folder is validated before changes are made.

## 🚀 Launcher Improvements

After installation, **Play Modernized WoW** is created both:

- in the WoW game folder;
- on the Windows Desktop.

Use either shortcut to launch the modernized client.

## 📦 Notable Bundled / Known-Good Versions

- VanillaFixes **1.5.3**
- DXVK **2.6.1 x86**
- Nampower **4.6.1**
- ClassicAPI **1.12.7**
- AuctionQueryThrottle **1.2.0**
- UnitXP_SP3 **v90**
- SuperWoW **2.2**
- VanillaHelpers **1.1.2**
- WeirdPerformance **0.7.3**
- WorldMarkers **0.7.1**
- VanillaMultiMonitorFix **0.2**
- Interact **1.0.4**

## ✅ Updating from v1.1

Download **WoW_Modernization_Tool.exe**, select your existing WoW installation and click **Apply Setup & Tweaks**.

A complete WoW reinstall is not required.

---

The detailed change list since **v1.1** is generated automatically by GitHub below.
