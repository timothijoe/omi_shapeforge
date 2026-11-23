"""New task contract on unchanged smooth-guide geometry; originals preserved."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'omi_proj/src'))
from omi_hil_rl.hil.insertion_task import InsertionAssessmentConfig


def build(source, output):
    source,output=Path(source).resolve(),Path(output).resolve()
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    hashes={str(source/n):digest(source/n) for n in ('transfer.json','meshes.npz')}
    packet=json.loads((source/'transfer.json').read_text())
    if not any(j['name']=='Arm_L1_Joint' for j in packet['joints']):
        raise ValueError('staged task wiring requires a robot transfer; local legacy proxy suites remain separate')
    original_geoms=json.dumps(packet['geoms'],sort_keys=True)
    config=asdict(InsertionAssessmentConfig())
    packet['manifest']['insertion_assessment']=config
    packet['manifest']['task_contract_id']='entry-strict-interior-tolerant-v1'
    packet['manifest']['staged_contract_provenance']=dict(parent_transfer=str(source),
        geometry_changed=False,friction_changed=False,collisions_always_enabled=True,
        thresholds_calibrated_on_real_hardware=False,old_results_relabelled=False,
        user_requirement='strict entrance qualification; tolerate minor interior contact; recover by retreat and realignment')
    assert original_geoms==json.dumps(packet['geoms'],sort_keys=True)
    output.mkdir(parents=True,exist_ok=False)
    shutil.copy2(source/'meshes.npz',output/'meshes.npz')
    assert digest(output/'meshes.npz')==packet['meshes_sha256']
    (output/'transfer.json').write_text(json.dumps(packet,indent=2)+'\n')
    assert all(digest(Path(p))==s for p,s in hashes.items())
    report=dict(source_sha256=hashes,source_unchanged=True,geometry_changed=False,
        friction_changed=False,config=config,transfer_sha256=digest(output/'transfer.json'))
    (output/'candidate.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.source,args.output),indent=2))
