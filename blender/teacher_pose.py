"""Seat the teacher in a cross-legged pose with IK, export a skinned GLB and a posed mesh for baked shadows.
Usage: Blender -b -P teacher_pose.py -- [render]"""
import bpy, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix, Euler, Quaternion
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WHO = sys.argv[sys.argv.index('--') + 1]
FBX = f'{ROOT}/data/rb/{WHO}/{WHO}_facial.fbx'; WT = f'{ROOT}/web/assets/teacher/{WHO}'
POSE = 'stand' if 'stand' in sys.argv else 'seat'
KEEP = ('AK_09_EyeBlinkLeft', 'AK_10_EyeBlinkRight', 'AK_11_EyeLookDownLeft', 'AK_12_EyeLookDownRight')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX)
A = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]; M = [o for o in bpy.data.objects if o.type == 'MESH'][0]
sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
sc.render.fps = 30
head = A.matrix_world @ A.data.bones['Bip01 Head'].head_local; nose = A.matrix_world @ A.data.bones['Bip01 MNose'].head_local
f = (nose - head); ang = math.atan2(f.x, f.y); print('facing', f, ang)
# face +Y in Blender world
A.animation_data_clear(); M.animation_data_clear() if M.animation_data else None
A.rotation_mode = 'XYZ'; A.rotation_euler.z += ang
bpy.context.view_layer.update()
print('after turn', A.matrix_world @ A.data.bones['Bip01 L Thigh'].head_local, A.matrix_world @ A.data.bones['Bip01 MNose'].head_local)
keys = M.data.shape_keys.key_blocks
bpy.context.view_layer.objects.active = M
for k in [k for k in keys if k.name not in KEEP and k.name != 'Basis']: M.shape_key_remove(k)

bpy.context.view_layer.objects.active = A; A.select_set(True); bpy.ops.object.mode_set(mode='POSE')
AW = A.matrix_world; PB = A.pose.bones
def pm(name): return AW @ PB[name].matrix
def set_world_loc(name, p):
    m = PB[name].matrix.copy(); m.translation = AW.inverted() @ Vector(p); PB[name].matrix = m; bpy.context.view_layer.update()
def rot_world(name, axis, deg):
    """Turn a bone about a world axis through its head."""
    W = pm(name); t = W.translation.copy()
    R = Quaternion(Vector(axis).normalized(), math.radians(deg)).to_matrix().to_4x4()
    N = Matrix.Translation(t) @ R @ Matrix.Translation(-t) @ W
    PB[name].matrix = AW.inverted() @ N; bpy.context.view_layer.update()

if POSE == 'seat': set_world_loc('Bip01 Pelvis', (0, 0, .315))
rot_world('Bip01 Pelvis', (1, 0, 0), -6)       # pelvis tips forward a little
rot_world('Bip01 Spine1', (1, 0, 0), 2); rot_world('Bip01 Spine2', (1, 0, 0), 3)
rot_world('Bip01 Neck', (1, 0, 0), 5); rot_world('Bip01 Head', (1, 0, 0), -11)   # chin level, eyes low

def wp(name): return pm(name).translation.copy()
def aim(bone, child, target):
    """Turn a bone about its head so that its child's head lands on the target direction."""
    h = wp(bone); v = (wp(child) - h).normalized(); d = (Vector(target) - h).normalized()
    q = v.rotation_difference(d); W = pm(bone); R = q.to_matrix().to_4x4()
    PB[bone].matrix = AW.inverted() @ (Matrix.Translation(h) @ R @ Matrix.Translation(-h) @ W); bpy.context.view_layer.update()
def two_bone(up, lo, end, target, pole):
    """Analytic IK: place the middle joint on the side of the pole."""
    H = wp(up); a = (wp(lo) - H).length; b = (wp(end) - wp(lo)).length
    T = Vector(target); D = T - H; d = min(D.length, (a + b) * .999); n = D.normalized()
    x = (a * a - b * b + d * d) / (2 * d); h = math.sqrt(max(a * a - x * x, 0))
    P = Vector(pole) - H; perp = (P - n * P.dot(n)).normalized()
    knee = H + n * x + perp * h
    aim(up, lo, knee); aim(lo, end, T); return knee
