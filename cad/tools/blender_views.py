"""Orthographic views and radial measurements of selected objects of a .blend file.

    blender -b file.blend --python cad/tools/blender_views.py -- out_prefix all|visible [object names ...]

Renders <prefix>_iso.png, _front.png (looking along +Y), _side.png (looking along -X), _top.png and
writes <prefix>_measure.json with, per shown mesh, the radial profile about the z axis in 12 z-bands
(r_min, r_max of the vertices) and the x/y extents. Measurement helper for cad/params.py.
"""
import bpy, sys, json, math
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
prefix, mode = argv[0], argv[1]
names = argv[2:]
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
if names:
    show = [o for o in meshes if o.name in names]
elif mode == "all":
    show = meshes
else:
    show = [o for o in meshes if o.visible_get() and not o.hide_render]
for o in meshes:
    o.hide_render = o not in show
    if o in show:
        o.hide_set(False); o.hide_viewport = False

meas = {}
pts_all = []
for o in show:
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    vs = [o.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not vs:
        continue
    pts_all += vs
    zmin = min(v.z for v in vs); zmax = max(v.z for v in vs)
    nb = 12
    bands = []
    for i in range(nb):
        z0 = zmin + (zmax - zmin) * i / nb; z1 = zmin + (zmax - zmin) * (i + 1) / nb
        sel = [v for v in vs if z0 <= v.z <= z1 + 1e-6]
        if sel:
            rs = [math.hypot(v.x, v.y) for v in sel]
            bands.append({"z": [round(z0, 2), round(z1, 2)], "r_min": round(min(rs), 2), "r_max": round(max(rs), 2),
                          "x": [round(min(v.x for v in sel), 2), round(max(v.x for v in sel), 2)],
                          "y": [round(min(v.y for v in sel), 2), round(max(v.y for v in sel), 2)]})
    meas[o.name] = {"n_verts": len(vs), "z": [round(zmin, 2), round(zmax, 2)],
                    "x": [round(min(v.x for v in vs), 2), round(max(v.x for v in vs), 2)],
                    "y": [round(min(v.y for v in vs), 2), round(max(v.y for v in vs), 2)],
                    "bands": bands}
with open(prefix + "_measure.json", "w", encoding="utf-8") as f:
    json.dump(meas, f, indent=1)

mn = Vector((min(p.x for p in pts_all), min(p.y for p in pts_all), min(p.z for p in pts_all)))
mx = Vector((max(p.x for p in pts_all), max(p.y for p in pts_all), max(p.z for p in pts_all)))
ctr = (mn + mx) / 2
size = (mx - mn).length

scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light = "STUDIO"
scene.display.shading.color_type = "RANDOM"
scene.display.shading.show_cavity = True
scene.display.shading.show_xray = False
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
if scene.world:
    scene.world.color = (1, 1, 1)
cam_data = bpy.data.cameras.new("v_cam")
cam_data.type = "ORTHO"
cam_data.clip_end = size * 20
cam_data.clip_start = size * 0.001
cam = bpy.data.objects.new("v_cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

views = {
    "iso": (Vector((1.0, -1.2, 0.9)), (mx - mn).length * 0.9, 1000, 1000),
    "front": (Vector((0, -1, 0)), 1.05 * max(mx.x - mn.x, mx.z - mn.z), 1000, 1000),
    "side": (Vector((1, 0, 0)), 1.05 * max(mx.y - mn.y, mx.z - mn.z), 1000, 1000),
    "top": (Vector((0, 0, 1)), 1.05 * max(mx.x - mn.x, mx.y - mn.y), 1000, 1000),
}
for name, (d, scale, rx, ry) in views.items():
    d = d.normalized()
    cam_data.ortho_scale = scale
    cam.location = ctr + d * size * 3
    up = Vector((0, 0, 1)) if abs(d.z) < 0.99 else Vector((0, 1, 0))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if name == "top":
        cam.rotation_euler = (0, 0, 0)
    scene.render.resolution_x = rx; scene.render.resolution_y = ry
    scene.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)
print("VIEWS_OK", prefix)
