"""Finite-step, per-part V3 insertion audit in Blender; never modifies inputs.

All rigid collisions and scenarios excluding uncertain contact details are
reported separately. Exclusion is a diagnostic, not an elastic simulation.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((args.inputs / "manifest.json").read_text())

    def load(kind):
        parts = []
        for p in manifest[kind]["parts"]:
            d = np.load(args.inputs / kind / p["file"])
            v, f = d["vertices"], d["faces"]
            parts.append({**p, "v": v, "f": f, "lo": v.min(0), "hi": v.max(0),
                          "tree": BVHTree.FromPolygons(v.tolist(), f.tolist(), all_triangles=True, epsilon=0.)})
        return parts

    module, socket = load("module"), load("socket")
    for h in socket:
        name = h["name"].lower()
        if any(s in name for s in ["spring", "finger", "embossed", "pressed side seam", "lower mouth rolled"]):
            category = "fine_contact_or_compliant"
        elif h["group"] == "electronics":
            category = "inferred_electronics"
        elif "rear metal bridge" in name:
            category = "inferred_internal_bridge"
        else:
            category = "structural"
        h["category"] = category
    tip = min(p["lo"][1] for p in module)
    head = next(p for p in module if p["name"].startswith("11 Raised"))
    stop = head["lo"][1] - tip
    mouth_y = 1.85
    scenarios = {"all_rigid": {"structural", "fine_contact_or_compliant", "inferred_electronics", "inferred_internal_bridge"},
                 "excluding_fine_contact_details": {"structural", "inferred_electronics", "inferred_internal_bridge"},
                 "structural_only": {"structural"}}

    def collisions(depth, x=-.5, z=.7, roll=0., pitch=0., yaw=0., details=False):
        rx, ry, rz = np.deg2rad([pitch, roll, yaw])
        X = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
        Y = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
        Z = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
        rotation = Z @ X @ Y
        translation = np.array([x, mouth_y - tip - depth, z])
        hits = []
        for p in module:
            v = p["v"] @ rotation.T + translation
            lo, hi = v.min(0), v.max(0)
            possible = [h for h in socket if np.all(hi >= h["lo"] - 1e-7) and np.all(lo <= h["hi"] + 1e-7)]
            if not possible:
                continue
            tree = BVHTree.FromPolygons(v.tolist(), p["f"].tolist(), all_triangles=True, epsilon=0.)
            for h in possible:
                pairs = tree.overlap(h["tree"])
                if pairs:
                    hit = {"module_part": p["name"], "socket_part": h["name"],
                           "category": h["category"], "triangle_pairs": len(pairs)}
                    if details:
                        hit["module_faces"] = sorted({int(a) for a, b in pairs})
                        hit["socket_faces"] = sorted({int(b) for a, b in pairs})
                    hits.append(hit)
        return hits

    def flags(hits):
        return {name: any(h["category"] in groups for h in hits) for name, groups in scenarios.items()}

    profiles = []
    for z in [.7, 1.0]:
        rows, first = [], {name: None for name in scenarios}
        for depth in np.arange(-2, stop + 3, .25):
            hits = collisions(float(depth), z=z)
            f = flags(hits)
            rows.append({"depth_mm": float(depth), "collisions": hits, "scenario_collision": f})
            for name in scenarios:
                if f[name] and first[name] is None:
                    low, high = float(depth - .25), float(depth)
                    while high - low > .01:
                        middle = (low + high) / 2
                        if flags(collisions(middle, z=z))[name]:
                            high = middle
                        else:
                            low = middle
                    first[name] = {"bracket_mm": [low, high],
                                   "contacts": [h for h in collisions(high, z=z, details=True)
                                                if h["category"] in scenarios[name]]}
        profiles.append({"x_mm": -.5, "z_mm": z, "rows": rows, "first_contacts": first})
        print("PROFILE", z, {k: v["bracket_mm"] if v else None for k, v in first.items()}, flush=True)
    sensitivity = []
    # Finite perturbations at a near-stop position, independently varied.
    for axis, values in [("x", [-1., -.5, 0., .5, 1.]), ("z", [-.5, -.25, 0., .25, .5]),
                         ("pitch", [-2., -1., 0., 1., 2.]), ("yaw", [-2., -1., 0., 1., 2.])]:
        for value in values:
            kw = {"x": -.5, "z": .7, "pitch": 0., "yaw": 0.}
            kw[axis] += value
            hits = collisions(stop - 1., **kw)
            sensitivity.append({"axis": axis, "offset": value, "depth_mm": stop - 1.,
                                "pose": kw, "flags": flags(hits), "collisions": hits})
    report = {"module": manifest["module"]["source"], "socket": manifest["socket"]["source"],
              "module_source_sha256": manifest["module"]["source_sha256"],
              "socket_source_sha256": manifest["socket"]["source_sha256"],
              "units": "mm", "leading_tip_y_mm": float(tip),
              "shoulder_y_mm": float(head["lo"][1]), "tip_to_shoulder_mm": float(stop),
              "mouth_y_body_mm": mouth_y, "direction_body": [0, -1, 0],
              "nominal_alignment": {"x_mm": -.5, "z_mm": .7, "rotation": np.eye(3).tolist()},
              "profiles": profiles, "near_stop_sensitivity": sensitivity,
              "scenario_meaning": "Category exclusions are diagnostics; no geometry removal or elastic deflection is simulated.",
              "method": "Per-part triangle surface intersections at 0.25 mm path samples; first detected onset bracket bisected to 0.01 mm. Containment and sampled clearance are audited separately.",
              "limitations": ["Finite-step checks do not certify continuous motion", "Input shapes and dimensions are not physical ground truth", "Two module seam meshes are open surfaces", "No forces, compliance, latch or electrical seating simulation"],
              "physical_insertability_verified": False}
    (args.output / "surface_contacts.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("V3_INSERTION_AUDIT_READY", flush=True)


if __name__ == "__main__":
    main()
