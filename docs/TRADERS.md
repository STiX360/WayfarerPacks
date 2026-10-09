# Trader Stock

Source: [https://en.uesp.net/wiki/Morrowind:Trader](https://en.uesp.net/wiki/Morrowind:Trader),
revision 3126622, retrieved 2026-10-10.

Includes 45 vanilla torch sellers from the 77 listed Traders and Pawnbrokers,
plus Arrille as an explicit exception (46 merchants total). NPC record IDs
were matched against the vanilla Morrowind master during development.
Torch sellers were identified from carryable Torch lights in NPC inventories,
owned stock containers, and owned display items, with Lights barter enabled.
This eligibility snapshot is fixed, not a live inventory or modlist scan.
Assignments are fixed at build time; gameplay never reads merchant gold.

- Under 500 gold: one Satchel (Feather 25).
- 500-999 gold: one Satchel and one Backpack (Feather 25/50).
- 1,000+ gold: one Backpack and one Expedition Pack (Feather 50/75).

Missing assigned stock replenishes when the NPC becomes active.
Only one copy of each assigned type is added. Existing extra items, including
player-sold packs or stock from older releases, are never deleted.
Artisan variants are crafting-only. Mod-added traders are not auto-enrolled.

| Trader | Record ID | Listed Gold | Packs |
| --- | --- | ---: | --- |
| Ababael Timsar-Dadisun | `ababael timsar-dadisun` | 9000 | Backpack, Expedition |
| Fonas Retheran | `fonas retheran` | 1300 | Backpack, Expedition |
| Lliros Tures | `lliros tures` | 1300 | Backpack, Expedition |
| Thongar | `thongar` | 1200 | Backpack, Expedition |
| Verick Gemain | `verick gemain` | 1100 | Backpack, Expedition |
| Vasesius Viciulus | `vasesius viciulus` | 1000 | Backpack, Expedition |
| Malpenix Blonia | `malpenix blonia` | 899 | Satchel, Backpack |
| Ancola | `ancola` | 800 | Satchel, Backpack |
| Arrille | `arrille` | 800 | Satchel, Backpack |
| Clagius Clanler | `clagius clanler` | 800 | Satchel, Backpack |
| Tiras Sadus | `tiras sadus` | 799 | Satchel, Backpack |
| Balen Andrano | `balen andrano` | 600 | Satchel, Backpack |
| Berwen | `berwen` | 600 | Satchel, Backpack |
| Galtis Guvron | `galtis guvron` | 600 | Satchel, Backpack |
| Lucretinaus Olcinius | `lucretinaus olcinius` | 600 | Satchel, Backpack |
| Daynes Redothril | `daynes redothril` | 500 | Satchel, Backpack |
| Elegal | `elegal` | 500 | Satchel, Backpack |
| Fadase Selvayn | `fadase selvayn` | 500 | Satchel, Backpack |
| Hjotra the Peacock | `hjotra the peacock` | 500 | Satchel, Backpack |
| Kaye | `kaye` | 500 | Satchel, Backpack |
| Goldyn Belaram | `goldyn belaram` | 450 | Satchel |
| Mebestian Ence | `mebestian ence` | 449 | Satchel |
| Ferele Athram | `ferele athram` | 400 | Satchel |
| Gadayn Andarys | `gadayn andarys` | 400 | Satchel |
| Meder Nulen | `meder nulen` | 400 | Satchel |
| Naspis Apinia | `naspis apinia` | 400 | Satchel |
| Ralds Oril | `ralds oril` | 400 | Satchel |
| Sedam Omalen | `sedam omalen` | 400 | Satchel |
| Shulki Ashunbabi | `shulki ashunbabi` | 400 | Satchel |
| Tervur Braven | `tervur braven` | 400 | Satchel |
| Urfing | `urfing` | 400 | Satchel |
| Landorume | `landorume` | 350 | Satchel |
| Mandur Omalen | `mandur omalen` | 350 | Satchel |
| Syloria Siruliulus | `syloria siruliulus` | 325 | Satchel |
| Allding | `allding` | 300 | Satchel |
| Both gro-Durug | `both gro-durug` | 300 | Satchel |
| Jeanne | `jeanne` | 300 | Satchel |
| Marasa Aren | `marasa aren` | 250 | Satchel |
| Sottilde | `sottilde` | 250 | Satchel |
| Trasteve | `trasteve` | 250 | Satchel |
| Alveno Andules | `alveno andules` | 200 | Satchel |
| Hinald | `hinald` | 150 | Satchel |
| Perien Aurelie | `perien aurelie` | 150 | Satchel |
| Rarvela Teran | `rarvela teran` | 150 | Satchel |
| Selvura Andrano | `selvura andrano` | 150 | Satchel |
| Baissa | `baissa` | 100 | Satchel |
