"""Run marker-free structural observations on the real wrist video."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from structural_edge_pose import StructuralModel,StructuralDetector,StructuralPoseSolver,load_ownership_masks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--ownership',type=Path,required=True);a=p.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=False);(root/'images').mkdir()
    prior=Path('/data/omi_runtime/runs/v2d_wrist_trial_20261121');cal_path=Path('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json');cal=json.loads(cal_path.read_text())
    model_inputs=Path('/data/omi_runtime/runs/v3_socket_insertion_20261120T073119Z/inputs');model=StructuralModel(model_inputs);detector=StructuralDetector(cal)
    catalogue=model.catalogue();(root/'structure_catalogue.json').write_text(json.dumps(catalogue,indent=2))
    record=json.loads((prior/'pixel_refinement_results.json').read_text())['records'][0];T=np.array(record['T_rect_from_model']);R4=np.eye(4);R4[:3,:3]=np.load(prior/'rectification.npz')['R_rect_from_raw'].T;T=R4@T
    solver=StructuralPoseSolver(model,cal,T)
    meta=json.loads((prior/'inputs.json').read_text());ownership_meta=json.loads((a.ownership/'inputs.json').read_text())
    if ownership_meta['source_frames']!=meta['source_frames'] or Path(ownership_meta['video']).resolve()!=Path(meta['input']).resolve():
        raise ValueError('Ownership masks must correspond to the same video and exact source frame indices')
    if not ownership_meta.get('printed_patch_removed_before_segmentation'):
        raise ValueError('Marker must be excluded before segmentation')
    cap=cv2.VideoCapture(meta['input']);records=[];checks=[]
    for i,source in enumerate(meta['source_frames']):
        cap.set(cv2.CAP_PROP_POS_FRAMES,source);ok,image=cap.read()
        if not ok:raise ValueError(source)
        ownership=load_ownership_masks(a.ownership,i,image.shape[:2])
        observed,exclude,_=detector.detect(image,ownership);result=solver.solve(observed,multistart=i==0)
        result.update(index=i,source_frame=source,time_s=source/30.,features=observed)
        records.append(result)
        if i in [0,10,20,30,40,50,60]:cv2.imwrite(str(root/'images'/f'{i:06d}.png'),image)
        if i in [0,30,60]:
            baseline=StructuralPoseSolver(model,cal,T).solve(observed,multistart=True)
            for variant in ['black','white','noise']:
                changed=image.copy()
                if variant=='noise':changed[exclude>0]=np.random.default_rng(55).integers(0,256,(int((exclude>0).sum()),3),dtype=np.uint8)
                else:changed[exclude>0]=0 if variant=='black' else 255
                other,_,_=detector.detect(changed,ownership)
                assert observed==other,'Marker replacement changed structural observations'
                after=StructuralPoseSolver(model,cal,T).solve(other,multistart=True)
                if baseline['T_camera_from_model'] is None:assert after['T_camera_from_model'] is None
                else:assert np.allclose(baseline['T_camera_from_model'],after['T_camera_from_model'],atol=1e-10)
                checks.append({'frame':source,'replacement':variant,'features_identical':True,'pose_identical':True})
        (root/'results.json').write_text(json.dumps(records,indent=2))
        print(source,result['status'],len(result['observed_lines']),result.get('line_residual_rms_pixel_equivalent'),flush=True)
    cap.release()
    # Explicit detection of loss: no visibility mask is given to the extractor.
    image=cv2.imread(str(root/'images/000000.png'));clean_pose=np.array(records[0]['T_camera_from_model']) if records[0]['T_camera_from_model'] is not None else T.copy();controls=[]
    control_ownership=load_ownership_masks(a.ownership,0,image.shape[:2])
    for name,rectangle in [('clear',None),('shaft_hidden',(925,675,1020,728)),('whole_module_hidden',(925,675,1020,820))]:
        test=image.copy()
        if rectangle is not None:cv2.rectangle(test,rectangle[:2],rectangle[2:],(128,128,128),-1)
        obs,_,_=detector.detect(test,control_ownership);result=StructuralPoseSolver(model,cal,clean_pose).solve(obs)
        result.update(case=name,features=obs,visibility_mask_given=False,absolute_pose_truth=False)
        controls.append(result);cv2.imwrite(str(root/(name+'.png')),test)
    (root/'occlusion_checks.json').write_text(json.dumps(controls,indent=2))
    if controls[-1]['T_camera_from_model'] is not None:raise RuntimeError('Fully hidden object produced an unsupported pose')
    (root/'marker_exclusion_checks.json').write_text(json.dumps({'scope':'Same rough pose/search priors; arbitrary patch replacement before feature extraction','cases':checks,'passed':True},indent=2))
    poses=[np.array(x['T_camera_from_model']) for x in records if x['T_camera_from_model'] is not None]
    observed_counts={name:sum(x['features'].get(name,{}).get('status')=='observed' for x in records) for name in model.lines}
    summary={'frames':len(records),'statuses':{s:sum(x['status']==s for x in records) for s in set(x['status'] for x in records)},
             'potential_model_feature_ids':list(model.lines),'active_feature_ids':[name for name,count in observed_counts.items() if count>0],
             'observed_frames_by_feature':observed_counts,
             'mean_line_fit_residual_pixel_equivalent':float(np.mean([x['line_residual_rms_pixel_equivalent'] for x in records if 'line_residual_rms_pixel_equivalent' in x])),
             'printed_patch_used':False,'added_marker_identity_or_3d_coordinates_used':False,'patch_replacement_invariance_verified':True,'model_rescaled':False,
             'physical_pose_accuracy_validated':False,'pose_prior':'Previous coarse body pose supplies only a search/face prior; no marker correspondence used',
             'limitations':['Known wrist/grasp view ROIs','Three-dimensional line identities and model dimensions require physical verification','Head step and insertion notches not used when not observable','Geometric fit residual is not pose accuracy']}
    (root/'summary.json').write_text(json.dumps(summary,indent=2))
    (root/'inputs.json').write_text(json.dumps({'video':meta['input'],'calibration':str(cal_path),'model_inputs':str(model_inputs),'initial_pose':T.tolist(),
        'source_frames':meta['source_frames'],'ownership_masks':str(a.ownership),'ignored_patch_polygon_raw_px':detector.exclude_polygon.tolist(),
        'ignored_patch_use':'Exclusion only, never a fitting feature','camera_calibration_sha256':hashlib.sha256(cal_path.read_bytes()).hexdigest()},indent=2))


if __name__=='__main__':main()
