"""Immutable, metric, task-weighted surface point templates from existing meshes."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial import cKDTree

MODULE=Path('/data/omi_runtime/assets/optical_module_v4/r05')
SOCKET=Path('/data/omi_runtime/assets/sim_insertion/r06')
COUNTS=[512,2048,8192,16384]


def hash_file(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sources():
    manifest=json.loads((MODULE/'asset_manifest.json').read_text())
    module=[{'path':p['mesh'],'name':p['name'],'color':p['color'][:3]} for p in manifest['parts'] if 'Green pull' not in p['name'] and 'shadow block' not in p['name']]
    meta=json.loads((SOCKET/'asset_manifest.json').read_text());names={k[:14]:v['part'] for k,v in meta['mappings'].items() if k.startswith('sim_socket_')}
    xml=ET.parse(SOCKET/'scene.xml');colors={g.get('mesh'):list(map(float,g.get('rgba','0.65 0.65 0.65 1').split()))[:3] for g in xml.findall('.//geom')}
    socket=[{'path':str(p),'name':names.get(p.stem[:14],p.stem),'color':colors.get(p.stem,[.65]*3)} for p in sorted((SOCKET/'meshes').glob('sim_socket_*_visual.obj'))]
    return {'module':module,'socket':socket}


def mesh_arrays(parts):
    triangles=[];normals=[];ids=[];colors=[];areas=[];records=[]
    for i,part in enumerate(parts):
        mesh=trimesh.load(part['path'],force='mesh',process=False)
        good=np.isfinite(mesh.area_faces)&(mesh.area_faces>1e-16)
        triangles.append(mesh.triangles[good]);normals.append(mesh.face_normals[good]);areas.append(mesh.area_faces[good]);ids.append(np.full(good.sum(),i,np.int16));colors.append(np.tile(np.clip(part['color'],0,1),(good.sum(),1)))
        records.append({**part,'part_id':i,'sha256':hash_file(part['path']),'surface_area_m2':float(mesh.area_faces[good].sum()),'triangles':int(good.sum())})
    return {'triangles':np.concatenate(triangles),'normals':np.concatenate(normals),'areas':np.concatenate(areas),'part_id':np.concatenate(ids),'colors':np.concatenate(colors),'parts':records}


def region_pools(kind,mesh):
    c=mesh['triangles'].mean(1);all_faces=np.arange(len(c));part_names=[p['name'] for p in mesh['parts']]
    if kind=='module':
        pools=[all_faces,np.flatnonzero(c[:,1]<-.02),np.flatnonzero(c[:,1]>.014)]
        labels=['whole_surface','insertion_tip','rear_step_and_windows']
    else:
        mouth_ids=[i for i,n in enumerate(part_names) if any(s in n.lower() for s in ['cage','mouth','embossed','folded vertical'])]
        frame_ids=[i for i,n in enumerate(part_names) if any(s in n.lower() for s in ['housing printed','pcb upper'])]
        pools=[all_faces,np.flatnonzero(np.isin(mesh['part_id'],mouth_ids)&(c[:,1]>-.022)),np.flatnonzero(np.isin(mesh['part_id'],frame_ids))]
        labels=['whole_fixed_assembly_including_stand','mouth_and_channel','frame_and_pcb']
    if any(len(p)==0 for p in pools):raise ValueError('Empty task surface region')
    return pools,labels


def sample_faces(mesh,faces,rng):
    uv=rng.random((len(faces),2));uv[uv.sum(1)>1]=1-uv[uv.sum(1)>1]
    bary=np.c_[1-uv.sum(1),uv]
    points=np.einsum('ni,nij->nj',bary,mesh['triangles'][faces])
    return points,bary


def template(kind,mesh,count=16384,seed=20261122):
    rng=np.random.default_rng(seed);pools,labels=region_pools(kind,mesh)
    # Repeated interleaving gives every prefix the same 50/25/25 allocation.
    region=np.resize(np.array([0,1,0,2,0,1,0,2],np.uint8),count);face=np.zeros(count,np.int32)
    for k,pool in enumerate(pools):
        where=np.flatnonzero(region==k);prob=mesh['areas'][pool];prob=prob/prob.sum();face[where]=rng.choice(pool,len(where),p=prob)
    # Preserve small physical parts rather than letting the large stand consume
    # all global samples. Round-robin prefixes cover every component first.
    global_slots=np.flatnonzero(region==0)
    for j,slot in enumerate(global_slots[:4*len(mesh['parts'])]):
        pool=np.flatnonzero(mesh['part_id']==j%len(mesh['parts']));area=mesh['areas'][pool]
        face[slot]=rng.choice(pool,p=area/area.sum())
    points,bary=sample_faces(mesh,face,rng)
    return {'points_m':points.astype('float32'),'normals':mesh['normals'][face].astype('float32'),'rgb':np.rint(mesh['colors'][face]*255).astype('uint8'),
            'part_id':mesh['part_id'][face],'region_id':region,'point_id':np.arange(count,dtype=np.int32),'face_id':face,'barycentric':bary.astype('float32')},labels


def write_ply(path,arrays):
    points=arrays['points_m'];rgb=arrays['rgb']
    with Path(path).open('w') as f:
        f.write('ply\nformat ascii 1.0\ncomment units meters; sampled mesh prior, not sensor observations\nelement vertex '+str(len(points))+'\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
        for p,c in zip(points,rgb):f.write('%.8f %.8f %.8f %d %d %d\n'%(*p,*c))


def build(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    report={'schema':'omi-complete-surface-template-v1','units':'meters','seed':20261122,'sampling':'50% global surface (minimum component coverage, then area sampling) + 25% task region 1 + 25% task region 2; fixed nested point IDs',
            'recommended_counts':{'module':2048,'socket':8192},'models':{},'metric_accuracy_validated':False,'source_mesh_modified':False,
            'scope':{'module':'V4-r05 metal body and attached black plug, no green hanging accessory or hypothetical internal shadow block','socket':'all SIM-r06 fixed visual parts including lower stand; equivalent moving contact pads excluded'}}
    for kind,parts in sources().items():
        mesh=mesh_arrays(parts);master,labels=template(kind,mesh)
        rng=np.random.default_rng(9871);face=rng.choice(len(mesh['areas']),100000,p=mesh['areas']/mesh['areas'].sum());reference,_=sample_faces(mesh,face,rng)
        pools,_=region_pools(kind,mesh);task=rng.choice(pools[1],20000,p=mesh['areas'][pools[1]]/mesh['areas'][pools[1]].sum());task_ref,_=sample_faces(mesh,task,rng)
        model={'parts':mesh['parts'],'region_labels':labels,'surface_area_m2':float(mesh['areas'].sum()),'bounds_m':[mesh['triangles'].reshape(-1,3).min(0).tolist(),mesh['triangles'].reshape(-1,3).max(0).tolist()],'levels':[]}
        for n in COUNTS:
            arrays={k:v[:n] for k,v in master.items()};prefix=output/f'{kind}_{n}';np.savez_compressed(str(prefix)+'.npz',**arrays);write_ply(str(prefix)+'.ply',arrays)
            tree=cKDTree(arrays['points_m']);d=tree.query(reference)[0]*1000;task_d=tree.query(task_ref)[0]*1000
            reconstruction=np.einsum('ni,nij->nj',arrays['barycentric'],mesh['triangles'][arrays['face_id']])
            err=float(np.max(np.linalg.norm(reconstruction-arrays['points_m'],axis=1)))
            if err>1e-7:raise ValueError('Sample left source mesh triangle')
            model['levels'].append({'count':n,'npz':str(prefix)+'.npz','ply':str(prefix)+'.ply','npz_sha256':hash_file(str(prefix)+'.npz'),'xyz_float32_bytes':n*12,
              'surface_reference_nearest_sample_p50_mm':float(np.median(d)),'surface_reference_nearest_sample_p95_mm':float(np.quantile(d,.95)),
              'task_region_p95_mm':float(np.quantile(task_d,.95)),'part_count_represented':int(len(np.unique(arrays['part_id']))),'max_barycentric_reconstruction_error_m':err,
              'region_counts':np.bincount(arrays['region_id'],minlength=3).tolist()})
        report['models'][kind]=model
    (output/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);a=p.parse_args();r=build(a.output)
    print(json.dumps({k:v['levels'] for k,v in r['models'].items()},indent=2))
