local L = AceLibrary("AceLocale-2.2"):new("NampowerSettings")

-- No Nampower v2, no need for settings
if not GetNampowerVersion then
	DEFAULT_CHAT_FRAME:AddMessage(L["|cffffcc00Nampower v2|cffffaaaa not present hiding settings."])
	return
end

Nampower = AceLibrary("AceAddon-2.0"):new("AceEvent-2.0", "AceDebug-2.0", "AceModuleCore-2.0", "AceConsole-2.0", "AceDB-2.0", "AceHook-2.1")
Nampower:RegisterDB("NampowerSettingsDB")
Nampower:RegisterDefaults("profile", {
	per_character_settings = false,
	show_queued_spell = false,
	queued_spell_posx = 0,
	queued_spell_posy = 0,
	queued_spell_size = 16,
	queued_spell_enable_mouse = true,
})
Nampower.frame = CreateFrame("Frame", "Nampower", UIParent)

local DISPLAY_ONLY_SETTINGS = {
	NP_EnableAuraCastEvents = true,
	NP_EnableAutoAttackEvents = true,
	NP_EnableSpellStartEvents = true,
	NP_EnableSpellGoEvents = true,
	NP_EnableSpellHealEvents = true,
	NP_EnableSpellEnergizeEvents = true,
	NP_EnableUnitEventsPet = true,
	NP_EnableUnitEventsParty = true,
	NP_EnableUnitEventsRaid = true,
	NP_EnableUnitEventsMouseover = true,
	NP_EnableUnitEventsGuid = true,
}

local function isProfileManagedSetting(settingKey)
	return string.find(settingKey, "NP_") == 1 and not DISPLAY_ONLY_SETTINGS[settingKey]
end

local function clearDisplayOnlyProfileSettings()
	for settingKey in pairs(DISPLAY_ONLY_SETTINGS) do
		Nampower.db.profile[settingKey] = nil
	end
end

function Nampower:HasMinimumVersion(major, minor, patch)
	if GetNampowerVersion then
		local installedMajor, installedMinor, installedPatch = GetNampowerVersion()

		if installedMajor > major then
			return true
		elseif installedMajor == major and installedMinor > minor then
			return true
		elseif installedMajor == major and installedMinor == minor and installedPatch >= patch then
			return true
		end
	end

	return false
end

-- check if they have the latest nampower dll
if not Nampower:HasMinimumVersion(2, 20, 0) then
	DEFAULT_CHAT_FRAME:AddMessage(L["update available"])
end

-- setup queued spell frame
Nampower.queued_spell = CreateFrame("Frame", "Queued Spell", UIParent)
Nampower.queued_spell:SetFrameStrata("HIGH")
Nampower.queued_spell.texture = Nampower.queued_spell:CreateTexture(nil, "OVERLAY")
Nampower.queued_spell.texture:SetAllPoints()
Nampower.queued_spell.texture:SetTexCoord(.08, .92, .08, .92)
Nampower.queued_spell.texture:SetTexture("Interface\\Icons\\Spell_Nature_HealingWaveLesser") -- set test texture

-- setup dragging
Nampower.queued_spell:RegisterForDrag("LeftButton")
Nampower.queued_spell:SetMovable(true)

Nampower.queued_spell:SetScript("OnDragStart", function()
	this:StartMoving()
end)

local function saveQueuedSpellPosition()
	Nampower.db.profile.queued_spell_posx = Nampower.queued_spell:GetLeft()
	Nampower.db.profile.queued_spell_posy = Nampower.queued_spell:GetTop()
end

Nampower.queued_spell:SetScript("OnDragStop", function()
	this:StopMovingOrSizing()
	saveQueuedSpellPosition()
end)

local ON_SWING_QUEUED = 0
local ON_SWING_QUEUE_POPPED = 1
local NORMAL_QUEUED = 2
local NORMAL_QUEUE_POPPED = 3
local NON_GCD_QUEUED = 4
local NON_GCD_QUEUE_POPPED = 5

local function spellQueueEventNampower(eventCode, spellId)
  if eventCode == NORMAL_QUEUED or eventCode == NON_GCD_QUEUED then
    local texture = GetSpellIconTexture(GetSpellRecField(spellId, "spellIconID"))
    if texture then
      Nampower.queued_spell.texture:SetTexture(texture)
      Nampower.queued_spell:Show()
    end
  elseif eventCode == NORMAL_QUEUE_POPPED or eventCode == NON_GCD_QUEUE_POPPED then
    Nampower.queued_spell:Hide()
  end
end

local function spellQueueEventSuperwow(eventCode, spellId)
  if eventCode == NORMAL_QUEUED or eventCode == NON_GCD_QUEUED then
		local _, _, texture = SpellInfo(spellId) -- superwow function
		Nampower.queued_spell.texture:SetTexture(texture)
		Nampower.queued_spell:Show()
	elseif eventCode == NORMAL_QUEUE_POPPED or eventCode == NON_GCD_QUEUE_POPPED then
		Nampower.queued_spell:Hide()
	end
end

local function toggleEventListener()
	if Nampower.db.profile.show_queued_spell then
    if GetSpellRecField and GetSpellIconTexture then
      Nampower:RegisterEvent("SPELL_QUEUE_EVENT", spellQueueEventNampower)
    elseif SpellInfo then
      Nampower:RegisterEvent("SPELL_QUEUE_EVENT", spellQueueEventSuperwow)
		else
			DEFAULT_CHAT_FRAME:AddMessage(L["Superwow required to display queued spells."])
			if Nampower:IsEventRegistered("SPELL_QUEUE_EVENT") then
				Nampower:UnregisterEvent("SPELL_QUEUE_EVENT")
			end
		end
	else
		if Nampower:IsEventRegistered("SPELL_QUEUE_EVENT") then
			Nampower:UnregisterEvent("SPELL_QUEUE_EVENT")
		end
	end
