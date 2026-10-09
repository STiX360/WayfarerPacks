# Wayfarer Packs Model Studio

Local Three.js art-review viewer. Its generated vertex positions, normals, UVs,
colors, and albedo bitmap are exported by the same build as the OpenMW models.
Browser lighting is not OpenMW lighting; this preview is for shape and material
review, not a substitute for final in-game clipping/lighting checks. Fit reference
is an approximate torso, not a Morrowind skeleton or body replacer.

From this directory: `npm install`, then `npm run dev`. Vite displays the local
URL; it binds only to localhost. `npm run build` produces the static website in
`dist`. No external CDN, game installation, or player save is needed for viewing.

Rebuild meshes and preview assets from the workspace root with
`python tools/build_wayfarer_packs.py`, then refresh the browser.

The screenshot button saves the current view as a PNG. Surface/lighting/reference
controls are inspection settings, not changes to mod balance or model exports.
