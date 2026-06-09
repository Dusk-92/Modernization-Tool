local L = AceLibrary("AceLocale-2.2"):new("NampowerSettings")

L:RegisterTranslations("enUS", function()
    return {
        ["|cffffcc00Nampower v2|cffffaaaa not present hiding settings."] = true,

        ["update available"] = "|cffffcc00Nampower update v2.20.0 available.|cffffcc00  Some settings may be hidden until you update.  Replace your existing nampower.dll with the latest from https://gitea.com/avitasia/nampower/releases",

        ["Superwow required to display queued spells."] = true,

        ["Enable Per Character Settings"] = true,
        ["Whether to use per character settings for all of the NP_ settings.  This will cause settings saved in your character's NampowerSettings.lua to override any global settings in Config.wtf."] = true,

        ["Queue Cast Time Spells"] = true,
        ["Whether to enable spell queuing for spells with a cast time"] = true,

        ["Queue Instant Spells"] = true,
        ["Whether to enable spell queuing for instant cast spells tied to gcd"] = true,

        ["Queue On Swing Spells"] = true,
        ["Whether to enable on swing spell queuing"] = true,

        ["Queue Channeling Spells"] = true,
        ["Whether to enable channeling spell queuing"] = true,

        ["Queue Targeting Spells"] = true,
        ["Whether to enable terrain targeting spell queuing"] = true,

        ["Queue Spells Coming Off Cooldown"] = true,
        ["Whether to enable spell queuing for spells coming off cooldown"] = true,

        ["Queue Windows"] = true,
        ["How much time in ms you have before a cast ends to queue different types of spells"] = true,

        ["Spell Queue Window (ms)"] = true,
        ["The window in ms before a cast finishes where the next will get queued"] = true,

        ["On Swing Buffer Cooldown (ms)"] = true,
        ["The cooldown time in ms after an on swing spell before you can queue on swing spells"] = true,

        ["Channel Queue Window (ms)"] = true,
        ["The window in ms before a channel finishes where the next will get queued"] = true,

        ["Targeting Queue Window (ms)"] = true,
        ["The window in ms before a terrain targeting spell finishes where the next will get queued"] = true,

        ["Cooldown Queue Window (ms)"] = true,
        ["The window in ms before a spell coming off cooldown finishes where the next will get queued"] = true,

        ["Cast Options"] = true,
        ["Options for controlling casting behavior"] = true,

        ["QOL Options"] = true,
        ["Quality of life options to prevent common issues"] = true,
        ["Chat Bubbles"] = true,
        ["Chat bubble options"] = true,
        ["Chat Bubbles (Say/Yell)"] = true,
        ["Whether to enable chat bubbles for /say and /yell messages."] = true,
        ["Chat Bubbles (Party)"] = true,
        ["Whether to enable chat bubbles for /party messages."] = true,
        ["Chat Bubbles (Whisper)"] = true,
        ["Whether to enable chat bubbles for /whisper messages."] = true,
        ["Chat Bubbles (Raid)"] = true,
        ["Whether to enable chat bubbles for /raid messages."] = true,
        ["Chat Bubbles (Battleground)"] = true,
        ["Whether to enable chat bubbles for battleground messages."] = true,
        ["Chat Bubble Distance"] = true,
        ["The distance in yards to show chat bubbles"] = true,

        ["Advanced options"] = true,
        ["Collection of various advanced options"] = true,
        ["Spell Events"] = true,
        ["Controls optional spell and combat event CVars."] = true,

        ["Double Cast to End Channel Early"] = true,
        ["Whether to allow double casting a spell within 350ms to end channeling on the next tick.  Takes into account your ChannelLatencyReductionPercentage."] = true,

        ["Quickcast Targeting Spells on Double Cast"] = true,
        ["Allows casting targeting spells by attempting to cast them twice as opposed to the default client behavior which cancels the targeting indicator"] = true,

        ["Interrupt Channels Outside Queue Window"] = true,
        ["Whether to allow interrupting channels (the original client behavior) when trying to cast a spell outside the channeling queue window"] = true,

        ["Retry Server Rejected Spells"] = true,
        ["Whether to retry spells that are rejected by the server for these reasons: SPELL_FAILED_ITEM_NOT_READY, SPELL_FAILED_NOT_READY, SPELL_FAILED_SPELL_IN_PROGRESS"] = true,

        ["Quickcast Targeting Spells"] = true,
        ["Whether to enable quick casting for ALL spells with terrain targeting"] = true,

        ["Replace Matching Non GCD Category"] = true,
        ["Whether to replace any queued non gcd spell when a new non gcd spell with the same non zero StartRecoveryCategory is cast.  Most trinkets and spells are category 0 which are ignored by this setting.  The primary use case is to switch which potion you have queued."] = true,

        ["Optimize Buffer Using Packet Timings"] = true,
        ["Whether to attempt to optimize your buffer using your latency and server packet timings"] = true,

        ["Minimum Buffer Time (ms)"] = true,
        ["The minimum buffer delay in ms added to each cast"] = true,

        ["Non GCD Buffer Time (ms)"] = true,
        ["The buffer delay in ms added AFTER each cast that is not tied to the gcd"] = true,

        ["Max Buffer Increase (ms)"] = true,
        ["The maximum amount of time in ms to increase the buffer by when the server rejects a cast"] = true,

        ["Channel Latency Reduction (%)"] = true,
        ["The percentage of your latency to subtract from the end of a channel duration to optimize cast time while hopefully not losing any ticks"] = true,

        ["Queued Spell Display Options"] = true,
        ["Options for displaying an icon for the queued spell"] = true,

        ["Display queued spell icon"] = true,
        ["Whether to display an icon of the queued spell"] = true,

        ["Icon size"] = true,
        ["Change the spell icon size"] = true,

        ["Allow dragging"] = true,
        ["Whether to allow interaction with the queued spell icon so you can move it around"] = true,

        ["Reset Position"] = true,
        ["Reset the position of the queued spell icon"] = true,

        ["Show/Hide for positioning"] = true,
        ["Test the queued spell icon and position it to your liking"] = true,

        ["Prevent Right Click Target Change"] = true,
        ["Whether to prevent right-clicking from changing your current target when in combat.  If you don't have a target right click will still change your target even with this on.  This is mainly to prevent accidentally changing targets in combat when trying to adjust your camera."] = true,

        ["Nameplate Distance"] = true,
        ["The distance in yards to show nameplates"] = true,

        ["Spam Protection"] = true,
        ["Whether to enable spam protection functionality that blocks spamming spells while waiting for the server to respond to your initial cast due to issues spamming can cause"] = true,

        ["Prevent Right Click PvP Attack"] = true,
        ["Whether to prevent right-clicking on PvP flagged players to avoid accidental PvP attacks"] = true,

        ["Prevent Mounting When Buff Capped"] = true,
        ["Whether to prevent mounting when you have 32 buffs (buff capped) and are not already mounted. This prevents the issue where you mount but cannot dismount because the mount aura fails to apply due to the buff cap. When blocked, displays an error message."] = true,

        ["Enable Enhanced Tooltips"] = true,
        ["Whether to enable nampower's tooltip additions such as spell proc chance, ICD, and item cooldown text."] = true,

        ["Enable Aura Cast Events"] = true,
        ["Whether to enable AURA_CAST_ON_SELF and AURA_CAST_ON_OTHER events."] = true,

        ["Enable Auto Attack Events"] = true,
        ["Whether to enable AUTO_ATTACK_SELF and AUTO_ATTACK_OTHER events."] = true,

        ["Enable Spell Start Events"] = true,
        ["Whether to enable SPELL_START_SELF and SPELL_START_OTHER events."] = true,

        ["Enable Spell Go Events"] = true,
        ["Whether to enable SPELL_GO_SELF and SPELL_GO_OTHER events."] = true,

        ["Enable Spell Heal Events"] = true,
        ["Whether to enable SPELL_HEAL_BY_SELF, SPELL_HEAL_BY_OTHER, and SPELL_HEAL_ON_SELF events."] = true,

        ["Enable Spell Energize Events"] = true,
        ["Whether to enable SPELL_ENERGIZE_BY_SELF, SPELL_ENERGIZE_BY_OTHER, and SPELL_ENERGIZE_ON_SELF events."] = true,

        ["Unit Event Filters"] = true,
        ["Controls which unit identifiers trigger unit events (UNIT_HEALTH, UNIT_COMBAT, etc.). In the base game the same event can fire multiple times for the same unit, once per identifying string (e.g. 'party1', 'raid1', 'mouseover'). Disabling unused identifiers reduces redundant event calls. Note: 'player', 'target', and 'pet' (your own pet) always trigger regardless of these settings, as they are critical."] = true,

        ["Enable Pet Unit Events"] = true,
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party and raid pet identifiers ('party1pet', 'raid1pet', etc.). Party pets additionally require Enable Party Unit Events to be on; raid pets additionally require Enable Raid Unit Events to be on. Your own pet ('pet') always fires events regardless of this setting."] = true,

        ["Enable Party Unit Events"] = true,
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party member identifiers ('party1', 'party2', 'party3', 'party4'). Also required alongside Enable Pet Unit Events for party pet identifiers to fire."] = true,

        ["Enable Raid Unit Events"] = true,
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for raid member identifiers ('raid1' through 'raid40'). Also required alongside Enable Pet Unit Events for raid pet identifiers to fire."] = true,

        ["Enable Mouseover Unit Events"] = true,
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for the 'mouseover' unit identifier."] = true,

        ["Enable GUID Unit Events"] = true,
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_MANA, UNIT_AURA, etc.) using the raw GUID as the unit token, mirroring SuperWoW behavior. Fires for every unit the client tracks — not just named tokens like 'player', 'party1', 'raid1' — which can cause significant event spam in raids, BGs, and crowded zones. Older addons (e.g. pfUI) written for standard named tokens may have performance issues receiving GUID-based events. Addons needing GUID tracking (e.g. Automarker, Cursive) should use the new dedicated UNIT_HEALTH_GUID, UNIT_MANA_GUID, etc. events instead, allowing this to be safely disabled."] = true,

        ["Enable GUID Unit Event Filtering"] = true,
        ["When enabled, suppresses high-frequency GUID events that cause spam in older addons — specifically UNIT_AURA, UNIT_HEALTH, UNIT_MANA, and similar events below UNIT_COMBAT, plus UNIT_NAME_UPDATE, UNIT_PORTRAIT_UPDATE, UNIT_INVENTORY_CHANGED, and PLAYER_GUILD_UPDATE. UNIT_COMBAT_GUID and other less frequent GUID events are still fired. Has no effect if Enable GUID Unit Events is disabled. This is a direct replacement for the 'Filter GUID Events' option in PerfBoost."] = true,

        ["Preserve Greater Demon Autocast"] = true,
        ["Whether to remember and restore Felguard/Doomguard autocast preferences when swapping or resummoning those greater demons."] = true,
    }
