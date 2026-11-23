"""Publish a stricter task-prior subset; preserve the complete physical catalog."""
import argparse,json
from pathlib import Path
from collections import Counter
from generate_sim_wrist_dataset import sha
LIMITS={'fore_aft_error_mm':.1,'height_error_mm':.1,'pitch_error_deg':.25,'lateral_center_mm':.02,'non_pitch_rotation_deg':.05}
def violations(row):
 a=row['actual_module'];q=row['requested_module'];values={'fore_aft_error_mm':abs(a['fore_aft_mm']-q['fore_aft_mm']),'height_error_mm':abs(a['height_mm']-q['height_mm']),'pitch_error_deg':abs(a['pitch_deg']-q['pitch_deg']),'lateral_center_mm':abs(a['lateral_center_mm']),'non_pitch_rotation_deg':a['non_pitch_rotation_deg']};return [k for k,v in values.items() if v>LIMITS[k]]
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();r=a.run;data=r/'data';out=r/'data_strict';out.mkdir(exist_ok=False);rows=list(map(json.loads,(data/'records.jsonl').read_text().splitlines()));accepted=[];aux=[];counts=Counter()
 for row in rows:
  bad=violations(row)
  if bad:aux.append({'sample_id':row['sample_id'],'grasp_id':row['grasp_id'],'violations':bad,'actual_module':row['actual_module'],'requested_module':row['requested_module']});counts.update(bad)
  else:accepted.append(row)
 (out/'shards').symlink_to(r/'shards',target_is_directory=True)
 for name in ['scene.xml','physics_scene.xml','calibration.json','dependencies.json','grasps.json','grasp_sources.json']:(out/name).symlink_to(data/name)
 (out/'records.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in accepted));(out/'excluded_from_strict.json').write_text(json.dumps(aux,indent=2))
 cfg=json.loads((data/'config.json').read_text());cfg['task_prior_quality_gate']=LIMITS;cfg['physical_parent_dataset']=str(data);cfg['phase']='pre-insertion only';(out/'config.json').write_text(json.dumps(cfg,indent=2))
 report={'physical_parent_images':len(rows),'strict_images':len(accepted),'auxiliary_only_images':len(aux),'limits':LIMITS,'violation_counts_not_mutually_exclusive':dict(counts),'strict_grasp_groups':len({x['grasp_id'] for x in accepted}),'split_images':{s:sum(x['split']==s for x in accepted) for s in ['train','val','test']},'accepted_for_sim_supervision':True,'physical_validation_inherited_from':str(data/'label_audit.json'),'physical_validation_sha256':sha(data/'label_audit.json'),'parent_records_sha256':sha(data/'records.jsonl'),'strict_records_sha256':sha(out/'records.jsonl'),'parent_unmodified':True,'training_performed':False,'notes':'Working task-prior quality thresholds, not real metrology or neural accuracy. Parent retains valid but off-prior physical states for inspection.'}
 (out/'complete.json').write_text(json.dumps(report,indent=2));(out/'label_audit.json').write_text(json.dumps(report,indent=2));(r/'strict_subset_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
