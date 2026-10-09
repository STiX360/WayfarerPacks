local core = require('openmw.core')
local self = require('openmw.self')
local types = require('openmw.types')
local I = require('openmw.interfaces')
local camera = require('openmw.camera')
local animation = require('openmw.animation')
local stage = 0
local frames = 0
local ids = {'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}
local magnitudes = {25, 50, 75}

local function check(condition, message)
    if condition then return true end
    print('WFP_SMOKE_FAIL: '..message)
    core.quit()
    stage = 99
    return false
end

local function use(id)
    local item = types.Actor.inventory(self):find(id)
    core.sendGlobalEvent('UseItem', {object=item, actor=self})
end

return {
    engineHandlers = {
        onFrame = function()
            if stage == 99 then return end
            frames = frames + 1
            if frames < 30 then return end
            frames = 0
            if stage == 0 then
                if not types.Actor.inventory(self):find(ids[3]) then return end
                camera.setMode(camera.MODE.ThirdPerson)
                if not check(I.WayfarerPacks ~= nil, 'missing mod interface') then return end
                use(ids[1]); stage = 1
            elseif stage <= 3 then
                if not check(camera.getMode() == camera.MODE.ThirdPerson
                             and animation.hasBone(self, 'Bip01 Spine1'), 'back attachment bone unavailable') then return end
                local item = I.WayfarerPacks.getEquipped()
                if not check(item and item.recordId == ids[stage], 'wrong selected bag at stage '..stage) then return end
                local effect = types.Actor.activeEffects(self):getEffect(core.magic.EFFECT_TYPE.Feather)
                if not check(effect and effect.magnitude == magnitudes[stage], 'wrong Feather at stage '..stage) then return end
                print('WFP_SMOKE_EQUIPPED: '..ids[stage]..' Feather '..effect.magnitude)
                if stage < 3 then use(ids[stage+1]) else use(ids[3]) end
                stage = stage + 1
            elseif stage == 4 then
                if not check(I.WayfarerPacks.getEquipped() == nil, 'toggle did not clear slot') then return end
                use(ids[2]); stage = 5
            elseif stage == 5 then
                local item = I.WayfarerPacks.getEquipped()
                if not check(item ~= nil, 'second equip failed') then return end
                core.sendGlobalEvent('WFPTestDiscard', {item=item}); stage = 6
            else
                local effect = types.Actor.activeEffects(self):getEffect(core.magic.EFFECT_TYPE.Feather)
                if not check(I.WayfarerPacks.getEquipped() == nil and (not effect or effect.magnitude == 0),
                             'lost bag left a bonus') then return end
                print('WFP_SMOKE_PASS')
                core.quit(); stage = 99
            end
        end,
    },
}
