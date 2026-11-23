"""Same images and same geometric template, frozen-old vs contact-finetuned poses."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from render_surface_scheme_results import projected_samples,paint
from render_sim_surface_results import text,video

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;out=r/'transfer_evaluation/visual';out.mkdir(exist_ok=False)
 html=(r/'index.html').read_text();at=html.index('const data=')+len('const data=');data,_=json.JSONDecoder().raw_decode(html[at:]);rows={x['id']:x for x in data['frames']};cfg=json.loads((r/'train/config.json').read_text());cal=cfg['calibration'];K=np.array(cal['K']);D=np.array(cal['D']);W,H=cal['image_width'],cal['image_height'];crop=[int(.32*W),int(.43*H),int(.68*W),int(.98*H)];x0,y0,x1,y1=crop
 base=Path('/data/omi_runtime/runs/regular_surface_schemes_20261122/templates_v2');templates={n:dict(np.load(base/f'{n}_focus.npz')) for n in ['module','socket']};old=np.load(r/'transfer_evaluation/old_frozen_predictions.npz');new=np.load(r/'transfer_evaluation/contact_finetuned_predictions.npz');assert np.array_equal(old['frame_ids'],new['frame_ids']);assert np.allclose(old['gt'],new['gt'])
 frames=[];chosen=data['selected_video_episodes'];used=[]
 for episode in chosen:
  for i,fid in enumerate(new['frame_ids']):
   row=rows[int(fid)]
   if row['episode']!=episode:continue
   raw=cv2.imread(str(r/row['image']));detail=cv2.resize(raw[y0:y1,x0:x1],(640,540));truth=projected_samples(templates,new['gt'][i],K,D,crop)[1];panels=[]
   for pred in [old['pred'][i],new['pred'][i]]:
    points=projected_samples(templates,pred,K,D,crop);im=paint(detail,*points,(20,130,255))
    for u,v,*_ in truth[::3]:cv2.circle(im,(round(u),round(v)),3,(50,255,50),1,cv2.LINE_AA)
    panels.append(im)
   header=np.full((65,1280,3),22,np.uint8);text(header,'Frozen old model | same NEW contact test image',12,25,.6);text(header,'Contact-finetuned model | same image',652,25,.6);text(header,'Orange: predicted tip/mouth | Green rings: ground truth',12,53,.55)
   footer=np.full((45,1280,3),22,np.uint8);text(footer,f"{episode}/{row['frame']:02d}  tip error: {old['tip_in_socket_error_mm'][i]:.2f} mm",12,30,.65);text(footer,f"tip error: {new['tip_in_socket_error_mm'][i]:.2f} mm",652,30,.65)
   frames.append(np.vstack([header,np.hstack(panels),footer]));used.append(int(fid))
 video(out/'old_vs_contact_finetuned.mp4',frames,6);cv2.imwrite(str(out/'first_frame.png'),frames[0]);(out/'manifest.json').write_text(json.dumps({'frame_ids':used,'episodes':chosen,'same_images_and_same_template':True,'point_region':'focus_only_for_readability','predictions_unchanged':True},indent=2))
 anchor='<a href="transfer_evaluation/visual/old_vs_contact_finetuned.mp4" target="_blank">旧模型／本轮：同图对比</a>'
 html=html.replace('<div class="tabs">','<div class="tabs">'+anchor);(r/'index.html').write_text(html)
 print('Compared',len(frames),'frames',flush=True)
if __name__=='__main__':main()
