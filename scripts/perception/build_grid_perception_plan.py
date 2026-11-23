"""Bounded v1 coverage catalog. Only the module 3D grid is fully enumerated.
Socket translation/rotation grids and their interaction strata are explicit.
"""
import argparse,itertools,json,hashlib
from pathlib import Path
import numpy as np

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 module={'fore_aft_mm':np.arange(-3,3.001,.5).tolist(),'height_mm':np.arange(-1,1.001,.25).tolist(),'pitch_deg':np.arange(-4,4.001,.5).tolist()}
 lateral=np.arange(-3,3.001,.5).tolist();near=np.arange(-1,1.001,.25).tolist();gaps=[.5,1,1.5,2,3,4,5,7.5,10,15,20,30,40];angles=list(range(-6,7));modules=[];records=[];seen={};lookup={}
 for i,vals in enumerate(itertools.product(*module.values())):
  gid=f'g{i:04d}';q=dict(zip(module,vals));rank=int(hashlib.sha256(('grid-v1:'+gid).encode()).hexdigest()[:8],16)%10;split='test' if rank==0 else 'val' if rank==1 else 'train';modules.append({'grasp_id':gid,'requested_module':q,'split':split});lookup[vals]=modules[-1]
 def add(g,x,z,gap,rx=0,ry=0,rz=0,family='module_full_grid'):
  key=(g['grasp_id'],x,z,gap,rx,ry,rz)
  if key in seen:records[seen[key]]['coverage_families'].append(family);return
  i=len(records);seen[key]=i;records.append({'sample_id':i,'grasp_id':g['grasp_id'],'split':g['split'],'requested_module':g['requested_module'],'requested_socket_relation':{'lateral_mm':x,'vertical_mm':z,'tip_gap_mm':gap,'rotation_socket_xyz_deg':[rx,ry,rz]},'coverage_families':[family]})
 for i,g in enumerate(modules):
  sign=1 if i%2 else -1
  for view in [(0,0,2,0,0,0),(0,0,10,0,0,0),(0,0,40,0,0,0),(2*sign,-2*sign,5,0,0,0),(-3*sign,3*sign,20,4*sign,0,-4*sign),(0,0,10,-4*sign,4*sign,0)]:add(g,*view)
 zero=lookup[(0.,0.,0.)]
 for x,z,gap in itertools.product(lateral,lateral,gaps):add(zero,x,z,gap,family='socket_full_translation_grid_at_nominal_grasp')
 for x,z,gap in itertools.product(near,near,[.5,1,2]):add(zero,x,z,gap,family='socket_fine_near_mouth_grid_at_nominal_grasp')
 for rx,ry,rz in itertools.product(angles,repeat=3):add(zero,0,0,10,rx,ry,rz,family='socket_full_rotation_grid_at_nominal_grasp')
 # Dense socket families all remain with the nominal grasp's split: no same
 # grasp is split by image. These are training coverage, not broad held-out
 # socket extrapolation evidence. Save an explicit group split limitation.
 manifest={'version':'grid-perception-v1','phase':'pre-insertion only','module_grid':module,'module_grid_complete':True,'module_grasp_groups':len(modules),'module_fixed_constraints':['lateral_center=0','no non-pitch rotation'],'socket_translation':{'lateral_mm':lateral,'vertical_mm':lateral,'tip_gap_mm':gaps},'socket_rotation_xyz_deg':angles,'near_mouth_lateral_and_vertical_mm':near,'candidate_images':len(records),'full_nine_variable_cartesian_product':False,'coverage_description':'Complete 1989 module grid with six deterministic socket views each; complete socket translation and joint-angle grids at nominal grasp; near-mouth local fine grid. Requested cells rejected by physics, mesh collision, IK or visibility remain explicitly recorded.','split_policy':'Entire module grasp ID remains in one split. Dense socket grids only at nominal grasp; this split measures module/general paired-view interpolation, not independent dense-socket generalization.','nominal_grasp_split':zero['split'],'fine_sampling_is_not_claimed_prediction_accuracy':True,'render_resolution':[960,540],'template_contract':'/data/omi_runtime/runs/contact_wrist_surface_20261123_r01/network_templates/manifest.json','label_storage':'shared surface templates plus actual transforms; no duplicated full point clouds per image','visibility_labels':'rendered module/socket instance mask','acceptance':{'module_target_fore_aft_height_tolerance_mm':.1,'module_pitch_tolerance_deg':.5,'lateral_center_tolerance_mm':.1,'non_pitch_rotation_tolerance_deg':.5,'each_pad_force_N':.1,'max_visible_pad_penetration_mm':.05,'minimum_visible_module_pixels':60,'minimum_visible_socket_pixels':100,'reject_module_or_gripper_intersection_with_socket':True},'training_performed':False,'real_world_labels':False}
 (a.output/'plan.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));(a.output/'grasps.json').write_text(json.dumps(modules,indent=2));(a.output/'candidates.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records));print(json.dumps(manifest,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
