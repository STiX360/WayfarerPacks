"""Build standalone TES3 records and original prototype pack assets."""
from pathlib import Path
import json
import math
import struct
import zlib
import shutil

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'Wayfarer Packs'
VERSION = (ROOT / 'VERSION').read_text(encoding='ascii').strip()
WORN_BACK_OFFSET = 5
WORN_HEIGHT_OFFSET = 5
BODY_FIT = json.loads((ROOT / 'tools/wayfarer_body_fit.json').read_text())


def subrecord(tag, data):
    return tag.encode('ascii') + struct.pack('<I', len(data)) + data


def text_sub(tag, value):
    return subrecord(tag, value.encode('ascii') + b'\0')


def record(tag, *fields):
    body = b''.join(fields)
    return tag.encode('ascii') + struct.pack('<III', len(body), 0, 0) + body


def all_packs(packs):
    variants = []
    for pack, feather, name in zip(packs, (35, 65, 95),
            ("Artisan's Satchel", "Artisan's Backpack", "Artisan's Expedition Pack")):
        variants.append(dict(pack, id=pack['id']+'_artisan', name=name,
            feather=feather, value=pack['value']+200, modelId=pack['id'], craftingOnly=True))
    return packs + variants


def plugin(packs):
    records = []
    for pack in packs:
        pack_id = pack['id']
        model_id = pack.get('modelId', pack_id)
        records.append(record('MISC', text_sub('NAME', pack_id),
            text_sub('MODL', f'wayfarer_packs/{model_id}.osgt'),
            text_sub('FNAM', f"{pack['name']} (Feather {pack['feather']})"),
            subrecord('MCDT', struct.pack('<fii', pack['weight'], pack['value'], 0)),
            text_sub('SCRI', 'wfp_unique_item'),
            text_sub('ITEX', f'wayfarer_packs/{model_id}.tga')))
        records.append(record('SPEL', text_sub('NAME', pack_id + '_ability'),
            text_sub('FNAM', pack['name']),
            subrecord('SPDT', struct.pack('<iii', 1, 0, 0)),
            # TES3 Feather effect 8, no skill/attribute, self range, fixed magnitude.
            subrecord('ENAM', struct.pack('<hbbiiiii', 8, -1, -1, 0, 0, 0,
                                         pack['feather'], pack['feather']))))
    # Legacy-scripted items do not stack in OpenMW. Equipment remains Lua-managed.
    records.append(record('SCPT',
        subrecord('SCHD', struct.pack('<32s5I', b'wfp_unique_item', 0, 0, 0, 0, 0)),
        subrecord('SCDT', b''),
        text_sub('SCTX', 'begin wfp_unique_item\nend wfp_unique_item\n')))
    header = struct.pack('<fi32s256si', 1.3, 0, b'Wayfarer Packs',
                         f'Wayfarer Packs {VERSION} - script-managed backpacks.'.encode('ascii'), len(records))
    return record('TES3', subrecord('HEDR', header), text_sub('MAST', 'Morrowind.esm'),
                  subrecord('DATA', struct.pack('<Q', 0))) + b''.join(records)


def face(triangles, points, color):
    for i in range(1, len(points) - 1):
        triangles.append((points[0], points[i], points[i + 1], color))


