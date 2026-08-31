# Modernization Tool third-party notices

Audit date: 2026-08-31

Modernization Tool combines an original installer/configuration layer with
third-party client fixes, patchers, addons, DLLs, visual/audio modifications,
and external download sources.

This document records the currently known licensing and distribution boundary.
It does not replace upstream licenses or grant rights that the upstream authors
did not grant.

## Project-owned material

Original Modernization Tool code and documentation authored by Dusk-92 are
covered by the project notice in `LICENSE`.

Third-party material is excluded from that project notice and remains under its
own terms.

## Bundled components with a verified redistribution license

The following bundled components have a license text that was located and
preserved during this audit:

### VanillaFixes

- Source: https://github.com/hannesmann/vanillafixes
- Bundled files include `Payload/VanillaFixes.exe` and
  `Payload/VfPatcher.dll`
- License: MIT
- Preserved as `LICENSES/VanillaFixes-MIT.txt`

### DXVK

- Source: https://github.com/doitsujin/dxvk
- Bundled file: `Payload/DXVK_Standard/d3d9.dll`
- License: zlib/libpng
- Preserved as `LICENSES/DXVK-zlib.txt`

### vanilla-tweaks

- Source: https://github.com/tubtubs/vanilla-tweaks
- Bundled fallback: `vanilla-tweaks.exe`
- License: MIT
- Preserved as `LICENSES/vanilla-tweaks-MIT.txt`

### Nampower

- Source: https://github.com/brues-code/nampower
- Bundled fallback: `Payload/nampower.dll`
- License: BSD-style two-clause redistribution terms
- Preserved as `LICENSES/Nampower-BSD.txt`

### VanillaHelpers

- Source: https://github.com/isfir/VanillaHelpers
- Bundled fallback: `Payload/VanillaHelpers.dll`
- Upstream carries GNU GPL v3 and GNU LGPL v3 license documents
- Preserved as `LICENSES/VanillaHelpers-GPL-3.0.txt` and
  `LICENSES/VanillaHelpers-LGPL-3.0.txt`

### VanillaMultiMonitorFix

- Source: https://github.com/Mates1500/VanillaMultiMonitorFix
- Bundled offline fallback under `Payload/Fallback/VanillaMultiMonitorFix/`
- License: MIT
- Preserved as `LICENSES/VanillaMultiMonitorFix-MIT.txt`

## SuperWoW and SuperAPI: upstream-only distribution

SuperWoW's current upstream license states that distribution is prohibited
without the copyright holder's express written permission.

Because no written redistribution authorization is documented in this
repository, Modernization Tool no longer bundles `SuperWoWhook.dll` as an
offline fallback. The tool already downloads SuperWoW directly from the
official upstream release when the user enables it.

- SuperWoW source: https://github.com/balakethelock/SuperWoW
- License copy: `LICENSES/SuperWoW-LICENSE.txt`
- Distribution mode: downloaded from upstream at install time; not bundled

SuperAPI is likewise downloaded directly from its upstream repository as part
of the SuperWoW installation path and is no longer kept as a bundled fallback.

- SuperAPI source: https://github.com/balakethelock/SuperAPI
- Distribution mode: downloaded from upstream at install time; not bundled

If the upstream download is unavailable, an already complete installed
SuperWoW/SuperAPI setup may be kept by the tool, but a new offline installation
cannot use a bundled SuperWoW fallback.

## Components whose redistribution license was not independently located

The following source projects or fallback sources did not expose a project-wide
license file that could be independently verified during this audit, or their
license status still needs a dedicated provenance review:

- UnitXP_SP3 — https://github.com/brues-code/UnitXP_SP3
- Interact — https://github.com/lookino/Interact
- RetroCro/TurtleWoW-Mods sources used for No1600x1200 and PerfBoost
- FishPing — https://github.com/notsureawake/FishPing
- NoErrorSounds — https://github.com/Macumbafeh/NoErrorSounds
- Warlock Muted Demons — https://github.com/spzilyk/Warlock-Muted-Demons
- Vanilla AutoLogin — https://github.com/MarcelineVQ/turtle-autologin
- WeirdUtils releases referenced by the payload provenance manifest

Their source locations and hashes remain documented in
`Payload/Fallback/versions.json` and/or `Docs/BINARY_PROVENANCE.md`.

The absence of a verified license in this audit must not be interpreted as a
grant of redistribution rights. If explicit permission or an upstream license
is later confirmed, preserve that evidence in `LICENSES/` and update this
notice.

## ClassicAPI and AuctionQueryThrottle

Modernization Tool downloads current releases of ClassicAPI and
AuctionQueryThrottle from their official upstream repositories and also
currently retains known-good fallback binaries.

Both upstream repositories carry GNU GPL v3 license documents. Their licensing
and source locations should be preserved alongside any redistributed fallback
binaries. A copy of the GPL v3 text is stored in
`LICENSES/GPL-3.0.txt`.

- ClassicAPI: https://github.com/brues-code/ClassicAPI
- AuctionQueryThrottle: https://github.com/brues-code/AuctionQueryThrottle

## AutoLogin provenance

`Payload/Data/Interface/GlueXML/AutoLogin.xml` and `GlueXML.toc` are
byte-identical at Git blob level to the corresponding files in
`MarcelineVQ/turtle-autologin` at the time of this audit.

`AutoLogin.lua` is a modified variant of that upstream file and includes
Modernization Tool-specific secure-default behavior. This is documented as
adapted third-party material rather than claimed as wholly original.

## Visual and audio material

Visual/audio replacements and game-facing assets may have copyright or
trademark considerations separate from software licenses.

See `Docs/ASSET_PROVENANCE.md` for project branding and game-facing asset
notes. Source paths for bundled audio fallbacks remain recorded in
`Payload/Fallback/versions.json`.

## Blizzard / World of Warcraft

Modernization Tool is unofficial and independent.

World of Warcraft, Warcraft, Blizzard Entertainment, and associated names,
marks, artwork, audio, client files, and game assets remain the property of
their respective rights holders. Nothing in this repository grants additional
rights in those materials.

## Preservation rule

When a bundled component is updated, replaced, or moved to upstream-only
distribution:

1. keep its source URL and version;
2. keep or update the applicable license/permission record;
3. preserve hashes for redistributed binaries where practical;
4. do not remove historical attribution simply because the file is no longer
   bundled.
