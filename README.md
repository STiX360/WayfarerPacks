# Wayfarer Packs

An OpenMW mod adding wearable backpacks and satchels with Feather bonuses,
optional crafting, and quality-scaled upgrades.

## In Game

- Three normal packs: Feather 25, 50, and 75, available from Arrille.
- One worn pack at a time; duplicates remain separate inventory items.
- Optional Crafting Framework recipes use leather/hides, not clothing.
- Artisan's Touch adds one diamond, doubles crafting time, and scales Feather
  with crafting quality. At governing skill 100: Feather 38, 71, and 101.
- Crafting Framework and Inventory Extender are optional, not hard dependencies.

See [installation and mod details](Wayfarer%20Packs/README.md) and
[the isolated test environment](TESTING-WAYFARER-PACKS.md).
Release preparation is documented in [PUBLISHING.md](PUBLISHING.md), with
separate acceptance evidence in [TESTING.md](TESTING.md).

## Development

Use Python 3.12 or newer. The build itself needs only the standard library;
Lua tests use Lupa's Lua 5.1 runtime.

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_wayfarer_packs.py
python -m unittest discover -s tests -v
python tools/release.py verify
```

The build produces `dist/WayfarerPacks-0.4.1.zip`, a per-file manifest, and SHA-256
checksums, and refreshes the mod's records, models, icons, catalog, and preview.
Tests cover equipment, crafting hooks, quality scaling, distribution, and guarded
release helpers. Real OpenMW checks
need a licensed local Morrowind installation; see the test-environment guide.

## Model Preview

After running the Python build:

```powershell
cd pack-preview
npm ci
npm run dev
```

Open the localhost URL printed by Vite. Use `npm run build` for a static build.
For optional browser tests, keep that server running in a second terminal:

```powershell
cd pack-preview
npx playwright install chromium
npm run test:preview
```

The extracted vanilla-body reference is deliberately excluded. The preview works
without it. See [local-only reference instructions](pack-preview/VANILLA-REFERENCE.md)
and [texture provenance](Wayfarer%20Packs/TEXTURE_SOURCE.md).

## Repository Scope

This repository contains Wayfarer Packs only. It does not redistribute OpenMW,
Morrowind files, POTI mods, downloaded tools, local saves, or runtime profiles.
Build outputs, dependencies, screenshots, and local references are ignored.
Existing files in the original Morrowind workspace are left untouched.

No license has been selected yet; choose one before the first public release.
