# Testing

This is the single guide for the local tester, automated checks, and release
acceptance. Test fixtures and developer documentation are not included in the
production ZIP.

## Launch the Tester

Double-click `Test-Wayfarer-Packs.cmd` in the repository root. Each launch starts
a fresh game in Arrille's Tradehouse with:

- 5,000 gold, a common shirt, pants, and shoes, and third-person view.
- The current workspace mod, rather than an installed release ZIP.
- Installed Inventory Extender and Crafting Framework integrations.
- 48 netch leather, three diamonds, a repair hammer, and Armorer 60.

Buy the Satchel and Backpack from Arrille; no packs are granted directly.
Craft the Expedition Pack or use `player->AddItem "wfp_expedition" 1`.
Talk to Arrille and check the `travel packs` topic and its recommendations.

The launcher defaults to OpenMW 0.52 in `C:\Modlists\POTI\.OpenMW` and a licensed
Morrowind installation in `D:\Steam\steamapps\common\Morrowind\Data Files`.
Use `-Engine` (the executable path), `-GameData`, `-InventoryExtender`, and
`-CraftingFramework` to override installation paths.

```powershell
# Prepare the isolated configuration without launching.
.\tools\start-wayfarer-test.ps1 -PrepareOnly

# Test without Inventory Extender.
.\tools\start-wayfarer-test.ps1 -VanillaInventory

# Test without either optional integration.
.\tools\start-wayfarer-test.ps1 -VanillaInventory -NoCrafting

# Run the automated environment/crafting smoke and exit.
.\tools\start-wayfarer-test.ps1 -SmokeTest
```

## Isolation and Files

Only the base game, the enabled optional integrations, Wayfarer Packs, and test
scripts are loaded. Simply Crafting is a separate recipe collection and is not
needed. This is not the full POTI setup: body/clothing replacers, animation mods,
and Sun's Dusk are excluded. Integration files are read in place, not modified.
POTI configuration and existing saves are untouched.

- Configuration/logs: `.runtime/wayfarer-packs-manual-profile`.
- Saves/screenshots: `.runtime/wayfarer-packs-manual-user-data`.
- Automated fixture profiles: `.runtime/wayfarer-packs-smoke-*`.

Video settings persist. Each launcher run creates a fresh game; saved test
sessions can be loaded through the game menu without another gold grant.
Close the game and relaunch after changing scripts or assets.

## Manual Checks

Drag a purchased bag onto the character to equip, then repeat to unequip.
Swap all three packs and verify Feather 25/50/75. Dropping or selling the worn
copy should remove its bonus; owning more copies must not multiply the effect.
Check front/side fit while standing, walking, and playing idle animations.

Open the inventory's framework hammer button, or hold Shift while using the
repair hammer. Find Travel Packs, craft one pack, and verify material consumption
and equipping. Craft All must produce multiple distinct copies without consuming
equipped clothing. The supplied leather allows one normal and one Artisan set.

Enable the diamond button for Artisan's Touch: one extra diamond, double crafting
time, and quality-scaled Feather. Disable it for normal 25/50/75 packs. At
governing skill 100, Artisan Feather is 38/71/101; the manual character starts
at Armorer 60. Artisan packs are not sold by Arrille.

## Automated Checks

Use Python 3.12 or newer. Build before testing: asset/distribution tests inspect
generated output.

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_wayfarer_packs.py
python -m unittest discover -s tests -v
python tools/release.py verify
```

Lupa Lua 5.1 tests cover mocked equipment lifecycle, integrations, nonstacking,
quality scaling, merchant stock, and save handlers. Release tests cover allowlists,
hashes, deterministic archives, unsafe paths, version tags, notes, and mocked
provider boundaries. CI runs these without game data; no publishing calls occur.
Browser preview checks are documented separately in `README.md`.

The `-SmokeTest` launcher verifies spawn, gold, clothing, camera, Arrille's stock,
and the mod interface. With Crafting Framework it opens the real GUI, queues
parsed recipes through framework code, checks outputs/material consumption,
and runs a Craft All batch. It does not automate mouse clicks or judge fit.

For the smaller native equipment/dialogue smoke:

```powershell
python tools/verify_wayfarer_models.py --engine-root 'C:\Modlists\POTI\.OpenMW' --game-data 'D:\Steam\steamapps\common\Morrowind\Data Files'
```

Its output is under `reports/wayfarer-engine-check`. Earlier engine/crafting
evidence is retained in `reports/wayfarer-packs-validation.md`.

## Current Validation: 0.4.2 (2026-10-10)

- All 52 automated tests passed after the trader-document packaging cleanup.
- The 21-file production ZIP passed verification and byte-identical repeat packaging.
- OpenMW 0.52 environment/crafting smoke passed Arrille's Satchel/Backpack-only
  stock, normal crafting, Craft All, distinct-copy equipping, and Artisan 38/71/101.
- A subsequent native smoke loaded the `travel packs` topic and Arrille-only
  response, then passed equipment switching, Feather, toggle, and lost-item cleanup.
- Engine tests preceded the final documentation/header-only cleanup; they were
  not rerun for those non-gameplay changes.

Production ZIP SHA-256:
`be6749602eade489a466b8fce56ab0c6718ea171c86ddadfb9055fd79ebf37cc`.

Merchant provenance and the full assignment table are in `docs/TRADERS.md`.
Eligibility is a fixed snapshot of 45 torch-selling traders plus Arrille, using
UESP revision 3126622 for gold. Existing extra stock is preserved.

Historical 0.4.1 packaging preparation passed 46 tests and verified a 20-file ZIP;
that evidence is not the current release result. Its three workflow YAML files
parsed locally; mocked uploads did not prove live provider publication.

## Remaining Acceptance

Automated tests do not prove native timing, visual fit, real disk saves, or balance.
These checks remain manual:

- Generated Artisan packs: disk save/reload and equipment recovery.
- Fit across races, armor, body replacers, and idle animations in the target modlist.
- Mouse-driven crafting/barter and Inventory Extender behavior.
- Arrille's dialogue-menu visibility and topic registration in existing saves.
- Barter across eligible merchants and existing-save stock migration.
- Compatibility/balance with other wearable packs; independent bonuses can stack.
- Minimum advertised OpenMW 0.51 acceptance; recorded engine checks used 0.52.
- Owner's licensing decision before publication.

Run engine/manual checks when gameplay or assets change. Preparing a profile is
not a gameplay pass. Keep fixtures, gold grants, profiles, game data, and saves
out of production.
