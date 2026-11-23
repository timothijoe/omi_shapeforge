"""Single-image inference using a saved simulation-trained surface estimator."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
import torch
from image_to_surface_network import ImageToCompleteSurface
from build_surface_representation import write_ply


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--templates',type=Path);p.add_argument('--resize-full-frame',action='store_true');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);checkpoint=torch.load(a.checkpoint,map_location='cpu',weights_only=True);cfg=checkpoint['config'];templates=a.templates or Path(cfg['templates'])
    if hashlib.sha256((templates/'manifest.json').read_bytes()).hexdigest()!=cfg['template_manifest_sha256']:raise ValueError('Template contract differs from training checkpoint')
    model=ImageToCompleteSurface(templates,cfg['calibration']);model.load_state_dict(checkpoint['model']);device='cuda' if torch.cuda.is_available() else 'cpu';model=model.to(device).eval()
    image=Image.open(a.image).convert('RGB');original_size=image.size;expected=model.image_size
    if image.size!=expected:
        if not a.resize_full_frame or abs(image.width/image.height-expected[0]/expected[1])>1e-6:raise ValueError(f'Expected full-frame {expected}; explicitly allow same-aspect full-frame resize if appropriate')
        image=image.resize(expected,Image.Resampling.BILINEAR)
    x=torch.from_numpy(np.asarray(image).copy()).permute(2,0,1)[None].float().to(device)/255
    with torch.no_grad():outputs=model(x)
    arrays={};poses={}
    for name,o in outputs.items():
        for key in ['points_m','normals','T_camera_from_model','representation_level']:arrays[name+'_'+key]=o[key][0].cpu().numpy()
        source=np.load(templates/f'{name}_{model.counts[name]}.npz');write_ply(a.output/f'{name}_prediction.ply',{'points_m':arrays[name+'_points_m'],'rgb':source['rgb']})
        poses[name]={'point_count':model.counts[name],'T_camera_from_model':arrays[name+'_T_camera_from_model'].tolist()}
    np.savez_compressed(a.output/'complete_surfaces.npz',**arrays)
    report={'source_image':str(a.image),'source_image_sha256':hashlib.sha256(a.image.read_bytes()).hexdigest(),'checkpoint':str(a.checkpoint),'checkpoint_sha256':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),
            'original_image_size':original_size,'model_input_size':expected,'resized':original_size!=expected,'input_arguments_to_network':['RGB image only'],
            'coordinate_frame':'wrist camera optical: x right, y down, z forward','units':'meters','objects':poses,
            'training_domain':cfg.get('training_domain','MuJoCo kinematic randomized grasp/arm rendering'),'prediction_accuracy_for_this_input_validated':False,'real_image_accuracy_validated':False,'visibility_scores_exported':False,
            'note':'Complete geometry includes shape-prior inference of hidden surfaces. No manual pose or point-cloud input was used.'}
    (a.output/'prediction.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=='__main__':main()
