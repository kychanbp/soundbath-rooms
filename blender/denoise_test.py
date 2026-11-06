import bpy, numpy as np, sys, os
a=np.load('data/lm_himalayan.npy').astype('f4'); h,w=a.shape[:2]
img=bpy.data.images.new('lmi',w,h,alpha=False,float_buffer=True); img.colorspace_settings.name='Non-Color'
b=np.ones((h,w,4),'f4'); b[...,:3]=a[::-1]; img.pixels.foreach_set(b.ravel())
sc=bpy.context.scene; sc.render.resolution_x,sc.render.resolution_y=w,h; sc.render.resolution_percentage=100
ng=bpy.data.node_groups.new('den','CompositorNodeTree'); sc.compositing_node_group=ng
print([p for p in dir(sc) if 'comp' in p.lower()])
i=ng.nodes.new('CompositorNodeImage'); i.image=img
d=ng.nodes.new('CompositorNodeDenoise'); print([s.name for s in d.inputs],[x for x in dir(d) if not x.startswith('_')][:0])
ng.interface.new_socket('Image',in_out='OUTPUT',socket_type='NodeSocketColor')
out=ng.nodes.new('NodeGroupOutput')
ng.links.new(i.outputs[0],d.inputs[0]); ng.links.new(d.outputs[0],out.inputs[0])
for s in d.inputs:
    if s.name=='HDR': s.default_value=True
    print(s.name, getattr(s,'default_value',None))
sc.render.image_settings.file_format='OPEN_EXR'; sc.render.image_settings.color_depth='32'; sc.render.filepath=os.path.abspath('data/den.exr')
sc.view_settings.view_transform='Raw'; sc.render.film_transparent=False
bpy.ops.render.render(write_still=True)
print('ok')
