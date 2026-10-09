local types = require('openmw.types')
local world = require('openmw.world')
local I = require('openmw.interfaces')
local packs = require('scripts.wayfarer_packs.catalog')
local core = require('openmw.core')
local quality = require('scripts.wayfarer_packs.quality')
local generated = {}
local generatedCache = {}

local function publishGenerated()
    for _, actor in ipairs(world.players) do
        actor:sendEvent('WayfarerPacksCatalog', {packs = generated})
    end
end

local function scaledPack(templateId, multiplier)
    local template = packs[templateId]
    local magnitude = quality.feather(template.baseFeather, multiplier)
    local key = templateId .. ':' .. magnitude
    if generatedCache[key] then return generatedCache[key] end
    local ability = world.createRecord(core.magic.spells.createRecordDraft{
        template = core.magic.spells.records[template.ability],
        effects = {{id = core.magic.EFFECT_TYPE.Feather, range = core.magic.RANGE.Self,
            magnitudeMin = magnitude, magnitudeMax = magnitude}},
    })
    local item = world.createRecord(types.Miscellaneous.createRecordDraft{
        template = types.Miscellaneous.records[templateId],
        name = template.name .. ' (Feather ' .. magnitude .. ')',
    })
    local pack = {name = template.name, feather = magnitude, ability = ability.id,
        wornModel = template.wornModel, craftingOnly = true, baseFeather = template.baseFeather,
        templateId = templateId}
    generated[item.id] = pack
    packs[item.id] = pack
    generatedCache[key] = item.id
    return item.id
end

local function craft(data)
    if not data or not data.player or data.player.type ~= types.Player then return end
    local pack = packs[data.recordId]
    if not pack then return end
    local payload = {}
    for k, v in pairs(data) do payload[k] = v end
    if pack.craftingOnly then
        payload.recordId = scaledPack(data.recordId, data.qualityMult)
        publishGenerated()
    end
    payload.preserveRecordId = true
    -- Let CF consume materials, deliver the item, and notify its other integrations.
    core.sendGlobalEvent('CraftingFramework_getItem', payload)
end

local function separateCopies(item, actor)
    -- Keep the original reference so an already-worn copy stays selected.
    -- SCRI prevents moveInto from merging these copies back together.
    while item.count > 1 do item:split(1):moveInto(actor) end
end

local function normalizeInventory(actor)
    if actor.type ~= types.Player then return end
    for _, item in ipairs(types.Actor.inventory(actor):getAll(types.Miscellaneous)) do
        if packs[item.recordId] then separateCopies(item, actor) end
    end
end

I.ItemUsage.addHandlerForType(types.Miscellaneous, function(item, actor)
    if actor.type ~= types.Player or not packs[item.recordId] then return end
    -- Reject forged UseItem events for bags outside the player's inventory.
    for _, owned in ipairs(types.Actor.inventory(actor):getAll(types.Miscellaneous)) do
        if owned == item then
            separateCopies(item, actor)
            actor:sendEvent('WayfarerPacksUse', { item = item })
            return false
        end
    end
    return false
end)

local function stockMerchant(actor)
    if actor.recordId ~= 'arrille' or not types.NPC.objectIsInstance(actor) then return end
    local inventory = types.Actor.inventory(actor)
    for id, pack in pairs(packs) do
        if not pack.craftingOnly and not inventory:find(id) then
            world.createObject(id, 1):moveInto(actor)
        end
    end
end

return {
    engineHandlers = {
        onActorActive = function(actor)
            stockMerchant(actor)
            normalizeInventory(actor)
        end,
        onUpdate = function()
            for _, actor in ipairs(world.players) do normalizeInventory(actor) end
        end,
        onSave = function() return { version = 3, generated = generated, cache = generatedCache } end,
        -- Discard the legacy one-time stock flag: testing stock tops up on activation.
        onLoad = function(data)
            for id in pairs(generated) do packs[id] = nil end
            generated = data and data.generated or {}
            generatedCache = data and data.cache or {}
            for id, pack in pairs(generated) do packs[id] = pack end
        end,
    },
    eventHandlers = {
        WayfarerPacksCraft = craft,
    },
}
