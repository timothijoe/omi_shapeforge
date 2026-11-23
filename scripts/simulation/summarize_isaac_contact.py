"""Collect the fixed local/robot qualification matrix without inferring missing passes."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def summarize(root):
    root=Path(root).resolve()
    cases=[('local',n) for n in ['normal','half_step','locked','x_plus','x_minus','yaw_plus','yaw_minus']]
    cases += [('robot',n) for n in ['robot_video','robot_19','robot_41']]
    rows=[]
    for kind,name in cases:
        folder=root/f'pgs_{kind}'/name;path=folder/'report.json'
        suite_path=folder.parent/'suite.json'
        executions=json.loads(suite_path.read_text()).get('cases',[]) if suite_path.exists() else []
        execution=next((x for x in executions if x['case']==name),{})
        row=dict(group=kind,case=name,report=str(path),completed=path.exists(),accepted=False)
        row['execution_returncode']=execution.get('returncode')
        row['timed_out']=execution.get('timed_out')
        if path.exists():
            r=json.loads(path.read_text());trajectory=json.loads((folder/'trajectory.json').read_text())
            row.update(accepted=bool(execution.get('returncode')==0 and not execution.get('timed_out',True) and r.get('accepted') and r.get('solver')=='PGS' and r.get('asset_id')=='SIM-OM001-OS001-r06'),solver=r.get('solver'),dt=r['dt'],seed=r['seed'],
                phases=r['phases'],report_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                max_penetration_mm=max(x.get('step_peak_penetration_mm',x.get('peak_penetration_mm',0.)) for x in trajectory),
                max_sampled_contact_force_N=max(x['contact_force_N'] for x in trajectory),
                max_substep_contact_force_N=max(x.get('step_peak_contact_force_N',0.) for x in trajectory),
                renderer_executed=r['renderer_executed'])
            if kind=='robot':
                row['min_floor_gap_mm']=min(x['step_min_floor_gap_mm'] for x in trajectory)
                row['learner_10N_force_gate_passed']=row['max_sampled_contact_force_N']<=10.
            if r['renderer_executed']:
                row.update(camera_frames=len(r['camera_checks']),video=str(folder/'cycle.mp4'),preview=str(folder/'preview.png'))
        rows.append(row)
    def test_summary(path):
        if not path.exists():return dict(status='not_evaluated',log=str(path))
        text=path.read_text();count=re.search(r'Ran (\d+) test',text);skipped=re.search(r'OK \(skipped=(\d+)\)',text)
        passed=bool(re.search(r'^OK(?: \(skipped=\d+\))?$',text,re.M))
        total=int(count[1]) if count else 0;skip=int(skipped[1]) if skipped else 0
        return dict(status='passed' if passed and total>0 else 'failed',executed=total-skip,skipped=skip,log=str(path))
    return dict(schema_version=1,experiment='ISAAC-SIM-r06-PGS-v1',checked_date='2026-11-22',
        acceptance_scope='MuJoCo source rule-cycle criteria and local obstacle checks; excludes the learning-evaluation 10N stop gate',
        source_asset='SIM-OM001-OS001-r06',run_root=str(root),cases=rows,
        completed_cases=sum(x['completed'] for x in rows),expected_cases=len(cases),
        all_required_passed=bool(len(rows)==10 and all(x['completed'] and x['accepted'] for x in rows)),
        viewer_asset=str(root/'review_assets/ISAAC-SIM-r06-PGS-initial.usdc'),
        source_protection=json.loads((root/'source_protection.json').read_text()),
        tests=dict(control=test_summary(root/'final_control_tests.log'),independent_fk=test_summary(root/'final_transfer_tests.log')),
        physical_accuracy_validated=False,training_executed=False,gui_interaction_validated=False,
        limitations=['Fixed module attachment; physical grasp and robot self-contact unvalidated',
            'Robot rule cycles do not apply the learner 10N force gate; some control samples exceed it',
            'RGBA materials and legacy pinhole cameras; no WG-r08/fisheye integration',
            'PhysX cooking still approximates some curved colliders; see full cooking audit',
            'Rule-based trials only; no Isaac BC/SAC learning result',
            'Initial offsets are small; no broad robustness or real-robot validation'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=summarize(a.root);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(completed=result['completed_cases'],expected=result['expected_cases'],all_required_passed=result['all_required_passed'])))
