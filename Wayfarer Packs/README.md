# Wayfarer Packs 0.4.1

An OpenMW prototype with a script-managed backpack slot. Drag a bag from your
inventory onto your character to equip it. Repeat to unequip; another bag replaces
the current one. Clothing and armor slots remain available. Bags hold no inventory.

Requires OpenMW 0.51 or newer and Morrowind.esm. No other mods are required.

| Bag | Feather | Weight | Base Price | Net Weight Relief |
| --- | ---: | ---: | ---: | ---: |
| Wayfarer's Satchel | 25 | 2 | 100 | 23 |
| Wayfarer's Backpack | 50 | 4 | 300 | 46 |
| Expedition Pack | 75 | 6 | 650 | 69 |

Feather reduces encumbrance; it does not change Strength or the displayed maximum
capacity. Other Feather sources continue to work normally. The pack's own weight
still counts. Exactly one of this mod's abilities is applied while a bag is worn.
Selling, dropping, or otherwise losing the selected bag removes its bonus.

These are miscellaneous items, not conventional enchanted clothing. Their Feather
is an ability added while worn, visible in active effects; it has no charge meter.
With Inventory Extender's equipped-override API, the selected bag gets its equipped
border and sorting priority. Its name is shown without the fallback effect suffix,
with a separated, centered description and a purple Feather line in the tooltip.
Integration is automatic and optional. The standard inventory cannot highlight
these bags because they do not occupy an engine equipment slot. Item names retain
the Feather amount as a fallback without Inventory Extender.

## Optional Crafting

With OpenMW Crafting Framework enabled, these recipes appear under Crafting /
Travel Packs. The framework discovers `CF_recipes/wayfarerPacks.lua` automatically.
Load `CraftingFramework.omwscripts` before `WayfarerPacks.omwscripts`. Simply
Crafting, Skill Framework, and Sun's Dusk are not required. Without the framework,
this data file is unused: the packs still work and can be bought from Arrille.

| Pack | Armorer Level | Leather/Hides |
| --- | ---: | ---: |
| Satchel | 10 | 3 |
| Backpack | 25 | 6 |
| Expedition | 40 | 10 |

Leather uses the framework's built-in Any leather wildcard (including netch leather
and guar hides). Since 0.3.4, recipes use only leather/hides, not equipable clothing.
Each recipe produces one pack and consumes its materials, with no station
requirement. A repair tool can open the GUI; Inventory Extender also adds a hammer
button. Skill Framework users may see Crafting instead of Armorer if the
framework's skill replacement setting is enabled. Recipe levels are unchanged.
Original record IDs are preserved so crafted packs support the same equipment,
Feather, save/load, and inventory integration as purchased packs.

The framework's diamond button now enables Artisan's Touch for these recipes.
It adds one diamond and doubles crafting time, producing a distinct named pack:

Artisan Feather is now `round(base Feather * crafting quality)`, frozen when the
item is crafted. At governing skill 100 without other quality modifiers:

| Artisan Pack | Quality | Feather | Increase Over Base |
| --- | ---: | ---: | ---: |
| Artisan's Satchel | 150% | 38 | +13 |
| Artisan's Backpack | 142% | 71 | +21 |
| Artisan's Expedition Pack | 135% | 101 | +26 |

Weight and models are unchanged. Artisan packs occupy the same single-pack slot
and do not multiply Feather when carrying duplicates. They are crafted, not stocked
by Arrille. Turning the diamond toggle off restores the normal recipe output.
The integration preserves the existing Artisan eligibility gate for other items
and uses the framework's built-in diamond/time modifiers. Crafting Framework is
still optional. Generated item/ability records and their metadata are saved by
Wayfarer Packs, not the crafting framework. Later skill changes do not alter an
existing item's Feather. There is no gameplay quality cap; other modifiers and
fortified skill can produce stronger packs. Existing 0.4.0 packs retain their old
35/65/95 effects; the six static records remain as compatible templates.

Armorer is the vanilla crafting skill, so successful recipes award Armorer XP.
With Skill Framework and CF's skill-replacement setting, CF can use its separate
Crafting skill instead. Other attributes/skills do not directly enter the built-in
Artisan quality calculation.

## Installation

Extract the archive as a mod, add its folder as a data directory, and enable BOTH
content files (plugin first, scripts second). For manual configuration:

```ini
data="D:\Projects\Coding\WayfarerPacks\Wayfarer Packs"
content=WayfarerPacks.esp
content=WayfarerPacks.omwscripts
```

Arrille in Seyda Neen receives one of each bag on his next activation, including
in existing saves. For testing, any missing bag is replenished each time he loads;
existing stock is not duplicated. This also ignores earlier releases' one-time
stock flag. Leave the shop and return or reload your save to trigger activation.
No NPC records are replaced.
Console commands can supply the bags immediately:

```text
player->AddItem "wfp_satchel" 1
player->AddItem "wfp_backpack" 1
player->AddItem "wfp_expedition" 1
```

## Prototype Limitations

The included models are original procedural leather bags with rounded, uneven
bodies, curved flaps/straps, small tubular buckles, stitches, and an expedition
bedroll. A generated leather albedo texture is UV-mapped onto the meshes; vertex
colors tint each variant. Inventory icons are simplified geometry thumbnails.
An isolated
OpenMW 0.52 test loads the world and worn models and verifies equipping, switching,
exact Feather magnitudes, toggling off, and cleanup after item removal. Thirty
Lua lifecycle and distribution tests also pass, including save/load recovery.
Appearance in the paper doll, attachment orientation, collision behavior, and
clipping with different body replacers still need visual verification. Models attach to the standard
Spine1 bone, so no extra animation skeleton is needed. Satchels currently use the
same back attachment as backpacks. There is no
dedicated slot widget. Inventory Extender integration has mocked callback coverage;
its border, sorting, and tooltip still need checking in your installed modlist.

