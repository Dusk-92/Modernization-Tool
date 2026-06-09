--[[
    UnitXP Service Pack 3 Lua Addon

    By allfox, and the thankful community
]] --
UnitXP_SP3_Addon = nil; -- It's a SavedVariable, not local
UnitXP_SP3_Icon = nil; -- It's a SavedVariable, not local

local function UnitXP_SP3_Print(msg)
    if not DEFAULT_CHAT_FRAME then
        return;
    end
    DEFAULT_CHAT_FRAME:AddMessage(tostring(msg));
end

-- Bindings
BINDING_HEADER_UNITXPSP3TARGETING = "UnitXP SP3 Targeting Functions";
BINDING_NAME_UNITXPSP3NEARESTENEMY = "Nearest Enemy";
BINDING_NAME_UNITXPSP3TARGETMOSTHP = "The enemy with most HP";
BINDING_NAME_UNITXPSP3WORLDBOSS = "World Boss";
BINDING_NAME_UNITXPSP3NEXTMARKER = "Next Target Marker";
BINDING_NAME_UNITXPSP3PREVIOUSMARKER = "Previous Target Marker";
BINDING_NAME_UNITXPSP3NEXTENEMY = "Next Enemy";
BINDING_NAME_UNITXPSP3PREVIOUSENEMY = "Previous Enemy";
BINDING_NAME_UNITXPSP3NEXTMELEE = "Next Enemy Prioritizing Melee";
BINDING_NAME_UNITXPSP3PREVIOUSMELEE = "Previous Enemy Prioritizing Melee";
BINDING_HEADER_UNITXPSP3UTILITIES = "UnitXP SP3 Utilities";
BINDING_NAME_UNITXPSP3RAISECAMERA = "Raise Camera";
BINDING_NAME_UNITXPSP3LOWERCAMERA = "Lower Camera";
BINDING_NAME_UNITXPSP3LEFTCAMERA = "Left Camera";
BINDING_NAME_UNITXPSP3RIGHTCAMERA = "Right Camera";
BINDING_NAME_UNITXPSP3RESETCAMERA = "Reset Camera";
BINDING_NAME_UNITXPSP3TOGGLEMODERNNAMEPLATEDISTANCE = "Toggle Proper Nameplates Behavior";
BINDING_NAME_UNITXPSP3TOGGLEPRIORITIZETARGETNAMEPLATE = "Toggle Prioritize Target Nameplate";
BINDING_NAME_UNITXPSP3TOGGLEPRIORITIZEMARKEDNAMEPLATE = "Toggle Prioritize Marked Nameplate";

local UNITXPSP3TOOLTIP = "UnitXP SP3 is running";

local libIcon = LibStub("LibDBIcon-1.0");
local libData = LibStub("LibDataBroker-1.1");
local skipUpdateMessage = false;
local original_CombatText_AddMessage = nil;

function UnitXP_SP3_OnLoad()
    xpsp3Frame:RegisterEvent("ADDON_LOADED");
end

local function UnitXP_SP3_flashTaskbarIcon()
    local test, result = pcall(UnitXP, "notify", "taskbarIcon");

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"notify taskbarIcon\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return nil;
    end

    return result;
end

local function UnitXP_SP3_playSystemDefaultSound()
    local test, result = pcall(UnitXP, "notify", "systemSound", "SystemDefault");

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"notify systemSound\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return nil;
    end

    return result;
end

local function UnitXP_SP3_FPScap(cap)
    local test, result = pcall(UnitXP, "FPScap", cap);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"FPScap\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["FPScap"];
    end

    UnitXP_SP3_Addon["FPScap"] = result;
    return UnitXP_SP3_Addon["FPScap"];
end

local function UnitXP_SP3_backgroundFPScap(cap)
    local test, result = pcall(UnitXP, "backgroundFPScap", cap);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"backgroundFPScap\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["backgroundFPScap"];
    end

    UnitXP_SP3_Addon["backgroundFPScap"] = result;
    return UnitXP_SP3_Addon["backgroundFPScap"];
end

local function UnitXP_SP3_setTargetingRangeConeFactor(factor)
    local test, result = pcall(UnitXP, "target", "rangeCone", factor);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"target rangeCone\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["targetingRangeConeFactor"];
    end

    UnitXP_SP3_Addon["targetingRangeConeFactor"] = result;
    return UnitXP_SP3_Addon["targetingRangeConeFactor"];
end

