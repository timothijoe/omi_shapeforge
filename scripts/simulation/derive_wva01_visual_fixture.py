"""Use current WVA-01 visuals in the validated fixed-grasp insertion contract.

GC-r01 supplies the settled reference pose, not a claim of a successful PhysX
free-grasp port. That experimental packet and its failed motion tests are retained.
"""
import argparse
from copy import deepcopy
import hashlib,json,shutil,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from omi_shapeforge.sim.isaac_contact_kinematics import local_pose


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    packet=json.loads((a.source/'transfer.json').read_text());manifest=packet['manifest']
    assert manifest['wrist_tool_asset']=='WG-DAIMON-LOGO-r15'
    assert manifest['module_visual_asset']['asset_id']=='OM-001/V4 r08'
    manifest['experimental_free_grasp_contract']=deepcopy(manifest.pop('grasp_contract'))
    manifest['experimental_free_grasp_contract']['validation_status']='hold/release only; motion failed; not used by this fixture'
    held=np.eye(4);held[:3,:3]=manifest['tool_to_module']['rotation'];held[:3,3]=manifest['tool_to_module']['position_m']
    bodies=packet['bodies'];tcp=next(b for b in bodies if b['name']=='TCP_Link_L');module=next(b for b in bodies if b['name']=='sim_module')
    module.update(parent=tcp['id'],position=held[:3,3].tolist(),quaternion=np.roll(Rotation.from_matrix(held[:3,:3]).as_quat(),1).tolist())
    zero_tcp=np.eye(4);zero_tcp[:3,:3]=tcp['world_rotation'];zero_tcp[:3,3]=tcp['world_position']
    zero_module=zero_tcp@held
    module.update(world_position=zero_module[:3,3].tolist(),world_rotation=zero_module[:3,:3].tolist(),gravcomp=1.)
    for b in bodies:
        if b['parent']==module['id']:
            T=zero_module@local_pose(b);b.update(world_position=T[:3,3].tolist(),world_rotation=T[:3,:3].tolist())
    packet['free_bodies']=[]
    for g in packet['geoms']:
        if g['name'].startswith('grasp_pad_') or g.get('collision_role')=='grasp_rear':g['contact']=False
    manifest.update(asset_contract='wva01-closed-reference-fixture-v1',
        integration_release='SC-WVA01-ISAAC-FIXTURE-r01',
        grasp='fixed module insertion fixture using GC-r01 settled reference pose; NOT free contact grasp',
        grasp_reference=dict(source_release='GC-r01',state='gravity_hold',scope='closed pose reference only'),
        wrist_tool_collision_enabled=False,contact_grasp_validated=False,
        scope='current WVA-01 visual geometry/UV plus GC closed reference; validated fixed-grasp insertion task')
    packet['limitations']=['Module is fixed to TCP; this film does not validate contact-mediated grasp',
        'Free-grasp PhysX candidate and failed motion checks are retained separately',
        'Robot inertia/friction/camera calibration are not real-hardware certifications',
        'Socket uses the existing staged smooth-guide contact assumption; no electrical/latch model']
    shutil.copy2(a.source/'meshes.npz',a.output/'meshes.npz')
    assert hashlib.sha256((a.output/'meshes.npz').read_bytes()).hexdigest()==packet['meshes_sha256']
    (a.output/'transfer.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2))
    audit=json.loads((a.source/'asset_audit.json').read_text());audit.update(
        selected_contract=manifest['asset_contract'],integration_release=manifest['integration_release'],
        grasp_updated='GC-r01 gravity_hold reference pose; fixed insertion fixture, not free grasp',
        fixed_module_attachment_removed=False,free_grasp_motion_validation=False,
        experimental_free_grasp_source=str(a.source),source_visual_meshes_unchanged=True)
    (a.output/'asset_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    print(json.dumps({'transfer':str(a.output),'contract':manifest['asset_contract'],'tool':manifest['wrist_tool_asset'],'free_grasp_used':False},ensure_ascii=False))


if __name__=='__main__':main()
