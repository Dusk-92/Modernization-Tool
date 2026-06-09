if not Nampower then
	return
end

if not Nampower:HasMinimumVersion(2, 14, 0) then
	return
end

local function GetSpellMod(num)
	local modifierTypes = {
		[0] = "DAMAGE",
		[1] = "DURATION",
		[2] = "THREAT",
		[3] = "ATTACK_POWER",
		[4] = "CHARGES",
		[5] = "RANGE",
		[6] = "RADIUS",
		[7] = "CRITICAL_CHANCE",
		[8] = "ALL_EFFECTS",
		[9] = "NOT_LOSE_CASTING_TIME",
		[10] = "CASTING_TIME",
		[11] = "COOLDOWN",
		[12] = "SPEED",
		[14] = "COST",
		[15] = "CRIT_DAMAGE_BONUS",
		[16] = "RESIST_MISS_CHANCE",
		[17] = "JUMP_TARGETS",
		[18] = "CHANCE_OF_SUCCESS",
		[19] = "ACTIVATION_TIME",
		[20] = "EFFECT_PAST_FIRST",
		[21] = "CASTING_TIME_OLD",
		[22] = "DOT",
		[23] = "HASTE",
		[24] = "SPELL_BONUS_DAMAGE",
		[27] = "MULTIPLE_VALUE",
		[28] = "RESIST_DISPEL_CHANCE"
	}
	return modifierTypes[num] or "UNKNOWN"
end

function PrintTable(tbl, indent)
	indent = indent or 0
	local prefix = string.rep("  ", indent)

	for k, v in pairs(tbl) do
		if type(v) == "table" then
			print(prefix .. tostring(k) .. ":")
			PrintTable(v, indent + 1)
		else
			print(prefix .. tostring(k) .. ": " .. tostring(v))
		end
	end
end

if CombatLogAdd then
	function PrintTableToCombatLog(tbl, indent)
		indent = indent or 0
		local prefix = string.rep("  ", indent)

		for k, v in pairs(tbl) do
			if type(v) == "table" then
				CombatLogAdd(prefix .. tostring(k) .. ":")
				PrintTableToCombatLog(v, indent + 1)
			else
				CombatLogAdd(prefix .. tostring(k) .. ": " .. tostring(v))
			end
		end
	end

	function LogUnitData(unit)
		local data = GetUnitData(unit)
		if data then
			PrintTableToCombatLog(data)
		else
			print("No unit data available")
		end
	end

	function LogSpellData(spellId)
		local data = GetSpellRec(spellId)
		if data then
			PrintTableToCombatLog(data)
		else
			print("No spell data available")
		end
	end
end

function PrintBuffs(unit)
  for i = 1, 32 do
    local texture, stacks, spellId = UnitBuff(unit, i)
    if not texture then
      break
    end
    print(tostring(i) .. " " .. texture .. " " .. tostring(spellId))
  end
end

function PrintAuras(unit)
  local auras = GetUnitField(unit, "aura")
  local applications = GetUnitField(unit, "auraApplications")
  if not auras then return end
  for i, auraId in ipairs(auras) do
    local stacks = -1
    if applications then
      local stacks = (applications[i] or 0) + 1
    end
    if auraId > 0 then
      print(tostring(i) .. " " .. tostring(auraId) .. " x" .. tostring(stacks))
    end
  end
end

function PrintUnitData(unit)
	local data = GetUnitData(unit)
	if data then
		PrintTable(data)
	else
		print("No unit data available")
	end
end

function PrintSpellMods(spellId)
	for i = 0, 28 do
		local flatMod, percentMod, ret = GetSpellModifiers(spellId, i)
		if ret > 0 then
			print(GetSpellMod(i) .. " (" .. tostring(i) .. "): flat:" .. tostring(flatMod) .. " percent:" .. tostring(percentMod))
		end
	end
end

function PrintSpellData(spellId)
	local data = GetSpellRec(spellId)
	if data then
		PrintTable(data)
	else
		print("No spell data available")
	end
end

if not Nampower:HasMinimumVersion(2, 16, 0) then
	return
end

function PrintItemLocation(itemNameOrId)
	local bagIndex, slot = FindPlayerItemSlot(itemNameOrId)
	print(tostring(bagIndex) .. " " .. tostring(slot))
end

function PrintEquippedItems()
	local target = "player"
	if UnitExists("target") then
		target = "target"
	end
	local data = GetEquippedItems(target)
	PrintTable(data)
end

function LogEquippedItems()
	local target = "player"
	if UnitExists("target") then
		target = "target"
	end
	local data = GetEquippedItems(target)
	PrintTableToCombatLog(data)
end

function PrintBagItems()
	local data = GetBagItems()
	PrintTable(data)
end

function LogBagItems()
	local data = GetBagItems()
	PrintTableToCombatLog(data)
end

