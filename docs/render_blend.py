"""Render one orthographic view of a .blend file with the Workbench engine (no scene setup needed).

    blender -b model.blend -P docs/render_blend.py -- out.png <iso|tall> [objects to unhide ...]

Frames all visible meshes (plus the named ones), random per-object colours with cavity shading.
"tall" uses a 900x1400 portrait frame and a flatter camera, "iso" a 900x900 frame.
docs/img/model_rocket.png was made this way from model_rocket.blend (not in this repo).
"""
import bpy, sys, math
from mathutils import Vector

out, view = sys.argv[sys.argv.index("--") + 1:][:2]
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "RANDOM"
scene.display.shading.show_cavity = True
scene.render.resolution_x = 900
scene.render.resolution_y = 1400 if view == "tall" else 900
scene.render.film_transparent = False
scene.world.color = (1, 1, 1) if scene.world else None

extra = sys.argv[sys.argv.index("--") + 3:]
for o in scene.objects:
    if o.name in extra:
        o.hide_set(False); o.hide_render = False; o.hide_viewport = False
vis = [o for o in scene.objects if o.type == "MESH" and o.visible_get() and not o.hide_render]
for o in scene.objects:
    if o.type == "MESH" and o not in vis:
        o.hide_render = True
pts = [o.matrix_world @ Vector(c) for o in vis for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2
size = (mx - mn).length

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam_data.ortho_scale = size * (1.0 if view == "tall" else 0.9)
cam_data.clip_end = size * 20
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
d = Vector((1.0, -1.2, 0.35 if view == "tall" else 0.9)).normalized()
cam.location = ctr + d * size * 3
cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