end

-- used when turning on per character settings
function Nampower:SavePerCharacterSettings()
	for settingKey, settingData in pairs(Nampower.cmdtable.args) do
		if isProfileManagedSetting(settingKey) then
			settingData.set(settingData.get()) -- trigger the set function for each setting with the current value
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.queue_windows.args) do
		if isProfileManagedSetting(settingKey) then
			settingData.set(settingData.get()) -- trigger the set function for each setting with the current value
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.advanced_options.args) do
		if isProfileManagedSetting(settingKey) then
			settingData.set(settingData.get()) -- trigger the set function for each setting with the current value
		end
	end

	if Nampower.cmdtable.args.advanced_options.args.unit_events then
		for settingKey, settingData in pairs(Nampower.cmdtable.args.advanced_options.args.unit_events.args) do
			if isProfileManagedSetting(settingKey) then
				settingData.set(settingData.get()) -- trigger the set function for each setting with the current value
			end
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.qol_options.args) do
		if isProfileManagedSetting(settingKey) then
			settingData.set(settingData.get()) -- trigger the set function for each setting with the current value
		end
	end

	if Nampower.cmdtable.args.chat_bubbles then
		for settingKey, settingData in pairs(Nampower.cmdtable.args.chat_bubbles.args) do
			if settingData.get and settingData.set then
				settingData.set(settingData.get())
			end
		end
	end
end

function Nampower:ApplySavedSettings()
	for settingKey, settingData in pairs(Nampower.cmdtable.args) do
		-- only apply settings that are prefixed with NP_
		if isProfileManagedSetting(settingKey) then
			if Nampower.db.profile[settingKey]~= nil then
				settingData.set(Nampower.db.profile[settingKey])
			end
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.queue_windows.args) do
		-- only apply settings that are prefixed with NP_
		if isProfileManagedSetting(settingKey) then
			if Nampower.db.profile[settingKey]~= nil then
				settingData.set(Nampower.db.profile[settingKey])
			end
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.advanced_options.args) do
		-- only apply settings that are prefixed with NP_
		if isProfileManagedSetting(settingKey) then
			if Nampower.db.profile[settingKey]~= nil then
				settingData.set(Nampower.db.profile[settingKey])
			end
		end
	end

	if Nampower.cmdtable.args.advanced_options.args.unit_events then
		for settingKey, settingData in pairs(Nampower.cmdtable.args.advanced_options.args.unit_events.args) do
			-- only apply settings that are prefixed with NP_
			if isProfileManagedSetting(settingKey) then
				if Nampower.db.profile[settingKey]~= nil then
					settingData.set(Nampower.db.profile[settingKey])
				end
			end
		end
	end

	for settingKey, settingData in pairs(Nampower.cmdtable.args.qol_options.args) do
		-- only apply settings that are prefixed with NP_
		if isProfileManagedSetting(settingKey) then
			if Nampower.db.profile[settingKey]~= nil then
				settingData.set(Nampower.db.profile[settingKey])
			end
		end
	end

	if Nampower.cmdtable.args.chat_bubbles then
		for settingKey, settingData in pairs(Nampower.cmdtable.args.chat_bubbles.args) do
			if Nampower.db.profile[settingKey]~= nil and settingData.set then
				settingData.set(Nampower.db.profile[settingKey])
			end
		end
	end
end

function Nampower:OnEnable()
	clearDisplayOnlyProfileSettings()

	Nampower.queued_spell:EnableMouse(Nampower.db.profile.queued_spell_enable_mouse)

	-- set scale
	local x = Nampower.db.profile.queued_spell_posx
	local y = Nampower.db.profile.queued_spell_posy
	local size = Nampower.db.profile.queued_spell_size

	-- set saved position
	Nampower.queued_spell:ClearAllPoints()
	Nampower.queued_spell:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", x, y)
	Nampower.queued_spell:SetWidth(size)
	Nampower.queued_spell:SetHeight(size)
	Nampower.queued_spell:Hide()

	-- if per character settings are enabled, apply them
	if Nampower.db.profile.per_character_settings then
		Nampower:ApplySavedSettings()
	end

	toggleEventListener()
end