function TestBagItems(bagIndex)
  local items = GetBagItems(bagIndex)
  local numItemsChecked = 0
  for slot, itemData in pairs(items) do
    local itemLink = GetContainerItemLink(bagIndex, slot)
    if not itemLink then
      print(tostring(bagIndex) .. " " .. tostring(slot))
      PrintTable(itemData)
    end
    local _, _, itemId = strfind(itemLink, "(%d+):")
    numItemsChecked = numItemsChecked + 1
    if (tostring(itemData.itemId) ~= itemId) then
      print("Item mismatch at " .. tostring(bagIndex) .. " " .. tostring(slot) .. " " .. tostring(itemData.itemId) .. " " .. tostring(itemId))
      print(itemLink)
    end
  end
  print("checked " .. tostring(numItemsChecked) .. " items")
end

function TestAllBagItems()
  local data = GetBagItems()
  local numItemsChecked = 0
  for bagIndex, items in pairs(data) do
    for slot, itemData in pairs(items) do
      local itemLink = GetContainerItemLink(bagIndex, slot)
      if not itemLink then
        print(tostring(bagIndex) .. " " .. tostring(slot))
        PrintTable(itemData)
      end
      local _, _, itemId = strfind(itemLink, "(%d+):")
      numItemsChecked = numItemsChecked + 1
      if (tostring(itemData.itemId) ~= itemId) then
        print("Item mismatch at " .. tostring(bagIndex) .. " " .. tostring(slot) .. " " .. tostring(itemData.itemId) .. " " .. tostring(itemId))
        print(itemLink)
      end
    end
  end
  print("checked " .. tostring(numItemsChecked) .. " items")
end

function TestTrinkets()
  local data = GetTrinkets()
  for index, trinketData in pairs(data) do
    local bagIndex = trinketData.bagIndex
    local slot = trinketData.slotIndex
    local itemLink
    if bagIndex then
      itemLink = GetContainerItemLink(bagIndex, slot)
    else
      itemLink = GetInventoryItemLink("player", slot)
    end
    local _, _, itemId = strfind(itemLink, "(%d+):")
    if (tostring(trinketData.itemId) ~= itemId) then
      print("Trinket mismatch at " .. tostring(bagIndex) .. " " .. tostring(slot) .. " " .. tostring(itemData.itemId) .. " " .. tostring(itemId))
      print(itemLink)
    end
  end
end

if not Nampower:HasMinimumVersion(2, 17, 0) then
	return
end

function PrintCastInfo()
	local data = GetCastInfo()
	if data then
		PrintTable(data)
	end
end

function PrintSpellCooldown(spellId)
	local data = GetSpellIdCooldown(spellId)
	if data then
		PrintTable(data)
	end
end

function PrintItemCooldown(itemId)
	local data = GetItemIdCooldown(itemId)
	if data then
		PrintTable(data)
	end
end

function PrintTrinketCooldown(trinketId)
	local data = GetTrinketCooldown(trinketId)
	if data then
		PrintTable(data)
	end
end

function PrintTrinkets()
	local data = GetTrinkets(1)
	if data then
		PrintTable(data)
	end
end

if not Nampower:HasMinimumVersion(2, 24, 0) then
	return
end

-- Auto Attack Event Constants
local HITINFO_NORMALSWING = 0
local HITINFO_UNK0 = 1
local HITINFO_AFFECTS_VICTIM = 2
local HITINFO_LEFTSWING = 4
local HITINFO_UNK3 = 8
local HITINFO_MISS = 16
local HITINFO_ABSORB = 32
local HITINFO_RESIST = 64
local HITINFO_CRITICALHIT = 128
local HITINFO_UNK8 = 256
local HITINFO_UNK9 = 8192
local HITINFO_GLANCING = 16384
local HITINFO_CRUSHING = 32768
local HITINFO_NOACTION = 65536
local HITINFO_SWINGNOHITSOUND = 524288

local VICTIMSTATE_UNAFFECTED = 0
local VICTIMSTATE_NORMAL = 1
local VICTIMSTATE_DODGE = 2
local VICTIMSTATE_PARRY = 3
local VICTIMSTATE_INTERRUPT = 4
local VICTIMSTATE_BLOCKS = 5
local VICTIMSTATE_EVADES = 6
local VICTIMSTATE_IS_IMMUNE = 7
local VICTIMSTATE_DEFLECTS = 8

local victimStateNames = {
	[0] = "Unaffected",
	[1] = "Normal",
	[2] = "Dodged",
	[3] = "Parried",
	[4] = "Interrupted",
	[5] = "Blocked",
	[6] = "Evaded",
	[7] = "Immune",
	[8] = "Deflected"
}

function GetHitType(hitInfo)
	local isCrit = bit.band(hitInfo, HITINFO_CRITICALHIT) ~= 0
	local isGlancing = bit.band(hitInfo, HITINFO_GLANCING) ~= 0
	local isCrushing = bit.band(hitInfo, HITINFO_CRUSHING) ~= 0
	local isMiss = bit.band(hitInfo, HITINFO_MISS) ~= 0
	local isOffHand = bit.band(hitInfo, HITINFO_LEFTSWING) ~= 0

	local hitType = "Normal"
	if isMiss then
		hitType = "Miss"
	elseif isCrit then
		hitType = "Critical"
	elseif isGlancing then
		hitType = "Glancing"
	elseif isCrushing then
		hitType = "Crushing"
	end

	if isOffHand then
		hitType = hitType .. " (Off-hand)"
	end

	return hitType
end

function GetVictimStateName(victimState)
	return victimStateNames[victimState] or "Unknown"
