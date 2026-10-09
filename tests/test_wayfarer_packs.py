"""Exercise equipment lifecycle in Lua and inspect the shipped TES3 records."""
from pathlib import Path
import json
import struct
import sys
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lupa.lua51 import LuaRuntime
import build_wayfarer_packs as builder

MOD = ROOT / 'Wayfarer Packs'

MOCK = """
types = {Actor = {}, Miscellaneous = {}, Player = {}, NPC = {}}
types.NPC.objectIsInstance = function(actor) return actor.type == types.NPC end
inventory = {}
local inventoryApi = {}
function inventoryApi:getAll(kind) return inventory end
function inventoryApi:find(id)
    for _, item in ipairs(inventory) do
        if item.recordId == id and item.count > 0 then return item end
    end
end
spells = { vanilla_feather = {id='vanilla_feather'} }
function spells:add(id) self[id] = {id=id} end
function spells:remove(id) self[id] = nil end
player = {type=types.Player, recordId='player', id='player', events={}}
function player:sendEvent(name, data) table.insert(self.events, {name=name, data=data}) end
types.Actor.inventory = function(actor) return actor.inventory or inventoryApi end
types.Actor.spells = function(actor) return spells end
vfx = {}; visualAdds = 0; boneExists = true; mode = 3
animation = {
    removeVfx = function(actor, id) vfx[id] = nil end,
    hasBone = function(actor, bone) return boneExists end,
    addVfx = function(actor, model, options)
        assert(options.vfxId == 'WayfarerPacks_Worn')
        assert(options.boneName == 'Bip01 Spine1')
        vfx[options.vfxId] = model; visualAdds = visualAdds + 1
    end,
}
camera = {MODE={FirstPerson=1}, getMode=function() return mode end}
messages = {}
ui = {ALIGNMENT={Center=1}, showMessage=function(message) table.insert(messages, message) end}
util = {color={rgb=function(r,g,b) return {r=r,g=g,b=b} end},
    vector2=function(x,y) return {x=x,y=y} end}
usage = {}; interfaces = {ItemUsage={}}
interfaces.ItemUsage.addHandlerForType = function(kind, handler) usage.handler = handler end
created = 0
world = {createObject=function(id, count)
    created = created + 1
    return {moveInto=function(item, actor) table.insert(actor.stock, {recordId=id, count=count}) end}
end}
world.players = {player}
core = {events={}, magic={spells={records={}}, EFFECT_TYPE={Feather='feather'}, RANGE={Self=0}}}
core.sendGlobalEvent = function(name,data) table.insert(core.events,{name=name,data=data}) end
core.magic.spells.createRecordDraft = function(draft) return draft end
types.Miscellaneous.records = {}
types.Miscellaneous.createRecordDraft = function(draft) return draft end
recordCount = 0
world.createRecord = function(draft)
    recordCount = recordCount + 1
    draft.id = 'generated_'..recordCount
    return draft
end
package.preload['openmw.core'] = function() return core end
package.preload['openmw.types'] = function() return types end
package.preload['openmw.self'] = function() return player end
package.preload['openmw.animation'] = function() return animation end
package.preload['openmw.camera'] = function() return camera end
package.preload['openmw.ui'] = function() return ui end
package.preload['openmw.util'] = function() return util end
package.preload['openmw.world'] = function() return world end
package.preload['openmw.interfaces'] = function() return interfaces end
function bag(id)
    local item = {recordId=id, count=1, valid=true}
    function item:isValid() return self.valid end
    function item:split(count)
        assert(count > 0 and count < self.count)
        self.count = self.count - count
        local copy = {recordId=self.recordId, count=count, valid=true, isValid=self.isValid}
        function copy:moveInto(actor)
            assert(actor == player)
            table.insert(inventory, self)
        end
        return copy
    end
    table.insert(inventory, item)
    return item
end
function equip(item)
    mod.eventHandlers.WayfarerPacksUse({item=item})
    mod.engineHandlers.onUpdate(0)
    mod.engineHandlers.onFrame()
    mod.engineHandlers.onFrame()
end
function abilityCount()
    local count = 0
    for id in pairs(spells) do
        if id:find('wfp_') == 1 then count = count + 1 end
    end
    return count
end
"""


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().mod_path = MOD.as_posix()
        self.lua.execute("package.path = mod_path .. '/?.lua;' .. package.path")
        self.lua.execute(MOCK)
        self.lua.execute("mod = require('scripts.wayfarer_packs.player')")

    def test_switch_toggle_and_unrelated_feather(self):
        self.lua.execute("""
            a = bag('wfp_satchel'); b = bag('wfp_expedition')
            equip(a); assert(spells.wfp_satchel_ability and abilityCount() == 1)
            equip(b); assert(spells.wfp_expedition_ability and abilityCount() == 1)
            assert(not spells.wfp_satchel_ability)
            equip(b); assert(abilityCount() == 0 and spells.vanilla_feather)
            assert(vfx.WayfarerPacks_Worn == nil)
        """)

    def test_use_stack_equips_only_original_single_copy(self):
        self.lua.execute("""
            global = require('scripts.wayfarer_packs.global')
            a = bag('wfp_backpack'); a.count = 4
            interfaces.InventoryExtender = {
                registerEquippedOverride = function(id, callback) override = callback end,
            }
            usage.handler(a, player)
            assert(a.count == 1 and #inventory == 4)
            equip(player.events[1].data.item)
            assert(mod.interface.getEquipped() == a and abilityCount() == 1)
            for _, item in ipairs(inventory) do
                assert(item.count == 1)
                assert(override(item, player) == (item == a))
            end
            equip(a); assert(abilityCount() == 0 and #inventory == 4)
        """)

    def test_existing_worn_stack_and_bulk_add_preserve_selected_reference(self):
        self.lua.execute("""
            global = require('scripts.wayfarer_packs.global')
            a = bag('wfp_satchel'); a.count = 3
            mod.engineHandlers.onLoad({version=1, equipped=a})
            global.engineHandlers.onActorActive(player)
            mod.engineHandlers.onFrame()
            assert(a.count == 1 and mod.interface.getEquipped() == a)
            b = bag('wfp_satchel'); b.count = 5
            global.engineHandlers.onUpdate()
            assert(#inventory == 8 and b.count == 1 and abilityCount() == 1)
            for _, item in ipairs(inventory) do assert(item.count == 1) end
            global.engineHandlers.onUpdate(); assert(#inventory == 8)
            inventory = {b}; mod.engineHandlers.onFrame()
            assert(abilityCount() == 0)
        """)

    def test_dropped_selected_copy_does_not_transfer_bonus_to_duplicate(self):
        self.lua.execute("""
            a = bag('wfp_backpack'); b = bag('wfp_backpack'); equip(a)
            inventory = {b}; mod.engineHandlers.onFrame()
            assert(abilityCount() == 0 and mod.interface.getEquipped() == nil)
            equip(b); assert(abilityCount() == 1)
        """)

    def test_deleted_or_empty_stack_removes_bonus(self):
        for removal in ('a.valid = false', 'a.count = 0'):
            with self.subTest(removal=removal):
                self.setUp()
                self.lua.execute("a = bag('wfp_backpack'); equip(a)")
                self.lua.execute(removal)
                self.lua.execute("mod.engineHandlers.onFrame(); assert(abilityCount() == 0)")

    def test_carrying_extra_bags_does_not_stack(self):
        self.lua.execute("""
            a = bag('wfp_satchel'); bag('wfp_backpack'); bag('wfp_expedition')
            equip(a); mod.engineHandlers.onFrame(); assert(abilityCount() == 1)
            assert(spells.wfp_satchel_ability)
        """)

    def test_reload_restores_only_selected_ability_and_one_model(self):
        self.lua.execute("""
            a = bag('wfp_backpack'); equip(a); saved = mod.engineHandlers.onSave()
            spells.wfp_satchel_ability = {id='wfp_satchel_ability'}
            spells.wfp_backpack_ability = nil
            mod.engineHandlers.onLoad(saved)
            mod.engineHandlers.onFrame(); mod.engineHandlers.onFrame()
            assert(abilityCount() == 1 and spells.wfp_backpack_ability)
            assert(mod.interface.getEquipped() == a)
            assert(vfx.WayfarerPacks_Worn)
        """)

    def test_stale_save_and_missing_script_save_clear_orphan_abilities(self):
        self.lua.execute("""
            a = bag('wfp_backpack'); equip(a); saved = mod.engineHandlers.onSave()
            inventory = {}; mod.engineHandlers.onLoad(saved); mod.engineHandlers.onFrame()
            assert(abilityCount() == 0)
            spells.wfp_satchel_ability = {id='wfp_satchel_ability'}
            mod.engineHandlers.onLoad(nil); mod.engineHandlers.onFrame()
            assert(abilityCount() == 0 and spells.vanilla_feather)
        """)

    def test_forged_or_unknown_item_event_is_ignored(self):
        self.lua.execute("""
            a = bag('wfp_satchel'); inventory = {}; equip(a)
            assert(abilityCount() == 0)
            b = bag('misc_de_lute_01'); equip(b); assert(abilityCount() == 0)
            mod.eventHandlers.WayfarerPacksUse(nil)
        """)

    def test_camera_rebuild_and_temporarily_missing_bone(self):
        self.lua.execute("""
            a = bag('wfp_backpack'); equip(a)
            mode = 1; mod.engineHandlers.onFrame(); mod.engineHandlers.onFrame()
            assert(vfx.WayfarerPacks_Worn == nil and abilityCount() == 1)
            mode = 3; boneExists = false
            mod.engineHandlers.onFrame(); mod.engineHandlers.onFrame()
            assert(vfx.WayfarerPacks_Worn == nil)
            boneExists = true; mod.engineHandlers.onFrame()
            assert(vfx.WayfarerPacks_Worn and abilityCount() == 1)
            before = visualAdds; mod.engineHandlers.onFrame(); assert(visualAdds == before)
        """)

    def test_cleanup_interface(self):
        self.lua.execute("""
            a = bag('wfp_expedition'); equip(a); mod.interface.unequip()
            mod.engineHandlers.onFrame(); assert(abilityCount() == 0)
            assert(vfx.WayfarerPacks_Worn == nil and spells.vanilla_feather)
        """)

    def test_artisan_variants_share_slot_and_cleanup_without_crafting_framework(self):
        self.lua.execute("""
            local catalog = require('scripts.wayfarer_packs.catalog')
            for _, id in ipairs({'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}) do
                normal = bag(id); artisan = bag(id..'_artisan')
                equip(normal); equip(artisan)
                assert(abilityCount() == 1 and spells[id..'_artisan_ability'])
                assert(not spells[id..'_ability'])
                assert(catalog[id].wornModel == catalog[id..'_artisan'].wornModel)
                saved = mod.engineHandlers.onSave()
                mod.engineHandlers.onLoad(saved); mod.engineHandlers.onFrame()
                assert(mod.interface.getEquipped() == artisan)
                equip(artisan); assert(abilityCount() == 0)
            end
        """)

    def test_scaled_craft_cache_persistence_and_player_catalog_recovery(self):
        self.lua.execute("""
            global = require('scripts.wayfarer_packs.global')
            local data = {player=player, recordId='wfp_backpack_artisan', qualityMult=1.42,
                consumedIngredients={leather=6}, count=1}
            global.eventHandlers.WayfarerPacksCraft(data)
            assert(recordCount==2 and data.recordId=='wfp_backpack_artisan')
            local result = core.events[1].data
            assert(result.recordId=='generated_2' and result.preserveRecordId)
            assert(result.consumedIngredients==data.consumedIngredients)
            assert(player.events[1].name=='WayfarerPacksCatalog')
            local metadata=player.events[1].data
            assert(metadata.packs.generated_2.feather==71)
            mod.eventHandlers.WayfarerPacksCatalog(metadata)
            a=bag(result.recordId); equip(a)
            assert(spells.generated_1 and mod.interface.getEquipped()==a)
            local saved=mod.engineHandlers.onSave()
            local globalSaved=global.engineHandlers.onSave()
            mod.engineHandlers.onLoad(nil); mod.engineHandlers.onFrame()
            global.engineHandlers.onLoad(globalSaved)
            mod.engineHandlers.onLoad(saved); mod.engineHandlers.onFrame()
            assert(mod.interface.getEquipped()==a and spells.generated_1)
            global.eventHandlers.WayfarerPacksCraft(data); assert(recordCount==2)
            data.qualityMult=2.5; global.eventHandlers.WayfarerPacksCraft(data)
            assert(recordCount==4 and core.events[3].data.recordId=='generated_4')
            global.eventHandlers.WayfarerPacksCraft({player=player,recordId='wfp_satchel'})
            assert(core.events[4].data.recordId=='wfp_satchel' and recordCount==4)
            inventory={}; mod.engineHandlers.onFrame(); assert(not spells.generated_1)
        """)

    def test_optional_inventory_extender_equipped_override_and_refresh(self):
        self.lua.execute("""
            a = bag('wfp_backpack'); b = bag('wfp_backpack'); equip(a)
            registrations = 0; refreshes = 0
            interfaces.InventoryExtender = {
                registerEquippedOverride = function(id, callback)
                    assert(id == 'WayfarerPacks')
                    registrations = registrations + 1; override = callback
                end,
                refresh = function() refreshes = refreshes + 1 end,
            }
            mod.engineHandlers.onFrame()
            assert(override(a, player) == true and override(b, player) == false)
            assert(override(a, {id='npc'}) == nil)
            assert(override({recordId='iron_shortsword'}, player) == nil)
            mod.engineHandlers.onFrame()
            assert(registrations == 1 and refreshes == 1)
            equip(b)
            assert(override(a, player) == false and override(b, player) == true)
            assert(refreshes == 2)
            inventory = {a}; mod.engineHandlers.onFrame()
            assert(override(a, player) == false and refreshes == 3)
        """)

    def test_inventory_extender_tooltip_and_unrelated_layouts(self):
        self.lua.execute("""
            interfaces.InventoryExtender = {
                Templates = {BASE = {textNormal = {}, intervalV=function(n) return {props={height=n}} end}},
                registerEquippedOverride = function() end,
                registerTooltipModifier = function(id, callback) tooltip = callback end,
                registerCellContentModifier = function(id, callback) cellModifier = callback end,
            }
            interfaces.MWUI = {templates={horizontalLine={}}}
            mod.engineHandlers.onFrame()
            content = {}
            content.name = {props={text='Old name'}}
            function content:add(row) self[#self+1] = row; if row.name then self[row.name] = row end end
            layout = {content={{content={{content=content}}}}}
            a = bag('wfp_backpack')
            tooltip(a, layout); tooltip(a, layout)
            assert(#content == 5 and content.name.props.text == "Wayfarer's Backpack")
            assert(content.WayfarerPacksEffect.props.text == '+50 Feather')
            assert(content.WayfarerPacksEffect.props.textColor.b == .9)
            assert(content.WayfarerPacksDescription.props.multiline)
            tooltip({recordId='iron_shortsword'}, layout); assert(#content == 5)
            tooltip(a, {})
            row = {item=a, Name="Wayfarer's Backpack (Feather 50)"}
            cell = {name='Name', content={{props={text=row.Name}}}, userData={text=row.Name}}
            cellModifier(cell, row)
            assert(row.Name == "Wayfarer's Backpack" and cell.content[1].props.text == row.Name)
            assert(cell.userData.text == row.Name)
            cellModifier(cell, {item={recordId='iron_shortsword'}})
            tooltip({recordId='wfp_satchel'}, {})
        """)

    def test_inventory_name_cleanup_preserves_stack_and_drag_counts(self):
        self.lua.execute("""
            interfaces.InventoryExtender = {
                registerEquippedOverride = function() end,
                registerCellContentModifier = function(id, callback) cellModifier = callback end,
            }
            mod.engineHandlers.onFrame()
            a = bag('wfp_backpack')
            for _, count in ipairs({'', ' (3)', ' (1,000)'}) do
                local label = "Wayfarer's Backpack (Feather 50)" .. count
                local row = {item=a}
                local cell = {name='Name', content={{props={text=label}}}, userData={text=label}}
                cellModifier(cell, row); cellModifier(cell, row)
                assert(cell.content[1].props.text == "Wayfarer's Backpack" .. count)
                assert(cell.userData.text == cell.content[1].props.text)
            end
            cellModifier({name='Name', content={{props={text=123}}}}, {item=a})
        """)

    def test_inventory_use_handler_checks_ownership_and_player(self):
        self.lua.execute("""
            global = require('scripts.wayfarer_packs.global')
            a = bag('wfp_satchel')
            assert(usage.handler(a, player) == false)
            assert(player.events[1].name == 'WayfarerPacksUse')
            inventory = {}; assert(usage.handler(a, player) == false)
            assert(#player.events == 1)
            npc = {type=types.NPC}; assert(usage.handler(a, npc) == nil)
            assert(usage.handler({recordId='misc_de_lute_01'}, player) == nil)
        """)

    def test_merchant_testing_stock_tops_up_without_duplicates_and_ignores_legacy_flag(self):
        self.lua.execute("""
            global = require('scripts.wayfarer_packs.global')
            merchant = {recordId='arrille', id='arrille-ref', type=types.NPC, stock={}}
            merchant.inventory = {find=function(inv,id)
                for _, item in ipairs(merchant.stock) do if item.recordId == id then return item end end
            end}
            global.engineHandlers.onActorActive(merchant)
            assert(created == 3 and #merchant.stock == 3)
            global.engineHandlers.onActorActive(merchant); assert(created == 3)
            table.remove(merchant.stock, 1)
            global.engineHandlers.onLoad({version=1, supplied={['arrille-ref']=true}})
            global.engineHandlers.onActorActive(merchant)
            assert(created == 4 and #merchant.stock == 3)
            saved = global.engineHandlers.onSave(); assert(saved.version == 3)
            global.engineHandlers.onLoad(saved)
            global.engineHandlers.onActorActive(merchant); assert(created == 4)
            global.engineHandlers.onActorActive({recordId='other', type=types.NPC})
            assert(created == 4)
            merchant.stock = {}
            global.engineHandlers.onActorActive(merchant); assert(created == 7)
        """)


