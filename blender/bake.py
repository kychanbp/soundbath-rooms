"""Build one room, bake light in Cycles, export glTF + manifest.
Usage: Blender -b -P blender/bake.py -- <room> <lightmap size> <samples> [preview|bake]"""
import sys, os, json, math, time, shutil, importlib
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np
from lib import *
from room_base import Room

argv = sys.argv[sys.argv.index('--') + 1:]
NAME, SIZE, SAMPLES = argv[0], int(argv[1]), int(argv[2])
MODE = argv[3] if len(argv) > 3 else 'bake'
WEB = f'{ROOT}/web/assets/rooms/{NAME}'; os.makedirs(WEB, exist_ok=True)
TEXOUT = f'{ROOT}/web/assets/tex'; os.makedirs(TEXOUT, exist_ok=True)

# position of each room's door on the gallery. West rooms: local +Y is world -X. East rooms: +X.
from layout import PLACE
T = PLACE[NAME]
B = importlib.import_module('build_' + NAME)

reset()
scene = bpy.context.scene
coll = bpy.data.collections.new('room'); scene.collection.children.link(coll)
R = Room(NAME, T)
cfg = B.build(R)
t0 = time.time()
shell, props = R.blender_objects(coll)
ground = None
if NAME == 'hall':
    ground = [o for o in shell if o.name == 'shell_ground'][0]; shell.remove(ground)
    L_ = json.load(open(f'{ROOT}/data/land.json')); cards_ = json.load(open(f'{ROOT}/web/assets/land/cards.json'))
    plc = {k: v for k, v in L_['place']['cards'].items() if k[0] in 'jip'}   # only trees cast shadow in the bake
    card_mesh(bpy.data.collections['room'], cards_, plc)
    plant_mesh(bpy.data.collections['room'], json.load(open(f'{ROOT}/web/assets/land/palms.json')), L_['place']['meshes'])
for name, M, mt in R.models:
    props += import_model(name, M, coll, max_tris=mt)
print('built', len(shell), len(props), round(time.time() - t0))
s = setup(cfg.get('hdri'), cfg.get('rot', 0), cfg.get('strength', 1), samples=SAMPLES)

# stub lights the passage as if the gallery lay beyond it
stub_m = bpy.data.materials.new('stub'); stub_m.use_nodes = True
pb = stub_m.node_tree.nodes['Principled BSDF']; pb.inputs['Emission Color'].default_value = (1, .78, .55, 1); pb.inputs['Emission Strength'].default_value = .5
for x0, y0, x1, h in R.stubs:
    P_ = [R.w(x0, y0, 0), R.w(x1, y0, 0), R.w(x1, y0, h), R.w(x0, y0, h)]
    me = bpy.data.meshes.new('stub'); me.from_pydata([tuple(p) for p in P_], [], [(0, 1, 2, 3)]); me.materials.append(stub_m)
    o = bpy.data.objects.new('stub', me); scene.collection.objects.link(o)
proxy = None
if R.teacher_at:
    t_ = np.load(f"{ROOT}/data/teacher_{R.teacher_at['pose']}.npz"); a_ = R.teacher_at['yaw']; c_, s_ = math.cos(a_), math.sin(a_)
    V_ = t_['V']; W_ = np.c_[c_ * V_[:, 0] - s_ * V_[:, 1] + R.teacher_at['pos'][0], s_ * V_[:, 0] + c_ * V_[:, 1] + R.teacher_at['pos'][1], V_[:, 2]]
    me = bpy.data.meshes.new('proxy'); me.from_pydata(W_.tolist(), [], t_['F'].tolist()); proxy = bpy.data.objects.new('proxy', me); scene.collection.objects.link(proxy)
for P_, st, col in R.glows:
    gm = bpy.data.materials.new('glow'); gm.use_nodes = True
    pb = gm.node_tree.nodes['Principled BSDF']; pb.inputs['Emission Color'].default_value = (*col, 1); pb.inputs['Emission Strength'].default_value = st
    me = bpy.data.meshes.new('glow'); me.from_pydata([tuple(p) for p in P_], [], [(0, 1, 2, 3)]); me.materials.append(gm)
    o = bpy.data.objects.new('glow', me); scene.collection.objects.link(o)
