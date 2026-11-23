"""Merge disjoint capture shards and verify physical-state labels and geometry."""
import argparse,json,shutil
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np,mujoco,trimesh
from PIL import Image
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from generate_sim_wrist_dataset import sha,read,transform,camera_transform
import sys
sys.path.insert(0,'/data/omi_runtime/assets/daimon/wrist_grasp_contact_r01/scripts')
from grasp_status import grasp_status


def merge(root):
    shards=sorted((root/'shards').glob('shard_*'));assert len(shards)==4
    for s in shards:
        if not (s/'complete.json').exists():raise ValueError('Incomplete shard '+str(s))
    out=root/'data';out.mkdir(exist_ok=False);(out/'episodes').mkdir();rows=[];episodes=[];attempts=[]
    for s in shards:
        for ep in sorted((s/'episodes').iterdir()):(out/'episodes'/ep.name).symlink_to(ep, target_is_directory=True)
        rows.extend(map(json.loads,(s/'records.jsonl').read_text().splitlines()));episodes.extend(read(s/'episodes.json'));attempts.extend(read(s/'attempts.json'))
    repair_paths=sorted(root.glob('repair_*/complete.json'))
    for done in repair_paths:
        repair=done.parent;replacement=read(repair/'episodes.json');ids={e['episode'] for e in replacement}
        if sha(repair/'scene.xml')!=sha(shards[0]/'scene.xml'):raise ValueError('Repair uses a different scene')
        rows=[r for r in rows if r['episode'] not in ids];episodes=[e for e in episodes if e['episode'] not in ids]
        for x in attempts:
            if x['episode'] in ids and x['accepted']:x.update(accepted=False,reason='post_capture_visible_penetration_audit',superseded_by=str(repair))
        for eid in ids:
            link=out/'episodes'/eid;link.unlink();link.symlink_to(repair/'episodes'/eid,target_is_directory=True)
        rows.extend(map(json.loads,(repair/'records.jsonl').read_text().splitlines()));episodes.extend(replacement);attempts.extend(read(repair/'attempts.json'))
    order={'train':0,'val':1,'test':2};rows.sort(key=lambda r:(order[r['split']],r['episode'],r['frame']));episodes.sort(key=lambda r:(order[r['split']],r['episode']))
    for i,r in enumerate(rows):r['id']=i
    for name,data in [('episodes.json',episodes),('attempts.json',attempts)]: (out/name).write_text(json.dumps(data,indent=2))
    (out/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    for name in ['scene.xml','calibration.json','dependencies.json']:
        if len({sha(s/name) for s in shards})!=1:raise ValueError('Shard '+name+' differs')
        shutil.copy2(shards[0]/name,out/name)
    cfg=read(shards[0]/'config.json');cfg.update(repair_paths=[str(p.parent) for p in repair_paths],shard_id=None,shard_paths=[str(s) for s in shards],derived_scene=str(out/'scene.xml'));(out/'config.json').write_text(json.dumps(cfg,indent=2))
    final={'frames':len(rows),'clips':len(episodes),'split_frames':{s:sum(r['split']==s for r in rows) for s in order},'split_clips':{s:sum(r['split']==s for r in episodes) for s in order},'attempts':len(attempts),'rejected':sum(not r['accepted'] for r in attempts),'all_accepted_episodes_pass_contact_gate':True,'source_assets_unchanged':True,'insertion_validated':False}
    (out/'complete.json').write_text(json.dumps(final,indent=2));return out


def audit(folder):
    rows=list(map(json.loads,(folder/'records.jsonl').read_text().splitlines()));eps=read(folder/'episodes.json');complete=read(folder/'complete.json');cfg=read(folder/'config.json');cal=read(folder/'calibration.json')
    assert len(rows)==complete['frames'] and len(eps)==complete['clips'];assert sha(folder/'scene.xml')==cfg['derived_scene_sha256']
    for path,h in read(folder/'dependencies.json').items():
        if sha(path)!=h:raise ValueError('Changed dependency '+path)
    m=mujoco.MjModel.from_xml_path(str(folder/'scene.xml'));d=mujoco.MjData(m);m.opt.gravity[:]=[0,0,-9.81];cam=m.camera('wrist_rgb').id;mb=m.body('sim_module').id;sb=m.body('sim_socket').id;tb=m.body('audit_tool').id
    if m.opt.disableflags&int(mujoco.mjtDisableBit.mjDSBL_CONTACT):raise ValueError('Contact disabled')
    if m.jnt_type[m.joint('module_free').id]!=mujoco.mjtJoint.mjJNT_FREE:raise ValueError('Module not free')
    if any(m.eq_type[i]==mujoco.mjtEq.mjEQ_WELD and mb in [m.eq_obj1id[i],m.eq_obj2id[i]] for i in range(m.neq)):raise ValueError('Module welded')
    images={};seeds={};byep={e['episode']:e for e in eps};states=None;eid=None;maxerr=0.;minforce=float('inf');maxslip=0.;maxrot=0.;maxpen=0.;contact_samples=0;replayed_min_force=float('inf')
    for e in eps:
        key=tuple(e['initial_offset_tool_mm']+e['initial_rpy_tool_deg'])
        if key in seeds and seeds[key]!=e['split']:raise ValueError('Initial grasp leakage')
        seeds[key]=e['split']
        if max(e['qpos_range_rad'])<.001:raise ValueError('No arm motion')
        if not e['contact_validation']['accepted']:raise ValueError('Rejected episode leaked')
    for row in rows:
        ep=byep[row['episode']]
        if ep['split']!=row['split']:raise ValueError('Split mismatch')
        h=sha(folder/row['image'])
        if h!=row['image_sha256'] or (h in images and images[h]!=row['split']):raise ValueError('Bad image hash or split leakage')
        images[h]=row['split']
        with Image.open(folder/row['image']) as image:assert image.size==(cal['image_width'],cal['image_height'])
        if row['episode']!=eid:
            eid=row['episode'];states=np.load(folder/'episodes'/eid/'states.npz');trace=states['contact_trace'];contact_samples+=len(trace)
            minforce=min(minforce,float(trace[:,1:3].min()));maxslip=max(maxslip,float(trace[:,3].max()));maxrot=max(maxrot,float(trace[:,4].max()));maxpen=max(maxpen,float(trace[:,5].max()))
            if np.any(trace[:,1:3]<.1) or np.any(trace[:,3]>.1) or np.any(trace[:,4]>.5) or np.any(trace[:,5]>.05):raise ValueError('Contact trace fails gate')
        f=row['frame'];d.qpos[:]=states['qpos'][f];d.qvel[:]=states['qvel'][f];d.mocap_pos[:]=states['mocap_pos'][f];d.mocap_quat[:]=states['mocap_quat'][f];d.ctrl[:]=states['ctrl'][f];mujoco.mj_forward(m,d)
        replay=grasp_status(m,d)
        if not replay['held']:raise ValueError('Replayed state is not in bilateral contact')
        replayed_min_force=min(replayed_min_force,min(replay['pad_normal_force_n'].values()))
        Twc=camera_transform(d,cam)
        for name,b in [('module',mb),('socket',sb)]:
            expected=np.linalg.inv(Twc)@transform(d,b);actual=np.array(row['T_camera_from_'+name]);maxerr=max(maxerr,float(abs(expected-actual).max()))
            if not np.isfinite(actual).all() or actual[2,3]<=0:raise ValueError('Invalid pose')
        v=row.get('visible_surface_gate')
        if v and (not v['accepted'] or v['nonpad_intersections'] or any(p['distance_mm']<-.05 or p['distance_mm']>.02 for p in v['pads'].values())):raise ValueError('Visible surface check failed')
        if not row['contact']['held']:raise ValueError('Frame not held')
    if maxerr>1e-9:raise ValueError('State label mismatch')
    # Authored coordinate frames survive MuJoCo mesh centering/rotation.
    xml=ET.parse(folder/'scene.xml').getroot();files={e.get('name'):e.get('file') for e in xml.findall('asset/mesh')};errors={};actual_parts={}
    for g in range(m.ngeom):
        b=m.geom_bodyid[g]
        if b not in [mb,sb] or m.geom_group[g]>=3 or m.geom_type[g]!=mujoco.mjtGeom.mjGEOM_MESH:continue
        mid=m.geom_dataid[g];src=trimesh.load(files[m.mesh(mid).name],force='mesh',process=False);orig=src.vertices@d.xmat[b].reshape(3,3).T+d.xpos[b];v=m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid]+m.mesh_vertnum[mid]];compiled=v@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g];err=float(cKDTree(compiled).query(orig)[0].max());errors[m.geom(g).name]=err
        actual_parts[sha(files[m.mesh(mid).name])]=src.vertices
    if max(errors.values())>2e-6:raise ValueError('Compiled visual mesh mismatch')
    # Validate regular template point barycentrics against source triangles.
    templates=Path('/data/omi_runtime/runs/regular_surface_schemes_20261122/templates_v2');tm=read(templates/'manifest.json');template_max=0.
    for name in ['module','socket']:
        parts=tm['models'][name]['parts'];meshes=[]
        for part in parts:
            if sha(part['path'])!=part['sha256']:raise ValueError('Template source changed')
            meshes.append(trimesh.load(part['path'],force='mesh',process=False))
        triangles=np.concatenate([x.triangles[np.isfinite(x.area_faces)&(x.area_faces>1e-16)] for x in meshes])
        for category in ['ordinary','focus']:
            a=np.load(templates/f'{name}_{category}.npz');err=float(np.linalg.norm(np.einsum('ni,nij->nj',a['barycentric'],triangles[a['face_id']])-a['points_m'],axis=1).max());template_max=max(template_max,err)
        # All template part geometry must occur in the rendered rigid body.
        rendered=[v for h,v in actual_parts.items()]
        for mesh in meshes:
            if not any(np.max(cKDTree(v).query(mesh.vertices)[0])<1e-7 and np.max(cKDTree(mesh.vertices).query(v)[0])<1e-7 for v in rendered):raise ValueError('Template part not rendered: '+parts[meshes.index(mesh)]['path'])
    if template_max>1e-7:raise ValueError('Template points leave source surface')
    report={'accepted_for_sim_supervision':True,'frames_verified':len(rows),'episodes':len(eps),'records_sha256':sha(folder/'records.jsonl'),'all_images_hash_and_resolution_verified':True,'grouped_splits_no_duplicate_images_or_initial_grasps':True,'state_replay_labels_checked':len(rows),'max_label_matrix_error':maxerr,'rendered_visual_parts_checked':len(errors),'compiled_mesh_max_error_m':max(errors.values()),'template_original_surface_max_error_m':template_max,'module_free_no_weld':True,'contact_enabled':True,'contact_samples_verified':contact_samples,'all_saved_frame_contacts_independently_recomputed':True,'replayed_minimum_each_pad_force_n':replayed_min_force,'minimum_each_pad_force_n':minforce,'max_slip_mm':maxslip,'max_rotation_drift_deg':maxrot,'max_collision_penetration_mm':maxpen,'all_frames_visible_surface_gate_present':all('visible_surface_gate' in r for r in rows),'robot_control':'kinematic FK visual context, dynamic tool servo','socket_contacts_enabled':False,'real_world_accuracy_validated':False}
    (folder/'label_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path);p.add_argument('--data',type=Path);a=p.parse_args();audit(merge(a.run) if a.run else a.data)
