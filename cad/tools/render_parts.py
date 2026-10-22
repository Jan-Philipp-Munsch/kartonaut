"""Blender-Renderer für cad/build.py: importiert die STLs aus einem Manifest, färbt sie und rendert eine Ansicht.

    blender -b --python cad/tools/render_parts.py -- manifest.json out.png <overall|section|tvc|avionics|...|pad|pad_detail|pad_section>
"""
import bpy, sys, json, math
from pathlib import Path
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
manifest, out_png, view = Path(argv[0]), argv[1], argv[2]
items = json.loads(manifest.read_text(encoding="utf-8"))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = "METRIC"
scene.unit_settings.scale_length = 0.001
scene.unit_settings.length_unit = "MILLIMETERS"

objs = []
for it in items:
    bpy.ops.wm.stl_import(filepath=str(manifest.parent / it["file"]))
    o = bpy.context.selected_objects[0]
    o.name = it["name"]
    mat = bpy.data.materials.new(it["name"])
    r, g, b = it["color"]
    mat.diffuse_color = (r, g, b, 1.0)
    mat.roughness = 0.6
    o.data.materials.append(mat)
    try:   # runde Flächen glatt, Kanten ab 30° scharf (Blender >= 4.1)
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    except Exception:
        pass
    objs.append(o)

pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (mn + mx) / 2
ext = mx - mn

scene.render.engine = "BLENDER_WORKBENCH"
sh = scene.display.shading
sh.light = "STUDIO"
sh.color_type = "MATERIAL"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_shadows = True
sh.show_object_outline = True
scene.display.render_aa = "8"
scene.render.film_transparent = False
world = bpy.data.worlds.new("w"); scene.world = world
world.color = (1, 1, 1)
scene.view_settings.view_transform = "Standard"

cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO"
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(direction, target, scale, rx, ry):
    d = Vector(direction).normalized()
    cam.location = Vector(target) + d * max(ext) * 4
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam_data.ortho_scale = scale
    cam_data.clip_end = max(ext) * 20
    scene.render.resolution_x, scene.render.resolution_y = rx, ry


if view == "overall":
    # von +x/+y: Luke (+y), Innenrahmen-Servo (+x) und Lagerohr des Außenrahmens (+y) sind zu sehen
    aim((1.0, 1.2, 0.55), ctr, max(ext.z * 1.05, ext.x * 1.3), 1000, 1500)
elif view == "section":
    # Blick aus +x auf die Schnittfläche x = 0, leicht von oben
    aim((1.0, -0.35, 0.25), ctr, ext.z * 1.04, 900, 1600)
elif view == "tvc":
    aim((1.0, -1.1, 0.7), ctr, max(ext) * 1.25, 1200, 1000)
elif view == "avionics":
    # von +y (Bestückungsseite mit Teensy), schräg
    aim((0.7, 1.0, 0.45), ctr, ext.z * 1.12, 1000, 1400)
elif view in ("hatch_a", "hatch_b"):
    # Blick radial auf die Luke (A: von +y, B: von -y), Ausschnitt um den Kuppler
    sgn = 1.0 if view == "hatch_a" else -1.0
    aim((0.0, sgn, 0.0), ctr, max(ext.z * 1.08, 90.0), 900, 1400)
elif view == "hatch_a_iso" or view == "hatch_b_iso":
    sgn = 1.0 if view == "hatch_a_iso" else -1.0
    aim((0.45, sgn, 0.35), ctr, max(ext.z * 1.1, 90.0), 1000, 1400)
elif view == "testrig":
    # Gestell von schräg vorn, Welle quer im Bild
    aim((0.9, 1.3, 0.5), ctr, max(ext.z * 1.08, ext.x * 1.15), 1200, 1500)
elif view == "testrig_drive":
    aim((1.0, -1.0, 0.55), ctr, max(ext) * 1.15, 1300, 1000)
elif view == "pad":
    # Startrampe (cad/landingpad.py) mit Rakete, schräg von oben
    aim((-1.0, -1.3, 0.75), ctr, max(ext.z * 1.15, ext.x * 1.25), 1400, 1300)
elif view == "pad_detail":
    aim((-1.0, -1.1, 0.8), ctr, max(ext.x, ext.y) * 1.3, 1300, 1100)
elif view == "pad_section":
    # Schnitt y = 0 durch die Stütze bei 180°, Blick aus -y
    aim((0.0, -1.0, 0.15), ctr, max(ext.x * 1.08, ext.z * 1.6), 1400, 1000)

scene.render.filepath = out_png
scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print("RENDER_OK", out_png)
