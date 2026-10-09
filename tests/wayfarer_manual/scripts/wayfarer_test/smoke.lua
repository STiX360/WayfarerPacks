local core = require('openmw.core')
local self = require('openmw.self')
local types = require('openmw.types')
local camera = require('openmw.camera')
local I = require('openmw.interfaces')
local frames = 0
local elapsed = 0
local checked = false
local craftingStage = 0
local recipes
local globals
local materialsBefore
local batchCount
local batchTarget
local batchBefore
local selectedCopy
local equipFrames = 0
local artisanIndex = 1
local artisanBefore
local artisanMagnitudes = {38, 71, 101}
local artisanIds = {}
local ids = {'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}

local function finish()
    checked = true
    print('WFP_MANUAL_PASS: spawn, gold, clothes, camera, merchant stock, mod interface')
    core.quit()
end

local function check(ok, message)
    if not ok then
        print('WFP_MANUAL_FAIL: '..message)
        core.quit()
    end
    return ok
end

return {
    engineHandlers = {
        onFrame = function(dt)
            frames = frames + 1
            elapsed = elapsed + dt
            if craftingStage > 0 then
                local inv = types.Actor.inventory(self)
                if craftingStage == 4 then
                    if inv:countOf('wfp_backpack') == batchTarget then
                        if not check(batchBefore.leather-inv:countOf('ingred_netch_leather_01') == 6*batchCount,
                            'batch leather consumption mismatch') then return end
                        if not check(batchBefore.shirts == inv:countOf('common_shirt_01')
                            and batchBefore.pants == inv:countOf('common_pants_01'),
                            'batch crafting consumed clothing') then return end
                        print('WFP_MANUAL_BATCH_PASS: Craft All produced '..batchCount..' additional backpacks')
                        local copies = 0
                        for _, item in ipairs(inv:getAll(types.Miscellaneous)) do
                            if item.recordId == 'wfp_backpack' then
                                if not check(item.count == 1, 'crafted copies merged into a stack') then return end
                                copies = copies + 1
                                selectedCopy = item
                            end
                        end
                        if not check(copies == batchTarget, 'missing distinct backpack copies') then return end
                        I.CraftingFramework.closeCraftingWindow()
                        I.UI.setMode(nil)
                        core.sendGlobalEvent('UseItem', {object=selectedCopy, actor=self})
                        craftingStage = 5
                    end
                elseif craftingStage == 5 then
                    equipFrames = equipFrames + 1
                    if equipFrames >= 30 then
                        if not check(I.WayfarerPacks.getEquipped() == selectedCopy and selectedCopy.count == 1,
                            'equip did not select exactly one copy') then return end
                        local effect = types.Actor.activeEffects(self):getEffect(core.magic.EFFECT_TYPE.Feather)
                        if not check(effect and effect.magnitude == 50, 'duplicate copies altered Feather') then return end
                        core.sendGlobalEvent('UseItem', {object=selectedCopy, actor=self})
                        craftingStage = 6
                        equipFrames = 0
                    end
                elseif craftingStage == 6 then
                    equipFrames = equipFrames + 1
                    if equipFrames >= 30 then
                        if not check(I.WayfarerPacks.getEquipped() == nil and inv:countOf('wfp_backpack') == batchTarget,
                            'toggle changed the number of copies') then return end
                        core.sendGlobalEvent('WayfarerTestBulkPack', {})
                        craftingStage = 7
                    end
                elseif craftingStage == 7 then
                    if inv:countOf('wfp_backpack') == batchTarget+4 then
                        local copies = 0
                        for _, item in ipairs(inv:getAll(types.Miscellaneous)) do
                            if item.recordId == 'wfp_backpack' then
                                if item.count ~= 1 then return end
                                copies = copies + 1
                            end
                        end
                        if not check(copies == batchTarget+4, 'bulk split lost copies') then return end
                        print('WFP_MANUAL_STACK_PASS: distinct crafted copies, one worn, Feather 50, toggle and bulk split preserve all copies')
                        core.sendGlobalEvent('WayfarerTestArtisanMaterials', {})
                        craftingStage = 8
                    end
                elseif craftingStage == 8 then
                    if inv:countOf('ingred_netch_leather_01') >= 19 then
                        artisanBefore = inv:countOf('ingred_netch_leather_01')
                        types.NPC.stats.skills.armorer(self).base = 100
                        globals.skillValueCache.armorer = nil
                        I.CraftingFramework.toggleTouch('artisan', true)
                        I.CraftingFramework.openCraftingWindow('Crafting')
                        for _, id in ipairs(ids) do
                            local recipe = recipes[id]
                            local touches = globals.getActiveTouches(recipe)
                            if not check(touches and touches.artisan, 'diamond toggle excludes '..id) then return end
                            local target = globals.resolveResultItem(recipe, touches, true)
                            if not check(target == id..'_artisan', 'wrong Artisan preview result') then return end
                            local duration = globals.calculateCraftingTime(recipe, touches)
                            local normalDuration = globals.calculateCraftingTime(recipe)
                            if not check(duration == 2*normalDuration, 'Artisan duration not doubled') then return end
                            globals.addToCraftingQueue(recipe, 1, false)
                        end
                        craftingStage = 9
                    end
                elseif craftingStage == 9 then
                    if artisanIds.wfp_expedition and inv:find(artisanIds.wfp_expedition) then
                        for _, id in ipairs(ids) do
                            if not check(artisanIds[id] and inv:countOf(artisanIds[id]) == 1, 'missing Artisan copy '..id) then return end
                        end
                        if not check(artisanBefore-inv:countOf('ingred_netch_leather_01') == 19
                            and inv:countOf('ingred_diamond_01') == 0, 'Artisan ingredients not consumed correctly') then return end
                        I.CraftingFramework.closeCraftingWindow()
                        I.UI.setMode(nil)
                        core.sendGlobalEvent('UseItem', {object=inv:find(artisanIds[ids[1]]), actor=self})
                        equipFrames = 0
                        craftingStage = 10
                    end
                elseif craftingStage == 10 then
                    equipFrames = equipFrames + 1
                    if equipFrames >= 30 then
                        local selected = I.WayfarerPacks.getEquipped()
                        local effect = types.Actor.activeEffects(self):getEffect(core.magic.EFFECT_TYPE.Feather)
                        if not check(selected and selected.recordId == artisanIds[ids[artisanIndex]]
                            and effect and effect.magnitude == artisanMagnitudes[artisanIndex],
                            'Artisan selection/Feather mismatch') then return end
                        if artisanIndex < 3 then
                            artisanIndex = artisanIndex + 1
                            core.sendGlobalEvent('UseItem', {object=inv:find(artisanIds[ids[artisanIndex]]), actor=self})
                            equipFrames = 0
                        else
                            I.CraftingFramework.toggleTouch('artisan', false)
                            for _, id in ipairs(ids) do
                                if not check(globals.resolveResultItem(recipes[id], globals.getActiveTouches(recipes[id]), true) == id,
                                    'toggle off did not restore normal output') then return end
                            end
                            print('WFP_MANUAL_ARTISAN_PASS: skill 100, generated packs, materials, doubled duration, Feather 38/71/101')
                            craftingStage = 0
                            finish()
                        end
                    end
                elseif inv:find(ids[craftingStage]) then
                    if craftingStage < 3 then
                        craftingStage = craftingStage + 1
                        globals.addToCraftingQueue(recipes[ids[craftingStage]], 1, false)
                    else
                        for id, consumed in pairs({ingred_netch_leather_01=19, common_shirt_01=0, common_pants_01=0}) do
                            local used = materialsBefore[id]-inv:countOf(id)
                            if not check(used == consumed, id..' consumption: expected '..consumed..', got '..used) then return end
                        end
                        print('WFP_MANUAL_CRAFTING_PASS: three original-ID bags crafted, ingredients consumed')
                        local recipe = recipes.wfp_backpack
                        batchCount = globals.checkIngredientsWithQueue(recipe, #globals.craftingQueue)
                        if not check(batchCount >= 2, 'batch fixture needs at least two crafts') then return end
                        batchTarget = inv:countOf('wfp_backpack')+batchCount
                        batchBefore = {leather=inv:countOf('ingred_netch_leather_01'),
                            shirts=inv:countOf('common_shirt_01'), pants=inv:countOf('common_pants_01')}
                        craftingStage = 4
                        -- This is the same maximum-count calculation/queue path used by Craft All.
                        globals.addToCraftingQueue(recipe, batchCount)
                    end
                end
            end
            if elapsed > 110 and not checked then
                checked = true
                check(false, 'fixture timed out')
            elseif frames == 120 then
                local inv = types.Actor.inventory(self)
                if not check(self.cell.name == "Seyda Neen, Arrille's Tradehouse", 'wrong spawn cell') then return end
                if not check(inv:countOf('gold_001') == 5000, 'wrong starting gold') then return end
                if not check(camera.getMode() == camera.MODE.ThirdPerson, 'wrong camera mode') then return end
                if not check(I.WayfarerPacks ~= nil, 'missing mod interface') then return end
                for _, id in ipairs({'common_shirt_01', 'common_pants_01', 'common_shoes_01'}) do
                    if not check(inv:find(id) ~= nil, 'missing clothing '..id) then return end
                end
                local eq = types.Actor.getEquipment(self)
                for slot, id in pairs({[types.Actor.EQUIPMENT_SLOT.Shirt]='common_shirt_01',
                    [types.Actor.EQUIPMENT_SLOT.Pants]='common_pants_01',
                    [types.Actor.EQUIPMENT_SLOT.Boots]='common_shoes_01'}) do
                    if not check(eq[slot] and eq[slot].recordId == id, 'clothing not equipped '..id) then return end
                end
                if I.InventoryExtender then print('WFP_MANUAL_INVENTORY_EXTENDER') end
                for _, id in ipairs({'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}) do
                    if not check(inv:find(id) == nil, 'bag should be bought, not pre-granted') then return end
                end
                core.sendGlobalEvent('WayfarerTestCheckStock', {})
            end
        end,
    },
    eventHandlers = {
        WayfarerPacksCatalog = function(data)
            for id, pack in pairs(data.packs or {}) do
                if pack.templateId then
                    artisanIds[pack.templateId:gsub('_artisan$', '')] = id
                end
            end
        end,
        WayfarerTestStock = function(data)
            if not check(data.stocked, 'Arrille is missing a bag') then return end
            if not I.CraftingFramework then finish(); return end
            globals = I.CraftingFramework.getGlobals()
            local category = globals.allProfessions.Crafting and globals.allProfessions.Crafting['Travel Packs']
            if not check(category and #category == 3, 'missing Travel Packs recipes') then return end
            recipes = {}
            for _, recipe in ipairs(category) do
                if not check(recipe.preserveRecordId, 'recipe must preserve original ID') then return end
                recipes[recipe.id] = recipe
            end
            for _, id in ipairs(ids) do
                if not check(recipes[id] ~= nil, 'missing recipe '..id) then return end
            end
            I.CraftingFramework.openCraftingWindow('Crafting')
            if not check(I.CraftingFramework.getCraftingWindow() ~= nil, 'crafting GUI missing') then return end
            materialsBefore = {}
            for _, id in ipairs({'ingred_netch_leather_01', 'common_shirt_01', 'common_pants_01'}) do
                materialsBefore[id] = types.Actor.inventory(self):countOf(id)
            end
            craftingStage = 1
            globals.addToCraftingQueue(recipes[ids[1]], 1, false)
        end,
    },
}
