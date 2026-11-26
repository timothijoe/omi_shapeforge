"""Check orientation glyphs against production reference features and OpenCV."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose
from omi_hil_rl.training.hierarchical_insertion.reference import ReferenceProvider,ReferenceConfig,pose,exp_rotation


def transform(T,p):return np.asarray(p)@T[:3,:3].T+T[:3,3]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);root=p.parse_args().output
    report=json.loads((root/'orientation.json').read_text());source=Path(report['source'])
    old=json.loads((source/'scene_packet.json').read_text())
    packet=json.loads((Path(report['source_transfer'])/'transfer.json').read_text());m=packet['manifest']
    data=np.load(Path(old['source_probes'])/'samples.npz',allow_pickle=False)
    module=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])
    gripper=report.get('frame_name')=='gripper-center-forward'
    display=None if gripper else np.array(report.get('module_from_display',pose([0,m['leading_tip_y_mm']/1000,0],np.eye(3))))
    tcp_from_display=np.array(report['tcp_from_display']) if 'tcp_from_display' in report else module@display
    if gripper:
        np.testing.assert_allclose(tcp_from_display[:3,:3],[[0,0,1],[0,-1,0],[1,0,0]],atol=1e-12)
        # Independently check against the already exported TCP-space tool meshes.
        arrays=np.load(source/'asset_geometry.npz',allow_pickle=False)
        centers=[]
        for name in report['center_geometry']['parts']:
            idx=next(i for i,g in enumerate(old['parts']) if g['name']==name)
            v=arrays[f'v{idx}'];centers.append((v.min(0)+v.max(0))/2)
        np.testing.assert_allclose(tcp_from_display[:3,3],np.mean(centers,axis=0),atol=1e-12)
        # A changed module-to-TCP relationship must not move the gripper frame.
        from render_system1_orientation import gripper_center_frame
        shifted=copy.deepcopy(packet)
        shifted['manifest']['tool_to_module']['position_m']=[.1,.2,.3]
        shifted['manifest']['tool_to_module']['rotation']=exp_rotation([.2,-.3,.4]).tolist()
        for b in shifted['bodies']:
            if b['name']=='sim_module':
                b['position']=[.1,.2,.3];b['quaternion']=[1,0,0,0]
        independent,_=gripper_center_frame(shifted,Path(report['source_transfer']))
        np.testing.assert_allclose(independent,tcp_from_display,atol=1e-12)
    if report.get('frame_name')=='body-center-forward':
        np.testing.assert_allclose(display[:3,:3],[[0,1,0],[-1,0,0],[0,0,1]],atol=1e-12)
        arrays=np.load(Path(report['source_transfer'])/'meshes.npz',allow_pickle=False)
        geoms={g['name']:g for g in packet['geoms']}
        bounds=[]
        for name in report['center_geometry']['parts']:
            g=geoms[name];bounds.append(transform(local_pose(g),arrays[f"v{g['mesh']}"]))
        vertices=np.concatenate(bounds)
        np.testing.assert_allclose(display[:3,3],(vertices.min(0)+vertices.max(0))/2,atol=1e-12)
        assert np.linalg.det(display[:3,:3])>.999999
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    C=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera))
    K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    origin_error=[];matrix_error=[];pixel_error=[];axis_error=[]
    count=0
    for case in report['cases']:
        i=case['id'];T=np.array(case['socket_from_tcp'])
        for key,array in [('pred','predicted_socket'),('gt','target_socket')]:
            if key not in case['frames']:continue
            socket=data[array][i];provider=ReferenceProvider(m)
            entry=socket@provider.local_entry;goal=socket@provider.local_goal
            axis=goal[:3,3]-entry[:3,3];length=np.linalg.norm(axis);axis/=length
            progress=-entry[:3,3]@axis
            distance=np.linalg.norm(entry[:3,3]) if progress<0 else length-np.clip(progress,0,length)
            provider=ReferenceProvider(m,ReferenceConfig(points=32,spacing_mm=max(distance*1000/32,1e-8)))
            provider.active=dict(start=np.eye(4),entry=entry,goal=goal,capture_step=0,version=1)
            vec=provider.features(np.eye(4),0)[:32*6].reshape(32,6)
            for f in case['frames'][key]:
                j=f['index']
                if j==0:
                    expected=np.eye(4) if progress<0 else pose(entry[:3,3]+axis*np.clip(progress,0,length),goal[:3,:3])
                else:expected=pose(vec[j-1,:3]*.01,exp_rotation(vec[j-1,3:]*.1))
                ref=T@expected@tcp_from_display
                origin=ref[:3,3]*1000
                origin_error.append(np.linalg.norm(origin-f['origin_mm']))
                matrix_error.append(np.max(np.abs(ref[:3,:3]-f['rotation'])))
                xyz=np.array(f['points_mm']);v=xyz[1:]-xyz[0]
                axis_error.append(np.max(np.abs(v/f['axis_length_mm']-np.array(f['rotation']).T)))
                xyzcam=transform(C@np.linalg.inv(T),xyz/1000)
                uv=cv2.fisheye.projectPoints(xyzcam[:,None],np.zeros(3),np.zeros(3),K,D)[0][:,0]
                samples=np.rint(np.linspace(0,388,128))
                uv=np.column_stack([np.interp(uv[:,0]-766,samples,np.arange(128),left=-1000,right=1000),np.interp(uv[:,1]-566,samples,np.arange(128),left=-1000,right=1000)])
                valid=xyzcam[:,2]>.001
                pixel_error.extend(np.linalg.norm((uv[valid]+.5)*6.25-.5-np.array(f['wrist_pixels'])[valid],axis=1))
                count+=1
    unchanged={path:hashlib.sha256(Path(path).read_bytes()).hexdigest()==h for path,h in report['source_hashes'].items()}
    assert all(unchanged.values())
    assert max(origin_error)<.001 and max(matrix_error)<1e-6 and max(axis_error)<1e-10 and max(pixel_error)<1e-7
    result=dict(cases=len(report['cases']),coordinate_frames=count,source_hashes_unchanged=unchanged,
                production_reference_max_origin_error_mm=float(max(origin_error)),
                production_reference_max_rotation_matrix_error=float(max(matrix_error)),
                axis_direction_max_error=float(max(axis_error)),opencv_fisheye_max_display_pixel_difference=float(max(pixel_error)),
                gripper_frame_independent_of_module_pose=gripper,
                scope='orientation rendering checks; no new training or policy execution')
    (root/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
