"""Audit the film asset set and build a separate r15/GC-r01 PhysX packet.

No source meshes are authored or overwritten. The insertion channel/task retain
their latest validated contract; the gripper, texture transport and grasp change.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
import trimesh

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from omi_shapeforge.sim.isaac_contact_kinematics import Kinematics, local_pose


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pose(T):
    return dict(position=T[:3, 3].tolist(), quaternion=np.roll(Rotation.from_matrix(T[:3, :3]).as_quat(), 1).tolist())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    wva = json.loads((ROOT/'manifests/wrist_visual_wva01_20261122.json').read_text())
    gc_ref = json.loads((ROOT/'manifests/wrist_contact_closure_20261122.json').read_text())
    tool = json.loads(Path(wva['assets']['tool']['manifest']).read_text())
    gc = json.loads(Path(gc_ref['manifest']).read_text())
    assert sha(wva['assets']['tool']['manifest']) == wva['assets']['tool']['manifest_sha256']
    assert sha(gc_ref['manifest']) == gc_ref['manifest_sha256']
    old = json.loads((a.source/'transfer.json').read_text())
    assert sha(a.source/'meshes.npz') == old['meshes_sha256']
    packet = deepcopy(old)
    arrays = dict(np.load(a.source/'meshes.npz'))
    protected = {str(p): sha(p) for p in [a.source/'transfer.json', a.source/'meshes.npz',
                 Path(wva['assets']['tool']['manifest']), Path(gc_ref['manifest']), Path(gc_ref['scene'])]}
    kin = Kinematics(packet)
    ids = {b['name']: b['id'] for b in packet['bodies']}
    q = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
    q['Arm_L10_Joint'] = q['Arm_L11_Joint'] = tool['integration_joint_reference_qpos_m']
    frames = kin.frames(q)
    tcp = frames[ids['TCP_Link_L']]
    next_mesh = max(int(k[1:]) for k in arrays if k.startswith('v'))+1
    material = packet['manifest']['visual_material_overrides']
    geoms = {g['name']: g for g in packet['geoms']}
    textures = []
    for i, part in enumerate(tool['parts']):
        g = geoms[f'wrist_tool_{i:03d}']
        mesh_path = Path(part['mesh'])
        protected[str(mesh_path)] = sha(mesh_path)
        mesh = trimesh.load(mesh_path, force='mesh', process=False)
        mesh_id = next_mesh
        next_mesh += 1
        arrays[f'v{mesh_id}'] = np.asarray(mesh.vertices, np.float32)
        arrays[f'f{mesh_id}'] = np.asarray(mesh.faces, np.int32)
        T = np.linalg.inv(frames[g['body']])@tcp
        g.update(mesh=mesh_id, **pose(T), rgba=part.get('mujoco_rgba', part['color']))
        override = dict(color_linear=part['color'][:3], metallic=part.get('metallic', 0.),
                        roughness=part.get('roughness', .5), source_part=part['name'], asset=tool['asset_id'])
        if part.get('base_color_texture'):
            uv = np.asarray(mesh.visual.uv, np.float32)
            assert uv.shape == (len(mesh.vertices), 2)
            arrays[f'uv{mesh_id}'] = uv
            arrays[f'fuv{mesh_id}'] = np.asarray(mesh.faces, np.int32)
            tex = Path(part['base_color_texture'])
            protected[str(tex)] = sha(tex)
            override['base_color_texture'] = str(tex)
            override['base_color_texture_sha256'] = sha(tex)
            textures.append(dict(geom=g['name'], texture=str(tex), sha256=sha(tex), uv_faces=len(mesh.faces)))
        material[g['name']] = override
    gc_model = mujoco.MjModel.from_xml_path(gc_ref['scene'])
    gc_data = mujoco.MjData(gc_model)
    mujoco.mj_resetDataKeyframe(gc_model, gc_data, gc_model.key('gravity_hold').id)
    mujoco.mj_forward(gc_model, gc_data)
    def gc_frame(name):
        i = gc_model.body(name).id
        T = np.eye(4)
        T[:3, :3] = gc_data.xmat[i].reshape(3, 3)
        T[:3, 3] = gc_data.xpos[i]
        return T
    held = np.linalg.inv(gc_frame('audit_tool'))@gc_frame('sim_module')
    finger_drives = {}
    for side, joint_name, part_index in [('left', 'Arm_L10_Joint', 22), ('right', 'Arm_L11_Joint', 33)]:
        j = next(j for j in packet['joints'] if j['name'] == joint_name)
        original_axis = tcp[:3, :3].T@frames[j['body']][:3, :3]@j['axis']
        desired_axis = np.array([0, -1 if side == 'left' else 1, 0])
        sign = float(original_axis@desired_axis)
        assert abs(abs(sign)-1) < 1e-6
        sign = 1 if sign > 0 else -1
        reference = tool['integration_joint_reference_qpos_m']
        initial = reference+float(gc_data.joint('jaw_'+side).qpos[0])/sign
        finger_drives[joint_name] = dict(reference=reference, sign=sign, closed_target=reference-.0015/sign,
                                       open_target=reference+.010/sign, initial=initial)
        packet['initial_qpos'][j['qpos_index']] = initial
        q[joint_name] = initial
        j.update(kp=2000., kd=2., max_force=4.)
        # Same visible black pad mesh as GC-r01, with separate physical material.
        collider = deepcopy(geoms[f'wrist_tool_{part_index:03d}'])
        collider.update(name=f'grasp_pad_{side}_collision', group=3, contact=True,
                        friction=[0., .003, .0001], rgba=[.05, .05, .05, 0.], contact_offset_m=.000005,
                        torsional_patch_radius_m=.003)
        packet['geoms'].append(collider)
    # Legacy insertion proxies stop at the shoulder: they do not cover the rear
    # body held by the jaws. Port that rear region from the original decomposed
    # module geometry; leave all six insertion/channel boxes unchanged.
    pad_frames=kin.frames(q)
    tcp_reference=np.linalg.inv(kin.tcp(q))
    pads=trimesh.collision.CollisionManager()
    for g in packet['geoms']:
        if g['name'].startswith('grasp_pad_'):
            mesh=trimesh.Trimesh(arrays[f'v{g["mesh"]}'],arrays[f'f{g["mesh"]}'],process=False)
            pads.add_object(g['name'],mesh,tcp_reference@pad_frames[g['body']]@local_pose(g))
    rear_colliders=[]
    for g in list(packet['geoms']):
        if g['body']!=ids['sim_module'] or g['group']<3 or g['contact'] or g['kind']!=7:
            continue
        T=local_pose(g)
        vertices=arrays[f'v{g["mesh"]}']@T[:3,:3].T+T[:3,3]
        faces=arrays[f'f{g["mesh"]}']
        cut=.017
        if vertices[:,1].max()<cut:continue
        clipped=[v for v in vertices if v[1]>=cut-1e-12]
        for x,y in vertices[np.unique(np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)]:
            if (x[1]-cut)*(y[1]-cut)<0:
                clipped.append(x+(y-x)*((cut-x[1])/(y[1]-x[1])))
        clipped=np.unique(np.round(np.asarray(clipped),12),axis=0)
        if len(clipped)<4 or np.linalg.matrix_rank(clipped-clipped.mean(0))<3:continue
        hull=ConvexHull(clipped)
        if hull.volume<1e-13:continue
        mesh=trimesh.Trimesh(clipped,hull.simplices,process=False)
        distance=float(pads.min_distance_single(mesh,held))
        if distance>.0002:continue
        mesh_id=next_mesh;next_mesh+=1
        arrays[f'v{mesh_id}']=clipped.astype(np.float32)
        arrays[f'f{mesh_id}']=hull.simplices.astype(np.int32)
        name=f'sim_module_grasp_rear_{len(rear_colliders):03d}'
        added=deepcopy(g)
        added.update(name=name,mesh=mesh_id,position=[0.,0.,0.],quaternion=[1.,0.,0.,0.],
                     contact=True,friction=[0.,.003,.0001],collision_role='grasp_rear',torsional_patch_radius_m=.003,
                     contact_offset_m=.000005)
        packet['geoms'].append(added)
        rear_colliders.append(dict(name=name,source_geom=g['name'],rear_cut_y_m=cut,
                                   distance_to_closed_pad_m=distance,source_geometry_modified=False))
    assert rear_colliders,'rear module contact geometry must reach the pads'
    socket = np.eye(4)
    socket[:3, :3] = packet['manifest']['socket_to_world']['rotation']
    socket[:3, 3] = packet['manifest']['socket_to_world']['position_m']
    manifest = packet['manifest']
    desired_rotation = socket[:3, :3]@held[:3, :3].T
    nominal = np.array(manifest['nominal_module_center_xz_mm'])/1000
    def tcp_target(depth):
        local = np.array([nominal[0], (manifest['mouth_y_mm']-manifest['leading_tip_y_mm']-depth)/1000, nominal[1]])
        return socket[:3, 3]+socket[:3, :3]@local-desired_rotation@held[:3, 3]
    arm = [next(j for j in packet['joints'] if j['name'] == f'Arm_L{i}_Joint') for i in range(1, 8)]
    limits = np.array([j['limits'] for j in arm])
    start = np.array([q[j['name']] for j in arm])
    def error(values):
        values_q = dict(q, **dict(zip([j['name'] for j in arm], values)))
        T = kin.tcp(values_q)
        return np.r_[T[:3, 3]-tcp_target(-5.), Rotation.from_matrix(T[:3, :3]@desired_rotation.T).as_rotvec()*.1]
    sol = least_squares(error, start, bounds=(limits[:, 0]+1e-6, limits[:, 1]-1e-6),
                        xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=600)
    assert np.linalg.norm(error(sol.x)) < 1e-7
    for j, value in zip(arm, sol.x):
        q[j['name']] = float(value)
        packet['initial_qpos'][j['qpos_index']] = float(value)
    new_frames = kin.frames(q)
    new_tcp = kin.tcp(q)
    module = packet['bodies'][ids['sim_module']]
    Tmodule = new_tcp@held
    module.update(parent=0, **pose(Tmodule))
    gid = gc_model.body('sim_module').id
    module.update(mass=float(gc_model.body_mass[gid]), inertia=gc_model.body_inertia[gid].tolist(),
                  com=gc_model.body_ipos[gid].tolist(), inertia_quaternion=gc_model.body_iquat[gid].tolist(), gravcomp=0.)
    # Robot world frames are the ZERO-joint PhysX reference, not the initial
    # articulated pose. Preserve them or joint positions would be applied twice.
    new_frames = Kinematics(packet).frames(q)
    for b in packet['bodies']:
        if b['name'] in ('sim_module','module_u_handle'):
            b.update(world_position=new_frames[b['id']][:3, 3].tolist(), world_rotation=new_frames[b['id']][:3, :3].tolist())
    packet['free_bodies'] = ['sim_module']
    manifest.update(wrist_tool_asset=tool['asset_id'], wrist_tool_asset_manifest=wva['assets']['tool']['manifest'],
                    wrist_tool_asset_manifest_sha256=wva['assets']['tool']['manifest_sha256'],
                    tool_to_module=dict(position_m=held[:3, 3].tolist(), rotation=held[:3, :3].tolist()),
                    preinsert_tcp_position=tcp_target(-5.).tolist(), seated_tcp_position=tcp_target(manifest['shoulder_depth_mm']).tolist(),
                    goal_tcp_position=tcp_target(manifest['shoulder_depth_mm']+.1).tolist(), goal_tcp_rotation=desired_rotation.tolist(),
                    initial_qpos=packet['initial_qpos'], grasp='free module held by physical black-pad contacts and friction',
                    asset_contract='wva01-gc01-free-grasp-v1', wrist_tool_collision_enabled=True,
                    grasp_contract=dict(version='isaac-gc01-free-module-v1', source_manifest=gc_ref['manifest'],
                                        source_sha256=gc_ref['manifest_sha256'], finger_drives=finger_drives,
                                        settle_seconds=3., minimum_side_force_N=.1, maximum_slip_mm=.1,
                                        maximum_rotation_deg=.5,solver_required='TGS',torsional_patch_radius_m=.003,
                                        spin_contact_model='bounded-condim4-soft-finger-v2',spin_time_constant_s=.002,spin_normal_filter_s=.005,
                                        sliding_friction_coefficient=1.,tangential_time_constant_s=.002,
                                        grasp_contact_offset_m=.000005,
                                        source_engine='MuJoCo local grasp; PhysX port needs fresh validation'),
                    source_visual_release='WVA-01', contact_grasp_validated=False, new_tool_contact_path_validated=False,
                    new_tool_training_validated=False)
    # Camera pose and fisheye calibration already match r15; retain them exactly.
    assert np.allclose(manifest['cameras']['wrist_rgb']['optical_position_m'], tool['camera']['optical_position_m'])
    assert np.allclose(manifest['observation_projection']['K'], tool['observation_projection']['K'])
    assert np.allclose(manifest['observation_projection']['D'], tool['observation_projection']['D'])
    packet['limitations'] = ['Free-grasp PhysX port of GC-r01 requires independent validation',
                            'Robot inertias and camera calibration remain uncalibrated; no learned-policy claim',
                            'Socket six-box smooth-guide contact model is an explicit task hypothesis',
                            'Green handle remains visual-only; no electrical or latch model']
    packet['updated_asset_sources_sha256'] = protected
    np.savez_compressed(a.output/'meshes.npz', **arrays)
    packet['meshes_sha256'] = sha(a.output/'meshes.npz')
    (a.output/'transfer.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2))
    original_urdf = Path(old['manifest']['source_urdf'])
    current_urdf = ROOT.parent/'omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/omi_ws/src/marvin_stand_viz/urdf/marvin_stand.urdf'
    audit = dict(previous_transfer=str(a.source), previous_gripper=old['manifest']['wrist_tool_asset'],
                 new_gripper=tool['asset_id'], gripper_parts=len(tool['parts']), textures=textures,
                 module='OM-001/V4 r08: already current, visual geometry preserved',
                 socket='SIM-r06 visual + latest staged/smooth-guide collision contract: preserved',
                 camera='r15 camera extrinsics and K/D equal previous values; preserved',
                 robot_urdf_current_file_exists=current_urdf.exists(),
                 robot_urdf_matches_current=sha(original_urdf)==sha(current_urdf) if current_urdf.exists() else None,
                 grasp_updated='GC-r01 closed-state mount, physical black pads, free dynamic module',
                 source_inputs_sha256=protected, original_sources_unchanged=all(sha(p)==s for p,s in protected.items()),
                 collision_task_thresholds_changed=False, fixed_module_attachment_removed=True,
                 rear_grasp_collision_geometry=rear_colliders,
                 matching_geometry='PCG-01 is separate matching geometry, not a replacement visual/physics release',
                 nominal_tool_to_module=manifest['tool_to_module'], initial_ik_error=error(sol.x).tolist())
    (a.output/'asset_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in audit.items() if k not in ['source_inputs_sha256', 'nominal_tool_to_module']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