end

local function onAutoAttack(attackerGuid, targetGuid, totalDamage, hitInfo, victimState, subDamageCount, blockedAmount, totalAbsorb, totalResist)
	local hitType = GetHitType(hitInfo)
	local victimStateName = GetVictimStateName(victimState)

	print(string.format(
		"Auto Attack: %s -> %s | %d damage (%s) | State: %s | SubDmg: %d | Absorbed: %d | Resisted: %d | Blocked: %d",
		attackerGuid, targetGuid, totalDamage, hitType, victimStateName,
		subDamageCount, totalAbsorb, totalResist, blockedAmount
	))
end

-- helpful event hooks for debugging
--Nampower:RegisterEvent("UNIT_CASTEVENT", function(casterGuid, targetGuid, event, spellID, castDuration)
--  if(casterGuid=="0x00000000001CD43C") then
--    print("CASTEVENT: " .. tostring(casterGuid) .. " -> " .. tostring(targetGuid) .. " event: " .. tostring(event) .. " spellID: " .. tostring(spellID) .. " castDuration: " .. tostring(castDuration))
--  end
--end)

--Nampower:RegisterEvent("AURA_CAST_ON_OTHER", function(spellId, caster, target, effect, effectname)
--  local unitName = target and UnitName(target) or ""
--  print("AURA_CAST_ON_OTHER: " .. tostring(spellId) .. " " .. tostring(GetSpellRecField(spellId, "name")) .. " by " .. tostring(UnitName(caster)) .. " on " .. unitName .. " effect: " .. tostring(effect) .. " effectname: " .. tostring(effectname))
--end)
--
--Nampower:RegisterEvent("AURA_CAST_ON_SELF", function(spellId, caster, target, effect, effectname)
--    local unitName = target and UnitName(target) or ""
--  print("AURA_CAST_ON_SELF: " .. tostring(spellId) .. " " .. tostring(GetSpellRecField(spellId, "name")) .. " by " .. tostring(UnitName(caster)) .. " on " .. unitName .. " effect: " .. tostring(effect) .. " effectname: " .. tostring(effectname))
--end)
--

--Nampower:RegisterEvent("AUTO_ATTACK_SELF", onAutoAttack)
--Nampower:RegisterEvent("AUTO_ATTACK_OTHER", onAutoAttack)

if not Nampower:HasMinimumVersion(2, 25, 0) then
	return
end

local spellTypeNames = {
	[0] = "Normal",
	[1] = "Channeling",
	[2] = "Autorepeating",
}

local function onSpellStart(itemId, spellId, casterGuid, targetGuid, castFlags, castTime, duration, spellType, corpseOwnerGuid)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	local spellTypeName = spellTypeNames[spellType] or "Unknown"
  local caster = UnitName(casterGuid) or tostring(casterGuid)
  local target = UnitName(targetGuid) or tostring(targetGuid)
  local corpse = nil
  if corpseOwnerGuid then
    	corpse = UnitName(corpseOwnerGuid) or tostring(corpseOwnerGuid)
  end
  print(string.format(
      "SPELL_START: %s (id:%d) | Caster: %s -> Target: %s | ItemId: %d | Flags: %d | CastTime: %dms | Duration: %dms | Type: %s | CorpseOwner: %s",
      tostring(spellName), spellId, caster, target, itemId, castFlags, castTime, duration, spellTypeName, tostring(corpse)
  ))
end

local function onSpellGo(itemId, spellId, casterGuid, targetGuid, castFlags, numTargetsHit, numTargetsMissed, corpseOwnerGuid)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
  local caster = UnitName(casterGuid) or tostring(casterGuid)
  local target = UnitName(targetGuid) or tostring(targetGuid)
  local corpse = nil
  if corpseOwnerGuid then
    	corpse = UnitName(corpseOwnerGuid) or tostring(corpseOwnerGuid)
  end
  print(string.format(
      "SPELL_GO: %s (id:%d) | Caster: %s -> Target: %s | ItemId: %d | Flags: %d | Hit: %d | Missed: %d | CorpseOwner: %s",
      tostring(spellName), spellId, caster, target, itemId, castFlags, numTargetsHit, numTargetsMissed, tostring(corpse)
  ))
end

local function onSpellFailedSelf(spellId, spellResult, failedByServer)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	local source = failedByServer == 1 and "Server" or "Client"
	print(string.format(
		"SPELL_FAILED_SELF: %s (id:%d) | Result: %d | Source: %s",
		tostring(spellName), spellId, spellResult, source
	))
end

local function onSpellFailedOther(casterGuid, spellId)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	print(string.format(
		"SPELL_FAILED_OTHER: %s (id:%d) | Caster: %s",
		tostring(spellName), spellId, casterGuid
	))
end

local function onSpellDelayed(casterGuid, delayMs)
	print(string.format(
		"SPELL_DELAYED: Caster: %s | Delay: %dms",
		casterGuid, delayMs
	))
end

local function onSpellChannelStart(spellId, targetGuid, durationMs)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	print(string.format(
		"SPELL_CHANNEL_START: %s (id:%d) | Target: %s | Duration: %dms",
		tostring(spellName), spellId, targetGuid, durationMs
	))
