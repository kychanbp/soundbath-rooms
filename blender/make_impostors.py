"""Photograph the dense CC0 plant models from two sides, with a clear background. The app shows them as crossed cards."""
import bpy, math, os, sys, json
from mathutils import Vector
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); M = f'{ROOT}/data/models'; OUT = f'{ROOT}/data/imp'; os.makedirs(OUT, exist_ok=True)
meta = {}
for name, res in (('island_tree_01', (2048, 2048)), ('island_tree_03', (2048, 2048)), ('tree_small_02', (2048, 2048)), ('pachira_aquatica_01', (2048, 2048)), ('shrub_01', (2048, 2048)), ('shrub_03', (2048, 2048)), ('fern_02', (2048, 2048)), ('calathea_orbifolia_01', (1536, 1536)), ('anthurium_botany_01', (1536, 1536)), ('grass_medium_01', (2048, 2048))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils; addon_utils.enable('cycles'); addon_utils.enable('io_scene_gltf2')
    bpy.ops.import_scene.gltf(filepath=f'{M}/{name}/{name}.gltf')
    s = bpy.context.scene; ms = [o for o in s.objects if o.type == 'MESH']
    bpy.context.view_layer.update()
    lo = Vector((1e9,) * 3); hi = Vector((-1e9,) * 3)
    for o in ms:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c); lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    size = hi - lo; c = (lo + hi) / 2; print(name, 'size', size, flush=True)
    s.render.engine = 'CYCLES'; p = bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type = 'METAL'; p.get_devices()
    for d in p.devices: d.use = True
    s.cycles.device = 'GPU'; s.cycles.samples = 48; s.cycles.use_denoising = False; s.render.film_transparent = True; s.cycles.max_bounces = 6
    s.view_settings.view_transform = 'Standard'; s.render.resolution_x, s.render.resolution_y = res
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.78, .84, .95, 1); w.node_tree.nodes['Background'].inputs[1].default_value = .85
    l = bpy.data.lights.new('s', 'SUN'); l.energy = 2.6; l.angle = .3; lo_ = bpy.data.objects.new('s', l); s.collection.objects.link(lo_); lo_.rotation_euler = (.9, 0, .5)
    cam = bpy.data.cameras.new('c'); cam.type = 'ORTHO'; aspect = res[0] / res[1]; span = max(size.z * 1.02, max(size.x, size.y) * 1.02 / aspect) if res[1] > res[0] else max(max(size.x, size.y) * 1.02, size.z * 1.02 * aspect)
    cam.ortho_scale = span if res[0] <= res[1] and False else max(span, span * aspect)
    co = bpy.data.objects.new('c', cam); s.collection.objects.link(co); s.camera = co
    for i, a in enumerate((0,)):
        d = Vector((math.sin(math.radians(a)), -math.cos(math.radians(a)), 0)); co.location = c + d * (max(size) * 2); co.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler(); cam.clip_end = max(size) * 6
        s.render.image_settings.file_format = 'PNG'; s.render.image_settings.color_mode = 'RGBA'; s.render.filepath = f'{OUT}/{name}_{i}.png'; bpy.ops.render.render(write_still=True)
    meta[name] = dict(w=cam.ortho_scale, h=cam.ortho_scale * res[1] / res[0] if res[0] >= res[1] else cam.ortho_scale, size=list(size), base=c.z - lo.z)
json.dump(meta, open(f'{OUT}/meta2.json', 'w')); print('IMP DONE', meta)
