# Local Vanilla Reference

`public/assets/vanilla-fit.json` contains locally extracted Bethesda torso geometry.
It is for this private preview only, not a redistributable mod asset. Do not publish
this reference or a website build containing it. The mod builder excludes it from
the release ZIP. The preview disables the fit reference if the file is absent.

The exporter uses [PyFFI](https://github.com/niftools/pyffi) 2.2.3 to read Morrowind
NIFs. It applies each chest vertex's skin bind transform and corresponding
base_anim bone transform, then the inverse Spine1 transform. The result is in the
same attachment coordinate system as the worn backpacks. The reference is the
vanilla Dunmer male torso in base_anim's rest pose, not an animated whole character.

To regenerate from a licensed local installation, use OpenMW's bsatool to extract
`meshes/base_anim.nif` and `meshes/b/b_n_dark elf_m_skins.nif` from Morrowind.bsa
into `.runtime/vanilla-fit` in the workspace (without preserving subdirectories).
Install PyFFI 2.2.3 into `.runtime/asset-tools`, then run:

```powershell
python -m pip install --target .runtime/asset-tools PyFFI==2.2.3
python tools/export_wayfarer_fit.py
python tools/build_wayfarer_packs.py
```

The exporter also writes `tools/wayfarer_body_fit.json`: a small numeric set of
measured strap control points, not a copy of the body mesh. The model builder uses
these routes for all three packs. It does not need PyFFI or game archives at build
time once the measurements exist. The game mod contains only our original meshes.
