"""Audit sim label provenance, grouped splits, FK and rendered mesh coordinates."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from PIL import Image
from generate_sim_wrist_dataset import SCENE,transform,camera_transform


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit(folder,geometry_report):
    if not (folder/'complete.json').is_file():raise ValueError('Capture not finalized')
    config=json.loads((folder/'config.json').read_text());rows=[json.loads(s) for s in (folder/'records.jsonl').read_text().splitlines()];episodes=json.loads((folder/'episodes.json').read_text());cal=json.loads((folder/'calibration.json').read_text())
    complete=json.loads((folder/'complete.json').read_text())
    if len(rows)!=complete['frames'] or len(episodes)!=complete['clips']:raise ValueError('Incomplete catalog')
    ep={e['episode']:e for e in episodes};seen={};frame_hashes={};matrix_max=0.
    for r in rows:
        if r['episode'] not in ep or r['split']!=ep[r['episode']]['split']:raise ValueError('Episode split mismatch')
        if r['episode'] in seen and seen[r['episode']]!=r['split']:raise ValueError('Episode leakage')
        seen[r['episode']]=r['split'];image=folder/r['image'];h=sha(image)
        if h!=r['image_sha256']:raise ValueError('Image hash mismatch')
        if h in frame_hashes and frame_hashes[h]!=r['split']:raise ValueError('Identical RGB image across splits')
        frame_hashes[h]=r['split']
        with Image.open(image) as im:
            if im.size!=(cal['image_width'],cal['image_height']):raise ValueError('Image calibration resolution mismatch')
        for name in ['module','socket']:
            T=np.array(r['T_camera_from_'+name]);error=max(float(np.max(abs(T[:3,:3].T@T[:3,:3]-np.eye(3)))),abs(np.linalg.det(T[:3,:3])-1))
            matrix_max=max(matrix_max,error)
            if error>1e-8 or not np.isfinite(T).all() or T[2,3]<=0:raise ValueError('Invalid pose matrix')
    grasp_keys={}
    for e in episodes:
        key=tuple(np.round(e['grasp_translation_mm']+e['grasp_rpy_deg'],8))
        if key in grasp_keys and grasp_keys[key]!=e['split']:raise ValueError('Same grasp across splits')
        grasp_keys[key]=e['split']
        if max(e['qpos_range_rad'])<.001:raise ValueError('Arm did not move')
    model=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'));model.opt.disableflags|=int(mujoco.mjtDisableBit.mjDSBL_CONTACT);d=mujoco.MjData(model);source=json.loads((SCENE/'robot_manifest.json').read_text())
    qids=model.jnt_qposadr[[model.joint(f'Arm_L{i}_Joint').id for i in range(1,8)]];mb=model.body('sim_module').id;sb=model.body('sim_socket').id;cam=model.camera('wrist_rgb').id
    base_p=model.body_pos[mb].copy();base_R=Rotation.from_quat(np.roll(model.body_quat[mb],-1)).as_matrix();pivot=np.array([0,.025,0])
    chosen=[]
    for split in ['train','val','test']:
        rs=[r for r in rows if r['split']==split]
        chosen.extend(rs[i] for i in sorted(set([0,len(rs)//2,len(rs)-1])))
    fk_max=0.
    for r in chosen:
        e=ep[r['episode']];R=Rotation.from_euler('xyz',e['grasp_rpy_deg'],degrees=True).as_matrix();delta=np.array(e['grasp_translation_mm'])/1000+pivot-R@pivot
        model.body_pos[mb]=base_p+base_R@delta;model.body_quat[mb]=np.roll(Rotation.from_matrix(base_R@R).as_quat(),1)
        d.qpos[:]=source['initial_qpos'];d.qpos[qids]=r['left_arm_qpos'];mujoco.mj_forward(model,d);Twc=camera_transform(d,cam)
        for name,b in [('module',mb),('socket',sb)]:fk_max=max(fk_max,float(np.max(abs(np.linalg.inv(Twc)@transform(d,b)-np.array(r['T_camera_from_'+name])))))
    if fk_max>1e-9:raise ValueError('Saved label does not match independent FK reconstruction')
    # Verify compiler mesh centering/rotation has not invalidated the original
    # authored object coordinate system used by the surface-point templates.
    xml=ET.parse(folder/'scene.xml').getroot();mesh_files={x.get('name'):Path(x.get('file')) for x in xml.findall('asset/mesh')};mesh_errors={}
    for g in range(model.ngeom):
        name=model.geom(g).name or ''
        if not (name.startswith(('sim_module_','sim_socket_')) and name.endswith('_visual')) or 'handle' in name:continue
        mid=model.geom_dataid[g]
        if mid<0:continue
        meshname=model.mesh(mid).name;path=mesh_files[meshname];asset=trimesh.load(path,force='mesh',process=False)
        if name.startswith('sim_module_'):body=mb
        else:body=sb
        original=asset.vertices@d.xmat[body].reshape(3,3).T+d.xpos[body]
        v=model.mesh_vert[model.mesh_vertadr[mid]:model.mesh_vertadr[mid]+model.mesh_vertnum[mid]]
        compiled=v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g]
        error=float(cKDTree(compiled).query(original)[0].max());mesh_errors[name]=error
    max_mesh=max(mesh_errors.values())
    if max_mesh>2e-6:raise ValueError('Rendered mesh differs from original object-frame vertices')
    module_audit=json.loads(geometry_report.read_text())
    if max(x['max_geometry_difference_m'] for x in module_audit)>1e-7:raise ValueError('Module template and rendered revision disagree')
    grasps=np.array([e['grasp_translation_mm']+e['grasp_rpy_deg'] for e in episodes]);q=np.array([r['left_arm_qpos'] for r in rows])
    report={'accepted_for_sim_supervision':True,'physical_pose_accuracy_validated':False,'records_sha256':sha(folder/'records.jsonl'),'frames_verified':len(rows),'episodes':len(episodes),
            'all_rgb_hashes_and_resolutions_verified':True,'split_by_complete_grasp_configuration':True,'identical_images_across_splits':False,
            'rigid_matrix_max_error':matrix_max,'independent_fk_samples':len(chosen),'independent_fk_max_matrix_difference':fk_max,
            'rendered_mesh_parts_checked':len(mesh_errors),'rendered_vs_authored_vertex_max_error_m':max_mesh,'module_r05_vs_rendered_r08_geometry_audit':str(geometry_report),
            'grasp_parameter_min':grasps.min(0).tolist(),'grasp_parameter_max':grasps.max(0).tolist(),'arm_joint_total_range_rad':np.ptp(q,axis=0).tolist(),
            'label_semantics':'Exact known scene transforms under kinematic rendering; no real-world calibration or physical grasp acceptance'}
    (folder/'label_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--geometry-audit',type=Path,required=True);a=p.parse_args();audit(a.data,a.geometry_audit)
