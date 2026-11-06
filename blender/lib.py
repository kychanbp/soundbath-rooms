"""Shared geometry, materials, imported models. Z is up, units are metres.
Geo comes from the temple walk project."""
import bpy, math, os, json
import numpy as np
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEX = os.path.join(ROOT, 'data', 'tex')
GEN = os.path.join(ROOT, 'data', 'gen')
MODELS = os.path.join(ROOT, 'data', 'models')
HDRI = os.path.join(ROOT, 'data', 'hdri')

# name: (texture base, metres per repeat, metallic, unused, dir)
MATS = {
    'floor_oak': ('old_wood_floor', 2.2, 0, 0), 'floor_pale': ('wood_floor', 2.4, 0, 0), 'plank_dark': ('dark_wooden_planks', 2.4, 0, 0),
    'hinoki': ('hinoki_planks', 2.2, 0, 0), 'cedar': ('japanese_cedar_planks', 2.0, 0, 0), 'plank': ('wood_planks', 2.4, 0, 0),
    'beam': ('dark_wooden_planks', 2.0, 0, 0), 'pale': ('brown_planks_05', 2.2, 0, 0), 'black_wood': ('black_painted_planks', 2.4, 0, 0),
    'clay': ('clay_plaster', 3.0, 0, 0), 'lime': ('lime_gen', 3.0, 0, 0), 'grey_plaster': ('grey_plaster', 3.0, 0, 0),
    'white_plaster': ('lime_gen', 3.0, 0, 0), 'old_plaster': ('plastered_wall_04', 3.0, 0, 0),
    'concrete_f': ('smooth_concrete_floor', 4.0, 0, 0), 'concrete_w': ('concrete_wall_008', 3.5, 0, 0), 'concrete_r': ('concrete_floor_02', 3.5, 0, 0),
    'rock': ('rock_face_03', 5.0, 0, 0), 'rock2': ('dark_rock', 4.0, 0, 0), 'sand2': ('rock_face_03', 3.0, 0, 0), 'felt': ('poly_wool_herringbone', .6, 0, 0), 'tatami': ('tatami_mat', 1.8, 0, 0),
    'wool': ('wool_boucle', .5, 0, 0), 'velvet': ('velour_velvet', .5, 0, 0), 'linen': ('rough_linen_g', .5, 0, 0), 'herring': ('poly_wool_herringbone', .6, 0, 0),
    'terry': ('terry_cloth', .4, 0, 0), 'rugtex': ('fabric_pattern_05', 1.1, 0, 0), 'rugred': ('quatrefoil_jacquard_fabric', 1.5, 0, 0), 'rugblue': ('quatrefoil_jacquard_fabric', 1.5, 0, 0), 'jacquard': ('quatrefoil_jacquard_fabric', .9, 0, 0),
    'leather': ('brown_leather', .6, 0, 0), 'ground': ('sparse_grass', 4, 0, 0), 'thatch': ('thatch_roof_angled', 3, 0, 0), 'bstone': ('mossy_stone_wall', 2.4, 0, 0), 'brick': ('red_brick', 1.6, 0, 0), 'paras': ('concrete_wall_008', 1.6, 0, 0), 'cobble': ('mossy_cobblestone', 2.4, 0, 0), 'gold': ('rough_linen_g', .4, 0, 0), 'redlac': ('rough_linen_g', .4, 0, 0), 'polw': ('rough_linen_g', .3, 0, 0), 'polb': ('rough_linen_g', .3, 0, 0), 'yellowc': ('rough_linen_g', .4, 0, 0), 'bamboog': ('bamboo_veneer', 1.2, 0, 0), 'rooftile': ('roof_tiles_14', 3, 0, 0), 'siding': ('weathered_planks', 2.4, 0, 0), 'bamboo': ('bamboo_veneer', 1.2, 0, 0),
}
# tint on top of the albedo texture
TINT = {'thatch': (.6, .48, .33), 'paras': (.62, .62, .56), 'gold': (.82, .6, .22), 'redlac': (.42, .05, .04), 'polw': (.92, .9, .84), 'polb': (.05, .05, .05), 'yellowc': (.86, .66, .12), 'bamboog': (.62, .6, .32), 'sand2': (.36, .33, .3), 'felt': (.16, .13, .11), 'cedar': (.6, .54, .5), 'concrete_r': (.34, .34, .33), 'jacquard': (.5, .34, .24), 'white_plaster': (.97, .91, .8), 'rugblue': (.13, .15, .24), 'rugred': (.46, .19, .13), 'velvet': (.42, .09, .07), 'linen': (.74, .66, .54), 'terry': (.55, .5, .42)}
# Generated textures: name -> (metallic, roughness scale, uv scale, dir under data/gen)
GENM = {'bronze_bowl': 1.0, 'gong_a': 1.0, 'gong_b': 1.0, 'gong_c': 1.0, 'skin': 0.0, 'brass': 1.0, 'quartz': 0.0, 'wax': 0, 'steel': 1.0, 'lacquer': 0, 'shoji': 0, 'water': 0, 'wick': 0, 'sand': 0, **{f'sign_{k}': 0 for k in ('himalayan', 'crystal', 'gong', 'rain', 'rin', 'strings', 'cave')}}


