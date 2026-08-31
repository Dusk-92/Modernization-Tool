# Discord Presence test component

This test branch builds two 32-bit native Windows components:

- `DiscordPresence.dll` — loaded by VanillaFixes; reads WoW 1.12.1 character state read-only.
- `DiscordPresence.exe` — invisible companion that launches `VanillaFixes.exe WoW_Modernized.exe`, reads the status file, and talks to Discord IPC.

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

The DLL never connects to Discord. The companion never reads or writes WoW memory.
