"""Dense interaction surfaces plus genuine crease/boundary samples.

Clip original triangle surfaces to explicit metric ROIs without capping cuts.
Keep real mesh edges separate from artificial ROI boundaries. Original meshes
and previous coarse representations remain immutable.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from build_surface_representation import sources,mesh_arrays,write_ply,hash_file

ROIS={
    'module':np.array([[-.012,-.0352,-.006],[.012,-.023,.008]]),
    'socket':np.array([[-.018,-.022,-.008],[.018,.007,.014]])
}


def clip_triangle(triangle,bounds):
    """Return triangle fragments and their barycentrics in the original face."""
    polygon=[(triangle[i],np.eye(3)[i]) for i in range(3)]
    for axis in range(3):
        for limit,sign in [(bounds[0,axis],1),(bounds[1,axis],-1)]:
            new=[]
            for i,(a,ba) in enumerate(polygon):
                b,bb=polygon[(i+1)%len(polygon)];da=sign*(a[axis]-limit);db=sign*(b[axis]-limit)
                inside_a=da>=-1e-12;inside_b=db>=-1e-12
                if inside_a:new.append((a,ba))
                if inside_a!=inside_b:
                    u=da/(da-db);new.append((a+u*(b-a),ba+u*(bb-ba)))
            polygon=new
            if len(polygon)<3:return []
    fragments=[]
    for i in range(1,len(polygon)-1):
        p=np.array([polygon[0][0],polygon[i][0],polygon[i+1][0]])
        if np.linalg.norm(np.cross(p[1]-p[0],p[2]-p[0]))>1e-16:
            fragments.append((p,np.array([polygon[0][1],polygon[i][1],polygon[i+1][1]])))
    return fragments


def clipped_mesh(mesh,bounds):
    triangles=mesh['triangles'];possible=((triangles.max(1)>=bounds[0]-1e-12)&(triangles.min(1)<=bounds[1]+1e-12)).all(1)
    t=[];b=[];ids=[]
    for face in np.flatnonzero(possible):
        for tri,bary in clip_triangle(triangles[face],bounds):t.append(tri);b.append(bary);ids.append(face)
    if not t:raise ValueError('ROI has no source surface')
    return np.array(t),np.array(b),np.array(ids,np.int32)


def lattice(triangle,pitch):
    """Approximately isotropic planar grid plus triangle-border coverage."""
    lengths=[np.linalg.norm(triangle[(i+1)%3]-triangle[i]) for i in range(3)]
    i=int(np.argmax(lengths));order=[i,(i+1)%3,(i+2)%3];a,b,c=triangle[order]
    length=lengths[i];u=(b-a)/length;cx=np.dot(c-a,u);v=c-a-cx*u;height=np.linalg.norm(v)
    if height<1e-12:return np.eye(3)
    v/=height;ys=np.arange(0,height+pitch*.01,pitch*np.sqrt(3)/2)
    bary=[]
    for row,y in enumerate(ys):
        xs=np.arange(min(0,cx),max(length,cx)+pitch*.01,pitch)+(row%2)*pitch/2
        w2=np.full(len(xs),y/height);w1=(xs-cx*w2)/length;w0=1-w1-w2
        weights=np.c_[w0,w1,w2];weights=weights[(weights>=-1e-10).all(1)]
        if len(weights):bary.append(weights)
    for j in range(3):
        n=max(1,int(np.ceil(lengths[j]/pitch)));t=np.linspace(0,1,n+1);weights=np.zeros((len(t),3));weights[:,j]=1-t;weights[:,(j+1)%3]=t
        # Borders are generated in original triangle vertex order.
        bary.append(weights[:,order])
    weights=np.concatenate(bary);original=np.zeros_like(weights);original[:,order]=weights
    return original


def clip_segment(a,b,bounds):
    lo,hi=0.,1.;d=b-a
    for axis in range(3):
        if abs(d[axis])<1e-15:
            if a[axis]<bounds[0,axis]-1e-12 or a[axis]>bounds[1,axis]+1e-12:return None
        else:
            x,y=sorted([(bounds[0,axis]-a[axis])/d[axis],(bounds[1,axis]-a[axis])/d[axis]]);lo=max(lo,x);hi=min(hi,y)
            if hi-lo<1e-12:return None
    return a+lo*d,a+hi*d


def real_edges(mesh,bounds,angle_deg=25):
    segments=[];face_ids=[]
    for part in range(len(mesh['parts'])):
        faces=np.flatnonzero(mesh['part_id']==part);raw=mesh['triangles'][faces].reshape(-1,3)
        _,first,inverse=np.unique(np.round(raw/1e-8).astype(np.int64),axis=0,return_index=True,return_inverse=True)
        welded=trimesh.Trimesh(vertices=raw[first],faces=inverse.reshape(-1,3),process=False)
        adjacent=welded.face_adjacency_angles>np.deg2rad(angle_deg)
        edges=list(welded.face_adjacency_edges[adjacent]);parents=list(welded.face_adjacency[adjacent,0])
        unique,index,counts=np.unique(np.sort(welded.edges,axis=1),axis=0,return_index=True,return_counts=True)
        edges.extend(unique[counts==1]);parents.extend((index[counts==1]//3).tolist())
        for edge,parent in zip(edges,parents):
            clipped=clip_segment(*welded.vertices[edge],bounds)
            if clipped is not None:segments.append(clipped);face_ids.append(faces[parent])
    return np.array(segments),np.array(face_ids,np.int32)


def arrays(mesh,points,face_ids,bary,level):
    return {'points_m':np.asarray(points,np.float32),'normals':mesh['normals'][face_ids].astype(np.float32),
            'rgb':np.rint(mesh['colors'][face_ids]*255).astype(np.uint8),'part_id':mesh['part_id'][face_ids],
            'face_id':np.asarray(face_ids,np.int32),'barycentric':np.asarray(bary,np.float32),
            'point_id':np.arange(len(points),dtype=np.int32),'representation_level':np.full(len(points),level,np.uint8)}


def build_detail(kind,mesh,surface_pitch=.0002,edge_pitch=.00005):
    bounds=ROIS[kind];triangles,barymaps,original=clipped_mesh(mesh,bounds)
    points=[];barys=[];faces=[]
    for tri,barymap,parent in zip(triangles,barymaps,original):
        weights=lattice(tri,surface_pitch);points.append(weights@tri);barys.append(weights@barymap);faces.append(np.full(len(weights),parent,np.int32))
    points=np.concatenate(points);barys=np.concatenate(barys);faces=np.concatenate(faces)
    # Duplicate shared vertices can be merged, but never merge nearby opposite
    # sides of a thin sheet. A 0.0001 mm tolerance is far below sheet thickness.
    key=np.c_[np.round(points/1e-7).astype(np.int64),mesh['part_id'][faces]]
    _,keep=np.unique(key,axis=0,return_index=True);keep=np.sort(keep)
    surface=arrays(mesh,points[keep],faces[keep],barys[keep],1)
    segments,parents=real_edges(mesh,bounds);ep=[];ef=[];eb=[];edge_ids=[]
    for i,((a,b),face) in enumerate(zip(segments,parents)):
        n=max(1,int(np.ceil(np.linalg.norm(b-a)/edge_pitch)));p=np.linspace(a,b,n+1)
        bary=trimesh.triangles.points_to_barycentric(np.repeat(mesh['triangles'][face][None],len(p),axis=0),p)
        ep.append(p);ef.append(np.full(len(p),face,np.int32));eb.append(bary);edge_ids.append(np.full(len(p),i,np.int32))
    edges=arrays(mesh,np.concatenate(ep),np.concatenate(ef),np.concatenate(eb),2);edges['edge_id']=np.concatenate(edge_ids)
    errors=[]
    for a in [surface,edges]:
        reconstruction=np.einsum('ni,nij->nj',a['barycentric'],mesh['triangles'][a['face_id']]);err=np.linalg.norm(reconstruction-a['points_m'],axis=1);errors.append(float(err.max()))
        if err.max()>1e-7 or np.any(a['points_m']<bounds[0]-1e-7) or np.any(a['points_m']>bounds[1]+1e-7):raise ValueError('A dense point left its original surface or ROI')
    rng=np.random.default_rng(481);areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1)/2
    ix=rng.choice(len(triangles),100000,p=areas/areas.sum());uv=rng.random((len(ix),2));uv[uv.sum(1)>1]=1-uv[uv.sum(1)>1];weights=np.c_[1-uv.sum(1),uv];reference=np.einsum('ni,nij->nj',weights,triangles[ix])
    lengths=np.linalg.norm(segments[:,1]-segments[:,0],axis=1);ei=rng.choice(len(segments),20000,p=lengths/lengths.sum());t=rng.random((len(ei),1));edge_reference=segments[ei,0]*(1-t)+segments[ei,1]*t
    distance=cKDTree(surface['points_m']).query(reference)[0]*1000;edge_distance=cKDTree(edges['points_m']).query(edge_reference)[0]*1000
    by_part={}
    for part in np.unique(mesh['part_id'][original]):
        mask=mesh['part_id'][original[ix]]==part;subset=surface['points_m'][surface['part_id']==part]
        if mask.sum() and len(subset):by_part[mesh['parts'][part]['name']]={'sample_count':len(subset),'reference_count':int(mask.sum()),'p95_mm':float(np.quantile(cKDTree(subset).query(reference[mask])[0]*1000,.95))}
    report={'roi_m':bounds.tolist(),'surface_grid_pitch_mm':surface_pitch*1000,'real_edge_step_mm':edge_pitch*1000,'crease_angle_deg':25,
            'surface_points':len(surface['points_m']),'edge_points':len(edges['points_m']),'source_surface_area_mm2':float(areas.sum()*1e6),
            'real_edge_length_mm':float(lengths.sum()*1000),'real_edge_segments':len(segments),
            'source_surface_coverage_p95_mm':float(np.quantile(distance,.95)),'source_surface_coverage_max_mm':float(distance.max()),
            'source_edge_coverage_p95_mm':float(np.quantile(edge_distance,.95)),'source_edge_coverage_max_mm':float(edge_distance.max()),
            'max_original_face_reconstruction_error_m':max(errors),'per_part':by_part,'cut_caps_added':False,'physical_accuracy_validated':False}
    return surface,edges,report,reference,edge_reference


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--coarse',type=Path,default=Path('/data/omi_runtime/runs/image_to_complete_surface_20261122/templates_v2'));p.add_argument('--compact-from',type=Path);a=p.parse_args()
    if a.compact_from:
        build_compact(a.compact_from,a.coarse,a.output);return
    a.output.mkdir(parents=True,exist_ok=False)
    manifest={'schema':'omi-interaction-surface-v1','units':'meters','models':{},'recommended_counts':{},'source_mesh_modified':False,
              'representation':'coarse complete surface + dense local surface + real crease/boundary points','network_weights_status':'untrained','sampling_accuracy_is_not_physical_accuracy':True}
    for kind,parts in sources().items():
        mesh=mesh_arrays(parts);surface,edge,report,reference,edge_ref=build_detail(kind,mesh)
        old_n=2048 if kind=='module' else 8192;old=np.load(a.coarse/f'{kind}_{old_n}.npz')
        inside=((old['points_m']>=ROIS[kind][0])&(old['points_m']<=ROIS[kind][1])).all(1);old_local=old['points_m'][inside]
        old_d=cKDTree(old_local).query(reference)[0]*1000 if len(old_local) else np.full(len(reference),np.inf)
        old_e=cKDTree(old_local).query(edge_ref)[0]*1000 if len(old_local) else np.full(len(edge_ref),np.inf)
        report.update(old_whole_points=old_n,old_roi_points=int(inside.sum()),old_roi_surface_p95_mm=float(np.quantile(old_d,.95)),old_roi_edge_p95_mm=float(np.quantile(old_e,.95)),parts=mesh['parts'])
        for name,arr in [('surface',surface),('edges',edge)]:
            np.savez_compressed(a.output/f'{kind}_{name}.npz',**arr);write_ply(a.output/f'{kind}_{name}.ply',arr)
        np.savez_compressed(a.output/f'{kind}_old_local.npz',**{k:old[k][inside] for k in old.files})
        coarse_n=2048 if kind=='module' else 2048
        packed={}
        for key in ['points_m','normals','rgb','part_id']:
            packed[key]=np.concatenate([old[key][:coarse_n],surface[key],edge[key]])
        n=len(packed['points_m']);packed['point_id']=np.arange(n,dtype=np.int32);packed['representation_level']=np.r_[np.zeros(coarse_n,np.uint8),surface['representation_level'],edge['representation_level']]
        packed['region_id']=packed['representation_level'].copy()
        np.savez_compressed(a.output/f'{kind}_{n}.npz',**packed)
        report['network_pack']={'global_count':coarse_n,'detail_surface_count':len(surface['points_m']),'detail_edge_count':len(edge['points_m']),'total_count':n,'npz':str(a.output/f'{kind}_{n}.npz'),'sha256':hash_file(a.output/f'{kind}_{n}.npz')}
        manifest['models'][kind]=report;manifest['recommended_counts'][kind]=n
        print(kind,json.dumps({k:v for k,v in report.items() if k not in ['parts','per_part']},ensure_ascii=False),flush=True)
    (a.output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


def balanced_subset(arrays,count,seed):
    rng=np.random.default_rng(seed);parts,n=np.unique(arrays['part_id'],return_counts=True)
    minimum=np.minimum(n,8);left=count-int(minimum.sum());raw=left*(n-minimum)/max(1,(n-minimum).sum());quotas=minimum+np.floor(raw).astype(int)
    for i in np.argsort(-(raw-np.floor(raw)))[:count-int(quotas.sum())]:quotas[i]+=1
    chosen=[]
    for part,quota in zip(parts,quotas):chosen.extend(rng.choice(np.flatnonzero(arrays['part_id']==part),int(quota),replace=False))
    chosen=np.sort(chosen)
    if len(chosen)!=count:raise ValueError('Invalid compact quota')
    return {k:arrays[k][chosen] for k in arrays.files},chosen


def build_compact(dense,coarse,output):
    """A bounded training budget; retain dense reference for geometry review."""
    output.mkdir(parents=True,exist_ok=False);manifest={'schema':'omi-interaction-surface-compact-v1','units':'meters',
        'source_dense_manifest':str(dense/'manifest.json'),'source_dense_manifest_sha256':hash_file(dense/'manifest.json'),
        'recommended_counts':{},'models':{},'loss_level_weights':[.2,.5,.3],'source_mesh_modified':False,'physical_accuracy_validated':False}
    for kind,ns,ne in [('module',16384,4096),('socket',32768,8192)]:
        source_s=np.load(dense/f'{kind}_surface.npz');source_e=np.load(dense/f'{kind}_edges.npz');s,si=balanced_subset(source_s,ns,17);e,ei=balanced_subset(source_e,ne,29)
        original=np.load(coarse/f'{kind}_2048.npz');pack={k:np.concatenate([original[k],s[k],e[k]]) for k in ['points_m','normals','rgb','part_id']}
        n=len(pack['points_m']);pack['point_id']=np.arange(n,dtype=np.int32);pack['representation_level']=np.r_[np.zeros(2048,np.uint8),np.ones(ns,np.uint8),np.full(ne,2,np.uint8)]
        pack['region_id']=pack['representation_level'].copy();pack['source_level_point_id']=np.r_[np.arange(2048),si,ei].astype(np.int32)
        np.savez_compressed(output/f'{kind}_{n}.npz',**pack)
        ds=cKDTree(s['points_m']).query(source_s['points_m'])[0]*1000;de=cKDTree(e['points_m']).query(source_e['points_m'])[0]*1000
        manifest['recommended_counts'][kind]=n;manifest['models'][kind]={'global_points':2048,'local_surface_points':ns,'real_edge_points':ne,'total_points':n,
            'dense_surface_to_compact_p95_mm':float(np.quantile(ds,.95)),'dense_edge_to_compact_p95_mm':float(np.quantile(de,.95)),
            'npz':str(output/f'{kind}_{n}.npz'),'sha256':hash_file(output/f'{kind}_{n}.npz')}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
