"""Small native MJCF scene: open primitive channel and held module proxy."""
import xml.etree.ElementTree as ET

from .config import InsertionConfig


def _numbers(values):
    return " ".join(f"{float(v):.10g}" for v in values)


def make_scene(config: InsertionConfig) -> str:
    c = config
    root = ET.Element("mujoco", model="shapeforge_insertion_interface_v0")
    ET.SubElement(root, "compiler", angle="radian", autolimits="true")
    ET.SubElement(root, "option", timestep=str(c.timestep_s), integrator="implicitfast", iterations="80")
    visual = ET.SubElement(root, "visual")
    ET.SubElement(visual, "global", offwidth="960", offheight="720")
    defaults = ET.SubElement(root, "default")
    ET.SubElement(defaults, "geom", friction="0.4 0.005 0.0001", solref="0.01 1", condim="3")
    world = ET.SubElement(root, "worldbody")
    ET.SubElement(world, "light", pos="0.1 0.1 0.5", dir="0 0 -1")
    ET.SubElement(world, "camera", name="overview", pos=".27 .32 .29", xyaxes="-.764 .645 0 -.25 -.296 .922")

    def box(parent, name, pos, halfsize, rgba, collide=True, mass=None):
        attributes = dict(name=name, type="box", pos=_numbers(pos), size=_numbers(halfsize), rgba=rgba)
        if not collide:
            attributes.update(contype="0", conaffinity="0")
        if mass is not None:
            attributes["mass"] = str(mass)
        return ET.SubElement(parent, "geom", **attributes)

    box(world, "table", [0, 0, -.012], [.20, .18, .012], ".70 .72 .71 1")
    # Open-sided support proxy, for layout context only.
    for x in [-.043, .043]:
        for y in [-.068, .008]:
            box(world, f"stand_{x}_{y}", [x, y, .065], [.006, .006, .065], ".85 .85 .80 1", False)
    box(world, "stand_top", [0, -.03, .135], [.055, .05, .005], ".85 .85 .80 1", False)
    box(world, "pcb", [0, -.025, .155], [.045, .043, .001], ".05 .35 .16 1", False)
    for x in [-.036, .036]:
        for y in [-.057, .007]:
            box(world, f"spacer_{x}_{y}", [x, y, .147], [.002, .002, .007], ".65 .45 .13 1", False)
    z = .17
    depth = .055
    wall = .001
    for side in [-1, 1]:
        box(world, f"channel_side_{side}", [side * (c.channel_width_m / 2 + wall / 2), -depth / 2, z],
            [wall / 2, depth / 2, c.channel_height_m / 2 + wall], ".65 .69 .71 1")
        box(world, f"channel_vertical_{side}", [0, -depth / 2, z + side * (c.channel_height_m / 2 + wall / 2)],
            [c.channel_width_m / 2, depth / 2, wall / 2], ".65 .69 .71 1")
    ET.SubElement(world, "site", name="mouth", pos=f"0 0 {z}", size=".001", rgba="1 .8 0 1")
    body = ET.SubElement(world, "body", name="cartesian_holder_proxy", pos=f"0 0 {z}", gravcomp="1")
    ET.SubElement(body, "inertial", pos=f"0 {c.shaft_length_m / 2} 0", mass=".02", diaginertia=".00001 .00001 .00001")
    joints = [("x", "slide", "1 0 0", "-.015 .015"), ("y", "slide", "0 1 0", "-.056 .015"),
              ("z", "slide", "0 0 1", "-.015 .015"), ("rx", "hinge", "1 0 0", "-.12 .12"),
              ("ry", "hinge", "0 1 0", "-.12 .12"), ("rz", "hinge", "0 0 1", "-.12 .12")]
    for name, kind, axis, limits in joints:
        ET.SubElement(body, "joint", name=name, type=kind, axis=axis, range=limits, damping=".01", armature=".00001")
    box(body, "shaft_proxy", [0, c.shaft_length_m / 2, 0],
        [c.shaft_width_m / 2, c.shaft_length_m / 2, c.shaft_height_m / 2], ".60 .64 .67 1", mass=0)
    head_center_z = (c.head_height_m - c.shaft_height_m) / 2
    box(body, "head_proxy", [0, c.shaft_length_m + c.head_length_m / 2, head_center_z],
        [c.shaft_width_m / 2, c.head_length_m / 2, c.head_height_m / 2], ".32 .38 .42 1", mass=0)
    for side in [-1, 1]:
        box(body, f"grip_visual_{side}", [side * .014, c.shaft_length_m + .012, 0], [.003, .013, .009],
            ".12 .13 .14 1", False, 0)
    ET.SubElement(body, "site", name="module_tip", size=".001", rgba=".9 .3 .1 1")
    actuators = ET.SubElement(root, "actuator")
    for index, (name, _, _, limits) in enumerate(joints):
        ET.SubElement(actuators, "position", name=f"servo_{name}", joint=name,
            kp="4000" if index < 3 else "2", kv="15" if index < 3 else ".05",
            ctrlrange=limits, forcerange="-10 10" if index < 3 else "-.5 .5")
    ET.indent(root)
    return ET.tostring(root, encoding="unicode")