for p, col, power, rad in R.lights:
    l = bpy.data.lights.new('l', 'POINT'); l.color = col; l.energy = power; l.shadow_soft_size = rad
    o = bpy.data.objects.new('l', l); o.location = tuple(p); scene.collection.objects.link(o)


def select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def principled(m):
    return [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED']


class NoMetal:
    """During a diffuse bake every surface must scatter, so remove metal and glass."""
    def __init__(s, objs): s.objs = objs
    def __enter__(s):
        s.saved = []
        seen = set()
        for o in s.objs:
            for m in o.data.materials:
                if m is None or m.name in seen: continue
                seen.add(m.name)
                for p in principled(m):
                    i = p.inputs['Metallic']
                    links = [(l.from_socket, i) for l in i.links]
                    for l in list(i.links): m.node_tree.links.remove(l)
                    j = p.inputs['Transmission Weight']
                    s.saved.append((m, p, i.default_value, links, j.default_value))
                    i.default_value = 0; j.default_value = 0
    def __exit__(s, *a):
        for m, p, v, links, tr in s.saved:
            p.inputs['Metallic'].default_value = v; p.inputs['Transmission Weight'].default_value = tr
            for f, i in links: m.node_tree.links.new(f, i)


def lightmap_uv(objs):
    for o in objs:
        o.data.uv_layers.new(name='lm', do_init=False)
        o.data.uv_layers['lm'].active = True
    select(objs)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(44), island_margin=.0016, area_weight=0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def denoise(img, w, h):
    """Run Intel OIDN through the compositor on a float image."""
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.resolution_percentage = 100
    ng = bpy.data.node_groups.new('den', 'CompositorNodeTree'); sc.compositing_node_group = ng
    i = ng.nodes.new('CompositorNodeImage'); i.image = img
    d = ng.nodes.new('CompositorNodeDenoise'); d.prefilter = 'NONE'
    try: d.use_hdr = True
    except Exception: pass
    for sock in d.inputs:
        if sock.name.upper() == 'HDR': sock.default_value = True
    out = ng.nodes.new('NodeGroupOutput'); ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    ng.links.new(i.outputs[0], d.inputs[0]); ng.links.new(d.outputs[0], out.inputs[0])
    return ng


def bake_lm(objs, SIZE=SIZE):
    t = time.time()
    img = bpy.data.images.new('lm', SIZE, SIZE, alpha=False, float_buffer=True); img.colorspace_settings.name = 'Non-Color'
    for o in objs:
        for m in o.data.materials:
            n = m.node_tree.nodes.new('ShaderNodeTexImage'); n.name = 'LM'; n.image = img; m.node_tree.nodes.active = n
    select(objs)
    sc = bpy.context.scene; sc.cycles.samples = SAMPLES
    sc.render.bake.use_pass_direct = True; sc.render.bake.use_pass_indirect = True; sc.render.bake.use_pass_color = False
    sc.render.bake.margin = 10
    with NoMetal(objs):
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, margin=10, use_clear=True)
    a = np.empty(SIZE * SIZE * 4, 'f4'); img.pixels.foreach_get(a); a = a.reshape(SIZE, SIZE, 4)[::-1, :, :3]
    for o in objs:
        for m in o.data.materials:
            n = m.node_tree.nodes.get('LM')
            if n: m.node_tree.nodes.remove(n)
    bpy.data.images.remove(img)
    print('baked lm', round(time.time() - t), 's', flush=True)
    return a