end

local function onSpellChannelUpdate(spellId, targetGuid, remainingMs)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	print(string.format(
		"SPELL_CHANNEL_UPDATE: %s (id:%d) | Target: %s | Remaining: %dms",
		tostring(spellName), spellId, targetGuid, remainingMs
	))
end

--Nampower:RegisterEvent("SPELL_START_SELF", onSpellStart)
--Nampower:RegisterEvent("SPELL_START_OTHER", onSpellStart)
--Nampower:RegisterEvent("SPELL_GO_SELF", onSpellGo)
--Nampower:RegisterEvent("SPELL_GO_OTHER", onSpellGo)
--Nampower:RegisterEvent("SPELL_FAILED_SELF", onSpellFailedSelf)
--Nampower:RegisterEvent("SPELL_FAILED_OTHER", onSpellFailedOther)
--Nampower:RegisterEvent("SPELL_DELAYED_SELF", onSpellDelayed)
--Nampower:RegisterEvent("SPELL_DELAYED_OTHER", onSpellDelayed)
--Nampower:RegisterEvent("SPELL_CHANNEL_START", onSpellChannelStart)
--Nampower:RegisterEvent("SPELL_CHANNEL_UPDATE", onSpellChannelUpdate)

if not Nampower:HasMinimumVersion(2, 26, 0) then
	return
end

-- Spell Heal Events (gated behind NP_EnableSpellHealEvents CVar, default 0)
-- SPELL_HEAL_BY_SELF - Fires when the active player is the caster (you healed someone)
-- SPELL_HEAL_BY_OTHER - Fires when someone other than the active player is the caster (someone else healed someone)
-- SPELL_HEAL_ON_SELF - Fires when the active player is the target (you received a heal)
-- Note: SPELL_HEAL_BY_SELF and SPELL_HEAL_ON_SELF can both fire for the same heal if you heal yourself

local function createSpellHealHandler(eventName)
	return function(targetGuid, casterGuid, spellId, amount, critical, periodic)
		local critText = critical == 1 and " (CRIT)" or ""
		local periodicText = periodic == 1 and " (PERIODIC)" or ""
		local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
		print(string.format(
			"%s: %s healed %s for %d with %s%s%s",
			eventName, UnitName(casterGuid), UnitName(targetGuid), amount, tostring(spellName), critText, periodicText
		))
	end
end

-- Spell Energize Events (gated behind NP_EnableSpellEnergizeEvents CVar, default 0)
-- SPELL_ENERGIZE_BY_SELF - Fires when the active player is the caster (you restored power to someone)
-- SPELL_ENERGIZE_BY_OTHER - Fires when someone other than the active player is the caster (someone else restored power)
-- SPELL_ENERGIZE_ON_SELF - Fires when the active player is the target (you received power)
-- Note: SPELL_ENERGIZE_BY_SELF and SPELL_ENERGIZE_ON_SELF can both fire for the same energize if you restore power to yourself

-- Power Type Constants
local POWER_MANA = 0
local POWER_RAGE = 1
local POWER_FOCUS = 2
local POWER_ENERGY = 3
local POWER_HAPPINESS = 4
local POWER_HEALTH = -2 -- 0xFFFFFFFE as unsigned

local POWER_NAMES = {
	[0] = "Mana",
	[1] = "Rage",
	[2] = "Focus",
	[3] = "Energy",
	[4] = "Happiness",
	[-2] = "Health",
}

function GetPowerTypeName(powerType)
	return POWER_NAMES[powerType] or "Unknown"
end

local function createSpellEnergizeHandler(eventName)
	return function(targetGuid, casterGuid, spellId, powerType, amount, periodic)
		local powerName = GetPowerTypeName(powerType)
		local periodicText = periodic == 1 and " (PERIODIC)" or ""
		local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
		print(string.format(
			"%s: %s restored %d %s to %s with %s%s",
			eventName, UnitName(casterGuid), amount, powerName, UnitName(targetGuid), tostring(spellName), periodicText
		))
	end
end

--Nampower:RegisterEvent("SPELL_HEAL_BY_SELF", createSpellHealHandler("SPELL_HEAL_BY_SELF"))
--Nampower:RegisterEvent("SPELL_HEAL_BY_OTHER", createSpellHealHandler("SPELL_HEAL_BY_OTHER"))
--Nampower:RegisterEvent("SPELL_HEAL_ON_SELF", createSpellHealHandler("SPELL_HEAL_ON_SELF"))
--Nampower:RegisterEvent("SPELL_ENERGIZE_BY_SELF", createSpellEnergizeHandler("SPELL_ENERGIZE_BY_SELF"))
--Nampower:RegisterEvent("SPELL_ENERGIZE_BY_OTHER", createSpellEnergizeHandler("SPELL_ENERGIZE_BY_OTHER"))
--Nampower:RegisterEvent("SPELL_ENERGIZE_ON_SELF", createSpellEnergizeHandler("SPELL_ENERGIZE_ON_SELF"))

if not Nampower:HasMinimumVersion(2, 30, 0) then
	return
end

-- Aura Duration Update Events
-- BUFF_UPDATE_DURATION_SELF - aura slot 0-31
-- DEBUFF_UPDATE_DURATION_SELF - aura slot 32-47
-- Parameters: auraSlot, durationMs, expirationTimeMs

