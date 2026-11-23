"""Prepare and run the wrist mesh-feature tracking prototype on real inputs."""
import argparse
import json
import os
from pathlib import Path
import time
import cv2
import numpy as np
from scipy.spatial.transform import Rotation
from mesh_feature_tracker import FisheyeCamera, MeshSurface, MeshFeatureTracker

MODEL=Path('/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/inputs')
CALIBRATION=Path('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json')
WRIST=Path('/data/omi_runtime/runs/v2d_wrist_trial_20261121')
BATCH=Path('/data/omi_runtime/runs/episode_v3_mesh_batch_20261120T163456Z/batch')
EPISODES=['8083942d4ead4367aa334198e7a9890f','19c7887c59f34dcb9d53bd1d8bc9b950','015d0561623342f5a179834d526f1f61']


def make_camera(case,cal):
    return FisheyeCamera(cal,case['image_size'],origin=case.get('origin',[0,0]),episode_roi=case['camera_kind']=='episode_roi')


def prepare(root,segment_episodes):
    root.mkdir(parents=True,exist_ok=False);cal=json.loads(CALIBRATION.read_text());cases=[]
    full=root/'full_fisheye_video';full.mkdir();(full/'images').mkdir();(full/'masks').mkdir()
    inputs=json.loads((WRIST/'inputs.json').read_text());rect=np.load(WRIST/'rectification.npz');pose=json.loads((WRIST/'pixel_refinement_results.json').read_text())['records'][0]
    T=np.array(pose['T_rect_from_model']);to_raw=np.eye(4);to_raw[:3,:3]=rect['R_rect_from_raw'].T;T=to_raw@T
    case={'id':'full_fisheye_video','camera_kind':'raw_crop','image_size':[360,440],'origin':[800,540],
          'initial_pose':T.tolist(),'initial_pose_source':'Previous first-frame PnP/silhouette hypothesis, not calibrated pose truth','frames':[]}
    camera=make_camera(case,cal);yy,xx=np.indices((440,360));rays=camera.rays(np.c_[xx.ravel(),yy.ravel()])@rect['R_rect_from_raw'].T;uv=rays@rect['K'].T;uv=uv[:,:2]/uv[:,2,None]
    mx=uv[:,0].reshape(440,360).astype(np.float32);my=uv[:,1].reshape(440,360).astype(np.float32)
    cap=cv2.VideoCapture(inputs['input'])
    for index,source in enumerate(inputs['source_frames']):
        cap.set(cv2.CAP_PROP_POS_FRAMES,source);ok,image=cap.read()
        if not ok:raise ValueError(source)
        image=image[540:980,800:1160];mask=cv2.imread(str(WRIST/'masks/1'/f'{index:06d}.png'),0);mask=cv2.remap(mask,mx,my,cv2.INTER_NEAREST)
        ip=full/'images'/f'{index:06d}.png';mp=full/'masks'/f'{index:06d}.png';cv2.imwrite(str(ip),image);cv2.imwrite(str(mp),mask)
        case['frames'].append({'index':index,'source_frame':source,'time_s':source/30.,'image':str(ip),'mask':str(mp)})
    cap.release();cases.append(case)
    rows=[json.loads(line) for line in (BATCH/'frame_results.jsonl').open()]
    for episode in EPISODES:
        records=sorted([r for r in rows if r['episode']==episode],key=lambda r:r['tick'])
        first=records[0]
        if first['pose'] is None:raise ValueError('Missing initialization for '+episode)
        T=np.eye(4);T[:3,:3]=cv2.Rodrigues(np.array(first['pose'][:3]))[0];T[:3,3]=np.array(first['pose'][3:])/1000
        folder=root/episode[:8];folder.mkdir();(folder/'sam_images').mkdir()
        case={'id':episode[:8],'episode':episode,'camera_kind':'episode_roi','image_size':[128,128],
              'initial_pose':T.tolist(),'initial_pose_source':'Previous episode tick-0 prior; no later per-frame PnP poses used','frames':[]}
        camera=make_camera(case,cal)
        obj=np.array([[0,.025,.00653],[0,-.005,.003919],[0,.055,.002],[-.022,.020,.005],[.022,.020,.005],[0,-.07,.003919]])
        uv=camera.project(obj,T);labels=[1,1,0,0,0,0]
        valid=(uv[:,0]>=0)&(uv[:,0]<128)&(uv[:,1]>=0)&(uv[:,1]<128)
        prompt={'prompts':[{'frame_index':0,'object_id':1,'points':[{'x':float(x),'y':float(y)} for x,y in uv[valid]],'point_labels':[lab for lab,v in zip(labels,valid) if v]}]}
        (folder/'prompts.json').write_text(json.dumps(prompt,indent=2))
        if segment_episodes:
            for index,row in enumerate(records):
                image=cv2.imread(row['image']);cv2.imwrite(str(folder/'sam_images'/f'{index:06d}.jpg'),image,[cv2.IMWRITE_JPEG_QUALITY,99])
            os.environ['CONFIG_FILE']='configs/sam2.1/sam2.1_hiera_s.yaml';os.environ['CHECKPOINT_FILE']='sam2.1_hiera_small.pt'
            from v2d.sam2.lib.video_to_masks import video_to_masks
            video_to_masks(str(folder/'sam_images'),str(folder/'prompts.json'),str(folder/'masks'),'/data/omi_runtime/baselines/reconstruction_20261119/workspace/BundleSDF_trial/runtime/sam2_source/checkpoints')
        for index,row in enumerate(records):
            case['frames'].append({'index':index,'source_frame':row['tick'],'time_s':(row['reference_ns']-records[0]['reference_ns'])/1e9,'image':row['image'],
                                  'mask':str(folder/'masks/1'/f'{index:06d}.png') if segment_episodes else None,
                                  'old_per_frame_pose_status':row['status'],'old_per_frame_pose':row['pose']})
        cases.append(case)
        (root/'cases.json').write_text(json.dumps({'calibration':str(CALIBRATION),'module_inputs':str(MODEL),'cases':cases},indent=2))
    (root/'cases.json').write_text(json.dumps({'calibration':str(CALIBRATION),'module_inputs':str(MODEL),'cases':cases},indent=2))


