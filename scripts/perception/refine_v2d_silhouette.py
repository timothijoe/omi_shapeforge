"""Custom bounded pixel refinement driven by V2D SAM2 masks, fixed V3 geometry.

This downstream optimizer is our adapter, not FoundationPose or a V2D feature.
"""
import argparse
import json
import time
from pathlib import Path
import cv2
import numpy as np
import torch
import trimesh
import nvdiffrast.torch as dr


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--all-frames', action='store_true')
    a = p.parse_args(); root = a.run
    device = 'cuda'; side = 480
    cal = json.loads((root/'intrinsics.json').read_text())
    fx, fy, cx, cy = [cal[x]/2 for x in ['fx', 'fy', 'cx', 'cy']]
    mesh = trimesh.load(root/'v3_rigid_body.ply', process=False)
    vertices = torch.tensor(mesh.vertices, dtype=torch.float32, device=device)
    faces = torch.tensor(mesh.faces, dtype=torch.int32, device=device)
    ctx = dr.RasterizeCudaContext()
    T = np.array(json.loads((root/'initial_pose.json').read_text())['T_rect_from_model'])
    R0 = torch.tensor(T[:3, :3], dtype=torch.float32, device=device)
    t0 = torch.tensor(T[:3, 3], dtype=torch.float32, device=device)

    def pose(parameters):
        w = torch.tanh(parameters[:3])*.20  # bound each rotation increment to 11.5 deg
        z = w[0]*0
        skew = torch.stack([z, -w[2], w[1], w[2], z, -w[0], -w[1], w[0], z]).reshape(3, 3)
        R = torch.matrix_exp(skew) @ R0
        t = t0 + torch.tanh(parameters[3:])*torch.tensor([.006, .006, .015], device=device)
        return R, t

    def silhouette(R, t):
        v = vertices @ R.T + t
        x, y, z = v.unbind(1)
        clip = torch.stack([2*fx/side*x+(2*cx/side-1)*z,
                            -2*fy/side*y+(1-2*cy/side)*z,
                            1.00002*z-.00200002, z], dim=1)[None]
        rast, _ = dr.rasterize(ctx, clip, faces, resolution=[side, side])
        hard = (rast[..., 3:] > 0).float()
        soft = dr.antialias(hard, rast, clip, faces)[0, ..., 0].flip(0)
        return soft

    records = []
    mask_output = root/'pixel_all_masks' if a.all_frames else root
    mask_output.mkdir(exist_ok=True)
    frame_indices = range(len(list((root/'masks/1').glob('*.png')))) if a.all_frames else [0, 10, 20, 30, 40, 50, 60]
    for i in frame_indices:
        m = cv2.imread(str(root/'masks/1'/f'{i:06d}.png'), 0)
        target = torch.tensor(cv2.resize(m, (side, side), interpolation=cv2.INTER_NEAREST)>0, device=device)
        param = torch.zeros(6, device=device, requires_grad=True)
        opt = torch.optim.Adam([param], lr=.035)
        def iou(a):
            a = a > .5
            return float((a & target).sum() / (a | target).sum().clamp(min=1))
        before = iou(silhouette(R0, t0))
        start = time.perf_counter(); best_loss = float('inf'); best = None
        for step in range(220):
            opt.zero_grad(); R, t = pose(param); pred = silhouette(R, t)
            loss = ((pred-target.float())**2).sum()/target.sum().clamp(min=1)
            loss = loss + .002*torch.tanh(param).square().sum()
            value = float(loss.detach())
            if value < best_loss:
                best_loss = value; best = (R.detach().clone(), t.detach().clone())
            loss.backward(); opt.step()
        R, t = best; pred = silhouette(R, t)
        out = np.eye(4); out[:3, :3] = R.cpu().numpy(); out[:3, 3] = t.cpu().numpy()
        record = {'frame': i, 'T_rect_from_model': out.tolist(), 'sam2_iou_before': before,
                  'sam2_iou_after': iou(pred), 'seconds': time.perf_counter()-start,
                  'translation_change_mm': float(torch.linalg.norm(t-t0)*1000)}
        records.append(record); print(record, flush=True)
        cv2.imwrite(str(mask_output/f'pixel_refined_mask_{i:06d}.png'), (pred.detach().cpu().numpy()>.5).astype(np.uint8)*255)
    result_name = 'pixel_refinement_all_frames.json' if a.all_frames else 'pixel_refinement_results.json'
    (root/result_name).write_text(json.dumps({'method': 'Our bounded silhouette optimizer using V2D SAM2 masks',
        'initial_source': 'Previous single-image PnP, no head-camera extrinsics', 'scale_fixed': True,
        'metrics_are_fitting_metrics_not_ground_truth': True, 'records': records}, indent=2))


if __name__ == '__main__':
    main()