Worn meshes retain the 0.1.2 orientation correction. The 0.2.0 attachment is raised
5 units and moved 3 units closer to the body. Please recheck clipping in game.

The 0.2.2 flap and pocket follow the triangulated bag surface rather than guessed
offsets. Tie-down straps weave over buckle center bars. Shoulder loops extend from
embedded upper bag anchors, across an approximate shoulder/chest envelope, beneath
the arms, and back to lower anchors. This is a rigid Spine1 attachment, not skinned
clothing: body replacers, armor, and shoulder animations can still cause clipping.
It does not have cloth simulation or adapt automatically to character proportions.

In 0.2.3, tie-down straps are densely subdivided and project onto the combined
body/flap/pocket surface, with clearance for the inner leather face. A regression
test samples triangle interiors and edges, not just path anchors, to catch clipping.

In 0.2.4 the straight tie-down sections reuse clipped triangles from the flap/body
instead of a separate offset surface. The leather is 0.10 units thick, with its
back embedded 0.002 units into the support; there is no modeled air gap in these
sewn sections. Only the short buckle-threading section remains raised. Contact
tests check sampled face interiors and edges against the actual support planes.

In 0.2.5 the shoulder harness is narrower, lower, and seven units shallower at
the chest. Some overlap with clothing is intentional to reduce floating loops.
It remains rigid: folded arms and other idle poses will not deform the straps.

In 0.2.6 the worn pack moves another three units inward. The shoulder curve is
nine units higher and its chest reach is four units shorter than 0.2.5, avoiding
the nearly horizontal upper straps on the Expedition Pack. The browser fit
reference uses the exported attachment offsets. Clothing overlap remains an
intentional compromise; these straps are still rigid, not skinned or simulated.

In 0.3.1 the shoulder route is measured from the vanilla Dunmer male chest mesh
transformed into base_anim's Spine1 coordinates. It is narrower, follows the
chest surface, and peaks near 22 units above Spine1 instead of 28. The bag moves
one more unit inward. The local preview uses that actual torso mesh, not a
mannequin. Extracted game geometry is excluded from the mod ZIP. The reference
is a rest pose, not a simulation of animation, races, armor, or body replacers.

In 0.3.2 inventory name cleanup removes only the Feather suffix, preserving
Inventory Extender's stack-count suffix, including partially dragged stacks.
Since 0.3.3 each backpack is a separate inventory item. An inert legacy item script
prevents OpenMW from merging duplicates; Lua still handles equipping and Feather.
Existing stacks are separated automatically, retaining the original selected
reference as one copy. Craft All still produces the full number of backpacks.

To update from 0.1.x, replace that mod's files with this release and restart OpenMW.
Record IDs and saved equipment data are unchanged; existing bags remain usable.

Other mods manage their own backpack slots independently. In particular, Sun's
Dusk packs can be worn alongside these and their bonuses can stack. This version
does not modify Sun's Dusk or Bardcraft. NPC backpack equipping is not implemented.

Unequip before uninstalling, save, then disable both content files. To clear the
slot through the player Lua console, enter `luap`, then
`I.WayfarerPacks.unequip()`, exit the console, and save.

## Development

Balance data is in `packs.json`. Build records, catalog, original OSG meshes, TGA
icons, and the distribution archive from the workspace root:

```powershell
python tools/build_wayfarer_packs.py
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools/release.py verify
python tools/verify_wayfarer_models.py --engine-root 'C:\Modlists\POTI\.OpenMW' --game-data 'D:\Steam\steamapps\common\Morrowind\Data Files'
```

The build uses only the Python standard library. Script tests use Lupa's Lua 5.1
runtime from `requirements-dev.txt`; use Python 3.12 or newer. The engine smoke
test uses the installed OpenMW executable and vanilla game plus expansion data,
with isolated configuration and user-data paths in `reports/wayfarer-engine-check`.
It does not change the installed modlist or load a player save.
No assets or scripts from other mods are
redistributed. The archive contains data files at its root for mod-manager import.

## Browser Preview

The workspace's `pack-preview` website displays the same positions, smooth
normals, UVs, vertex colors, and leather bitmap used by the mod export. Rebuild
with the command above, then refresh the browser to see new assets. From
`pack-preview`, run `npm run dev` and open the localhost URL displayed by Vite.
It includes orbit/zoom, all three variants, automatic rotation, camera presets,
surface modes, lighting options, and snapshot download. The optional fit reference
is a rough torso, not an actual game body. Browser lighting is not OpenMW's renderer;
final lighting/clipping checks still need the game. Texture provenance and its
generation prompt are in `TEXTURE_SOURCE.md`.

## In-Game Acceptance Check

1. Buy or spawn each pack. Record encumbrance with and without it equipped.
2. Switch between packs; check the active effect magnitude is 25, 50, or 75.
3. Toggle the same pack off. Verify the bonus disappears.
4. Carry duplicates, equip one, drop the selected copy, and confirm the bonus disappears.
5. Sell/transfer the selected bag and check the same behavior.
6. Save while equipped, reload, and verify one bonus and one model.
7. Switch first/third person, change cells, and open inventory; inspect attachment.
8. Check human and beast races, robes, armor, and installed body replacers.
9. Cast Feather while wearing a bag, then remove the bag; the spell must remain.
10. With Inventory Extender, check equipped borders, sorting, and the effect tooltip.
