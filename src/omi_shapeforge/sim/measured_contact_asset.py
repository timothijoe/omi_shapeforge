"""Build a separate V4 contact rig with measured throat dimensions.

Only cage-related socket geometry is reshaped; fixture/PCB/support stay fixed.
Input meshes and historical simulation assets are never overwritten.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
import trimesh

from .mesh_contact_probe import numbers


def clip_proxy_to_bounds(proxy, bounds):
    """Remove decomposition inflation beyond the source's exact outer bounds."""
    result = proxy.copy()
    for axis in range(3):
        for side, sign in ((0, 1.), (1, -1.)):
            if not len(result.vertices):
                return None
            limit = bounds[side, axis]
            outside = (result.vertices[:, axis] - limit) * sign < -1e-12
            if not outside.any():
                continue
            normal, origin = np.zeros(3), np.zeros(3)
            normal[axis], origin[axis] = sign, limit
            result = trimesh.intersections.slice_mesh_plane(result, normal, origin, cap=False)
            # Cap each cut before applying the next plane. Otherwise a proxy
            # surrounding the entire source box can lose every original face.
            if len(result.vertices) < 4 or np.linalg.matrix_rank(
                    result.vertices-result.vertices.mean(axis=0), tol=1e-12) < 3:
                return None
            result = result.convex_hull
    if len(result.vertices) < 4:
        return None
    result = result.convex_hull
    if result.volume < 1e-18:
        return None
    return result


def socket_vertices(vertices, *, width_mm, height_mm, center_x_mm):
    """Continuous monotone mapping, preserving sheet thickness beyond throat."""
    v = np.asarray(vertices, dtype=float).copy() * 1000
    u = v[:, 0] + .5
    half = width_mm / 2
    v[:, 0] = center_x_mm + np.where(
        np.abs(u) <= 9.5, u * half / 9.5,
        np.sign(u) * (half + np.abs(u) - 9.5))
    z = v[:, 2]
    v[:, 2] = np.where(z < -4.1, z, np.where(
        z <= 5.5, -4.1 + (z + 4.1) * height_mm / 9.6,
        z + height_mm - 9.6))
    return v / 1000


