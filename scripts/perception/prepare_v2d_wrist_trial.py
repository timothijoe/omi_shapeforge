"""Prepare a calibrated virtual pinhole view for the V2D wrist experiment.

Manual first-frame point prompts locate rigid metal; the handle is excluded.
The existing PnP hypothesis is a diagnostic initializer, NOT a head-cloud pose.
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
import trimesh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = a.output
    root.mkdir(parents=True, exist_ok=False)
    for folder in ['rectified', 'raw', 'masks', 'depth', 'poses']:
        (root/folder).mkdir()
    video = Path('/home/linux/Downloads/img/腕部相机_插口接近_6秒.mp4')
    calibration = Path('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json')
    cal = json.loads(calibration.read_text())
    K, D = np.array(cal['K']), np.array(cal['D'])
    center = cv2.fisheye.undistortPoints(np.array([[[970., 750.]]]), K, D)[0, 0]
    forward = np.r_[center, 1.]; forward /= np.linalg.norm(forward)
    right = np.cross([0., 1., 0.], forward); right /= np.linalg.norm(right)
    down = np.cross(forward, right)
    R = np.stack([right, down, forward])
    side, focal = 960, 900.
    new_K = np.array([[focal, 0, (side-1)/2], [0, focal, (side-1)/2], [0, 0, 1.]])
    mx, my = cv2.fisheye.initUndistortRectifyMap(K, D, R, new_K, (side, side), cv2.CV_32FC1)
    np.savez_compressed(root/'rectification.npz', map_x=mx, map_y=my, R_rect_from_raw=R, K=new_K, raw_K=K, raw_D=D)
    indices = list(range(0, 180, 3))+[179]
    cap = cv2.VideoCapture(str(video))
    writer = cv2.VideoWriter(str(root/'rectified.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), 10., (side, side))
    for i, original in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, original)
        ok, frame = cap.read()
        if not ok: raise ValueError(original)
        image = cv2.remap(frame, mx, my, cv2.INTER_LINEAR)
        cv2.imwrite(str(root/'rectified'/f'{i:06d}.jpg'), image, [cv2.IMWRITE_JPEG_QUALITY, 97])
        if original in [0, 30, 60, 90, 120, 150, 179]:
            cv2.imwrite(str(root/'raw'/f'{original:06d}.png'), frame)
        writer.write(image)
    cap.release(); writer.release()
    intrinsics = dict(fx=focal, fy=focal, cx=(side-1)/2, cy=(side-1)/2, width=side, height=side)
    (root/'intrinsics.json').write_text(json.dumps(intrinsics, indent=2))
    raw_points = np.array([[970., 704.], [970., 751.], [970., 785.], [922., 739.], [1022., 739.], [970., 660.]])
    points = cv2.fisheye.undistortPoints(raw_points[:, None], K, D, R=R, P=new_K)[:, 0]
    prompts = {'prompts': [{'frame_index': 0, 'object_id': 1,
                           'points': [{'x': float(x), 'y': float(y)} for x, y in points],
                           'point_labels': [1, 1, 0, 0, 0, 0]}]}
    (root/'prompts.json').write_text(json.dumps(prompts, indent=2))
    body = np.load('/data/omi_runtime/runs/pointcloud_v3_overlay_20261121_face_corrected/body_mesh.npz')
    trimesh.Trimesh(vertices=body['vertices'], faces=body['triangles'], process=False).export(root/'v3_rigid_body.ply')
    previous = json.loads(Path('/data/omi_runtime/runs/wrist_v3_pose_20261120T155953Z/result/pose.json').read_text())
    T = np.array(previous['T_model_to_camera_m'])
    R4 = np.eye(4); R4[:3, :3] = R
    (root/'initial_pose.json').write_text(json.dumps({'T_raw_from_model': T.tolist(), 'T_rect_from_model': (R4@T).tolist(),
        'source': 'Previous image-based PnP hypothesis; NOT calibrated transfer of HTML point cloud', 'ground_truth': False}, indent=2))
    report = {'input': str(video), 'input_sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
              'calibration': str(calibration), 'source_frames': indices,
              'virtual_camera': intrinsics, 'R_rect_from_raw': R.tolist(),
              'manual_prompt_raw_pixels': raw_points.tolist(), 'manual_prompt_labels': [1, 1, 0, 0, 0, 0],
              'head_to_wrist_extrinsics_available': False, 'measured_wrist_depth_available': False,
              'mesh_scale_changed': False, 'handle_excluded': True,
              'sampling_note': 'Every third original frame plus final frame; video display uses 10 fps; exact source indices preserved'}
    (root/'inputs.json').write_text(json.dumps(report, indent=2))
    print(root)


if __name__ == '__main__':
    main()