def run_cases(root,result_subdir=None,experimental_se3=False):
    description=json.loads((root/'cases.json').read_text());cal=json.loads(Path(description['calibration']).read_text());surface=MeshSurface(description['module_inputs']);summaries=[]
    results=root/result_subdir if result_subdir else root
    results.mkdir(exist_ok=True)
    for case in description['cases']:
        folder=results/case['id'];folder.mkdir(exist_ok=True);camera=make_camera(case,cal);first=case['frames'][0]
        if (folder/'tracking.json').exists():raise FileExistsError(folder/'tracking.json')
        image=cv2.imread(first['image']);mask=cv2.imread(first['mask'],0) if first['mask'] else None
        try:tracker=MeshFeatureTracker(image,camera,surface,case['initial_pose'],mask,first['time_s'],enable_se3_updates=experimental_se3)
        except ValueError as error:
            summaries.append({'id':case['id'],'status':'initialization_failed','reason':str(error)});continue
        tracker.save_reference_pack(folder,{'reference_image':first['image'],'camera_kind':case['camera_kind'],
            'image_size':case['image_size'],'origin':case.get('origin',[0,0]),'intrinsics_source':description['calibration'],
            'model_inputs':description['module_inputs'],'initial_pose_source':case['initial_pose_source']})
        records=[];started=time.perf_counter()
        for frame in case['frames']:
            image=cv2.imread(frame['image']);mask=cv2.imread(frame['mask'],0) if frame['mask'] else None
            record=tracker.update(image,frame['time_s'],mask)
            record.update(index=frame['index'],source_frame=frame['source_frame'],image=frame['image'],mask=frame['mask'])
            if frame['index']==0:
                record['state']='initializing';record['measurement_update']=False;record['measurement_dof_count']=0;record['pose_update_mode']='initial_pose_prior'
            records.append(record)
        (folder/'tracking.json').write_text(json.dumps(records,indent=2))
        states={state:sum(x['state']==state for x in records) for state in sorted(set(x['state'] for x in records))}
        values=[x['check_feature_rms_native_px'] for x in records if x['check_feature_rms_native_px'] is not None]
        summary={'id':case['id'],'frames':len(records),'reference_features':len(tracker.points),'reference_head_features':int(tracker.head.sum()),'states':states,
                 'median_check_feature_rms_native_px':float(np.median(values)) if values else None,
                 'max_translation_change_from_initial_mm':max(x['translation_from_initial_mm'] for x in records),
                 'max_rotation_change_from_initial_deg':max(x['rotation_from_initial_deg'] for x in records),
                 'processing_seconds':time.perf_counter()-started,'physical_pose_accuracy_validated':False,'initial_binding_accuracy_validated':False}
        summaries.append(summary);print(json.dumps(summary),flush=True)
        (results/'summary.json').write_text(json.dumps({'scope':'Feature tracking and conditional local pose prototype; not validated absolute 6D','cases':summaries},indent=2))
    (results/'summary.json').write_text(json.dumps({'scope':'Feature tracking and conditional local pose prototype; not validated absolute 6D','cases':summaries},indent=2))


