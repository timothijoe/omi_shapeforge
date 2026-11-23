"""Derive a dual-camera, rigid-held-module pre-insertion scene from the URDF MVP.

Camera mounts, grasp transform and support height are explicit simulation
assumptions. This task stops before the aperture and retains disabled contact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def numbers(value):
    return " ".join(map(str, np.asarray(value).ravel()))


def quaternion(rotation):
    result = np.empty(4)
    mujoco.mju_mat2Quat(result, np.asarray(rotation).ravel())
    return result


def camera_axes(eye, target, up):
    z = np.asarray(eye) - target  # MuJoCo looks down local -Z.
    z /= np.linalg.norm(z)
    x = np.cross(up, z)
    x /= np.linalg.norm(x)
    return np.r_[x, np.cross(z, x)]


def build_vision_scene(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    original = json.loads((source / "robot_manifest.json").read_text())
    root = ET.parse(source / "scene.xml").getroot()
    world = root.find("worldbody")
    module = world.find("body[@name='reference_module']")
    socket = world.find("body[@name='reference_socket']")
    if module is None or socket is None:
        raise ValueError("source scene must contain actual V3 and r04 reference meshes")
    output.mkdir(parents=True, exist_ok=False)
    mesh_dependencies = {}
    for mesh in root.findall("asset/mesh"):
        mesh.set("file", str((source / mesh.get("file")).resolve()))
        path = Path(mesh.get("file"))
        mesh_dependencies[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    model = mujoco.MjModel.from_xml_path(str(source / "scene.xml"))
    data = mujoco.MjData(model)
    data.qpos[:] = original["initial_qpos"]
    qids = [model.jnt_qposadr[model.joint(f"Arm_L{i}_Joint").id] for i in range(1, 8)]
    data.qpos[qids] += [.02, -.015, .01, 0, .01, 0, 0]
    mujoco.mj_forward(model, data)
    site = model.site("urdf_tcp_L").id
    goal_pos = data.site_xpos[site].copy()
    goal_rot = data.site_xmat[site].reshape(3, 3).copy()
    socket_rot = np.array([[0., -1, 0], [1, 0, 0], [0, 0, 1]])
    tool_rotation = goal_rot.T @ socket_rot
    # URDF TCP is at the flange: fingers span local Z=74..169 mm.
    # Place the module in their distal region, not inside the gripper palm.
    tool_position = np.array([0., 0., .14])
    # Source OBJ vertices already contain this reference assembly translation.
    baked_translation = np.array([-.0005, .041943169659, .0007])
    preinsert_translation = baked_translation.copy()  # tip 5 mm outside metal lip
    socket_position = goal_pos + goal_rot @ tool_position - socket_rot @ preinsert_translation
    tcp = root.find(".//body[@name='TCP_Link_L']")
    world.remove(module)
    tcp.append(module)
    module.set("name", "held_module")
    module.set("pos", numbers(tool_position - tool_rotation @ baked_translation))
    module.set("quat", numbers(quaternion(tool_rotation)))
    socket.set("pos", numbers(socket_position))
    socket.set("quat", numbers(quaternion(socket_rot)))
    goal = world.find("site[@name='reach_goal']")
    goal.set("pos", numbers(goal_pos))
    goal.set("rgba", "0 0 0 0")
    for side in ("L", "R"):
        root.find(f".//site[@name='urdf_tcp_{side}']").set("rgba", "0 0 0 0")
    # Keep the socket support on the table, using the imported geometry's bounds.
    old_z = float(world.find("geom[@name='work_table']").get("pos").split()[2])
    old_socket_z = float(model.body("reference_socket").pos[2])
    table_z = old_z + socket_position[2] - old_socket_z
    world.find("geom[@name='work_table']").set("pos", numbers([socket_position[0], socket_position[1], table_z]))
    world.find("geom[@name='table_leg']").set("pos", numbers([socket_position[0], socket_position[1], table_z / 2]))
    world.find("geom[@name='table_leg']").set("size", numbers([.045, table_z / 2]))
    focus = socket_position + socket_rot @ np.array([-.0005, .01, .015])
    head_eye = focus + np.array([-.22, -.22, .26])
    base = root.find(".//body[@name='ZJ_Robot_link']")
    base_id = model.body("ZJ_Robot_link").id
    base_r = data.xmat[base_id].reshape(3, 3)
    head_local = base_r.T @ (head_eye - data.xpos[base_id])
    focus_local = base_r.T @ (focus - data.xpos[base_id])
    ET.SubElement(base, "camera", name="head_rgb", pos=numbers(head_local),
                  xyaxes=numbers(camera_axes(head_local, focus_local, base_r.T @ [0., 0, 1])), fovy="42")
    wrist_eye = np.array([.10, -.06, .07])
    wrist_target = goal_rot.T @ (focus - goal_pos)
    ET.SubElement(tcp, "camera", name="wrist_rgb", pos=numbers(wrist_eye),
                  xyaxes=numbers(camera_axes(wrist_eye, wrist_target, goal_rot.T @ [0., 0, 1])), fovy="68")
    root.find("visual").append(ET.Element("map", znear="0.001"))
    ET.indent(root)
    ET.ElementTree(root).write(output / "scene.xml", encoding="unicode")
    mujoco.MjModel.from_xml_path(str(output / "scene.xml"))
    report = dict(original, scene=str(output / "scene.xml"),
        scene_sha256=hashlib.sha256((output / "scene.xml").read_bytes()).hexdigest(),
        parent_scene=str(source / "scene.xml"), parent_scene_sha256=hashlib.sha256((source / "scene.xml").read_bytes()).hexdigest(),
        task="rigid-held-module-preinsert-v1", mesh_dependencies_sha256=mesh_dependencies,
        goal_tcp_position=goal_pos.tolist(),
        goal_tcp_rotation=goal_rot.tolist(), tool_to_module=dict(position_m=tool_position.tolist(),
        rotation=tool_rotation.tolist()), socket_to_world=dict(position_m=socket_position.tolist(), rotation=socket_rot.tolist()),
        module_mesh_baked_translation_m=baked_translation.tolist(), preinsert_tip_gap_m=.005,
        cameras=dict(head_rgb=dict(parent="ZJ_Robot_link", position_m=head_local.tolist(), fovy_degrees=42),
                     wrist_rgb=dict(parent="TCP_Link_L", position_m=wrist_eye.tolist(), fovy_degrees=68)),
        scope="uncontacted pre-insertion reach with rigid visual attachment; uncalibrated grasp and pinhole camera mounts; no elastic insertion",
        grasp="fixed TCP child, not a contact grasp", camera_calibrated=False)
    (output / "robot_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build_vision_scene(a.source, a.output), indent=2))


if __name__ == "__main__":
    main()
