"""Measured gripper-center correction relative to a fixed insertion axis."""
import numpy as np


def gripper_pose_errors(row, initial_audit, insertion_axis):
    tcp=np.eye(4);tcp[:3,:3]=row['tcp_rotation'];tcp[:3,3]=row['tcp_position']
    current=tcp@np.asarray(initial_audit['tcp_from_gripper'])
    aligned=np.asarray(initial_audit['aligned_gripper']);axes=aligned[:3,:3]
    axis=np.asarray(insertion_axis,dtype=float);axis/=np.linalg.norm(axis)
    denominator=float(axis@axes[:,0])
    if denominator<.9:raise ValueError('gripper forward and insertion axis inconsistent')
    displacement=current[:3,3]-aligned[:3,3]
    progress=float(displacement@axes[:,0])/denominator
    transverse=axes.T@(displacement-axis*progress)
    relative=axes.T@current[:3,:3]
    return dict(lateral_mm=float(transverse[1]*1000),vertical_mm=float(transverse[2]*1000),
        pitch_deg=float(np.rad2deg(np.arcsin(np.clip(-relative[2,0],-1.,1.)))),
        yaw_deg=float(np.rad2deg(np.arctan2(relative[1,0],relative[0,0]))),
        roll_deg=float(np.rad2deg(np.arctan2(relative[2,1],relative[2,2]))),
        angular_error_deg=float(np.rad2deg(np.arccos(np.clip((np.trace(relative)-1)/2,-1.,1.)))))
