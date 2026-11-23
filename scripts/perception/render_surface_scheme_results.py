"""Apply regular whole/local-only representations to the same frozen predictions."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from render_sim_surface_results import project,text,video


def pack(parts):
    p=np.concatenate([x['points_m'] for x in parts]);level=np.concatenate([x['representation_level'] for x in parts])
    data=np.c_[p,level].astype('<f4')
    return {'data':base64.b64encode(data.tobytes()).decode(),'count':len(p)}


def screen_samples(candidates,spacing,width=640,height=540):
    """Select existing projected points, never snap them to cell centers."""
    if not len(candidates):return candidates
    q=candidates;cell=np.floor(q[:,:2]/spacing).astype(int);key=cell[:,1]*(int(np.ceil(width/spacing))+2)+cell[:,0]
    order=np.lexsort((q[:,2],key));_,first=np.unique(key[order],return_index=True)
    return q[order[first]]


def projected_samples(arrays,transforms,K,D,crop):
    x0,y0,x1,y1=crop;items=[]
    for j,name in enumerate(['module','socket']):
        a=arrays[name];T=np.asarray(transforms[j]);xyz=a['points_m']@T[:3,:3].T+T[:3,3];normals=a['normals']@T[:3,:3].T
        take=(normals*xyz).sum(1)<0;uv,valid=project(a['points_m'][take],T,K,D);xyz=xyz[take];level=a['representation_level'][take]
        uv=(uv-[x0,y0])*[640/(x1-x0),540/(y1-y0)];valid&=(uv[:,0]>=1)&(uv[:,0]<638)&(uv[:,1]>=1)&(uv[:,1]<538)
        items.append(np.c_[uv[valid],xyz[valid,2],level[valid]])
    q=np.concatenate(items)
    # Frontmost point per display pixel approximates self-occlusion. Gripper
    # occlusion is not a GT mask for hiding incorrectly projected predictions.
    pixel=np.rint(q[:,:2]).astype(int);key=pixel[:,1]*640+pixel[:,0];depth=np.full(640*540,np.inf);np.minimum.at(depth,key,q[:,2]);q=q[q[:,2]<=depth[key]+.0005]
    ordinary=screen_samples(q[q[:,3]<.5],6);focus=screen_samples(q[q[:,3]>.5],3)
    return ordinary,focus


def paint(image,ordinary,focus,color):
    result=image.copy()
    for points,tint,radius in [(ordinary,(175,185,198),0),(focus,color,1)]:
        for u,v,*_ in points:cv2.circle(result,(int(round(u)),int(round(v))),radius,tint,-1,cv2.LINE_AA)
    return result


def build(run,templates,output):
    run=Path(run);templates=Path(templates);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    source_html=(run/'index.html').read_text();(output/'index_before.html').write_text(source_html)
    at=source_html.index('const data=')+len('const data=');payload,_=json.JSONDecoder().raw_decode(source_html[at:]);cfg=json.loads((run/'train/config.json').read_text())
    protected={str(run/rel):hashlib.sha256((run/rel).read_bytes()).hexdigest() for rel in ['train/report.json','train/test_predictions.npz','train/best.pt']}
    m=json.loads((templates/'manifest.json').read_text());arrays={};schemes={}
    for kind in ['module','socket']:
        ordinary=dict(np.load(templates/f'{kind}_ordinary.npz'));focus=dict(np.load(templates/f'{kind}_focus.npz'));arrays[kind]={'ordinary':ordinary,'focus':focus}
    for sid,label in [('whole_grid','方案一：完整规则网格＋重点加密'),('focus_only','方案二：仅尖端与孔口')]:
        schemes[sid]={'label':label,'templates':{},'counts':{},'ordinary_pitch_mm':m['ordinary_pitch_mm'],'focus_pitch_mm':m['focus_pitch_mm']}
        for name in ['module','socket']:
            selected=[arrays[name]['ordinary'],arrays[name]['focus']] if sid=='whole_grid' else [arrays[name]['focus']]
            schemes[sid]['templates'][name]=pack(selected);schemes[sid]['counts'][name]=sum(len(x['points_m']) for x in selected)
    K=np.array(cfg['calibration']['K']);D=np.array(cfg['calibration']['D']);W,H=cfg['calibration']['image_width'],cfg['calibration']['image_height'];crop=[int(.32*W),int(.43*H),int(.68*W),int(.98*H)];x0,y0,x1,y1=crop
    counts=[];relative=output.relative_to(run)
    for sid in schemes:
        folder=output/sid;(folder/'frames').mkdir(parents=True)
        selected={}
        for name in ['module','socket']:
            chosen=[arrays[name]['ordinary'],arrays[name]['focus']] if sid=='whole_grid' else [arrays[name]['focus']]
            selected[name]={key:np.concatenate([x[key] for x in chosen]) for key in ['points_m','normals','representation_level']}
        for row in payload['frames']:
            raw=cv2.imread(str(run/row['image']));detail=cv2.resize(raw[y0:y1,x0:x1],(640,540));gt=projected_samples(selected,row['gt'],K,D,crop);pred=projected_samples(selected,row['pred'],K,D,crop)
            g=paint(detail,*gt,(50,255,50));p=paint(detail,*pred,(20,130,255));overlay=paint(detail,*pred,(20,130,255))
            for u,v,*_ in gt[1][::3]:cv2.circle(overlay,(int(round(u)),int(round(v))),3,(50,255,50),1,cv2.LINE_AA)
            panel=np.hstack([g,p]);header=np.full((70,1280,3),22,np.uint8)
            scheme_title='Scheme 1: regular whole surfaces + dense task surfaces' if sid=='whole_grid' else 'Scheme 2: insertion tip + socket mouth ONLY'
            text(header,scheme_title,15,23,.60);text(header,'GT: ordinary gray / task GREEN',15,54,.60,(50,255,50));text(header,'Prediction: ordinary gray / task ORANGE',655,54,.60,(20,130,255))
            footer=np.full((38,1280,3),22,np.uint8);text(footer,f"{row['episode']} frame {row['frame']:02d} | unchanged relative tip error {row['relative_tip_error_mm']:.2f} mm | display point thinning only",15,25,.55)
            both=np.vstack([header,panel,footer]);row.setdefault('surface_schemes',{})[sid]={}
            for key,image in [('gt_detail',g),('pred_detail',p),('overlay',overlay),('comparison',both)]:
                rel=relative/sid/'frames'/f"{row['id']:06d}_{key}.jpg";cv2.imwrite(str(run/rel),image,[cv2.IMWRITE_JPEG_QUALITY,96]);row['surface_schemes'][sid][key]=str(rel)
            counts.append({'scheme':sid,'frame_id':row['id'],'gt_ordinary_display_points':len(gt[0]),'gt_focus_display_points':len(gt[1]),'pred_ordinary_display_points':len(pred[0]),'pred_focus_display_points':len(pred[1])})
        episodes=payload['selected_video_episodes'];frames=[cv2.imread(str(run/r['surface_schemes'][sid]['comparison'])) for e in episodes for r in payload['frames'] if r['episode']==e]
        path=folder/'heldout_comparison.mp4';video(path,frames,json.loads((run/'data/config.json').read_text())['fps']);schemes[sid]['video']=str(path.relative_to(run))
        cv2.imwrite(str(folder/'first_frame.png'),frames[0]);print('Rendered',sid,len(payload['frames']),'frames',flush=True)
    for name,h in protected.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=h:raise ValueError('Predictions or metrics changed')
    payload['surface_schemes']=schemes;payload['surface_scheme_manifest']=str((templates/'manifest.json'))
    html=Path(__file__).with_name('sim_surface_results.html').read_text().replace('__PAYLOAD__',json.dumps(payload,separators=(',',':')))
    (output/'index.html').write_text(html);temporary=run/'index_scheme_update.tmp';temporary.write_text(html);temporary.replace(run/'index.html')
    report={'schemes':{k:{'label':v['label'],'counts':v['counts'],'video':v['video']} for k,v in schemes.items()},'templates':str(templates),
            'same_prediction_and_GT_poses':True,'model_and_metrics_unchanged':protected,'new_training_performed':False,'scope':'display step only; training status and metrics are in train/report.json','model_was_trained':bool(payload['report']['training_performed']),'screen_spacing_px':{'ordinary':6,'focus':3},
            'display_points_are_subsets_of_geometric_points_not_snapped':True,'focus_only_has_zero_ordinary_display_points':all(r['gt_ordinary_display_points']==0 and r['pred_ordinary_display_points']==0 for r in counts if r['scheme']=='focus_only')}
    (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(output/'display_counts.json').write_text(json.dumps(counts,indent=2));print(json.dumps(report,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--templates',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.run,a.templates,a.output)
