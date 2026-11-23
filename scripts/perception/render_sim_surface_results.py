"""Render held-out image/point-cloud comparisons; never feed labels into inference."""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def project(p,T,K,D):
    q=p@T[:3,:3].T+T[:3,3]
    uv=cv2.fisheye.projectPoints(q[:,None,:],np.zeros(3),np.zeros(3),K,D)[0][:,0]
    return uv,q[:,2]>.001


def dots(image,uv,valid,color,alpha=.65):
    h,w=image.shape[:2];x,y=np.rint(uv).astype(int).T;ok=valid&(x>=0)&(x<w)&(y>=0)&(y<h)
    mask=np.zeros((h,w),np.uint8);mask[y[ok],x[ok]]=255;mask=cv2.dilate(mask,np.ones((2,2),np.uint8))>0
    image[mask]=np.rint(image[mask]*(1-alpha)+np.array(color)*alpha).astype('uint8')


def text(image,s,x,y,size=.55,color=(235,240,245)):
    cv2.putText(image,s,(x,y),cv2.FONT_HERSHEY_SIMPLEX,size,color,1,cv2.LINE_AA)


def video(path,frames,fps):
    h,w=frames[0].shape[:2]
    process=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)
    for f in frames:process.stdin.write(f.tobytes())
    process.stdin.close()
    if process.wait():raise RuntimeError('Video encoding failed')


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run;training=root/'train';out=root/'results';out.mkdir(exist_ok=False);(out/'frames').mkdir()
    config=json.loads((training/'config.json').read_text());report=json.loads((training/'report.json').read_text());prediction=np.load(training/'test_predictions.npz');cal=config['calibration'];K=np.array(cal['K']);D=np.array(cal['D'])
    records={r['id']:r for r in map(json.loads,(root/'data/records.jsonl').read_text().splitlines())};templates={};payload={'report':report,'training_config_summary':{k:config[k] for k in ['train_frames','val_frames','test_frames','image_only_at_inference','visibility_head_trained']},'templates':{},'frames':[]}
    payload['capture_summary']=json.loads((root/'data/config.json').read_text())
    failure=root/'failure_analysis.json'
    if failure.exists():payload['failure_analysis']=json.loads(failure.read_text())
    transfer=root/'transfer_evaluation/report.json'
    if transfer.exists():payload['transfer_evaluation']=json.loads(transfer.read_text())
    for name in ['module','socket']:
        m=json.loads((Path(config['templates'])/'manifest.json').read_text());n=m['recommended_counts'][name];v=np.load(Path(config['templates'])/f'{name}_{n}.npz');templates[name]={k:v[k] for k in v.files}
        packed=np.c_[v['points_m'],v['representation_level']].astype('<f4');payload['templates'][name]={'data':base64.b64encode(packed.tobytes()).decode(),'count':n}
    crop=[int(.32*cal['image_width']),int(.43*cal['image_height']),int(.68*cal['image_width']),int(.98*cal['image_height'])]
    rows=[]
    for i,frame_id in enumerate(prediction['frame_ids']):
        r=records[int(frame_id)];raw=cv2.imread(str(root/'data'/r['image']));overlay=raw.copy();Ts=prediction['pred'][i];gt=prediction['gt'][i]
        for j,name in enumerate(['module','socket']):
            d=templates[name];indices=[]
            for level,n in [(0,300),(1,650),(2,850)]:
                ids=np.flatnonzero(d['representation_level']==level);indices.extend(ids[np.linspace(0,len(ids)-1,min(n,len(ids))).astype(int)])
            indices=np.array(indices);points=d['points_m'][indices];normals=d['normals'][indices]
            xyz=points@gt[j,:3,:3].T+gt[j,:3,3];normal=normals@gt[j,:3,:3].T
            # Same GT-facing point IDs on both overlays; do not hide erroneous
            # predictions by clipping them to a GT object mask.
            facing=(normal*xyz).sum(1)<0;points=points[facing]
            uv,valid=project(points,gt[j],K,D);dots(overlay,uv,valid,(80,230,80),.6)
            uv,valid=project(points,Ts[j],K,D);dots(overlay,uv,valid,(30,150,255),.7)
        x0,y0,x1,y1=crop;detail=cv2.resize(overlay[y0:y1,x0:x1],(640,540));raw_detail=cv2.resize(raw[y0:y1,x0:x1],(640,540))
        canvas=np.full((620,1280,3),22,np.uint8);canvas[80+90:80+450,:640]=cv2.resize(raw,(640,360));canvas[80:,640:]=detail
        text(canvas,r['episode']+f"  frame {r['frame']:02d} | held-out configuration",16,25,.65)
        text(canvas,'RGB input (full field)',16,60);text(canvas,'GT green / Prediction orange | task detail',655,60)
        dt=prediction['translation_mm'][i];dr=prediction['rotation_deg'][i];tip=float(prediction['tip_in_socket_error_mm'][i])
        text(canvas,f'Module {dt[0]:.2f} mm / {dr[0]:.2f} deg   Socket {dt[1]:.2f} mm / {dr[1]:.2f} deg',16,550,.6)
        text(canvas,f'Tip relative to socket: {tip:.2f} mm   |   Simulation only',16,584,.62)
        cv2.imwrite(str(out/'frames'/f'{frame_id:06d}_comparison.jpg'),canvas,[cv2.IMWRITE_JPEG_QUALITY,94]);cv2.imwrite(str(out/'frames'/f'{frame_id:06d}_detail.jpg'),detail,[cv2.IMWRITE_JPEG_QUALITY,94]);cv2.imwrite(str(out/'frames'/f'{frame_id:06d}_raw_detail.jpg'),raw_detail,[cv2.IMWRITE_JPEG_QUALITY,94])
        row={'id':int(frame_id),'episode':r['episode'],'frame':r['frame'],'image':'data/'+r['image'],'comparison':f'results/frames/{frame_id:06d}_comparison.jpg','detail':f'results/frames/{frame_id:06d}_detail.jpg',
             'raw_detail':f'results/frames/{frame_id:06d}_raw_detail.jpg','pred':Ts.tolist(),'gt':gt.tolist(),'translation_mm':dt.tolist(),'rotation_deg':dr.tolist(),'relative_tip_error_mm':tip}
        rows.append(row)
    episodes=sorted(set(r['episode'] for r in rows));means={e:np.mean([r['relative_tip_error_mm'] for r in rows if r['episode']==e]) for e in episodes}
    worst=max(means,key=means.get);median=sorted(means,key=means.get)[len(means)//2];chosen=list(dict.fromkeys(episodes[:4]+[median,worst]))
    video_frames=[cv2.imread(str(root/r['comparison'])) for e in chosen for r in rows if r['episode']==e]
    fps=json.loads((root/'data/config.json').read_text())['fps'];video(out/'heldout_predictions.mp4',video_frames,fps)
    # Save complete metric clouds for one ordinary and the worst configuration.
    clouds={}
    for label,e in [('first',episodes[0]),('worst',worst)]:
        row=next(r for r in rows if r['episode']==e and r['frame']==6)
        for j,name in enumerate(['module','socket']):
            points=templates[name]['points_m']
            for key in ['pred','gt']:
                T=np.array(row[key][j]);clouds[f'{label}_{name}_{key}_points_m']=points@T[:3,:3].T+T[:3,3]
        clouds[label+'_frame_id']=np.array(row['id'])
    np.savez_compressed(out/'complete_cloud_examples.npz',**clouds)
    history=json.loads((training/'history.json').read_text());fig,axs=plt.subplots(1,3,figsize=(15,4))
    for name in ['module','socket']:
        axs[0].plot([r['epoch'] for r in history],[r['validation']['network'][name]['translation_mm']['mean'] for r in history],label=name)
        axs[1].plot([r['epoch'] for r in history],[r['validation']['network'][name]['rotation_deg']['mean'] for r in history],label=name)
    axs[2].plot([r['epoch'] for r in history],[r['validation']['network']['relative_tip_error_mm']['mean'] for r in history],label='network')
    axs[2].axhline(history[0]['validation']['constant_train_mean']['relative_tip_error_mm']['mean'],color='gray',ls='--',label='constant mean')
    for ax,title in zip(axs,['Validation translation (mm)','Validation rotation (deg)','Validation relative tip (mm)']):ax.set_title(title);ax.set_xlabel('epoch');ax.grid(alpha=.25);ax.legend()
    fig.tight_layout();fig.savefig(out/'learning_curves.png',dpi=160);plt.close(fig)
    sample_indices=[0,len(rows)//4,len(rows)//2,int(np.argmax(prediction['tip_in_socket_error_mm']))];cells=[cv2.imread(str(root/rows[i]['comparison'])) for i in sample_indices];cv2.imwrite(str(out/'test_contact_sheet.jpg'),np.vstack([cv2.resize(c,(960,465)) for c in cells]))
    episodes_meta=[e for e in json.loads((root/'data/episodes.json').read_text()) if e['split']=='train']
    parameters=np.array([e['grasp_translation_mm']+[e['grasp_rpy_deg'][0]] for e in episodes_meta]);chosen_variations=[]
    for axis in [1,2,3]:chosen_variations.extend([int(parameters[:,axis].argmin()),int(parameters[:,axis].argmax())])
    tiles=[]
    for i in chosen_variations:
        e=episodes_meta[i];frame=e['frames']//2;im=cv2.imread(str(root/'data/episodes'/e['episode']/f'{frame:04d}.jpg'))
        tile=np.full((530,600,3),24,np.uint8);tile[50:]=cv2.resize(im[y0:y1,x0:x1],(600,480))
        text(tile,f"{e['episode']} dY={e['grasp_translation_mm'][1]:+.2f}mm dZ={e['grasp_translation_mm'][2]:+.2f}mm",12,20,.5)
        text(tile,f"Pitch about module X: {e['grasp_rpy_deg'][0]:+.2f} deg",12,42,.5);tiles.append(tile)
    cv2.imwrite(str(out/'grasp_variations.jpg'),np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])]))
    payload['frames']=rows;payload['selected_video_episodes']=chosen;payload['worst_episode']=worst;payload['episode_mean_relative_tip_mm']=means
    html=Path(__file__).with_name('sim_surface_results.html').read_text().replace('__PAYLOAD__',json.dumps(payload,separators=(',',':')))
    (root/'index.html').write_text(html);(out/'visualization_manifest.json').write_text(json.dumps({'frames':len(rows),'video_episodes':chosen,'selection':'first four held-out episodes plus median and worst by relative-tip error; no best-only selection','full_cloud_examples':str(out/'complete_cloud_examples.npz'),'physical_accuracy_validated':False},indent=2))
    from render_sim_color_compare import build as build_color_comparison
    build_color_comparison(root,out/'color_compare_v2')
    print(json.dumps({'video':str(out/'heldout_predictions.mp4'),'frames':len(rows),'worst_episode':worst}),flush=True)


if __name__=='__main__':main()
