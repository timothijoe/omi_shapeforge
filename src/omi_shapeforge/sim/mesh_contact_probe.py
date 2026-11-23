"""Isolated contact rig for actual V3/r04 assets, not a robot insertion task.

Compare imported single convex hulls, cavity-preserving decomposition and an
explicit *hypothetical* hinged lip assembly. Original meshes are never saved.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import trimesh

from .mesh_audit import load_parts, geometry_hash


SPRING_PARTS = set(range(17, 31)) | {119} | set(range(120, 127))


def numbers(values):
    return " ".join(str(float(v)) for v in np.asarray(values).ravel())


def piece_meshes(part, kind, cache, cavity):
    mesh = part["mesh"]
    if not cavity:
        return [mesh.convex_hull], "single convex hull"
    if kind == "socket" and part["index"] == 4:
        # Exact three-box union of the source 16-vertex extruded U profile.
        lo, hi = mesh.bounds
        xs = np.unique(np.round(mesh.vertices[:, 0], 3))
        zs = np.unique(np.round(mesh.vertices[:, 2], 3))
        boxes = [(lo, [hi[0], hi[1], zs[1]]),
                 ([lo[0], lo[1], zs[1]], [xs[1], hi[1], hi[2]]),
                 ([xs[-2], lo[1], zs[1]], hi)]
        result = [trimesh.creation.box(bounds=np.array(b)) for b in boxes]
        if not np.isclose(sum(p.volume for p in result), mesh.volume, rtol=1e-5):
            raise ValueError("U-channel decomposition disagrees with source volume")
        return result, "exact source U-channel split into floor and two sidewalls"
    source_index = 120 if kind == "socket" and 120 <= part["index"] <= 126 else part["index"]
    folder = cache / f"{kind}_{source_index:03d}"
    critical = (kind, source_index) in (("socket", 33), ("module", 14), ("socket", 120))
    if critical and not folder.exists():
        raise FileNotFoundError(f"cavity-preserving collision pieces required: {folder}")
    if folder.exists():
        record = json.loads((folder / "record.json").read_text())
        if source_index == part["index"] and record.get("geometry_sha256") != geometry_hash(mesh):
            raise ValueError("collision decomposition does not match source geometry")
        pieces = []
        for path in sorted(folder.glob("*.npz")):
            data = np.load(path)
            vertices = data["vertices"].copy()
            if source_index != part["index"]:
                vertices[:, 0] += mesh.bounds[0, 0] - (-9.8)
            pieces.append(trimesh.Trimesh(vertices, data["faces"], process=False))
        if not pieces or len(pieces) != record["pieces"]:
            raise ValueError("incomplete collision decomposition")
        return pieces, "CoACD approximate convex decomposition; see cache record"
    return [mesh.convex_hull], "single conservative hull; open seams and degenerate faces not used as solid input"


def build_probe(inputs, cache, output, *, mode="split_rigid", x_offset_mm=0., yaw_deg=0., stiffness=.001):
    if mode not in ("raw_hulls", "split_rigid", "split_compliant", "structural_diagnostic"):
        raise ValueError("unknown contact probe mode")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest, parts = load_parts(inputs)
    tip = min(p["mesh"].bounds[0, 1] for p in parts["module"])
    stop = next(p["mesh"].bounds[0, 1] for p in parts["module"] if p["name"].startswith("11 Raised")) - tip
    start_depth = -3.
    root = ET.Element("mujoco", model="v3_r04_mesh_contact_probe")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep="0.0002", gravity="0 0 0", integrator="implicitfast", iterations="100", tolerance="1e-10")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1200", offheight="900")
    ET.SubElement(visual, "map", znear=".0001")
    asset = ET.SubElement(root, "asset")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos=".1 .2 .2", dir="-.3 -.4 -1")
    socket = ET.SubElement(world, "body", name="socket")
    module = ET.SubElement(world, "body", name="module",
        pos=numbers([(-.5 + x_offset_mm) / 1000, (1.85 - tip - start_depth) / 1000, .0007]),
        euler=numbers([0, 0, np.deg2rad(yaw_deg)]))
    ET.SubElement(module, "joint", name="insertion", type="slide", axis="0 -1 0", damping=".1")
    ET.SubElement(module, "inertial", pos="0 0 0", mass=".02", diaginertia="8.3e-6 6e-7 8.8e-6")
    pivot = np.array([-.5, -1.45, -4.05])
    spring = socket
    if mode == "split_compliant":
        spring = ET.SubElement(world, "body", name="hypothetical_lip_assembly", pos=numbers(pivot / 1000))
        ET.SubElement(spring, "joint", name="lip_hinge", type="hinge", axis="1 0 0",
            range=numbers(np.deg2rad([-75, 0])), stiffness=str(stiffness), damping=".00002", armature="1e-8",
            solreflimit=".0004 1", solimplimit=".99999 .99999 .0001")
        ET.SubElement(spring, "inertial", pos="0 .002 .001", mass=".0005", diaginertia="4e-9 2e-8 2e-8")
    actuator = ET.SubElement(root, "actuator")
    ET.SubElement(actuator, "position", name="drive", joint="insertion", kp="2000", kv="10", forcerange="-2 2")
    meshes = output / "meshes"
    meshes.mkdir()
    mapping = {}
    approximations = []
    for kind, objects in parts.items():
        for part in objects:
            index = part["index"]
            is_lip = kind == "socket" and index in SPRING_PARTS
            target = module if kind == "module" else spring if is_lip else socket
            offset = pivot if is_lip and mode == "split_compliant" else np.zeros(3)
            name = f"{kind}_{index:03d}"
            visual_mesh = part["mesh"].copy()
            visual_mesh.vertices = (visual_mesh.vertices - offset) / 1000
            path = meshes / f"{name}_visual.obj"
            visual_mesh.export(path)
            ET.SubElement(asset, "mesh", name=name + "_visual", file=str(path), inertia="shell")
            color = part["colors"].mean(0)
            if is_lip:
                color = [1, .45, .05, 1]
            ET.SubElement(target, "geom", name=name + "_visual", mesh=name + "_visual", type="mesh",
                contype="0", conaffinity="0", group="1", mass="0", rgba=numbers(color))
            pieces, method = piece_meshes(part, kind, Path(cache), mode != "raw_hulls")
            approximations.append(dict(kind=kind, index=index, name=part["name"], method=method, pieces=len(pieces)))
            for j, piece in enumerate(pieces):
                key = f"{name}_collision_{j:03d}"
                piece = piece.copy()
                piece.vertices = (piece.vertices - offset) / 1000
                path = meshes / f"{key}.obj"
                piece.export(path)
                ET.SubElement(asset, "mesh", name=key, file=str(path), inertia="shell")
                enabled = not (mode == "structural_diagnostic" and is_lip)
                ET.SubElement(target, "geom", name=key, mesh=key, type="mesh", group="3", mass="0",
                    contype=str((2 if kind == "module" else 1) if enabled else 0),
                    conaffinity=str((1 if kind == "module" else 2) if enabled else 0),
                    friction=".2 .001 .0001", condim="3", solref=".002 1", solimp=".99 .99 .0001", margin="0", gap="0")
                mapping[key] = dict(kind=kind, index=index, part=part["name"], lip=is_lip)
    ET.indent(root)
    ET.ElementTree(root).write(output / "scene.xml", encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(output / "scene.xml"))
    report = dict(mode=mode, source_inputs=str(Path(inputs).resolve()), source_hashes={k: manifest[k]["source_sha256"] for k in parts},
        start_depth_mm=start_depth, shoulder_depth_mm=float(stop), x_offset_mm=x_offset_mm, yaw_deg=yaw_deg,
        mappings=mapping, approximations=approximations, geoms=model.ngeom,
        assumptions=dict(gravity="disabled to isolate insertion axis", driven_dofs=1, robot_or_grasp=False,
            drive_force_limit_N=2, module_mass_kg=.02, friction=.2, compliant_lip_stiffness_Nm_rad=stiffness if mode == "split_compliant" else None,
            compliant_lip="unvalidated whole-lip hinge hypothesis, including rolled seam and ribs" if mode == "split_compliant" else None,
            socket_lip_self_collision="not enabled; independent geometry audit needed for deforming assembly"))
    (output / "probe_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def contacts(model, data, manifest):
    result = []
    for c in data.contact:
        names = [model.geom(int(i)).name for i in c.geom]
        rec = [manifest["mappings"].get(n) for n in names]
        if all(rec) and rec[0]["kind"] != rec[1]["kind"]:
            result.append(dict(parts=[r["part"] for r in rec], gap_mm=float(c.dist * 1000), position_mm=(c.pos * 1000).tolist()))
    return result


def run_probe(directory, *, render=False, target_depth_mm=54., timestep=None):
    directory = Path(directory)
    manifest = json.loads((directory / "probe_manifest.json").read_text())
    model = mujoco.MjModel.from_xml_path(str(directory / "scene.xml"))
    if timestep is not None:
        model.opt.timestep = timestep
    data = mujoco.MjData(model)
    q = model.jnt_qposadr[model.joint("insertion").id]
    mujoco.mj_forward(model, data)
    rows, first, worst_gap = [], None, 0.
    duration = (target_depth_mm - manifest["start_depth_mm"]) / 10 + 1
    interval = round(.02 / model.opt.timestep)
    renderer = mujoco.Renderer(model, height=600, width=900) if render else None
    frames = []
    try:
        for step in range(round(duration / model.opt.timestep)):
            desired = min(target_depth_mm - manifest["start_depth_mm"], data.time * 10) / 1000
            data.ctrl[0] = desired
            mujoco.mj_step(model, data)
            if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():
                raise RuntimeError("nonfinite insertion dynamics")
            cs = contacts(model, data, manifest)
            if cs:
                worst_gap = min(worst_gap, min(c["gap_mm"] for c in cs))
                if first is None:
                    first = dict(depth_mm=float(data.qpos[q] * 1000 + manifest["start_depth_mm"]), contacts=cs)
            if step % interval == 0:
                row = dict(time=float(data.time), commanded_depth_mm=float(desired * 1000 + manifest["start_depth_mm"]),
                    depth_mm=float(data.qpos[q] * 1000 + manifest["start_depth_mm"]),
                    force_N=float(data.actuator_force[0]), contacts=cs,
                    hinge_deg=float(np.rad2deg(data.joint("lip_hinge").qpos[0])) if manifest["mode"] == "split_compliant" else None)
                rows.append(row)
                if renderer is not None and len(rows) % 5 == 0:
                    camera = mujoco.MjvCamera()
                    camera.lookat[:] = [-.005, -.013, 0]
                    camera.distance, camera.azimuth, camera.elevation = .18, 125, -25
                    options = mujoco.MjvOption()
                    options.geomgroup[3:] = 0
                    renderer.update_scene(data, camera=camera, scene_option=options)
                    frames.append(renderer.render().copy())
        mujoco.mj_forward(model, data)
        final = float(data.qpos[q] * 1000 + manifest["start_depth_mm"])
        report = dict(mode=manifest["mode"], timestep=model.opt.timestep, commanded_depth_mm=target_depth_mm,
            final_depth_mm=final, expected_shoulder_mm=manifest["shoulder_depth_mm"],
            reached_shoulder=abs(final-manifest["shoulder_depth_mm"]) < .15,
            worst_contact_gap_mm=worst_gap, first_contact=first, final_contacts=contacts(model, data, manifest),
            max_depth_mm=max(r["depth_mm"] for r in rows), rows=rows,
            physical_realism_validated=False, scope="isolated axial contact test; no robot, elastic calibration or real-object verification")
        if manifest["mode"] == "split_compliant":
            report["hinge_range_observed_deg"] = [min(r["hinge_deg"] for r in rows), max(r["hinge_deg"] for r in rows)]
        destination = directory / ("dynamic_report.json" if timestep is None else "dynamic_refined_report.json")
        destination.write_text(json.dumps(report, indent=2) + "\n")
        if frames:
            import imageio.v2 as imageio
            imageio.imwrite(directory / "final.png", frames[-1])
            imageio.mimsave(directory / "insertion.gif", frames, duration=100, loop=0)
        print(json.dumps({k: v for k, v in report.items() if k not in ("rows", "final_contacts", "first_contact")}), flush=True)
        return report
    finally:
        if renderer is not None:
            renderer.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mode", choices=("raw_hulls", "split_rigid", "split_compliant", "structural_diagnostic"), required=True)
    p.add_argument("--x-offset-mm", type=float, default=0.)
    p.add_argument("--yaw-deg", type=float, default=0.)
    p.add_argument("--render", action="store_true")
    args = p.parse_args()
    build_probe(args.inputs, args.cache, args.output, mode=args.mode, x_offset_mm=args.x_offset_mm, yaw_deg=args.yaw_deg)
    run_probe(args.output, render=args.render)


if __name__ == "__main__":
    main()