def bake_vc(objs):
    t = time.time()
    objs = [o for o in objs if len(o.data.polygons)]
    for o in objs:
        me = o.data
        me.color_attributes.new('lmv', 'FLOAT_COLOR', 'POINT'); me.attributes.active_color = me.attributes['lmv']
    sc = bpy.context.scene; sc.render.bake.target = 'VERTEX_COLORS'; sc.cycles.samples = max(64, SAMPLES // 2)
    with NoMetal(objs):
        for o in objs:
            select([o])
            bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'})
    sc.render.bake.target = 'IMAGE_TEXTURES'
    for o in objs:   # remove sample noise: average each vertex with its neighbours
        me = o.data; c = np.empty(len(me.vertices) * 4, 'f4'); a = me.color_attributes['lmv']; a.data.foreach_get('color', c); c = c.reshape(-1, 4)
        if NAME == 'cave' and o.name.startswith('shell_') is False and o.name == 'prop_rock':   # wall foot sits below the floor line
            q = np.empty(len(me.vertices) * 3, 'f4'); me.vertices.foreach_get('co', q); q = q.reshape(-1, 3)
            c[q[:, 2] < .16, :3] = .006
        if NAME == 'cave' and 'sand2' in o.name:   # floor outside the cave wall saw the sky in the bake
            q = np.empty(len(me.vertices) * 3, 'f4'); me.vertices.foreach_get('co', q); q = q.reshape(-1, 3)
            c[np.hypot(q[:, 0] / 6.2, (q[:, 1] - 46.2) / 7.0) > .93, :3] = .004
        e = np.empty(len(me.edges) * 2, 'i4'); me.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
        for _ in range(3):
            acc = c[:, :3].copy(); cnt = np.ones(len(c))
            np.add.at(acc, e[:, 0], c[e[:, 1], :3]); np.add.at(acc, e[:, 1], c[e[:, 0], :3])
            np.add.at(cnt, e[:, 0], 1); np.add.at(cnt, e[:, 1], 1)
            c[:, :3] = acc / cnt[:, None]
        a.data.foreach_set('color', c.ravel())
    print('baked verts', len(objs), round(time.time() - t), 's', flush=True)


def render_sky():
    """The view through the windows: the same world, seen by a panorama camera, in photographic tone."""
    if not cfg.get('hdri'): return
    pc = bpy.data.cameras.new('skyc'); pc.type = 'PANO'; pc.panorama_type = 'EQUIRECTANGULAR'
    cam = bpy.data.objects.new('skyc', pc); scene.collection.objects.link(cam); cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
    cam.location = (0, 0, 0); scene.camera = cam
    w = bpy.context.scene.world; e = [n for n in w.node_tree.nodes if n.type == 'TEX_ENVIRONMENT'][0]
    e.image = bpy.data.images.load(f"{HDRI}/{cfg.get('sky_hdri', cfg['hdri'])}_4k.hdr")
    for o in scene.objects:
        if o is not cam: o.hide_render = True
    s.render.resolution_x, s.render.resolution_y = 4096, 2048; s.cycles.samples = 8; s.cycles.use_denoising = False
    if cfg.get('far'):
        # the real island around the site: Copernicus elevation with Sentinel-2 colour, fading into haze with distance
        F_ = np.load(f'{ROOT}/data/bali/dem.npz'); Zf = F_['Z'][::2, ::2]; sf = float(F_['s']) * 2; n_ = Zf.shape[0]; h0 = float(F_['Z'][F_['Z'].shape[0] // 2, F_['Z'].shape[1] // 2])
        xx = (np.arange(n_) - n_ / 2) * sf; yy = (n_ / 2 - np.arange(n_)) * sf; XXf, YYf = np.meshgrid(xx, yy)
        V_ = np.stack([XXf.ravel(), YYf.ravel(), (Zf.ravel() - h0)], -1)
        cut = (np.abs(XXf.ravel()) < 150) & (np.abs(YYf.ravel()) < 170); V_[cut, 2] -= 40
        idx = np.arange(n_ * n_).reshape(n_, n_); Q_ = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
        me = bpy.data.meshes.new('far'); me.vertices.add(len(V_)); me.vertices.foreach_set('co', V_.ravel()); me.loops.add(Q_.size); me.loops.foreach_set('vertex_index', Q_.ravel()); me.polygons.add(len(Q_)); me.polygons.foreach_set('loop_start', np.arange(len(Q_)) * 4); me.update(calc_edges=True)
        me.polygons.foreach_set('use_smooth', np.ones(len(Q_), bool))
        ul = me.uv_layers.new(name='UVMap'); vi_ = Q_.ravel(); ul.data.foreach_set('uv', np.c_[V_[vi_, 0] / 18000 + .5, V_[vi_, 1] / 18000 + .5].ravel().astype('f4'))
        m_ = bpy.data.materials.new('far'); m_.use_nodes = True; nt_ = m_.node_tree; nt_.nodes.clear(); out = nt_.nodes.new('ShaderNodeOutputMaterial'); mix = nt_.nodes.new('ShaderNodeMixShader'); dif = nt_.nodes.new('ShaderNodeBsdfDiffuse'); em = nt_.nodes.new('ShaderNodeEmission'); em.inputs[0].default_value = (.72, .76, .80, 1); em.inputs[1].default_value = cfg.get('haze', 1.0)
        tx = nt_.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(f'{ROOT}/data/bali/s2.png'); tx.extension = 'EXTEND'; 
        # terrace contours and tree clumps at fine scale, so that the near hills are not a smear
        geo = nt_.nodes.new('ShaderNodeNewGeometry'); sep = nt_.nodes.new('ShaderNodeSeparateXYZ'); nt_.links.new(geo.outputs['Position'], sep.inputs[0])
        sc = nt_.nodes.new('ShaderNodeMath'); sc.operation = 'MULTIPLY'; sc.inputs[1].default_value = 6.28 / 3.0; nt_.links.new(sep.outputs[2], sc.inputs[0])
        si = nt_.nodes.new('ShaderNodeMath'); si.operation = 'SINE'; nt_.links.new(sc.outputs[0], si.inputs[0])
        rp = nt_.nodes.new('ShaderNodeMapRange'); rp.inputs[1].default_value = -1; rp.inputs[2].default_value = 1; rp.inputs[3].default_value = 1.; rp.inputs[4].default_value = 1.; nt_.links.new(si.outputs[0], rp.inputs[0])
        no = nt_.nodes.new('ShaderNodeTexNoise'); no.inputs['Scale'].default_value = 1 / 26; no.inputs['Detail'].default_value = 7; nt_.links.new(geo.outputs['Position'], no.inputs['Vector'])
        cr = nt_.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = .46; cr.color_ramp.elements[0].color = (.28, .36, .22, 1); cr.color_ramp.elements[1].position = .56; cr.color_ramp.elements[1].color = (1, 1, 1, 1); nt_.links.new(no.outputs[0], cr.inputs[0])
        m1 = nt_.nodes.new('ShaderNodeVectorMath'); m1.operation = 'MULTIPLY'; nt_.links.new(tx.outputs[0], m1.inputs[0]); nt_.links.new(cr.outputs[0], m1.inputs[1])
        m2 = nt_.nodes.new('ShaderNodeVectorMath'); m2.operation = 'SCALE'; nt_.links.new(m1.outputs[0], m2.inputs[0]); nt_.links.new(rp.outputs[0], m2.inputs['Scale']); nt_.links.new(m2.outputs[0], dif.inputs[0])
        cd = nt_.nodes.new('ShaderNodeCameraData'); dv = nt_.nodes.new('ShaderNodeMath'); dv.operation = 'DIVIDE'; dv.inputs[1].default_value = -3200; ex = nt_.nodes.new('ShaderNodeMath'); ex.operation = 'EXPONENT'; inv = nt_.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1
        nt_.links.new(cd.outputs['View Distance'], dv.inputs[0]); nt_.links.new(dv.outputs[0], ex.inputs[0]); nt_.links.new(ex.outputs[0], inv.inputs[1]); nt_.links.new(inv.outputs[0], mix.inputs[0]); nt_.links.new(dif.outputs[0], mix.inputs[1]); nt_.links.new(em.outputs[0], mix.inputs[2]); nt_.links.new(mix.outputs[0], out.inputs[0])
        me.materials.append(m_); fo = bpy.data.objects.new('far', me); scene.collection.objects.link(fo); cam.location = (0, -60, 9); s.cycles.samples = 48; s.cycles.use_denoising = True; pc.clip_end = 200000
    s.render.film_transparent = False; s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Medium High Contrast'
    s.view_settings.exposure = cfg.get('sky_ev', -1.0) - math.log2(max(cfg.get('strength', 1), 1e-3))
    s.render.image_settings.file_format = 'JPEG'; s.render.image_settings.quality = 88; s.render.filepath = f'{WEB}/sky.jpg'
    bpy.ops.render.render(write_still=True)


if MODE == 'sky':
    render_sky(); print('SKY DONE'); raise SystemExit

if MODE == 'preview':
    cams = cfg['cams'][:int(argv[4])] if len(argv) > 4 else cfg['cams']
    s.cycles.samples = SAMPLES
    s.view_settings.exposure = math.log2(cfg.get('exposure', 1))
    s.render.image_settings.file_format = 'JPEG'
    for i, (loc, tg) in enumerate(cams):
        c = camera(f'c{i}', R.w(*loc), R.w(*tg)); s.camera = c
        s.render.filepath = f'{ROOT}/renders/{NAME}_{i}.jpg'
        bpy.ops.render.render(write_still=True)
    print('PREVIEW DONE'); raise SystemExit

# ---- bake
lightmap_uv(shell)
lm = bake_lm(shell)
lmg = None
if ground:
    me = ground.data; ul = me.uv_layers.new(name='lm', do_init=False); co = np.empty(len(me.vertices) * 3, 'f4'); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    vi = np.empty(len(me.loops), 'i4'); me.loops.foreach_get('vertex_index', vi); b = cfg['box']
    ul.data.foreach_set('uv', np.c_[(co[vi, 0] - b[0]) / (b[3] - b[0]), (co[vi, 1] - b[1]) / (b[4] - b[1])].ravel().astype('f4')); me.uv_layers['lm'].active = True
    lmg = bake_lm([ground], cfg.get('lm_ground', 4096))
np.save(f'{ROOT}/data/lm_{NAME}.npy', lm.astype('f4'))
import subprocess
ex = f'{ROOT}/data/lm_{NAME}_den.exr'
subprocess.run([bpy.app.binary_path, '-b', '-P', f'{ROOT}/blender/denoise.py', '--', f'{ROOT}/data/lm_{NAME}.npy', ex], check=True, stdout=subprocess.DEVNULL)
_i = bpy.data.images.load(ex); _i.colorspace_settings.name = 'Non-Color'
_a = np.empty(SIZE * SIZE * 4, 'f4'); _i.pixels.foreach_get(_a); lm = _a.reshape(SIZE, SIZE, 4)[::-1, :, :3]; bpy.data.images.remove(_i); os.remove(ex)
bake_vc(props)

# light scale from the bright end of the lightmap
rng = float(max(.5, np.percentile(lm, 99.9) * 1.15))
scipy_ok = False
try:
    import cv2  # not in Blender's Python, kept for the case it exists
except Exception:
    cv2 = None
enc = np.clip(lm / rng, 0, 1) ** (1 / 2.2)
save_jpg(f'{WEB}/lm.jpg', enc, 94)
np.save(f'{ROOT}/data/lmrange_{NAME}.npy', np.array(rng))
print('lm range', rng, flush=True)


# ---- export as glTF: textures are shared files, geometry goes to one .bin per room
class Gltf:
    def __init__(s):
        s.j = dict(asset=dict(version='2.0', generator='soundbath_rooms'), scene=0, scenes=[dict(nodes=[])], nodes=[],
                   meshes=[], accessors=[], bufferViews=[], buffers=[], materials=[], textures=[], images=[], samplers=[dict(wrapS=10497, wrapT=10497, magFilter=9729, minFilter=9987)])
        s.blob = bytearray(); s.mats = {}; s.imgs = {}; s.extra = {}
    def view(s, arr, target, ctype, typ, minmax=False):
        while len(s.blob) % 4: s.blob.append(0)
        s.j['bufferViews'].append(dict(buffer=0, byteOffset=len(s.blob), byteLength=arr.nbytes, target=target)); s.blob += arr.tobytes()
        ac = dict(bufferView=len(s.j['bufferViews']) - 1, componentType=ctype, count=len(arr) if typ != 'SCALAR' else arr.size, type=typ)
        if minmax: ac['min'] = [float(x) for x in arr.min(0)]; ac['max'] = [float(x) for x in arr.max(0)]
        s.j['accessors'].append(ac); return len(s.j['accessors']) - 1
    def tex(s, uri):
        if uri not in s.imgs:
            s.j['images'].append(dict(uri=uri)); s.j['textures'].append(dict(source=len(s.j['images']) - 1, sampler=0)); s.imgs[uri] = len(s.j['textures']) - 1
        return s.imgs[uri]
    def shared(s, src):
        fn = os.path.basename(src); dst = f'{TEXOUT}/{fn}'
        if not os.path.exists(dst): shutil.copy(src, dst)
        return s.tex(f'../../tex/{fn}')
    def material(s, bm, lm):
        name = bm.name; key = (name, lm)
        if key in s.mats: return s.mats[key]
        src = bm.get('model')
        if src:
            d = json.load(open(f'{MODELS}/{src}/{src}.gltf'))
            cand = [m for m in d['materials'] if m['name'] == name or name.startswith(m['name'])]
            sm = cand[0]
            def image(ti):
                uri = d['images'][d['textures'][ti['index']]['source']]['uri']
                sf = f'{MODELS}/{src}/{uri}'; return s.shared(sf)
            pbr = sm.get('pbrMetallicRoughness', {}); o = dict(name=name, pbrMetallicRoughness=dict(metallicFactor=pbr.get('metallicFactor', 1), roughnessFactor=pbr.get('roughnessFactor', 1)))
            if 'baseColorTexture' in pbr: o['pbrMetallicRoughness']['baseColorTexture'] = dict(index=image(pbr['baseColorTexture']))
            if 'metallicRoughnessTexture' in pbr: o['pbrMetallicRoughness']['metallicRoughnessTexture'] = dict(index=image(pbr['metallicRoughnessTexture']))
            if 'baseColorFactor' in pbr: o['pbrMetallicRoughness']['baseColorFactor'] = pbr['baseColorFactor']
            if 'normalTexture' in sm: o['normalTexture'] = dict(index=image(sm['normalTexture']))
            for k in ('alphaMode', 'alphaCutoff', 'doubleSided'):
                if k in sm: o[k] = sm[k]
        else:
            c, n, r = tex_paths(name)
            pbr = dict(metallicFactor=float(MATS[name][2] if name in MATS else GENM.get(name, 0)), roughnessFactor=1.0, baseColorTexture=dict(index=s.shared(c)), metallicRoughnessTexture=dict(index=s.shared(r)))
            if name in TINT: pbr['baseColorFactor'] = [*TINT[name], 1]
            o = dict(name=name, pbrMetallicRoughness=pbr, normalTexture=dict(index=s.shared(n)))
        if lm: o['occlusionTexture'] = dict(index=s.tex(lm), texCoord=1)
        s.j['materials'].append(o); s.mats[key] = len(s.j['materials']) - 1
        return s.mats[key]
    def add_object(s, o, lm):
        me = o.data; me.calc_loop_triangles(); nt = len(me.loop_triangles)
        if not nt: return 0
        li = np.empty(nt * 3, 'i4'); me.loop_triangles.foreach_get('loops', li)
        mi = np.empty(nt, 'i4'); me.loop_triangles.foreach_get('material_index', mi)
        vi = np.empty(len(me.loops), 'i4'); me.loops.foreach_get('vertex_index', vi)
        co = np.empty(len(me.vertices) * 3, 'f4'); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        nr = np.empty(len(me.loops) * 3, 'f4'); me.corner_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
        uvname = 'UVMap' if 'UVMap' in me.uv_layers else me.uv_layers[0].name
        uv0 = np.empty(len(me.loops) * 2, 'f4'); me.uv_layers[uvname].data.foreach_get('uv', uv0); uv0 = uv0.reshape(-1, 2)
        P_ = co[vi]; cols = [np.round(P_ * 2000), np.round(nr * 200), np.round(uv0 * 4096)]
        vc = None
        if 'lmv' in me.color_attributes:
            c = np.empty(len(me.vertices) * 4, 'f4'); me.color_attributes['lmv'].data.foreach_get('color', c); vc = c.reshape(-1, 4)[vi, :3]
        if lm:
            uv1 = np.empty(len(me.loops) * 2, 'f4'); me.uv_layers['lm'].data.foreach_get('uv', uv1); uv1 = uv1.reshape(-1, 2); cols.append(np.round(uv1 * 8192))
        _, first, inv = np.unique(np.concatenate(cols, 1), axis=0, return_index=True, return_inverse=True)
        idx = inv.ravel()[li].astype('u4'); P_ = P_[first]; N = nr[first]
        attrs = dict(POSITION=s.view(np.c_[P_[:, 0], P_[:, 2], -P_[:, 1]].astype('f4'), 34962, 5126, 'VEC3', True),
                     NORMAL=s.view(np.c_[N[:, 0], N[:, 2], -N[:, 1]].astype('f4'), 34962, 5126, 'VEC3'),
                     TEXCOORD_0=s.view((uv0[first] * [1, -1] + [0, 1]).astype('f4'), 34962, 5126, 'VEC2'))
        if vc is not None: attrs['COLOR_0'] = s.view(vc[first].astype('f4'), 34962, 5126, 'VEC3')
        if lm: attrs['TEXCOORD_1'] = s.view((uv1[first] * [1, -1] + [0, 1]).astype('f4'), 34962, 5126, 'VEC2')
        prims = []
        tri = idx.reshape(-1, 3)
        for k in np.unique(mi):
            ii = tri[mi == k].ravel()
            prims.append(dict(attributes=attrs, indices=s.view(ii, 34963, 5125, 'SCALAR'), material=s.material(me.materials[int(k)], lm)))
        s.j['meshes'].append(dict(name=o.name, primitives=prims))
        s.j['nodes'].append(dict(name=o.name, mesh=len(s.j['meshes']) - 1)); s.j['scenes'][0]['nodes'].append(len(s.j['nodes']) - 1)
        return nt
    def save(s, path):
        base = os.path.basename(path)
        s.j['buffers'] = [dict(uri=base + '.bin', byteLength=len(s.blob))]
        with open(path + '.gltf', 'w') as f: json.dump(s.j, f)
        with open(path + '.bin', 'wb') as f: f.write(s.blob)


G = Gltf(); tris = 0
for o in shell: tris += G.add_object(o, 'lm.jpg')
if ground:
    gmax = float(max(.5, np.percentile(lmg, 99.9) * 1.15)); save_jpg(f'{WEB}/lmg.jpg', np.clip(lmg / gmax, 0, 1) ** (1 / 2.2), 92)
    Gg = Gltf(); tris += Gg.add_object(ground, 'lmg.jpg'); Gg.save(f'{WEB}/ground'); shutil.copy(f'{ROOT}/data/land_splat.png', f'{WEB}/splat.png'); Image_ = None
    Z_ = np.load(f'{ROOT}/data/land.npz'); Z_['Z'].astype('<f4').tofile(f'{WEB}/height.f32'); (Z_['slope'] > 1.05).astype('u1').tofile(f'{WEB}/steep.u8')
for o in props: tris += G.add_object(o, None)
G.save(f'{WEB}/room'); print('tris', tris, 'KB', len(G.blob) // 1024, flush=True)

# ---- reflection probe: one equirect panorama from the middle of the room
if proxy: proxy.hide_render = True
pc = bpy.data.cameras.new('pano'); pc.type = 'PANO'; pc.panorama_type = 'EQUIRECTANGULAR'
cam = bpy.data.objects.new('pano', pc); scene.collection.objects.link(cam)
cam.location = tuple(R.w(*cfg['pano'])); cam.rotation_euler = (math.pi / 2, 0, -math.pi / 2)
scene.camera = cam
s.render.resolution_x, s.render.resolution_y = 1024, 512; s.cycles.samples = max(128, SAMPLES // 2)
s.render.film_transparent = False; s.view_settings.view_transform = 'Standard'; s.view_settings.look = 'None'
s.render.image_settings.file_format = 'HDR'; s.render.filepath = f'{WEB}/probe.hdr'
bpy.ops.render.render(write_still=True)

# ---- sun direction: the brightest spot of the world image, turned by the world rotation
sun = None
if cfg.get('shafts') and cfg.get('hdri'):
    im = bpy.data.images.load(f"{HDRI}/{cfg['hdri']}.hdr"); w_, h_ = im.size
    px = np.empty(w_ * h_ * 4, 'f4'); im.pixels.foreach_get(px); L_ = px.reshape(h_, w_, 4)[..., :3].sum(2)
    j_, i_ = np.unravel_index(np.argmax(L_), L_.shape)
    az = -(i_ / w_ - .5) * 2 * math.pi; el = (j_ / h_ - .5) * math.pi      # image rows are bottom-up in Blender
    d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
    c_, s_ = math.cos(math.radians(-cfg['rot'])), math.sin(math.radians(-cfg['rot']))
    sun = [float(c_ * d[0] - s_ * d[1]), float(s_ * d[0] + c_ * d[1]), float(d[2])]
    print('sun', sun, flush=True)

# ---- manifest for the web app
lo = R.w(*cfg['box'][:3]); hi = R.w(*cfg['box'][3:])
meta = dict(**cfg.get('meta', {}), **({'gmax': gmax} if ground else {}), teacher=R.teacher_at, sun=sun, shaftGain=cfg.get('shafts', 0), name=NAME, title=B.TITLE, lmRange=rng, instruments=R.instruments, seats=R.seats, obstacles=R.obstacles, windows=R.windows, flames=R.flames,
            sky=R.skybox, hdri=cfg.get('hdri'), rot=cfg.get('rot', 0), skygain=cfg.get('skygain', 1.0), exposure=cfg.get('exposure', 1), surface=cfg['surface'],
            box=[*np.minimum(lo, hi).tolist(), *np.maximum(lo, hi).tolist()], probe=R.w(*cfg['pano']).tolist(), walk=[[*R.w(a, b)[:2].tolist(), *R.w(c, d)[:2].tolist()] for a, b, c, d in [*cfg['walk'], *([] if NAME == 'hall' else [(-.62, -.5, .62, 1.3)])]],
            door=R.w(0, 0).tolist(), windowDir=(R.T[:3, :3] @ np.array(cfg.get('window_dir', (0, 0, 1)))).tolist())
if NAME == 'hall':
    meta.update(bounds=L_['bounds'], rocks=L_['place']['rock'], walk=[], lmRangeShell=rng, pond=L_['pond'])
    json.dump(dict(cards=L_['place']['cards'], meshes=L_['place']['meshes'], rice=L_['place']['rice']), open(f'{WEB}/plants.json', 'w'), separators=(',', ':'))
json.dump(meta, open(f'{WEB}/room.json', 'w'))
json.dump(dict(rt=cfg['rt'], box=cfg['box']), open(f'{ROOT}/data/acoustic_{NAME}.json', 'w'))
render_sky()
print('DONE', NAME, flush=True)
