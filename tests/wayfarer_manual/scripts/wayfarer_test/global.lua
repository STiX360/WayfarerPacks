local world = require('openmw.world')
local types = require('openmw.types')
local prepared = false
local elapsed = 0

return {
    engineHandlers = {
        onUpdate = function(dt)
            elapsed = elapsed + dt
            local player = world.players[1]
            if prepared or not player or elapsed < .5 then return end
            world.createObject('gold_001', 5000):moveInto(player)
            for _, id in ipairs({'common_shirt_01', 'common_pants_01', 'common_shoes_01'}) do
                local item = world.createObject(id, 1)
                item:moveInto(player)
            end
            for id, count in pairs({ingred_netch_leather_01 = 48, ingred_diamond_01 = 3, hammer_repair = 1}) do
                world.createObject(id, count):moveInto(player)
            end
            prepared = true
            player:sendEvent('WayfarerTestReady', {})
        end,
        onSave = function() return {prepared = prepared} end,
        onLoad = function(data)
            prepared = data and data.prepared == true or false
            elapsed = 0
        end,
    },
    eventHandlers = {
        WayfarerTestArtisanMaterials = function()
            world.createObject('ingred_netch_leather_01', 19):moveInto(world.players[1])
        end,
        WayfarerTestBulkPack = function()
            -- Simulate an old save/console-created multi-copy reference.
            world.createObject('wfp_backpack', 4):moveInto(world.players[1])
        end,
        WayfarerTestCheckStock = function()
            local stocked = false
            for _, actor in ipairs(world.activeActors) do
                if actor.recordId == 'arrille' then
                    local inv = types.Actor.inventory(actor)
                    stocked = inv:find('wfp_satchel') ~= nil and inv:find('wfp_backpack') ~= nil
                        and inv:find('wfp_expedition') == nil
                    break
                end
            end
            world.players[1]:sendEvent('WayfarerTestStock', {stocked = stocked})
        end,
    },
}
