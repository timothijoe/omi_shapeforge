"""Mount the separately authored contact asset in the real URDF camera scene."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from .vision_scene import numbers, quaternion


TASK = "sim-contact-insertion-v1"


def build(source, contact_asset, output):
    source, contact_asset, output = map(lambda x: Path(x).resolve(), (source, contact_asset, output))
    original = json.loads((source / "robot_manifest.json").read_text())
    contact = json.loads((contact_asset / "asset_manifest.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    root = ET.parse(source / "scene.xml").getroot()
    asset_root = ET.parse(contact_asset / "scene.xml").getroot()
    world = root.find("worldbody")
    old_model = mujoco.MjModel.from_xml_path(str(source / "scene.xml"))
    # These URDF collision meshes are not yet a calibrated contact-grasp model.
    # Explicitly restrict this milestone to module/socket/table/pad contact.
    for geom in root.findall(".//geom"):
        geom.set("contype", "0");geom.set("conaffinity", "0")
    for name in ("floor", "work_table", "table_leg"):
        geom = root.find(f".//geom[@name='{name}']")
        geom.set("contype", "1");geom.set("conaffinity", "6")
    old_socket = world.find("body[@name='reference_socket']")
    tcp = root.find(".//body[@name='TCP_Link_L']")
    tcp.remove(tcp.find("body[@name='held_module']"))
    world.remove(old_socket)
    assets = root.find("asset")
    for mesh in list(assets):
        if mesh.tag == "mesh" and mesh.get("name", "").startswith("optical_"):
            assets.remove(mesh)
        elif mesh.get("file"):
            mesh.set("file", str((source / mesh.get("file")).resolve()))
    for mesh in asset_root.find("asset"):
        assets.append(deepcopy(mesh))
    socket = deepcopy(asset_root.find("worldbody/body[@name='sim_socket']"))
    socket.set("pos", old_socket.get("pos"));socket.set("quat", old_socket.get("quat"))
    for body in socket.iter("body"):
        body.set("gravcomp", "1")
    world.append(socket)
    module = deepcopy(asset_root.find("worldbody/body[@name='sim_module']"))
    module.remove(module.find("joint"))
    module.set("pos", numbers(original["tool_to_module"]["position_m"]))
    module.set("quat", numbers(quaternion(np.array(original["tool_to_module"]["rotation"]))))
    module.set("gravcomp", "1")
    tcp.append(module)
    option = root.find("option")
    option.set("timestep", ".0002");option.set("iterations", "80");option.set("tolerance", "1e-9")
    flag = option.find("flag")
    if flag is not None: flag.set("contact", "enable")
    R = np.array(original["socket_to_world"]["rotation"])
    old_center = np.asarray(original.get("nominal_module_center_xz_mm", [-.5, .7]), dtype=float)
    new_center = np.asarray(contact.get("nominal_module_center_xz_mm", [-.5, .7]), dtype=float)
    delta_center = new_center - old_center
    pre = np.array(original["goal_tcp_position"]) + R @ [delta_center[0]/1000, 0., delta_center[1]/1000]
    seating = pre + R @ [0., -(contact["shoulder_depth_mm"] + 5.)/1000, 0.]
    goal = seating + R @ [0., -.00015, 0.]
    root.find(".//site[@name='reach_goal']").set("pos", numbers(goal))
    ET.indent(root)
    ET.ElementTree(root).write(output / "scene.xml", encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(output / "scene.xml"))
    initial = np.zeros(model.nq)
    for i in range(old_model.njnt):
        name = old_model.joint(i).name
        initial[model.jnt_qposadr[model.joint(name).id]] = original["initial_qpos"][old_model.jnt_qposadr[i]]
    # The preinsert target in the parent scene was authored with this known
    # joint offset. Start at that pose; subsequent movement is always dynamic.
    for i, delta in enumerate([.02, -.015, .01, 0, .01, 0, 0], 1):
        initial[model.jnt_qposadr[model.joint(f"Arm_L{i}_Joint").id]] += delta
    manifest = dict(original, task=TASK, initial_qpos=initial.tolist(), goal_tcp_position=goal.tolist(),
        preinsert_tcp_position=pre.tolist(), seated_tcp_position=seating.tolist(),
        asset_id=contact["asset_id"], contact_asset_dir=str(contact_asset),
        contact_asset_manifest_sha256=hashlib.sha256((contact_asset / "asset_manifest.json").read_bytes()).hexdigest(),
        leading_tip_y_mm=contact["leading_tip_y_mm"], mouth_y_mm=contact["mouth_y_mm"],
        nominal_module_center_xz_mm=new_center.tolist(),
        pad_rest_static_gap_mm=contact.get("pad_rest_static_gap_mm", [.4] * 7),
        channel_width_mm=contact["channel_width_mm"],channel_height_mm=contact["channel_height_mm"],
        shoulder_depth_mm=contact["shoulder_depth_mm"], scene=str(output / "scene.xml"),
        scene_sha256=hashlib.sha256((output / "scene.xml").read_bytes()).hexdigest(),
        mesh_dependencies_sha256={mesh.get("file"): hashlib.sha256(Path(mesh.get("file")).read_bytes()).hexdigest()
                                  for mesh in root.findall("asset/mesh")},
        contacts_enabled=True, robot_self_collision_validated=False, contact_grasp_validated=False,
        scope="real URDF and fixed attachment with new equivalent spring-contact asset; module/socket/table contacts active; URDF self-contact and physical grasp unvalidated",
        success="within 0.15mm of shoulder, lateral error<0.35mm, rotation<0.01rad, shoulder contact and 3 stable control samples")
    (output / "robot_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--asset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(build(a.source,a.asset,a.output)['scene'])


if __name__=='__main__':main()