Nampower.cmdtable = {
	type = "group",
	handler = Nampower,
	args = {
		per_character_settings = {
			type = "toggle",
			name = L["Enable Per Character Settings"],
			desc = L["Whether to use per character settings for all of the NP_ settings.  This will cause settings saved in your character's NampowerSettings.lua to override any global settings in Config.wtf."],
			order = 1,
			get = function()
				return Nampower.db.profile.per_character_settings
			end,
			set = function(v)
				if v ~= Nampower.db.profile.per_character_settings then
					Nampower.db.profile.per_character_settings = v
					if v == true then
						Nampower:SavePerCharacterSettings()
					end
				end
			end,
		},
		NP_QueueCastTimeSpells = {
			type = "toggle",
			name = L["Queue Cast Time Spells"],
			desc = L["Whether to enable spell queuing for spells with a cast time"],
			order = 5,
			get = function()
				return GetCVar("NP_QueueCastTimeSpells") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueCastTimeSpells = v
				if v == true then
					SetCVar("NP_QueueCastTimeSpells", "1")
				else
					SetCVar("NP_QueueCastTimeSpells", "0")
				end
			end,
		},
		NP_QueueInstantSpells = {
			type = "toggle",
			name = L["Queue Instant Spells"],
			desc = L["Whether to enable spell queuing for instant cast spells tied to gcd"],
			order = 10,
			get = function()
				return GetCVar("NP_QueueInstantSpells") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueInstantSpells = v
				if v == true then
					SetCVar("NP_QueueInstantSpells", "1")
				else
					SetCVar("NP_QueueInstantSpells", "0")
				end
			end,
		},
		NP_QueueOnSwingSpells = {
			type = "toggle",
			name = L["Queue On Swing Spells"],
			desc = L["Whether to enable on swing spell queuing"],
			order = 15,
			get = function()
				return GetCVar("NP_QueueOnSwingSpells") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueOnSwingSpells = v
				if v == true then
					SetCVar("NP_QueueOnSwingSpells", "1")
				else
					SetCVar("NP_QueueOnSwingSpells", "0")
				end
			end,
		},
		NP_QueueChannelingSpells = {
			type = "toggle",
			name = L["Queue Channeling Spells"],
			desc = L["Whether to enable channeling spell queuing"],
			order = 20,
			get = function()
				return GetCVar("NP_QueueChannelingSpells") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueChannelingSpells = v
				if v == true then
					SetCVar("NP_QueueChannelingSpells", "1")
				else
					SetCVar("NP_QueueChannelingSpells", "0")
				end
			end,
		},
		NP_QueueTargetingSpells = {
			type = "toggle",
			name = L["Queue Targeting Spells"],
			desc = L["Whether to enable terrain targeting spell queuing"],
			order = 25,
			get = function()
				return GetCVar("NP_QueueTargetingSpells") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueTargetingSpells = v
				if v == true then
					SetCVar("NP_QueueTargetingSpells", "1")
				else
					SetCVar("NP_QueueTargetingSpells", "0")
				end
			end,
		},
		NP_QueueSpellsOnCooldown = {
			type = "toggle",
			name = L["Queue Spells Coming Off Cooldown"],
			desc = L["Whether to enable spell queuing for spells coming off cooldown"],
			order = 30,
			get = function()
				return GetCVar("NP_QueueSpellsOnCooldown") == "1"
			end,
			set = function(v)
				Nampower.db.profile.NP_QueueSpellsOnCooldown = v
				if v == true then
					SetCVar("NP_QueueSpellsOnCooldown", "1")
				else
					SetCVar("NP_QueueSpellsOnCooldown", "0")
				end
			end,
		},
		spacera = {
			type = "header",
			name = " ",
			order = 31,
		},
		queue_windows = {
			type = "group",
			name = L["Queue Windows"],
			desc = L["How much time in ms you have before a cast ends to queue different types of spells"],
			order = 40,
			args = {
				NP_SpellQueueWindowMs = {
					type = "range",
					name = L["Spell Queue Window (ms)"],
					desc = L["The window in ms before a cast finishes where the next will get queued"],
					order = 40,
					min = 0,
					max = 5000,
					step = 50,
					get = function()
						return GetCVar("NP_SpellQueueWindowMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_SpellQueueWindowMs = v
						SetCVar("NP_SpellQueueWindowMs", v)
					end,
				},
				NP_OnSwingBufferCooldownMs = {
					type = "range",
					name = L["On Swing Buffer Cooldown (ms)"],
					desc = L["The cooldown time in ms after an on swing spell before you can queue on swing spells"],
					order = 45,
					min = 0,
					max = 5000,
					step = 50,
					get = function()
						return GetCVar("NP_OnSwingBufferCooldownMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_OnSwingBufferCooldownMs = v
						SetCVar("NP_OnSwingBufferCooldownMs", v)
					end,
				},
				NP_ChannelQueueWindowMs = {
					type = "range",
					name = L["Channel Queue Window (ms)"],
					desc = L["The window in ms before a channel finishes where the next will get queued"],
					order = 50,
					min = 0,
					max = 5000,
					step = 50,
					get = function()
						return GetCVar("NP_ChannelQueueWindowMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_ChannelQueueWindowMs = v
						SetCVar("NP_ChannelQueueWindowMs", v)
					end,
				},
				NP_TargetingQueueWindowMs = {
					type = "range",
					name = L["Targeting Queue Window (ms)"],
					desc = L["The window in ms before a terrain targeting spell finishes where the next will get queued"],
					order = 55,
					min = 0,
					max = 5000,
					step = 50,
					get = function()
						return GetCVar("NP_TargetingQueueWindowMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_TargetingQueueWindowMs = v
						SetCVar("NP_TargetingQueueWindowMs", v)
					end,
				},
				NP_CooldownQueueWindowMs = {
					type = "range",
					name = L["Cooldown Queue Window (ms)"],
					desc = L["The window in ms before a spell coming off cooldown finishes where the next will get queued"],
					order = 60,
					min = 0,
					max = 5000,
					step = 50,
					get = function()
						return GetCVar("NP_CooldownQueueWindowMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_CooldownQueueWindowMs = v
						SetCVar("NP_CooldownQueueWindowMs", v)
					end,
				}
			},
		},
		spacerb = {
			type = "header",
			name = " ",
			order = 50,
		},
		cast_options = {
			type = "group",
			name = L["Cast Options"],
			desc = L["Options for controlling casting behavior"],
			order = 55,
			args = {
				NP_QuickcastTargetingSpells = {
					type = "toggle",
					name = L["Quickcast Targeting Spells"],
					desc = L["Whether to enable quick casting for ALL spells with terrain targeting"],
					order = 5,
					get = function()
						return GetCVar("NP_QuickcastTargetingSpells") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_QuickcastTargetingSpells = v
						if v == true then
							SetCVar("NP_QuickcastTargetingSpells", "1")
						else
							SetCVar("NP_QuickcastTargetingSpells", "0")
						end
					end,
				},
				NP_DoubleCastToEndChannelEarly = {
					type = "toggle",
					name = L["Double Cast to End Channel Early"],
					desc = L["Whether to allow double casting a spell within 350ms to end channeling on the next tick.  Takes into account your ChannelLatencyReductionPercentage."],
					order = 15,
					get = function()
						return GetCVar("NP_DoubleCastToEndChannelEarly") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_DoubleCastToEndChannelEarly = v
						if v == true then
							SetCVar("NP_DoubleCastToEndChannelEarly", "1")
						else
							SetCVar("NP_DoubleCastToEndChannelEarly", "0")
						end
					end,
				},
			},
		},
		spacerc2 = {
			type = "header",
			name = " ",
			order = 58,
		},
		qol_options = {
			type = "group",
			name = L["QOL Options"],
			desc = L["Quality of life options to prevent common issues"],
			order = 59,
			args = {
			},
		},
		chat_bubbles = {
			type = "group",
			name = L["Chat Bubbles"],
			desc = L["Chat bubble options"],
			order = 120,
			args = {
			},
		},
		spacerc3 = {
			type = "header",
			name = " ",
			order = 60,
		},
		advanced_options = {
			type = "group",
			name = L["Advanced options"],
			desc = L["Collection of various advanced options"],
			order = 65,
			args = {
				NP_InterruptChannelsOutsideQueueWindow = {
					type = "toggle",
					name = L["Interrupt Channels Outside Queue Window"],
					desc = L["Whether to allow interrupting channels (the original client behavior) when trying to cast a spell outside the channeling queue window"],
					order = 70,
					get = function()
						return GetCVar("NP_InterruptChannelsOutsideQueueWindow") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_InterruptChannelsOutsideQueueWindow = v
						if v == true then
							SetCVar("NP_InterruptChannelsOutsideQueueWindow", "1")
						else
							SetCVar("NP_InterruptChannelsOutsideQueueWindow", "0")
						end
					end,
				},
				NP_RetryServerRejectedSpells = {
					type = "toggle",
					name = L["Retry Server Rejected Spells"],
					desc = L["Whether to retry spells that are rejected by the server for these reasons: SPELL_FAILED_ITEM_NOT_READY, SPELL_FAILED_NOT_READY, SPELL_FAILED_SPELL_IN_PROGRESS"],
					order = 100,
					get = function()
						return GetCVar("NP_RetryServerRejectedSpells") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_RetryServerRejectedSpells = v
						if v == true then
							SetCVar("NP_RetryServerRejectedSpells", "1")
						else
							SetCVar("NP_RetryServerRejectedSpells", "0")
						end
					end,
				},
				NP_ReplaceMatchingNonGcdCategory = {
					type = "toggle",
					name = L["Replace Matching Non GCD Category"],
					desc = L["Whether to replace any queued non gcd spell when a new non gcd spell with the same non zero StartRecoveryCategory is cast.  Most trinkets and spells are category 0 which are ignored by this setting.  The primary use case is to switch which potion you have queued."],
					order = 110,
					get = function()
						return GetCVar("NP_ReplaceMatchingNonGcdCategory") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_ReplaceMatchingNonGcdCategory = v
						if v == true then
							SetCVar("NP_ReplaceMatchingNonGcdCategory", "1")
						else
							SetCVar("NP_ReplaceMatchingNonGcdCategory", "0")
						end
					end,
				},
				NP_OptimizeBufferUsingPacketTimings = {
					type = "toggle",
					name = L["Optimize Buffer Using Packet Timings"],
					desc = L["Whether to attempt to optimize your buffer using your latency and server packet timings"],
					order = 115,
					get = function()
						return GetCVar("NP_OptimizeBufferUsingPacketTimings") == "1"
					end,
					set = function(v)
						Nampower.db.profile.NP_OptimizeBufferUsingPacketTimings = v
						if v == true then
							SetCVar("NP_OptimizeBufferUsingPacketTimings", "1")
						else
							SetCVar("NP_OptimizeBufferUsingPacketTimings", "0")
						end
					end,
				},
				NP_MinBufferTimeMs = {
					type = "range",
					name = L["Minimum Buffer Time (ms)"],
					desc = L["The minimum buffer delay in ms added to each cast"],
					order = 80,
					min = 0,
					max = 300,
					step = 1,
					get = function()
						return GetCVar("NP_MinBufferTimeMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_MinBufferTimeMs = v
						SetCVar("NP_MinBufferTimeMs", v)
					end,
				},
				NP_NonGcdBufferTimeMs = {
					type = "range",
					name = L["Non GCD Buffer Time (ms)"],
					desc = L["The buffer delay in ms added AFTER each cast that is not tied to the gcd"],
					order = 85,
					min = 0,
					max = 300,
					step = 1,
					get = function()
						return GetCVar("NP_NonGcdBufferTimeMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_NonGcdBufferTimeMs = v
						SetCVar("NP_NonGcdBufferTimeMs", v)
					end,
				},
				NP_MaxBufferIncreaseMs = {
					type = "range",
					name = L["Max Buffer Increase (ms)"],
					desc = L["The maximum amount of time in ms to increase the buffer by when the server rejects a cast"],
					order = 90,
					min = 0,
					max = 100,
					step = 5,
					get = function()
						return GetCVar("NP_MaxBufferIncreaseMs")
					end,
					set = function(v)
						Nampower.db.profile.NP_MaxBufferIncreaseMs = v
						SetCVar("NP_MaxBufferIncreaseMs", v)
					end,
				},
				NP_ChannelLatencyReductionPercentage = {
					type = "range",
					name = L["Channel Latency Reduction (%)"],
					desc = L["The percentage of your latency to subtract from the end of a channel duration to optimize cast time while hopefully not losing any ticks"],
					order = 125,
					min = 0,
					max = 100,
					step = 1,
					get = function()
						return GetCVar("NP_ChannelLatencyReductionPercentage")
					end,
					set = function(v)
						Nampower.db.profile.NP_ChannelLatencyReductionPercentage = v
						SetCVar("NP_ChannelLatencyReductionPercentage", v)
					end,
				},
				spell_events = {
					type = "group",
					name = L["Spell Events"],
					desc = L["Controls optional spell and combat event CVars."],
					order = 150,
					args = {
					},
				},
			},
		},
		spacerc = {
			type = "header",
			name = " ",
			order = 75,
		},
		queued_spell_options = {
			type = "group",
			name = L["Queued Spell Display Options"],
			desc = L["Options for displaying an icon for the queued spell"],
			order = 85,
			args = {
				enabled = {
					type = "toggle",
					name = L["Display queued spell icon"],
					desc = L["Whether to display an icon of the queued spell"],
					order = 5,
					get = function()
						return Nampower.db.profile.show_queued_spell
					end,
					set = function(v)
						Nampower.db.profile.show_queued_spell = v
						toggleEventListener()
					end,
				},
				size = {
					type = "range",
					name = L["Icon size"],
					desc = L["Change the spell icon size"],
					order = 10,
					min = 8,
					max = 48,
					step = 1,
					get = function()
						return Nampower.db.profile.queued_spell_size
					end,
					set = function(v)
						Nampower.db.profile.queued_spell_size = v
						Nampower.queued_spell:SetWidth(v)
						Nampower.queued_spell:SetHeight(v)
					end,
				},
				draggable = {
					type = "toggle",
					name = L["Allow dragging"],
					desc = L["Whether to allow interaction with the queued spell icon so you can move it around"],
					order = 15,
					get = function()
						return Nampower.db.profile.queued_spell_enable_mouse
					end,
					set = function(v)
						Nampower.db.profile.queued_spell_enable_mouse = v
						Nampower.queued_spell:EnableMouse(v)
					end,
				},
				reset_position = {
					type = "execute",
					name = L["Reset Position"],
					desc = L["Reset the position of the queued spell icon"],
					order = 20,
					func = function()
						local scale = Nampower.queued_spell:GetEffectiveScale()
						Nampower.queued_spell:ClearAllPoints()
						Nampower.queued_spell:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", 500 / scale, 500 / scale)
						saveQueuedSpellPosition()
					end,
				},
				test = {
					type = "execute",
					name = L["Show/Hide for positioning"],
					desc = L["Test the queued spell icon and position it to your liking"],
					order = 25,
					func = function()
						if Nampower.queued_spell:IsVisible() then
							Nampower.queued_spell:Hide()
						else
							Nampower.queued_spell:Show()
						end
					end,
				},
			},
		},
		spacerd = {
			type = "header",
			name = " ",
			order = 95,
		},
	},
}

if Nampower:HasMinimumVersion(2, 8, 6) then
	Nampower.cmdtable.args.NP_NameplateDistance = {
		type = "range",
		name = L["Nameplate Distance"],
		desc = L["The distance in yards to show nameplates"],
		order = 115,
		min = 5,
		max = 200,
		step = 1,
		get = function()
			return GetCVar("NP_NameplateDistance")
		end,
		set = function(v)
			Nampower.db.profile.NP_NameplateDistance = v
			SetCVar("NP_NameplateDistance", v)
		end,
	}
end

Nampower.cmdtable.args.qol_options.args.NP_PreventRightClickTargetChange = {
	type = "toggle",
	name = L["Prevent Right Click Target Change"],
	desc = L["Whether to prevent right-clicking from changing your current target when in combat.  If you don't have a target right click will still change your target even with this on.  This is mainly to prevent accidentally changing targets in combat when trying to adjust your camera."],
	order = 5,
	get = function()
		return GetCVar("NP_PreventRightClickTargetChange") == "1"
	end,
	set = function(v)
		Nampower.db.profile.NP_PreventRightClickTargetChange = v
		if v == true then
			SetCVar("NP_PreventRightClickTargetChange", "1")
		else
			SetCVar("NP_PreventRightClickTargetChange", "0")
		end
	end,
}

if Nampower:HasMinimumVersion(2, 11, 0) then
	Nampower.cmdtable.args.qol_options.args.NP_SpamProtectionEnabled = {
		type = "toggle",
		name = L["Spam Protection"],
		desc = L["Whether to enable spam protection functionality that blocks spamming spells while waiting for the server to respond to your initial cast due to issues spamming can cause"],
		order = 10,
		get = function()
			return GetCVar("NP_SpamProtectionEnabled") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_SpamProtectionEnabled = v
			if v == true then
				SetCVar("NP_SpamProtectionEnabled", "1")
			else
				SetCVar("NP_SpamProtectionEnabled", "0")
			end
		end,
	}

	Nampower.cmdtable.args.qol_options.args.NP_PreventRightClickPvPAttack = {
		type = "toggle",
		name = L["Prevent Right Click PvP Attack"],
		desc = L["Whether to prevent right-clicking on PvP flagged players to avoid accidental PvP attacks"],
		order = 15,
		get = function()
			return GetCVar("NP_PreventRightClickPvPAttack") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_PreventRightClickPvPAttack = v
			if v == true then
				SetCVar("NP_PreventRightClickPvPAttack", "1")
			else
				SetCVar("NP_PreventRightClickPvPAttack", "0")
			end
		end,
	}
else
	DEFAULT_CHAT_FRAME:AddMessage(L["update available"])
end

if Nampower:HasMinimumVersion(2, 15, 0) then
	Nampower.cmdtable.args.cast_options.args.NP_QuickcastOnDoubleCast = {
		type = "toggle",
		name = L["Quickcast Targeting Spells on Double Cast"],
		desc = L["Allows casting targeting spells by attempting to cast them twice as opposed to the default client behavior which cancels the targeting indicator"],
		order = 10,
		get = function()
			return GetCVar("NP_QuickcastOnDoubleCast") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_QuickcastOnDoubleCast = v
			if v == true then
				SetCVar("NP_QuickcastOnDoubleCast", "1")
			else
				SetCVar("NP_QuickcastOnDoubleCast", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(2, 20, 0) then
	Nampower.cmdtable.args.qol_options.args.NP_PreventMountingWhenBuffCapped = {
		type = "toggle",
		name = L["Prevent Mounting When Buff Capped"],
		desc = L["Whether to prevent mounting when you have 32 buffs (buff capped) and are not already mounted. This prevents the issue where you mount but cannot dismount because the mount aura fails to apply due to the buff cap. When blocked, displays an error message."],
		order = 20,
		get = function()
			return GetCVar("NP_PreventMountingWhenBuffCapped") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_PreventMountingWhenBuffCapped = v
			if v == true then
				SetCVar("NP_PreventMountingWhenBuffCapped", "1")
			else
				SetCVar("NP_PreventMountingWhenBuffCapped", "0")
			end
		end,
	}

	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableAuraCastEvents = {
		type = "toggle",
		name = L["Enable Aura Cast Events"],
		desc = L["Whether to enable AURA_CAST_ON_SELF and AURA_CAST_ON_OTHER events."],
		order = 155,
		get = function()
			return GetCVar("NP_EnableAuraCastEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableAuraCastEvents", "1")
			else
				SetCVar("NP_EnableAuraCastEvents", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(2, 24, 0) then
	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableAutoAttackEvents = {
		type = "toggle",
		name = L["Enable Auto Attack Events"],
		desc = L["Whether to enable AUTO_ATTACK_SELF and AUTO_ATTACK_OTHER events."],
		order = 160,
		get = function()
			return GetCVar("NP_EnableAutoAttackEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableAutoAttackEvents", "1")
			else
				SetCVar("NP_EnableAutoAttackEvents", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(2, 25, 0) then
	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableSpellStartEvents = {
		type = "toggle",
		name = L["Enable Spell Start Events"],
		desc = L["Whether to enable SPELL_START_SELF and SPELL_START_OTHER events."],
		order = 165,
		get = function()
			return GetCVar("NP_EnableSpellStartEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableSpellStartEvents", "1")
			else
				SetCVar("NP_EnableSpellStartEvents", "0")
			end
		end,
	}

	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableSpellGoEvents = {
		type = "toggle",
		name = L["Enable Spell Go Events"],
		desc = L["Whether to enable SPELL_GO_SELF and SPELL_GO_OTHER events."],
		order = 170,
		get = function()
			return GetCVar("NP_EnableSpellGoEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableSpellGoEvents", "1")
			else
				SetCVar("NP_EnableSpellGoEvents", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(2, 26, 0) then
	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableSpellHealEvents = {
		type = "toggle",
		name = L["Enable Spell Heal Events"],
		desc = L["Whether to enable SPELL_HEAL_BY_SELF, SPELL_HEAL_BY_OTHER, and SPELL_HEAL_ON_SELF events."],
		order = 175,
		get = function()
			return GetCVar("NP_EnableSpellHealEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableSpellHealEvents", "1")
			else
				SetCVar("NP_EnableSpellHealEvents", "0")
			end
		end,
	}

	Nampower.cmdtable.args.advanced_options.args.spell_events.args.NP_EnableSpellEnergizeEvents = {
		type = "toggle",
		name = L["Enable Spell Energize Events"],
		desc = L["Whether to enable SPELL_ENERGIZE_BY_SELF, SPELL_ENERGIZE_BY_OTHER, and SPELL_ENERGIZE_ON_SELF events."],
		order = 180,
		get = function()
			return GetCVar("NP_EnableSpellEnergizeEvents") == "1"
		end,
		set = function(v)
			if v == true then
				SetCVar("NP_EnableSpellEnergizeEvents", "1")
			else
				SetCVar("NP_EnableSpellEnergizeEvents", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(2, 39, 0) then
	Nampower.cmdtable.args.advanced_options.args.unit_events = {
		type = "group",
		name = L["Unit Event Filters"],
		desc = L["Controls which unit identifiers trigger unit events (UNIT_HEALTH, UNIT_COMBAT, etc.). In the base game the same event can fire multiple times for the same unit, once per identifying string (e.g. 'party1', 'raid1', 'mouseover'). Disabling unused identifiers reduces redundant event calls. Note: 'player', 'target', and 'pet' (your own pet) always trigger regardless of these settings, as they are critical."],
		order = 200,
		args = {
			NP_EnableUnitEventsPet = {
				type = "toggle",
				name = L["Enable Pet Unit Events"],
				desc = L["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party and raid pet identifiers ('party1pet', 'raid1pet', etc.). Party pets additionally require Enable Party Unit Events to be on; raid pets additionally require Enable Raid Unit Events to be on. Your own pet ('pet') always fires events regardless of this setting."],
				order = 5,
				get = function()
					return GetCVar("NP_EnableUnitEventsPet") == "1"
				end,
				set = function(v)
					if v == true then
						SetCVar("NP_EnableUnitEventsPet", "1")
					else
						SetCVar("NP_EnableUnitEventsPet", "0")
					end
				end,
			},
			NP_EnableUnitEventsParty = {
				type = "toggle",
				name = L["Enable Party Unit Events"],
				desc = L["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for party member identifiers ('party1', 'party2', 'party3', 'party4'). Also required alongside Enable Pet Unit Events for party pet identifiers to fire."],
				order = 10,
				get = function()
					return GetCVar("NP_EnableUnitEventsParty") == "1"
				end,
				set = function(v)
					if v == true then
						SetCVar("NP_EnableUnitEventsParty", "1")
					else
						SetCVar("NP_EnableUnitEventsParty", "0")
					end
				end,
			},
			NP_EnableUnitEventsRaid = {
				type = "toggle",
				name = L["Enable Raid Unit Events"],
				desc = L["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for raid member identifiers ('raid1' through 'raid40'). Also required alongside Enable Pet Unit Events for raid pet identifiers to fire."],
				order = 15,
				get = function()
					return GetCVar("NP_EnableUnitEventsRaid") == "1"
				end,
				set = function(v)
					if v == true then
						SetCVar("NP_EnableUnitEventsRaid", "1")
					else
						SetCVar("NP_EnableUnitEventsRaid", "0")
					end
				end,
			},
			NP_EnableUnitEventsMouseover = {
				type = "toggle",
				name = L["Enable Mouseover Unit Events"],
				desc = L["Whether to fire unit events (UNIT_HEALTH, UNIT_COMBAT, etc.) for the 'mouseover' unit identifier."],
				order = 25,
				get = function()
					return GetCVar("NP_EnableUnitEventsMouseover") == "1"
				end,
				set = function(v)
					if v == true then
						SetCVar("NP_EnableUnitEventsMouseover", "1")
					else
						SetCVar("NP_EnableUnitEventsMouseover", "0")
					end
				end,
			},
			NP_EnableUnitEventsGuid = {
				type = "toggle",
				name = L["Enable GUID Unit Events"],
				desc = L["Whether to fire unit events (UNIT_HEALTH, UNIT_MANA, UNIT_AURA, etc.) using the raw GUID as the unit token, mirroring SuperWoW behavior. Fires for every unit the client tracks — not just named tokens like 'player', 'party1', 'raid1' — which can cause significant event spam in raids, BGs, and crowded zones. Older addons (e.g. pfUI) written for standard named tokens may have performance issues receiving GUID-based events. Addons needing GUID tracking (e.g. Automarker, Cursive) should use the new dedicated UNIT_HEALTH_GUID, UNIT_MANA_GUID, etc. events instead, allowing this to be safely disabled."],
				order = 30,
				get = function()
					return GetCVar("NP_EnableUnitEventsGuid") == "1"
				end,
				set = function(v)
					if v == true then
						SetCVar("NP_EnableUnitEventsGuid", "1")
					else
						SetCVar("NP_EnableUnitEventsGuid", "0")
					end
				end,
			},
			NP_EnableUnitEventsGuidFiltering = {
				type = "toggle",
				name = L["Enable GUID Unit Event Filtering"],
				desc = L["When enabled, suppresses high-frequency GUID events that cause spam in older addons — specifically UNIT_AURA, UNIT_HEALTH, UNIT_MANA, and similar events below UNIT_COMBAT, plus UNIT_NAME_UPDATE, UNIT_PORTRAIT_UPDATE, UNIT_INVENTORY_CHANGED, and PLAYER_GUILD_UPDATE. UNIT_COMBAT_GUID and other less frequent GUID events are still fired. Has no effect if Enable GUID Unit Events is disabled. This is a direct replacement for the 'Filter GUID Events' option in PerfBoost."],
				order = 35,
				get = function()
					return GetCVar("NP_EnableUnitEventsGuidFiltering") == "1"
				end,
				set = function(v)
					Nampower.db.profile.NP_EnableUnitEventsGuidFiltering = v
					if v == true then
						SetCVar("NP_EnableUnitEventsGuidFiltering", "1")
					else
						SetCVar("NP_EnableUnitEventsGuidFiltering", "0")
					end
				end,
			},
		},
	}
end

if Nampower:HasMinimumVersion(3, 1, 0) then
	Nampower.cmdtable.args.qol_options.args.NP_PreserveGreaterDemonAutocast = {
		type = "toggle",
		name = L["Preserve Greater Demon Autocast"],
		desc = L["Whether to remember and restore Felguard/Doomguard autocast preferences when swapping or resummoning those greater demons."],
		order = 25,
		get = function()
			return GetCVar("NP_PreserveGreaterDemonAutocast") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_PreserveGreaterDemonAutocast = v
			if v == true then
				SetCVar("NP_PreserveGreaterDemonAutocast", "1")
			else
				SetCVar("NP_PreserveGreaterDemonAutocast", "0")
			end
		end,
	}

end

if Nampower:HasMinimumVersion(4, 3, 0) then
	Nampower.cmdtable.args.qol_options.args.NP_EnableEnhancedTooltips = {
		type = "toggle",
		name = L["Enable Enhanced Tooltips"],
		desc = L["Whether to enable nampower's tooltip additions such as spell proc chance, ICD, and item cooldown text."],
		order = 30,
		get = function()
			return GetCVar("NP_EnableEnhancedTooltips") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_EnableEnhancedTooltips = v
			if v == true then
				SetCVar("NP_EnableEnhancedTooltips", "1")
			else
				SetCVar("NP_EnableEnhancedTooltips", "0")
			end
		end,
	}
end

if Nampower:HasMinimumVersion(3, 3, 0) then
	Nampower.cmdtable.args.chat_bubbles.args.ChatBubbles = {
		type = "toggle",
		name = L["Chat Bubbles (Say/Yell)"],
		desc = L["Whether to enable chat bubbles for /say and /yell messages."],
		order = 5,
		get = function()
			return GetCVar("ChatBubbles") == "1"
		end,
		set = function(v)
			Nampower.db.profile.ChatBubbles = v
			if v == true then
				SetCVar("ChatBubbles", "1")
			else
				SetCVar("ChatBubbles", "0")
			end
		end,
	}

	Nampower.cmdtable.args.chat_bubbles.args.ChatBubblesParty = {
		type = "toggle",
		name = L["Chat Bubbles (Party)"],
		desc = L["Whether to enable chat bubbles for /party messages."],
		order = 10,
		get = function()
			return GetCVar("ChatBubblesParty") == "1"
		end,
		set = function(v)
			Nampower.db.profile.ChatBubblesParty = v
			if v == true then
				SetCVar("ChatBubblesParty", "1")
			else
				SetCVar("ChatBubblesParty", "0")
			end
		end,
	}

	Nampower.cmdtable.args.chat_bubbles.args.NP_ChatBubblesWhisper = {
		type = "toggle",
		name = L["Chat Bubbles (Whisper)"],
		desc = L["Whether to enable chat bubbles for /whisper messages."],
		order = 15,
		get = function()
			return GetCVar("NP_ChatBubblesWhisper") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_ChatBubblesWhisper = v
			if v == true then
				SetCVar("NP_ChatBubblesWhisper", "1")
			else
				SetCVar("NP_ChatBubblesWhisper", "0")
			end
		end,
	}

	Nampower.cmdtable.args.chat_bubbles.args.NP_ChatBubblesRaid = {
		type = "toggle",
		name = L["Chat Bubbles (Raid)"],
		desc = L["Whether to enable chat bubbles for /raid messages."],
		order = 20,
		get = function()
			return GetCVar("NP_ChatBubblesRaid") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_ChatBubblesRaid = v
			if v == true then
				SetCVar("NP_ChatBubblesRaid", "1")
			else
				SetCVar("NP_ChatBubblesRaid", "0")
			end
		end,
	}

	Nampower.cmdtable.args.chat_bubbles.args.NP_ChatBubblesBattleground = {
		type = "toggle",
		name = L["Chat Bubbles (Battleground)"],
		desc = L["Whether to enable chat bubbles for battleground messages."],
		order = 25,
		get = function()
			return GetCVar("NP_ChatBubblesBattleground") == "1"
		end,
		set = function(v)
			Nampower.db.profile.NP_ChatBubblesBattleground = v
			if v == true then
				SetCVar("NP_ChatBubblesBattleground", "1")
			else
				SetCVar("NP_ChatBubblesBattleground", "0")
			end
		end,
	}

	Nampower.cmdtable.args.chat_bubbles.args.NP_ChatBubbleDistance = {
		type = "range",
		name = L["Chat Bubble Distance"],
		desc = L["The distance in yards to show chat bubbles"],
		order = 30,
		min = 5,
		max = 100,
		step = 1,
		get = function()
			local value = tonumber(GetCVar("NP_ChatBubbleDistance")) or 0
			return math.floor(value + 0.5)
		end,
		set = function(v)
			Nampower.db.profile.NP_ChatBubbleDistance = v
			SetCVar("NP_ChatBubbleDistance", v)
		end,
	}
else
	Nampower.cmdtable.args.chat_bubbles = nil
end

local deuce = Nampower:NewModule("Nampower Options Menu")
deuce.hasFuBar = IsAddOnLoaded("FuBar") and FuBar
deuce.consoleCmd = not deuce.hasFuBar

NampowerOptions = AceLibrary("AceAddon-2.0"):new("AceDB-2.0", "FuBarPlugin-2.0")
NampowerOptions.name = "FuBar - Nampower"
NampowerOptions.hasIcon = "Interface\\Icons\\inv_misc_book_04"
NampowerOptions.defaultMinimapPosition = 180
NampowerOptions.independentProfile = true
NampowerOptions.hideWithoutStandby = false

NampowerOptions:RegisterDB("NampowerSettingsDB")

NampowerOptions.OnMenuRequest = Nampower.cmdtable
local args = AceLibrary("FuBarPlugin-2.0"):GetAceOptionsDataTable(NampowerOptions)
for k, v in pairs(args) do
	if NampowerOptions.OnMenuRequest.args[k] == nil then
		NampowerOptions.OnMenuRequest.args[k] = v
	end
end
