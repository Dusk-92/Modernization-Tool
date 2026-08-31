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
