# Modernization Tool asset provenance

Audit date: 2026-08-31

This document tracks project branding and game-facing non-binary assets that
need provenance separate from software DLL/EXE licensing.

## Project icon

### `PurpleWowLogo.ico`

- Git blob SHA-1:
  `7285e997cb6d635101d0d000867af75878894719`
- Current use: PyInstaller application icon and bundled application resource
- Provenance status: **unresolved-project-branding-asset**

The file name suggests World of Warcraft-themed branding, but this audit did
not establish its original creator or source license. No claim is made that
Modernization Tool owns any Blizzard logo, trademark, or underlying game art
that may be represented by the icon.

Until provenance is confirmed, the project should avoid representing the icon
as an official Blizzard asset or as evidence of Blizzard affiliation.

## AutoLogin GlueXML files

Source reference:

- https://github.com/MarcelineVQ/turtle-autologin

Current comparison:

| File | Status | Current Git blob SHA-1 |
| --- | --- | --- |
| `Payload/Data/Interface/GlueXML/AutoLogin.xml` | exact upstream Git blob match | `65c7d0c08ba62ad9b1630aae6faa0046f96295d1` |
| `Payload/Data/Interface/GlueXML/GlueXML.toc` | exact upstream Git blob match | `11ab97c6dc64385c2c8d717d0182fbee538484ff` |
| `Payload/Data/Interface/GlueXML/AutoLogin.lua` | modified upstream-derived variant | `1de856864a16399977e6220714bd1249da0dcefe` |

The upstream `AutoLogin.lua` Git blob observed during the audit was
`979af097982379ca14e4266dfea41f65452a9561`. The Modernization Tool variant
contains additional secure-default behavior and therefore is not byte-identical.

The source repository did not expose a project-wide license file during this
audit, so this provenance record does not itself establish redistribution
permission.

## Audio and visual mods

The tool may bundle or download visual/audio replacements from community
projects. Their source URLs and many exact file hashes are recorded in
`Payload/Fallback/versions.json`.

Game-facing media can have rights separate from the software that installs it.
Do not infer that an MIT/GPL/BSD license covering installer code automatically
covers Blizzard artwork, sounds, or other game assets.

## Trademark boundary

World of Warcraft, Warcraft, Blizzard Entertainment, and associated logos,
names, artwork, audio, client files, and game assets remain the property of
their respective rights holders.

Modernization Tool is an independent community project and does not claim
official status or endorsement.
