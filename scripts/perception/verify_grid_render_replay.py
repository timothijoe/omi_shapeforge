"""Independently re-render representative saved states and reproduce labels."""
import argparse,json,os,io
from pathlib import Path
os.environ.setdefault('MUJOCO_GL','egl')
import numpy as np,mujoco
from PIL import Image
from generate_contact_wrist_dataset import ContactRenderer
from generate_sim_wrist_dataset import read,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();root=a.run;data=root/'data';rows=list(map(json.loads,(data/'records.jsonl').read_text().splitlines()));chosen={}
 for family in sorted({f for row in rows for f in row['coverage_families']}):
  subset=[x for x in rows if family in x['coverage_families']]
  for i in [0,len(subset)//2,len(subset)-1]:chosen[subset[i]['sample_id']]=subset[i]
 for key in ['fore_aft_mm','height_mm','pitch_deg']:
  for pick in [min,max]:
   row=pick(rows,key=lambda x:x['requested_module'][key]);chosen[row['sample_id']]=row
 r=ContactRenderer(data/'scene.xml',read(data/'calibration.json'),672);r.m.opt.disableflags|=int(mujoco.mjtDisableBit.mjDSBL_CONTACT);reports=[]
 for row in chosen.values():
  state=np.load(data/row['state']);rng=np.random.default_rng(np.random.SeedSequence([20261123,row['sample_id']]));r.reset(np.array(row['T_world_from_tcp']),np.array(row['T_tcp_from_module']),rng);r.robot_pose(state['robot_qpos'])
  for key in ['qpos','qvel','mocap_pos','mocap_quat','ctrl']:getattr(r.d,key)[:]=state[key]
  mujoco.mj_forward(r.m,r.d);rgb,seg=r.render(segmentation=True);mask=np.zeros(seg.shape,np.uint8);mask[np.isin(seg,r.module_geoms)]=1;mask[np.isin(seg,r.socket_geoms)]=2;original_mask=np.array(Image.open(data/row['instance_mask']));mask_diff=int(np.count_nonzero(mask!=original_mask))
  b=io.BytesIO();Image.fromarray(rgb).save(b,format='JPEG',quality=95,subsampling=0);b.seek(0);reencoded=np.array(Image.open(b)).astype(float);original=np.array(Image.open(data/row['image'])).astype(float);mae=float(np.mean(abs(reencoded-original)));maximum=float(np.max(abs(reencoded-original)))
  changed=float(np.mean(np.any(reencoded!=original,axis=2)))
  reports.append({'sample_id':row['sample_id'],'families':row['coverage_families'],'mask_mismatch_pixels':mask_diff,'decoded_rgb_mae':mae,'decoded_rgb_max_difference':maximum,'changed_rgb_pixel_fraction':changed})
 r.close();report={'selected_states':reports,'all_masks_exact':all(x['mask_mismatch_pixels']==0 for x in reports),'all_RGB_exact':all(x['decoded_rgb_max_difference']==0 for x in reports),'max_RGB_MAE':max(x['decoded_rgb_mae'] for x in reports),'max_changed_pixel_fraction':max(x['changed_rgb_pixel_fraction'] for x in reports),'scope':'Independent state replay; report photometric differences separately from geometry mask agreement'};(root/'render_replay_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
