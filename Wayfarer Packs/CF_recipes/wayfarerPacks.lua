-- Crafting Framework discovers this data file; OpenMW alone never executes it.
if world then return end

-- Extend the diamond toggle, retaining other mods' eligibility rules.
if registerTouch and registerResultItemModifier and registerRecipeNameModifier and touchList then
    local catalog = require('scripts.wayfarer_packs.catalog')
    local quality = require('scripts.wayfarer_packs.quality')
    local artisan
    for _, touch in ipairs(touchList) do
        if touch.id == 'artisan' then artisan = touch; break end
    end
    if artisan then
        local previousGate = artisan.gate
        local function packRecipe(recipe)
            local pack = catalog[recipe.id]
            return recipe.type == 'Miscellaneous' and recipe.preserveRecordId
                and pack and pack.artisanId ~= nil
        end
        registerTouch{
            id = artisan.id, label = artisan.label, priority = artisan.priority,
            gate = function(recipe)
                return packRecipe(recipe) or not previousGate or previousGate(recipe)
            end,
        }
        local function active(recipe, ctx)
            return packRecipe(recipe) and ctx.touches and ctx.touches.artisan
        end
        registerResultItemModifier{
            id = 'WayfarerPacks:artisan', global = true,
            func = function(recipe, ctx)
                if active(recipe, ctx) then ctx.modified = catalog[recipe.id].artisanId end
            end,
        }
        registerRecipeNameModifier{
            id = 'WayfarerPacks:artisan', global = true,
            func = function(recipe, ctx)
                if active(recipe, ctx) then
                    local pack = catalog[catalog[recipe.id].artisanId]
                    local multiplier = ctx.qualityMult or calculateQuality(recipe, ctx.touches, ctx.isPreview)
                    ctx.modified = pack.name .. ' (Feather ' .. quality.feather(pack.baseFeather, multiplier) .. ')'
                end
            end,
        }
    end
end

return {
    {
        id = '!wfp_satchel', types = 'Miscellaneous', count = 1,
        nameOpt = "Wayfarer's Satchel", profession = 'Crafting',
        craftingCategory = 'Travel Packs', skill = 'armorer', level = 10,
        craftingTime = 5,
        craftingEvent = 'WayfarerPacksCraft',
        ingredients = {{id = 'Any leather', count = 3}},
    },
    {
        id = '!wfp_backpack', types = 'Miscellaneous', count = 1,
        nameOpt = "Wayfarer's Backpack", profession = 'Crafting',
        craftingCategory = 'Travel Packs', skill = 'armorer', level = 25,
        craftingTime = 8,
        craftingEvent = 'WayfarerPacksCraft',
        ingredients = {{id = 'Any leather', count = 6}},
    },
    {
        id = '!wfp_expedition', types = 'Miscellaneous', count = 1,
        nameOpt = 'Expedition Pack', profession = 'Crafting',
        craftingCategory = 'Travel Packs', skill = 'armorer', level = 40,
        craftingTime = 12,
        craftingEvent = 'WayfarerPacksCraft',
        ingredients = {{id = 'Any leather', count = 10}},
    },
}