local function createAuraDurationHandler(eventName)
	return function(auraSlot, durationMs, expirationTimeMs)
		print(string.format(
			"%s: slot %d | Duration: %dms | Expires: %d",
			eventName, auraSlot, durationMs, expirationTimeMs
		))
	end
end
--
--Nampower:RegisterEvent("DEBUFF_UPDATE_DURATION_SELF", createAuraDurationHandler("DEBUFF_UPDATE_DURATION_SELF"))
--Nampower:RegisterEvent("BUFF_UPDATE_DURATION_SELF", createAuraDurationHandler("BUFF_UPDATE_DURATION_SELF"))

-- Aura Added/Removed Events
-- BUFF_ADDED_SELF, BUFF_REMOVED_SELF, BUFF_ADDED_OTHER, BUFF_REMOVED_OTHER
-- DEBUFF_ADDED_SELF, DEBUFF_REMOVED_SELF, DEBUFF_ADDED_OTHER, DEBUFF_REMOVED_OTHER
-- Parameters: guid, luaSlot, spellId, stackCount, auraLevel, auraSlot

local function createAuraChangeHandler(eventName)
	return function(guid, luaSlot, spellId, stackCount, auraLevel, auraSlot)
		local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
		print(string.format(
			"%s: %s | luaSlot %d | %s (id:%d) | Stacks: %d | Level: %d | auraSlot: %d",
			eventName, guid, luaSlot, tostring(spellName), spellId, stackCount, auraLevel, auraSlot
		))
	end
end

--Nampower:RegisterEvent("BUFF_ADDED_SELF", createAuraChangeHandler("BUFF_ADDED_SELF"))
--Nampower:RegisterEvent("BUFF_REMOVED_SELF", createAuraChangeHandler("BUFF_REMOVED_SELF"))
--Nampower:RegisterEvent("BUFF_ADDED_OTHER", createAuraChangeHandler("BUFF_ADDED_OTHER"))
--Nampower:RegisterEvent("BUFF_REMOVED_OTHER", createAuraChangeHandler("BUFF_REMOVED_OTHER"))
--Nampower:RegisterEvent("DEBUFF_ADDED_SELF", createAuraChangeHandler("DEBUFF_ADDED_SELF"))
--Nampower:RegisterEvent("DEBUFF_REMOVED_SELF", createAuraChangeHandler("DEBUFF_REMOVED_SELF"))
--Nampower:RegisterEvent("DEBUFF_ADDED_OTHER", createAuraChangeHandler("DEBUFF_ADDED_OTHER"))
--Nampower:RegisterEvent("DEBUFF_REMOVED_OTHER", createAuraChangeHandler("DEBUFF_REMOVED_OTHER"))

-- Spell Damage Events (gated behind NP_EnableSpellDamageEvents CVar, default 0)
-- SPELL_DAMAGE_EVENT_SELF - Fires when the active player deals spell damage
-- SPELL_DAMAGE_EVENT_OTHER - Fires when someone other than the active player deals spell damage

-- Spell Damage Hit Info Constants
local SPELL_DAMAGE_HIT_NORMAL = 0
local SPELL_DAMAGE_HIT_CRIT = 2

-- Spell School Constants
local SPELL_SCHOOL_NORMAL = 0
local SPELL_SCHOOL_HOLY = 1
local SPELL_SCHOOL_FIRE = 2
local SPELL_SCHOOL_NATURE = 3
local SPELL_SCHOOL_FROST = 4
local SPELL_SCHOOL_SHADOW = 5
local SPELL_SCHOOL_ARCANE = 6

local SPELL_SCHOOL_NAMES = {
	[0] = "Physical",
	[1] = "Holy",
	[2] = "Fire",
	[3] = "Nature",
	[4] = "Frost",
	[5] = "Shadow",
	[6] = "Arcane",
}

function GetSpellSchoolName(spellSchool)
	return SPELL_SCHOOL_NAMES[spellSchool] or "Unknown"
end

local function createSpellDamageHandler(eventName)
	return function(targetGuid, casterGuid, spellId, amount, mitigationStr, hitInfo, spellSchool, effectAuraStr)
		local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
		local schoolName = GetSpellSchoolName(spellSchool)
		local critText = hitInfo == SPELL_DAMAGE_HIT_CRIT and " (CRIT)" or ""
		print(string.format(
			"%s: %s -> %s | %s (id:%d) | %d %s damage%s | Mitigation: %s | HitInfo: %d | Effects: %s",
			eventName, casterGuid, targetGuid, tostring(spellName), spellId, amount, schoolName, critText, mitigationStr, hitInfo, effectAuraStr
		))
	end
end

--Nampower:RegisterEvent("SPELL_DAMAGE_EVENT_SELF", createSpellDamageHandler("SPELL_DAMAGE_EVENT_SELF"))
--Nampower:RegisterEvent("SPELL_DAMAGE_EVENT_OTHER", createSpellDamageHandler("SPELL_DAMAGE_EVENT_OTHER"))

if not Nampower:HasMinimumVersion(2, 31, 0) then
	return
end