def records(data, header_size):
    pos = 0
    while pos < len(data):
        tag = data[pos:pos+4].decode('ascii')
        size, = struct.unpack_from('<I', data, pos+4)
        end = pos+header_size+size
        if end > len(data):
            raise AssertionError('Truncated record')
        yield tag, data[pos+header_size:end]
        pos = end


class DistributionTests(unittest.TestCase):
    def test_quality_scaling_rounding_and_no_balance_cap(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        quality = lua.execute((MOD / 'scripts/wayfarer_packs/quality.lua').read_text())
        for base, multiplier, expected in ((25, 1.5, 38), (50, 1.42, 71),
                (75, 1.35, 101), (50, 1.15, 58), (75, 2.5, 188), (50, .9, 45)):
            self.assertEqual(quality.feather(base, multiplier), expected)
        self.assertEqual(quality.feather(50, float('nan')), 50)
        self.assertEqual(quality.feather(50, -1), 0)

    def test_artisan_crafting_hooks_preserve_existing_gate_and_scope_modifiers(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().mod_path = MOD.as_posix()
        lua.execute("package.path = mod_path .. '/?.lua;' .. package.path")
        lua.execute("""
            touchList = {{id='artisan', label="Artisan's touch", priority=-1,
                gate=function(recipe) return recipe.customEligible == true end}}
            registerTouch = function(touch) artisanTouch=touch; touchList={touch} end
            registerResultItemModifier = function(opts) resultModifier=opts.func end
            registerRecipeNameModifier = function(opts) nameModifier=opts.func end
        """)
        recipes = lua.execute((MOD / 'CF_recipes/wayfarerPacks.lua').read_text())
        self.assertEqual(len(recipes), 3)
        lua.execute("""
            local catalog = require('scripts.wayfarer_packs.catalog')
            for _, id in ipairs({'wfp_satchel', 'wfp_backpack', 'wfp_expedition'}) do
                local recipe = {id=id, type='Miscellaneous', preserveRecordId=true}
                assert(artisanTouch.gate(recipe))
                local ctx = {touches={artisan=true}, modified=id, qualityMult=1.15}
                resultModifier(recipe,ctx); assert(ctx.modified == id..'_artisan')
                nameModifier(recipe,ctx)
                assert(ctx.modified:find(catalog[id..'_artisan'].name,1,true))
                local inactive = {modified=id}
                resultModifier(recipe,inactive); assert(inactive.modified==id)
            end
            assert(artisanTouch.gate({customEligible=true}))
            assert(not artisanTouch.gate({id='unrelated', type='Miscellaneous'}))
            assert(not artisanTouch.gate({id='wfp_satchel_artisan', type='Miscellaneous', preserveRecordId=true}))
            local unrelated = {modified='unrelated', touches={artisan=true}}
            resultModifier({id='unrelated'},unrelated); nameModifier({id='unrelated'},unrelated)
            assert(unrelated.modified=='unrelated')
        """)

    def test_optional_crafting_recipe_data_preserves_ids_and_balance(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        recipe_file = MOD / 'CF_recipes/wayfarerPacks.lua'
        recipes = lua.execute(recipe_file.read_text())
        self.assertEqual(len(recipes), 3)
        for i, (id, level, leather) in enumerate((
                ('wfp_satchel', 10, 3), ('wfp_backpack', 25, 6),
                ('wfp_expedition', 40, 10)), 1):
            recipe = recipes[i]
            self.assertEqual(recipe['id'], '!'+id)
            self.assertEqual(recipe['types'], 'Miscellaneous')
            self.assertEqual(recipe['count'], 1)
            self.assertEqual(recipe['level'], level)
            self.assertEqual(recipe['craftingCategory'], 'Travel Packs')
            self.assertEqual(recipe['ingredients'][1]['id'], 'Any leather')
            self.assertEqual(recipe['ingredients'][1]['count'], leather)
            self.assertEqual(len(recipe['ingredients']), 1)
        lua.execute('world = {}')
        self.assertIsNone(lua.execute(recipe_file.read_text()))

    def test_crafting_framework_is_not_a_runtime_or_plugin_dependency(self):
        content = (MOD / 'WayfarerPacks.omwscripts').read_text()
        self.assertNotIn('CraftingFramework', content)
        for script in (MOD / 'scripts').rglob('*.lua'):
            self.assertNotIn('scripts.CraftingFramework', script.read_text())
        header = list(records((MOD / 'WayfarerPacks.esp').read_bytes(), 16))[0][1]
        masters = [data for tag, data in records(header, 8) if tag == 'MAST']
        self.assertEqual(masters, [b'Morrowind.esm\0'])

    def test_records_match_balance_data_and_assets(self):
        packs = builder.all_packs(json.loads((MOD / 'packs.json').read_text()))
        contents = list(records((MOD / 'WayfarerPacks.esp').read_bytes(), 16))
        self.assertEqual(len(contents), 2+2*len(packs))
        self.assertEqual(contents[0][0], 'TES3')
        header = dict(records(contents[0][1], 8))
        self.assertEqual(struct.unpack_from('<i', header['HEDR'], 296)[0], 13)
        self.assertEqual(header['MAST'], b'Morrowind.esm\0')
        for i, pack in enumerate(packs):
            kind, body = contents[1+i*2]
            self.assertEqual(kind, 'MISC')
            item = dict(records(body, 8))
            self.assertEqual(item['NAME'].rstrip(b'\0').decode(), pack['id'])
            self.assertEqual(item['SCRI'], b'wfp_unique_item\0')
            weight, value, is_key = struct.unpack('<fii', item['MCDT'])
            self.assertEqual((weight, value, is_key), (pack['weight'], pack['value'], 0))
            for field, folder in [('MODL', 'meshes'), ('ITEX', 'icons')]:
                self.assertTrue((MOD / folder / item[field].rstrip(b'\0').decode()).is_file())
            kind, body = contents[2+i*2]
            self.assertEqual(kind, 'SPEL')
            spell = dict(records(body, 8))
            self.assertEqual(struct.unpack('<iii', spell['SPDT']), (1, 0, 0))
            self.assertEqual(struct.unpack('<hbbiiiii', spell['ENAM']),
                             (8, -1, -1, 0, 0, 0, pack['feather'], pack['feather']))
        self.assertEqual(contents[-1][0], 'SCPT')
        script = dict(records(contents[-1][1], 8))
        self.assertEqual(script['SCHD'][:32].rstrip(b'\0'), b'wfp_unique_item')
        self.assertIn(b'begin wfp_unique_item', script['SCTX'])

    def test_archive_has_both_content_files_and_every_asset(self):
        with ZipFile(ROOT / f'dist/WayfarerPacks-{builder.VERSION}.zip') as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
            self.assertIn('WayfarerPacks.esp', names)
            self.assertIn('WayfarerPacks.omwscripts', names)
            for path in MOD.rglob('*'):
                if path.is_file():
                    name = path.relative_to(MOD).as_posix()
                    self.assertEqual(archive.read(name), path.read_bytes())

    def test_meshes_have_explicit_vertex_color_materials(self):
        for path in (MOD / 'meshes/wayfarer_packs').glob('*.osgt'):
            with self.subTest(mesh=path.name):
                source = path.read_text()
                self.assertIn('osg::Material {', source)
                self.assertIn('ColorMode AMBIENT_AND_DIFFUSE', source)
                self.assertIn('Emission TRUE Front 0 0 0 1', source)

    def test_worn_rotation_maps_height_to_spine_axis_and_preserves_normals(self):
        for pack in json.loads((MOD / 'packs.json').read_text()):
            with self.subTest(pack=pack['id']):
                h, d = pack['height'], pack['depth']
                color = (0.3, 0.4, 0.5)
                a, b, c, result_color = builder.worn_geometry(
                    [((0, 0, h/2), (1, 0, h/2), (0, 0, h/2+1), color)], pack)[0]
                self.assertEqual(a, (5, -5-d/2, 0))
                self.assertEqual(b, (5, -5-d/2, -1))
                self.assertEqual(c, (6, -5-d/2, 0))
                self.assertEqual(result_color, color)
                self.assertEqual(builder.normal(a, b, c), (0, -1, 0))
                triangles = builder.geometry(pack)
                mesh_dir = MOD / 'meshes/wayfarer_packs'
                self.assertEqual((mesh_dir / (pack['id']+'.osgt')).read_text(),
                                 builder.osg(triangles))
                self.assertEqual((mesh_dir / (pack['id']+'_worn.osgt')).read_text(),
                                 builder.osg(builder.worn_geometry(triangles, pack), uv_triangles=triangles))

    def test_preview_matches_exported_geometry_and_texture(self):
        preview = ROOT / 'pack-preview/public/assets'
        data = json.loads((preview / 'packs.json').read_text())
        self.assertEqual(data['version'], builder.VERSION)
        for pack in data['models']:
            self.assertEqual(pack['wornBackOffset'], builder.WORN_BACK_OFFSET)
            self.assertEqual(pack['wornHeightOffset'], builder.WORN_HEIGHT_OFFSET)
            triangles = builder.geometry(pack)
            arrays = builder.mesh_arrays(triangles)
            for key, values in zip(('positions', 'normals', 'colors', 'uvs'), arrays):
                self.assertEqual(pack[key], [list(row) for row in values])
            self.assertGreater(pack['triangles'], 1000)
            self.assertEqual(arrays[3], builder.mesh_arrays(
                builder.worn_geometry(triangles, pack), triangles)[3])
            for n in arrays[1]:
                self.assertAlmostEqual(sum(v*v for v in n), 1)
        self.assertEqual((preview / 'leather.png').read_bytes(),
                         (MOD / 'textures/wayfarer_packs/leather.png').read_bytes())
        reference = preview / 'vanilla-fit.json'
        if reference.exists():
            fit = json.loads(reference.read_text())
            points = [(-p[2], p[1], p[0]) for p in fit['positions']]
            torso = [(*points[i:i+3], (1,1,1)) for i in range(0, len(points), 3)]
            for route in builder.BODY_FIT['routes']:
                for x, y, z in route[3:]:
                    self.assertAlmostEqual(y-builder.surface_y(torso, x, z, False), .1)
            with ZipFile(ROOT / f'dist/WayfarerPacks-{builder.VERSION}.zip') as archive:
                self.assertFalse(any('vanilla-fit' in name or name.endswith('.nif')
                                     for name in archive.namelist()))

    def test_flap_contact_threaded_buckles_and_anchored_harnesses(self):
        for pack in json.loads((MOD / 'packs.json').read_text()):
            with self.subTest(pack=pack['id']):
                details = {}
                builder.geometry(pack, details)
                for x, z, front, y in details['flap_samples']:
                    actual = builder.surface_y(details['body'], x, z, front)
                    self.assertAlmostEqual(abs(y-actual), .14)
                for tie, (_, bar_y, bar_z) in zip(details['ties'], details['buckles']):
                    loop = [p for p in tie if abs(p[2]-bar_z)<.6]
                    self.assertTrue(any(p[1]>bar_y for p in loop))
                    self.assertTrue(any(p[1]<bar_y-.2 for p in loop))
                    self.assertTrue(any(p[2]>bar_z for p in loop))
                    self.assertTrue(any(p[2]<bar_z for p in loop))
                for path in details['harnesses']:
                    for x, y, z, _ in (path[0], path[-1]):
                        self.assertAlmostEqual(y, builder.surface_y(details['body'], x, z, False)-.08)
                    worn = builder.worn_geometry([(p[:3], p[:3], p[:3], (1,1,1)) for p in path], pack)
                    points = [t[0] for t in worn]
                    self.assertGreater(max(p[0] for p in points), 22)
                    self.assertLess(max(p[0] for p in points), 23)
                    self.assertLess(max(abs(p[2]) for p in points), 9)
                    self.assertLess(max(p[1] for p in points), 10)

    def test_tie_surfaces_clear_body_flap_and_pocket_between_vertices(self):
        for pack in json.loads((MOD / 'packs.json').read_text()):
            details = {}
            builder.geometry(pack, details)
            for mesh, path in zip(details['tie_meshes'], details['ties']):
                for a, b, c, _ in mesh:
                    # Sample face interiors as well as edges: endpoints alone
                    # miss a strap triangle cutting through a curved flap.
                    for weights in ((1/3, 1/3, 1/3), (.5, .5, 0), (0, .5, .5), (.5, 0, .5)):
                        p = tuple(sum(weights[j]*v[k] for j, v in enumerate((a, b, c)))
                                  for k in range(3))
                        surface = builder.surface_y(details['support'], p[0], p[2])
                        end_distance = min(abs(p[2]-path[0][2]), abs(p[2]-path[-1][2]))
                        minimum = 0 if end_distance < .1 else .025
                        self.assertGreater(surface-p[1], minimum,
                                           f"{pack['id']}: strap intersects support at {p}")

    def test_seated_straps_follow_support_without_an_air_gap(self):
        for pack in json.loads((MOD / 'packs.json').read_text()):
            details = {}
            builder.geometry(pack, details)
            self.assertTrue(details['contact_faces'])
            for a, b, c, _ in details['contact_faces']:
                for weights in ((1/3, 1/3, 1/3), (.5, .5, 0), (0, .5, .5), (.5, 0, .5)):
                    p = tuple(sum(weights[j]*v[k] for j, v in enumerate((a, b, c)))
                              for k in range(3))
                    support = builder.surface_y(details['support'], p[0], p[2])
                    # 0.10 is leather thickness, not empty clearance. Its rear
                    # face is embedded 0.002 units into this exact support plane.
                    self.assertAlmostEqual(support-p[1], .10, places=6,
                                           msg=f"{pack['id']}: strap stands off the leather")


if __name__ == '__main__':
    unittest.main()