def norm(v):
    v = np.asarray(v, float); l = np.linalg.norm(v)
    return v / l if l > 1e-9 else v


class Geo:
    def __init__(self):
        self.b = {}
        self.T = None
        self.rng = np.random.default_rng(7)

    def _bk(self, m):
        return self.b.setdefault(m, dict(V=[], UV=[], Q=[], Tr=[], N=[], n=0))

    def add(self, mat, V, UV, Q=None, Tr=None, N=None):
        V = np.asarray(V, float); UV = np.asarray(UV, float)
        Q = None if Q is None else np.asarray(Q, int).reshape(-1, 4)
        Tr = None if Tr is None else np.asarray(Tr, int).reshape(-1, 3)
        if self.T is not None:
            R = self.T[:3, :3]
            V = V @ R.T + self.T[:3, 3]
            if N is not None:
                N = np.asarray(N, float) @ R.T
            if np.linalg.det(R) < 0:
                if Q is not None: Q = Q[:, ::-1]
                if Tr is not None: Tr = Tr[:, ::-1]
        b = self._bk(mat); o = b['n']
        b['V'].append(V); b['UV'].append(UV)
        if Q is not None and len(Q): b['Q'].append(Q + o)
        if Tr is not None and len(Tr): b['Tr'].append(Tr + o)
        b['N'].append(np.zeros_like(V) if N is None else np.asarray(N, float))
        if N is not None: b['custom'] = True
        b['n'] = o + len(V)

    def with_T(self, T):
        g = self
        class C:
            def __enter__(s):
                s.old = g.T
                g.T = T if s.old is None else s.old @ T
            def __exit__(s, *a):
                g.T = s.old
        return C()

    def uvs(self, m):
        return 1.0 / MATS[m][1] if m in MATS else 1.0

    def quad(self, m, a, b, c, d, flip=False):
        """Flat quad, a b c d counter clockwise seen from the front."""
        P = np.array([a, b, c, d], float)
        e1 = P[1] - P[0]; L1 = np.linalg.norm(e1); e1 = e1 / max(L1, 1e-9)
        n = norm(np.cross(P[1] - P[0], P[3] - P[0])); e2 = np.cross(n, e1)
        s = self.uvs(m); o = self.rng.random(2)
        UV = np.c_[(P - P[0]) @ e1, (P - P[0]) @ e2] * s + o
        self.add(m, P, UV, Q=[[3, 2, 1, 0] if flip else [0, 1, 2, 3]])

    def poly(self, m, pts):
        P = np.asarray(pts, float)
        n = norm(np.cross(P[1] - P[0], P[2] - P[0])); e1 = norm(P[1] - P[0]); e2 = np.cross(n, e1)
        UV = np.c_[(P - P[0]) @ e1, (P - P[0]) @ e2] * self.uvs(m)
        self.add(m, P, UV, Tr=[[0, i, i + 1] for i in range(1, len(P) - 1)])

    def box(self, m, lo, hi):
        lo = np.asarray(lo, float); hi = np.asarray(hi, float)
        c = (lo + hi) / 2; s = hi - lo
        ax = int(np.argmax(s))
        d = np.zeros(3); d[ax] = 1
        up = np.array([0, 0, 1.]) if ax != 2 else np.array([1., 0, 0])
        side = np.cross(up, d)
        w = abs(side @ s); h = abs(up @ s)
        self.beam(m, c - d * s[ax] / 2, c + d * s[ax] / 2, w, h, up)

    def beam(self, m, p0, p1, w, h, up=(0, 0, 1), taper=1.0):
        """Oriented box. Texture grain follows the length."""
        p0 = np.asarray(p0, float); p1 = np.asarray(p1, float)
        d = p1 - p0; L = np.linalg.norm(d); d = d / max(L, 1e-9)
        up = np.asarray(up, float)
        if abs(d @ up) > .99: up = np.array([1., 0, 0])
        s = norm(np.cross(up, d)); u = np.cross(d, s)
        r = []
        for t, k in ((0, 1.0), (1, taper)):
            c = p0 + (p1 - p0) * t
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                r.append(c + s * a * w / 2 * k + u * b * h / 2 * k)
        r = np.array(r)
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        sc = self.uvs(m); o = self.rng.random(2) * 3
        sizes = [(w, h), (w, h), (L, w), (L, h), (L, w), (L, h)]
        for (a, b, c_, e), (su, sv) in zip(faces, sizes):
            P = r[[a, b, c_, e]]
            if su == L:   # grain along U
                if np.linalg.norm(P[1] - P[0]) > np.linalg.norm(P[3] - P[0]) + 1e-9 or abs(np.linalg.norm(P[1]-P[0]) - L) < 1e-6:
                    uv = np.array([[0, 0], [L, 0], [L, sv], [0, sv]])
                else:
                    uv = np.array([[0, 0], [0, sv], [L, sv], [L, 0]])
            else:
                uv = np.array([[0, 0], [su, 0], [su, sv], [0, sv]])
            self.add(m, P, uv * sc + o, Q=[[0, 1, 2, 3]])

    def grid(self, m, P, closed_u=False, closed_v=False, along='u', flip=False, N=None):
        """P shape (nu, nv, 3). A smooth surface. Arc length UV."""
        P = np.asarray(P, float); nu, nv = P.shape[:2]
        if closed_u:
            P = np.concatenate([P, P[:1]], 0); nu += 1
        if closed_v:
            P = np.concatenate([P, P[:, :1]], 1); nv += 1
        du = np.linalg.norm(np.diff(P, axis=0), axis=2).mean(1) if nu > 1 else np.zeros(0)
        dv = np.linalg.norm(np.diff(P, axis=1), axis=2).mean(0) if nv > 1 else np.zeros(0)
        U = np.r_[0, np.cumsum(du)]; W = np.r_[0, np.cumsum(dv)]
        uu, vv = np.meshgrid(U, W, indexing='ij')
        s = self.uvs(m); o = self.rng.random(2)
        uv = (np.stack([uu, vv], -1) if along == 'u' else np.stack([vv, uu], -1)) * s + o
        idx = np.arange(nu * nv).reshape(nu, nv)
        q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
        if flip: q = q[:, ::-1]
        self.add(m, P.reshape(-1, 3), uv.reshape(-1, 2), Q=q,
                 N=None if N is None else np.asarray(N).reshape(-1, 3))

    def cyl(self, m, p0, p1, r0, r1=None, n=12, caps=True, path=None):
        r1 = r0 if r1 is None else r1
        path = np.array([p0, p1], float) if path is None else np.asarray(path, float)
        rs = np.linspace(r0, r1, len(path)) if not hasattr(r0, '__len__') else np.asarray(r0)
        self.tube(m, path, rs, n, caps)

    def tube(self, m, path, rs, n=10, caps=True):
        path = np.asarray(path, float); k = len(path)
        d = np.gradient(path, axis=0); d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
        up = np.array([0, 0, 1.]) if abs(d[0][2]) < .9 else np.array([1., 0, 0])
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        P = np.zeros((n, k, 3))
        s = norm(np.cross(up, d[0]))
        for i in range(k):
            s = norm(s - d[i] * (s @ d[i])); t = np.cross(d[i], s)
            for j in range(n):
                P[j, i] = path[i] + (s * math.cos(a[j]) + t * math.sin(a[j])) * rs[i]
        self.grid(m, P, closed_u=True, along='v')
        if caps:
            self.poly(m, P[::-1, -1] if False else P[:, -1])
            self.poly(m, P[::-1, 0])

    def lathe(self, m, c, prof, n=24):
        """Revolve prof [(r,z),...] around Z through c. Faces out when z rises."""
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        prof = np.asarray(prof, float)
        P = np.zeros((n, len(prof), 3))
        for j, (r, z) in enumerate(prof):
            P[:, j, 0] = c[0] + r * np.cos(a); P[:, j, 1] = c[1] + r * np.sin(a); P[:, j, 2] = c[2] + z
        self.grid(m, P, closed_u=True, along='u')

    # ---- mesh objects
    def build(self, coll, prefix=''):
        objs = []
        for m, b in self.b.items():
            if not b['V']: continue
            V = np.concatenate(b['V']); UV = np.concatenate(b['UV'])
            Q = np.concatenate(b['Q']) if b['Q'] else np.zeros((0, 4), int)
            Tr = np.concatenate(b['Tr']) if b['Tr'] else np.zeros((0, 3), int)
            nf = len(Q) + len(Tr)
            mesh = bpy.data.meshes.new(prefix + m)
            mesh.vertices.add(len(V)); mesh.vertices.foreach_set('co', V.ravel())
            idx = np.concatenate([Q.ravel(), Tr.ravel()])
            mesh.loops.add(len(idx)); mesh.loops.foreach_set('vertex_index', idx)
            starts = np.r_[np.arange(len(Q)) * 4, len(Q) * 4 + np.arange(len(Tr)) * 3]
            mesh.polygons.add(nf); mesh.polygons.foreach_set('loop_start', starts)
            mesh.update(calc_edges=True)
            mesh.polygons.foreach_set('use_smooth', np.ones(nf, bool))
            uvl = mesh.uv_layers.new(name='UVMap')
            uvl.data.foreach_set('uv', UV[idx].ravel())
            if b.get('custom'):
                N = np.concatenate(b['N']); N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-9)
                mesh.normals_split_custom_set_from_vertices([tuple(n) for n in N])
            mesh.materials.append(get_material(m))
            mesh.update()
            o = bpy.data.objects.new(prefix + m, mesh)
            coll.objects.link(o)
            objs.append(o)
        return objs


