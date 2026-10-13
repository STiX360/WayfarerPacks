# 0.4.2 Model Loading Regression

Investigated on 2026-10-13 using OpenMW 0.52.0, revision 73765c58a2.
The test profile loaded only the vanilla masters, engine resources, the extracted
release archive, and developer equipment fixtures. No workspace mod data or
existing modlist configuration was loaded.

## Published Archive Evidence

Downloaded the GitHub v0.4.2 release archive, not a local rebuild:

- ZIP SHA-256: `15443ac29b722b4319f7156287b33688833ce9b47f32d221e9b0f3adc4b7baec`.
- The Nexus 0.4.2 file's public virus-scan link reports the same archive SHA-256.
  A separate authenticated Nexus download was not performed.
- Both downloaded 0.4.1 and 0.4.2 archives contain the identical leather PNG:
  `2486c7cbd10aaef4ac5210b24ae85941e83b4f6825488632d3464e2b37f51bd4`.
- All six meshes differ between those releases only in the generator header.

## Cause and Controlled Test

0.4.2 changed `#Generator WayfarerPacks 0.4.1` to
`#Generator WayfarerPacks`. This is a parsed header, not an ordinary comment.
OpenSceneGraph reads both a generator name and version; without the version it
consumes the following `osg::Geode` token and begins reading the object incorrectly.
See the [OpenSceneGraph 3.6.5 reader](https://github.com/openscenegraph/OpenSceneGraph/blob/OpenSceneGraph-3.6.5/src/osgDB/InputStream.cpp#L959-L961).

The unchanged published 0.4.2 archive produced `Unmatched property 1, expecting
UniqueID`, `Unsupported wrapper class {`, and load failures for all six models.
Equipment/Feather assertions still passed, demonstrating that script success
alone does not establish asset correctness.

Changing only the missing generator-version token in a copy of that downloaded
archive removed all pack-model load errors. OpenMW then loaded the leather PNG.
The 0.4.3 fix uses `#Generator WayfarerPacks 1`, keeping the generator format
version independent of the mod release version.

## Corrected Archive Validation

The rebuilt 0.4.3 ZIP was extracted into its own test directory and passed native
equip/switch/unequip, Feather 25/50/75, and lost-item cleanup assertions without
pack-model resource errors. The third-person worn model was also observed in the
engine. All 54 automated tests and release archive verification passed.

This reproduces a model-loading regression; the commenters' exact `No bound
texture` observation was not independently reproduced. OpenMW 0.51, save/reload,
optional integrations, detailed visual fit, and a future published 0.4.3 download
remain separate acceptance checks. Local logs and downloaded archives are in
`D:/Projects/Morrowind/reports/wayfarer-release-investigation` and are not packaged.
