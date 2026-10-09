"""Export a local-only vanilla torso reference in Spine1 attachment coordinates."""
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.runtime/asset-tools'))
time.clock = time.perf_counter
from pyffi.formats.nif import NifFormat
from pyffi.object_models.common import UShort

# PyFFI's duplicate XML fields allocate a byte for old NIF UV counts.
original_read = NifFormat.NiTriShapeData.read
def read_morrowind_shape(self, stream, data):
    if data.version == 0x04000002:
        self._num_uv_sets_value_ = UShort()
    original_read(self, stream, data)
NifFormat.NiTriShapeData.read = read_morrowind_shape

def read(name):
    data = NifFormat.Data()
    with (ROOT / '.runtime/vanilla-fit' / name).open('rb') as stream:
        data.read(stream)
    return data.roots[0]

base = read('base_anim.nif')
bones = {node.name: node for node in base.tree() if isinstance(node, NifFormat.NiNode)}
inverse = bones[b'Bip01 Spine1'].get_transform(base).get_inverse()
skin = read('b_n_dark elf_m_skins.nif')
positions = []
for shape in skin.tree():
    if not isinstance(shape, NifFormat.NiTriBasedGeom) or shape.name != b'Tri Chest':
        continue
    instance = shape.skin_instance
    verts = [[0., 0., 0.] for _ in shape.data.vertices]
    for bone, bind in zip(instance.bones, instance.data.bone_list):
        transform = bind.get_transform() * bones[bone.name].get_transform(base) * inverse
        for weight in bind.vertex_weights:
            point = shape.data.vertices[weight.index] * transform
            for k, axis in enumerate(('x', 'y', 'z')):
                verts[weight.index][k] += getattr(point, axis) * weight.weight
    for tri in shape.data.get_triangles():
        positions.extend(verts[i] for i in tri)
if not positions:
    raise RuntimeError('No chest geometry found')
bounds = [[min(p[k] for p in positions), max(p[k] for p in positions)] for k in range(3)]
output = ROOT / 'pack-preview/public/assets/vanilla-fit.json'
output.write_text(json.dumps({'source': 'Local Morrowind.bsa: Dunmer male chest / base_anim.nif',
    'coordinates': 'Spine1 local; X up, Y forward, Z left',
    'positions': positions, 'bounds': bounds}, separators=(',', ':')))
print('Spine1 torso bounds:', bounds)
print('Local-only reference:', output)

sys.path.insert(0, str(ROOT / 'tools'))
from build_wayfarer_packs import surface_y
standard = [(-p[2], p[1], p[0]) for p in positions]
triangles = [(*standard[i:i+3], (1, 1, 1)) for i in range(0, len(standard), 3)]
routes = []
for sign in (-1, 1):
    route = []
    for height in (20, 21):
        x = sign*7.5
        route.append([x, surface_y(triangles, x, height, True)-.1, height])
    x, height = sign*7.5, 22
    route.append([x, (surface_y(triangles, x, height, True)+
                      surface_y(triangles, x, height, False))/2, height+.1])
    for height in (21, 19, 17, 14, 10, 6, 2, -2):
        x = sign*(7.5 if height >= 10 else 6)
        route.append([x, surface_y(triangles, x, height, False)+.1, height])
    routes.append(route)
fit_file = ROOT / 'tools/wayfarer_body_fit.json'
fit_file.write_text(json.dumps({'source': 'Vanilla Dunmer male torso, base_anim rest pose',
    'routes': routes}, indent=2)+'\n')
print('Measured strap routes:', fit_file)
