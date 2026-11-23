"""Mount the pinned WG-r10/OM-r08 bundle in a new robot scene; audit static paths."""
import argparse
import hashlib
import json
from pathlib import Path

import mujoco
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

from omi_shapeforge.sim.wrist_tool_scene import build


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--bundle',type=Path,default=Path('manifests/wrist_visual_asset_handoff_20261122.json'))
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    bundle=json.loads(a.bundle.read_text());kit=json.loads((a.inputs/'tool/asset_manifest.json').read_text())
    for label in ('tool','module'):
        item=bundle['assets'][label];copy=a.inputs/label
        for name in ('manifest','delivery_manifest'):
            assert hashlib.sha256((copy/Path(item[name]).name).read_bytes()).hexdigest()==item[name+'_sha256']
        for rel,digest in json.loads((copy/'delivery_manifest.json').read_text())['files'].items():
            assert hashlib.sha256((copy/rel).read_bytes()).hexdigest()==digest,rel
    original=json.loads((a.source/'robot_manifest.json').read_text())
    m=mujoco.MjModel.from_xml_path(str(a.source/'scene.xml'));d=mujoco.MjData(m)
    d.qpos[:]=original['initial_qpos']
    for name in ('Arm_L10_Joint','Arm_L11_Joint'):d.joint(name).qpos[0]=kit['integration_joint_reference_qpos_m']
    joints=[m.joint(f'Arm_L{i}_Joint').id for i in range(1,8)];qids=m.jnt_qposadr[joints]
    tcp=m.body('TCP_Link_L').id;Rs=np.asarray(original['socket_to_world']['rotation']);ps=np.asarray(original['socket_to_world']['position_m'])
    Rtm=np.asarray(kit['tool_to_module']['rotation']);ptm=np.asarray(kit['tool_to_module']['position_m'])
    nominal=np.asarray(original['nominal_module_center_xz_mm'])/1000
    target_R=Rs@Rtm.T
    def target(depth):
        pm=ps+Rs@np.array([nominal[0],(original['mouth_y_mm']-original['leading_tip_y_mm']-depth)/1000,nominal[1]])
        return pm-target_R@ptm
    def residual(q,depth):
        d.qpos[qids]=q;mujoco.mj_forward(m,d)
        return np.r_[d.xpos[tcp]-target(depth),Rotation.from_matrix(target_R@d.xmat[tcp].reshape(3,3).T).as_rotvec()*.1]
    lower,upper=m.jnt_range[joints].T
    starts=[np.array(original['initial_qpos'])[qids]]
    rng=np.random.default_rng(2210)
    starts += [np.clip(starts[0]+rng.normal(0,.5,7),lower+1e-5,upper-1e-5) for _ in range(8)]
    best=None
    for start in starts:
        sol=least_squares(residual,start,args=(-5.,),bounds=(lower+1e-6,upper-1e-6),diff_step=1e-5,xtol=1e-12,ftol=1e-12,gtol=1e-12,max_nfev=500)
        error=residual(sol.x,-5.)
        if best is None or np.linalg.norm(error)<best[0]:best=(np.linalg.norm(error),sol.x.copy(),error.copy())
        if np.linalg.norm(error[:3])<1e-7 and np.linalg.norm(error[3:])<1e-7:break
    _,q,error=best
    solution=dict(left_arm_qpos=q.tolist(),position_error_mm=float(np.linalg.norm(error[:3])*1000),
        angle_error_rad=float(np.linalg.norm(error[3:])/.1),tool_to_module=kit['tool_to_module'],
        preinsert_tcp_position=target(-5.).tolist(),goal_tcp_rotation=target_R.tolist(),
        bundle_id=bundle['bundle_id'],bundle_sha256=hashlib.sha256(a.bundle.read_bytes()).hexdigest())
    (a.output/'mount_solution.json').write_text(json.dumps(solution,indent=2)+'\n')
    if solution['position_error_mm']>.01 or solution['angle_error_rad']>.0001:raise RuntimeError('No accurate new mounting solution')
    result=build(a.source,a.inputs/'tool',a.output/'mount_solution.json',a.output/'robot_scene',a.inputs/'module')
    # Follow the nominal insertion corridor by IK only. This is a static audit,
    # not a dynamically executed insertion or physical grasp validation.
    path=[]
    for depth in np.linspace(-5.,original['shoulder_depth_mm'],22):
        sol=least_squares(residual,q,args=(depth,),bounds=(lower+1e-6,upper-1e-6),xtol=1e-11,ftol=1e-11,gtol=1e-11,max_nfev=180)
        q=sol.x;err=residual(q,depth)
        path.append(dict(depth_mm=float(depth),left_arm_qpos=q.tolist(),position_error_mm=float(np.linalg.norm(err[:3])*1000),rotation_error_rad=float(np.linalg.norm(err[3:])/.1)))
    (a.output/'ik_path.json').write_text(json.dumps(path,indent=2)+'\n')
    (a.output/'integration.json').write_text(json.dumps(dict(bundle_id=bundle['bundle_id'],scene=result['scene'],
        mount=solution,tool_parts=len(result['wrist_tool_bindings']),module_visual_parts=17,
        physical_grasp_validated=False,robot_contact_path_validated=False,training_validated=False),indent=2)+'\n')
    print(json.dumps(solution),flush=True)


if __name__=='__main__':main()
