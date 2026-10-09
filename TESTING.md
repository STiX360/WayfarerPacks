# Release Testing

## Local Preparation Evidence (2026-10-10)

- Production build passed in the migrated repository with its own Python environment.
- All 46 tests passed: 30 existing mod/asset tests and 16 release tests.
- ZIP verification and CRC checks passed for all 20 allowlisted production files.
- Repackaging produced an identical ZIP (stable timestamps, permissions, and ordering).
- No test fixtures, profiles, developer tools, extracted game assets, or saves are packaged.
- All three GitHub workflow YAML files parsed successfully. Hosted jobs and actual
  provider uploads have not been run; GitHub release interactions were mocked.
- Gameplay scripts, plugin, meshes, icons, balance data, and texture remain byte-identical
  to the original Morrowind workspace. No engine or browser session was launched
  for these build/release-only changes.

Production ZIP SHA-256:
`1e391e841b84805806488554624f597d0740fe88ff5bdeca46c13205869cd564`.

## Automated Local Checks

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_wayfarer_packs.py
python -m unittest discover -s tests -v
python tools/release.py verify
```

Build first: geometry/preview/distribution tests inspect generated output.
Lupa Lua 5.1 tests cover mocked equipment lifecycle, optional integrations,
nonstacking, quality scaling, and save handlers. Release tests cover deterministic
archives, allowlists, hashes, content declarations, unsafe paths, version tags,
release notes, and mocked GitHub/Nexus boundaries. No publishing calls are made.

These tests do not prove real-engine timing, disk save compatibility, visual fit,
or balance. CI runs this suite on Windows and Linux without game data. Optional
browser preview checks are documented in `README.md`; they are separate from mod
package verification.

## Engine and Manual Acceptance

Existing engine smoke and crafting evidence is retained in
`reports/wayfarer-packs-validation.md`. The isolated launcher and fixture remain
unchanged; see `TESTING-WAYFARER-PACKS.md`. Preparing a profile is not a gameplay
pass. No game needs to launch merely to adopt the release workflow.

Pending checks before publication:

- Actual disk save/reload of generated Artisan packs, including equipment recovery.
- Fit and clipping across races, armor, body replacers, and idle animations.
- Mouse-driven crafting/barter and Inventory Extender behavior in the target modlist.
- Balance and compatibility with other wearable packs; independent bonuses can stack.
- Minimum advertised OpenMW 0.51 acceptance; recorded engine checks used 0.52.
- Owner's licensing and release-status decisions.

Run the existing engine and manual fixtures when gameplay/assets change. Keep test
scripts, gold grants, local profiles, game data, and player saves out of production.
