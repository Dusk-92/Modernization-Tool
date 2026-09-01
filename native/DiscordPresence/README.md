# Discord Presence test component

This test branch builds two 32-bit native Windows components:

- `DiscordPresence.dll` — loaded by VanillaFixes; reads WoW 1.12.1 character state read-only, writes the status snapshot, and starts the companion from its worker thread after WoW startup.
- `DiscordPresence.exe` — invisible companion that only reads the status file and talks to Discord IPC. It no longer launches WoW.

The normal game launch path stays unchanged:

```
Play Modernized WoW
  -> VanillaFixes.exe WoW_Modernized.exe
  -> WoW_Modernized.exe
  -> DiscordPresence.dll
  -> DiscordPresence.exe
```

The OctoWoW Discord Application ID is built into `DiscordPresence.exe`:

```
1544072796098011176
```

No manual Application ID setup is required. Advanced users may optionally create a
`discord_application_id` text file to override the built-in ID.

Runtime data is stored under:

```
<WoW folder>\.modernization_tool\DiscordPresence\
  discord_wow_status.json
  discord_broadcast_flags
  DiscordPresence.log
  discord_application_id   (optional override)
```

The companion is never launched from `DllMain`; it is started only from the DLL worker
thread after the startup delay. The DLL never performs Discord IPC, and the companion
never reads or writes WoW memory.

## OctoWoW race mapping

For OctoWoW, the helper treats:

- race id 9 as `Goblin` / Horde
- race id 10 as `High Elf` / Alliance
- race id 16 as a `High Elf` / Alliance compatibility fallback

The companion reads the `race` field from `discord_wow_status.json` and includes it in
Rich Presence details, e.g. `Lvl 1 Priest · High Elf · Alliance`.


## Independent sampler implementation

The WoW memory sampler is implemented in this repository with its own internal
organization. It preserves the existing runtime contract (same status JSON,
broadcast flags, timings, read-only memory access, and exact-PID companion
startup) so DiscordPresence.exe does not need to change.

The client addresses/field offsets are compatibility data for WoW 1.12.1 build
5875. IchaLaunch remains credited as an earlier Rich Presence implementation
that inspired this integration; its source code is not bundled here.
