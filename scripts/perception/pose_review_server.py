"""Local-only per-sample point-cloud / fisheye mesh pose review application.

Run with the foundation_stereo environment. Original captures are read-only;
annotations, derived clouds and append-only save history live in --output.
"""
import argparse
import copy
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from functools import lru_cache
import numpy as np
import cv2
import trimesh
from pose_review_geometry import matrix, pose, validate_matrix, optical_extrinsic, roi_cloud, coarse_candidates, refine_pixels, project, guided_initialize, fit_metrics

DEFAULT_BACKUP='/data/zt-think-d1-data/nov_22/session_backup_20261121_20261122_20261122_014108'
MODULE='/data/omi_runtime/assets/optical_module_v4/r05'
SOCKET='/data/omi_runtime/assets/sim_insertion/r06'
GUIDES={
    'module':{'name':'金属模块顶面四角（需全部可见）',
              'labels':['插入端左角','插入端右角','尾部金属盖右角','尾部金属盖左角'],
              'points':[[.00873138,-.03507784,.00406798],[-.00873138,-.03507784,.00406798],[-.00881815,.03491006,.00652814],[.00881815,.03491006,.00652814]],
              'diagram':[[.28,.18],[.72,.18],[.8,.82],[.2,.82]],'top_label':'插入端','bottom_label':'尾部金属盖'},
    'socket':{'name':'白色框架顶面外侧四角（不是底边）',
              'labels':['白框左后上角','白框右后上角','白框右前上角','白框左前上角'],
              'points':[[.01571302,-.06371302,.01235515],[-.04571302,-.06385514,.01221302],[-.04545,.001,.01195],[.01545,.001,.01195]],
              'diagram':[[.18,.18],[.82,.18],[.82,.82],[.18,.82]],'top_label':'后端','bottom_label':'插口前端'}
}


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_json(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    temp=p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
    with temp.open('w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(temp,p)


def load_models():
    result={}
    manifest=read(Path(MODULE)/'asset_manifest.json')
    # Exclude detachable accessory and unobserved internal shadow block.
    files={'module':[Path(p['mesh']) for p in manifest['parts'] if 'Green pull' not in p['name'] and 'shadow block' not in p['name']],
           'socket':sorted((Path(SOCKET)/'meshes').glob('sim_socket_*_visual.obj'),key=lambda p:(p.name=='sim_socket_039_visual.obj',p.name))}
    for kind,paths in files.items():
        chunks=[];lines=[];stand_lines=[]
        for p in paths:
            mesh=trimesh.load(p,force='mesh',process=True)
            is_stand=kind=='socket' and p.name=='sim_socket_039_visual.obj'
            if not is_stand:chunks.append(mesh)
            adj=mesh.face_adjacency_edges[mesh.face_adjacency_angles>np.deg2rad(27)]
            unique,counts=np.unique(np.sort(mesh.edges,axis=1),axis=0,return_counts=True)
            edges=np.concatenate([adj,unique[counts==1]],axis=0)
            if len(edges):(stand_lines if is_stand else lines).append(mesh.vertices[edges])
        mesh=trimesh.util.concatenate(chunks)
        rng=np.random.default_rng(41)
        ix=rng.choice(len(mesh.faces),size=16000,p=mesh.area_faces/mesh.area)
        uv=rng.random((len(ix),2)); uv[uv.sum(1)>1]=1-uv[uv.sum(1)>1]
        tri=mesh.triangles[ix];samples=tri[:,0]+uv[:,:1]*(tri[:,1]-tri[:,0])+uv[:,1:]*(tri[:,2]-tri[:,0])
        edges=np.concatenate(lines)
        if len(edges)>6500:edges=edges[np.linspace(0,len(edges)-1,6500).astype(int)]
        # Subdivide long lines so fisheye projection curves, rather than connects
        # distorted endpoints with a straight line across the raw image.
        pieces=[]
        for a,b in edges:
            n=max(1,int(np.ceil(np.linalg.norm(a-b)/.003)))
            q=np.linspace(a,b,n+1);pieces.extend(zip(q[:-1],q[1:]))
        main_line_count=len(pieces)*2
        for a,b in np.concatenate(stand_lines) if stand_lines else []:
            n=max(1,int(np.ceil(np.linalg.norm(a-b)/.003)));q=np.linspace(a,b,n+1);pieces.extend(zip(q[:-1],q[1:]))
        landmarks=np.unique(np.round(edges.reshape(-1,3),8),axis=0)
        if len(landmarks)>2500:landmarks=landmarks[np.linspace(0,len(landmarks)-1,2500).astype(int)]
        result[kind]={'samples':samples,'lines':np.array(pieces).reshape(-1,3),'main_line_count':main_line_count,'vertices':landmarks,
                      'bounds':mesh.bounds,'source_files':{str(p):sha(p) for p in paths},
                      'version':'OM-001/V4-r05 (no green accessory)' if kind=='module' else 'SIM-r06 fixed socket visual parts (no equivalent moving pads)'}
    return result


class Review:
    def __init__(self,backup,output,calibration):
        self.backup=Path(backup).resolve();self.output=Path(output).resolve();self.output.mkdir(parents=True,exist_ok=True)
        if self.output.is_relative_to(self.backup):raise ValueError('Output must be outside immutable backup')
        self.cal_path=Path(calibration);self.cal=read(calibration)
        self.samples={}
        for f in sorted((self.backup/'captures/BundleSDF_trial/datasets/units').glob('*/samples/*/sample.json')):
            d=read(f);sid=d['sample_id']
            if sid in self.samples:raise ValueError('Duplicate sample ID')
            self.samples[sid]={'id':sid,'unit':f.parents[2].name,'path':f.parent,'meta':d,'metadata_sha256':sha(f),'legacy':None}
        for d in sorted((self.backup/'session_results/BundleSDF_trial/results').glob('button_sample*')):
            if (d/'source_sample.json').exists():
                source=read(d/'source_sample.json');sid=source['sample_id']
                if sid in self.samples and (d/'stereo/points.npz').exists():
                    if all(source['images'][k]['sha256']==self.samples[sid]['meta']['images'][k]['sha256'] for k in ['left','right','color']):self.samples[sid]['legacy']=d
        self.models=load_models();self.lock=threading.RLock();self.jobs={};self.gpu_lock=threading.Lock()
        self.binding={'path':str(self.cal_path),'sha256':sha(self.cal_path),'new_capture_identity_verified':False,'note':'User-provided prior calibration; identity/exposure sync/extrinsics not certified'}
        atomic_json(self.output/'session.json',{'backup':str(self.backup),'sample_count':len(self.samples),'wrist_calibration':self.binding,'models':{k:{'version':v['version'],'source_files':v['source_files']} for k,v in self.models.items()},'coordinate_convention':'T_destination_from_source; meters; optical x right y down z forward; UI mm/degrees, Rz(yaw)Ry(pitch)Rx(roll)','source_data_modified':False})

    def cloud_path(self,sid):
        s=self.samples[sid];new=self.output/'clouds'/sid/'points.npz'
        if new.exists():return new
        return s['legacy']/'stereo/points.npz' if s['legacy'] else None

    @lru_cache(maxsize=3)
    def cloud(self,sid):
        p=self.cloud_path(sid)
        if p is None:raise ValueError('This sample has no cloud yet. Generate stereo cloud first.')
        with np.load(p) as d:
            xyz=d['xyz'].astype(float);rgb=d['rgb'].astype(float)
        good=np.isfinite(xyz).all(1)&(xyz[:,2]>.1)&(xyz[:,2]<2)
        if rgb.max()>1:rgb/=255
        return xyz[good],rgb[good]

    @lru_cache(maxsize=3)
    def colored_cloud(self,sid):
        xyz,_=self.cloud(sid);s=self.samples[sid]
        uv,valid=project(xyz,optical_extrinsic(s['meta']),s['meta']['calibration']['color'])
        image=cv2.imread(str(s['path']/s['meta']['images']['color']['file']))
        if image is None:raise ValueError('Head RGB image cannot be read')
        u,v=np.rint(uv).astype(int).T;h,w=image.shape[:2]
        valid&=(u>=0)&(u<w)&(v>=0)&(v<h)
        rgb=np.full((len(xyz),3),.25)
        rgb[valid]=image[v[valid],u[valid],::-1]/255.
        uv[~valid]=-10000
        return xyz,rgb,uv

    def display_cloud(self,sid):
        xyz,rgb,uv=self.colored_cloud(sid);d=self.state(sid)
        dense=np.zeros(len(xyz),bool);rects=[o.get('roi') for o in d['objects'].values() if o.get('roi')]
        if not rects:rects=[[650,200,1250,800]]
        for x0,y0,x1,y1 in rects:
            dense|=(uv[:,0]>x0-35)&(uv[:,0]<x1+35)&(uv[:,1]>y0-35)&(uv[:,1]<y1+35)
        ids=np.union1d(np.linspace(0,len(xyz)-1,min(100000,len(xyz))).astype(int),np.flatnonzero(dense))
        return np.c_[xyz[ids],rgb[ids],uv[ids]].astype('<f4')

    def blank(self,sid):
        s=self.samples[sid]
        objects={k:{'head':None,'wrist':None,'roi':None,'pairs':[],'status':'uninitialized','head_candidates':[]} for k in self.models}
        if s['legacy'] and (s['legacy']/'target_selection.json').exists():
            d=read(s['legacy']/'target_selection.json')
            if 'polygon_rgb' in d:
                poly=np.array(d['polygon_rgb']);objects['module']['roi']=np.r_[poly.min(0),poly.max(0)].tolist()
        return {'schema':'omi-head-wrist-pose-review-v1','sample_id':sid,'revision':0,'objects':objects,'T_wrist_from_head':None,'extrinsic_status':'unknown','notes':'','reviewed':False,'training_label_valid':False}

    def state(self,sid):
        p=self.output/'annotations'/f'{sid}.json'
        return read(p) if p.exists() else self.blank(sid)

    def save(self,sid,state):
        if state.get('sample_id')!=sid:raise ValueError('Sample identity mismatch')
        with self.lock:
            prior=self.state(sid)
            if state.get('revision')!=prior['revision']:raise ValueError('Revision conflict: reload sample before saving')
            d=copy.deepcopy(state)
            for kind in ['module','socket']:
                ob=d['objects'][kind]
                for frame in ['head','wrist']:
                    if ob[frame] is not None:validate_matrix(ob[frame])
                if len(ob.get('pairs',[]))>100:raise ValueError('Too many annotation points')
                for pair in ob.get('pairs',[]):
                    vid=int(pair['vertex']);uv=np.asarray(pair['pixel'],float)
                    if not 0<=vid<len(self.models[kind]['vertices']) or uv.shape!=(2,) or not np.isfinite(uv).all():raise ValueError('Invalid correspondence')
                anchors=np.asarray(ob.get('head_anchor_pixels',[]),float)
                if anchors.size and (anchors.ndim!=2 or anchors.shape[1]!=2 or len(anchors)>4 or not np.isfinite(anchors).all()):raise ValueError('Invalid initialization corners')
            if d.get('T_wrist_from_head') is not None:validate_matrix(d['T_wrist_from_head'])
            d.update(revision=prior['revision']+1,saved_unix=time.time(),training_label_valid=False,physical_accuracy_validated=False,
                     wrist_calibration=self.binding,source_metadata_sha256=self.samples[sid]['metadata_sha256'],
                     source_images=self.samples[sid]['meta']['images'],models={k:v['version'] for k,v in self.models.items()},
                     frame_names={'head':'camera_infra1_optical_frame','wrist':'omi_wrist_camera_optical'},
                     units='meters',euler_display='degrees extrinsic xyz; Rz(yaw) Ry(pitch) Rx(roll)')
            # Relative pose in each camera independently; no false fusion claim.
            d['relative_socket_from_module']={}
            for frame in ['head','wrist']:
                m=d['objects']['module'][frame];s=d['objects']['socket'][frame]
                if m is not None and s is not None:d['relative_socket_from_module'][frame]=(np.linalg.inv(s)@m).tolist()
            atomic_json(self.output/'history'/sid/f'{d["revision"]:06d}_{uuid.uuid4().hex[:8]}.json',d)
            atomic_json(self.output/'annotations'/f'{sid}.json',d)
            return d

    def sample(self,sid):
        s=self.samples[sid]
        proposal_path=self.output/'initialization_proposals'/f'{sid}.json'
        proposals={}
        if proposal_path.exists():
            p=read(proposal_path)
            if p.get('source_metadata_sha256')==s['metadata_sha256']:
                proposals={k:v for k,v in p.get('objects',{}).items() if k in self.models and v.get('model_version')==self.models[k]['version']}
        return {'id':sid,'unit':s['unit'],'state':self.state(sid),'head_calibration':s['meta']['calibration']['color'],
                'initialization_proposals':proposals,
                'T_color_from_head':optical_extrinsic(s['meta']).tolist(),'wrist_calibration':self.cal,
                'calibration_binding':self.binding,'has_cloud':self.cloud_path(sid) is not None,
                'cloud_layout':'xyz_rgb_head_uv_float32','cloud_color_source':'associated head RGB through per-sample IR-to-RGB calibration; gray outside RGB FOV',
                'receipt_delta_ms':s['meta'].get('wrist_left_receipt_delta_ms'),'exposure_synchronization_verified':False}

    def generate(self,sid):
        with self.lock:
            if self.cloud_path(sid):return {'status':'complete'}
            if self.jobs.get(sid,{}).get('status') in ['queued','running']:return self.jobs[sid]
            self.jobs[sid]={'status':'queued'}
        def work():
            try:
                with self.gpu_lock:
                    self.jobs[sid]={'status':'running'}
                    out=self.output/'clouds'/sid;out.mkdir(parents=True,exist_ok=True)
                    script=Path(__file__).resolve().parents[3]/'FoundationStereo/scripts/infer_pose_review_sample.py'
                    cmd=['/data/omi_runtime/envs/foundation_stereo/bin/python',str(script),'--sample',str(self.samples[sid]['path']/'sample.json'),'--output',str(out),'--checkpoint','/data/omi_runtime/models/FoundationStereo/11-33-40/model_best_bp2.pth']
                    with (out/'inference.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=600)
                    self.cloud.cache_clear();self.colored_cloud.cache_clear();self.jobs[sid]={'status':'complete'}
            except Exception as e:self.jobs[sid]={'status':'failed','error':str(e),'log':str(self.output/'clouds'/sid/'inference.log')}
        threading.Thread(target=work,daemon=True).start();return self.jobs[sid]


def handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def send(self,data,kind='application/json',code=200):
            if kind=='application/json':data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(code);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            try:
                path=urlparse(self.path);q=parse_qs(path.query);sid=q.get('id',[''])[0]
                if path.path=='/':self.send(Path(__file__).with_name('pose_review.html').read_bytes(),'text/html; charset=utf-8')
                elif path.path=='/api/index':self.send({'samples':[{'id':s['id'],'unit':s['unit'],'has_cloud':app.cloud_path(s['id']) is not None,'saved':(app.output/'annotations'/f'{s["id"]}.json').exists()} for s in app.samples.values()],'output':str(app.output),'model_versions':{k:v['version'] for k,v in app.models.items()}})
                elif path.path=='/api/models':self.send({k:{'lines':v['lines'].round(8).tolist(),'main_line_count':v['main_line_count'],'vertices':v['vertices'].round(8).tolist(),'bounds':v['bounds'].tolist(),'version':v['version'],'guide':GUIDES[k]} for k,v in app.models.items()})
                elif path.path=='/api/sample':self.send(app.sample(sid))
                elif path.path=='/api/cloud':
                    self.send(app.display_cloud(sid).tobytes(),'application/octet-stream')
                elif path.path=='/api/job':self.send(app.jobs.get(sid,{'status':'idle'}))
                elif path.path=='/api/image':
                    view=q.get('view',['wrist'])[0]
                    if view not in ['wrist','color']:raise ValueError('Unknown view')
                    s=app.samples[sid];p=s['path']/s['meta']['images'][view]['file'];self.send(p.read_bytes(),'image/png')
                else:self.send({'error':'Not found'},code=404)
            except (KeyError,ValueError,FileNotFoundError) as e:self.send({'error':str(e)},code=400)
            except Exception as e:traceback.print_exc();self.send({'error':str(e)},code=500)
        def do_POST(self):
            try:
                origin=self.headers.get('Origin')
                if origin and origin != 'http://'+self.headers.get('Host',''):raise ValueError('Cross-origin request rejected')
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<2000000:raise ValueError('Invalid request size')
                data=json.loads(self.rfile.read(n));sid=data['id'];s=app.samples[sid]
                if self.path=='/api/save':self.send(app.save(sid,data['state']))
                elif self.path=='/api/generate':self.send(app.generate(sid))
                elif self.path=='/api/coarse':
                    kind=data['object'];model=app.models[kind];points,_=app.cloud(sid);q=roi_cloud(points,s['meta'],data['roi'])
                    self.send({'candidates':coarse_candidates(model['samples'],q,data.get('initial')),'roi_points':len(q),'automatic_full_scene_detection':False,'physical_accuracy_validated':False})
                elif self.path=='/api/guided':
                    kind=data['object'];points,_=app.cloud(sid)
                    result=guided_initialize(GUIDES[kind]['points'],data['pixels'],points,s['meta'])
                    p=np.array(data['pixels']);rect=np.r_[p.min(0)-3,p.max(0)+3].tolist()
                    observed=roi_cloud(points,s['meta'],rect)
                    result.update(fit_metrics(app.models[kind]['samples'],observed,np.array(result['T'])))
                    result['roi']=rect;result['guide']=GUIDES[kind];self.send(result)
                elif self.path=='/api/refine':
                    kind=data['object'];pairs=data['pairs'];vertices=app.models[kind]['vertices'];ix=[int(p['vertex']) for p in pairs]
                    if any(i<0 or i>=len(vertices) for i in ix):raise ValueError('Invalid mesh vertex ID')
                    self.send(refine_pixels(vertices[ix],[p['pixel'] for p in pairs],data['T'],app.cal))
                else:self.send({'error':'Not found'},code=404)
            except (KeyError,ValueError,FileNotFoundError) as e:self.send({'error':str(e)},code=400)
            except Exception as e:traceback.print_exc();self.send({'error':str(e)},code=500)
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--backup',default=DEFAULT_BACKUP);p.add_argument('--output',required=True);p.add_argument('--calibration',default='/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json');p.add_argument('--port',type=int,default=8876);a=p.parse_args()
    app=Review(a.backup,a.output,a.calibration)
    server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(app))
    print(f'Pose review: http://127.0.0.1:{a.port} | {len(app.samples)} samples | {app.output}',flush=True)
    server.serve_forever()


if __name__=='__main__':main()
