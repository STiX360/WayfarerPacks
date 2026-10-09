local core = require('openmw.core')
local world = require('openmw.world')
local util = require('openmw.util')
local prepared = false
local age = 0

return {
    engineHandlers = {
        onUpdate = function(dt)
            age = age + dt
            if age > 30 then print('WFP_SMOKE_TIMEOUT'); core.quit() end
            if prepared or not world.players[1] then return end
            local player = world.players[1]
            for i, id in ipairs({'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}) do
                world.createObject(id, 1):moveInto(player)
                local object = world.createObject(id, 1)
                object:teleport(player.cell, player.position + util.vector3(i*40, 40, 0))
            end
            prepared = true
        end,
    },
    eventHandlers = {
        WFPTestDiscard = function(data) data.item:remove() end,
    },
}
