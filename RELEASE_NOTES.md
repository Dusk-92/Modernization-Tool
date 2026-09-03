# 🛠️ WoW Modernization Tool v2.2

## 🎮 Discord Rich Presence

- Added detailed Discord Rich Presence privacy controls.
- Choose individually whether Discord can display:
  - Character Name
  - Guild
  - Race
  - Faction
  - Class
  - Level
  - Zone
- Added a `Show character details` option to quickly enable all Discord details.
- Updated WowPresence integration for the new privacy system.

## 🔄 Updates & Reliability

- Added smart update checks for remote components.
- Unchanged components are no longer downloaded again on every Apply.
- Modified or missing managed files are automatically detected and repaired.
- Release assets are detected even when an upstream project replaces a file under the same tag.
- Improved vanilla-tweaks update detection to avoid unnecessary downloads and repatching.
- Improved branch-based component downloads to use the exact resolved revision.
- SuperAPI continues to follow upstream `master` while installing the exact detected revision.
- Added integrity checks for bundled components before installation.
- Improved atomic installation of bundled components and dependent addons.
- Improved Nampower and UnitXP addon handling during updates and offline fallback.
- No1600x1200 now uses the bundled known-good version.
- Fixed stale `.modernization-backup-*` files remaining after successful updates.

## ✅ Updating from v2.1

Download the new executable, select your existing WoW folder and click **Apply Setup & Tweaks**.

A complete WoW reinstall is not required.