-- Spell Miss Events (gated behind NP_EnableSpellMissEvents CVar, default 0)
-- SPELL_MISS_SELF - Fires when the active player's spell misses/resists/is immune/etc
-- SPELL_MISS_OTHER - Fires when someone else's spell misses/resists/is immune/etc
-- Triggered by SMSG_SPELLLOGMISS, SMSG_PROCRESIST, and SMSG_SPELLORDAMAGE_IMMUNE

-- SpellMissInfo Constants
local SPELL_MISS_NONE = 0
local SPELL_MISS_MISS = 1
local SPELL_MISS_RESIST = 2
local SPELL_MISS_DODGE = 3
local SPELL_MISS_PARRY = 4
local SPELL_MISS_BLOCK = 5
local SPELL_MISS_EVADE = 6
local SPELL_MISS_IMMUNE = 7
local SPELL_MISS_IMMUNE2 = 8
local SPELL_MISS_DEFLECT = 9
local SPELL_MISS_ABSORB = 10
local SPELL_MISS_REFLECT = 11

local SPELL_MISS_NAMES = {
	[0] = "None",
	[1] = "Miss",
	[2] = "Resist",
	[3] = "Dodge",
	[4] = "Parry",
	[5] = "Block",
	[6] = "Evade",
	[7] = "Immune",
	[8] = "Immune",
	[9] = "Deflect",
	[10] = "Absorb",
	[11] = "Reflect",
}

function GetSpellMissName(missInfo)
	return SPELL_MISS_NAMES[missInfo] or "Unknown"
end

local function createSpellMissHandler(eventName)
	return function(casterGuid, targetGuid, spellId, missInfo)
		local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
		local missName = GetSpellMissName(missInfo)
		print(string.format(
			"%s: %s -> %s | %s (id:%d) | %s",
			eventName, UnitName(casterGuid), UnitName(targetGuid), tostring(spellName), spellId, missName
		))
	end
end

--Nampower:RegisterEvent("SPELL_MISS_SELF", createSpellMissHandler("SPELL_MISS_SELF"))
--Nampower:RegisterEvent("SPELL_MISS_OTHER", createSpellMissHandler("SPELL_MISS_OTHER"))

if not Nampower:HasMinimumVersion(2, 39, 0) then
  return
end

-- UNIT_INVENTORY_CHANGED - fires when a unit's inventory changes (standard named token variant)
-- Parameters: unit (string) - unit token like "player", "target", "party1", etc.

-- UNIT_INVENTORY_CHANGED_GUID - fires when a unit's inventory changes (GUID variant)
-- Parameters:
--   guid        (string) - unit GUID e.g. "0xF5300000000000A5"
--   isPlayer    (int)    - 1 if the unit is the active player, 0 otherwise
--   isTarget    (int)    - 1 if the unit is the current locked target, 0 otherwise
--   isMouseover (int)    - 1 if the unit is the current mouseover, 0 otherwise
--   isPet       (int)    - 1 if the unit is the active player's pet, 0 otherwise
--   partyIndex  (int)    - party slot (1-4) if the unit is a party member, 0 otherwise
--   raidIndex   (int)    - raid slot (1-40) if the unit is a raid member, 0 otherwise

local function onUnitInventoryChanged(unit)
  print(string.format("UNIT_MODEL_CHANGED: %s", unit))
end

local function onUnitInventoryChangedGuid(guid, isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex)
  print(string.format(
      "UNIT_MODEL_CHANGED_GUID: %s | isPlayer:%d isTarget:%d isMouseover:%d isPet:%d party:%d raid:%d",
      guid, isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex
  ))
end

--Nampower:RegisterEvent("UNIT_MODEL_CHANGED", onUnitInventoryChanged)
--Nampower:RegisterEvent("UNIT_MODEL_CHANGED_GUID", onUnitInventoryChangedGuid)

-- UNIT_MANA - fires when a unit's mana changes (standard named token variant)
-- Parameters: unit (string) - unit token like "player", "target", "party1", etc.

-- UNIT_MANA_GUID - fires when a unit's mana changes (GUID variant)
-- Parameters:
--   guid        (string) - unit GUID e.g. "0xF5300000000000A5"
--   isPlayer    (int)    - 1 if the unit is the active player, 0 otherwise
--   isTarget    (int)    - 1 if the unit is the current locked target, 0 otherwise
--   isMouseover (int)    - 1 if the unit is the current mouseover, 0 otherwise
--   isPet       (int)    - 1 if the unit is the active player's pet, 0 otherwise
--   partyIndex  (int)    - party slot (1-4) if the unit is a party member, 0 otherwise
--   raidIndex   (int)    - raid slot (1-40) if the unit is a raid member, 0 otherwise

local function onUnitMana(unit)
	print(string.format("UNIT_MANA: %s", unit))
end

local function onUnitManaGuid(guid, isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex)
  if UnitName(guid) == "Tankeboy" or  UnitName(guid) == "Icansummon" then
    print(string.format(
        "UNIT_MANA_GUID: %s | isPlayer:%d isTarget:%d isMouseover:%d isPet:%d party:%d raid:%d",
        UnitName(guid), isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex
    ))
  end
end

