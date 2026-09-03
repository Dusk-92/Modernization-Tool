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

### [VanillaFixes](https://github.com/hannesmann/vanillafixes) — DirectX 9

The default option.

Uses WoW's native DirectX 9 renderer together with VanillaFixes.

### VanillaFixes + [DXVK](https://github.com/doitsujin/dxvk) — Vulkan

Uses DXVK to translate DirectX 9 to Vulkan.

DXVK is bundled with the tool and can be selected directly from the renderer options.

Existing custom DirectX wrapper files are backed up rather than blindly deleted when switching renderers.

---

# 🧩 Client Plugins & Sources

## Recommended Core

The tool can install and configure several recommended client extensions:

- **[Nampower](https://github.com/brues-code/nampower)** — improves spell responsiveness and latency handling. Settings addon: [NampowerSettings](https://github.com/brues-code/NampowerSettings).
- **[UnitXP_SP3](https://github.com/brues-code/UnitXP_SP3)** — adds networking, targeting, Lua and client improvements.
- **[SuperWoW](https://github.com/balakethelock/SuperWoW)** — expands the Vanilla Lua API and improves addon compatibility. Its companion API addon is [SuperAPI](https://github.com/balakethelock/SuperAPI).
- **[TransmogFix](https://codeberg.org/MarcelineVQ/WeirdUtils)** — prevents performance drops caused by rapid appearance updates.
- **[PerfBoost](https://github.com/RetroCro/TurtleWoW-Mods)** — provides additional unit rendering/performance controls. Configuration addon: [PerfBoost Settings](https://gitea.com/avitasia/PerfBoostSettings).
- **[WeirdPerformance](https://codeberg.org/Dusk92/WeirdUtils)** — lightweight client optimizations aimed at improving FPS and reducing UI memory leaks for smoother gameplay.
- **[VanillaHelpers](https://github.com/isfir/VanillaHelpers)** — extends several Vanilla client limits.
- **[ClassicAPI](https://github.com/brues-code/ClassicAPI)** — adds newer WoW API functions for compatible addons.
- **[AuctionQueryThrottle](https://github.com/brues-code/AuctionQueryThrottle)** — removes the fixed delay between Auction House queries.

## Optional Plugins

Optional client-side improvements include:

- **[VanillaMultiMonitorFix](https://github.com/Mates1500/VanillaMultiMonitorFix)** — improved resolution, refresh-rate and monitor detection.
- **[Interact](https://github.com/lookino/Interact)** — adds a modern Interact key for NPCs, objects, gathering nodes and loot.
- **[No1600x1200](https://github.com/RetroCro/TurtleWoW-Mods#no1600x1200)** — fixes the old Vanilla resolution limitation on some systems.
- **[BigCursor](https://codeberg.org/MarcelineVQ/WeirdUtils)** — upscales the hardware cursor for better visibility on modern high-resolution displays without sacrificing sharpness.
- **[CustomAssets](https://codeberg.org/MarcelineVQ/WeirdUtils)** — allows loose game files to be loaded directly from the `Data/` folder and supports custom multi-character patch names without repacking MPQ archives.
- **[LogSessions](https://codeberg.org/MarcelineVQ/WeirdUtils)** — automatically organizes combat and chat logs into clean per-character, per-day files when you log in.
- **[MinimapIcons](https://codeberg.org/MarcelineVQ/WeirdUtils)** — adds TBC/WotLK-style minimap tracking icons for NPCs and game objects, with a combined tracking menu and saved preferences.
- **[PNG Screenshots](https://codeberg.org/MarcelineVQ/WeirdUtils)** — saves screenshots as compressed PNG files instead of the default uncompressed TGA format, using background processing to minimize frame-time impact.
- **[WorldMarkers](https://codeberg.org/MarcelineVQ/WeirdUtils)** — lets party or raid leaders place up to five animated, Cataclysm-style colored world markers for positioning and tactical planning.
- **[Discord Rich Presence](https://github.com/Dusk-92/WowPresence)** — installs and keeps **WowPresence** up to date. The Tool preconfigures the OctoWoW Discord Application ID and lets you choose which character details are shown on Discord, including **Name, Guild, Race, Faction, Class, Level and Zone**. Custom Discord Application IDs are preserved across updates.

---

# ⚙️ Vanilla Tweaks

Modernization Tool integrates the modern **[tubtubs/vanilla-tweaks](https://github.com/tubtubs/vanilla-tweaks)** patcher.

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
- [Automatic WDB management](https://github.com/RetroCro/TurtleWoW-Mods#automatically-clear-wdb-folder-every-time-you-launch-turtle-wow)

When **SuperWoW** already provides a feature, the equivalent vanilla-tweaks patch is automatically skipped to avoid duplicate modifications.

---

# 🌙 Visual Mods

Optional visual modifications are available directly from the tool:

- **[Bluemoon Patch](https://github.com/tubtubs/vanilla-tweaks)** — restores the rare blue moon effect.
- **[Darker Nights](https://projectreforged.github.io/vanilla/downloads/turtle/)** — darker and more atmospheric nights.
- **[Pretty Night Sky](https://github.com/RetroCro/TurtleWoW-Mods)** — improved starry night sky.
- **[Epoch Water](https://github.com/RetroCro/TurtleWoW-Mods)** — alternative water textures.
- **[Fog Pushback](https://github.com/RetroCro/TurtleWoW-Mods)** — moves environmental fog farther away.
- **[Pink Herbs](https://github.com/seacrabsam/patch-herb)** — makes herb nodes much easier to spot.

All visual mods are **disabled by default**.

---

# 🔊 Audio Mods

Optional sound replacements include:

- **[NoErrorSounds](https://github.com/Macumbafeh/NoErrorSounds)** — removes repetitive error/fizzle and interface sounds.
- **[FishPing](https://github.com/notsureawake/FishPing)** — replaces the fishing bite sound with a clearer ping.
- **[Warlock Muted Demons](https://github.com/spzilyk/Warlock-Muted-Demons)** — mutes repetitive Warlock demon voice lines.

All audio mods are **disabled by default**.

---

# 🔄 Automatic Updates & Offline Fallbacks

Supported components are downloaded directly from their upstream projects when possible.

Modernization Tool is designed to avoid breaking an existing installation if an online source becomes unavailable.

Depending on the component, the tool can:

- keep an already installed valid version;
- use a bundled known-good fallback where redistribution terms allow it;
- avoid re-downloading files that are already current.

**SuperWoW and SuperAPI prefer their upstream sources:** SuperWoW is downloaded
from its official stable release and SuperAPI follows the current upstream
`master` revision. If either online source is unavailable, the tool can install
the bundled known-good SuperWoW + SuperAPI fallback instead.

**WowPresence and remote visual mods keep a validated local cache.** A successful
download refreshes the cache, while already valid installed files can seed it
when possible. Cache write failures never block a successful normal install.
A completely fresh offline installation of these cache-only components still
requires a cache created by an earlier valid installation.

**No1600x1200 uses the bundled known-good copy** instead of following the
RetroCro archive repository automatically.

Downloaded, cached and bundled DLLs are validated before installation.

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

[Vanilla AutoLogin](https://github.com/MarcelineVQ/turtle-autologin) can optionally save account and character shortcuts on the login screen.

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

Because Modernization Tool creates a patched `WoW_Modernized.exe` and installs client-side DLL plugins, some antivirus products may flag the executable or some included components.

The original `WoW.exe` is not modified in place.

Always download Modernization Tool from the official GitHub Releases page.

---

# 🔗 Useful Links

- **[Latest Release](https://github.com/Dusk-92/Modernization-Tool/releases/latest)**
- **[OctoWoW Installation & Modernization Guide](https://octowow.st/forum/viewtopic.php?t=831)**

---

# ❤️ Credits

Modernization Tool builds on the work of the community projects and developers linked throughout this README.

Thank you to all upstream authors and contributors whose work makes this project possible. Additional attribution is available directly in the **Credits** tab of Modernization Tool.

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

SuperWoW and SuperAPI prefer their upstream projects, with a bundled known-good
pair available as an offline fallback. Other remote components use the fallback
behavior described in **Automatic Updates & Offline Fallbacks** above.

---

## Disclaimer

Modernization Tool is a community project and is not affiliated with or endorsed by Blizzard Entertainment.

World of Warcraft and Warcraft are trademarks of Blizzard Entertainment.