if POSE == 'seat': print('knee L', two_bone('Bip01 L Thigh', 'Bip01 L Calf', 'Bip01 L Foot', (.17, .27, .085), (-1.2, .8, .5)))
if POSE == 'seat': print('knee R', two_bone('Bip01 R Thigh', 'Bip01 R Calf', 'Bip01 R Foot', (-.16, .20, .085), (1.2, .8, .5)))
# soles turn up and in
if POSE == 'seat': aim('Bip01 L Foot', 'Bip01 L Toe0', (.26, .36, .05)); aim('Bip01 R Foot', 'Bip01 R Toe0', (-.26, .29, .05))
# arms rest with hands on the knees; the app takes over the arms while playing
for side, s in (('L', 1), ('R', -1)):
    s2 = -s; two_bone(f'Bip01 {side} UpperArm', f'Bip01 {side} Forearm', f'Bip01 {side} Hand', *(((s2 * .17, .32, .31), (s2 * 1.0, -.5, .25)) if POSE == 'seat' else ((s2 * .21, .06, .84), (s2 * 1.0, -.6, .9))))
    for f_ in ('0', '1', '2', '3', '4'):
        for j, a in (('', 14), ('1', 22), ('2', 16)):
            b = f'Bip01 {side} Finger{f_}{j}'
            if b in PB: rot_world(b, (s * .1, 1, 0), s * a * (1.5 if side == 'R' else .3))

bpy.ops.pose.select_all(action='SELECT')
for b in PB:
    b.rotation_mode = 'QUATERNION'
    b.keyframe_insert('rotation_quaternion', frame=1); b.keyframe_insert('location', frame=1)
A.animation_data.action.name = 'seat'
bpy.ops.object.mode_set(mode='OBJECT')

# posed mesh for the bake: it casts shadow but is not exported with the room
de = M.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = de.to_mesh()
mw = np.array(M.matrix_world); V = np.array([tuple(M.matrix_world @ v.co) for v in me.vertices], 'f4'); F = np.array([list(p.vertices)[:3] for p in me.polygons], 'i4')
Q = [list(p.vertices) for p in me.polygons]; print('posed', V.min(0), V.max(0), len(V))
if WHO == 'Female_Adult_09' or POSE == 'stand': np.savez(f'{ROOT}/data/teacher_{POSE}.npz', V=V, F=np.array([q[:3] for q in Q] + [[q[0], q[2], q[3]] for q in Q if len(q) == 4], 'i4'))
de.to_mesh_clear()

if 'render' in sys.argv:
    for m_ in M.data.materials:
        m_.use_nodes = True; nt = m_.node_tree; p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
        k = 'head' if 'head' in m_.name else 'body' if 'body' in m_.name else None
        if k:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{WT}/{k}_c.jpg'); nt.links.new(t.outputs[0], p.inputs['Base Color']); p.inputs['Roughness'].default_value = .55; p.inputs['Specular IOR Level'].default_value = .4
        else:
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(f'{WT}/op.png'); nt.links.new(t.outputs[0], p.inputs['Base Color']); nt.links.new(t.outputs[1], p.inputs['Alpha'])
    sc.render.engine = 'CYCLES'; pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'METAL'; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = 'GPU'; sc.cycles.samples = 48; sc.render.resolution_x, sc.render.resolution_y = 700, 700; sc.view_settings.view_transform = 'AgX'
    w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[0].default_value = (.6, .58, .55, 1)
    g = bpy.data.meshes.new('g'); g.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)], [], [(0, 1, 2, 3)]); sc.collection.objects.link(bpy.data.objects.new('g', g))
    l = bpy.data.lights.new('s', 'SUN'); l.energy = 2.5; lo = bpy.data.objects.new('s', l); lo.rotation_euler = (.9, .3, .6); sc.collection.objects.link(lo)
    for i, (loc, tg, lens) in enumerate(((( 0, 1.7, .8), (0, 0, .42), 40), ((1.6, .6, .7), (0, .1, .4), 40), ((.2, .85, .98), (0, .02, .98), 85))):
        c = bpy.data.cameras.new('c'); c.lens = lens; o = bpy.data.objects.new('c', c); sc.collection.objects.link(o); o.location = loc
        o.rotation_euler = (Vector(tg) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); sc.camera = o
        sc.render.image_settings.file_format = 'JPEG'; sc.render.filepath = f'{ROOT}/renders/teacher_{i}.jpg'; bpy.ops.render.render(write_still=True)
if 'render' not in sys.argv:
    bpy.ops.object.select_all(action='DESELECT'); A.select_set(True); M.select_set(True); bpy.context.view_layer.objects.active = A
    bpy.ops.export_scene.gltf(filepath=f"{WT}/{'teacher_stand' if POSE == 'stand' else 'teacher'}.glb", export_format='GLB', use_selection=True, export_yup=True, export_apply=False, export_animations=True, export_skins=True,
                              export_morph=True, export_morph_normal=False, export_image_format='NONE', export_materials='EXPORT', export_force_sampling=True, export_frame_range=False, export_animation_mode='ACTIONS')
print('POSE DONE')
