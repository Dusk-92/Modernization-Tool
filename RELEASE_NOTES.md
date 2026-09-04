# 🛠️ WoW Modernization Tool v2.3

This update focuses on **better compatibility, safer WoW.exe patching and improved recovery**.

## ⚙️ Vanilla Tweaks & Compatibility

- Reworked Vanilla Tweaks handling for better compatibility with **Vanilla, Turtle WoW, OctoWoW and compatible clients**.
- `WoW_Modernized.exe` is now built and validated transactionally before replacing the previous version.
- Vanilla Tweaks now runs before other installation changes.
- Improved support for already-patched clients while preserving client-specific loader code.
- Removed overly strict build/version checks that could reject compatible clients.

## 🎨 MPQ & Recovery

- Improved MPQ validation to reject corrupted or invalid archives.
- Existing valid files can now be preserved when a remote source is temporarily unavailable.
- Improved offline recovery for supported components.
- Better handling of local installation and permission errors.

## 🛡️ Reliability

- Expanded automated tests for installation ordering, recovery and executable patching.
- Improved rollback behavior to reduce the risk of partial installations.

## ✅ Updating from v2.2

Download the new executable, select your existing WoW folder and click **Apply Setup & Tweaks**.

A complete WoW reinstall is not required.