--Nampower:RegisterEvent("UNIT_MANA", onUnitMana)
--Nampower:RegisterEvent("UNIT_MANA_GUID", onUnitManaGuid)

-- UNIT_COMBAT - fires when a unit participates in combat (standard named token variant)
-- Parameters:
--   unit     (string) - unit token like "player", "target", "party1", etc.
--   action   (string) - e.g. "WOUND", "MISS", "DODGE", "PARRY", "BLOCK", "EVADE", "IMMUNE", "REFLECT", "ABSORB", "INTERRUPT"
--   critical (string) - "CRITICAL" if a crit, "" otherwise
--   damage   (int)    - raw damage amount (0 for non-damaging outcomes)
--   school   (int)    - damage school (0=Physical, 1=Holy, 2=Fire, 3=Nature, 4=Frost, 5=Shadow, 6=Arcane)

-- UNIT_COMBAT_GUID - fires once per combat feedback event, identified by GUID
-- Unlike other GUID events, carries full combat detail rather than unit membership flags.
-- Parameters:
--   guid       (string) - unit GUID e.g. "0xF5300000000000A5"
--   action     (string) - e.g. "WOUND", "MISS", "DODGE", "PARRY", "BLOCK", "EVADE", "IMMUNE", "REFLECT", "ABSORB", "INTERRUPT"
--   damage     (int)    - raw damage amount (0 for non-damaging outcomes like dodge/miss)
--   school     (int)    - damage school (0=Physical, 1=Holy, 2=Fire, 3=Nature, 4=Frost, 5=Shadow, 6=Arcane)
--   hitInfo    (int)    - hit info bitfield
--   isInteract (int)    - 1 if the unit matches the current interact target, 0 otherwise
--   isPet      (int)    - 1 if the unit is the active player's pet, 0 otherwise
--   partyIndex (int)    - party slot (1-4) if the unit is a party member, 0 otherwise
--   raidIndex  (int)    - raid slot (1-40) if the unit is a raid member, 0 otherwise

local function onUnitCombat(unit, action, critical, damage, school)
  local schoolName = GetSpellSchoolName(school)
  local critText = critical == "CRITICAL" and " (CRIT)" or ""
  print(string.format(
      "UNIT_COMBAT: %s | %s | %d %s damage%s",
      unit, action, damage, schoolName, critText
  ))
end

local function onUnitCombatGuid(guid, action, damage, school, hitInfo, isInteract, isPet, partyIndex, raidIndex)
  local name = UnitName(guid)
  local schoolName = GetSpellSchoolName(school)
  print(string.format(
      "UNIT_COMBAT_GUID: %s | %s | %d %s | hitInfo:%d isInteract:%d isPet:%d party:%d raid:%d",
      name, action, damage, schoolName, hitInfo, isInteract, isPet, partyIndex, raidIndex
  ))
end

--Nampower:RegisterEvent("UNIT_COMBAT", onUnitCombat)
--Nampower:RegisterEvent("UNIT_COMBAT_GUID", onUnitCombatGuid)

-- SPELL_CAST_EVENT - fires when you (or certain pets) initiate a spell cast
-- Triggered client-side before the cast is sent to the server.
-- Only fires for spells you initiated.
-- Parameters:
--   success    (int)    - 1 if cast succeeded, 0 if failed
--   spellId    (int)    - spell ID
--   castType   (int)    - see Cast Type Constants below
--   targetGuid (string) - guid string like "0xF5300000000000A5"
--   itemId     (int)    - item ID that triggered the spell, 0 if not item-triggered

-- Cast Type Constants
local CAST_TYPE_NORMAL            = 0
local CAST_TYPE_NON_GCD           = 1
local CAST_TYPE_ON_SWING          = 2
local CAST_TYPE_CHANNEL           = 3
local CAST_TYPE_TARGETING         = 4
local CAST_TYPE_TARGETING_NON_GCD = 5

local CAST_TYPE_NAMES = {
	[0] = "Normal",
	[1] = "NonGCD",
	[2] = "OnSwing",
	[3] = "Channel",
	[4] = "Targeting",
	[5] = "TargetingNonGCD",
}

function GetCastTypeName(castType)
	return CAST_TYPE_NAMES[castType] or "Unknown"
end

local function onSpellCastEvent(success, spellId, castType, targetGuid, itemId)
	local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
	local castTypeName = GetCastTypeName(castType)
	local successText = success == 1 and "OK" or "FAILED"
	local itemText = itemId ~= 0 and (" | Item: " .. tostring(itemId)) or ""
	print(string.format(
		"SPELL_CAST_EVENT: [%s] %s (id:%d) | Type: %s | Target: %s%s",
		successText, tostring(spellName), spellId, castTypeName, tostring(targetGuid), itemText
	))
end

--Nampower:RegisterEvent("SPELL_CAST_EVENT", onSpellCastEvent)

