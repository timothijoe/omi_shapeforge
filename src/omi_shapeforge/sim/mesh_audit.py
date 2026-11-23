"""Read-only per-part topology and collision-convexity checks in millimeters."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh


def geometry_hash(mesh):
    digest = hashlib.sha256()
    digest.update(np.asarray(mesh.vertices, dtype="<f8").tobytes())
    digest.update(np.asarray(mesh.faces, dtype="<i8").tobytes())
    return digest.hexdigest()


def load_parts(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    parts = {}
    for kind in ("module", "socket"):
        parts[kind] = []
        for index, rec in enumerate(manifest[kind]["parts"]):
            path = directory / kind / rec["file"]
            with np.load(path) as arrays:
                mesh = trimesh.Trimesh(arrays["vertices"], arrays["faces"], process=False)
                colors = arrays["face_colors"].copy()
            parts[kind].append(dict(rec, index=index, mesh=mesh, colors=colors,
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return manifest, parts


def topology(directory):
    manifest, parts = load_parts(directory)
    rows = []
    for kind, objects in parts.items():
        for p in objects:
            mesh = p["mesh"]
            counts = np.bincount(mesh.edges_unique_inverse)
            hull = mesh.convex_hull
            ratio = float((hull.volume - abs(mesh.volume)) / hull.volume)
            row = dict(kind=kind, index=p["index"], name=p["name"], vertices=len(mesh.vertices),
                triangles=len(mesh.faces), watertight=bool(mesh.is_watertight), winding_consistent=bool(mesh.is_winding_consistent),
                nonfinite_vertices=int((~np.isfinite(mesh.vertices)).any(1).sum()),
                boundary_edges=int((counts == 1).sum()), nonmanifold_edges=int((counts > 2).sum()),
                degenerate_faces_area_below_1e_10_mm2=int((mesh.area_faces < 1e-10).sum()),
                volume_mm3=float(mesh.volume) if mesh.is_watertight else None,
                hull_volume_mm3=float(hull.volume), hull_added_volume_fraction=ratio if mesh.is_watertight else None,
                materially_nonconvex=bool(mesh.is_watertight and ratio > 1e-4), input_sha256=p["sha256"])
            rows.append(row)
    return dict(inputs=str(Path(directory).resolve()), source_hashes={k: manifest[k]["source_sha256"] for k in parts},
        units="mm", parts=rows,
        summary={k: dict(parts=len(parts[k]), closed=sum(r["watertight"] for r in rows if r["kind"] == k),
            degenerate_faces=sum(r["degenerate_faces_area_below_1e_10_mm2"] for r in rows if r["kind"] == k)) for k in parts},
        scope="topology and convex-hull volume difference; no physical accuracy or insertability certification")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = topology(args.inputs)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
