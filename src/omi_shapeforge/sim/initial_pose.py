"""Explicit fixed-grasp reset poses; task targets and runtime actions stay fixed."""
import numpy as np
from .isaac_contact_kinematics import Kinematics, local_pose, transform, axis_rotation


def solve_reset_ik(solver, kin, q, target):
    """Numerical IK continuation only; no physical action or limit bypass."""
    start=kin.tcp(q);relative=target[:3,:3]@start[:3,:3].T
    angle=float(np.arccos(np.clip((np.trace(relative)-1)/2,-1.,1.)))
    axis=np.array([relative[2,1]-relative[1,2],relative[0,2]-relative[2,0],relative[1,0]-relative[0,1]])
    if np.linalg.norm(axis)<1e-10:
        axis=np.linalg.eigh((relative+relative.T)/2)[1][:,-1] if angle>1e-7 else np.array([1.,0.,0.])
    else:axis/=np.linalg.norm(axis)
    delta=target[:3,3]-start[:3,3]
    count=max(1,int(np.ceil(np.linalg.norm(delta)/.003)),int(np.ceil(angle/np.deg2rad(.5))))
    solved=dict(q)
    for i in range(1,count+1):
        fraction=i/count
        intermediate=transform(start[:3,3]+fraction*delta,axis_rotation(axis,fraction*angle)@start[:3,:3])
        solved=solver.solve(solved,intermediate)
    return solved,dict(numerical_ik_stages=count,maximum_requested_segment_mm=3.,maximum_requested_segment_deg=.5,
                       native_continuity_and_joint_limits_preserved=True,physical_preparation_actions=0)


def validate_initial_pose(spec):
    limits = {'gap_mm': (5., 40.), 'lateral_mm': (-10., 10.), 'vertical_mm': (-5., 5.),
              'pitch_deg': (-5., 5.), 'yaw_deg': (-5., 5.)}
    if not isinstance(spec, dict) or set(spec) != set(limits):
        raise ValueError('initial pose requires gap/lateral/vertical_mm and pitch/yaw_deg')
    result = {k: float(v) for k, v in spec.items()}
    if any(not np.isfinite(v) or not limits[k][0] <= v <= limits[k][1] for k, v in result.items()):
        raise ValueError('initial pose exceeds registered evaluation bounds')
    return result


def gripper_center_from_mesh(packet, meshes):
    """Nominal contact-pad midpoint in true TCP coordinates, X forward, Z up."""
    kin = Kinematics(packet)
    q = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
    frames = kin.frames(q); inv_tcp = np.linalg.inv(kin.tcp(q))
    centers = []
    for name in ('wrist_tool_022', 'wrist_tool_033'):
        geom = next(g for g in packet['geoms'] if g['name'] == name)
        t = inv_tcp@frames[geom['body']]@local_pose(geom)
        v = meshes[f"v{geom['mesh']}"]@t[:3, :3].T+t[:3, 3]
        centers.append((v.min(0)+v.max(0))/2)
    return transform(np.mean(centers, axis=0), np.array([[0., 0., 1.], [0., -1., 0.], [1., 0., 0.]]))


def initial_tcp_target(manifest, tcp_from_gripper, spec):
    spec = validate_initial_pose(spec)
    slot = transform(manifest['socket_to_world']['position_m'], np.asarray(manifest['socket_to_world']['rotation']))
    tool_module = transform(manifest['tool_to_module']['position_m'], np.asarray(manifest['tool_to_module']['rotation']))
    tip_tcp = (tool_module@np.array([0., manifest['leading_tip_y_mm']/1000, 0., 1.]))[:3]
    cx, cz = manifest['nominal_module_center_xz_mm']
    aligned_tip = (slot@np.array([cx/1000, (manifest['mouth_y_mm']+spec['gap_mm'])/1000, cz/1000, 1.]))[:3]
    rotation = np.asarray(manifest['goal_tcp_rotation'])
    aligned_tcp = transform(aligned_tip-rotation@tip_tcp, rotation)
    gripper = aligned_tcp@tcp_from_gripper
    axes = gripper[:3, :3].copy()
    gripper[:3, 3] += axes@np.array([0., spec['lateral_mm']/1000, spec['vertical_mm']/1000])
    yaw,pitch=np.deg2rad([spec['yaw_deg'],spec['pitch_deg']])
    cy,sy=np.cos(yaw),np.sin(yaw);cp,sp=np.cos(pitch),np.sin(pitch)
    rz=np.array([[cy,-sy,0.],[sy,cy,0.],[0.,0.,1.]])
    ry=np.array([[cp,0.,sp],[0.,1.,0.],[-sp,0.,cp]])
    gripper[:3, :3] = axes@rz@ry
    target = gripper@np.linalg.inv(tcp_from_gripper)
    return target, dict(request=spec, tcp_from_gripper=tcp_from_gripper.tolist(),
        target_tcp=target.tolist(), target_gripper=gripper.tolist(),
        aligned_gripper=(aligned_tcp@tcp_from_gripper).tolist(),
        frame='fixed contact-pad midpoint; X forward, Y left, Z up; yaw then intrinsic pitch',
        gap_definition='aligned tip gap before rotation about gripper center; actual tilted gap audited separately')
