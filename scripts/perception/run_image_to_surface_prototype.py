"""Run the untrained image -> complete point-cloud prototype and gradient checks.

This is a shape/gradient plumbing check, not a pose-accuracy demonstration.
Manual marker-ignore rectangles are image preprocessing, not pose labels.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import cv2
import numpy as np
import torch
from torch.nn import functional as F
from image_to_surface_network import ImageToCompleteSurface,supervised_surface_loss
from build_surface_representation import write_ply


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--templates',type=Path,required=True);p.add_argument('--image',type=Path,required=True);p.add_argument('--calibration',type=Path,default=Path('/home/linux/Downloads/img/wrist_intrinsics_1920x1080.json'));p.add_argument('--output',type=Path,required=True);p.add_argument('--ignore-rects',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4);torch.manual_seed(20261122)
    image=cv2.imread(str(a.image));cal=json.loads(a.calibration.read_text());mask=np.zeros(image.shape[:2],np.uint8)
    rectangles=json.loads(a.ignore_rects.read_text())['rectangles_xyxy']
    for x0,y0,x1,y1 in rectangles:mask[y0:y1,x0:x1]=255
    clean=image.copy();clean[mask>0]=127
    cv2.imwrite(str(a.output/'input_masked.png'),clean);cv2.imwrite(str(a.output/'ignored_regions.png'),mask)
    cv2.imwrite(str(a.output/'input_preview.jpg'),cv2.resize(clean,(960,540)))
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=ImageToCompleteSurface(a.templates,cal).to(device).eval()
    x=torch.from_numpy(cv2.cvtColor(clean,cv2.COLOR_BGR2RGB).copy()).permute(2,0,1)[None].float().to(device)/255
    if device=='cuda':torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
    start=time.perf_counter()
    with torch.no_grad():
        outputs=model(x)
        if device=='cuda':torch.cuda.synchronize()
        seconds=time.perf_counter()-start
        blank=model(torch.full_like(x,.5))
    arrays={};objects={}
    for name,o in outputs.items():
        for key,value in o.items():arrays[name+'_'+key]=value[0].detach().cpu().numpy()
        points=arrays[name+'_points_m'];T=arrays[name+'_T_camera_from_model'];n=model.counts[name]
        template=np.load(a.templates/f'{name}_{n}.npz')
        expected=template['points_m']@T[:3,:3].T+T[:3,3]
        error=float(np.max(np.abs(expected-points)))
        if error>1e-6 or not np.isfinite(points).all():raise ValueError('Rigid complete output check failed')
        write_ply(a.output/f'{name}_UNTRAINED_prediction.ply',{'points_m':points,'rgb':template['rgb']})
        objects[name]={'point_shape':list(points.shape),'T_camera_from_model':T.tolist(),'template_transform_max_error_m':error,
                       'rotation_determinant':float(np.linalg.det(T[:3,:3])),
                       'image_vs_gray_pose_matrix_max_change':float((o['T_camera_from_model']-blank[name]['T_camera_from_model']).abs().max()),
                       'visibility_score_status':'untrained, not calibrated confidence','prediction_valid_for_use':False}
    np.savez_compressed(a.output/'UNTRAINED_predictions.npz',**arrays)
    # Synthetic labels are used only to verify a backward pass. No optimizer,
    # no pose annotations, and no parameter updates are performed.
    pred=model(x);targets={};templates={}
    for name,o in pred.items():
        T=o['T_camera_from_model'].detach().clone();T[:,:3,3]+=torch.tensor([.008,-.004,.012],device=device);targets[name]=T;templates[name]=getattr(model,name+'_template')
    loss=supervised_surface_loss(pred,targets,templates)
    for o in pred.values():
        loss=loss+.01*F.binary_cross_entropy_with_logits(o['presence_logits'],torch.ones_like(o['presence_logits']))
        alternating=torch.arange(o['visibility_logits'].shape[1],device=device)%2
        loss=loss+.01*F.binary_cross_entropy_with_logits(o['visibility_logits'],alternating[None].float())
    loss.backward()
    grads={name:float(p.grad.norm()) for name,p in model.named_parameters() if p.grad is not None}
    if not all(np.isfinite(v) for v in grads.values()):raise ValueError('Nonfinite gradient')
    if not all(any(k.startswith(prefix) and v>0 for k,v in grads.items()) for prefix in ['attention','pose_heads.module','pose_heads.socket','visibility_heads.module','visibility_heads.socket']):raise ValueError('One output head has no gradient')
    report={'status':'untrained_network_forward_and_backward_checked','training_performed':False,'optimizer_steps':0,'input_pose_labels_used':False,'pretrained_backbone_used':False,
            'source_image':str(a.image),'source_image_sha256':hashlib.sha256(a.image.read_bytes()).hexdigest(),'ignore_rectangles':rectangles,'ignore_regions_source':'manual first-frame preprocessing, not automatic marker detection',
            'calibration':str(a.calibration),'calibration_sha256':hashlib.sha256(a.calibration.read_bytes()).hexdigest(),'new_capture_intrinsics_identity_verified':False,
            'templates':str(a.templates),'template_manifest_sha256':hashlib.sha256((a.templates/'manifest.json').read_bytes()).hexdigest(),
            'input_shape':list(x.shape),'input_dynamic_arguments':['RGB image only'],'objects':objects,'device':device,'torch':torch.__version__,
            'parameters':sum(p.numel() for p in model.parameters()),'first_forward_seconds':seconds,'finite_gradient_parameter_tensors':len(grads),
            'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated() if device=='cuda' else None,'synthetic_gradient_check_loss':float(loss.detach()),
            'physical_pose_accuracy_validated':False,'point_order_stable':True,'free_deformation_or_scale_prediction':False}
    (a.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
