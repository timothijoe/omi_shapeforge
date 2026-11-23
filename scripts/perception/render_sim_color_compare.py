"""Unambiguous GT/prediction display without changing poses or evaluation.

Create separate green-GT and orange-prediction images/video panels. Preserve
the original overlaid artifacts and record unchanged metric/prediction hashes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from render_sim_surface_results import project,dots,text,video


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(root,output):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=False);(output/'frames').mkdir()
    protected=[root/'train/report.json',root/'train/test_predictions.npz',root/'train/best.pt']
    before={str(p):digest(p) for p in protected}
    original=(root/'index.html').read_text();(output/'index_before.html').write_text(original)
    begin=original.index('const data=')+len('const data=');payload,_=json.JSONDecoder().raw_decode(original[begin:])
    cfg=json.loads((root/'train/config.json').read_text());K=np.array(cfg['calibration']['K']);D=np.array(cfg['calibration']['D'])
    W,H=cfg['calibration']['image_width'],cfg['calibration']['image_height'];x0,y0,x1,y1=int(.32*W),int(.43*H),int(.68*W),int(.98*H)
    source={};counts=json.loads((Path(cfg['templates'])/'manifest.json').read_text())['recommended_counts']
    for name,n in counts.items():
        with np.load(Path(cfg['templates'])/f'{name}_{n}.npz') as a:
            ids=[]
            for level,budget in [(0,300),(1,650),(2,850)]:
                candidates=np.flatnonzero(a['representation_level']==level);ids.extend(candidates[np.linspace(0,len(candidates)-1,min(budget,len(candidates))).astype(int)])
            source[name]=(a['points_m'][ids],a['normals'][ids])
    frames=[];relative=output.relative_to(root)
    for row in payload['frames']:
        raw=cv2.imread(str(root/row['image']));gt_image=raw.copy();pred_image=raw.copy();overlay=raw.copy();gt_pixels=[]
        for i,name in enumerate(['module','socket']):
            points,normals=source[name];gt=np.array(row['gt'][i]);pred=np.array(row['pred'][i]);xyz=points@gt[:3,:3].T+gt[:3,3];normal=normals@gt[:3,:3].T
            points=points[(normal*xyz).sum(1)<0]
            uv,valid=project(points,gt,K,D);dots(gt_image,uv,valid,(60,255,40),.92);gt_pixels.append(uv[valid][::5])
            uv,valid=project(points,pred,K,D);dots(pred_image,uv,valid,(20,130,255),.92);dots(overlay,uv,valid,(20,130,255),.85)
        def crop(im):return cv2.resize(im[y0:y1,x0:x1],(640,540))
        gt_detail=crop(gt_image);pred_detail=crop(pred_image);combined=crop(overlay)
        for points in gt_pixels:
            coords=(points-[x0,y0])*[640/(x1-x0),540/(y1-y0)]
            for u,v in np.rint(coords).astype(int):
                if 0<=u<640 and 0<=v<540:cv2.circle(combined,(int(u),int(v)),3,(60,255,40),1,cv2.LINE_AA)
        pair=np.hstack([gt_detail,pred_detail]);header=np.full((62,1280,3),22,np.uint8)
        text(header,f"{row['episode']}  frame {row['frame']:02d}  |  same frame, same crop",16,22,.6)
        text(header,'GROUND TRUTH - GREEN',16,49,.65,(60,255,40));text(header,'PREDICTION - ORANGE',656,49,.65,(20,130,255))
        footer=np.full((40,1280,3),22,np.uint8)
        text(footer,f"Module {row['translation_mm'][0]:.2f}mm / {row['rotation_deg'][0]:.2f}deg | Socket {row['translation_mm'][1]:.2f}mm / {row['rotation_deg'][1]:.2f}deg | Relative tip {row['relative_tip_error_mm']:.2f}mm",16,26,.58)
        comparison=np.vstack([header,pair,footer])
        fid=row['id'];items={'gt_detail':gt_detail,'pred_detail':pred_detail,'overlay_rings':combined,'separate_compare':comparison}
        for key,im in items.items():
            rel=relative/'frames'/f'{fid:06d}_{key}.jpg';cv2.imwrite(str(root/rel),im,[cv2.IMWRITE_JPEG_QUALITY,96]);row[key]=str(rel)
        frames.append(row)
    selected=payload['selected_video_episodes']
    images=[cv2.imread(str(root/r['separate_compare'])) for episode in selected for r in frames if r['episode']==episode]
    fps=json.loads((root/'data/config.json').read_text())['fps'];path=output/'heldout_gt_pred_separate.mp4';video(path,images,fps)
    capture=cv2.VideoCapture(str(path));ok,frame=capture.read();capture.release()
    if not ok:raise ValueError('Comparison video cannot be decoded')
    left=frame[:,:640];right=frame[:,640:]
    green=(left[:,:,1]>200)&(left[:,:,2]<120)&(left[:,:,0]<150)
    orange=(right[:,:,2]>200)&(right[:,:,1]>65)&(right[:,:,1]<175)&(right[:,:,0]<120)
    if green.sum()<300 or orange.sum()<300:raise ValueError('Encoded colors are not sufficiently visible')
    cv2.imwrite(str(output/'video_first_frame.png'),frame)
    payload['clear_compare_video']=str(path.relative_to(root));payload['clear_color_compare']=True
    template=Path(__file__).with_name('sim_surface_results.html').read_text();(root/'index.html').write_text(template.replace('__PAYLOAD__',json.dumps(payload,separators=(',',':'))))
    (output/'frame_manifest.json').write_text(json.dumps(frames,indent=2))
    after={str(p):digest(p) for p in protected}
    if before!=after:raise ValueError('Model or predictions changed while rendering')
    report={'frames':len(frames),'video':str(path),'video_episodes':selected,'same_crop_and_scale_for_GT_and_prediction':True,
            'decoded_video_first_frame_green_pixels_left':int(green.sum()),'decoded_video_first_frame_orange_pixels_right':int(orange.sum()),
            'unchanged_inputs':before,'pose_or_metric_changes':False,'old_overlays_preserved':True}
    (output/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.run,a.output)
