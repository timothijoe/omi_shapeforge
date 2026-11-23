"""Read-only episode-wide wrist pose diagnostics and actual V3 mesh galleries.

The supplied calibration is reused on the user's same-camera assumption.
Geometric checks and temporal flags are not a measured pose accuracy score.
"""
import argparse
from collections import Counter
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation

import estimate_wrist_module_pose as pose_impl


class CropMapping:
    def __init__(self, calibration):
        w, h = calibration["image_width"], calibration["image_height"]
        self.side = round(min(w, h)*.36)
        self.left = max(0, min(w-self.side, round(w*.5)-self.side//2))
        self.top = max(0, min(h-self.side, round(h*.704)-self.side//2))
        self.indices = np.rint(np.linspace(0, self.side-1, 128)).astype(int)
        self.K = np.array(calibration["K"], dtype=float)
        self.D = np.array(calibration["D"], dtype=float)
        self.scale = 127/(self.side-1)
        self.K_roi = np.array([[self.scale, 0, -self.left*self.scale],
                               [0, self.scale, -self.top*self.scale], [0, 0, 1]]) @ self.K

    def to_raw(self, points):
        points = np.asarray(points)
        return np.c_[np.interp(points[:, 0], np.arange(128), self.indices)+self.left,
                     np.interp(points[:, 1], np.arange(128), self.indices)+self.top]

    def to_roi(self, points):
        points = np.asarray(points)
        return np.c_[np.interp(points[:, 0]-self.left, self.indices, np.arange(128)),
                     np.interp(points[:, 1]-self.top, self.indices, np.arange(128))]

    def record(self):
        return {"crop_xywh": [self.left, self.top, self.side, self.side], "roi_wh": [128, 128],
                "sampling": "nearest-rint-linspace", "sample_indices": self.indices.tolist(),
                "K_roi_affine_approximation": self.K_roi.tolist(), "D_unchanged": self.D.tolist(),
                "fitting": "ROI feature points mapped through exact sample lookup to raw pixels; original fisheye K/D used for PnP",
                "rendering": "affine ROI K; nearest-grid discretization is below 0.17 ROI pixel for this crop",
                "calibration_identity": "user reports likely same camera/settings; not independently re-calibrated"}


class RoiFeatures:
    """Image features under a known orange-gripper view prior, no per-frame labels."""
    def __init__(self, mapping):
        self.mapping = mapping
        self.last = {}

    def __call__(self, image, _K):
        self.last = {}
        if image.shape != (128, 128, 3):
            raise ValueError("expected recorded wrist ROI 128x128")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        orange = cv2.inRange(hsv, np.array([3, 100, 50]), np.array([32, 255, 255]))
        left, right = [], []
        for y in range(88, 119):
            a = np.where(orange[y, :64] > 0)[0]
            b = np.where(orange[y, 64:] > 0)[0]+64
            if len(a) > 4 and len(b) > 4:
                left.append(a.max())
                right.append(b.min())
        if len(left) < 5:
            raise ValueError("orange_gripper_prior_unavailable")
        center = int(np.clip(round((np.median(left)+np.median(right))/2), 52, 78))
        profile = np.median(gray[:, center-5:center+6], axis=1).astype(float)
        scores = [np.mean(profile[y-3:y])-np.mean(profile[y:y+4]) for y in range(60, 91)]
        head = int(np.argmax(scores))+60
        if max(scores) < 45:
            raise ValueError("head_edge_contrast_insufficient")
        row = np.mean(gray[head-7:head-2].astype(float), axis=0)
        gradient = np.convolve(row, [1, 0, -1], mode="same")
        lr = np.arange(max(30, center-25), center-5)
        rr = np.arange(center+5, min(102, center+26))
        xl, xr = float(lr[np.argmax(gradient[lr])]), float(rr[np.argmin(gradient[rr])])
        if not 16 <= xr-xl <= 38:
            raise ValueError("head_width_invalid")
        x0, x1 = max(0, int(xl)-5), min(128, int(xr)+6)
        y0, y1 = max(15, head-55), min(100, head+15)
        mask = np.zeros((128, 128), np.uint8)
        mask[y0:y1, x0:x1] = cv2.GC_PR_BGD
        poly = np.array([[int(xl+3), max(y0+2, head-40)], [int(xr-3), max(y0+2, head-40)],
                         [int(xr), head], [int(xr-3), head+12], [int(xl+3), head+12], [int(xl), head]])
        cv2.fillPoly(mask, [poly], cv2.GC_PR_FGD)
        mask[head-12:head-4, center-4:center+5] = cv2.GC_FGD
        mask[head+3:head+8, center-3:center+4] = cv2.GC_FGD
        mask[(hsv[:, :, 1] > 100) & (hsv[:, :, 2] > 40)] = cv2.GC_BGD
        cv2.setRNGSeed(7)
        cv2.grabCut(image, mask, None, np.zeros((1, 65)), np.zeros((1, 65)), 4, cv2.GC_INIT_WITH_MASK)
        binary = np.uint8((mask == 1) | (mask == 3))*255
        dark = np.where(profile[y0:head-15] < .65*np.median(profile[head-12:head-4]))[0]+y0
        if len(dark):
            binary[:int(dark[-1]+1)] = 0
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            raise ValueError("body_region_missing")
        hull = cv2.convexHull(max(contours, key=cv2.contourArea))[:, 0].astype(float)
        top = hull[hull[:, 1] <= hull[:, 1].min()+2]
        uv = np.array([top[np.argmin(top[:, 0])], top[np.argmax(top[:, 0])],
                       [xl, head-1], [xr, head-1]], dtype=float)
        length = float(np.mean(uv[2:, 1])-np.mean(uv[:2, 1]))
        self.last = {"feature_roi_xy": uv.tolist(), "head_center_roi_xy": [(xl+xr)/2, float(head-1)],
                     "head_width_roi_px": xr-xl, "visible_body_length_roi_px": length,
                     "apparent_length_width_ratio": length/(xr-xl)}
        if length < 15:
            raise ValueError("visible_shaft_short_or_occluded")
        if min(uv[1, 0]-uv[0, 0], xr-xl) < 10:
            raise ValueError("far_edge_too_narrow")
        if (uv[1, 0]-uv[0, 0])/(xr-xl) > 1.08:
            raise ValueError("far_edge_wider_than_head_possible_socket_contamination")
        return self.mapping.to_raw(uv), [x0, y0, x1, y1], binary


def select_review_frames(rows, count=8):
    """Include ends, pitch extremes and failure/review cases, not just low errors."""
    chosen = {0, len(rows)-1}
    pitch = [(i, r.get("recorded_eef_rpy_deg", [0, np.nan, 0])[1]) for i, r in enumerate(rows)]
    pitch = [(i, p) for i, p in pitch if np.isfinite(p)]
    if pitch:
        chosen.add(min(pitch, key=lambda x: x[1])[0])
        chosen.add(max(pitch, key=lambda x: x[1])[0])
    for status in ["rejected", "review_flagged"]:
        indices = [i for i, r in enumerate(rows) if r["status"] == status]
        if indices:
            chosen.add(indices[len(indices)//2])
    usable = [(i, r.get("features", {}).get("apparent_length_width_ratio")) for i, r in enumerate(rows)]
    usable = [(i, v) for i, v in usable if v is not None]
    if usable:
        chosen.add(min(usable, key=lambda x: x[1])[0])
        chosen.add(max(usable, key=lambda x: x[1])[0])
    for i in np.linspace(0, len(rows)-1, count).round().astype(int):
        if len(chosen) >= count:
            break
        chosen.add(int(i))
    return sorted(chosen)[:count]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", type=Path, required=True)
    parser.add_argument("--omi-source", type=Path, required=True)
    parser.add_argument("--intrinsics", type=Path, required=True)
    parser.add_argument("--model-inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(args.omi_source / "src"))
    from omi_hil_rl.hil.observation_storage import ObservationReader
    reader = ObservationReader(cache_size=128)
    calibration = json.loads(args.intrinsics.read_text())
    mapping = CropMapping(calibration)
    # Validate lookup geometry against the actual recorded-stream publisher.
    spec = importlib.util.spec_from_file_location("wrist_publication", args.omi_source / "ros2/omi_sensors/omi_sensors/wrist_image.py")
    publication = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publication)
    w, h = calibration["image_width"], calibration["image_height"]
    yy, xx = np.indices((h, w))
    coordinate_image = np.stack([xx % 256, yy % 256, xx//256], axis=-1).astype(np.uint8)
    check, metadata = publication.prepare_image(coordinate_image, "roi")
    assert metadata["roi_xywh"] == [mapping.left, mapping.top, mapping.side, mapping.side]
    expected = coordinate_image[mapping.top+mapping.indices[:, None], mapping.left+mapping.indices[None, :]]
    assert np.array_equal(check, expected)
    (args.output / "crop_mapping.json").write_text(json.dumps({**mapping.record(), "publisher_roundtrip_passed": True}, indent=2))
    model_manifest, parts = pose_impl.load_parts(args.model_inputs)
    detector = RoiFeatures(mapping)
    cache, all_rows, inventories, grouped = {}, [], [], {}
    root = args.episodes.resolve()
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():
            continue
        rows = []
        image_dir = args.output / "wrist_images" / directory.name
        image_dir.mkdir(parents=True)
        previous = None
        for file in sorted(directory.glob("*.npz")):
            if not file.stem.isdigit():
                continue
            with np.load(file, allow_pickle=False) as archive:
                meta = json.loads(str(archive["metadata"]))
            reference = meta.get("observation_storage", {}).get("observation")
            if not reference or not meta.get("observation_present"):
                continue
            frame_dir = (directory / reference["directory"]).resolve()
            if not frame_dir.is_relative_to(root):
                raise ValueError("frame reference escapes selected episode root")
            frame = reader._frame(frame_dir, reference["frames"][-1])
            status = meta.get("observation_status", {})
            rgb = frame["wrist_rgb"]
            if rgb.shape != (3, 128, 128):
                raise ValueError("unsupported wrist image shape")
            raw_path = image_dir / f"{file.stem}.png"
            Image.fromarray(rgb.transpose(1, 2, 0)).save(raw_path)
            wrist_hash = hashlib.sha256(rgb.tobytes()).hexdigest()
            row = {"episode": directory.name, "tick": int(file.stem), "source_file": str(file),
                   "frame_content_id": reference["frames"][-1], "wrist_sha256": wrist_hash,
                   "reference_ns": meta.get("observation_reference_ns"), "image": str(raw_path),
                   "camera_mask": frame["camera_mask"].tolist(), "flags": []}
            eef = status.get("eef_xyz_xyzw")
            if eef:
                assert np.allclose(frame["state"][7:], eef, atol=1e-7)
                row["recorded_eef_xyz_xyzw"] = eef
                row["recorded_eef_rpy_deg"] = Rotation.from_quat(eef[3:]).as_euler("xyz", degrees=True).tolist()
            if wrist_hash not in cache:
                result = {"status": "rejected", "pose": None}
                detector.last = {}
                try:
                    if not frame["camera_mask"][1]:
                        raise ValueError("wrist_camera_mask_missing")
                    image = cv2.cvtColor(rgb.transpose(1, 2, 0), cv2.COLOR_RGB2BGR)
                    p, fit, _ = pose_impl.estimate_pose(image, mapping.K, mapping.D, parts, feature_extractor=detector)
                    rotation = cv2.Rodrigues(p[:3])[0]
                    if np.dot(rotation[:, 2], -p[3:]) <= 0:
                        raise ValueError("estimated_top_face_points_away_from_camera")
                    predicted_roi = mapping.to_roi(np.array(fit["projected_points_px"]))
                    roi_error = np.linalg.norm(predicted_roi-np.array(detector.last["feature_roi_xy"]), axis=1)
                    result.update(status="hypothesis", pose=p.tolist(), translation_mm=p[3:].tolist(),
                                  rotation_vector_rad=p[:3].tolist(), rpy_xyz_deg=Rotation.from_matrix(rotation).as_euler("xyz", degrees=True).tolist(),
                                  fit_rmse_roi_px=float(np.sqrt(np.mean(roi_error**2))), fit_rmse_raw_px=fit["corner_rmse_px"],
                                  estimated_shaft_optical_axis_angle_deg=float(np.degrees(np.arccos(np.clip(abs(rotation[2, 1]), 0, 1)))))
                except (ValueError, cv2.error) as error:
                    result["reason"] = str(error)
                result["features"] = dict(detector.last)
                cache[wrist_hash] = result
            row.update(cache[wrist_hash])
            if row["pose"] is not None:
                if row["features"]["apparent_length_width_ratio"] < 1.15:
                    row["flags"].append("short_visible_body_occlusion_or_tilt")
                if previous is not None:
                    dt = (row["reference_ns"]-previous["reference_ns"])/1e9
                    R1, R0 = cv2.Rodrigues(np.array(row["pose"][:3]))[0], cv2.Rodrigues(np.array(previous["pose"][:3]))[0]
                    angle = float(np.linalg.norm(cv2.Rodrigues(R1@R0.T)[0])*180/np.pi)
                    movement = float(np.linalg.norm(np.array(row["pose"][3:])-np.array(previous["pose"][3:])))
                    row["rotation_step_deg"], row["translation_step_mm"] = angle, movement
                    if 0 < dt <= .5 and (angle > 5*max(dt, .1)/.1 or movement > 10*max(dt, .1)/.1):
                        row["flags"].append("large_temporal_pose_change_review_needed")
                previous = row
                if row["flags"]:
                    row["status"] = "review_flagged"
            rows.append(row)
        if not rows:
            continue
        all_rows.extend(rows)
        grouped[directory.name] = rows
        angles = np.array([r["recorded_eef_rpy_deg"] for r in rows if "recorded_eef_rpy_deg" in r])
        inventories.append({"episode": directory.name, "observations": len(rows),
            "unique_wrist_images": len({r["wrist_sha256"] for r in rows}),
            "status_counts": dict(Counter(r["status"] for r in rows)),
            "recorded_eef_rpy_span_deg": np.ptp(angles, axis=0).tolist() if len(angles) else None})
        print("EPISODE", directory.name, len(rows), inventories[-1]["status_counts"], flush=True)
    with (args.output / "frame_results.jsonl").open("w") as stream:
        for row in all_rows:
            stream.write(json.dumps(row, ensure_ascii=False)+"\n")
    with (args.output / "pose_hypotheses.csv").open("w") as stream:
        writer = csv.writer(stream)
        writer.writerow(["episode", "tick", "status", "reason_or_flags", "estimated_tx_mm", "estimated_ty_mm", "estimated_tz_mm",
                         "estimated_rx_rad", "estimated_ry_rad", "estimated_rz_rad", "fit_rmse_roi_px", "recorded_eef_pitch_deg"])
        for row in all_rows:
            p = row.get("pose")
            values = p[3:]+p[:3] if p else [""]*6
            writer.writerow([row["episode"], row["tick"], row["status"], row.get("reason") or ";".join(row["flags"]),
                             *values, row.get("fit_rmse_roi_px", ""), row.get("recorded_eef_rpy_deg", [None, "", None])[1]])
    (args.output / "episode_inventory.json").write_text(json.dumps(inventories, indent=2))
    galleries = args.output / "galleries"
    galleries.mkdir()
    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font, small = ImageFont.truetype(font_path, 22), ImageFont.truetype(font_path, 17)
    rendered = []
    for eid, rows in grouped.items():
        selected = select_review_frames(rows)
        canvas = Image.new("RGB", (4*390, 2*500+100), "#16222f")
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), f"真实 episode {eid[:8]}：V3 mesh 回投影批量诊断", font=font, fill="white")
        draw.text((16, 48), "按文档 ROI 还原；沿用所给内参。黄色=主体，青色=拉臂。数值通过≠识别准确。", font=small, fill="#ccd7e0")
        for slot, index in enumerate(selected):
            row = rows[index]
            image = cv2.imread(row["image"])
            big = cv2.resize(image, (256, 256), interpolation=cv2.INTER_NEAREST)
            if row["pose"] is not None:
                display_K = np.diag([2., 2., 1.]) @ mapping.K_roi
                big, _ = pose_impl.render_mesh(big, parts, np.array(row["pose"]), display_K, mapping.D)
            x, y = (slot % 4)*390, 100+(slot//4)*500
            canvas.paste(Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB)).resize((360, 360), Image.Resampling.NEAREST), (x+15, y+32))
            title = f"tick {row['tick']} · " + ("拒绝输出" if row["status"] == "rejected" else "需复核" if row["status"] == "review_flagged" else "粗位姿候选")
            draw.text((x+12, y), title, font=font, fill="#ff9c8a" if row["status"] == "rejected" else "#f1db9c")
            pitch = row.get("recorded_eef_rpy_deg", [0, float('nan'), 0])[1]
            draw.text((x+12, y+402), f"记录末端 pitch：{pitch:.1f}°（base_link）", font=small, fill="white")
            if row["pose"] is not None:
                draw.text((x+12, y+430), f"拟合角点 RMS：{row['fit_rmse_roi_px']:.2f} ROI px", font=small, fill="#cbd6e0")
                draw.text((x+12, y+457), f"估计轴向夹角：{row['estimated_shaft_optical_axis_angle_deg']:.1f}°（相机）", font=small, fill="#cbd6e0")
            else:
                draw.text((x+12, y+430), "特征／几何检查未通过，未沿用前帧位姿", font=small, fill="#cbd6e0")
            rendered.append({"episode": eid, "tick": row["tick"], "status": row["status"]})
        path = galleries / f"{eid[:8]}_mesh_review.png"
        canvas.save(path)
        print("GALLERY", path.name, flush=True)
    summary = {"episodes": len(inventories), "observations": len(all_rows), "unique_wrist_images": len(cache),
               "pose_status_counts": dict(Counter(r["status"] for r in all_rows)),
               "rejection_reasons": dict(Counter(r.get("reason") for r in all_rows if r["status"] == "rejected")),
               "rendered_keyframes": rendered, "model_source": model_manifest["module"], "crop_mapping": mapping.record(),
               "data_scope": "All accessible raw periodic episodes under the selected local run; training segments are not extra independent episodes",
               "accuracy_measured": False, "metric_pose_validated": False,
               "development_views": "Feature-rule development used selected 19c7887c and 8083942d views; other episodes are diagnostic holdouts, not ground truth",
               "limitations": ["No independent 6D truth or manual full-mask labels", "128x128 image quantization, occlusion and truncation", "Fixed orange-gripper/semantic-corner prior, not general recognition", "External scene occlusion is not rendered", "V3 pull arms differ from the real handle", "EEF pitch in base_link is not module pitch in camera", "Temporal flags indicate suspicion, not independently proven error"]}
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print("BATCH_COMPLETE", json.dumps({k: summary[k] for k in ["episodes", "observations", "unique_wrist_images", "pose_status_counts"]}), flush=True)


if __name__ == "__main__":
    main()
