"""Read-only Open3D desktop comparison with synchronized metric cameras."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import open3d as o3d
from open3d.visualization import gui, rendering


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--body-frame", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--right-model", choices=["r01", "r02"], default="r01")
    args = parser.parse_args()
    sources = [("原始 TSDF 扫描", "original_tsdf_upper.ply"),
               ("历史 SDF（人工清孔）", "edited_sdf_upper.ply"),
               ("保留背面结构 r01", "r01_upper.ply"),
               ("平背面候选 r02", "r02_upper.ply")]
    meshes = []
    for label, filename in sources:
        mesh = o3d.io.read_triangle_mesh(str(args.review_dir / filename))
        if not mesh.has_triangles():
            raise ValueError(f"Empty mesh: {filename}")
        if filename.startswith(("r01_", "r02_")):
            # Keep sharp mechanical faces; averaged corner normals falsely
            # round the shell and create diagonal shading across flat panels.
            faces = np.asarray(mesh.triangles)
            vertices = np.asarray(mesh.vertices)[faces].reshape(-1, 3)
            colors = np.asarray(mesh.vertex_colors)[faces].reshape(-1, 3) if mesh.has_vertex_colors() else None
            mesh = o3d.geometry.TriangleMesh(
                o3d.utility.Vector3dVector(vertices),
                o3d.utility.Vector3iVector(np.arange(len(vertices)).reshape(-1, 3)))
            if colors is not None:
                mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
        mesh.compute_vertex_normals()
        meshes.append(mesh)
    B = np.array(json.loads(args.body_frame.read_text())["body_to_object"])
    app = gui.Application.instance
    app.initialize()
    font = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if Path(font).is_file():
        fd = gui.FontDescription(font, point_size=18)
        fd.add_typeface_for_language(font, "zh_all")
        app.set_font(app.DEFAULT_FONT_ID, fd)
    win = app.create_window("OMI | 光模块插接座 · Open3D 网格对照", 1660, 960)
    head = gui.Vert(6, gui.Margins(12, 8, 12, 8))
    head.add_child(gui.Label("光模块插接座｜原始扫描与模型对照"))
    head.add_child(gui.Label("左键旋转 · 滚轮缩放 · Ctrl＋左键平移｜两侧视角同步、相同物理比例"))
    head.add_child(gui.Label("显示插接座上部；背面结构按实拍保留，r02 平背面仅留作对照。"))
    buttons = gui.Horiz(8)
    head.add_child(buttons)
    win.add_child(head)
    choices, views = [], []
    material = rendering.MaterialRecord()
    material.shader = "defaultLit"
    material.base_roughness = .7
    state = {"first": True, "active": 0, "last": None, "syncs": 0, "ready": False}

    def snap(view):
        cam = view.scene.camera
        return np.r_[np.asarray(cam.get_view_matrix()).ravel(),
                     np.asarray(cam.get_projection_matrix()).ravel()]

    def capture():
        state["last"] = [snap(v) for v in views]

    def receipt():
        data = {"pid": os.getpid(), "open3d_version": o3d.__version__,
                "sources": [str(args.review_dir / f) for _, f in sources],
                "selected": [sources[c.selected_index][0] for c in choices],
                "equal_camera_matrices": bool(np.allclose(snap(views[0]), snap(views[1]), atol=1e-7, rtol=0)),
                "synchronizations": state["syncs"], "source_coordinates_unchanged": True,
                "read_only_viewer": True}
        args.receipt.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def draw(index):
        view = views[index]
        if view.scene.has_geometry("model"):
            view.scene.remove_geometry("model")
        view.scene.add_geometry("model", meshes[choices[index].selected_index], material)
        view.force_redraw()
        if not state["first"]:
            receipt()

    for index, selected in enumerate([0, 2 if args.right_model == "r01" else 3]):
        choice = gui.Combobox()
        for label, _ in sources:
            choice.add_item(label)
        choice.selected_index = selected
        win.add_child(choice)
        choices.append(choice)
        view = gui.SceneWidget()
        view.scene = rendering.Open3DScene(win.renderer)
        view.scene.set_background([.065, .078, .1, 1])
        view.set_view_controls(gui.SceneWidget.Controls.ROTATE_CAMERA)
        win.add_child(view)
        views.append(view)
        choice.set_on_selection_changed(lambda _text, _idx, i=index: draw(i))

        def mouse(_event, i=index):
            state["active"] = i
            return gui.Widget.EventCallbackResult.IGNORED

        view.set_on_mouse(mouse)

    def aim(kind):
        center = B[:3, 3] + B[:3, :3] @ np.array([-.006, -.035, .002])
        offsets = {"rear": [.11, -.16, .12], "front": [-.10, .16, .10],
                   "side": [-.20, 0, .035], "top": [0, 0, .22]}
        eye = center + B[:3, :3] @ np.array(offsets[kind])
        up = B[:3, 1] if kind == "top" else B[:3, 2]
        bounds = meshes[3].get_axis_aligned_bounding_box()
        for view in views:
            view.setup_camera(40, bounds, center)
            view.look_at(center, eye, up)
            view.scene.camera.set_projection(40, max(1, view.frame.width) / max(1, view.frame.height),
                                             .0001, 5, rendering.Camera.FovType.Vertical)
            view.force_redraw()
        capture()
        receipt()

    for label, kind in [("背面", "rear"), ("正面孔口", "front"), ("侧面", "side"), ("俯视", "top")]:
        button = gui.Button(label)
        button.set_on_clicked(lambda k=kind: aim(k))
        buttons.add_child(button)

    def layout(_context):
        rect = win.content_rect
        header, selectors, gap = 175, 42, 8
        width = (rect.width - gap) // 2
        height = max(1, rect.height - header - selectors)
        head.frame = gui.Rect(rect.x, rect.y, rect.width, header)
        for i, view in enumerate(views):
            x = rect.x + i * (width + gap)
            choices[i].frame = gui.Rect(x + 8, rect.y + header, width - 16, selectors - 4)
            view.frame = gui.Rect(x, rect.y + header + selectors, width, height)
        if state["first"]:
            state["first"] = False
            aim("rear")
        for view in views:
            view.scene.camera.set_projection(40, width / height, .0001, 5, rendering.Camera.FovType.Vertical)
        capture()

    def tick():
        if state["first"]:
            return False
        if not state["ready"]:
            state["ready"] = True
            receipt()
            print("SOCKET_VIEWER_READY", flush=True)
        now = [snap(v) for v in views]
        changed = [i for i in range(2) if not np.allclose(now[i], state["last"][i], atol=1e-8, rtol=0)]
        if not changed:
            return False
        src = state["active"] if state["active"] in changed else changed[0]
        dst = 1 - src
        views[dst].scene.camera.copy_from(views[src].scene.camera)
        views[dst].center_of_rotation = views[src].center_of_rotation
        views[dst].force_redraw()
        state["syncs"] += 1
        capture()
        receipt()
        return True

    win.set_on_layout(layout)
    win.set_on_tick_event(tick)
    for index in range(2):
        draw(index)
    app.run()


if __name__ == "__main__":
    main()