def box(triangles, center, size, color):
    x, y, z = center
    a, b, c = (v / 2 for v in size)
    vertices = [(x-a, y-b, z-c), (x+a, y-b, z-c), (x+a, y+b, z-c),
                (x-a, y+b, z-c), (x-a, y-b, z+c), (x+a, y-b, z+c),
                (x+a, y+b, z+c), (x-a, y+b, z+c)]
    for indices in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                    (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        face(triangles, [vertices[i] for i in indices], color)


def surface_y(triangles, x, z, front=True):
    hits = []
    for a, b, c, _ in triangles:
        denominator = (b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(denominator) < 1e-9:
            continue
        u = ((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/denominator
        v = ((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/denominator
        if min(u, v, 1-u-v) >= -1e-7:
            hits.append(u*a[1]+v*b[1]+(1-u-v)*c[1])
    if not hits:
        raise ValueError(f'No bag surface at {x}, {z}')
    return min(hits) if front else max(hits)


def clipped_contact_strip(source, bounds, color):
    # Reuse the support's triangle planes, so leather cannot bridge over valleys
    # or cut through ridges. Only the front face is offset; the back is seated.
    x0, x1, z0, z1 = bounds
    result, outer = [], []
    for a, b, c, _ in source:
        if normal(a, b, c)[1] >= -.01:
            continue
        polygon = [a, b, c]
        for axis, limit, direction in ((0, x0, 1), (0, x1, -1), (2, z0, 1), (2, z1, -1)):
            clipped = []
            for p, q in zip(polygon, polygon[1:]+polygon[:1]):
                inside_p = direction*(p[axis]-limit) >= 0
                inside_q = direction*(q[axis]-limit) >= 0
                if inside_p:
                    clipped.append(p)
                if inside_p != inside_q:
                    t = (limit-p[axis])/(q[axis]-p[axis])
                    clipped.append(tuple(p[k]+t*(q[k]-p[k]) for k in range(3)))
            polygon = clipped
            if len(polygon) < 3:
                break
        if len(polygon) < 3:
            continue
        # Remove duplicate boundary vertices before triangulating tiny pieces.
        cleaned = []
        for p in polygon:
            if not cleaned or sum((p[k]-cleaned[-1][k])**2 for k in range(3)) > 1e-16:
                cleaned.append(p)
        if len(cleaned)>1 and sum((cleaned[0][k]-cleaned[-1][k])**2 for k in range(3))<1e-16:
            cleaned.pop()
        if len(cleaned)<3:
            continue
        front = [(x, y-.10, z) for x, y, z in cleaned]
        back = [(x, y+.002, z) for x, y, z in cleaned]
        piece = []
        face(piece, front, color)
        for tri in piece:
            u, v, w = tri[:3]
            area = abs((v[0]-u[0])*(w[2]-u[2])-(w[0]-u[0])*(v[2]-u[2]))
            if area > 1e-10:
                result.append(tri); outer.append(tri)
                result.append(((w[0], w[1]+.102, w[2]),
                               (v[0], v[1]+.102, v[2]),
                               (u[0], u[1]+.102, u[2]), color))
        for i, (p, q) in enumerate(zip(cleaned, cleaned[1:]+cleaned[:1])):
            if any(abs(p[axis]-limit)<1e-7 and abs(q[axis]-limit)<1e-7
                   for axis, limit in ((0, x0), (0, x1), (2, z0), (2, z1))):
                if sum((p[k]-q[k])**2 for k in range(3)) > 1e-12:
                    face(result, [front[i], back[i], back[(i+1)%len(back)], front[(i+1)%len(front)]], color)
    return result, outer


def geometry(pack, details=None):
    triangles = []
    w, h, d = pack['width'], pack['height'], pack['depth']
    color = pack['color']
    dark = [v * 0.78 for v in color]
    flap = [min(v * 1.16, 1) for v in color]
    leather = (0.13, 0.085, 0.055)
    brass = (0.53, 0.40, 0.19)
    stitch = (0.53, 0.45, 0.31)

    # Rounded, subtly uneven cross-sections replace the prototype's box body.
    levels = [(0.025, .38), (.065, .72), (.13, .9), (.24, .98),
              (.4, 1), (.58, .98), (.73, .96), (.84, .89),
              (.92, .85), (.97, .76), (.985, .70)]
    rings = []
    for z, scale in levels:
        ring = []
        for i in range(32):
            angle = 2*math.pi*i/32
            co, si = math.cos(angle), math.sin(angle)
            x = math.copysign(abs(co)**0.65, co)*w/2*scale
            y = math.copysign(abs(si)**0.65, si)*d/2*scale
            wrinkle = 1+.018*math.sin(5*angle+z*16)+.012*math.cos(9*angle-z*20)
            ring.append((x*wrinkle+.35*math.sin(z*4), y*wrinkle, z*h))
        rings.append(ring)
    face(triangles, list(reversed(rings[0])), dark)
    face(triangles, rings[-1], flap)
    for lower, upper in zip(rings, rings[1:]):
        for i in range(32):
            j = (i+1)%32
            face(triangles, [lower[i], lower[j], upper[j], upper[i]], color)
    body = list(triangles)
    def body_y(x, z, front=True):
        return surface_y(body, x, min(z, h*.985), front)

    def width_at(z):
        for (z0, s0), (z1, s1) in zip(levels, levels[1:]):
            if z0 <= z <= z1:
                return w*(s0+(s1-s0)*(z-z0)/(z1-z0))*.78
        return w*.70*.78

    def ribbon(path, width, tint, thickness=.14, oriented=False, conform=False):
        # Path rows contain (center X, Y, Z, width multiplier).
        if conform:
            dense = []
            for a, b in zip(path, path[1:]):
                steps = max(1, math.ceil(max(abs(b[k]-a[k]) for k in range(3))/.28))
                for j in range(steps):
                    t = j/steps
                    dense.append(tuple(a[k]+(b[k]-a[k])*t for k in range(4)))
            path = dense+[path[-1]]
        fronts, backs = [], []
        columns = 6 if conform else (8 if width > 5 else 2)
        for row, (x, y, z, scale) in enumerate(path):
            front, back = [], []
            for j in range(columns+1):
                f = j/columns
                xx = x+(f-.5)*width*scale
                yy, zz = y, z
                if conform:
                    # Keep the strap's INNER face clear of the combined flap,
                    # pocket, and body, while retaining the buckle weave depth.
                    end_distance = min(abs(z-path[0][2]), abs(z-path[-1][2]))
                    minimum = thickness+.025+min(.15, end_distance*.4)
                    clearance = max(minimum, body_y(x, z)-y-.14)
                    yy = surface_y(support, xx, z)-clearance
                dy, dz = thickness, 0
                if oriented:
                    prev, nex = path[max(row-1, 0)], path[min(row+1, len(path)-1)]
                    ty, tz = nex[1]-prev[1], nex[2]-prev[2]
                    length = math.hypot(ty, tz)
                    dy, dz = -tz/length*thickness, ty/length*thickness
                front.append((xx, yy, zz)); back.append((xx, yy+dy, zz+dz))
            fronts.append(front); backs.append(back)
        for i in range(len(path)-1):
            for j in range(columns):
                face(triangles, [fronts[i][j], fronts[i][j+1], fronts[i+1][j+1], fronts[i+1][j]], tint)
                face(triangles, [backs[i][j+1], backs[i][j], backs[i+1][j], backs[i+1][j+1]], tint)
            for side in (0, columns):
                edge = [fronts[i][side], fronts[i+1][side], backs[i+1][side], backs[i][side]]
                face(triangles, edge if side == 0 else list(reversed(edge)), tint)
        for j in range(columns):
            face(triangles, [fronts[0][j+1], fronts[0][j], backs[0][j], backs[0][j+1]], tint)
            face(triangles, [fronts[-1][j], fronts[-1][j+1], backs[-1][j+1], backs[-1][j]], tint)

    # Project every flap vertex onto the actual triangulated body, not an
    # independently guessed silhouette. The doubled skin sits 0.06 units clear.
    rows = [(z/100, 'front') for z in range(55, 98, 3)]
    rows += [(.985, 'front'), (.990, 'top-front'), (.990, 'top-back'),
             (.985, 'back'), (.97, 'back'), (.94, 'back'), (.91, 'back')]
    fronts, backs = [], []
    flap_front = []
    flap_samples = []
    for z, side in rows:
        front_row, back_row = [], []
        for j in range(17):
            x = (j/16-.5)*width_at(z)
            if side.startswith('top'):
                y = body_y(x, h*.985, side == 'top-front')*.5
                front_row.append((x, y, z*h)); back_row.append((x, y, z*h-.08))
            else:
                sign = -1 if side == 'front' else 1
                y = body_y(x, z*h, side == 'front')
                front_row.append((x, y+sign*.14, z*h))
                back_row.append((x, y+sign*.06, z*h))
                flap_samples.append((x, z*h, side == 'front', y+sign*.14))
        fronts.append(front_row); backs.append(back_row)
    for i in range(len(rows)-1):
        for j in range(16):
            if rows[i][1] == rows[i+1][1] == 'front':
                face(flap_front, [fronts[i][j], fronts[i][j+1], fronts[i+1][j+1], fronts[i+1][j]], flap)
            face(triangles, [fronts[i][j], fronts[i][j+1], fronts[i+1][j+1], fronts[i+1][j]], flap)
            face(triangles, [backs[i][j+1], backs[i][j], backs[i+1][j], backs[i+1][j+1]], flap)
        for j in (0, 16):
            edge = [fronts[i][j], fronts[i+1][j], backs[i+1][j], backs[i][j]]
            face(triangles, edge if j == 0 else list(reversed(edge)), flap)
    for i in (0, len(rows)-1):
        for j in range(16):
            edge = [fronts[i][j], backs[i][j], backs[i][j+1], fronts[i][j+1]]
            face(triangles, edge if i == 0 else list(reversed(edge)), flap)

    # Small sewn-on rounded pocket, rather than a protruding rigid box.
    pocket = dict(pack, width=w*.63, height=h*.31, depth=d*.25, color=dark)
    for i in range(24):
        angle = i*2*math.pi/24
        nxt = (i+1)*2*math.pi/24
        center = (0, body_y(0, h*.29)-.7, h*.29)
        def pocket_point(a, front):
            x, z = math.cos(a)*pocket['width']/2, h*.29+math.sin(a)*pocket['height']/2
            return (x, body_y(x, z)-front, z)
        face(triangles, [center, pocket_point(angle, .65), pocket_point(nxt, .65)], dark)
        face(triangles, [pocket_point(nxt, .65), pocket_point(angle, .65),
                         pocket_point(angle, 0), pocket_point(nxt, 0)], dark)

    def tube(path, radius, tint, closed=False):
        rings = []
        for i, p in enumerate(path):
            prev = path[(i-1)%len(path)] if closed or i else path[0]
            nex = path[(i+1)%len(path)] if closed or i<len(path)-1 else path[-1]
            tangent = [nex[k]-prev[k] for k in range(3)]
            length = math.sqrt(sum(v*v for v in tangent))
            t = [v/length for v in tangent]
            axis = (0, 1, 0) if abs(t[1])<.9 else (1, 0, 0)
            u = (t[1]*axis[2]-t[2]*axis[1], t[2]*axis[0]-t[0]*axis[2], t[0]*axis[1]-t[1]*axis[0])
            length = math.sqrt(sum(v*v for v in u)); u = [v/length for v in u]
            v = (t[1]*u[2]-t[2]*u[1], t[2]*u[0]-t[0]*u[2], t[0]*u[1]-t[1]*u[0])
            rings.append([tuple(p[k]+radius*(u[k]*math.cos(j*math.pi/3)+v[k]*math.sin(j*math.pi/3))
                                for k in range(3)) for j in range(6)])
        count = len(path) if closed else len(path)-1
        for i in range(count):
            for j in range(6):
                face(triangles, [rings[i][j], rings[i][(j+1)%6],
                                 rings[(i+1)%len(path)][(j+1)%6], rings[(i+1)%len(path)][j]], tint)
        if not closed:
            face(triangles, list(reversed(rings[0])), tint)
            face(triangles, rings[-1], tint)

    support = list(triangles)
    tie_meshes = []
    contact_faces = []
    harnesses, ties, buckles = [], [], []
    for x in (-w*.23, w*.23):
        zc = h*.58
        by = body_y(x, zc)-.49
        def contact(z):
            return surface_y(support, x, z)-.10
        # Strap feeds through the upper opening, over the center bar, and back
        # through the lower opening before its tail returns to the bag surface.
        tie = [(x, contact(zc+1.4), zc+1.4, 1), (x, by+.24, zc+.5, 1),
                (x, by-.34, zc+.22, 1), (x, by-.34, zc-.22, 1),
                (x, by+.24, zc-.5, 1), (x, contact(zc-1.4), zc-1.4, 1)]
        for source, low, high in ((flap_front, zc+1.4, h*.92), (body, h*.42, zc-1.4)):
            seated, outer = clipped_contact_strip(source, (x-.725, x+.725, low, high), leather)
            triangles.extend(seated); contact_faces.extend(outer)
        first_triangle = len(triangles)
        ribbon(tie, 1.45, leather, .10, conform=True)
        tie_meshes.append(triangles[first_triangle:])
        ties.append(tie); buckles.append((x, by, zc))
        buckle = []
        for i in range(24):
            a = i*2*math.pi/24
            buckle.append((x+math.copysign(abs(math.cos(a))**.5, math.cos(a))*1.06,
                           by, zc+math.copysign(abs(math.sin(a))**.5, math.sin(a))*1.27))
        tube(buckle, .16, brass, True)
        tube([(x-1, by, zc), (x+1, by, zc)], .11, brass)
        sign = -1 if x < 0 else 1
        upper = (x, body_y(x, h*.88, False)-.08, h*.88, 1)
        lower = (x, body_y(x, h*.20, False)-.08, h*.20, .8)
        # Measured on the vanilla torso in Spine1 space, not a guessed ellipse.
        route = BODY_FIT['routes'][0 if sign < 0 else 1]
        anchors = [upper] + [(rx, ry+d/2+WORN_BACK_OFFSET,
            rz+h/2-WORN_HEIGHT_OFFSET, 1) for rx, ry, rz in route] + [lower]
        harness = []
        # Cubic Hermite interpolation rounds the shoulders and underarm turn.
        for i in range(len(anchors)-1):
            a, b = anchors[i:i+2]
            prev, nex = anchors[max(0, i-1)], anchors[min(len(anchors)-1, i+2)]
            for j in range(8):
                t = j/8
                point = tuple((2*t**3-3*t*t+1)*a[k]+(-2*t**3+3*t*t)*b[k]
                              +(t**3-2*t*t+t)*(b[k]-prev[k])*.5
                              +(t**3-t*t)*(nex[k]-a[k])*.5 for k in range(4))
                harness.append(point)
        harness.append(lower)
        ribbon(harness, 2.2, leather, .18, oriented=True)
        harnesses.append(harness)
    # Curved handle and visible seam around the flap's lower edge.
    tube([(-w*.14, 0, h*.98), (-w*.13, 0, h*1.025),
          (0, 0, h*1.04), (w*.13, 0, h*1.025), (w*.14, 0, h*.98)], .38, leather)
    for i in range(25):
        x = (i/24-.5)*width_at(.55)*.92
        z = h*.557
        y = body_y(x, z)-.22
        tube([(x-.12, y, z), (x+.12, y, z)], .06, stitch)
    if pack['id'] == 'wfp_expedition':
        # Rolled bedroll, cylindrical cross-section with bound ends.
        roll = []
        for x in (-w*.54, w*.54):
            roll.append([(x, math.cos(i*math.pi/12)*3, h+3+math.sin(i*math.pi/12)*3)
                         for i in range(24)])
        face(triangles, list(reversed(roll[0])), (.38, .4, .32))
        face(triangles, roll[1], (.38, .4, .32))
        for i in range(24):
            j=(i+1)%24
            face(triangles, [roll[0][i], roll[0][j], roll[1][j], roll[1][i]], (.38, .4, .32))
        for x in (-w*0.27, w*0.27):
            tube([(x, math.cos(i*math.pi/12)*3.13, h+3+math.sin(i*math.pi/12)*3.13)
                  for i in range(24)], .27, leather, True)
            binding = [(x, body_y(x, h*.94)-.08, h*.94, 1)]
            binding += [(x, math.cos(math.pi-i*math.pi/16)*3.15,
                         h+3+math.sin(math.pi-i*math.pi/16)*3.15, 1) for i in range(17)]
            binding.append((x, body_y(x, h*.94, False)+.08, h*.94, 1))
            ribbon(binding, 1.2, leather, .14, oriented=True)
    if details is not None:
        details.update(body=body, flap_samples=flap_samples, ties=ties,
                       buckles=buckles, harnesses=harnesses,
                       support=support, tie_meshes=tie_meshes, contact_faces=contact_faces)
    return triangles


def normal(a, b, c):
    u = [b[i]-a[i] for i in range(3)]
    v = [c[i]-a[i] for i in range(3)]
    n = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    length = math.sqrt(sum(x*x for x in n))
    return tuple(x/length for x in n)


def worn_geometry(triangles, pack):
    # Spine1's longitudinal axis is X; rotate the Z-up bag +90 degrees about Y.
    # Center first, so rotating does not swing the bag away from the attachment.
    def transform(point):
        x, y, z = point
        return (z-pack['height']/2+WORN_HEIGHT_OFFSET, y-WORN_BACK_OFFSET-pack['depth']/2, -x)
    return [(transform(a), transform(b), transform(c), color)
            for a, b, c, color in triangles]


def mesh_arrays(triangles, uv_triangles=None):
    positions, normals, colors, uvs = [], [], [], []
    face_normals = [normal(a, b, c) for a, b, c, _ in triangles]
    neighbors = {}
    for tri, n in zip(triangles, face_normals):
        for vertex in tri[:3]:
            neighbors.setdefault((vertex, tuple(tri[3])), []).append(n)
    for tri, original, n in zip(triangles, uv_triangles or triangles, face_normals):
        a, b, c, color = tri
        original_normal = normal(*original[:3])
        axis = max(range(3), key=lambda k: abs(original_normal[k]))
        uv_axes = [(1, 2), (0, 2), (0, 1)][axis]
        for vertex, source in zip((a, b, c), original[:3]):
            positions.append(vertex)
            nearby = [other for other in neighbors[(vertex, tuple(color))]
                      if sum(n[k]*other[k] for k in range(3)) > .7]
            averaged = [sum(other[k] for other in nearby) for k in range(3)]
            length = math.sqrt(sum(v*v for v in averaged))
            normals.append(tuple(v/length for v in averaged))
            colors.append((*color, 1))
            uvs.append(tuple(source[k]/24 for k in uv_axes))
    return positions, normals, colors, uvs


def osg(triangles, offset=(0, 0, 0), uv_triangles=None):
    positions, normals, colors, uvs = mesh_arrays(triangles, uv_triangles)
    positions = [tuple(p[k]+offset[k] for k in range(3)) for p in positions]
    def array(name, kind, values, binding, unique_id):
        rows = '\n'.join('          ' + ' '.join(f'{v:.5f}' for v in row) for row in values)
        return (f'      {name} TRUE {{\n        osg::{kind} {{\n'
                f'          UniqueID {unique_id}\n          Binding {binding}\n          vector {len(values)} {{\n'
                f'{rows}\n          }}\n        }}\n      }}\n')
    # OpenMW needs an explicit material to preserve vertex colors in its shaders.
    return (f'#Ascii Scene\n#Version 161\n#Generator WayfarerPacks {VERSION}\n'
            'osg::Geode {\n  UniqueID 1\n'
            '  StateSet TRUE {\n    osg::StateSet {\n      UniqueID 7\n'
            '      AttributeList 1 {\n        osg::Material {\n          UniqueID 8\n'
            '          ColorMode AMBIENT_AND_DIFFUSE\n'
            '          Ambient TRUE Front 1 1 1 1 Back 1 1 1 1\n'
            '          Diffuse TRUE Front 1 1 1 1 Back 1 1 1 1\n'
            '          Specular TRUE Front 0 0 0 1 Back 0 0 0 1\n'
            '          Emission TRUE Front 0 0 0 1 Back 0 0 0 1\n'
            '          Shininess TRUE Front 0 Back 0\n'
            '        }\n        Value ON\n      }\n'
            '      TextureModeList 1 { Data 1 { GL_TEXTURE_2D ON } }\n'
            '      TextureAttributeList 1 { Data 1 { osg::Texture2D {\n'
            '        UniqueID 9\n        WRAP_S REPEAT\n        WRAP_T REPEAT\n'
            '        MIN_FILTER LINEAR_MIPMAP_LINEAR\n        MAG_FILTER LINEAR\n'
            '        Image TRUE {\n          ClassName osg::Image\n          UniqueID 10\n'
            '          FileName "textures/wayfarer_packs/leather.png"\n'
            '          WriteHint 2 2\n        }\n'
            '      } Value ON } }\n    }\n  }\n'
            '  Drawables 1 {\n    osg::Geometry {\n      UniqueID 2\n'
            '      UseDisplayList FALSE\n      UseVertexBufferObjects TRUE\n'
            '      PrimitiveSetList 1 {\n        osg::DrawArrays {\n          UniqueID 3\n'
            f'          Mode TRIANGLES\n          First 0\n          Count {len(positions)}\n'
            '        }\n      }\n'
            + array('VertexArray', 'Vec3Array', positions, 'BIND_UNDEFINED', 4)
            + array('NormalArray', 'Vec3Array', normals, 'BIND_PER_VERTEX', 5)
            + array('ColorArray', 'Vec4Array', colors, 'BIND_PER_VERTEX', 6)
            + '      TexCoordArrayList 1 {\n        osg::Vec2Array {\n          UniqueID 11\n'
            + f'          Binding BIND_PER_VERTEX\n          vector {len(uvs)} {{\n'
            + '\n'.join('            '+' '.join(f'{v:.5f}' for v in row) for row in uvs)
            + '\n          }\n        }\n      }\n'
            + '    }\n  }\n}\n')


def render(triangles, size):
    # Orthographic thumbnail of the actual mesh, with a small three-quarter turn.
    points = [p for tri in triangles for p in tri[:3]]
    projected = [(x*0.92+y*0.38, z*0.98+y*0.16) for x, y, z in points]
    left, right = min(p[0] for p in projected), max(p[0] for p in projected)
    bottom, top = min(p[1] for p in projected), max(p[1] for p in projected)
    scale = (size-8) / max(right-left, top-bottom)
    pixels = [(0, 0, 0, 0)] * (size*size)
    depths = [float('inf')] * (size*size)
    def project(p):
        x, y, z = p
        return ((x*0.92+y*0.38-(left+right)/2)*scale+size/2,
                (top-(z*0.98+y*0.16))*scale+4, y*0.92-x*0.38)
    for a, b, c, color in triangles:
        a2, b2, c2 = project(a), project(b), project(c)
        denominator = ((b2[1]-c2[1])*(a2[0]-c2[0])+(c2[0]-b2[0])*(a2[1]-c2[1]))
        if abs(denominator) < 1e-8:
            continue
        n = normal(a, b, c)
        shade = 0.5 + 0.5 * max(0, n[0]*-0.35+n[1]*-0.65+n[2]*0.67)
        rgba = tuple(int(min(255, v*shade*255)) for v in color) + (255,)
        for y in range(max(0, math.floor(min(a2[1], b2[1], c2[1]))),
                       min(size, math.ceil(max(a2[1], b2[1], c2[1])))):
            for x in range(max(0, math.floor(min(a2[0], b2[0], c2[0]))),
                           min(size, math.ceil(max(a2[0], b2[0], c2[0])))):
                u = ((b2[1]-c2[1])*(x+0.5-c2[0])+(c2[0]-b2[0])*(y+0.5-c2[1]))/denominator
                v = ((c2[1]-a2[1])*(x+0.5-c2[0])+(a2[0]-c2[0])*(y+0.5-c2[1]))/denominator
                t = 1-u-v
                if min(u, v, t) < 0:
                    continue
                depth = u*a2[2]+v*b2[2]+t*c2[2]
                index = y*size+x
                if depth < depths[index]:
                    depths[index] = depth
                    pixels[index] = rgba
    return pixels


def tga(pixels, size):
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, size, size, 32, 0x28)
    return header + bytes(v for r, g, b, a in pixels for v in (b, g, r, a))


def png(pixels, width, height):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind+data))
    raw = b''.join(b'\0'+bytes(v for px in pixels[y*width:(y+1)*width] for v in px)
                   for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def build():
    packs = json.loads((MOD / 'packs.json').read_text())
    equipment = all_packs(packs)
    ids = set()
    for pack in equipment:
        assert pack['id'] not in ids
        assert pack['id'].isascii() and len(pack['id'] + '_ability') < 32
        assert pack['feather'] > pack['weight'] >= 0
        ids.add(pack['id'])
    (MOD / 'WayfarerPacks.esp').write_bytes(plugin(equipment))
    catalog = ['-- Generated from packs.json by tools/build_wayfarer_packs.py.', 'return {']
    for pack in equipment:
        pack_id = pack['id']
        model_id = pack.get('modelId', pack_id)
        variant = 'true' if pack.get('craftingOnly') else 'false'
        artisan_id = 'nil' if pack.get('craftingOnly') else json.dumps(pack_id+'_artisan')
        base_feather = next(p['feather'] for p in packs if p['id'] == model_id)
        catalog.append(f'    {pack_id} = {{ name = {json.dumps(pack["name"])}, '
                       f'feather = {pack["feather"]}, ability = "{pack_id}_ability", '
                       f'wornModel = "meshes/wayfarer_packs/{model_id}_worn.osgt", '
                       f'craftingOnly = {variant}, artisanId = {artisan_id}, '
                       f'baseFeather = {base_feather} }},')
    previews = []
    preview_dir = ROOT / 'pack-preview/public/assets'
    preview_dir.mkdir(parents=True, exist_ok=True)
    preview_models = []
    for pack in packs:
        pack_id = pack['id']
        triangles = geometry(pack)
        model_dir = MOD / 'meshes/wayfarer_packs'
        model_dir.mkdir(parents=True, exist_ok=True)
        (model_dir / f'{pack_id}.osgt').write_text(osg(triangles), encoding='ascii')
        (model_dir / f'{pack_id}_worn.osgt').write_text(
            osg(worn_geometry(triangles, pack), uv_triangles=triangles), encoding='ascii')
        positions, normals, colors, uvs = mesh_arrays(triangles)
        preview_models.append(dict(pack, wornBackOffset=WORN_BACK_OFFSET,
                                   wornHeightOffset=WORN_HEIGHT_OFFSET, positions=positions, normals=normals,
                                   colors=colors, uvs=uvs, triangles=len(triangles)))
        icon_dir = MOD / 'icons/wayfarer_packs'
        icon_dir.mkdir(parents=True, exist_ok=True)
        (icon_dir / f'{pack_id}.tga').write_bytes(tga(render(triangles, 64), 64))
        (preview_dir / f'{pack_id}.png').write_bytes(png(render(triangles, 96), 96, 96))
        previews.append(render(triangles, 256))
    catalog.append('}')
    (MOD / 'scripts/wayfarer_packs/catalog.lua').write_text('\n'.join(catalog)+'\n', encoding='ascii')
    preview = [px for y in range(256) for image in previews for px in image[y*256:(y+1)*256]]
    (ROOT / 'reports').mkdir(exist_ok=True)
    (ROOT / 'reports/wayfarer-packs-preview.png').write_bytes(png(preview, 256*len(packs), 256))
    (preview_dir / 'packs.json').write_text(json.dumps(
        {'version': VERSION, 'models': preview_models}, separators=(',', ':')), encoding='ascii')
    shutil.copyfile(MOD / 'textures/wayfarer_packs/leather.png', preview_dir / 'leather.png')
    import release
    target = release.package(ROOT)
    print(f'Built {len(equipment)} pack records sharing {len(packs)} models and icons.')
    print(target)


if __name__ == '__main__':
    build()