-- UNIT_AURA_GUID - fires when a unit's aura state changes (GUID variant)
-- All GUID events share the same parameter format:
--   guid        (string) - unit guid like "0xF5300000000000A5"
--   isPlayer    (int)    - 1 if the unit is the active player, 0 otherwise
--   isTarget    (int)    - 1 if the unit is the current locked target, 0 otherwise
--   isMouseover (int)    - 1 if the unit is the current mouseover, 0 otherwise
--   isPet       (int)    - 1 if the unit is the active player's pet, 0 otherwise
--   partyIndex  (int)    - party slot (1-4) if the unit is a party member, 0 otherwise
--   raidIndex   (int)    - raid slot (1-40) if the unit is a raid member, 0 otherwise
local function onUnitGuid(guid, isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex)
  isPlayer = isPlayer or 0
  isTarget = isTarget or 0
  isMouseover = isMouseover or 0
  isPet = isPet or 0
  partyIndex = partyIndex or 0
  raidIndex = raidIndex or 0
  print(string.format(
      "%s: %s | isPlayer:%d isTarget:%d isMouseover:%d isPet:%d party:%d raid:%d",
      "UNIT_AURA_GUID", tostring(UnitName(guid) or guid), isPlayer, isTarget, isMouseover, isPet, partyIndex, raidIndex
  ))
end

--Nampower:RegisterEvent("UNIT_AURA_GUID", onUnitGuid)

if not Nampower:HasMinimumVersion(3, 4, 0) then
  return
end

-- ENVIRONMENTAL_DMG_SELF / ENVIRONMENTAL_DMG_OTHER
-- Parameters:
--   unitGuid (string) - guid of the unit that took damage
--   dmgType  (int)    - environmental damage type
--   damage   (int)    - amount of damage taken
--   absorb   (int)    - amount of damage absorbed
--   resist   (int)    - amount of damage resisted
local ENV_DMG_NAMES = {
  [0] = "Exhausted",
  [1] = "Drowning",
  [2] = "Fall",
  [3] = "Lava",
  [4] = "Slime",
  [5] = "Fire",
  [6] = "FallToVoid",
}

local function onEnvironmentalDmg(unitGuid, dmgType, damage, absorb, resist)
  dmgType = dmgType or -1
  damage = damage or 0
  absorb = absorb or 0
  resist = resist or 0
  print(string.format(
      "ENVIRONMENTAL_DMG: %s took %d %s damage (absorbed:%d resisted:%d)",
      tostring(unitGuid), damage, ENV_DMG_NAMES[dmgType] or "Unknown", absorb, resist
  ))
end

--Nampower:RegisterEvent("ENVIRONMENTAL_DMG_SELF", onEnvironmentalDmg)
--Nampower:RegisterEvent("ENVIRONMENTAL_DMG_OTHER", onEnvironmentalDmg)

-- DAMAGE_SHIELD_SELF / DAMAGE_SHIELD_OTHER
-- Parameters:
--   unitGuid    (string) - guid of shield owner
--   targetGuid  (string) - guid of attacker taking reflected damage
--   damage      (int)    - amount of shield damage dealt
--   spellSchool (int)    - school of shield damage
local SCHOOL_NAMES = {
  [0] = "Physical",
  [1] = "Holy",
  [2] = "Fire",
  [3] = "Nature",
  [4] = "Frost",
  [5] = "Shadow",
  [6] = "Arcane",
}

local function onDamageShield(unitGuid, targetGuid, damage, spellSchool)
  damage = damage or 0
  spellSchool = spellSchool or -1
  print(string.format(
      "DAMAGE_SHIELD: %s dealt %d %s damage to %s",
      tostring(unitGuid), damage, SCHOOL_NAMES[spellSchool] or "Unknown", tostring(targetGuid)
  ))
end

--Nampower:RegisterEvent("DAMAGE_SHIELD_SELF", onDamageShield)
--Nampower:RegisterEvent("DAMAGE_SHIELD_OTHER", onDamageShield)

-- SPELL_DISPEL_BY_SELF / SPELL_DISPEL_BY_OTHER
-- Parameters:
--   casterGuid (string) - guid of dispel caster
--   targetGuid (string) - guid of dispelled unit
--   spellId    (int)    - dispelled spell id
local function onSpellDispel(casterGuid, targetGuid, spellId)
  spellId = spellId or 0
  local spellName = GetSpellRecField and GetSpellRecField(spellId, "name") or spellId
  print(string.format(
      "SPELL_DISPEL_BY: %s dispelled %s (id:%d) from %s",
      tostring(casterGuid), tostring(spellName), spellId, tostring(targetGuid)
  ))
end

--Nampower:RegisterEvent("SPELL_DISPEL_BY_SELF", onSpellDispel)
--Nampower:RegisterEvent("SPELL_DISPEL_BY_OTHER", onSpellDispel)

-- PrintSpellRange(rangeIndex)
-- Prints the SpellRange DBC record for the given index using GetSpellRangeData.
-- GetSpellRangeData returns: minRange, maxRange, flags, name
function PrintSpellRange(rangeIndex)
  if not GetSpellRangeData then
    print("GetSpellRangeData is not available")
    return
  end
  local minRange, maxRange, flags, name = GetSpellRangeData(rangeIndex)
  if minRange == nil then
    print(string.format("PrintSpellRange(%d): no record found", rangeIndex))
    return
  end
  print(string.format(
      "SpellRange[%d]: name=%q  min=%.2f  max=%.2f  flags=0x%08X",
      rangeIndex, tostring(name), minRange, maxRange, flags
  ))
end
