"""Local insertion geometry from two poses in the same camera frame.

This module performs geometry only: it does not estimate poses, establish their
precision, simulate contact, or certify insertion success. Dimensions come from
the existing V3/r04 model contract, not independent physical measurements.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation


def rigid(value):
    T=np.asarray(value,dtype=float)
    if T.shape!=(4,4) or not np.isfinite(T).all():
        raise ValueError('Expected a finite 4x4 pose, translations in metres')
    R=T[:3,:3]
    if not np.allclose(T[3],[0,0,0,1],atol=1e-8):
        raise ValueError('Invalid homogeneous bottom row')
    if not np.allclose(R.T@R,np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(R),1,atol=1e-5):
        raise ValueError('Pose must be rigid; scaling/reflection is not permitted')
    return T


def frames_from_contract(contract):
    frame=contract['frame_convention']
    mouth=np.eye(4);mouth[:3,3]=np.array([frame['center_x_mm'],frame['mouth_reference_y_mm'],frame['center_z_mm']])/1000
    tip=np.eye(4);tip[1,3]=frame['module_source_tip_y_mm']/1000
    return {'units':'m','T_socket_from_mouth':mouth.tolist(),'T_module_from_tip':tip.tolist(),
            'nominal_tip_to_shoulder_m':contract['dimensions_mm']['tip_to_head_shoulder_mm']/1000,
            'tip_definition':'Virtual shaft-axis origin at foremost nominal tip Y; not a measured surface/contact point',
            'mouth_definition':'Existing metal-mouth reference, not the other open bay',
            'axes':'X transverse; +Y outward, insertion along -Y; Z up',
            'geometry_source':'Existing V3/r04 width-review model; not metrology-certified'}


def interaction_geometry(T_camera_module,T_camera_socket,frames):
    if frames.get('units')!='m':raise ValueError('Frame translations must be explicitly specified in metres')
    cm=rigid(T_camera_module);cs=rigid(T_camera_socket)
    sm=rigid(frames['T_socket_from_mouth']);mt=rigid(frames['T_module_from_tip'])
    socket_module=np.linalg.inv(cs)@cm
    mouth_tip=np.linalg.inv(sm)@socket_module@mt
    t=mouth_tip[:3,3];R=mouth_tip[:3,:3]
    insertion_axis=R@np.array([0.,-1.,0.])
    tilt=np.degrees(np.arccos(np.clip(insertion_axis@np.array([0.,-1.,0.]),-1,1)))
    depth=-float(t[1]);shoulder_distance=float(frames['nominal_tip_to_shoulder_m'])
    shoulder_point=t+R@np.array([0.,shoulder_distance,0.])
    return {'T_socket_from_module':socket_module.tolist(),'T_mouth_from_tip':mouth_tip.tolist(),
            'tip_position_in_mouth_mm':(t*1000).tolist(),
            'transverse_offset_x_mm':float(t[0]*1000),'vertical_offset_z_mm':float(t[2]*1000),
            'signed_insertion_depth_mm':depth*1000,
            'axis_tilt_deg':float(tilt),'orientation_error_rotvec_xyz_rad':Rotation.from_matrix(R).as_rotvec().tolist(),
            'nominal_shoulder_axis_point_in_mouth_mm':(shoulder_point*1000).tolist(),
            'source_assumption':'Both input poses refer to the same camera frame and time; caller must establish this',
            'hidden_tip_is_model_prediction':True,'precision_validated':False,
            'mechanical_seating':'not_determined','electrical_connection':'not_determined',
            'note':'Depth is a signed geometric coordinate; it is not proof of clearance, lack of obstruction, or seating'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--poses',type=Path,required=True,help='JSON: units=m, T_camera_from_module, T_camera_from_socket')
    p.add_argument('--contract',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();poses=json.loads(a.poses.read_text())
    if poses.get('units')!='m':raise ValueError('Input pose units must be m')
    if a.output.exists():raise FileExistsError(a.output)
    frames=frames_from_contract(json.loads(a.contract.read_text()))
    result=interaction_geometry(poses['T_camera_from_module'],poses['T_camera_from_socket'],frames)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'frames':frames,'geometry':result},indent=2))


if __name__=='__main__':main()
