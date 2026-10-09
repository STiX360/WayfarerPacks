local camera = require('openmw.camera')
local ui = require('openmw.ui')
local self = require('openmw.self')
local types = require('openmw.types')

return {
    eventHandlers = {
        WayfarerTestReady = function()
            types.NPC.stats.skills.armorer(self).base = 60
            local equipment = types.Actor.getEquipment(self)
            equipment[types.Actor.EQUIPMENT_SLOT.Shirt] = 'common_shirt_01'
            equipment[types.Actor.EQUIPMENT_SLOT.Pants] = 'common_pants_01'
            equipment[types.Actor.EQUIPMENT_SLOT.Boots] = 'common_shoes_01'
            types.Actor.setEquipment(self, equipment)
            camera.setMode(camera.MODE.ThirdPerson)
            ui.showMessage('Wayfarer Packs test: 5,000 gold, crafting materials, and a repair hammer ready.')
            print('WFP_MANUAL_READY: fresh character prepared')
        end,
    },
}