def build(parent_asset, module_asset, decomposition, output, *, asset_id,
          width_mm=18.8, height_mm=8.8, front_left_margin_mm=6.9):
    parent_asset, module_asset, decomposition, output = map(
        lambda p: Path(p).resolve(), (parent_asset, module_asset, decomposition, output))
    if not (width_mm > 18.1 and height_mm > 8.2 and front_left_margin_mm > 0):
        raise ValueError("invalid measured throat or side margin")
    parent = json.loads((parent_asset / "asset_manifest.json").read_text())
    source = json.loads((module_asset / "asset_manifest.json").read_text())
    cache = json.loads((decomposition / "manifest.json").read_text())
    if len(cache) != len(source["parts"]):
        raise ValueError("incomplete module decomposition")
    protected = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                 for folder in (parent_asset, module_asset)
                 for p in folder.rglob("*") if p.is_file()}
    output.mkdir(parents=True, exist_ok=False)
    folder = output / "meshes"
    folder.mkdir()
    root = ET.parse(parent_asset / "scene.xml").getroot()
    root.set("model", asset_id)
    asset = root.find("asset")
    old_assets = list(asset)
    asset.clear()
    socket = root.find("worldbody/body[@name='sim_socket']")
    for body in list(socket.findall("body")):
        socket.remove(body)
    module = root.find("worldbody/body[@name='sim_module']")
    module.clear()
    module.set("name", "sim_module")
    ET.SubElement(module, "joint", name="insertion", type="slide", axis="0 -1 0", damping=".1")
    ET.SubElement(module, "inertial", pos="0 0 0", mass=".02", diaginertia="8.3e-6 6e-7 8.8e-6")
    # Looking into the mouth from +Y, screen-left is socket +X.
    outer_edge_x = 16.0  # Existing printed frame outer edge, retained unchanged.
    center_x = outer_edge_x - front_left_margin_mm - width_mm / 2
    names = {k.split("_collision_")[0]: v["part"] for k, v in parent["mappings"].items()
             if k.startswith("sim_socket_")}
    changed, mappings, bounds = [], {}, {}
    def is_cage(name):
        return name.startswith(("Cage ", "Dark insert", "Lower mouth rolled", "Embossed mouth floor",
                                "Folded vertical mouth", "Pressed side seam"))
    for old in old_assets:
        key = old.get("name", "")
        if not key.startswith("sim_socket_"):
            continue
        base = key.split("_collision_")[0].removesuffix("_visual")
        part_name = names[base]
        mesh = trimesh.load(old.get("file"), force="mesh", process=False)
        if is_cage(part_name):
            mesh.vertices = socket_vertices(mesh.vertices, width_mm=width_mm,
                height_mm=height_mm, center_x_mm=center_x)
            if "_collision_" in key:
                mesh = mesh.convex_hull
            changed.append(key)
        path = folder / (key + ".obj")
        mesh.export(path)
        item = deepcopy(old)
        item.set("file", str(path))
        asset.append(item)
        if key.endswith("_visual"):
            bounds[part_name] = (mesh.bounds * 1000).tolist()
        if "_collision_" in key:
            mappings[key] = dict(parent["mappings"][key],
                measured_channel_transform=is_cage(part_name))
    # Keep the unmeasured dark support. Center the module in the tightest
    # retained vertical corridor, rather than silently deleting this obstacle.
    ceiling = -4.1 + height_mm
    internal_floor = bounds["Dark insert inside cage"][1][2]
    center_z = (ceiling + internal_floor) / 2
    if ceiling - internal_floor <= 8.2:
        raise ValueError("retained internal support leaves no 8.2mm module corridor")
    tip, shoulder_y = np.inf, None
    proxy_bounds_audit = []
    for i, part in enumerate(source["parts"]):
        rec = cache[i]
        if rec["index"] != i or rec["source_sha256"] != hashlib.sha256(Path(part["mesh"]).read_bytes()).hexdigest():
            raise ValueError("decomposition does not match module source")
        mesh = trimesh.load(part["mesh"], force="mesh", process=False)
        tip = min(tip, mesh.bounds[0, 1] * 1000)
        if part["name"].startswith("11 Raised"):
            shoulder_y = mesh.bounds[0, 1] * 1000
        key = f"sim_module_{i:03d}"
        path = folder / (key + "_visual.obj")
        path.write_bytes(Path(part["mesh"]).read_bytes())
        ET.SubElement(asset, "mesh", name=key+"_visual", file=str(path), inertia="shell")
        ET.SubElement(module, "geom", name=key+"_visual", type="mesh", mesh=key+"_visual",
                      group="1", mass="0", contype="0", conaffinity="0", rgba=numbers(part["color"]))
        files = sorted((decomposition / f"{i:03d}").glob("*.obj"))
        if len(files) != rec["pieces"]:
            raise ValueError("missing collision pieces")
        for j, src in enumerate(files):
            name = key + f"_collision_{j:03d}"
            raw = trimesh.load(src, force="mesh", process=False)
            bounded = clip_proxy_to_bounds(raw, mesh.bounds)
            excursion = float(max(np.max(mesh.bounds[0]-raw.bounds[0]),np.max(raw.bounds[1]-mesh.bounds[1]),0.)*1000)
            proxy_bounds_audit.append(dict(geom=name,raw_bound_excess_mm=excursion,
                retained=bounded is not None,source_part=part["name"]))
            if bounded is None:
                continue
            path = folder / (name + ".obj")
            bounded.export(path)
            ET.SubElement(asset, "mesh", name=name, file=str(path), inertia="shell")
            ET.SubElement(module, "geom", name=name, mesh=name, type="mesh", group="3", mass="0",
                          contype="2", conaffinity="5", friction=".2 .001 .0001", condim="3",
                          solref=".002 1", solimp=".99 .99 .0001")
            mappings[name] = dict(kind="module", part=part["name"], method=rec["method"]+"; clipped to exact source outer bounds")
    if shoulder_y is None:
        raise ValueError("module shoulder not identified")
    start, mouth = -3.0, parent["mouth_y_mm"]
    module.set("pos", numbers([center_x/1000, (mouth-tip-start)/1000, center_z/1000]))
    # Equivalent contact parameters are hypotheses, fitted to available geometric
    # room; they are not physical EMI-leaf identification.
    radius, stroke, preload = .15, .15, .10  # mm
    pad_z = center_z - 4.1 + preload - radius
    pads = []
    for i, x in enumerate(np.linspace(center_x-7.7, center_x+7.7, 7)):
        body = ET.SubElement(socket, "body", name=f"compliant_pad_{i}", pos=numbers([x/1000, 0, pad_z/1000]))
        ET.SubElement(body, "joint", name=f"pad_slide_{i}", type="slide", axis="0 0 -1", range=numbers([0,stroke/1000]),
                      stiffness="100", damping=".63", solreflimit=".0004 1", solimplimit=".99999 .99999 .0001")
        ET.SubElement(body, "inertial", pos="0 0 0", mass=".001", diaginertia="4.9e-11 4.9e-11 4.9e-11")
        ET.SubElement(body, "geom", name=f"pad_contact_{i}", type="sphere", size=str(radius/1000),
                      contype="4", conaffinity="3", group="2", mass="0", rgba=".95 .55 .08 1",
                      friction=".2 .001 .0001", condim="3", solref=".002 1", solimp=".99 .99 .0001")
        mappings[f"pad_contact_{i}"] = dict(kind="pad", part=f"equivalent spring contact {i}", method="bounded passive slide")
        pads.append(dict(name=f"compliant_pad_{i}", center_m=[float(x/1000),0.,pad_z/1000], radius_m=radius/1000,
                         stroke_m=stroke/1000, stiffness_N_m=100., damping_Ns_m=.63))
    ET.indent(root)
    ET.ElementTree(root).write(output / "scene.xml", encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(output / "scene.xml"))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    static = [g for g in range(model.ngeom) if model.geom(g).name.startswith("sim_socket_")
              and "_collision_" in model.geom(g).name]
    for i, pad in enumerate(pads):
        geom = model.geom(f"pad_contact_{i}").id
        gap = min(mujoco.mj_geomDistance(model,data,geom,h,.01,np.zeros(6)) for h in static)
        pad["rest_minimum_static_gap_m"] = float(gap)
        pad["minimum_static_gap_bound_over_full_stroke_m"] = float(gap-stroke/1000)
        q = model.jnt_qposadr[model.joint(f"pad_slide_{i}").id]
        data.qpos[q] = stroke/1000
    mujoco.mj_forward(model,data)
    for i,pad in enumerate(pads):
        geom = model.geom(f"pad_contact_{i}").id
        pad["minimum_static_gap_at_full_stroke_m"] = float(min(
            mujoco.mj_geomDistance(model,data,geom,h,.01,np.zeros(6)) for h in static))
        if pad["minimum_static_gap_bound_over_full_stroke_m"] <= .000025:
            raise ValueError("insufficient conservative static pad clearance")
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    report = dict(asset_id=asset_id, parent_asset=parent["asset_id"], module_asset="OM-001/V4 r05 双窗尾槽版",
        source_assets=dict(module=source["files"]["blend"], socket=parent["source_assets"]["socket"]),
        protected_sha256=protected, source_authoring_modified=False, scene_sha256=hashlib.sha256((output/"scene.xml").read_bytes()).hexdigest(),
        mesh_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob("*.obj")},
        start_depth_mm=start, leading_tip_y_mm=float(tip), mouth_y_mm=mouth, shoulder_depth_mm=float(shoulder_y-tip),
        nominal_module_center_xz_mm=[center_x,center_z], channel_width_mm=width_mm, channel_height_mm=height_mm,
        channel_inner_x_mm=[center_x-width_mm/2,center_x+width_mm/2],channel_inner_z_mm=[-4.1,ceiling],
        front_left_margin_mm=front_left_margin_mm, front_left_margin_interpretation="viewed from +Y into mouth: +X inner metal wall to printed-frame +X outer edge at 16mm; user measurement location not separately confirmed",
        retained_internal_support_top_z_mm=internal_floor, nominal_internal_vertical_margin_per_side_mm=(ceiling-internal_floor-8.2)/2,
        changed_socket_meshes=changed, socket_visual_bounds_mm=bounds, module_decomposition=cache,
        module_proxy_outer_bounds_audit=proxy_bounds_audit,
        pads=pads,pad_rest_static_gap_mm=[p["rest_minimum_static_gap_m"]*1000 for p in pads],
        mappings=mappings, replaced_entrance_parts=parent["replaced_entrance_parts"],
        assumptions=dict(module_mass_kg=.02,friction=.2,contact_stiffness_calibrated=False,
            replacement="seven equivalent spherical contacts; radius .15mm, travel .15mm, nominal preload .10mm; 1g per contact numerical assumption",
            socket_port_transform="inner cross-section compressed, external sheet thickness retained; only cage-related parts modified; internal support retained",
            fixture_frame_unchanged=True, pcb_and_stand_unchanged=True, plug_fixed_to_module=True,
            actual_grasp=False,electrical_seating=False))
    (output/"asset_manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("parent-asset","module-asset","decomposition","output"):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--asset-id',required=True,help='Explicit new simulation revision identity')
    p.add_argument('--front-left-margin-mm',type=float,default=6.9)
    a=p.parse_args()
    r=build(a.parent_asset,a.module_asset,a.decomposition,a.output,asset_id=a.asset_id,front_left_margin_mm=a.front_left_margin_mm)
    print(json.dumps({k:r[k] for k in ('asset_id','channel_inner_x_mm','channel_inner_z_mm','nominal_module_center_xz_mm','nominal_internal_vertical_margin_per_side_mm','pad_rest_static_gap_mm')},indent=2))


if __name__=='__main__':main()
