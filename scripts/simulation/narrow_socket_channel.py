"""Create a narrower socket-channel review candidate without scaling the assembly.

Target width is a photo-constrained modeling hypothesis, not a measurement.
Preserve sheet thickness, aperture height, global shell dimensions and rear bodies.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revise_socket_rear import digest, inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--body-frame", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inner-width-mm", type=float, default=18.6)
    parser.add_argument("--revision", default="r03")
    parser.add_argument("--basis-note", default="Photo-constrained visual-fit hypothesis; not independently measured")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    assert 18.2 <= args.inner_width_mm <= 20.9
    assert re.fullmatch(r"r\d{2,}", args.revision), "Expected revision such as r03 or r04"
    if args.output.exists():
        raise FileExistsError(args.output)
    source_hash = digest(args.source)
    B = Matrix(json.loads(args.body_frame.read_text())["body_to_object"])
    bpy.ops.wm.open_mainfile(filepath=str(args.source))
    before = inventory()
    args.output.mkdir(parents=True, exist_ok=False)
    delta = 20.9 - args.inner_width_mm
    center = -.5
    changed = []
    for obj in list(bpy.data.objects):
        if obj.type != "MESH":
            continue
        name = obj.name
        transform = B.inverted() @ obj.matrix_world
        inverse = transform.inverted()
        q = np.array([transform @ v.co for v in obj.data.vertices]) * 1000
        original = q.copy()
        if name == "Cage bottom and thin sidewalls":
            assert abs(np.ptp(q[:, 0]) - 21.5) < .001, "Use the original r01 20.90-mm channel as source"
        mode = None
        if name == "Housing printed frame":
            # Only vertices on the front aperture boundary. Global outer shell,
            # windows, rear and ceiling retain their coordinates.
            selected = ((q[:, 1] >= -3.001) & (q[:, 1] <= 1.001) &
                        (q[:, 2] <= 6.001) & (q[:, 0] >= -11.751) & (q[:, 0] <= 10.751))
            assert selected.sum() >= 8
            q[selected, 0] = center + (q[selected, 0] - center) * ((22.5 - delta) / 22.5)
            mode = "narrow front opening only"
        elif name.startswith(("Visible folded spring finger", "Finger embossed rib")):
            mid = (q[:, 0].min() + q[:, 0].max()) / 2
            target_mid = center + (mid - center) * ((21.5 - delta - 3.) / (21.5 - 3.))
            q[:, 0] += target_mid - mid
            mode = "reposition finger; retain its individual size"
        elif name.startswith("Embossed mouth floor rib"):
            mid = (q[:, 0].min() + q[:, 0].max()) / 2
            q[:, 0] += center + (mid - center) * ((21.5 - delta - 3.2) / (21.5 - 3.2)) - mid
            mode = "reposition floor rib; retain its individual size"
        elif name.startswith(("Folded vertical mouth rim", "Pressed side seam")):
            mid = (q[:, 0].min() + q[:, 0].max()) / 2
            q[:, 0] -= np.sign(mid - center) * delta / 2
            mode = "translate side detail inward; retain thickness"
        elif name in ["Lower mouth rolled edge", "Spring retaining rolled seam"]:
            width = np.ptp(q[:, 0])
            q[:, 0] = center + (q[:, 0] - center) * ((width - delta) / width)
            mode = "shorten transverse roll; preserve radius"
        elif name in ["Cage bottom and thin sidewalls", "Cage upper mouth rim", "Dark insert inside cage", "Cage rear connector polymer"] or name.startswith("Cage rear metal bridge"):
            q[:, 0] -= np.sign(q[:, 0] - center) * delta / 2
            mode = "move opposite edges inward; retain wall thickness"
        if mode is None:
            continue
        assert np.allclose(q[:, 1:], original[:, 1:], atol=1e-9)
        for vertex, point in zip(obj.data.vertices, q / 1000):
            vertex.co = inverse @ Vector(point)
        obj.data.update()
        obj["width_revision"] = f"OS-001/{args.revision} width-review candidate"
        changed.append({"name": name, "operation": mode,
                        "before_bounds_body_mm": [original.min(0).tolist(), original.max(0).tolist()],
                        "after_bounds_body_mm": [q.min(0).tolist(), q.max(0).tolist()]})
    after = inventory()
    names = {r["name"] for r in changed}
    assert all(after[name] == before[name] for name in before if name not in names)
    checks = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        checks.append({"name": obj.name, "nonmanifold_edges": sum(not e.is_manifold for e in bm.edges),
                       "degenerate_faces": sum(f.calc_area() < 1e-16 for f in bm.faces)})
        bm.free()
    assert all(c["nonmanifold_edges"] == 0 and c["degenerate_faces"] == 0 for c in checks)
    scene = bpy.context.scene
    scene["revision"] = f"{args.revision}-width-review"
    scene["channel_inner_width_mm"] = args.inner_width_mm
    scene["white_aperture_width_mm"] = 22.5 - delta
    scene["width_evidence"] = args.basis_note
    scene["physical_accuracy_verified"] = False
    scene["parent_source_sha256"] = source_hash
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(False)
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(args.output / f"OS-001-{args.revision}.glb"),
                             export_format="GLB", use_selection=True, export_yup=True,
                             export_extras=True, export_animations=False)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.data.objects["Lower printed stand"].hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / f"OS-001-{args.revision}.blend"))
    bpy.ops.wm.open_mainfile(filepath=str(args.output / f"OS-001-{args.revision}.blend"))
    assert inventory() == after
    assert digest(args.source) == source_hash
    report = {"revision": f"{args.revision}-width-review", "basis_note": args.basis_note,
              "source": str(args.source), "source_sha256": source_hash,
              "source_unchanged": True, "target_inner_width_mm": args.inner_width_mm,
              "target_white_aperture_width_mm": 22.5 - delta, "changed": changed,
              "unchanged_mesh_count": len(before) - len(changed), "mesh_count": len(after),
              "checks": checks, "reopen_passed": True, "physical_accuracy_verified": False,
              "outputs_sha256": {p.name: digest(p) for p in args.output.iterdir() if p.is_file()}}
    (args.output / "revision.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("NARROW_CHANNEL_READY", len(changed), args.inner_width_mm, flush=True)


if __name__ == "__main__":
    main()
