"""Import the supplied dual-arm URDF into an isolated MuJoCo prototype scene."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def build_robot_scene(source, output, optical_inputs=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    robot = ET.parse(source).getroot()
    package_root = source.parents[1]
    mesh_hashes = {}
    for mesh in robot.findall(".//mesh"):
        uri = mesh.get("filename")
        if uri.startswith("package://"):
            package, relative = uri[len("package://"):].split("/", 1)
            if package != package_root.name:
                raise ValueError(f"Unmapped URDF package: {package}")
            path = package_root / relative
        else:
            path = source.parent / uri
        path = path.resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        mesh.set("filename", str(path))
        mesh_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    removed = []
    for link in robot.findall("link"):
        if link.get("name") in ("TCP_Link_L", "TCP_Link_R"):
            for child in list(link):
                if child.tag in ("visual", "collision"):
                    link.remove(child)
                    removed.append(f"{link.get('name')}/{child.tag}")
    extension = ET.SubElement(robot, "mujoco")
    ET.SubElement(extension, "compiler", discardvisual="false", fusestatic="false", strippath="false")
    ET.ElementTree(robot).write(output / "resolved.urdf", encoding="unicode")
    imported = mujoco.MjModel.from_xml_path(str(output / "resolved.urdf"))
    mujoco.mj_saveLastXML(str(output / "imported.xml"), imported)
    root = ET.parse(output / "imported.xml").getroot()
    option = ET.SubElement(root, "option", timestep="0.002", integrator="implicitfast")
    ET.SubElement(option, "flag", contact="disable")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="1200", offheight="900")
    for body in root.findall(".//body"):
        body.set("gravcomp", "1")
        for geom in body.findall("geom"):
            if geom.get("contype") == "0":
                geom.set("rgba", ".82 .85 .87 1")
            else:
                geom.set("group", "3")
        for joint in body.findall("joint"):
            joint.set("damping", "1")
            joint.set("armature", ".01")
    for side in ("L", "R"):
        body = root.find(f".//body[@name='TCP_Link_{side}']")
        if body is None:
            raise ValueError("URDF TCP frame was lost during import")
        ET.SubElement(body, "site", name=f"urdf_tcp_{side}", size=".008", rgba="1 .2 .1 1")
    actuators = ET.SubElement(root, "actuator")
    for index in range(imported.njnt):
        name = mujoco.mj_id2name(imported, mujoco.mjtObj.mjOBJ_JOINT, index)
        slide = imported.jnt_type[index] == mujoco.mjtJoint.mjJNT_SLIDE
        limit = imported.jnt_range[index]
        source_joint = robot.find(f"joint[@name='{name}']/limit")
        effort = float(source_joint.get("effort", "30"))
        ET.SubElement(actuators, "position", name="servo_" + name, joint=name,
                      kp="200" if slide else "400", kv="10" if slide else "40",
                      ctrlrange=" ".join(map(str, limit)), forcerange=f"{-effort} {effort}")
    world = root.find("worldbody")
    ET.SubElement(world, "light", pos="0.5 0.2 2.5", dir="0 0 -1")
    ET.SubElement(world, "geom", name="floor", type="plane", size="2 2 .05", rgba=".35 .38 .40 1")
    ET.SubElement(world, "geom", name="work_table", type="cylinder", pos=".65 .15 .735", size=".32 .015", rgba=".75 .76 .73 1")
    ET.SubElement(world, "geom", name="table_leg", type="cylinder", pos=".65 .15 .36", size=".045 .36", rgba=".10 .11 .12 1")
    ET.SubElement(world, "site", name="reach_goal", pos=".5 .25 .95", size=".012", rgba=".1 .9 .3 .6")
    asset = root.find("asset")
    displayed = []
    if optical_inputs is not None:
        optical_inputs = Path(optical_inputs).resolve()
        manifest = json.loads((optical_inputs / "manifest.json").read_text())
        meshes = output / "optical_meshes"
        meshes.mkdir()
        stand_min = min(p["bounds_mm"][0][2] for p in manifest["socket"]["parts"])
        z_origin = .751 - stand_min / 1000
        for kind in ("socket", "module"):
            body = ET.SubElement(world, "body", name=f"reference_{kind}", pos=f".69 .23 {z_origin}", quat=".7071067812 0 0 .7071067812")
            for index, part in enumerate(manifest[kind]["parts"]):
                data = np.load(optical_inputs / kind / part["file"])
                vertices = data["vertices"].copy() / 1000
                if kind == "module":
                    vertices += [-.0005, .041943169659, .0007]
                filename = meshes / f"{kind}_{index:03d}.obj"
                with filename.open("w") as stream:
                    for v in vertices:
                        stream.write("v " + " ".join(map(str, v)) + "\n")
                    for f in data["faces"]:
                        stream.write("f " + " ".join(str(int(i) + 1) for i in f) + "\n")
                name = f"optical_{kind}_{index}"
                ET.SubElement(asset, "mesh", name=name, file=str(filename), inertia="shell")
                rgba = np.mean(data["face_colors"], axis=0)
                ET.SubElement(body, "geom", name=name, type="mesh", mesh=name, contype="0", conaffinity="0",
                              group="1", mass="0", rgba=" ".join(map(str, rgba)))
                displayed.append(part["name"])
    ET.indent(root)
    path = output / "scene.xml"
    ET.ElementTree(root).write(path, encoding="unicode")
    model = mujoco.MjModel.from_xml_path(str(path))
    data = mujoco.MjData(model)
    for side, pose in [("L", [.45, -.6, 0, -1.4, 0, 0, 0]), ("R", [0, -.6, 0, -1.0, 0, 0, 0])]:
        for index, q in enumerate(pose, 1):
            joint = model.joint(f"Arm_{side}{index}_Joint").id
            data.qpos[model.jnt_qposadr[joint]] = q
    mujoco.mj_forward(model, data)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    report = {"source_urdf": str(source), "source_sha256": original_hash, "source_unchanged": True,
              "scene": str(path), "joints": model.njnt, "actuators": model.nu, "mimic_equalities": model.neq,
              "removed_zero_volume_markers": removed, "tcp_frames_retained": True,
              "initial_qpos": data.qpos.tolist(), "active_arm": "URDF L; A-arm identity not physically calibrated",
              "optical_visual_parts": len(displayed), "mesh_sources_sha256": mesh_hashes,
              "optical_inputs": str(optical_inputs) if optical_inputs is not None else None,
              "optical_input_manifest_sha256": hashlib.sha256((optical_inputs / "manifest.json").read_bytes()).hexdigest() if optical_inputs is not None else None,
              "scope": "real URDF joint model and geometry with assumed position servos, gravity compensation and contacts disabled; optical assets are static references, not grasped",
              "robot_contact_validated": False, "tcp_tool_offset_calibrated": False,
              "photo_layout_metric_calibration": False,
              "scene_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    (output / "robot_manifest.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--urdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--optical-inputs", type=Path)
    args = parser.parse_args()
    report = build_robot_scene(args.urdf, args.output, args.optical_inputs)
    print(json.dumps({k: v for k, v in report.items() if k != "mesh_sources_sha256"}, indent=2))


if __name__ == "__main__":
    main()
