"""Test the actual V2D FoundationPose backend with MoGe-predicted depth.

This is not measured RGB-D and not a transfer of the head point-cloud pose.
"""
import argparse
import json
import time
import traceback
from pathlib import Path
import cv2
import numpy as np
import torch
from v2d.common.datatypes import CameraIntrinsics, DepthImage, Image, Mask, Transform3d
from v2d.mesh.lib.mesh import Mesh
from v2d.foundation_pose.lib.foundation_pose_tracker import FoundationPoseTracker


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--weights', required=True)
    a = p.parse_args(); root = a.run
    torch.manual_seed(7); np.random.seed(7)
    k = CameraIntrinsics.load(str(root/'intrinsics.json'))
    factor = .5
    intr = CameraIntrinsics(k.fx*factor, k.fy*factor, k.cx*factor, k.cy*factor, 480, 480)
    model = Mesh.load(str(root/'v3_rigid_body.ply'))
    tracker = FoundationPoseTracker(model, a.weights, backend='nvlabs_pytorch')
    initial = np.array(json.loads((root/'initial_pose.json').read_text())['T_rect_from_model'])
    indices = [0, 10, 20, 30, 40, 50, 60]
    results = {'backend': tracker.runtime_info, 'depth_source': 'MoGe prediction, unscaled; not measured',
               'initial_pose_source': 'Previous image-based PnP hypothesis, not head cloud',
               'mesh_scale_changed': False, 'handle_excluded': True, 'variants': {}}
    for variant in ['initialized_refinement', 'global_registration']:
        records = []
        try:
            for i in indices:
                rgb = cv2.cvtColor(cv2.imread(str(root/'rectified'/f'{i:06d}.jpg')), cv2.COLOR_BGR2RGB)
                rgb = Image(cv2.resize(rgb, (480, 480)))
                depth = DepthImage.load(str(root/'depth'/f'{i:06d}.png')).depth
                depth = cv2.resize(depth, (480, 480), interpolation=cv2.INTER_NEAREST)
                depth[~np.isfinite(depth)] = 0
                depth = DepthImage(depth.astype(np.float32))
                mask = Mask(cv2.resize(cv2.imread(str(root/'masks/1'/f'{i:06d}.png'), 0), (480, 480), interpolation=cv2.INTER_NEAREST)>0)
                t0 = time.perf_counter()
                if i == 0 and variant == 'global_registration':
                    pose = tracker.register(rgb, depth, mask, intr, iteration=5)
                else:
                    if i == 0:
                        tracker.reset_to_pose(Transform3d.from_matrix(initial))
                    pose = tracker.track_one(rgb, depth, intr, iteration=3)
                record = {'frame': i, 'T_rect_from_model': pose.to_matrix().tolist(),
                          'seconds': time.perf_counter()-t0,
                          'sam2_mask_iou': tracker._mask_iou(mask, intr, pose),
                          'predicted_depth_median_m': float(np.median(depth.depth[mask.mask]))}
                records.append(record)
                results['variants'][variant] = records
                (root/'foundationpose_results.json').write_text(json.dumps(results, indent=2))
                print(variant, i, record['sam2_mask_iou'], pose.to_matrix()[:3, 3], flush=True)
        except Exception:
            results[variant+'_error'] = traceback.format_exc()
            (root/'foundationpose_results.json').write_text(json.dumps(results, indent=2))
            print(traceback.format_exc(), flush=True)
            torch.cuda.empty_cache()
    (root/'foundationpose_results.json').write_text(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
