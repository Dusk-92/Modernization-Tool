# 🛠️ WoW Modernization Tool

[![Build Windows EXE](https://github.com/Dusk-92/Modernization-Tool/actions/workflows/build.yml/badge.svg)](https://github.com/Dusk-92/Modernization-Tool/actions/workflows/build.yml)
[![Latest Release](https://img.shields.io/github/v/release/Dusk-92/Modernization-Tool)](https://github.com/Dusk-92/Modernization-Tool/releases/latest)

A simple all-in-one setup tool for **Vanilla WoW 1.12 compatible clients**.

Modernization Tool installs and configures client fixes, performance plugins, Vanilla Tweaks, DXVK and optional visual/audio improvements without requiring users to manually manage DLLs or configuration files.

> 💡 Hover over any setting inside the tool to see an explanation of what it does.

---

## ⬇️ Download

Download the latest version from:

**[GitHub Releases](https://github.com/Dusk-92/Modernization-Tool/releases/latest)**

Current major release: **v2.2**

No installation is required. Download and run:

`WoW_Modernization_Tool.exe`

---

## 🚀 Quick Start

1. Launch **WoW_Modernization_Tool.exe**
2. Select your Vanilla WoW game folder.
3. Choose your renderer, plugins and optional tweaks.
4. Click **Apply Setup & Tweaks**.
5. Launch the game using **Play Modernized WoW**.

The launcher shortcut is automatically created:

- 📁 inside your WoW folder
- 🖥️ on your Windows Desktop

> ⚠️ Use **Play Modernized WoW** to launch the modernized client.

---

# 🎮 Rendering

Two rendering modes are available:

### VanillaFixes — DirectX 9

The default option.

Uses WoW's native DirectX 9 renderer together with VanillaFixes.

### VanillaFixes + DXVK — Vulkan

Uses DXVK to translate DirectX 9 to Vulkan.

The bundled version is currently:

**DXVK 2.6.1 x86**

Existing custom DirectX wrapper files are backed up rather than blindly deleted when switching renderers.

---

# 🧩 Client Plugins

## Recommended Core

The tool can install and configure several recommended client extensions:

- **Nampower** — improves spell responsiveness and latency handling.
- **UnitXP_SP3** — adds networking, targeting, Lua and client improvements.
- **SuperWoW** — expands the Vanilla Lua API and improves addon compatibility.
- **TransmogFix** — prevents performance drops caused by rapid appearance updates.
- **PerfBoost** — provides additional unit rendering/performance controls.
- **WeirdPerformance** — lightweight client optimizations aimed at improving FPS and reducing UI memory leaks for smoother gameplay.
- **VanillaHelpers** — extends several Vanilla client limits.
- **ClassicAPI** — adds newer WoW API functions for compatible addons.
- **AuctionQueryThrottle** — removes the fixed delay between Auction House queries.

## Optional Plugins

Optional client-side improvements include:

- **VanillaMultiMonitorFix** — improved resolution, refresh-rate and monitor detection.
- **Interact** — adds a modern Interact key for NPCs, objects, gathering nodes and loot.
- **No1600x1200** — fixes the old Vanilla resolution limitation on some systems.
- **BigCursor** — upscales the hardware cursor for better visibility on modern high-resolution displays without sacrificing sharpness.
- **CustomAssets** — allows loose game files to be loaded directly from the `Data/` folder and supports custom multi-character patch names without repacking MPQ archives.
- **LogSessions** — automatically organizes combat and chat logs into clean per-character, per-day files when you log in.
- **MinimapIcons** — adds TBC/WotLK-style minimap tracking icons for NPCs and game objects, with a combined tracking menu and saved preferences.
- **PNG Screenshots** — saves screenshots as compressed PNG files instead of the default uncompressed TGA format, using background processing to minimize frame-time impact.
- **WorldMarkers** — lets party or raid leaders place up to five animated, Cataclysm-style colored world markers for positioning and tactical planning.
- **Discord Rich Presence** — installs and keeps **WowPresence** up to date from [Dusk-92/WowPresence](https://github.com/Dusk-92/WowPresence). The Tool preconfigures the OctoWoW Discord Application ID and lets you choose which character details are shown on Discord, including **Name, Guild, Race, Faction, Class, Level and Zone**. Custom Discord Application IDs are preserved across updates.

---

# ⚙️ Vanilla Tweaks

Modernization Tool integrates the modern **tubtubs/vanilla-tweaks** patcher.

Available settings include:

- Field of View
- Render Distance
- Ground Clutter Distance
- Nameplate Distance
- Camera Distance
- Sound Channels
- Always Auto-Loot
- Background Sounds
- Large Address Aware
- Camera Skip Fix
- DEP compatibility
- Unlimited AddOn Script Memory
- Cross-Faction Resurrection Fix
- Custom Glues Patch
- Automatic WDB management

When **SuperWoW** already provides a feature, the equivalent vanilla-tweaks patch is automatically skipped to avoid duplicate modifications.

---

# 🌙 Visual Mods

Optional visual modifications are available directly from the tool:

- **Bluemoon Patch** — restores the rare blue moon effect.
- **Darker Nights** — darker and more atmospheric nights.
- **Pretty Night Sky** — improved starry night sky.
- **Epoch Water** — alternative water textures.
- **Fog Pushback** — moves environmental fog farther away.
- **Pink Herbs** — makes herb nodes much easier to spot.

All visual mods are **disabled by default**.

---

# 🔊 Audio Mods

Optional sound replacements include:

- **NoErrorSounds** — removes repetitive error/fizzle and interface sounds.
- **FishPing** — replaces the fishing bite sound with a clearer ping.
- **Warlock Muted Demons** — mutes repetitive Warlock demon voice lines.

All audio mods are **disabled by default**.

---

# 🔄 Automatic Updates & Offline Fallbacks

Supported components are downloaded directly from their upstream projects when possible.

Modernization Tool is designed to avoid breaking an existing installation if an online source becomes unavailable.

Depending on the component, the tool can:

- keep an already installed valid version;
- use a bundled known-good fallback where redistribution terms allow it;
- avoid re-downloading files that are already current.

**SuperWoW and SuperAPI are upstream-only:** SuperWoW is downloaded from its
official stable release and SuperAPI follows the current upstream `master`
revision. They are not bundled as offline fallbacks, so a first-time SuperWoW
installation requires network access.

**No1600x1200 uses the bundled known-good copy** instead of following the
RetroCro archive repository automatically.

Downloaded and bundled DLLs are validated before installation.

---

# 💾 Safe Configuration Management

Modernization Tool remembers settings separately for each WoW installation.

It also:

- preserves manually added `dlls.txt` entries;
- preserves comments and unknown DLL entries;
- detects incompatible plugin combinations;
- validates the selected Vanilla client before modifying it;
- performs important file replacements transactionally;
- protects unknown/custom renderer files;
- safely manages WDB ownership.

---

# 🔐 AutoLogin

AutoLogin can optionally save account and character shortcuts on the login screen.

When **AutoLogin + Nampower** are enabled together, Modernization Tool automatically creates or reuses the Windows user encryption key required by Nampower.

Password encryption is enabled by default when available.

Existing encryption keys are never replaced.

> 🔒 Your encryption key is stored in the Windows user environment and is not written to the WoW folder.

---

# 📝 Updating Modernization Tool

Updating from an older version does **not** require reinstalling WoW.

Simply:

1. Download the latest Modernization Tool release.
2. Select your existing WoW folder.
3. Review your settings.
4. Click **Apply Setup & Tweaks** again.

Your per-installation settings will be restored automatically.

---

# 🛡️ Antivirus Notice

Because Modernization Tool modifies a game executable and installs client-side DLL plugins, some antivirus products may flag the executable or some included components.

Always download Modernization Tool from the official GitHub Releases page.

---

# 🔗 Useful Links

- **[Latest Release](https://github.com/Dusk-92/Modernization-Tool/releases/latest)**
- **[v2.2 Release Notes](https://github.com/Dusk-92/Modernization-Tool/releases/tag/v2.2)**
- **[OctoWoW Installation & Modernization Guide](https://octowow.st/forum/viewtopic.php?t=831)**

---

# ❤️ Credits

Modernization Tool brings together work from several community projects and developers.

## Rendering & Client Patching

- [VanillaFixes](https://github.com/hannesmann/vanillafixes)
- [DXVK](https://github.com/doitsujin/dxvk)
- [vanilla-tweaks](https://github.com/tubtubs/vanilla-tweaks)

## Core Engine & API Plugins

- [VanillaHelpers](https://github.com/isfir/VanillaHelpers)
- [PerfBoost Settings](https://gitea.com/avitasia/PerfBoostSettings)
- [UnitXP_SP3](https://github.com/brues-code/UnitXP_SP3)
- [SuperWoW](https://github.com/balakethelock/SuperWoW)
- [SuperAPI](https://github.com/balakethelock/SuperAPI)
- [ClassicAPI](https://github.com/brues-code/ClassicAPI)
- [AuctionQueryThrottle](https://github.com/brues-code/AuctionQueryThrottle)
- [Nampower](https://github.com/brues-code/nampower)
- [NampowerSettings](https://github.com/brues-code/NampowerSettings)
- [No1600x1200](https://github.com/RetroCro/TurtleWoW-Mods#no1600x1200)
- [VanillaMultiMonitorFix](https://github.com/Mates1500/VanillaMultiMonitorFix)
- [Interact](https://github.com/lookino/Interact)
- [WowPresence](https://github.com/Dusk-92/WowPresence)

## Visual & Audio Mods

- [Bluemoon Patch via vanilla-tweaks](https://github.com/tubtubs/vanilla-tweaks)
- [Darker Nights — Project Reforged](https://projectreforged.github.io/vanilla/downloads/turtle/)
- [Pretty Night Sky / Epoch Water / Fog Pushback — RetroCro TurtleWoW Mods](https://github.com/RetroCro/TurtleWoW-Mods)
- [Pink Herbs](https://github.com/seacrabsam/patch-herb)
- [NoErrorSounds](https://github.com/Macumbafeh/NoErrorSounds)
- [FishPing](https://github.com/notsureawake/FishPing)
- [Warlock Muted Demons](https://github.com/spzilyk/Warlock-Muted-Demons)
- [Automatic WDB management guide](https://github.com/RetroCro/TurtleWoW-Mods#automatically-clear-wdb-folder-every-time-you-launch-turtle-wow)

## Other Bundled Enhancements

- [Vanilla AutoLogin](https://github.com/MarcelineVQ/turtle-autologin)
- [WeirdUtils](https://codeberg.org/Dusk92/WeirdUtils)

Additional attribution and source links are available directly in the **Credits** tab of Modernization Tool.

---

## 🧾 Licensing & Provenance

Modernization Tool is an independent community project. Third-party components
retain their own licenses, permissions, and trademarks.

For detailed redistribution and provenance information, see:

- [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
- [PROJECT_IDENTITY.md](PROJECT_IDENTITY.md)
- [Docs/BINARY_PROVENANCE.md](Docs/BINARY_PROVENANCE.md)
- [Docs/ASSET_PROVENANCE.md](Docs/ASSET_PROVENANCE.md)
- [LICENSES/](LICENSES/)

SuperWoW and the current SuperAPI master revision are downloaded directly from
their upstream projects and are not bundled as offline fallbacks.

---

## Disclaimer

Modernization Tool is a community project and is not affiliated with or endorsed by Blizzard Entertainment.

World of Warcraft and Warcraft are trademarks of Blizzard Entertainment.
