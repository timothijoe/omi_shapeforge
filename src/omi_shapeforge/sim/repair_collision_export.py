"""New collision-only derivative: remove zero-area faces and cap two seam tubes.

Does not modify Blender authoring files, dimensions, or the insertion fit.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from .mesh_audit import load_parts


def cap_boundary_loops(mesh):
    counts = np.bincount(mesh.edges_unique_inverse)
    boundary = mesh.edges[counts[mesh.edges_unique_inverse] == 1]
    successor = {int(a): int(b) for a, b in boundary}
    if len(successor) != len(boundary) or len(set(successor.values())) != len(boundary):
        raise ValueError("boundary is not a set of simple directed loops")
    remaining = set(successor)
    vertices, faces, loops = mesh.vertices.tolist(), mesh.faces.tolist(), []
    while remaining:
        first = min(remaining)
        loop, current = [], first
        while current not in loop:
            loop.append(current)
            remaining.remove(current)
            current = successor[current]
        if current != first or len(loop) < 3:
            raise ValueError("invalid tube boundary")
        points = mesh.vertices[loop]
        _, singular, _ = np.linalg.svd(points - points.mean(0))
        if singular[-1] > 1e-5:
            raise ValueError("only planar source end loops may be capped")
        center = len(vertices)
        vertices.append(points.mean(0).tolist())
        for a in loop:
            faces.append([successor[a], a, center])
        loops.append(loop)
    result = trimesh.Trimesh(vertices, faces, process=False)
    if not result.is_watertight or not result.is_winding_consistent:
        raise ValueError("cap validation failed")
    return result, len(loops)


def repair(inputs, output):
    inputs, output = Path(inputs).resolve(), Path(output).resolve()
    manifest, parts = load_parts(inputs)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for kind, objects in parts.items():
        (output / kind).mkdir()
        for part in objects:
            original = part["mesh"]
            repaired = original.copy()
            needs_cleanup = bool((original.area_faces < 1e-10).any())
            if needs_cleanup:
                repaired.process(validate=True)
            caps = 0
            if not repaired.is_watertight:
                if not part["name"].startswith("15 Estimated folded seam"):
                    raise ValueError("unexpected open source component")
                repaired, caps = cap_boundary_loops(repaired)
            if not repaired.is_watertight or not repaired.is_winding_consistent or (repaired.area_faces < 1e-10).any():
                raise ValueError("collision topology repair did not validate")
            if not np.allclose(repaired.bounds, original.bounds, atol=1e-8, rtol=0):
                raise ValueError("repair unexpectedly changed the envelope")
            np.savez_compressed(output / kind / part["file"], vertices=repaired.vertices, faces=repaired.faces,
                face_colors=np.tile(part["colors"].mean(0), (len(repaired.faces), 1)))
            rec = manifest[kind]["parts"][part["index"]]
            rec.update(vertices=len(repaired.vertices), triangles=len(repaired.faces))
            rows.append(dict(kind=kind, part=part["name"], original_sha256=part["sha256"],
                removed_degenerate_faces=len(original.faces) - len(repaired.faces) if needs_cleanup else 0,
                caps_added=caps, original_vertices=len(original.vertices), resulting_vertices=len(repaired.vertices),
                original_faces=len(original.faces), resulting_faces=len(repaired.faces), bounds_changed=False))
    manifest.update(collision_derivative=True, source_inputs=str(inputs), source_geometry_changed=False,
        surface_topology_changed=True, purpose="collision-only repair; source Blender and physical dimensions unchanged",
        appearance_note="per-part mean colors only; original authoring remains primary")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = dict(parts=rows, all_parts_closed=True, part_count=len(rows), shape_envelopes_unchanged=True,
                  repair_solves_spring_obstruction=False, source_authoring_modified=False)
    (output / "repair_report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    repair(args.inputs, args.output)


if __name__ == "__main__":
    main()