def controlled_occlusion(root,result_subdir=None,experimental_se3=False):
    data=json.loads((root/'cases.json').read_text());case=data['cases'][0];camera=make_camera(case,json.loads(CALIBRATION.read_text()));surface=MeshSurface(MODEL)
    first=case['frames'][0];image=cv2.imread(first['image']);mask=cv2.imread(first['mask'],0);T=np.array(case['initial_pose'])
    folder=(root/result_subdir if result_subdir else root)/'controlled_occlusion';folder.mkdir(parents=True,exist_ok=False);(folder/'images').mkdir()
    tracker=MeshFeatureTracker(image,camera,surface,T,mask,enable_se3_updates=experimental_se3);atlas=tracker.atlas();(folder/'feature_atlas.json').write_text(json.dumps(atlas,indent=2))
    full_uv=camera.project(surface.vertices,T);front_uv=camera.project(surface.vertices[surface.vertices[:,1]<-.008],T)
    def box(uv,pad):
        lo=np.maximum(np.floor(uv.min(0)-pad).astype(int),0);hi=np.minimum(np.ceil(uv.max(0)+pad).astype(int),np.array([camera.width-1,camera.height-1]));return [*lo,*hi]
    front=box(front_uv,4);whole=box(full_uv,10);records=[];tip=np.array([0.,-.035093169659,0.]);initial_tip=T[:3,:3]@tip+T[:3,3]
    for i in range(26):
        frame=image.copy();phase='clear'
        if 4<=i<12:
            cv2.rectangle(frame,tuple(front[:2]),tuple(front[2:]),(150,150,150),-1);phase='front_occluded'
        elif 12<=i<19:
            cv2.rectangle(frame,tuple(whole[:2]),tuple(whole[2:]),(150,150,150),-1);phase='fully_occluded'
        elif i>=19:phase='reappeared'
        # No oracle occlusion mask is supplied to the tracker in this stress test.
        record=tracker.update(frame,i*.1,None);record['phase']=phase;record['index']=i
        P=np.array(record['prediction_for_display_only']);pred_tip=P[:3,:3]@tip+P[:3,3];record['relative_tip_drift_mm']=float(np.linalg.norm(pred_tip-initial_tip)*1000)
        path=folder/'images'/f'{i:06d}.png';cv2.imwrite(str(path),frame);record['image']=str(path);records.append(record)
    (folder/'tracking.json').write_text(json.dumps(records,indent=2))
    result={'type':'Controlled masks on one stationary real image; relative pose truth is zero motion, absolute pose is not known',
            'oracle_occlusion_mask_supplied_to_tracker':False,
            'front_occlusion_max_tip_drift_mm':max(x['relative_tip_drift_mm'] for x in records if x['phase']=='front_occluded'),
            'front_occlusion_observed_frames':sum(x['measurement_update'] for x in records if x['phase']=='front_occluded'),
            'full_occlusion_false_observed_frames':sum(x['measurement_update'] for x in records if x['phase']=='fully_occluded'),
            'full_occlusion_has_lost_state':any(x['state']=='lost' for x in records if x['phase']=='fully_occluded'),
            'reappearance_observed_frames':sum(x['measurement_update'] for x in records if x['phase']=='reappeared'),
            'physical_accuracy_validated':False}
    (folder/'checks.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--prepare',action='store_true');p.add_argument('--segment-episodes',action='store_true');p.add_argument('--track',action='store_true');p.add_argument('--controlled-occlusion',action='store_true');p.add_argument('--result-subdir');p.add_argument('--experimental-se3',action='store_true',help='Diagnostic only; current image-to-mesh bindings are not calibrated');args=p.parse_args()
    cv2.setNumThreads(4)
    if args.prepare:prepare(args.run,args.segment_episodes)
    if args.track:run_cases(args.run,args.result_subdir,args.experimental_se3)
    if args.controlled_occlusion:controlled_occlusion(args.run,args.result_subdir,args.experimental_se3)


if __name__=='__main__':main()
