# Discord Presence test component

This test branch builds two 32-bit native Windows components:

- `DiscordPresence.dll` — loaded by VanillaFixes; reads WoW 1.12.1 character state read-only.
- `DiscordPresence.exe` — invisible companion that launches `VanillaFixes.exe WoW_Modernized.exe`, reads the status file, and talks to Discord IPC.

Runtime data is stored under:

```
<WoW folder>\.modernization_tool\DiscordPresence\
  discord_wow_status.json
  discord_broadcast_flags
  discord_application_id
  DiscordPresence.log
```

The DLL never connects to Discord. The companion never reads or writes WoW memory.