# ---- materials
_mcache = {}
def _img(path, colorspace):
    i = bpy.data.images.load(path, check_existing=True)
    i.colorspace_settings.name = colorspace
    return i


def tex_paths(name):
    if name in MATS:
        b = MATS[name][0]; return f'{TEX}/{b}_c.jpg', f'{TEX}/{b}_n.jpg', f'{TEX}/{b}_r.jpg'
    return f'{GEN}/{name}_c.jpg', f'{GEN}/{name}_n.jpg', f'{GEN}/{name}_r.jpg'


def get_material(name):
    if name in _mcache: return _mcache[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; p = nt.nodes['Principled BSDF']
    c, n, r = tex_paths(name)
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = _img(c, 'sRGB')
    col = t.outputs['Color']
    if name in TINT:
        mx = nt.nodes.new('ShaderNodeVectorMath'); mx.operation = 'MULTIPLY'
        mx.inputs[1].default_value = TINT[name]; nt.links.new(col, mx.inputs[0]); col = mx.outputs[0]
    nt.links.new(col, p.inputs['Base Color'])
    rr = nt.nodes.new('ShaderNodeTexImage'); rr.image = _img(r, 'Non-Color')
    nt.links.new(rr.outputs['Color'], p.inputs['Roughness'])
    nm = nt.nodes.new('ShaderNodeNormalMap')
    nn = nt.nodes.new('ShaderNodeTexImage'); nn.image = _img(n, 'Non-Color')
    nt.links.new(nn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], p.inputs['Normal'])
    p.inputs['Metallic'].default_value = MATS[name][2] if name in MATS else GENM.get(name, 0)
    if name == 'quartz':
        p.inputs['Transmission Weight'].default_value = .35
    if name == 'shoji':
        p.inputs['Emission Color'].default_value = (1, .95, .86, 1); p.inputs['Emission Strength'].default_value = 1.4
    _mcache[name] = m
    return m


