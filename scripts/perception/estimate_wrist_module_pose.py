"""Known-wrist-view V3 pose hypothesis and true-mesh reprojection preview.

Uses a calibrated-image ROI prior, image-derived metal-end features and a rigid
CAD correspondence rule. This is not an unconstrained category pose detector.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import trimesh


def project(points, pose, K, D):
    points = np.ascontiguousarray(points, dtype=np.float64).reshape(-1, 1, 3)
    return cv2.fisheye.projectPoints(points, pose[:3], pose[3:], K, D)[0][:, 0]


def metal_features(image, K):
    # Grasp-location prior relative to the supplied full-image calibration.
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    x0, y0, x1, y1 = map(round, [cx-.075*fx, cy+.175*fy, cx+.083*fx, cy+.403*fy])
    h, w = image.shape[:2]
    if not (0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h):
        raise ValueError("Expected wrist ROI is outside image")
    crop = image[y0:y1, x0:x1]
    H, W = crop.shape[:2]
    mask = np.full((H, W), cv2.GC_BGD, np.uint8)
    mask[round(.047*H):round(.973*H), round(.125*W):round(.923*W)] = cv2.GC_PR_BGD
    mask[round(.08*H):round(.947*H), round(.202*W):round(.808*W)] = cv2.GC_PR_FGD
    mask[round(.233*H):round(.533*H), round(.385*W):round(.644*W)] = cv2.GC_FGD
    mask[round(.747*H):round(.853*H), round(.375*W):round(.664*W)] = cv2.GC_FGD
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    mask[(hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 45)] = cv2.GC_BGD
    cv2.setRNGSeed(7)
    cv2.grabCut(crop, mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 7, cv2.GC_INIT_WITH_MASK)
    binary = np.uint8((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)) * 255
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No body candidate in wrist ROI")
    contour = max(contours, key=cv2.contourArea)
    if not 2000 < cv2.contourArea(contour) < 14000:
        raise ValueError("Body candidate has implausible area for this view prior")
    hull = cv2.convexHull(contour)[:, 0].astype(float) + [x0, y0]
    front = hull[hull[:, 1] <= hull[:, 1].min() + 7]
    near_y0, near_y1 = cy + .306*fy, cy + .346*fy
    back = hull[(hull[:, 1] >= near_y0) & (hull[:, 1] < near_y1)]
    if len(front) < 2 or len(back) < 2:
        raise ValueError("Metal-end feature extraction failed")
    left = back[back[:, 0] == back[:, 0].min()]
    right = back[back[:, 0] == back[:, 0].max()]
    uv = np.array([front[np.argmin(front[:, 0])], front[np.argmax(front[:, 0])],
                   left[np.argmax(left[:, 1])], right[np.argmax(right[:, 1])]])
    widths = [uv[1, 0]-uv[0, 0], uv[3, 0]-uv[2, 0]]
    if min(widths) < 20 or not 1.05 < widths[1]/widths[0] < 2.5:
        raise ValueError("Corner geometry inconsistent with this wrist view")
    return uv, [x0, y0, x1, y1], binary


def load_parts(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    parts = []
    for record in manifest["module"]["parts"]:
        path = directory / "module" / record["file"]
        with np.load(path) as data:
            parts.append({"name": record["name"], "vertices": data["vertices"].copy(),
                          "faces": data["faces"].copy(), "file": str(path)})
    return manifest, parts


def estimate_pose(image, K, D, parts, feature_extractor=None):
    started = time.perf_counter()
    uv, roi, mask = (feature_extractor or metal_features)(image, K)
    top = next(p for p in parts if p["name"].startswith("01 Connected"))["vertices"]
    head = next(p for p in parts if p["name"].startswith("11 Raised"))["vertices"]
    # Correspondence assumes the far upper-guard edge and near raised-head edge
    # are visible. Occlusion can violate that assumption even at low fit error.
    obj = np.array([[top[:, 0].max(), top[:, 1].min(), top[:, 2].max()],
                    [top[:, 0].min(), top[:, 1].min(), top[:, 2].max()],
                    [head[:, 0].max(), head[:, 1].max(), head[:, 2].max()],
                    [head[:, 0].min(), head[:, 1].max(), head[:, 2].max()]])
    normalized = cv2.fisheye.undistortPoints(uv[:, None], K, D)
    ok, rv, tv = cv2.solvePnP(obj, normalized, np.eye(3), None, flags=cv2.SOLVEPNP_SQPNP)
    if not ok:
        raise ValueError("PnP failed")
    fit = least_squares(lambda p: (project(obj, p, K, D)-uv).ravel(),
                        np.r_[rv.ravel(), tv.ravel()], loss="soft_l1", f_scale=2, max_nfev=200)
    pose = fit.x
    R = cv2.Rodrigues(pose[:3])[0]
    predicted = project(obj, pose, K, D)
    errors = np.linalg.norm(predicted-uv, axis=1)
    vertices = np.vstack([p["vertices"] for p in parts])
    if not fit.success or np.min((vertices @ R.T + pose[3:])[:, 2]) <= 10 or np.sqrt(np.mean(errors**2)) > 5:
        raise ValueError("Pose failed depth or reprojection sanity check")
    hypotheses = []
    candidates = cv2.solvePnPGeneric(obj, normalized, np.eye(3), None, flags=cv2.SOLVEPNP_IPPE)
    for ar, at in zip(candidates[1], candidates[2]):
        candidate = np.r_[ar.ravel(), at.ravel()]
        e = np.linalg.norm(project(obj, candidate, K, D)-uv, axis=1)
        hypotheses.append({"rvec_rad": candidate[:3].tolist(), "translation_mm": candidate[3:].tolist(),
                           "corner_rmse_px": float(np.sqrt(np.mean(e**2)))})
    return pose, {"image_points_px": uv.tolist(), "model_points_mm": obj.tolist(),
                  "projected_points_px": predicted.tolist(), "point_errors_px": errors.tolist(),
                  "corner_rmse_px": float(np.sqrt(np.mean(errors**2))), "roi_xyxy": roi,
                  "planar_hypotheses": hypotheses, "estimation_seconds": time.perf_counter()-started}, mask


def render_mesh(image, parts, pose, K, D):
    H, W = image.shape[:2]
    depth = np.full((H, W), np.inf, np.float32)
    color = np.zeros((H, W, 3), np.uint8)
    R = cv2.Rodrigues(pose[:3])[0]
    feature_edges = []
    for part in parts:
        is_handle = part["name"].startswith("14 Green")
        bgr = np.array([255, 190, 30] if is_handle else [20, 200, 255], np.uint8)
        vertices, faces = part["vertices"], part["faces"]
        cached = part.get("_render_cache")
        if cached is None:
            mesh = trimesh.Trimesh(vertices, faces, process=False)
            edge_faces = {}
            for fi, face in enumerate(faces):
                for a, b in zip(face, np.roll(face, -1)):
                    edge_faces.setdefault(tuple(sorted((int(a), int(b)))), []).append(fi)
            verts, tris = trimesh.remesh.subdivide_to_size(vertices, faces, max_edge=5., max_iter=8)
            cached = part["_render_cache"] = (mesh, edge_faces, verts, tris)
        mesh, edge_faces, verts, tris = cached
        camera = vertices @ R.T + pose[3:]
        visible_faces = np.einsum("ij,ij->i", mesh.face_normals @ R.T,
                                 camera[faces].mean(1)) < 0
        for (a, b), adjacency in edge_faces.items():
            if not any(visible_faces[i] for i in adjacency):
                continue
            crease = len(adjacency) == 1 or len(adjacency) > 2
            if len(adjacency) == 2:
                i, j = adjacency
                crease = visible_faces[i] != visible_faces[j] or np.dot(mesh.face_normals[i], mesh.face_normals[j]) < np.cos(np.deg2rad(25))
            if crease:
                feature_edges.append((vertices[[a, b]], bgr))
        # Subdivision keeps the straight raster pieces close to fisheye curves.
        camera = verts @ R.T + pose[3:]
        uv = project(verts, pose, K, D)
        for face in tris:
            xyz, pts = camera[face], uv[face]
            normal = np.cross(xyz[1]-xyz[0], xyz[2]-xyz[0])
            if np.dot(normal, xyz.mean(0)) >= 0:
                continue
            lo = np.maximum(np.floor(pts.min(0)).astype(int), [0, 0])
            hi = np.minimum(np.ceil(pts.max(0)).astype(int), [W-1, H-1])
            if np.any(lo > hi):
                continue
            x, y = np.meshgrid(np.arange(lo[0], hi[0]+1)+.5, np.arange(lo[1], hi[1]+1)+.5)
            a, b, c = pts
            denominator = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator) < 1e-10:
                continue
            w0 = ((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/denominator
            w1 = ((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/denominator
            w2 = 1-w0-w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            z = 1 / np.maximum(w0/xyz[0, 2]+w1/xyz[1, 2]+w2/xyz[2, 2], 1e-12)
            region = depth[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
            take = inside & (z < region)
            region[take] = z[take]
            color[lo[1]:hi[1]+1, lo[0]:hi[0]+1][take] = bgr
    overlay = image.copy()
    mask = np.isfinite(depth)
    overlay[mask] = (image[mask]*.78 + color[mask]*.22).astype(np.uint8)
    for edge, bgr in feature_edges:
        count = max(3, int(np.linalg.norm(edge[1]-edge[0])/2)+1)
        samples = np.linspace(edge[0], edge[1], count)
        pixels = project(samples, pose, K, D)
        camera = samples @ R.T + pose[3:]
        for i in range(count-1):
            midpoint = np.rint((pixels[i]+pixels[i+1])/2).astype(int)
            x, y = midpoint
            if 0 <= x < W and 0 <= y < H and camera[i:i+2, 2].mean() <= depth[y, x] + .6:
                cv2.line(overlay, tuple(np.rint(pixels[i]).astype(int)), tuple(np.rint(pixels[i+1]).astype(int)),
                         tuple(map(int, bgr)), 1, cv2.LINE_AA)
    return overlay, mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--intrinsics", type=Path, required=True)
    parser.add_argument("--model-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    image = cv2.imread(str(args.image))
    cal = json.loads(args.intrinsics.read_text())
    if image is None or image.shape[1::-1] != (cal["image_width"], cal["image_height"]):
        raise ValueError("Image must match the supplied full-resolution intrinsic domain; cropped episode ROI is not supported")
    if cal["distortion_model"] != "opencv_fisheye":
        raise ValueError("Expected opencv_fisheye intrinsics")
    K, D = np.array(cal["K"], dtype=float), np.array(cal["D"], dtype=float)
    manifest, parts = load_parts(args.model_inputs)
    pose, fit, mask = estimate_pose(image, K, D, parts)
    overlay, rendered_mask = render_mesh(image, parts, pose, K, D)
    cv2.imwrite(str(args.output / "mesh_overlay.png"), overlay)
    cv2.imwrite(str(args.output / "detected_body_mask.png"), mask)
    cv2.imwrite(str(args.output / "projected_mesh_mask.png"), rendered_mask.astype(np.uint8)*255)
    R = cv2.Rodrigues(pose[:3])[0]
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, pose[3:]/1000
    euler = Rotation.from_matrix(R).as_euler("xyz", degrees=True)
    report = {"status": "rough_pose_hypothesis_with_real_v3_mesh_projection", "image": str(args.image),
              "model": manifest["module"], "intrinsics": cal, "fit": fit,
              "translation_mm": pose[3:].tolist(), "rotation_vector_rad": pose[:3].tolist(),
              "rpy_extrinsic_xyz_deg": euler.tolist(), "T_model_to_camera_m": T.tolist(),
              "camera_axes": "OpenCV: X right, Y down, Z forward", "model_axes": "unchanged V3 source axes; Y toward pull arms, Z raised-head side",
              "method": "Known wrist ROI prior -> image color/edge feature extraction -> fisheye-normalized PnP -> raw-fisheye robust reprojection refinement -> full unchanged V3 mesh rasterization",
              "manual_per_image_landmarks": False, "requires_view_and_roi_prior": True,
              "landmark_geometry": "Bounding-box corner proxies of the upper guard and raised head; rounded mesh vertices need not coincide with these proxy points",
              "limits": ["Four semantic correspondences are assumed, not independently labeled ground truth", "This is corner-based initialization/refinement, not dense full-mesh registration", "Fitted corner error is not independent pose accuracy", "Existing V3 pull arms differ from the visible U-shaped handle; they are not fitting targets", "No external gripper/socket occlusion model", "Calibration is marked unapproved in supplied source", "No claim of general pose recognition or reliable metric 6D on cropped episodes"],
              "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.image, args.intrinsics, args.model_inputs/'manifest.json']},
              "metric_pose_accuracy_validated": False}
    (args.output / "pose.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    canvas = Image.new("RGB", (1680, 1000), "#15202d")
    draw = ImageDraw.Draw(canvas)
    fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font, small = ImageFont.truetype(fp, 25), ImageFont.truetype(fp, 20)
    draw.text((20, 15), "V3 真实 mesh 回投影 · 由图像估计位姿（已知腕部视角原型）", font=font, fill="white")
    full = Image.fromarray(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    full.thumbnail((1120, 650))
    canvas.paste(full, (20, 70))
    close = Image.fromarray(cv2.cvtColor(overlay[640:980, 900:1055], cv2.COLOR_BGR2RGB))
    close = close.resize((434, 952), Image.Resampling.LANCZOS)
    close.thumbnail((450, 865))
    canvas.paste(close, (1195, 70))
    lines = ["金色：V3 主体网格；青色：V3 拉臂网格（模型未拉伸）",
             "相机系平移 mm：" + ", ".join(f"{x:.2f}" for x in pose[3:]),
             "固定轴 XYZ 欧拉角 °：" + ", ".join(f"{x:.2f}" for x in euler),
             f"4 个拟合对应点 RMSE：{fit['corner_rmse_px']:.2f} px；不是位姿真值误差。",
             "主体可对照检查；拉手投影有明显偏差，需要继续核查模型与对应关系。",
             "使用已知腕部 ROI 与几何对应规则；尚非任意图像的通用自动识别。"]
    for i, line in enumerate(lines):
        draw.text((20, 735+i*36), line, font=small, fill="#e4e9ef")
    canvas.save(args.output / "pose_mesh_preview.png")
    print(json.dumps({"translation_mm": report["translation_mm"], "rpy_deg": report["rpy_extrinsic_xyz_deg"],
                      "corner_rmse_px": fit["corner_rmse_px"], "estimation_seconds": fit["estimation_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
