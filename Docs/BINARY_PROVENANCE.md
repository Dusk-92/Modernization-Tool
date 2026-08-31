# Modernization Tool binary provenance

Audit date: 2026-08-31

This document is the human-readable companion to
`Payload/Fallback/versions.json`, which contains machine-readable source,
version, SHA-256, and size records for many bundled components.

No remaining payload binary was modified during this provenance pass.

## Distribution status

| Component | Distribution mode after this audit | Source / provenance | License status |
| --- | --- | --- | --- |
| VanillaFixes | bundled + install support | hannesmann/vanillafixes v1.5.3 | MIT verified |
| DXVK | bundled | doitsujin/dxvk v2.6.1 x86 | zlib/libpng verified |
| vanilla-tweaks | bundled fallback + online update | tubtubs/vanilla-tweaks | MIT verified |
| Nampower | bundled fallback + online update | brues-code/nampower v4.6.1 | BSD-style terms verified |
| VanillaHelpers | bundled fallback + online update | isfir/VanillaHelpers v1.1.2 | GPL/LGPL documents verified |
| VanillaMultiMonitorFix | bundled fallback + online update | Mates1500/VanillaMultiMonitorFix 0.2 | MIT verified |
| ClassicAPI | bundled fallback + online update | brues-code/ClassicAPI | GPL v3 verified |
| AuctionQueryThrottle | bundled fallback + online update | brues-code/AuctionQueryThrottle | GPL v3 verified |
| SuperWoW | **upstream-only** | balakethelock/SuperWoW release | redistribution restricted upstream |
| SuperAPI | **upstream-only** | balakethelock/SuperAPI master | no bundled copy after this audit |
| UnitXP_SP3 | bundled fallback + online update | brues-code/UnitXP_SP3 v90 | project-wide license not independently located |
| Interact | bundled fallback + online update | lookino/Interact v1.0.4 | project-wide license not independently located |
| No1600x1200 | bundled fallback + online update | RetroCro/TurtleWoW-Mods | project-wide license not independently located |
| PerfBoost | bundled | RetroCro/TurtleWoW-Mods backup source | project-wide license not independently located |
| WeirdPerformance | bundled | Dusk92/WeirdUtils 0.7.3 | provenance recorded; license record pending |
| WeirdUtils modules | bundled | MarcelineVQ/WeirdUtils releases | provenance recorded; license record pending |
| FishPing | bundled fallback + online source | notsureawake/FishPing | project-wide license not independently located |
| NoErrorSounds | bundled fallback + online source | Macumbafeh/NoErrorSounds | project-wide license not independently located |
| Warlock Muted Demons | bundled fallback + online source | spzilyk/Warlock-Muted-Demons | project-wide license not independently located |

## SuperWoW change

Before this audit the repository contained:

- `Payload/SuperWoWhook.dll`
- SHA-256 recorded in `versions.json`:
  `bd214b32c878649e94ce654835946bd05e0ce7710e8f01bae10d8ab50a89351d`
- source:
  `balakethelock/SuperWoW` release package

That bundled fallback is removed by this audit because the current upstream
license restricts redistribution without express written permission.

The installation feature itself is retained: `remote_packages.install_superwow`
already downloads the official upstream release and downloads SuperAPI directly
from its upstream repository.

## SuperAPI change

The previous bundled fallback under
`Payload/Interface/Addons/SuperAPI/` is removed together with the SuperWoW
fallback. The installer continues to obtain SuperAPI directly from
`balakethelock/SuperAPI` when SuperWoW is installed.

## Hash manifest

For components that remain bundled, the canonical machine-readable hashes are
kept in `Payload/Fallback/versions.json`.

When updating a binary:

1. obtain it from the documented upstream source;
2. verify the version;
3. update the SHA-256 and size;
4. preserve the applicable license/permission;
5. update this document if the distribution mode changes.

## Important boundary

A matching hash proves file identity against the recorded source artifact. It
does not by itself prove that redistribution is licensed. License/permission
status must be tracked separately.
