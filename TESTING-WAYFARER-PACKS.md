# Wayfarer Packs Test Environment

Double-click `Test-Wayfarer-Packs.cmd` in this directory to start a fresh test game.
Each launch skips character generation and starts inside Arrille's Tradehouse with:

- 5,000 gold to buy all three packs from Arrille.
- A common shirt, pants, and shoes equipped, with third-person view enabled.
- The current workspace version of Wayfarer Packs, not the installed ZIP.
- Your installed Inventory Extender, for tooltip and equipped-border testing.
- Your installed Crafting Framework, with three Travel Packs recipes.
- 48 netch leather, three diamonds, and a repair
  hammer. Armorer starts at 60 in this test character only.

No packs are granted directly: use Arrille's Barter dialogue to buy them.
Drag a purchased bag onto your character to equip; repeat to unequip.
Check the front and side while standing, walking, and playing idle animations.
Swap all three packs and verify Feather 25, 50, and 75 in active effects.
Dropping or selling the worn pack should remove its Feather bonus.

## Isolation

Only the base game, Inventory Extender, Crafting Framework, Wayfarer Packs, and
test scripts are loaded. Simply Crafting is a separate recipe collection, not
needed to load the backpack recipes, and is not included.
This is not the complete POTI setup: body replacers, clothing replacements,
animation mods, and Sun's Dusk are deliberately excluded. Final fit still needs
checking in your actual modlist. Inventory Extender files are read in place, not
copied or modified. The test fixture is not included in the release ZIP.

Configuration/logs: `.runtime/wayfarer-packs-manual-profile`.
Saves/screenshots: `.runtime/wayfarer-packs-manual-user-data`.
Video settings persist between launches; each launcher run creates a fresh game.
You can load a saved test session using the game's menu. Loading it does not
grant another 5,000 gold. POTI configuration and existing saves are untouched.
After changing mod assets/scripts, close the test game and run the launcher again.

## Crafting

Open inventory and click the framework's hammer button. Alternatively, hold Shift
while using the repair hammer. Select Crafting and find the Travel Packs category
(or search the pack name). Select a recipe and craft one pack; materials should be
consumed and the resulting pack should equip like one purchased from Arrille.
There is enough leather to craft all three. Recipes do not consume clothing;
your equipped shirt and pants should remain unchanged, including after Craft All.
Enable the diamond button to craft Artisan's packs instead: one extra diamond,
double crafting time, and quality-scaled Feather. Disable it for normal 25/50/75 packs.
At governing skill 100, Artisan Feather is 38/71/101. The manual character starts
at Armorer 60; the automated Artisan regression sets it to 100 for that check.
The 48 leather is enough for one set of each; Artisan packs are not sold by Arrille.

## Launch Options

```powershell
# Prepare configuration without launching a window.
.\tools\start-wayfarer-test.ps1 -PrepareOnly

# Test the standard inventory without Inventory Extender.
.\tools\start-wayfarer-test.ps1 -VanillaInventory

# Confirm the mod works without either optional integration.
.\tools\start-wayfarer-test.ps1 -VanillaInventory -NoCrafting

# Verify the manual environment automatically, then exit.
.\tools\start-wayfarer-test.ps1 -SmokeTest
```

Use `-Engine`, `-GameData`, `-InventoryExtender`, or `-CraftingFramework` to override installation paths.
The launcher targets the tested OpenMW 0.52 build in `C:\Modlists\POTI\.OpenMW`.
The separate smoke profile is under `.runtime/wayfarer-packs-smoke-*`.
It checks spawn cell, gold, clothing, camera, all three bags in Arrille's stock,
and the Wayfarer Packs interface. With Crafting Framework enabled it also opens
the real GUI, queues each parsed recipe through the framework's crafting code,
checks all three original-ID outputs, and verifies material consumption. It does
an additional Craft All batch and verifies multiple backpacks and its material
consumption. Inventory-name regression tests preserve visible stack counts. It does
not automate mouse clicks, the barter UI, or judge fit.
Both launch modes passed this check with the installed OpenMW 0.52 build; the
Inventory Extender run also confirms its interface is available.
