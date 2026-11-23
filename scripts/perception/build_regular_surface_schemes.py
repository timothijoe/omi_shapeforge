"""Two surface representations with a shared planar lattice, no random points.

1. Complete ordinary surfaces on a coarse grid; task surfaces on a finer grid.
2. Task surfaces only, with strict geometry and component filters.
Coplanar triangles share grid axes/phase. No triangle-edge oversampling or caps.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from build_surface_representation import sources,mesh_arrays,write_ply
from build_interaction_surface import clipped_mesh

FOCUS_ROI={
    'module':np.array([[-.0091,-.0352,-.0042],[.0091,-.0266,.0042]]),
    'socket':np.array([[-.0125,-.010,-.006],[.0119,.004,.007]])
}


def plane_frame(normal):
    n=np.asarray(normal,float);sign=1 if n[np.argmax(abs(n))]>=0 else -1
    n=np.round(n*sign,6);n/=np.linalg.norm(n)
    axis=np.eye(3)[np.argmin(abs(n))];u=np.cross(n,axis);u/=np.linalg.norm(u);v=np.cross(n,u)
    return n,u,v,sign


def grid_in_triangle(tri,u,v,pitch):
    coords=np.c_[tri@u,tri@v];low=np.ceil(coords.min(0)/pitch-1e-8).astype(int);high=np.floor(coords.max(0)/pitch+1e-8).astype(int)
    if np.any(high<low):return np.empty((0,3)),np.empty((0,2),np.int32)
    ii,jj=np.meshgrid(np.arange(low[0],high[0]+1),np.arange(low[1],high[1]+1));ij=np.c_[ii.ravel(),jj.ravel()];xy=ij*pitch
    a,b,c=coords;ab=b-a;ac=c-a;det=ab[0]*ac[1]-ab[1]*ac[0]
    if abs(det)<1e-18:return np.empty((0,3)),np.empty((0,2),np.int32)
    q=xy-a;wb=(q[:,0]*ac[1]-q[:,1]*ac[0])/det;wc=(ab[0]*q[:,1]-ab[1]*q[:,0])/det
    weights=np.c_[1-wb-wc,wb,wc];ok=(weights>=-1e-8).all(1);weights=np.maximum(weights[ok],0);weights/=weights.sum(1,keepdims=True)
    return weights,ij[ok].astype(np.int32)


def planar_sample(mesh,triangles,barymaps,parents,pitch):
    if pitch<=0:raise ValueError('Grid pitch must be positive')
    original=mesh['triangles'];normals=np.cross(original[:,1]-original[:,0],original[:,2]-original[:,0]);length=np.linalg.norm(normals,axis=1)
    if np.any(length<=1e-18):raise ValueError('Degenerate source triangle')
    normals/=length[:,None]
    groups={};frames=[];points=[];bary=[];faces=[];plane_ids=[];grid_ids=[];regular=[]
    for triangle,barymap,parent in zip(triangles,barymaps,parents):
        n,u,v,sign=plane_frame(normals[parent]);key=(int(mesh['part_id'][parent]),*np.rint(n*1e6).astype(int),int(round(np.dot(n,triangle[0])/1e-7)),sign)
        if key not in groups:
            gid=len(frames);groups[key]={'id':gid,'count':0,'fallback':None,'area':0};frames.append((u,v))
        group=groups[key];area=np.linalg.norm(np.cross(triangle[1]-triangle[0],triangle[2]-triangle[0]))
        if area>group['area']:group.update(area=area,fallback=(triangle.mean(0),barymap.mean(0),parent))
        weights,ij=grid_in_triangle(triangle,u,v,pitch)
        if not len(weights):continue
        points.append(weights@triangle);bary.append(weights@barymap);faces.append(np.full(len(weights),parent,np.int32));plane_ids.append(np.full(len(weights),group['id'],np.int32));grid_ids.append(ij);regular.append(np.ones(len(weights),bool));group['count']+=len(weights)
    for g in groups.values():
        if g['count']==0:
            p,b,f=g['fallback'];points.append(p[None]);bary.append(b[None]);faces.append(np.array([f],np.int32));plane_ids.append(np.array([g['id']],np.int32));grid_ids.append(np.zeros((1,2),np.int32));regular.append(np.zeros(1,bool))
    if not points:raise ValueError('No surfaces to sample')
    points=np.concatenate(points);bary=np.concatenate(bary);faces=np.concatenate(faces);plane_ids=np.concatenate(plane_ids);grid_ids=np.concatenate(grid_ids);regular=np.concatenate(regular)
    _,keep=np.unique(np.c_[plane_ids,grid_ids,regular],axis=0,return_index=True);keep=np.sort(keep)
    points=points[keep];faces=faces[keep];bary=bary[keep];plane_ids=plane_ids[keep];grid_ids=grid_ids[keep];regular=regular[keep]
    output={'points_m':points.astype('float32'),'normals':normals[faces].astype('float32'),'rgb':np.rint(mesh['colors'][faces]*255).astype('uint8'),
            'part_id':mesh['part_id'][faces],'face_id':faces,'barycentric':bary.astype('float32'),'plane_id':plane_ids,'grid_ij':grid_ids,'on_regular_grid':regular}
    reconstructed=np.einsum('ni,nij->nj',output['barycentric'],mesh['triangles'][faces]);error=float(np.max(np.linalg.norm(reconstructed-output['points_m'],axis=1)))
    if error>1e-7:raise ValueError('Grid point left its original mesh surface')
    axes=np.array(frames);uv=np.stack([(points*axes[plane_ids,0]).sum(1),(points*axes[plane_ids,1]).sum(1)],axis=1)
    grid_error=float(np.max(abs(uv[regular]/pitch-grid_ids[regular]))) if regular.any() else 0
    if grid_error>1e-4:raise ValueError('Planar grid is not regular')
    return output,{'plane_count':len(groups),'regular_points':int(regular.sum()),'tiny_plane_fallback_points':int((~regular).sum()),
                   'max_original_triangle_error_m':error,'max_grid_index_error':grid_error,'pitch_mm':pitch*1000}


def focus_part_ids(kind,mesh):
    if kind=='module':return np.arange(len(mesh['parts']))
    phrases=['cage bottom','upper mouth','mouth floor rib','folded vertical','lower mouth rolled','housing printed frame','pressed side seam']
    return np.array([i for i,p in enumerate(mesh['parts']) if any(s in p['name'].lower() for s in phrases)])


def subset(arrays,mask):return {k:v[mask] for k,v in arrays.items()}


def build(output,ordinary_pitch=.0008,focus_pitch=.0002):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    manifest={'schema':'regular-planar-surface-schemes-v1','units':'meters','ordinary_pitch_mm':ordinary_pitch*1000,'focus_pitch_mm':focus_pitch*1000,
              'area_density_ratio':(ordinary_pitch/focus_pitch)**2,'models':{},'source_mesh_modified':False,'new_training_performed':False,
              'description':'Shared square grid per physical plane; sparse representative point only for sub-grid-size planes; no caps or triangulation-edge sprinkling'}
    for kind,parts in sources().items():
        mesh=mesh_arrays(parts);parents=np.arange(len(mesh['triangles']),dtype=np.int32);identity=np.repeat(np.eye(3)[None],len(parents),axis=0)
        ordinary,ordinary_audit=planar_sample(mesh,mesh['triangles'],identity,parents,ordinary_pitch)
        tri,bary,original=clipped_mesh(mesh,FOCUS_ROI[kind]);allowed=focus_part_ids(kind,mesh);take=np.isin(mesh['part_id'][original],allowed)
        focus,focus_audit=planar_sample(mesh,tri[take],bary[take],original[take],focus_pitch)
        # Replace the coarse task-region samples; don't stack duplicate grids.
        inside=((ordinary['points_m']>=FOCUS_ROI[kind][0]-1e-8)&(ordinary['points_m']<=FOCUS_ROI[kind][1]+1e-8)).all(1)&np.isin(ordinary['part_id'],allowed)
        ordinary=subset(ordinary,~inside)
        ordinary['representation_level']=np.zeros(len(ordinary['points_m']),np.uint8);focus['representation_level']=np.ones(len(focus['points_m']),np.uint8)
        for name,arr in [('ordinary',ordinary),('focus',focus)]:
            arr['point_id']=np.arange(len(arr['points_m']),dtype=np.int32);np.savez_compressed(output/f'{kind}_{name}.npz',**arr);write_ply(output/f'{kind}_{name}.ply',arr)
        if not (((focus['points_m']>=FOCUS_ROI[kind][0]-1e-7)&(focus['points_m']<=FOCUS_ROI[kind][1]+1e-7)).all() and np.isin(focus['part_id'],allowed).all()):raise ValueError('Focus-only scheme leaked outside selected components/ROI')
        manifest['models'][kind]={'parts':mesh['parts'],'focus_roi_m':FOCUS_ROI[kind].tolist(),'focus_part_names':[mesh['parts'][i]['name'] for i in allowed],
            'ordinary_points':len(ordinary['points_m']),'focus_points':len(focus['points_m']),'scheme1_total':len(ordinary['points_m'])+len(focus['points_m']),
            'scheme2_total':len(focus['points_m']),'ordinary_sampling_audit':ordinary_audit,'focus_sampling_audit':focus_audit,'focus_only_has_no_other_points':True}
        print(kind,json.dumps({k:v for k,v in manifest['models'][kind].items() if k not in ['parts','focus_part_names']},ensure_ascii=False),flush=True)
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--ordinary-mm',type=float,default=.8);p.add_argument('--focus-mm',type=float,default=.2);a=p.parse_args();build(a.output,a.ordinary_mm/1000,a.focus_mm/1000)
