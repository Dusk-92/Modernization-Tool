# Modernization Tool binary provenance

Audit date: 2026-09-03

This document is the human-readable companion to
`Payload/Fallback/versions.json`, which contains machine-readable source,
version, SHA-256, and size records for many bundled components.

This provenance pass restores the previously recorded SuperWoW fallback and verifies the paired SuperAPI source revision.

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
| SuperWoW | bundled fallback + online update | balakethelock/SuperWoW release 2.2 | redistribution permission reported by the Modernization Tool maintainer on 2026-09-03 |
| SuperAPI | bundled fallback + online update | balakethelock/SuperAPI master | redistribution permission reported by the Modernization Tool maintainer on 2026-09-03 |
| UnitXP_SP3 | bundled fallback + online update | brues-code/UnitXP_SP3 v90 | project-wide license not independently located |
| Interact | bundled fallback + online update | lookino/Interact v1.0.4 | project-wide license not independently located |
| No1600x1200 | **bundled known-good only** | RetroCro/TurtleWoW-Mods archive source | project-wide license not independently located |
| PerfBoost | bundled | RetroCro/TurtleWoW-Mods backup source | project-wide license not independently located |
| WeirdPerformance | bundled | Dusk92/WeirdUtils 0.7.3 | provenance recorded; license record pending |
| WeirdUtils modules | bundled | MarcelineVQ/WeirdUtils releases | provenance recorded; license record pending |
| FishPing | bundled fallback + online source | notsureawake/FishPing | project-wide license not independently located |
| NoErrorSounds | bundled fallback + online source | Macumbafeh/NoErrorSounds | project-wide license not independently located |
| Warlock Muted Demons | bundled fallback + online source | spzilyk/Warlock-Muted-Demons | project-wide license not independently located |
| WowPresence | release-build bundled fallback + online update | Dusk-92/WowPresence v1.3 | project-owned integration; see component notices |

## SuperWoW / SuperAPI fallback

The bundled SuperWoW + SuperAPI fallback has been restored after the
Modernization Tool maintainer reported upstream redistribution permission on
2026-09-03.

The online source remains preferred:

- SuperWoW is resolved from the official stable release;
- SuperAPI follows the current upstream `master` revision and is downloaded
  from the exact resolved commit SHA.

If the online installation fails and there is no complete existing install to
preserve, the tool can install the bundled known-good pair instead.

Bundled fallback provenance:

- `Payload/SuperWoWhook.dll`
- SuperWoW version: 2.2
- SHA-256:
  `bd214b32c878649e94ce654835946bd05e0ce7710e8f01bae10d8ab50a89351d`
- bundled SuperAPI revision:
  `901322dc88890a2ea10610b8228fb43c9c2a3610`
- bundled SuperAPI Git tree:
  `95bb25752b1f31f7d4ca8d5e416986b5e3031b33`

The exact fallback metadata is also recorded in
`Payload/Fallback/versions.json`.

## Hash manifests

For components stored directly in the repository, the canonical
machine-readable hashes are kept in `Payload/Fallback/versions.json`.

WowPresence is prepared as a release-build fallback by
`scripts/prepare_remote_fallbacks.py`. The script validates the release ZIP,
records its size and SHA-256, and writes
`Payload/Fallback/remote_fallbacks.json` before PyInstaller packages it into
the executable. Visual MPQ mods are intentionally not bundled as fallbacks.

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