end)

L:RegisterTranslations("zhCN", function()
    return {
        ["|cffffcc00Nampower v2|cffffaaaa not present hiding settings."] = "|cffffcc00Nampower v2|cffffaaaa 未安装，隐藏设置项。",

        ["update available"] = "|cffffcc00Nampower v2.20.0 更新可用。|cffffcc00 更新前部分设置可能隐藏。请从 https://gitea.com/avitasia/nampower/releases 下载最新 nampower.dll 替换当前版本。",

        ["Superwow required to display queued spells."] = "需 Superwow 插件显示队列中法术。",

        ["Enable Per Character Settings"] = "启用角色独立设置",
        ["Whether to use per character settings for all of the NP_ settings.  This will cause settings saved in your character's NampowerSettings.lua to override any global settings in Config.wtf."] = "是否为所有 NP_ 设置启用角色独立配置。启用后，角色 NampowerSettings.lua 中的设置将覆盖 Config.wtf 中的全局设置。",

        ["Queue Cast Time Spells"] = "队列施法时间法术",
        ["Whether to enable spell queuing for spells with a cast time"] = "是否对施法时间类法术启用队列功能",

        ["Queue Instant Spells"] = "队列瞬发法术",
        ["Whether to enable spell queuing for instant cast spells tied to gcd"] = "是否对涉及公共冷却的瞬发法术启用队列功能",

        ["Queue On Swing Spells"] = "队列特殊攻击法术",
        ["Whether to enable on swing spell queuing"] = "是否对特殊攻击类法术（如战士压制）启用队列功能",

        ["Queue Channeling Spells"] = "队列引导法术",
        ["Whether to enable channeling spell queuing"] = "是否对引导类法术（如暴风雪）启用队列功能",

        ["Queue Targeting Spells"] = "队列目标区域法术",
        ["Whether to enable terrain targeting spell queuing"] = "是否对目标区域类法术（如暴风雪）启用队列功能",

        ["Queue Spells Coming Off Cooldown"] = "队列冷却结束法术",
        ["Whether to enable spell queuing for spells coming off cooldown"] = "是否对即将结束冷却的法术启用队列功能",

        ["Queue Windows"] = "队列窗口设置",
        ["How much time in ms you have before a cast ends to queue different types of spells"] = "各种法术类型在施法结束前多少毫秒（ms）开始进入队列",

        ["Spell Queue Window (ms)"] = "法术队列窗口（ms）",
        ["The window in ms before a cast finishes where the next will get queued"] = "当前施法结束前多少毫秒（ms）可将下一个法术加入队列",

        ["On Swing Buffer Cooldown (ms)"] = "特殊攻击缓冲冷却（ms）",
        ["The cooldown time in ms after an on swing spell before you can queue on swing spells"] = "特殊攻击法术施放后，多少毫秒（ms）内无法再次将同类法术加入队列",

        ["Channel Queue Window (ms)"] = "引导法术队列窗口（ms）",
        ["The window in ms before a channel finishes where the next will get queued"] = "引导法术结束前多少毫秒（ms）可将下一个法术加入队列",

        ["Targeting Queue Window (ms)"] = "目标区域法术队列窗口（ms）",
        ["The window in ms before a terrain targeting spell finishes where the next will get queued"] = "目标区域法术结束前多少毫秒（ms）可将下一个法术加入队列",

        ["Cooldown Queue Window (ms)"] = "冷却结束队列窗口（ms）",
        ["The window in ms before a spell coming off cooldown finishes where the next will get queued"] = "法术冷却结束前多少毫秒（ms）可将该法术加入队列",

        ["Cast Options"] = "施法选项",
        ["Options for controlling casting behavior"] = "控制施法行为的选项",

        ["QOL Options"] = "便利性选项",
        ["Quality of life options to prevent common issues"] = "用于防止常见错误的便利性选项",
        ["Chat Bubbles"] = "聊天气泡",
        ["Chat bubble options"] = "聊天气泡相关选项",
        ["Chat Bubbles (Say/Yell)"] = "聊天气泡（说话/大喊）",
        ["Whether to enable chat bubbles for /say and /yell messages."] = "是否为 /say 与 /yell 消息启用聊天气泡。",
        ["Chat Bubbles (Party)"] = "聊天气泡（队伍）",
        ["Whether to enable chat bubbles for /party messages."] = "是否为 /party 消息启用聊天气泡。",
        ["Chat Bubbles (Whisper)"] = "聊天气泡（密语）",
        ["Whether to enable chat bubbles for /whisper messages."] = "是否为 /whisper 消息启用聊天气泡。",
        ["Chat Bubbles (Raid)"] = "聊天气泡（团队）",
        ["Whether to enable chat bubbles for /raid messages."] = "是否为 /raid 消息启用聊天气泡。",
        ["Chat Bubbles (Battleground)"] = "聊天气泡（战场）",
        ["Whether to enable chat bubbles for battleground messages."] = "是否为战场消息启用聊天气泡。",
        ["Chat Bubble Distance"] = "聊天气泡距离",
        ["The distance in yards to show chat bubbles"] = "显示聊天气泡的最大距离（码）",

        ["Advanced options"] = "高级选项",
        ["Collection of various advanced options"] = "各类高级选项集合",
        ["Spell Events"] = "法术事件",
        ["Controls optional spell and combat event CVars."] = "控制可选的法术和战斗事件 CVar。",

        ["Double Cast to End Channel Early"] = "双重施法提前结束引导",
        ["Whether to allow double casting a spell within 350ms to end channeling on the next tick.  Takes into account your ChannelLatencyReductionPercentage."] = "是否允许350毫秒内双重施法以在下一个伤害周期提前结束引导。受引导延迟削减比例影响。",

        ["Quickcast Targeting Spells on Double Cast"] = "双重施法快速施放目标区域法术",
        ["Allows casting targeting spells by attempting to cast them twice as opposed to the default client behavior which cancels the targeting indicator"] = "允许通过双次尝试施法来释放目标区域法术，而非默认客户端行为（取消目标指示器）",

        ["Interrupt Channels Outside Queue Window"] = "队列窗口外允许打断引导",
        ["Whether to allow interrupting channels (the original client behavior) when trying to cast a spell outside the channeling queue window"] = "在引导法术队列窗口外尝试施法时，是否允许打断引导（默认客户端行为）",

        ["Retry Server Rejected Spells"] = "重试服务器拒绝的法术",
        ["Whether to retry spells that are rejected by the server for these reasons: SPELL_FAILED_ITEM_NOT_READY, SPELL_FAILED_NOT_READY, SPELL_FAILED_SPELL_IN_PROGRESS"] = "是否对因以下原因被服务器拒绝的法术进行重试：未准备就绪、未冷却、已有法术施放中",

        ["Quickcast Targeting Spells"] = "快速施放目标区域法术",
        ["Whether to enable quick casting for ALL spells with terrain targeting"] = "是否为所有目标区域法术启用快速施放功能",

        ["Replace Matching Non GCD Category"] = "替换同类型非公共冷却法术",
        ["Whether to replace any queued non gcd spell when a new non gcd spell with the same non zero StartRecoveryCategory is cast.  Most trinkets and spells are category 0 which are ignored by this setting.  The primary use case is to switch which potion you have queued."] = "当施放新的非公共冷却法术且其启动类别相同时，是否替换队列中的同类法术。饰品和多数法术属类别0（不受影响），主要用于替换已队列的药水。",

        ["Optimize Buffer Using Packet Timings"] = "基于封包时间优化缓冲",
        ["Whether to attempt to optimize your buffer using your latency and server packet timings"] = "是否根据延迟和服务器封包时间优化法术缓冲机制",

        ["Minimum Buffer Time (ms)"] = "最低缓冲时间（ms）",
        ["The minimum buffer delay in ms added to each cast"] = "为每次施法添加的最小缓冲延迟（毫秒）",

        ["Non GCD Buffer Time (ms)"] = "非公共冷却缓冲时间（ms）",
        ["The buffer delay in ms added AFTER each cast that is not tied to the gcd"] = "在非公共冷却法术施放后添加的缓冲延迟（毫秒）",

        ["Max Buffer Increase (ms)"] = "最大缓冲增加量（ms）",
        ["The maximum amount of time in ms to increase the buffer by when the server rejects a cast"] = "当法术被服务器拒绝时，缓冲时间可增加的最大毫秒数",

        ["Channel Latency Reduction (%)"] = "引导延迟削减比例（%）",
        ["The percentage of your latency to subtract from the end of a channel duration to optimize cast time while hopefully not losing any ticks"] = "为优化施法时间，从引导结束时序中扣除延迟的百分比（避免丢失伤害周期）",

        ["Queued Spell Display Options"] = "队列法术显示选项",
        ["Options for displaying an icon for the queued spell"] = "队列中法术图标的显示设置",

        ["Display queued spell icon"] = "显示队列法术图标",
        ["Whether to display an icon of the queued spell"] = "是否显示队列中法术的图标",

        ["Icon size"] = "图标尺寸",
        ["Change the spell icon size"] = "修改法术图标大小",

        ["Allow dragging"] = "允许拖动",
        ["Whether to allow interaction with the queued spell icon so you can move it around"] = "是否允许通过拖动交互调整队列法术图标位置",

        ["Reset Position"] = "重置位置",
        ["Reset the position of the queued spell icon"] = "重置队列法术图标位置",

        ["Show/Hide for positioning"] = "显示/隐藏（用于定位）",
        ["Test the queued spell icon and position it to your liking"] = "测试队列法术图标位置，按需调整",

        ["Prevent Right Click Target Change"] = "阻止右键切换目标",
        ["Whether to prevent right-clicking from changing your current target when in combat.  If you don't have a target right click will still change your target even with this on.  This is mainly to prevent accidentally changing targets in combat when trying to adjust your camera."] = "战斗中右键点击是否不改变当前目标（无目标时仍可切换）。主要用于调整镜头时避免误切目标。",

        ["Nameplate Distance"] = "姓名板显示距离",
        ["The distance in yards to show nameplates"] = "显示姓名板的最大距离（码）",

        ["Spam Protection"] = "防连点保护",
        ["Whether to enable spam protection functionality that blocks spamming spells while waiting for the server to respond to your initial cast due to issues spamming can cause"] = "是否启用防连点保护功能，避免在等待服务器响应期间连点施法导致的问题",

        ["Prevent Right Click PvP Attack"] = "阻止右键PvP攻击",
        ["Whether to prevent right-clicking on PvP flagged players to avoid accidental PvP attacks"] = "是否防止右键点击PvP标记玩家以避免误触发PvP攻击",

        ["Prevent Mounting When Buff Capped"] = "Buff满时阻止上坐骑",
        ["Whether to prevent mounting when you have 32 buffs (buff capped) and are not already mounted. This prevents the issue where you mount but cannot dismount because the mount aura fails to apply due to the buff cap. When blocked, displays an error message."] = "当已有32个增益（Buff已满）且未在坐骑状态时，是否阻止上坐骑，以避免坐骑光环因Buff上限无法施加导致无法下马的问题。被阻止时会显示错误提示。",

        ["Enable Enhanced Tooltips"] = "启用增强工具提示",
        ["Whether to enable nampower's tooltip additions such as spell proc chance, ICD, and item cooldown text."] = "是否启用 nampower 的工具提示增强内容，例如法术触发几率、内置冷却时间（ICD）和物品冷却文本。",

        ["Enable Aura Cast Events"] = "启用光环施放事件",
        ["Whether to enable AURA_CAST_ON_SELF and AURA_CAST_ON_OTHER events."] = "是否启用 AURA_CAST_ON_SELF 和 AURA_CAST_ON_OTHER 事件。",

        ["Enable Auto Attack Events"] = "启用自动攻击事件",
        ["Whether to enable AUTO_ATTACK_SELF and AUTO_ATTACK_OTHER events."] = "是否启用 AUTO_ATTACK_SELF 和 AUTO_ATTACK_OTHER 事件。",

        ["Enable Spell Start Events"] = "启用法术开始事件",
        ["Whether to enable SPELL_START_SELF and SPELL_START_OTHER events."] = "是否启用 SPELL_START_SELF 和 SPELL_START_OTHER 事件。",

        ["Enable Spell Go Events"] = "启用法术释放事件",
        ["Whether to enable SPELL_GO_SELF and SPELL_GO_OTHER events."] = "是否启用 SPELL_GO_SELF 和 SPELL_GO_OTHER 事件。",

        ["Enable Spell Heal Events"] = "启用法术治疗事件",
        ["Whether to enable SPELL_HEAL_BY_SELF, SPELL_HEAL_BY_OTHER, and SPELL_HEAL_ON_SELF events."] = "是否启用 SPELL_HEAL_BY_SELF、SPELL_HEAL_BY_OTHER 和 SPELL_HEAL_ON_SELF 事件。",

        ["Enable Spell Energize Events"] = "启用法术回能事件",
        ["Whether to enable SPELL_ENERGIZE_BY_SELF, SPELL_ENERGIZE_BY_OTHER, and SPELL_ENERGIZE_ON_SELF events."] = "是否启用 SPELL_ENERGIZE_BY_SELF、SPELL_ENERGIZE_BY_OTHER 和 SPELL_ENERGIZE_ON_SELF 事件。",

        ["Unit Event Filters"] = "单位事件过滤器",
        ["Controls which unit identifiers trigger unit events (UNIT_HEALTH, UNIT_COMBAT, etc.). In the base game the same event can fire multiple times for the same unit, once per identifying string (e.g. 'party1', 'raid1', 'mouseover'). Disabling unused identifiers reduces redundant event calls. Note: 'player', 'target', and 'pet' (your own pet) always trigger regardless of these settings, as they are critical."] = "控制哪些单位标识符触发单位事件（UNIT_HEALTH、UNIT_COMBAT 等）。在原版游戏中，同一单位可能因多个标识符（如 'party1'、'raid1'、'mouseover'）重复触发同一事件。禁用不需要的标识符可减少冗余事件调用。注意：'player'（自身）、'target'（目标）和 'pet'（自己的宠物）始终会触发，不受此处设置影响，因为它们是关键标识符。",

        ["Enable Pet Unit Events"] = "启用宠物单位事件",
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party and raid pet identifiers ('party1pet', 'raid1pet', etc.). Party pets additionally require Enable Party Unit Events to be on; raid pets additionally require Enable Raid Unit Events to be on. Your own pet ('pet') always fires events regardless of this setting."] = "是否为队伍和团队宠物标识符（'party1pet'、'raid1pet' 等）触发单位事件（UNIT_HEALTH、UNIT_COMBAT 等）。队伍宠物还需同时开启「启用队伍单位事件」；团队宠物还需同时开启「启用团队单位事件」。自己的宠物（'pet'）始终触发事件，不受此设置影响。",

        ["Enable Party Unit Events"] = "启用队伍单位事件",
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party member identifiers ('party1', 'party2', 'party3', 'party4'). Also required alongside Enable Pet Unit Events for party pet identifiers to fire."] = "是否为队伍成员标识符（'party1'、'party2'、'party3'、'party4'）触发单位事件（UNIT_HEALTH、UNIT_COMBAT 等）。同时也是队伍宠物标识符触发的必要条件（需与「启用宠物单位事件」共同开启）。",

        ["Enable Raid Unit Events"] = "启用团队单位事件",
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for raid member identifiers ('raid1' through 'raid40'). Also required alongside Enable Pet Unit Events for raid pet identifiers to fire."] = "是否为团队成员标识符（'raid1' 至 'raid40'）触发单位事件（UNIT_HEALTH、UNIT_COMBAT 等）。同时也是团队宠物标识符触发的必要条件（需与「启用宠物单位事件」共同开启）。",

        ["Enable Mouseover Unit Events"] = "启用鼠标悬停单位事件",
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for the 'mouseover' unit identifier."] = "是否为 'mouseover'（鼠标悬停）单位标识符触发单位事件（UNIT_HEALTH、UNIT_COMBAT 等）。",

        ["Enable GUID Unit Events"] = "启用GUID单位事件",
        ["Whether to fire unit events (UNIT_HEALTH, UNIT_MANA, UNIT_AURA, etc.) using the raw GUID as the unit token, mirroring SuperWoW behavior. Fires for every unit the client tracks — not just named tokens like 'player', 'party1', 'raid1' — which can cause significant event spam in raids, BGs, and crowded zones. Older addons (e.g. pfUI) written for standard named tokens may have performance issues receiving GUID-based events. Addons needing GUID tracking (e.g. Automarker, Cursive) should use the new dedicated UNIT_HEALTH_GUID, UNIT_MANA_GUID, etc. events instead, allowing this to be safely disabled."] = "是否使用原始 GUID 作为单位标识符触发单位事件（UNIT_HEALTH、UNIT_MANA、UNIT_AURA 等），模拟 SuperWoW 行为。此功能会对客户端跟踪的所有单位触发事件——不仅限于 'player'、'party1'、'raid1' 等命名标识符——在团队、战场和人口密集区域可能产生大量事件。为标准命名标识符设计的旧版插件（如 pfUI）在收到 GUID 事件时可能出现性能问题。需要 GUID 跟踪的插件（如 Automarker、Cursive）应改用专用的 UNIT_HEALTH_GUID、UNIT_MANA_GUID 等事件，届时可安全禁用此选项。",

        ["Enable GUID Unit Event Filtering"] = "启用GUID单位事件过滤",
        ["When enabled, suppresses high-frequency GUID events that cause spam in older addons — specifically UNIT_AURA, UNIT_HEALTH, UNIT_MANA, and similar events below UNIT_COMBAT, plus UNIT_NAME_UPDATE, UNIT_PORTRAIT_UPDATE, UNIT_INVENTORY_CHANGED, and PLAYER_GUILD_UPDATE. UNIT_COMBAT_GUID and other less frequent GUID events are still fired. Has no effect if Enable GUID Unit Events is disabled. This is a direct replacement for the 'Filter GUID Events' option in PerfBoost."] = "启用后，将屏蔽对旧版插件造成刷屏的高频 GUID 事件——具体包括 UNIT_COMBAT 以下的事件（如 UNIT_AURA、UNIT_HEALTH、UNIT_MANA 等），以及 UNIT_NAME_UPDATE、UNIT_PORTRAIT_UPDATE、UNIT_INVENTORY_CHANGED 和 PLAYER_GUILD_UPDATE。UNIT_COMBAT_GUID 及其他低频 GUID 事件仍会正常触发。若已禁用「启用GUID单位事件」，则此设置无效。此选项直接替代 PerfBoost 中的「过滤GUID事件」功能。",

        ["Preserve Greater Demon Autocast"] = "保留大型恶魔自动施法",
        ["Whether to remember and restore Felguard/Doomguard autocast preferences when swapping or resummoning those greater demons."] = "切换或重新召唤地狱守卫/末日守卫时，是否记忆并恢复其自动施法设置。",
    }
end)
