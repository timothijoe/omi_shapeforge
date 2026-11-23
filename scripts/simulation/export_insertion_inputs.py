"""Export evaluated V3 and socket meshes for an insertion audit, using Blender Python."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--body-frame", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    B = np.array(json.loads(args.body_frame.read_text())["body_to_object"])
    records = {}
    for kind, source in [("module", args.module), ("socket", args.socket)]:
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(source))
        objects = (bpy.data.collections["Photo + stereo + connected groove reference"].objects
                   if kind == "module" else bpy.data.objects)
        folder = args.output / kind
        folder.mkdir()
        parts = []
        for obj in objects:
            if obj.type not in ("MESH", "CURVE") or (kind == "module" and obj.hide_render):
                continue
            evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            mesh = evaluated.to_mesh()
            mesh.calc_loop_triangles()
            vertices = np.array([evaluated.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
            faces = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
            if kind == "socket":
                vertices = (vertices - B[:3, 3]) @ B[:3, :3]
            vertices *= 1000
            if not len(vertices) or not len(faces):
                evaluated.to_mesh_clear()
                continue
            assert np.isfinite(vertices).all()
            colors = []
            for tri in mesh.loop_triangles:
                color = [.6, .6, .6, 1.]
                if mesh.materials:
                    mat = mesh.materials[tri.material_index]
                    if mat:
                        color = list(mat.diffuse_color)
                        if mat.use_nodes:
                            bs = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                            if bs:
                                color = list(bs.inputs["Base Color"].default_value)
                color[3] = 1.
                colors.append(color)
            filename = f"{len(parts):03d}.npz"
            np.savez_compressed(folder / filename, vertices=vertices, faces=faces, face_colors=colors)
            parts.append({"name": obj.name, "group": obj.get("group"), "file": filename,
                          "bounds_mm": [vertices.min(0).tolist(), vertices.max(0).tolist()],
                          "vertices": len(vertices), "triangles": len(faces)})
            evaluated.to_mesh_clear()
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before
        records[kind] = {"source": str(source), "source_sha256": before, "parts": parts,
                         "revision": bpy.context.scene.get("revision", "r01")}
        if kind == "socket":
            channel = next(p for p in parts if p["name"] == "Cage bottom and thin sidewalls")
            v = np.load(folder / channel["file"])["vertices"]
            xs = np.unique(np.round(v[:, 0], 3))
            zs = np.unique(np.round(v[:, 2], 3))
            rim = next(p for p in parts if p["name"] == "Cage upper mouth rim")
            assert len(xs) == 4 and len(zs) == 3, "Unexpected channel cross section"
            records["channel_basic_clearance"] = {
                "inner_x_mm": [float(xs[1]), float(xs[-2])],
                "inner_z_mm": [float(zs[1]), rim["bounds_mm"][0][2]],
                "width_mm": float(xs[-2] - xs[1]),
                "height_mm": float(rim["bounds_mm"][0][2] - zs[1]),
                "side_sheet_thickness_mm": float(xs[1] - xs[0]),
                "white_aperture_nominal_width_mm": bpy.context.scene.get("white_aperture_width_mm", 22.5),
                "excludes_fine_contacts": True}
    records["body_to_object_m"] = B.tolist()
    records["units"] = "millimeters; module source axes and socket body axes"
    records["source_geometry_changed"] = False
    (args.output / "manifest.json").write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print("INSERTION_INPUTS_READY", {k: len(records[k]["parts"]) for k in ["module", "socket"]}, flush=True)


if __name__ == "__main__":
    main()
