"""Conservative rear-detail correction; run with Blender's Python.

The reviewed RealSense RGB supports the two connector bodies, but not the
duplicated black end plates and 24 invented gold contacts. Preserve every other
mesh, including the aperture. This script is specific to legacy candidate_03.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh_record(obj):
    vertices = np.empty(len(obj.data.vertices) * 3, dtype=np.float32)
    obj.data.vertices.foreach_get("co", vertices)
    loops = np.empty(len(obj.data.loops), dtype=np.int32)
    obj.data.loops.foreach_get("vertex_index", loops)
    counts = np.array([len(p.vertices) for p in obj.data.polygons], dtype=np.int32)
    matrix = np.array(obj.matrix_world, dtype=np.float64)
    h = hashlib.sha256(vertices.tobytes() + loops.tobytes() + counts.tobytes() + matrix.tobytes())
    return {"geometry_sha256": h.hexdigest(), "vertices": len(obj.data.vertices),
            "faces": len(obj.data.polygons), "materials": [m.name if m else None for m in obj.data.materials]}


def inventory():
    return {o.name: mesh_record(o) for o in bpy.data.objects if o.type == "MESH"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--insertion", action="store_true")
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    source = args.source.resolve()
    source_hash = digest(source)
    evidence = json.loads(args.evidence.read_text())
    if args.output.exists():
        raise FileExistsError(args.output)
    bpy.ops.wm.open_mainfile(filepath=str(source))
    scene = bpy.context.scene
    original = inventory()
    assert args.insertion == ("optical_module_v2" in original), "Use --insertion for a module alignment scene"
    doomed = [o for o in bpy.data.objects if o.name.startswith("Rear socket contact")
              or o.name in ("Rear connector dark socket 0", "Rear connector dark socket 1")]
    assert len(doomed) == 26, "Unexpected source: expected 24 contacts and 2 end plates"
    assert all(o.type == "MESH" for o in doomed)
    assert "Rear connector housing 0" in original and "Rear connector housing 1" in original
    args.output.mkdir(parents=True, exist_ok=False)
    stand = bpy.data.objects.get("Lower printed stand")
    rear = bpy.data.objects["View rear_top"]
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

    def render(name, camera):
        scene.camera = camera
        stand.hide_render = True
        scene.render.filepath = str(args.output / name)
        bpy.ops.render.render(write_still=True)

    if args.render:
        render("rear_before.png", rear)
    removed = [{"name": o.name, **original[o.name]} for o in doomed]
    for obj in doomed:
        bpy.data.objects.remove(obj, do_unlink=True)
    current = inventory()
    assert set(original) - set(current) == {r["name"] for r in removed}
    assert all(current[name] == original[name] for name in current), "Unexpected retained geometry/material change"
    scene["asset_name_zh"] = "光模块插接座"
    scene["asset_id"] = "OS-001"
    scene["revision"] = "r01-rear-review"
    scene["parent_source_sha256"] = source_hash
    scene["correction_scope"] = "Remove unsupported rear end plates and decorative contact rows; retain observed connector bodies."
    scene["physical_accuracy_verified"] = False
    if args.render:
        render("rear_after.png", rear)
        render("front_after.png", bpy.data.objects["View front_detail"])

    # Export all surviving physical parts, including the lower stand.
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name in current:
            # The alternate optical module remains hidden in insertion scenes.
            if args.insertion and obj.name == "optical_module_v2_1":
                continue
            obj.hide_set(False)
            obj.select_set(True)
    if not args.insertion:
        bpy.ops.export_scene.gltf(filepath=str(args.output / "OS-001-r01.glb"),
                                 export_format="GLB", use_selection=True,
                                 export_yup=True, export_extras=True, export_animations=False)
    bpy.ops.object.select_all(action="DESELECT")
    stand.hide_set(True)
    stand.hide_render = True
    scene.camera = rear
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.overlay.show_overlays = False
                sp.shading.type = "MATERIAL"
                sp.shading.use_scene_world = False
                sp.shading.use_scene_lights = False
                sp.clip_start = .0001
                sp.clip_end = 10
                sp.region_3d.view_location = Vector((-.006, -.040, .004))
                sp.region_3d.view_rotation = rear.rotation_euler.to_quaternion()
                sp.region_3d.view_distance = .18
                sp.region_3d.view_perspective = "PERSP"
    filename = "OS-001-r01-insertion-V2.blend" if args.insertion else "OS-001-r01.blend"
    blend = args.output / filename
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    reopened = inventory()
    assert reopened == current, "Saved mesh inventory changed during reopen"
    if args.insertion:
        assert bpy.data.objects["optical_module_v2_1"].hide_get()
        assert not bpy.data.objects["optical_module_v2"].hide_get()
    checks = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        checks.append({"name": obj.name,
                       "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                       "degenerate_faces": sum(f.calc_area() < 1e-16 for f in bm.faces),
                       "finite_vertices": all(math.isfinite(c) for v in bm.verts for c in v.co)})
        bm.free()
    assert all(c["finite_vertices"] for c in checks)
    if not args.insertion:
        assert all(c["nonmanifold_edges"] == 0 and c["degenerate_faces"] == 0 for c in checks)
    assert digest(source) == source_hash
    report = {"asset_id": "OS-001", "name_zh": "光模块插接座", "revision": "r01-rear-review",
              "status": "observation_review_candidate", "source": str(source),
              "source_sha256": source_hash, "source_unchanged": True,
              "evidence": evidence, "evidence_manifest_sha256": digest(args.evidence),
              "removed": removed, "retained_meshes": reopened,
              "before_mesh_count": len(original), "after_mesh_count": len(current),
              "retained_geometry_and_materials_unchanged": True, "reopen_passed": True,
              "geometry_checks": checks, "physical_accuracy_verified": False,
              "dimensions_refitted": False, "insertion_revalidated": False,
              "outputs": {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}}
    (args.output / "revision.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("SOCKET_REVISION_OK", json.dumps({"file": str(blend), "before": len(original),
                                          "after": len(current), "removed": len(removed)}), flush=True)


if __name__ == "__main__":
    main()