# ---- imported CC0 models
def import_model(name, T, coll, keep_ratio=1.0, max_tris=None):
    """Import a Poly Haven glTF model, move it by matrix T, link it to coll. Returns its mesh objects."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=f'{MODELS}/{name}/{name}.gltf')
    new = [o for o in bpy.data.objects if o not in before]
    out = []
    TM = Matrix(np.asarray(T).tolist())
    for o in new:
        if o.type == 'MESH':
            mw = o.matrix_world.copy()
            me = o.data.copy(); o.data = me
            me.transform(TM @ mw); o.parent = None; o.matrix_world = Matrix.Identity(4)
            for c in list(o.users_collection): c.objects.unlink(o)
            coll.objects.link(o); out.append(o)
            o.name = f'prop_{name}_{len(out)}'
            for mat in me.materials:
                mat['model'] = name
    for o in new:
        if o.type != 'MESH': bpy.data.objects.remove(o)
    if max_tris:
        total = sum(len(o.data.polygons) for o in out)
        tri = sum(sum(p.loop_total - 2 for p in o.data.polygons) for o in out)
        if tri > max_tris:
            r = max_tris / tri
            for o in out:
                d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = r
                bpy.context.view_layer.objects.active = o; o.select_set(True)
                bpy.ops.object.modifier_apply(modifier=d.name); o.select_set(False)
    return out


def TRS(x=0, y=0, z=0, rz=0, s=1.0):
    c, n = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    return np.array([[c * s, -n * s, 0, x], [n * s, c * s, 0, y], [0, 0, s, z], [0, 0, 0, 1.]])


# ---- render setup
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable('cycles'); addon_utils.enable('io_scene_gltf2')
    _mcache.clear()


def setup(hdri, rot, strength, samples=64, res=(1280, 720)):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    p = bpy.context.preferences.addons['cycles'].preferences
    p.compute_device_type = 'METAL'; p.get_devices()
    for d in p.devices: d.use = True
    s.cycles.device = 'GPU'; s.cycles.samples = samples; s.cycles.use_denoising = True
    s.cycles.max_bounces = 10; s.cycles.diffuse_bounces = 6; s.cycles.glossy_bounces = 4; s.cycles.transmission_bounces = 6
    s.cycles.sample_clamp_indirect = 12
    s.render.resolution_x, s.render.resolution_y = res
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Medium High Contrast'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    if hdri:
        e = nt.nodes.new('ShaderNodeTexEnvironment'); e.image = bpy.data.images.load(f'{HDRI}/{hdri}.hdr')
        mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
        mp.inputs['Rotation'].default_value = (0, 0, math.radians(rot))
        nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], e.inputs['Vector'])
        nt.links.new(e.outputs[0], bg.inputs[0])
    else:
        bg.inputs[0].default_value = (0, 0, 0, 1)
    bg.inputs[1].default_value = strength
    return s


def camera(name, loc, target, lens=20):
    c = bpy.data.cameras.new(name); c.lens = lens; c.clip_end = 300; c.clip_start = .02
    o = bpy.data.objects.new(name, c); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


def save_jpg(path, a, q=90):
    h, w = a.shape[:2]
    i = bpy.data.images.new('tmp_out', w, h, alpha=False)
    i.colorspace_settings.name = 'Non-Color'
    b = np.ones((h, w, 4), 'f4'); b[..., :3] = a[::-1]
    i.pixels.foreach_set(b.ravel())
    i.filepath_raw = path; i.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = q
    i.save(quality=q)
    bpy.data.images.remove(i)


# ---- crossed tree cards, used as shadow casters in the land bake
def card_mesh(coll, cards, place):
    """One mesh per card image: two crossed quads per plant, with alpha from the card."""
    meshes = []
    for fn, c in cards.items():
        pts = place.get(fn) or []
        if not pts: continue
        V = []; F = []; UV = []
        for x, y, z, s, r in pts:
            w = c['w'] * s / 2; h = c['h'] * s
            for a in (r, r + math.pi / 2):
                dx, dy = math.cos(a) * w, math.sin(a) * w; b = len(V)
                V += [(x - dx, y - dy, z), (x + dx, y + dy, z), (x + dx, y + dy, z + h), (x - dx, y - dy, z + h)]; UV += [(0, 0), (1, 0), (1, 1), (0, 1)]; F.append((b, b + 1, b + 2, b + 3))
        me = bpy.data.meshes.new('card_' + fn); me.from_pydata(V, [], F); ul = me.uv_layers.new(name='UVMap'); ul.data.foreach_set('uv', np.array(UV)[np.array([l.vertex_index for l in me.loops])].ravel())
        m = bpy.data.materials.new('card_' + fn); m.use_nodes = True; nt = m.node_tree; p = nt.nodes['Principled BSDF']
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{ROOT}/data/imp/{fn}.png'); nt.links.new(t.outputs['Color'], p.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], p.inputs['Alpha']); m.blend_method = 'CLIP'
        me.materials.append(m); o = bpy.data.objects.new('card_' + fn, me); coll.objects.link(o); meshes.append(o)
    return meshes


def plant_mesh(coll, geom, place):
    """Palms and bananas as real meshes in the bake, so they cast the same shadows they will have in the app."""
    for key, m in (('f', 'frond'), ):
        V = []; F = []; UV = []
        for name, pts in place.items():
            g = geom[name][key]; P = np.array(g['pos']).reshape(-1, 3); U = np.array(g['uv']).reshape(-1, 2); I = np.array(g['idx']).reshape(-1, 3)
            for x, y, z, s, r in pts:
                c, n = math.cos(r), math.sin(r); b = len(V)
                # three: x, y up, z. Blender: x, -z, y
                X = (P[:, 0] * c + P[:, 2] * n) * s + x; Z_ = (-P[:, 0] * n + P[:, 2] * c) * s
                V += np.c_[X, y - Z_, P[:, 1] * s + z].tolist(); UV += U.tolist(); F += (I + b).tolist()
        me = bpy.data.meshes.new('plants'); me.from_pydata(V, [], F); ul = me.uv_layers.new(name='UVMap'); UVa = np.array(UV); ul.data.foreach_set('uv', UVa[np.array([l.vertex_index for l in me.loops])].ravel())
        mt = bpy.data.materials.new('plants'); mt.use_nodes = True; nt = mt.node_tree; p = nt.nodes['Principled BSDF']
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{ROOT}/data/imp/frond.png'); nt.links.new(t.outputs['Color'], p.inputs['Base Color']); nt.links.new(t.outputs['Alpha'], p.inputs['Alpha'])
        me.materials.append(mt); coll.objects.link(bpy.data.objects.new('plants', me))
