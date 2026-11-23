"""Verify a saved trained model's full image-only surface output on held-out RGB."""
import argparse
import inspect
import json
from pathlib import Path
import cv2
import numpy as np
import torch
from PIL import Image
from scipy.spatial.transform import Rotation
from image_to_surface_network import ImageToCompleteSurface
from build_surface_representation import write_ply
from train_sim_wrist_surface import errors,summarize


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run;out=root/'full_forward_check';out.mkdir(exist_ok=False)
    torch.set_num_threads(4);checkpoint=torch.load(root/'train/best.pt',map_location='cpu',weights_only=True);cfg=checkpoint['config'];device='cuda' if torch.cuda.is_available() else 'cpu'
    model=ImageToCompleteSurface(cfg['templates'],cfg['calibration']).to(device).eval();model.load_state_dict(checkpoint['model']);model.weights_status='trained_on_simulation'
    if list(inspect.signature(model.forward).parameters)!=['images']:raise ValueError('Model interface gained privileged inputs')
    predictions=np.load(root/'train/test_predictions.npz');records={r['id']:r for r in map(json.loads,(root/'data/records.jsonl').read_text().splitlines())}
    selected=sorted(set([0,len(predictions['frame_ids'])//2,int(np.argmax(predictions['tip_in_socket_error_mm']))]));reports=[]
    for i in selected:
        frame_id=int(predictions['frame_ids'][i]);r=records[frame_id]
        im=np.asarray(Image.open(root/'data'/r['image']).convert('RGB')).copy();x=torch.from_numpy(im).permute(2,0,1)[None].float().to(device)/255
        with torch.no_grad():result=model(x)
        arrays={};report={'frame_id':frame_id,'episode':r['episode'],'objects':{}}
        for j,name in enumerate(model.names):
            o=result[name];points=o['points_m'][0].cpu().numpy();T=o['T_camera_from_model'][0].cpu().numpy();template=getattr(model,name+'_template').cpu().numpy()
            predicted_from_T=template@T[:3,:3].T+T[:3,3];rigid=float(np.max(abs(predicted_from_T-points)));batch=float(np.max(abs(T-predictions['pred'][i,j])))
            saved=predictions['pred'][i,j];dt=float(np.linalg.norm(T[:3,3]-saved[:3,3])*1000)
            angle=float(np.rad2deg(Rotation.from_matrix(T[:3,:3].astype(float)@saved[:3,:3].astype(float).T).magnitude()))
            saved_points=template@saved[:3,:3].T+saved[:3,3];cloud_difference=float(np.max(np.linalg.norm(points-saved_points,axis=1))*1000)
            # CUDA convolution reductions differ slightly between B=1 and B=16.
            # Check geometric units rather than requiring bit-identical matrices.
            if rigid>1e-6 or dt>.01 or angle>.02 or cloud_difference>.05 or not np.isfinite(points).all():raise ValueError(f'Full output differs at {frame_id}/{name}: rigid={rigid}, translation={dt} mm, rotation={angle} deg, cloud={cloud_difference} mm')
            gt=predictions['gt'][i,j];arrays[name+'_prediction_points_m']=points;arrays[name+'_gt_points_m']=template@gt[:3,:3].T+gt[:3,3]
            source=np.load(Path(cfg['templates'])/f'{name}_{model.counts[name]}.npz');write_ply(out/f'{frame_id:06d}_{name}_prediction.ply',{'points_m':points,'rgb':source['rgb']})
            report['objects'][name]={'shape':list(points.shape),'rigid_expansion_max_difference_m':rigid,'batch_vs_single_T_max_difference':batch,
                                    'batch_vs_single_translation_mm':dt,'batch_vs_single_rotation_deg':angle,'batch_vs_single_cloud_max_mm':cloud_difference}
        np.savez_compressed(out/f'{frame_id:06d}_complete_surfaces.npz',**arrays);reports.append(report)
    rng=np.random.default_rng(773);perm=rng.permutation(len(predictions['pred']))
    permuted=summarize(errors(torch.from_numpy(predictions['pred'][perm]),torch.from_numpy(predictions['gt'])))
    report={'full_forward_image_only_verified':True,'model_dynamic_arguments':['images'],'selected_frames':reports,
            'negative_control':'Saved deterministic predictions paired with randomly permuted test labels; equivalent to shuffling image-label pairing for this per-image eval model',
            'permuted_pairing_metrics':permuted,'permutation_seed':773,'visibility_head_trained':False,'physical_accuracy_validated':False}
    report['batch_single_numeric_tolerances']={'translation_mm':.01,'rotation_deg':.02,'max_surface_point_difference_mm':.05}
    (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
