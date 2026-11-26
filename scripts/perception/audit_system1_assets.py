"""Independently check saved asset-view coordinates and OpenCV fisheye projection."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def transform(T, p):
    return np.asarray(p) @ T[:3, :3].T + T[:3, 3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--wide', action='store_true')
    args = parser.parse_args()
    root = args.output
    scene = json.loads((root/'scene_packet.json').read_text())
    packet = json.loads((Path(scene['source_transfer'])/'transfer.json').read_text())
    m = packet['manifest']
    camera = next(c for c in packet['cameras'] if c['name'] == 'wrist_rgb')
    w, x, y, z = np.array(camera['quaternion']) / np.linalg.norm(camera['quaternion'])
    C = np.eye(4)
    C[:3, :3] = [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                  [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                  [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    C[:3, 3] = camera['position']
    C = np.diag([1., -1., -1., 1.]) @ np.linalg.inv(C)
    K = np.array(m['observation_projection']['K'])
    D = np.array(m['observation_projection']['D'])
    W = np.eye(4)
    W[:3, :3] = m['socket_to_world']['rotation']
    W[:3, 3] = m['socket_to_world']['position_m']
    samples = np.load(Path(scene['source_probes'])/'samples.npz', allow_pickle=False)
    pixel_errors, tcp_errors, asset_pixel_errors = [], [], []
    for case in scene['cases']:
        T = np.array(case['socket_from_tcp'])
        tcp = W @ T
        tcp_errors.append(np.linalg.norm(tcp[:3, 3]-case['summary']['actual_tcp_m'])*1000)
        np.testing.assert_allclose(transform(T, samples['predicted_tip_path'][case['id']])*1000,
                                   case['paths_mm']['pred'], atol=1e-7)
        for key, p in case['paths_mm'].items():
            xyz = transform(C @ np.linalg.inv(T), np.array(p)/1000)
            uv = cv2.fisheye.projectPoints(xyz[:, None], np.zeros(3), np.zeros(3), K, D)[0][:, 0]
            sampling = np.rint(np.linspace(0, 388, 128))
            uv = np.column_stack([np.interp(uv[:, 0]-766, sampling, np.arange(128), left=-1000, right=1000),
                                  np.interp(uv[:, 1]-566, sampling, np.arange(128), left=-1000, right=1000)])
            valid = xyz[:, 2] > .001
            pixel_errors.extend(np.linalg.norm((uv[valid]+.5)*5-.5-np.array(case['wrist_pixels'][key])[valid], axis=1))
        if args.wide:
            for key, p in case['approach_mm'].items():
                xyz = transform(C @ np.linalg.inv(T), np.array(p)/1000)
                uv = cv2.fisheye.projectPoints(xyz[:,None],np.zeros(3),np.zeros(3),K,D)[0][:,0]
                sampling = np.rint(np.linspace(0,388,128))
                uv = np.column_stack([np.interp(uv[:,0]-766,sampling,np.arange(128),left=-1000,right=1000),
                                      np.interp(uv[:,1]-566,sampling,np.arange(128),left=-1000,right=1000)])
                valid=xyz[:,2]>.001
                pixel_errors.extend(np.linalg.norm((uv[valid]+.5)*6.25-.5-np.array(case['approach_wrist_pixels'][key])[valid],axis=1))
        for view in (('wide',) if args.wide else ('overview', 'detail')):
            saved = json.loads((root/f"case_{case['id']:02d}_{view}.json").read_text())
            Tcam = np.linalg.inv(saved['camera_world'])
            width,height=(1450,850) if args.wide else (1520,400)
            for key, p in (case['approach_mm'] if args.wide else case['paths_mm']).items():
                xyz = transform(Tcam, p)
                uv = xyz[:, :2]*[width/saved['ortho_scale'], -width/saved['ortho_scale']]+[width/2, height/2]
                asset_pixel_errors.extend(np.linalg.norm(uv-saved['pixels'][key], axis=1))
            assert (root/f"case_{case['id']:02d}_{view}.png").is_file()
        suffix='_wide' if args.wide else ''
        assert (root/f"case_{case['id']:02d}{suffix}.blend").is_file()
    unchanged = {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() == h for p, h in scene['source_hashes'].items()}
    assert all(unchanged.values())
    assert max(pixel_errors) < 1e-7
    assert max(tcp_errors) < 1e-7
    assert max(asset_pixel_errors) < .01
    report = dict(cases=len(scene['cases']), source_hashes_unchanged=unchanged,
                  opencv_fisheye_max_display_pixel_difference=float(max(pixel_errors)),
                  asset_camera_max_pixel_difference=float(max(asset_pixel_errors)),
                  reconstructed_tcp_max_error_mm=float(max(tcp_errors)),
                  predicted_short_paths_match_frozen_archive=True,
                  scope='source integrity and coordinate/projection validation; no new training or execution')
    (root/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
