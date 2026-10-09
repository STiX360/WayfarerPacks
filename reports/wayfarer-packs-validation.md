# Wayfarer Packs 0.4.1 Validation

Version 0.4.1 freezes rounded base Feather times CF quality in generated item and
ability records. A cache reuses records with the same template/magnitude; global
and player script saves preserve the registry without requiring CF for equipment.
The real engine crafts at Armorer 100 and verifies Feather 38/71/101. Thirty tests
cover rounding (including floating-point half ties), above-100% scaling, cache
reuse, save-handler recovery, and item removal. Actual disk save/reload of generated
packs remains a manual check.

Version 0.4.0 adds three standalone Artisan item/ability records sharing the
normal models. Optional crafting hooks extend the existing diamond toggle while
preserving its prior gate. The real-engine test crafts all three Artisan packs,
consumes 19 leather and three diamonds, verifies doubled recipe times and
quality-scaled Feather while switching packs, then checks normal output after toggle-off.
Normal crafting, Craft All, distinct-copy behavior, and clothing preservation pass.

Version 0.3.4 uses leather-only recipes (3/6/10 units). The manual fixture grants
no spare clothes and verifies crafting leaves the equipped shirt and pants intact.

Version 0.3.3 prevents duplicate backpacks merging by assigning an inert legacy
item script. Existing stacks are split into single-copy references without
replacing the selected reference. The real-engine Craft All check also verifies
distinct copies, one-copy equip, Feather 50, and toggling without losing copies.

- 30 tests pass using Python 3.12 and the workspace's Lua 5.1 runtime.
- The plugin contains six MISC records, six SPEL abilities, and one inert SCPT.
- The abilities contain self-range Feather 25/50/75 and Artisan 35/65/95.
- The distribution archive includes both content files and all referenced assets.
- An isolated OpenMW 0.52.0 run (revision 73765c58a2) passes the real-engine smoke
  test: equip each bag through UseItem, switch between them, verify active Feather,
  toggle off, equip again, and remove the selected item without leaving a bonus.
- That run loads the generated world and worn meshes without model/script errors.

The engine test starts a disposable game in Arrille's Tradehouse. Its config,
logs, cache, and user data live inside the workspace; it does not alter POTI's
configuration or player saves. Full engine output: `wayfarer-engine-check/result.txt`.

The manual fixture with the installed Crafting Framework opens the real GUI and
queues the three parsed Travel Packs recipes through the framework's existing
crafting function (via its test-facing getGlobals API). All three original record
IDs are produced; 19 leather is consumed and clothing counts are unchanged.
No cheat mode or direct output spawning is used. Mouse-driven
recipe selection remains a manual check. The recipe data has no script manifest
entry or ESP master dependency on Crafting Framework.

The Craft All regression runs the GUI's maximum-count calculation and
queue path for a backpack batch. Four additional backpacks are produced (five
total), consuming 24 leather and no clothing. The stack-count display regression
checks single, multiple, formatted, repeated-cleanup, and non-string labels.
Name cleanup now strips only the Feather suffix rather than replacing the whole
rendered inventory label. The previous implementation hid stack-count suffixes.

Save/load, invalid objects, duplicate bags, camera changes, unrelated Feather
preservation, forged use events, and merchant testing-stock replenishment have mocked Lua
coverage. Save/load is not yet checked in a real player save.
Merchant coverage includes ignoring the old supplied flag, topping up only missing
bags, leaving unrelated merchants alone, and avoiding duplicate stock.

Inventory Extender equipped overrides, clean name cells, and descriptive purple
effect tooltips have mocked coverage,
including late interface availability, duplicate copies, unrelated items, and
refresh after switching/removing the selected pack. Actual modlist UI behavior
remains an in-game acceptance check. Meshes now contain explicit materials with
AMBIENT_AND_DIFFUSE vertex-color tracking; visible lighting/color needs rechecking.

The worn-only orientation correction rotates the centered bag +90 degrees about
Y, mapping its height onto Spine1's X axis. In 0.2.6 the rearward offset is six
units plus half the pack depth, with the pack raised five units. Regression coverage checks the axis mapping, normal orientation, and
generated world/worn meshes for all three bags. The correction is based on the
user's screenshot; upright placement and clipping still require visual acceptance.

Visual inspection of attachment orientation and scale, paper-doll visibility,
lighting, world collision, human/beast races, and body/clothing replacer clipping
remains outstanding. Assets are original procedural models with generated leather
albedo, not imported meshes from other mods. The browser preview shares the export's
positions, normals, colors, UVs, and exact texture bytes, with regression coverage
checking parity and UV preservation through the worn transform.

In 0.3.1 `tools/export_wayfarer_fit.py` reads locally extracted vanilla Dunmer
male skin geometry and base_anim using PyFFI 2.2.3, computes weighted bone-space
positions relative to Spine1, and exports a local-only torso reference. Its bounds
are X -13.48..25.75 (height), Y -7.05..9.39 (depth), Z -13.01..12.97 (width).
The sampled strap routes in `tools/wayfarer_body_fit.json` replace the guessed
shoulder envelope. Tests compare front-route samples against the actual reference
triangle surface, limit the curve peak below 23 units, and exclude the extracted
geometry from the mod archive. This is a base_anim rest-pose reference, not proof
of fit for every animated pose or race.

The Three.js preview passes Playwright canvas-pixel checks on desktop/mobile,
orbit dragging, turntable animation, three variant selections, surface modes,
lighting presets, and no mobile horizontal overflow or page errors. Screenshots:
`pack-preview-desktop.png`, `pack-preview-mobile.png`, `pack-preview-back.png`.
Side and harness-reference views: `pack-preview-side.png`, `pack-preview-harness.png`.
Additional geometry checks cover flap clearance from the actual body triangles,
strap weaving across buckle-bar depth, shoulder span, and both harness anchors
embedded in the bag surface. These are geometric checks, not proof of fit against
the player's skeleton. The harness remains rigid and needs in-game acceptance.
The 0.2.3 tie-down clipping regression checks the interior and edge samples of
every strap triangle against the combined body/flap/pocket surface. It fails on
0.2.2 and passes after dense subdivision and inner-face clearance correction.
In 0.2.4 this clearance applies only to the buckle weave. Straight sewn sections
reuse clipped support triangles and have embedded rear faces. Their additional
contact regression requires the outer face to be exactly one leather thickness
from the actual support at interior/edge samples, checking for air gaps as well
as clipping. Browser side close-ups are captured for each of the three variants.
The production website build succeeds. Vite 6.4.4 dependency audit reports no
known vulnerabilities at build time. Preview lighting is not engine lighting.

The earlier headless BulletObjectTool attempts could parse the current meshes but
could not complete because that tool did not initialize shader defines in this
engine build. The successful game-engine test supersedes those attempts.
