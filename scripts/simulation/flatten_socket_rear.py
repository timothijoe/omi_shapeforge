"""Trim the two user-identified rear protrusions to the housing rear plane.

The flatness constraint is a user correction, not a new sensor measurement.
Run with Blender Python; preserve source files and write a fresh output directory.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revise_socket_rear import digest, inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--body-frame", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--insertion", action="store_true")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    if args.output.exists():
        raise FileExistsError(args.output)
    source_hash = digest(args.source)
    evidence = json.loads(args.evidence.read_text())
    B = Matrix(json.loads(args.body_frame.read_text())["body_to_object"])
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    before = inventory()
    assert args.insertion == ("optical_module_v2" in before)
    targets = ["Rear connector housing 0", "Rear connector housing 1"]
    assert all(name in before for name in targets)
    args.output.mkdir(parents=True, exist_ok=False)
    scene = bpy.context.scene
    stand = bpy.data.objects["Lower printed stand"]
    stand.hide_render = True
    rear_cam = bpy.data.objects["View rear_top"]
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 10
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    side_data = bpy.data.cameras.new("Rear plane side inspection")
    side = bpy.data.objects.new("Rear plane side inspection", side_data)
    scene.collection.objects.link(side)
    side_data.type = "ORTHO"
    side_data.ortho_scale = .115
    side_data.clip_start = .0001
    target = B @ Vector((-.015, -.035, .001))
    side.location = target + B.to_3x3() @ Vector((-.15, 0, .025))
    side.rotation_euler = (target - side.location).to_track_quat("-Z", "Y").to_euler()

    def render(name, cam):
        scene.camera = cam
        scene.render.filepath = str(args.output / name)
        bpy.ops.render.render(write_still=True)

    if args.render:
        render("rear_before.png", rear_cam)
        render("side_before.png", side)
    cuts = []
    rear_y = -.064
    shell = bpy.data.objects["Housing printed frame"]
    shell_to_body = B.inverted() @ shell.matrix_world
    shell_y = min((shell_to_body @ v.co).y for v in shell.data.vertices)
    assert abs(shell_y - rear_y) < 1e-7, "Existing housing rear plane differs from expected"
    for index, name in enumerate(targets):
        obj = bpy.data.objects[name]
        to_body = B.inverted() @ obj.matrix_world
        to_local = to_body.inverted()
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        for v in bm.verts:
            v.co = to_body @ v.co
        y_before = min(v.co.y for v in bm.verts)
        bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                              dist=1e-8, plane_co=Vector((0, rear_y, 0)),
                              plane_no=Vector((0, -1, 0)), clear_outer=True, clear_inner=False)
        boundary = [e for e in bm.edges if e.is_boundary]
        assert boundary and all(abs(v.co.y - rear_y) < 1e-6 for e in boundary for v in e.verts)
        bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        assert all(e.is_manifold for e in bm.edges)
        y_after = min(v.co.y for v in bm.verts)
        assert y_after >= rear_y - 1e-7
        for v in bm.verts:
            v.co = to_local @ v.co
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        obj.name = f"Rear flush surface {index}"
        obj["shape_constraint"] = "User requested flat rear; clipped to existing housing rear plane"
        obj["sensor_fitted"] = False
        cuts.append({"source_name": name, "new_name": obj.name,
                     "body_y_min_before_mm": y_before * 1000,
                     "body_y_min_after_mm": y_after * 1000,
                     "outward_protrusion_removed_mm": (rear_y - y_before) * 1000})
    after = inventory()
    unchanged = [name for name in before if name not in targets]
    assert all(before[name] == after[name] for name in unchanged)
    assert len(after) == len(before)
    if args.render:
        render("rear_after.png", rear_cam)
        render("side_after.png", side)
    if not args.insertion:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in bpy.data.objects:
            if obj.type == "MESH":
                obj.hide_set(False)
                obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(args.output / "OS-001-r02.glb"),
                                 export_format="GLB", use_selection=True, export_yup=True,
                                 export_extras=True, export_animations=False)
    bpy.ops.object.select_all(action="DESELECT")
    stand.hide_set(True)
    scene.camera = rear_cam
    scene["revision"] = "r02-flat-rear"
    scene["parent_source_sha256"] = source_hash
    scene["correction_scope"] = "Two circled rear protrusions trimmed flush to existing white housing back"
    scene["flatness_source"] = "Explicit user correction; not independently established by depth"
    scene["physical_accuracy_verified"] = False
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.overlay.show_overlays = False
                sp.shading.type = "MATERIAL"
                sp.shading.use_scene_world = False
                sp.shading.use_scene_lights = False
                sp.region_3d.view_location = Vector((-.006, -.040, .004))
                sp.region_3d.view_rotation = rear_cam.rotation_euler.to_quaternion()
                sp.region_3d.view_distance = .18
                sp.region_3d.view_perspective = "PERSP"
    name = "OS-001-r02-insertion-V2.blend" if args.insertion else "OS-001-r02.blend"
    output = args.output / name
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    bpy.ops.wm.open_mainfile(filepath=str(output))
    assert inventory() == after
    if args.insertion:
        assert bpy.data.objects["optical_module_v2_1"].hide_get()
        assert not bpy.data.objects["optical_module_v2"].hide_get()
    checks = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        checks.append({"name": obj.name, "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                       "degenerate_faces": sum(f.calc_area() < 1e-16 for f in bm.faces),
                       "finite": all(math.isfinite(c) for v in bm.verts for c in v.co)})
        bm.free()
    assert all(c["finite"] and c["nonmanifold_edges"] == 0 and c["degenerate_faces"] == 0 for c in checks)
    assert digest(args.source) == source_hash
    report = {"revision": "r02-flat-rear", "status": "user_corrected_review_candidate",
              "source": str(args.source), "source_sha256": source_hash, "source_unchanged": True,
              "evidence": evidence, "rear_plane_body_y_mm": rear_y * 1000, "cuts": cuts,
              "unchanged_mesh_count": len(unchanged), "total_mesh_count": len(after),
              "retained_meshes": after, "geometry_checks": checks, "saved_file_reopen_passed": True,
              "physical_accuracy_verified": False, "depth_fit_performed": False,
              "outputs_sha256": {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}}
    (args.output / "revision.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("FLAT_REAR_OK", json.dumps(cuts), flush=True)


if __name__ == "__main__":
    main()