local function UnitXP_SP3_setModernNameplateDistance(enable)
    local test, result = pcall(UnitXP, "modernNameplateDistance", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"modernNameplateDistance\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setHideEXPtext(enable)
    local test, result = pcall(UnitXP, "hideEXPtext", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"hideEXPtext\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

function UnitXP_SP3_detoured_CombatText_AddMessage(message, scrollFunction, r, g, b, displayType, isStaggered)
    if UnitXP_SP3_Addon["combatTextSP3"] then
        -- Reported by Heallios
        -- Super WoW/API is also hooking CombatText_AddMessage to process the message doing a GUID to name conversion.
        -- However as UnitXP_SP3 would not call underlying function when using its own combat text facility, this conversion would be skipped.
        -- For now, we copy pasTA Super WoW/API conversion code.
        if SUPERWOW_VERSION then
            message = gsub(message, "(%s%[)(0x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x%x)(%])", function(bracket1, hex, bracket2)
                if UnitIsUnit(hex, "player") then
                    return nil;
                else
                    return " [" .. UnitName(hex) .. "]";
                end
            end);
        end

        if displayType == "crit" then
            pcall(UnitXP, "addCombatText", "crit", message, r, g, b);
        else
            if COMBAT_TEXT_FLOAT_MODE == "1" then
                pcall(UnitXP, "addCombatText", "normal", message, r, g, b);
            elseif COMBAT_TEXT_FLOAT_MODE == "2" then
                pcall(UnitXP, "addCombatText", "downward", message, r, g, b);
            else
                pcall(UnitXP, "addCombatText", "arc", message, r, g, b);
            end
        end
        return nil;
    else
        if original_CombatText_AddMessage ~= nil then
            return original_CombatText_AddMessage(message, scrollFunction, r, g, b, displayType, isStaggered);
        end
    end
end

local function UnitXP_SP3_combatTextSP3_debugText()
    local test, result, scene_isEnabled = pcall(UnitXP, "combatTextSP3", "debugText");
    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"combatTextSP3 debugText\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end

    UnitXP_SP3_Print("UnitXP_SP3 floating combat text debug: " .. result);
end

local function UnitXP_SP3_combatTextSP3(enable)
    local test, result, scene_isEnabled = pcall(UnitXP, "combatTextSP3", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"combatTextSP3\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end

    if type(result) ~= "boolean" then
        result = false;
        UnitXP_SP3_Print(
            "UnitXP_SP3.dll failed to execute \"combatTextSP3\". You might need to update UnitXP_SP3.dll to support this method.");
    end

    if type(scene_isEnabled) == "boolean" and scene_isEnabled == false then
        UnitXP_SP3_combatTextSP3_debugText();
    end

    return result;
end

local function UnitXP_SP3_combatTextSP3_fontSize(size)
    local test, result, scene_isEnabled = pcall(UnitXP, "combatTextSP3", "setFontSize", size);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"combatTextSP3 setFontSize\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["combatTextSP3_fontSize"];
    end

    if type(result) ~= "number" then
        result = 40;
        UnitXP_SP3_Print(
            "UnitXP_SP3.dll failed to execute \"combatTextSP3 setFontSize\". You might need to update UnitXP_SP3.dll to support this method.");
    end

    if type(scene_isEnabled) == "boolean" and scene_isEnabled == false then
        UnitXP_SP3_combatTextSP3_debugText();
    end

    UnitXP_SP3_Addon["combatTextSP3_fontSize"] = result;
    return UnitXP_SP3_Addon["combatTextSP3_fontSize"];
end

local function UnitXP_SP3_combatTextSP3_fontName(name)
    local test, result, scene_isEnabled = pcall(UnitXP, "combatTextSP3", "setFontName", name);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"combatTextSP3 setFontName\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["combatTextSP3_fontName"];
    end

    if type(result) ~= "string" then
        result = "Cambria";
        UnitXP_SP3_Print(
            "UnitXP_SP3.dll failed to execute \"combatTextSP3 setFontName\". You might need to update UnitXP_SP3.dll to support this method.");
    end

    if type(scene_isEnabled) == "boolean" and scene_isEnabled == false then
        UnitXP_SP3_combatTextSP3_debugText();
    end

    UnitXP_SP3_Addon["combatTextSP3_fontName"] = result;
    return UnitXP_SP3_Addon["combatTextSP3_fontName"];
end

local function UnitXP_SP3_combatTextSP3_nameplateHeight(size)
    local test, result, scene_isEnabled = pcall(UnitXP, "combatTextSP3", "setNameplateHeight", size);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"combatTextSP3 setNameplateHeight\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"];
    end

    if type(result) ~= "number" then
        result = 55;
        UnitXP_SP3_Print(
            "UnitXP_SP3.dll failed to execute \"combatTextSP3 setNameplateHeight\". You might need to update UnitXP_SP3.dll to support this method.");
    end

    if type(scene_isEnabled) == "boolean" and scene_isEnabled == false then
        UnitXP_SP3_combatTextSP3_debugText();
    end

    UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"] = result;
    return UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"];
end

local function UnitXP_SP3_setPrioritizeTargetNameplate(enable)
    local test, result = pcall(UnitXP, "prioritizeTargetNameplate", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"prioritizeTargetNameplate\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setPrioritizeMarkedNameplate(enable)
    local test, result = pcall(UnitXP, "prioritizeMarkedNameplate", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"prioritizeMarkedNameplate\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setNameplateCombatFilter(enable)
    local test, result = pcall(UnitXP, "nameplateCombatFilter", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"nameplateCombatFilter\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setHideCritterNameplate(enable)
    local test, result = pcall(UnitXP, "hideCritterNameplate", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"hideCritterNameplate\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setShowInCombatNameplatesNearPlayer(enable)
    local test, result = pcall(UnitXP, "showInCombatNameplatesNearPlayer", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"showInCombatNameplatesNearPlayer\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setWeatherAlwaysClear(disable)
    local test, result;
    if enable then
        test, result = pcall(UnitXP, "weatherAlwaysClear", "disableRain");
    else
        test, result = pcall(UnitXP, "weatherAlwaysClear", "enableRain");
    end

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"weatherAlwaysClear\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_screenshotQuality(perfect)
    local test, result = pcall(UnitXP, "screenshot", perfect);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"screenshot\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setCameraPinHeight(enable)
    local test, result = pcall(UnitXP, "cameraPinHeight", enable);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"cameraPinHeight\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return false;
    end
    return result;
end

local function UnitXP_SP3_setCameraHeight(value)
    local test, result = pcall(UnitXP, "cameraVerticalDisplacement", "set", value);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"cameraVerticalDisplacement set\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["cameraHeight"];
    end

    UnitXP_SP3_Addon["cameraHeight"] = result;
    return UnitXP_SP3_Addon["cameraHeight"];
end

local function UnitXP_SP3_setCameraPitch(value)
    local test, result = pcall(UnitXP, "cameraPitch", "set", value);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"cameraPitch set\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["cameraPitch"];
    end

    UnitXP_SP3_Addon["cameraPitch"] = result;
    return UnitXP_SP3_Addon["cameraPitch"];
end

local function UnitXP_SP3_setCameraHorizontalDisplacement(value)
    local test, result = pcall(UnitXP, "cameraHorizontalDisplacement", "set", value);

    if not test then
        if not skipUpdateMessage then
            skipUpdateMessage = true;
            UnitXP_SP3_Print(
                "UnitXP_SP3.dll failed to execute \"cameraHorizontalDisplacement set\". You might need to update UnitXP_SP3.dll to support this method.");
        end
        return UnitXP_SP3_Addon["cameraHorizontalDisplacement"];
    end

    UnitXP_SP3_Addon["cameraHorizontalDisplacement"] = result;
    return UnitXP_SP3_Addon["cameraHorizontalDisplacement"];
end

function UnitXP_SP3_resetCamera()
    UnitXP_SP3_setCameraHorizontalDisplacement(0);
    UnitXP_SP3_setCameraHeight(0);
    UnitXP_SP3_setCameraPitch(0);
    return 0;
end

function UnitXP_SP3_leftPlayer()
    return UnitXP_SP3_setCameraHorizontalDisplacement(UnitXP_SP3_Addon["cameraHorizontalDisplacement"] + 0.11);
end

function UnitXP_SP3_rightPlayer()
    return UnitXP_SP3_setCameraHorizontalDisplacement(UnitXP_SP3_Addon["cameraHorizontalDisplacement"] - 0.11);
end

function UnitXP_SP3_raiseCameraHeight()
    return UnitXP_SP3_setCameraHeight(UnitXP_SP3_Addon["cameraHeight"] + 0.11);
end

function UnitXP_SP3_lowerCameraHeight()
    return UnitXP_SP3_setCameraHeight(UnitXP_SP3_Addon["cameraHeight"] - 0.11);
end

function UnitXP_SP3_cameraPitchUp()
    return UnitXP_SP3_setCameraPitch(UnitXP_SP3_Addon["cameraPitch"] + 0.011);
end

function UnitXP_SP3_cameraPitchDown()
    return UnitXP_SP3_setCameraPitch(UnitXP_SP3_Addon["cameraPitch"] - 0.011);
end

local function UnitXP_SP3_reloadConfig()
    UnitXP_SP3_FPScap(UnitXP_SP3_Addon["FPScap"]);
    xpsp3_editBox_FPScap:SetNumber(UnitXP_SP3_Addon["FPScap"]);

    UnitXP_SP3_backgroundFPScap(UnitXP_SP3_Addon["backgroundFPScap"]);
    xpsp3_editBox_backgroundFPScap:SetNumber(UnitXP_SP3_Addon["backgroundFPScap"]);

    UnitXP_SP3_setTargetingRangeConeFactor(UnitXP_SP3_Addon["targetingRangeConeFactor"]);

    UnitXP_SP3_setCameraHeight(UnitXP_SP3_Addon["cameraHeight"]);
    UnitXP_SP3_setCameraPitch(UnitXP_SP3_Addon["cameraPitch"]);
    UnitXP_SP3_setCameraHorizontalDisplacement(UnitXP_SP3_Addon["cameraHorizontalDisplacement"]);

    if UnitXP_SP3_Icon.hide then
        xpsp3_checkButton_minimapButton:SetChecked(false);
    else
        xpsp3_checkButton_minimapButton:SetChecked(true);
    end

    if UnitXP_SP3_Addon["modernNameplateDistance"] then
        UnitXP_SP3_setModernNameplateDistance("enable");
        xpsp3_checkButton_modernNameplate:SetChecked(true);
    else
        UnitXP_SP3_setModernNameplateDistance("disable");
        xpsp3_checkButton_modernNameplate:SetChecked(false);
    end

    if UnitXP_SP3_Addon["combatTextSP3"] then
        UnitXP_SP3_combatTextSP3("enable");
        xpsp3_checkButton_combatTextSP3:SetChecked(true);
        xpsp3_editBox_combatTextSP3_fontSize:Show();
        xpsp3_editBox_combatTextSP3_nameplateHeight:Show();
        xpsp3_editBox_combatTextSP3_fontName:Show();
        xpsp3_fontString_combatTextSP3_fontSize:Show();
        xpsp3_fontString_combatTextSP3_nameplateHeight:Show();
        xpsp3_fontString_combatTextSP3_fontName:Show();

        UnitXP_SP3_combatTextSP3_fontSize(UnitXP_SP3_Addon["combatTextSP3_fontSize"]);
        xpsp3_editBox_combatTextSP3_fontSize:SetNumber(UnitXP_SP3_Addon["combatTextSP3_fontSize"]);

        UnitXP_SP3_combatTextSP3_nameplateHeight(UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"]);
        xpsp3_editBox_combatTextSP3_nameplateHeight:SetNumber(UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"]);

        UnitXP_SP3_combatTextSP3_fontName(UnitXP_SP3_Addon["combatTextSP3_fontName"]);
        xpsp3_editBox_combatTextSP3_fontName:SetText(UnitXP_SP3_Addon["combatTextSP3_fontName"]);
    else
        UnitXP_SP3_combatTextSP3("disable");
        xpsp3_checkButton_combatTextSP3:SetChecked(false);
        xpsp3_editBox_combatTextSP3_fontSize:Hide();
        xpsp3_editBox_combatTextSP3_nameplateHeight:Hide();
        xpsp3_editBox_combatTextSP3_fontName:Hide();
        xpsp3_fontString_combatTextSP3_fontSize:Hide();
        xpsp3_fontString_combatTextSP3_nameplateHeight:Hide();
        xpsp3_fontString_combatTextSP3_fontName:Hide();
    end

    if UnitXP_SP3_Addon["hideEXPtext"] then
        UnitXP_SP3_setHideEXPtext("enable");
        xpsp3_checkButton_hideEXPtext:SetChecked(true);
    else
        UnitXP_SP3_setHideEXPtext("disable");
        xpsp3_checkButton_hideEXPtext:SetChecked(false);
    end

    if UnitXP_SP3_Addon["cameraPinHeight"] then
        UnitXP_SP3_setCameraPinHeight("enable");
        xpsp3_checkButton_cameraPinHeight:SetChecked(true);
    else
        UnitXP_SP3_setCameraPinHeight("disable");
        xpsp3_checkButton_cameraPinHeight:SetChecked(false);
    end

    if UnitXP_SP3_Addon["prioritizeTargetNameplate"] then
        UnitXP_SP3_setPrioritizeTargetNameplate("enable");
        xpsp3_checkButton_prioritizeTargetNameplate:SetChecked(true);
    else
        UnitXP_SP3_setPrioritizeTargetNameplate("disable");
        xpsp3_checkButton_prioritizeTargetNameplate:SetChecked(false);
    end

    if UnitXP_SP3_Addon["prioritizeMarkedNameplate"] then
        UnitXP_SP3_setPrioritizeMarkedNameplate("enable");
        xpsp3_checkButton_prioritizeMarkedNameplate:SetChecked(true);
    else
        UnitXP_SP3_setPrioritizeMarkedNameplate("disable");
        xpsp3_checkButton_prioritizeMarkedNameplate:SetChecked(false);
    end

    if UnitXP_SP3_Addon["nameplateCombatFilter"] then
        UnitXP_SP3_setNameplateCombatFilter("enable");
        xpsp3_checkButton_nameplateCombatFilter:SetChecked(true);
    else
        UnitXP_SP3_setNameplateCombatFilter("disable");
        xpsp3_checkButton_nameplateCombatFilter:SetChecked(false);
    end

    if UnitXP_SP3_Addon["hideCritterNameplate"] then
        UnitXP_SP3_setHideCritterNameplate("enable");
        xpsp3_checkButton_hideCritterNameplate:SetChecked(true);
    else
        UnitXP_SP3_setHideCritterNameplate("disable");
        xpsp3_checkButton_hideCritterNameplate:SetChecked(false);
    end

    if UnitXP_SP3_Addon["showInCombatNameplatesNearPlayer"] then
        UnitXP_SP3_setShowInCombatNameplatesNearPlayer("enable");
        xpsp3_checkButton_showInCombatNameplatesNearPlayer:SetChecked(true);
    else
        UnitXP_SP3_setShowInCombatNameplatesNearPlayer("disable");
        xpsp3_checkButton_showInCombatNameplatesNearPlayer:SetChecked(false);
    end

    if UnitXP_SP3_Addon["weatherAlwaysClear"] then
        UnitXP_SP3_setWeatherAlwaysClear("enable");
        xpsp3_checkButton_weatherAlwaysClear:SetChecked(true);
    else
        UnitXP_SP3_setWeatherAlwaysClear("disable");
        xpsp3_checkButton_weatherAlwaysClear:SetChecked(false);
    end

    if UnitXP_SP3_Addon["perfectScreenshot"] then
        UnitXP_SP3_screenshotQuality("perfect");
        xpsp3_checkButton_perfectScreenshot:SetChecked(true);
    else
        UnitXP_SP3_screenshotQuality("good");
        xpsp3_checkButton_perfectScreenshot:SetChecked(false);
    end

    for ev, v in pairs(UnitXP_SP3_Addon["notify_flashTaskbarIcon"]) do
        xpsp3Frame:UnregisterEvent(ev);
    end
    for ev, v in pairs(UnitXP_SP3_Addon["notify_playSystemDefaultSound"]) do
        xpsp3Frame:UnregisterEvent(ev);
    end

    for ev, v in pairs(UnitXP_SP3_Addon["notify_flashTaskbarIcon"]) do
        if v == true then
            xpsp3Frame:RegisterEvent(ev);
            xpsp3_checkButton_notify_flashTaskbarIcon:SetChecked(true);
        else
            xpsp3_checkButton_notify_flashTaskbarIcon:SetChecked(false);
        end
    end
    for ev, v in pairs(UnitXP_SP3_Addon["notify_playSystemDefaultSound"]) do
        if v == true then
            xpsp3Frame:RegisterEvent(ev);
            xpsp3_checkButton_notify_playSystemDefaultSound:SetChecked(true);
        else
            xpsp3_checkButton_notify_playSystemDefaultSound:SetChecked(false);
        end
    end

end

function UnitXP_SP3_UI_OnClick(widget)
    if widget == nil or string.find(widget:GetName(), "xpsp3") == nil then
        return
    end

    xpsp3_editBox_FPScap:ClearFocus();
    xpsp3_editBox_backgroundFPScap:ClearFocus();
    xpsp3_editBox_combatTextSP3_fontSize:ClearFocus();
    xpsp3_editBox_combatTextSP3_nameplateHeight:ClearFocus();
    xpsp3_editBox_combatTextSP3_fontName:ClearFocus();

    skipUpdateMessage = false;

    if string.find(widget:GetName(), "_editBox_") then
        PlaySound("igMainMenuContinue");
        if string.find(widget:GetName(), "_FPScap") then
            UnitXP_SP3_FPScap(widget:GetNumber());
        end
        if string.find(widget:GetName(), "_backgroundFPScap") then
            UnitXP_SP3_backgroundFPScap(widget:GetNumber());
        end
        if string.find(widget:GetName(), "_combatTextSP3_fontSize") then
            UnitXP_SP3_combatTextSP3_fontSize(widget:GetNumber());
        end
        if string.find(widget:GetName(), "_combatTextSP3_nameplateHeight") then
            UnitXP_SP3_combatTextSP3_nameplateHeight(widget:GetNumber());
        end
        if string.find(widget:GetName(), "_combatTextSP3_fontName") then
            UnitXP_SP3_combatTextSP3_fontName(widget:GetText());
        end
    end

    if string.find(widget:GetName(), "_button_") then
        PlaySound("igMainMenuContinue");
        if string.find(widget:GetName(), "_cameraHeight_raise") then
            UnitXP_SP3_raiseCameraHeight();
        end
        if string.find(widget:GetName(), "_cameraHeight_lower") then
            UnitXP_SP3_lowerCameraHeight();
        end
        if string.find(widget:GetName(), "_cameraPitch_up") then
            UnitXP_SP3_cameraPitchUp();
        end
        if string.find(widget:GetName(), "_cameraPitch_down") then
            UnitXP_SP3_cameraPitchDown();
        end
        if string.find(widget:GetName(), "_cameraHorizontalDisplacement_leftPlayer") then
            UnitXP_SP3_leftPlayer();
        end
        if string.find(widget:GetName(), "_cameraHorizontalDisplacement_rightPlayer") then
            UnitXP_SP3_rightPlayer();
        end
    end

    if string.find(widget:GetName(), "_buttonCancel_") then
        PlaySound("gsTitleOptionExit");
        if string.find(widget:GetName(), "_close") then
            xpsp3Frame:Hide();
        end
        if string.find(widget:GetName(), "_resetCamera") then
            UnitXP_SP3_resetCamera();
        end
    end

    if string.find(widget:GetName(), "_checkButton_") then
        if widget:GetChecked() then
            PlaySound("igMainMenuOptionCheckBoxOn");
        else
            PlaySound("igMainMenuOptionCheckBoxOff");
        end

        if string.find(widget:GetName(), "_minimapButton") then
            UnitXP_SP3_Icon.hide = not widget:GetChecked();
            libIcon:Refresh("UnitXP SP3 icon", UnitXP_SP3_Icon);
        end

        if string.find(widget:GetName(), "_modernNameplate") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["modernNameplateDistance"] = true;
            else
                UnitXP_SP3_Addon["modernNameplateDistance"] = false;
            end
        end

        if string.find(widget:GetName(), "_combatTextSP3") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["combatTextSP3"] = true;
            else
                UnitXP_SP3_Addon["combatTextSP3"] = false;
            end
        end

        if string.find(widget:GetName(), "_hideEXPtext") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["hideEXPtext"] = true;
            else
                UnitXP_SP3_Addon["hideEXPtext"] = false;
            end
        end

        if string.find(widget:GetName(), "_cameraPinHeight") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["cameraPinHeight"] = true;
            else
                UnitXP_SP3_Addon["cameraPinHeight"] = false;
            end
        end

        if string.find(widget:GetName(), "_prioritizeTargetNameplate") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["prioritizeTargetNameplate"] = true;
            else
                UnitXP_SP3_Addon["prioritizeTargetNameplate"] = false;
            end
        end

        if string.find(widget:GetName(), "_prioritizeMarkedNameplate") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["prioritizeMarkedNameplate"] = true;
            else
                UnitXP_SP3_Addon["prioritizeMarkedNameplate"] = false;
            end
        end

        if string.find(widget:GetName(), "_nameplateCombatFilter") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["nameplateCombatFilter"] = true;
            else
                UnitXP_SP3_Addon["nameplateCombatFilter"] = false;
            end
        end

        if string.find(widget:GetName(), "_weatherAlwaysClear") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["weatherAlwaysClear"] = true;
            else
                UnitXP_SP3_Addon["weatherAlwaysClear"] = false;
            end
        end

        if string.find(widget:GetName(), "_perfectScreenshot") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["perfectScreenshot"] = true;
            else
                UnitXP_SP3_Addon["perfectScreenshot"] = false;
            end
        end

        if string.find(widget:GetName(), "_showInCombatNameplatesNearPlayer") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["showInCombatNameplatesNearPlayer"] = true;
            else
                UnitXP_SP3_Addon["showInCombatNameplatesNearPlayer"] = false;
            end
        end

        if string.find(widget:GetName(), "_hideCritterNameplate") then
            if widget:GetChecked() then
                UnitXP_SP3_Addon["hideCritterNameplate"] = true;
            else
                UnitXP_SP3_Addon["hideCritterNameplate"] = false;
            end
        end

        if string.find(widget:GetName(), "_notify_flashTaskbarIcon") then
            for ev, v in pairs(UnitXP_SP3_Addon["notify_flashTaskbarIcon"]) do
                if widget:GetChecked() then
                    UnitXP_SP3_Addon["notify_flashTaskbarIcon"][ev] = true;
                else
                    UnitXP_SP3_Addon["notify_flashTaskbarIcon"][ev] = false;
                end
            end
        end

        if string.find(widget:GetName(), "_notify_playSystemDefaultSound") then
            for ev, v in pairs(UnitXP_SP3_Addon["notify_playSystemDefaultSound"]) do
                if widget:GetChecked() then
                    UnitXP_SP3_Addon["notify_playSystemDefaultSound"][ev] = true;
                else
                    UnitXP_SP3_Addon["notify_playSystemDefaultSound"][ev] = false;
                end
            end
        end
    end

    UnitXP_SP3_reloadConfig();
end

function UnitXP_SP3_toggleModernNameplateDistance()
    UnitXP_SP3_Addon["modernNameplateDistance"] = not UnitXP_SP3_Addon["modernNameplateDistance"];
    UnitXP_SP3_reloadConfig();
end

function UnitXP_SP3_togglePrioritizeTargetNameplate()
    UnitXP_SP3_Addon["prioritizeTargetNameplate"] = not UnitXP_SP3_Addon["prioritizeTargetNameplate"];
    UnitXP_SP3_reloadConfig();
end

function UnitXP_SP3_togglePrioritizeMarkedNameplate()
    UnitXP_SP3_Addon["prioritizeMarkedNameplate"] = not UnitXP_SP3_Addon["prioritizeMarkedNameplate"];
    UnitXP_SP3_reloadConfig();
end

-- Recording party members from previous PARTY_MEMBERS_CHANGED events so that we can verify if the party just became full
local lastRecordedPartyMembers = 0

local function checkEvent(listenedEvents, actionFunction)
    if listenedEvents[event] then
        if event == "PARTY_MEMBERS_CHANGED" then
            -- Party full
            if GetNumRaidMembers() == 0 and GetNumPartyMembers() == 4 and lastRecordedPartyMembers ~= 4 then
                actionFunction();
            end
        elseif event == "UPDATE_BATTLEFIELD_STATUS" then
            for i = 1, MAX_BATTLEFIELD_QUEUES do
                local s = GetBattlefieldStatus(i);
                -- Battlefield is ready
                if s == "confirm" then
                    actionFunction();
                    break
                end
            end
        elseif event == "CHAT_MSG_ADDON" then
            if arg1 == (LFT_ADDON_PREFIX or "TW_LFG") then
                if string.find(arg2, "S2C_OFFER_NEW") or string.find(arg2, "S2C_ROLECHECK_START") or
                    string.find(arg2, "S2C_QUEUE_LEFT") then
                    -- LFT found group or role check start or somehow player left queue
                    actionFunction();
                end
            end
        else
            actionFunction();
        end
    end
end

function UnitXP_SP3_OnEvent(event)
    if event == "ADDON_LOADED" and arg1 == "UnitXP_SP3_Addon" then
        local dataVersion = 34;
        if UnitXP_SP3_Addon == nil or UnitXP_SP3_Addon["dataVersion"] ~= dataVersion then
            UnitXP_SP3_Addon = {};
            UnitXP_SP3_Addon["dataVersion"] = dataVersion;
            UnitXP_SP3_Addon["targetRangeConeFactor"] = 2.2;
            UnitXP_SP3_Addon["cameraHeight"] = 0.0;
            UnitXP_SP3_Addon["cameraPitch"] = 0.0;
            UnitXP_SP3_Addon["cameraHorizontalDisplacement"] = 0.0;
            UnitXP_SP3_Addon["cameraPinHeight"] = false;
            UnitXP_SP3_Addon["modernNameplateDistance"] = true;
            UnitXP_SP3_Addon["prioritizeTargetNameplate"] = false;
            UnitXP_SP3_Addon["prioritizeMarkedNameplate"] = false;
            UnitXP_SP3_Addon["nameplateCombatFilter"] = false;
            UnitXP_SP3_Addon["showInCombatNameplatesNearPlayer"] = false;
            UnitXP_SP3_Addon["FPScap"] = 0;
            UnitXP_SP3_Addon["backgroundFPScap"] = 60;
            UnitXP_SP3_Addon["weatherAlwaysClear"] = false;
            UnitXP_SP3_Addon["hideCritterNameplate"] = true;
            UnitXP_SP3_Addon["combatTextSP3"] = false;
            UnitXP_SP3_Addon["combatTextSP3_fontSize"] = 40;
            UnitXP_SP3_Addon["combatTextSP3_nameplateHeight"] = 55;
            UnitXP_SP3_Addon["combatTextSP3_fontName"] = "Cambria";
            UnitXP_SP3_Addon["hideEXPtext"] = false;
            UnitXP_SP3_Addon["perfectScreenshot"] = false;

            UnitXP_SP3_Addon["notify_flashTaskbarIcon"] = {};
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["PLAYER_REGEN_DISABLED"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["CHAT_MSG_WHISPER"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["CHAT_MSG_RAID_WARNING"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["TRADE_SHOW"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["PARTY_INVITE_REQUEST"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["READY_CHECK"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["GUILD_INVITE_REQUEST"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["UPDATE_BATTLEFIELD_STATUS"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["PARTY_MEMBERS_CHANGED"] = true;
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["CHAT_MSG_ADDON"] = true; -- For LFT

            UnitXP_SP3_Addon["notify_playSystemDefaultSound"] = {};
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["PLAYER_REGEN_DISABLED"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["CHAT_MSG_WHISPER"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["CHAT_MSG_RAID_WARNING"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["TRADE_SHOW"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["PARTY_INVITE_REQUEST"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["READY_CHECK"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["GUILD_INVITE_REQUEST"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["UPDATE_BATTLEFIELD_STATUS"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["PARTY_MEMBERS_CHANGED"] = false;
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["CHAT_MSG_ADDON"] = false; -- For LFT
        end
        if UnitXP_SP3_Icon == nil then
            UnitXP_SP3_Icon = {
                hide = false
            };
        end
        xpsp3Frame:UnregisterEvent("ADDON_LOADED");
        xpsp3Frame:RegisterEvent("PLAYER_LOGIN");
        return;
    elseif event == "PLAYER_LOGIN" then
        if pcall(UnitXP, "nop", "nop") == true then
            UnitXP_SP3_reloadConfig();
            xpsp3Frame:RegisterEvent("PLAYER_ENTERING_WORLD");
            xpsp3Frame:RegisterEvent("PLAYER_LEAVING_WORLD");
            original_CombatText_AddMessage = CombatText_AddMessage;
            CombatText_AddMessage = UnitXP_SP3_detoured_CombatText_AddMessage;

            local message = "UnitXP Service Pack 3 is loaded.";
            local hasCOFFtimestamp, coffTimestamp = pcall(UnitXP, "version", "coffTimeDateStamp");
            if hasCOFFtimestamp then
                message = message .. " It was built on " .. date("%d %b %Y", coffTimestamp) .. ".";
            end
            UnitXP_SP3_Print(message);
        else
            UnitXP_SP3_Print("UnitXP Service Pack 3 didn't load properly.");
            return;
        end

        -- Chat Command
        SLASH_UNITXP1 = "/unitxp";
        SlashCmdList["UNITXP"] = function()
            if pcall(UnitXP, "nop", "nop") == true then
                if xpsp3Frame:IsShown() then
                    PlaySound("igMainMenuContinue");
                    xpsp3Frame:Hide();
                else
                    PlaySound("igMainMenuOpen");
                    xpsp3Frame:Show();
                end
            else
                UnitXP_SP3_Print("UnitXP Service Pack 3 didn't load properly.");
            end
        end

        if UnitXP_SP3_Addon["notify_flashTaskbarIcon"] ~= nil and
            UnitXP_SP3_Addon["notify_flashTaskbarIcon"]["PLAYER_REGEN_DISABLED"] == true and
            UnitAffectingCombat("player") then
            UnitXP_SP3_flashTaskbarIcon();
        end

        if UnitXP_SP3_Addon["notify_playSystemDefaultSound"] ~= nil and
            UnitXP_SP3_Addon["notify_playSystemDefaultSound"]["PLAYER_REGEN_DISABLED"] == true and
            UnitAffectingCombat("player") then
            UnitXP_SP3_playSystemDefaultSound();
        end

        local iconData = libData:NewDataObject("UnitXP SP3 icon data", {
            OnClick = function()
                if pcall(UnitXP, "nop", "nop") == true then
                    if xpsp3Frame:IsShown() then
                        PlaySound("igMainMenuContinue");
                        xpsp3Frame:Hide();
                    else
                        PlaySound("igMainMenuOpen");
                        xpsp3Frame:Show();
                    end
                else
                    UnitXP_SP3_Print("UnitXP Service Pack 3 didn't load properly.");
                end
            end,
            OnTooltipShow = function(tooltip)
                tooltip:SetText(UNITXPSP3TOOLTIP);
            end,
            icon = "Interface\\Icons\\INV_Misc_Gem_Pearl_05"
        });

        libIcon:Register("UnitXP SP3 icon", iconData, UnitXP_SP3_Icon);

        return;
    elseif event == "PLAYER_ENTERING_WORLD" then
        pcall(UnitXP, "onEvent", event);
        return;
    elseif event == "PLAYER_LEAVING_WORLD" then
        pcall(UnitXP, "onEvent", event);
        return;
    end

    if UnitXP_SP3_Addon then
        if UnitXP_SP3_Addon["notify_flashTaskbarIcon"] then
            checkEvent(UnitXP_SP3_Addon["notify_flashTaskbarIcon"], UnitXP_SP3_flashTaskbarIcon)
        end

        if UnitXP_SP3_Addon["notify_playSystemDefaultSound"] then
            checkEvent(UnitXP_SP3_Addon["notify_playSystemDefaultSound"], UnitXP_SP3_playSystemDefaultSound)
        end

        if event == "PARTY_MEMBERS_CHANGED" then
            lastRecordedPartyMembers = GetNumPartyMembers()
        end
    end
end
