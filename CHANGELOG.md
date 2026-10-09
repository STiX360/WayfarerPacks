# Changelog

## 0.4.2

- Add Arrille's "travel packs" topic recommending the Satchel and Backpack,
  without replacing existing greetings, NPC records, or dialogue responses.
- Sell normal packs through 45 vanilla torch sellers from UESP's Trader/Pawnbroker
  list, plus Arrille as an explicit exception (46 merchants total).
- Assign one or two distinct pack types using fixed wiki-listed merchant gold:
  under 500 gets a Satchel; 500-999 gets a Satchel and Backpack; 1,000+ gets
  a Backpack and Expedition Pack. No live-gold checks or Artisan stock.
- Retain runtime-only inventory additions without overriding NPC records.
- Replenish missing assigned types without duplicating stock or deleting existing items.
- Configure releases as stable rather than prerelease.

## 0.4.1

- Add three wearable packs with Feather 25/50/75, available from Arrille.
- Keep one pack equipped at a time without using clothing or armor slots.
- Keep duplicate packs as separate inventory items, including Craft All outputs.
- Add optional Crafting Framework leather/hide recipes and Inventory Extender integration.
- Scale new Artisan's Touch packs with crafting quality, frozen when crafted.
  At governing skill 100, their Feather effects are 38/71/101.
- Retain existing item IDs, saved equipment state, and legacy Artisan templates.
- Include original rounded models, leather texture, icons, and a separate developer preview.
- Add deterministic production packaging, per-file hashes, and guarded release workflows.

This is the initial public release; the entries summarize the current
mod rather than claiming all features were first introduced in 0.4.1.
Generated-item disk save/reload and broader race/armor/animation fit checks remain pending.
