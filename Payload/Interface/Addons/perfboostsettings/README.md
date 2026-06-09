# <b>If you manually download zip make sure you rename the folder after extracting to PerfBoostSettings instead of perfboostsettings or it won't work</b>


### PerfBoost Settings

A configuration addon for the perf_boost.dll mod https://gitea.com/avitasia/perf_boost that provides an easy-to-use interface for adjusting performance optimization settings.

### [Guide for new users](GUIDE.md)

## Settings

### Master Control
- **Enable Performance Boost** - Enable/disable all performance boost features

<b>You can keybind this in your keybinds — I highly recommend doing this in case you need to see hidden units in an emergency!<b>

### Rendering Settings
- **Always Render Raid Marks** - Whether to always render raid marks regardless of distance/combat/etc
- **Always Render PVP Players** - Whether to always render players flagged for PVP
- **Always Render Players With Aggro** - Whether to always render players who have aggro from enemies
- **Always Render Players** - Comma-separated list of player names to always render regardless of other settings
- **Never Render Players** - Comma-separated list of player names to never render regardless of other settings
- **Show All Players** - Show all players regardless of distance and other render settings
- **Hide All Players** - Hide all players regardless of other render settings

**Priority:** Settings are applied from top to bottom - earlier settings override later ones.

**Note:** The addon will scan for players in your always/never render lists once per minute to cache their GUIDs. For better performance, it's recommended to clear out old names from these lists when players are no longer relevant.

### Player Render Distance
- **Default Player Render Distance** - Max distance to render players when not in combat or cities (-1 to disable, 0-100 yards)
- **In Combat Player Render Distance** - Max distance to render players when in combat (-1 to disable, 0-100 yards)
- **In Cities Player Render Distance** - Max distance to render players when in cities (-1 to disable, 0-100 yards)

### Unit Render Distance
- **Default Trash Unit Render Distance** - Max distance to render trash units (level < 63) when not in combat (-1 to disable, 0-100 yards)
- **In Combat Trash Unit Render Distance** - Max distance to render trash units (level < 63) when in combat (-1 to disable, 0-100 yards)

### Pet Render Distance
- **Default Pet Render Distance** - Max distance to render pets when not in combat (-1 to disable, 0-100 yards)
- **In Combat Pet Render Distance** - Max distance to render pets when in combat (-1 to disable, 0-100 yards)

### Totem/Guardian Render Distance
- **Default Totem/Guardian Render Distance** - Max distance to render unnamed summons when not in combat (-1 to disable, 0-100 yards)
- **In Combat Totem/Guardian Render Distance** - Max distance to render unnamed summons when in combat (-1 to disable, 0-100 yards)

### Other Rendering
- **Corpse Render Distance** - Max distance to render corpses (-1 to disable, 0-100 yards)
- **Doodad Render Distance** - Max distance to render doodads (trees, crates, lamps, etc.). Interactable game objects are not hidden. Ignored if you are PvP flagged. (-1 to disable, 0-100 yards)

### Spell Visual Settings
- **Show Other Player Spell Visuals** - Whether to show spell visual effects from other players (spell casts, ranged weapon projectiles, wanding, etc.)
- **Show Other Player Ground Effects** - Whether to show ground effects from players
- **Show Other Player Aura Visuals** - Whether to show aura visual effects on players
- **Show Unit Aura Visuals** - Whether to show aura visual effects on units (NPCs, mobs)
- **Hide Spells for Hidden Players** - Hide spell visuals from players that are hidden due to render distance or other settings
- **Hide Laggy Boss Spells on Others** - Curated list of spells for Sapphiron, Gnarlmoon, and Anomalus that will be hidden on other players/units. If you aren't displaying unit auras most of these will already be hidden.
- **Always Hidden Spell IDs** - Comma-separated list of spell IDs to hide visuals for (e.g., 1234,5678)
- **Always Shown Spell IDs** - Comma-separated list of spell IDs to always show visuals for, overriding other settings
- **Apply Hidden Spell IDs to Me** - Whether to apply the hidden spell IDs list to your own character's spells
- **Debug Shown Spells** - Prints to the log information about each spell being displayed

**Note:** Some important debuff auras will always be shown regardless of settings:
- Mark of the Highlord
- Corruption of Medivh
- Living Bomb
- Plague

## Distance Priority

The addon will prioritize render distances in the following order:
1. **Combat Distance** - Used when in combat (highest priority)
2. **City Distance** - Used when in cities (for players only)
3. **Default Distance** - Used in all other situations (lowest priority)

## Slash Commands

### General Commands
- `/pbenable` or `/perfboostenable` - Toggle performance boost on/off.  Can be keybound also.
- `/pbshowallplayers` or `/pbsap` - Toggle show all players on/off.  Can be keybound also.
- `/pbhideallplayers` or `/pbhap` - Toggle hide all players on/off.  Can be keybound also.
- `/pbcycleplayervisibility` or `/pbcycle` - Cycle through player visibility modes: normal → show all → hide all → repeat.  Can be keybound also.
- `/pbtoggleplayerrenderist` or `/pbtrd` - Toggle both normal and combat player render distances between 0 and their previous values.  Can be keybound also.

### Player Render List Commands
- `/pbalwaysrender` or `/pbar` - Add current target to always render list
- `/pbalwaysrenderremove` or `/pbarr` - Remove current target from always render list
- `/pbalwaysrenderclear` or `/pbarc` - Clear entire always render list
- `/pbneverrender` or `/pbnr` - Add current target to never render list  
- `/pbneverrenderremove` or `/pbnrr` - Remove current target from never render list
- `/pbneverrenderclear` or `/pbnrc` - Clear entire never render list

## Per-Character Settings

Enable "Per Character Settings" to save different configurations for each character. When enabled, settings are saved to your character's saved variables file and will override whatever is in the global Config.wtf file.
