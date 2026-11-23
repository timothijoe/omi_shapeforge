"""Read-only Open3D inspection of actual V3 insertion geometry and contact audit."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import open3d as o3d
from open3d.visualization import gui, rendering


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.run / "inputs/manifest.json").read_text())
    audit = json.loads((args.run / "collision/surface_contacts.json").read_text())
    stop = audit["tip_to_shoulder_mm"]
    onset = audit["profiles"][0]["first_contacts"]["all_rigid"]["bracket_mm"][1]
    channel = manifest.get("channel_basic_clearance", {"width_mm": 20.9, "height_mm": 9.6})
    socket_revision = manifest["socket"].get("revision", "r01").split("-")[0]
    app = gui.Application.instance
    app.initialize()
    font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    fd = gui.FontDescription(font, point_size=18)
    fd.add_typeface_for_language(font, "zh_all")
    app.set_font(app.DEFAULT_FONT_ID, fd)
    win = app.create_window("OMI | V3 光模块 × 插接座 | 插入关系检查", 1760, 1000)
    panel = gui.Vert(8, gui.Margins(12, 12, 12, 12))
    for text in [f"V3 光模块 × 插接座 {socket_revision}", "目标：窄段进入，头部台阶限位", "当前模型尺寸（mm）", "窄段含侧弹片：18.17 × 7.84", f"金属通道净空：{channel['width_mm']:.2f} × {channel['height_mm']:.2f}", "头部最大高度：10.45", f"尖端至头部台阶：{stop:.2f}", "上述净空未扣除孔口弹片。"]:
        panel.add_child(gui.Label(text))
    panel.add_child(gui.Label("插入深度（尖端越过孔口）mm"))
    slider = gui.Slider(gui.Slider.DOUBLE)
    slider.set_limits(-5, stop + 2)
    number = gui.NumberEdit(gui.NumberEdit.DOUBLE)
    number.set_limits(-5, stop + 2)
    number.decimal_precision = 2
    panel.add_child(slider)
    panel.add_child(number)
    status = gui.Label("")
    contact = gui.Label("")
    panel.add_child(status)
    panel.add_child(contact)
    panel.add_child(gui.Label("几何检查，未模拟弹片让位或插入力。"))
    rows = []
    for _ in range(2):
        row = gui.Horiz(6)
        panel.add_child(row)
        rows.append(row)
    shell = gui.Checkbox("显示白色壳体")
    shell.checked = True
    springs = gui.Checkbox("显示孔口弹片")
    springs.checked = True
    stand = gui.Checkbox("显示下部支架")
    stand.checked = True
    panel.add_child(shell)
    panel.add_child(springs)
    panel.add_child(stand)
    panel.add_child(gui.Label("隐藏仅用于观察，接触判定仍保留原几何。"))
    directions = gui.Horiz(6)
    panel.add_child(directions)
    panel.add_child(gui.Label("左键旋转 · 滚轮缩放"))
    panel.add_child(gui.Label("Ctrl＋左键平移"))
    win.add_child(panel)
    view = gui.SceneWidget()
    view.scene = rendering.Open3DScene(win.renderer)
    view.scene.set_background([.065, .078, .1, 1])
    view.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)
    win.add_child(view)
    normal = rendering.MaterialRecord()
    normal.shader = "defaultLit"
    normal.base_roughness = .65
    red = rendering.MaterialRecord()
    red.shader = "defaultLit"
    red.base_color = [1., .14, .04, 1.]
    red.base_roughness = .5
    parts = []
    for kind in ["socket", "module"]:
        for index, rec in enumerate(manifest[kind]["parts"]):
            d = np.load(args.run / "inputs" / kind / rec["file"])
            vertices = d["vertices"][d["faces"]].reshape(-1, 3) / 1000
            colors = np.repeat(d["face_colors"][:, :3], 3, axis=0)
            mesh = o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices),
                       o3d.utility.Vector3iVector(np.arange(len(vertices)).reshape(-1, 3)))
            mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
            mesh.compute_vertex_normals()
            key = f"{kind}_{index}"
            view.scene.add_geometry(key, mesh, normal)
            fine = any(s in rec["name"].lower() for s in ["spring", "finger", "embossed", "pressed side seam", "lower mouth rolled"])
            parts.append({**rec, "key": key, "kind": kind, "fine": fine})
    # Insertion axis, from outside toward the metal channel.
    axis = o3d.geometry.LineSet(o3d.utility.Vector3dVector([[-.0005, .10, .0007], [-.0005, -.055, .0007]]),
                               o3d.utility.Vector2iVector([[0, 1]]))
    axis.paint_uniform_color([1., .75, .12])
    line = rendering.MaterialRecord()
    line.shader = "unlitLine"
    line.line_width = 2
    view.scene.add_geometry("insertion_axis", axis, line)
    state = {"updating": False, "first": True, "depth": stop}

    def visibility(_value=None):
        for p in parts:
            visible = p["group"] != "stand" or stand.checked
            if p["kind"] == "socket":
                visible &= p["group"] != "housing" or shell.checked
                visible &= not p["fine"] or springs.checked
            view.scene.show_geometry(p["key"], visible)
        view.force_redraw()

    def update(depth):
        if state["updating"]:
            return
        state["updating"] = True
        depth = float(np.clip(depth, -5, stop + 2))
        state["depth"] = depth
        slider.double_value = depth
        number.double_value = depth
        T = np.eye(4)
        T[:3, 3] = [-.0005, (1.85 - audit["leading_tip_y_mm"] - depth) / 1000, .0007]
        index = int(np.clip(round((depth + 2) / .25), 0, len(audit["profiles"][0]["rows"]) - 1))
        collisions = audit["profiles"][0]["rows"][index]["collisions"]
        hit_names = {h["socket_part"] for h in collisions}
        for p in parts:
            if p["kind"] == "module":
                view.scene.set_geometry_transform(p["key"], T)
            else:
                view.scene.modify_geometry_material(p["key"], red if p["name"] in hit_names else normal)
        if depth > stop + .01:
            status.text = f"{depth:.2f} mm：已越过台阶限位"
        elif depth >= stop - .01:
            status.text = f"{depth:.2f} mm：头部台阶达到孔沿"
        elif depth < 0:
            status.text = f"{depth:.2f} mm：尚未到孔口"
        else:
            status.text = f"{depth:.2f} mm：插入途中"
        contact.text = "模型弹片有相交，需要让位／几何复核。" if depth >= onset else "尚未到模型弹片首次接触位置。"
        view.force_redraw()
        win.set_needs_layout()
        win.post_redraw()
        state["updating"] = False
        (args.run / "insertion_viewer.json").write_text(json.dumps({"pid": os.getpid(),
            "module": "OM-001/V3", "socket": f"OS-001/{socket_revision}", "depth_mm": depth,
            "control_depth_mm": number.double_value, "status_text": status.text,
            "lower_stand_visible": stand.checked,
            "module_to_socket_body_m": T.tolist(), "physical_simulation": False,
            "source_geometry_changed": False}, indent=2))

    slider.set_on_value_changed(update)
    number.set_on_value_changed(update)
    shell.set_on_checked(visibility)
    springs.set_on_checked(visibility)
    def toggle_stand(value):
        visibility(value)
        aim("whole")
        update(state["depth"])

    stand.set_on_checked(toggle_stand)
    for i, (label, depth) in enumerate([("入口", 0), ("弹片接触", onset), ("接近终点", stop - 1), ("台阶限位", stop)]):
        button = gui.Button(label)
        button.set_on_clicked(lambda d=depth: update(d))
        rows[i // 2].add_child(button)

    def aim(kind):
        center = np.array([-.015, -.008, .003])
        offsets = {"whole": [-.14, .22, .16], "mouth": [0, .18, .025], "side": [.20, 0, .02], "top": [0, 0, .23]}
        if kind == "whole" and stand.checked:
            center = np.array([-.005, -.035, -.055])
            offsets["whole"] = [-.22, .32, .23]
        if kind == "mouth":
            center = np.array([-.0005, .00185, .0007])
        up = [0, 1, 0] if kind == "top" else [0, 0, 1]
        bounds = o3d.geometry.AxisAlignedBoundingBox([-.07, -.10, -.14 if stand.checked else -.01], [.06, .10, .025])
        view.setup_camera(40, bounds, center)
        view.look_at(center, center + offsets[kind], up)
        view.scene.camera.set_projection(40, max(1, view.frame.width) / max(1, view.frame.height), .0001, 5,
                                         rendering.Camera.FovType.Vertical)
        view.force_redraw()

    for label, kind in [("整体", "whole"), ("孔口", "mouth"), ("侧面", "side"), ("俯视", "top")]:
        button = gui.Button(label)
        button.set_on_clicked(lambda k=kind: aim(k))
        directions.add_child(button)

    def layout(_context):
        r = win.content_rect
        width = 390
        panel.frame = gui.Rect(r.x, r.y, width, r.height)
        view.frame = gui.Rect(r.x + width, r.y, max(1, r.width - width), r.height)
        if state["first"]:
            state["first"] = False
            aim("whole")
            update(stop)
            visibility()
            print("V3_INSERTION_VIEWER_READY", flush=True)
        else:
            view.scene.camera.set_projection(40, view.frame.width / max(1, view.frame.height), .0001, 5,
                                             rendering.Camera.FovType.Vertical)

    win.set_on_layout(layout)
    # Some desktop GL drivers otherwise keep the control panel's cached frame
    # while only the SceneWidget updates. Keep GUI and geometry composited.
    win.set_on_tick_event(lambda: True)
    app.run()


if __name__ == "__main__":
    main()
