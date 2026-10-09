# Publishing Wayfarer Packs

## Current Release Choices

- Current version is 0.4.2; its filename is `WayfarerPacks-0.4.2.zip`.
- Preserve root-relative install paths and the `Wayfarer Packs/` source directory.
- `release/config.json` uses `prerelease: false` for stable releases.
- Publishing is disabled unless the repository variable `RELEASES_ENABLED=true`.
- Nexus is separately disabled unless `NEXUSMODS_ENABLED=true`. Once enabled,
  tagged releases upload after GitHub publishing succeeds; there is no mode variable.
- No license has been selected. Choose licensing before public distribution;
  retain `TEXTURE_SOURCE.md` and do not redistribute extracted Bethesda assets.

## Local Preparation

Use Python 3.12 or newer from the repository root:

```powershell
python -m pip install -r requirements-dev.txt
python tools/build_wayfarer_packs.py
python -m unittest discover -s tests -v
python tools/release.py verify
```

The existing builder generates records, meshes, icons, catalog, and preview data,
then calls the bundled deterministic packager. Packaging only:

```powershell
python tools/release.py package
python tools/release.py verify
```

Packaging alone does not regenerate stale assets. Always run the builder after
changing balance data or geometry. The canonical artifacts are the ZIP, companion
`.manifest.json` with per-file SHA-256 hashes, and `.zip.sha256` hashing both.
All live mod files are explicitly mapped in `release/config.json`; add new runtime
files there. Developer fixtures, reports, profiles, tools, and dependencies are
not shipped. The original mod README, pack balance data, and texture provenance
remain included, matching the existing distribution convention.

Before release, update `VERSION`, the mod README heading, and exactly one matching
`## X.Y.Z` section in `CHANGELOG.md`. Tests enforce matching version metadata.
The generated plugin and preview read `VERSION`; no runtime IDs are renamed.

## GitHub

`validate.yml` builds and tests on Windows and Linux. `release.yml` accepts version
tags and manual dispatch on `main`. Manual release dispatch is build-only.
Tagged builds require `vVERSION` and source reachable from `origin/main`.
Once publishing has explicitly been enabled, a tag creates a GitHub release using
the previously verified CI artifact, not a rebuild. Existing assets must match
exactly; retries cannot silently overwrite conflicting files or release status.

Do not push a version tag until publication is authorized. Review licensing,
release notes, prerelease choice, and the pending acceptance checks in `TESTING.md`
first. This preparation does not configure repository variables, create releases,
push commits/tags, or contact Nexus.

## Optional Nexus

Create this mod's Nexus page and first file manually. Set the `nexus` GitHub
environment's secret `NEXUSMODS_API_KEY` and variables `NEXUSMODS_FILE_ID` and
`NEXUSMODS_MOD_ID` (API Unique Mod ID, not the page number). Never reuse another
project's identifiers or credentials. Set the repository variables described above
only when ready. Optional environment reviewers can guard actual uploads.

- To upload an existing release, dispatch `nexus.yml` from `main` with the release tag matching
  this checkout's `VERSION`. It downloads and verifies the GitHub ZIP and companions
  without rebuilding. For an older version, use the matching version of the
  workflow/config on the main branch; arbitrary mismatched tags are rejected.
- After a successful tagged GitHub release, the Nexus job in
  `release.yml` uploads the same verified CI archive.

Uploads do not archive previous Nexus files or change the primary download.
Record the returned Nexus version ID. An ambiguous upload failure may already
have created a version: inspect Nexus before retrying. Prefer retrying only failed
jobs while the retained CI artifacts are still available (14 days).

Keep local Nexus BBCode drafts in the Git-ignored `.publishing/` directory.
