"""Inventory of one .blend file, run headless by Blender:

    blender -b file.blend --python cad/tools/blender_inspect.py -- out.json out.png

Writes a JSON with file metadata, scene units, collections and every object (type, dimensions in
scene units, world-space bounding box, parent, modifiers, materials, vertex count, visibility),
then renders one isometric Workbench view of all visible meshes (all meshes if none is visible).
Used once on 2026-10-21 for cad/blender_inventory.md; the Blender files themselves are not in the repo.
"""
import bpy, sys, json, os, datetime
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
out_json, out_png = argv[0], argv[1]

scene = bpy.context.scene
path = bpy.data.filepath
st = os.stat(path)
info = {
    "file": os.path.basename(path),
    "modified": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
    "size_kb": round(st.st_size / 1024),
    "saved_with_blender": ".".join(str(v) for v in bpy.data.version),
    "unit_system": scene.unit_settings.system,
    "length_unit": scene.unit_settings.length_unit,
    "unit_scale": scene.unit_settings.scale_length,
    "scenes": [s.name for s in bpy.data.scenes],
    "collections": [],
    "objects": [],
}

def coll_tree(c, depth=0):
    info["collections"].append({"name": c.name, "depth": depth, "n_objects": len(c.objects),
                                "excluded": False})
    for ch in c.children:
        coll_tree(ch, depth + 1)

coll_tree(scene.collection)

for o in scene.objects:
    rec = {
        "name": o.name, "type": o.type,
        "collections": [c.name for c in o.users_collection],
        "parent": o.parent.name if o.parent else None,
        "location": [round(v, 3) for v in o.matrix_world.translation],
        "dimensions": [round(v, 3) for v in o.dimensions],
        "scale": [round(v, 3) for v in o.scale],
        "hidden": (not o.visible_get()) or o.hide_render,
        "modifiers": [f"{m.type}" for m in getattr(o, "modifiers", [])],
        "materials": [ms.material.name for ms in getattr(o, "material_slots", []) if ms.material],
    }
    if o.type == "MESH":
        rec["vertices"] = len(o.data.vertices)
        rec["faces"] = len(o.data.polygons)
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        rec["bbox_min"] = [round(min(p[i] for p in pts), 3) for i in range(3)]
        rec["bbox_max"] = [round(max(p[i] for p in pts), 3) for i in range(3)]
    info["objects"].append(rec)

# --- render -----------------------------------------------------------------
meshes = [o for o in scene.objects if o.type == "MESH"]
vis = [o for o in meshes if o.visible_get() and not o.hide_render]
if not vis:
    for o in meshes:
        o.hide_set(False); o.hide_render = False; o.hide_viewport = False
    vis = meshes
for o in meshes:
    o.hide_render = o not in vis
info["rendered_objects"] = [o.name for o in vis]

if vis:
    pts = [o.matrix_world @ Vector(c) for o in vis for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    info["scene_bbox_min"] = [round(v, 3) for v in mn]
    info["scene_bbox_max"] = [round(v, 3) for v in mx]
    info["scene_extent"] = [round(v, 3) for v in (mx - mn)]
    ctr = (mn + mx) / 2
    size = (mx - mn).length
    ext = mx - mn
    tall = ext.z > 2.5 * max(ext.x, ext.y)

    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "RANDOM"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 1400 if tall else 900
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    if scene.world:
        scene.world.color = (1, 1, 1)
    cam_data = bpy.data.cameras.new("inv_cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size * (1.0 if tall else 0.9)
    cam_data.clip_end = size * 20
    cam_data.clip_start = size * 0.001
    cam = bpy.data.objects.new("inv_cam", cam_data)
    scene.collection.objects.link(cam)
    d = Vector((1.0, -1.2, 0.35 if tall else 0.9)).normalized()
    cam.location = ctr + d * size * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    scene.render.filepath = out_png
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    info["render"] = os.path.basename(out_png)

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(info, f, indent=1, ensure_ascii=False)
print("INSPECT_OK", out_json)
