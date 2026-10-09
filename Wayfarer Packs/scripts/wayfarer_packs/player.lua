local self = require('openmw.self')
local types = require('openmw.types')
local animation = require('openmw.animation')
local camera = require('openmw.camera')
local ui = require('openmw.ui')
local util = require('openmw.util')
local I = require('openmw.interfaces')
local packs = require('scripts.wayfarer_packs.catalog')
local generated = {}

local VFX_ID = 'WayfarerPacks_Worn'
local BONE = 'Bip01 Spine1'
local equipped
local dirty = true
local visualDirty = true
local lastCameraMode
local inventoryExtender
local inventoryDirty = true

local function registerInventoryIntegration()
    local api = I.InventoryExtender
    if not api or api == inventoryExtender or not api.registerEquippedOverride then return end
    api.registerEquippedOverride('WayfarerPacks', function(item, actor)
        if actor and actor.id == self.id and packs[item.recordId] then
            return item == equipped
        end
    end)
    if api.registerTooltipModifier and api.Templates and api.Templates.BASE then
        api.registerTooltipModifier('WayfarerPacks', function(item, layout)
            local pack = packs[item.recordId]
            if not pack then return end
            -- Inventory Extender nests item details inside two wrapper layouts.
            local ok, content = pcall(function() return layout.content[1].content[1].content end)
            if not ok or not content then return end
            local found, existing = pcall(function() return content.WayfarerPacksEffect end)
            if found and existing then return end
            pcall(function() content.name.props.text = pack.name end)
            local base = api.Templates.BASE
            if base.intervalV then content:add(base.intervalV(8)) end
            if I.MWUI and I.MWUI.templates and I.MWUI.templates.horizontalLine then
                content:add({template = I.MWUI.templates.horizontalLine,
                    props = {size = util.vector2(200, 2)}})
            end
            if base.intervalV then content:add(base.intervalV(4)) end
            content:add({
                name = 'WayfarerPacksDescription',
                template = base.textNormal,
                props = {text = 'A travel pack that lightens your load\nwhile worn. Only one pack can be worn.',
                    multiline = true, textAlignH = ui.ALIGNMENT.Center},
            })
            content:add({
                name = 'WayfarerPacksEffect',
                template = api.Templates.BASE.textNormal,
                props = {text = '+' .. pack.feather .. ' Feather',
                    textColor = util.color.rgb(.7, .5, .9), textAlignH = ui.ALIGNMENT.Center},
            })
        end)
    end
    if api.registerCellContentModifier then
        api.registerCellContentModifier('WayfarerPacks', function(cell, row)
            local pack = row.item and packs[row.item.recordId]
            if not pack then return end
            if cell.name == 'Name' then
                row.Name = pack.name
                local suffix = ' %(Feather ' .. pack.feather .. '%)'
                local text = cell.content and cell.content[1]
                if text and text.props and type(text.props.text) == 'string' then
                    text.props.text = text.props.text:gsub(suffix, '')
                end
                if cell.userData and type(cell.userData.text) == 'string' then
                    cell.userData.text = cell.userData.text:gsub(suffix, '')
                end
            end
        end)
    end
    inventoryExtender = api
    inventoryDirty = true
end

local function owned(item)
    if not item or not item:isValid() or item.count < 1 or not packs[item.recordId] then
        return false
    end
    for _, candidate in ipairs(types.Actor.inventory(self):getAll(types.Miscellaneous)) do
        if candidate == item then return true end
    end
    return false
end

local function reconcileAbilities()
    local spells = types.Actor.spells(self)
    local wanted = equipped and packs[equipped.recordId].ability or nil
    for _, pack in pairs(packs) do
        if pack.ability ~= wanted and spells[pack.ability] then
            spells:remove(pack.ability)
        end
    end
    if wanted and not spells[wanted] then spells:add(wanted) end
end

local function refreshVisual()
    -- First-person skeletons have different bones; retry after a camera rebuild.
    animation.removeVfx(self, VFX_ID)
    if not equipped or camera.getMode() == camera.MODE.FirstPerson then return true end
    if not animation.hasBone(self, BONE) then return false end
    animation.addVfx(self, packs[equipped.recordId].wornModel, {
        vfxId = VFX_ID,
        boneName = BONE,
        loop = true,
        autoTransform = false,
        useAmbientLight = false,
    })
    return true
end

local function selectPack(item, notify)
    equipped = item
    dirty = true
    visualDirty = true
    inventoryDirty = true
    if notify then
        if item then
            local pack = packs[item.recordId]
            ui.showMessage(pack.name .. ' equipped (Feather ' .. pack.feather .. ').')
        else
            ui.showMessage('Backpack unequipped.')
        end
    end
end

local function update()
    if equipped and not owned(equipped) then selectPack(nil, false) end
    if dirty then
        reconcileAbilities()
        dirty = false
    end
end

local function onFrame()
    -- Also run while inventory is open: dropping a bag must remove its bonus.
    update()
    registerInventoryIntegration()
    if inventoryDirty and inventoryExtender then
        inventoryDirty = false
        if inventoryExtender.refresh then inventoryExtender.refresh() end
    end
    local mode = camera.getMode()
    if mode ~= lastCameraMode then
        lastCameraMode = mode
        visualDirty = true
        return -- wait one frame for the camera's skeleton to be rebuilt
    end
    if visualDirty then visualDirty = not refreshVisual() end
end

return {
    interfaceName = 'WayfarerPacks',
    interface = {
        version = 1,
        getEquipped = function() return equipped end,
        unequip = function() selectPack(nil, false) end,
    },
    engineHandlers = {
        onUpdate = update,
        onFrame = onFrame,
        onActive = function() dirty = true; visualDirty = true end,
        onSave = function() return { version = 2, equipped = equipped, generated = generated } end,
        onLoad = function(data)
            for id in pairs(generated) do packs[id] = nil end
            generated = data and data.generated or {}
            for id, pack in pairs(generated) do packs[id] = pack end
            equipped = data and data.equipped or nil
            dirty = true
            visualDirty = true
            lastCameraMode = nil
            inventoryDirty = true
        end,
    },
    eventHandlers = {
        WayfarerPacksCatalog = function(data)
            if not data or not data.packs then return end
            for id, pack in pairs(data.packs) do
                generated[id] = pack
                packs[id] = pack
            end
            inventoryDirty = true
        end,
        WayfarerPacksUse = function(data)
            if not data or not owned(data.item) then return end
            if equipped == data.item then
                selectPack(nil, true)
            else
                selectPack(data.item, true)
            end
        end,
    },
}
