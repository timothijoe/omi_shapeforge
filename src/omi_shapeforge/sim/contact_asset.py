"""Create SIM-OM001-OS001: a separate, explicitly simplified contact asset.

Reuse unmodified geometry envelopes and copy meshes into a NEW asset directory.
Replace the unaudited entrance assembly with seven bounded spring contacts.
This is an equivalent simulation mechanism, not a reconstruction of real EMI leaves.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from .mesh_audit import load_parts
from .mesh_contact_probe import SPRING_PARTS, numbers, piece_meshes


ASSET_ID = "SIM-OM001-OS001-r03"


def build_asset(inputs, cache, output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    inputs = Path(inputs).resolve()
    source, parts = load_parts(inputs)
    meshes = output / "meshes"
    meshes.mkdir()
    root = ET.Element("mujoco", model=ASSET_ID)
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep=".0002", gravity="0 0 0", integrator="implicitfast", iterations="80", tolerance="1e-10")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1200", offheight="900")
    ET.SubElement(visual, "map", znear=".0001")
    asset = ET.SubElement(root, "asset")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos=".1 .2 .25", dir="-.3 -.4 -1")
    socket = ET.SubElement(world, "body", name="sim_socket")
    start_depth = -3.
    tip = min(p["mesh"].bounds[0, 1] for p in parts["module"])
    shoulder = next(p["mesh"].bounds[0, 1] for p in parts["module"] if p["name"].startswith("11 Raised")) - tip
    module = ET.SubElement(world, "body", name="sim_module", pos=numbers([-.0005, (1.85 - tip - start_depth)/1000, .0007]))
    ET.SubElement(module, "joint", name="insertion", type="slide", axis="0 -1 0", damping=".1")
    ET.SubElement(module, "inertial", pos="0 0 0", mass=".02", diaginertia="8.3e-6 6e-7 8.8e-6")
    mappings, replaced = {}, []
    for kind, objects in parts.items():
        for part in objects:
            if kind == "socket" and part["index"] in SPRING_PARTS:
                replaced.append(part["name"])
                continue
            target = module if kind == "module" else socket
            name = f"sim_{kind}_{part['index']:03d}"
            shape = part["mesh"].copy()
            shape.vertices = shape.vertices / 1000
            path = meshes / f"{name}_visual.obj"
            shape.export(path)
            ET.SubElement(asset, "mesh", name=name + "_visual", file=str(path), inertia="shell")
            ET.SubElement(target, "geom", name=name + "_visual", type="mesh", mesh=name + "_visual",
                mass="0", contype="0", conaffinity="0", group="1", rgba=numbers(part["colors"].mean(0)))
            pieces, method = piece_meshes(part, kind, Path(cache), True)
            for i, piece in enumerate(pieces):
                key = f"{name}_collision_{i:03d}"
                copy = piece.copy()
                copy.vertices = copy.vertices / 1000
                path = meshes / f"{key}.obj"
                copy.export(path)
                ET.SubElement(asset, "mesh", name=key, file=str(path), inertia="shell")
                ET.SubElement(target, "geom", name=key, type="mesh", mesh=key, group="3", mass="0",
                    contype="2" if kind == "module" else "1", conaffinity="5" if kind == "module" else "6",
                    friction=".2 .001 .0001", solref=".002 1", solimp=".99 .99 .0001", condim="3")
                mappings[key] = dict(kind=kind, part=part["name"], method=method)
    pads = []
    for i, x in enumerate(np.linspace(-.0082, .0072, 7)):
        # The rounded pad starts 0.219 mm above the module's lower surface.
        # Limit stroke to 0.27 mm: the original floor ribs reach -4.0 mm,
        # so even at full travel the pad retains 0.03 mm static clearance.
        body = ET.SubElement(socket, "body", name=f"compliant_pad_{i}", pos=numbers([x, 0, -.00335]))
        ET.SubElement(body, "joint", name=f"pad_slide_{i}", type="slide", axis="0 0 -1",
            range="0 .00027", stiffness="100", damping=".63", solreflimit=".0004 1", solimplimit=".99999 .99999 .0001")
        ET.SubElement(body, "inertial", pos="0 0 0", mass=".001", diaginertia="4.9e-11 4.9e-11 4.9e-11")
        ET.SubElement(body, "geom", name=f"pad_contact_{i}", type="sphere",
            size=".00035", contype="4", conaffinity="3", group="2", mass="0", rgba=".95 .55 .08 1",
            friction=".2 .001 .0001", condim="3", solref=".002 1", solimp=".99 .99 .0001")
        mappings[f"pad_contact_{i}"] = dict(kind="pad", part=f"equivalent spring contact {i}", method="bounded passive slide")
        pads.append(dict(name=f"compliant_pad_{i}", center_m=[float(x), 0., -.00335], radius_m=.00035,
                         stroke_m=.00027, stiffness_N_m=100, damping_Ns_m=.63,
                         minimum_floor_gap_over_full_stroke_m=.00013,minimum_rib_gap_over_full_stroke_m=.00003))
    actuators = ET.SubElement(root, "actuator")
    ET.SubElement(actuators, "position", name="drive", joint="insertion", kp="2000", kv="10", forcerange="-2 2")
    ET.indent(root)
    ET.ElementTree(root).write(output / "scene.xml", encoding="unicode")
    mujoco.MjModel.from_xml_path(str(output / "scene.xml"))
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(meshes.glob("*.obj"))}
    report = dict(asset_id=ASSET_ID, source_inputs=str(inputs), source_assets={k: source[k]["source"] for k in parts},
        source_sha256={k: source[k]["source_sha256"] for k in parts}, source_authoring_modified=False,
        scene_sha256=hashlib.sha256((output / "scene.xml").read_bytes()).hexdigest(), mesh_sha256=hashes,
        start_depth_mm=start_depth, leading_tip_y_mm=float(tip), mouth_y_mm=1.85, shoulder_depth_mm=float(shoulder),
        nominal_module_center_xz_mm=[-.5, .7], channel_width_mm=19., channel_height_mm=9.6,
        replaced_entrance_parts=replaced, replacement="seven equivalent spherical spring contacts with finite vertical travel; contact mass 1g each is a numerical modeling assumption",
        pads=pads, mappings=mappings,
        assumptions=dict(module_mass_kg=.02, friction=.2, contact_stiffness_calibrated=False,
            geometry_role="separate simulation approximation; original V3/r04 geometry files retained",
            socket_pad_self_collision=True, module_pad_contact=True, cavity_collisions=True,
            actual_grasp=False, electrical_seating=False))
    (output / "asset_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(build_asset(a.inputs, a.cache, a.output)["asset_id"])


if __name__ == "__main__":
    main()
