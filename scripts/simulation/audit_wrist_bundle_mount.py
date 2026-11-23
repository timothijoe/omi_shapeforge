"""Static surface clearance, component binding and camera checks for a new mount."""
import argparse,json
from pathlib import Path
import mujoco
import numpy as np
import trimesh


def pose(position,rotation):
    t=np.eye(4);t[:3,:3]=rotation;t[:3,3]=position;return t


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--integration',type=Path,required=True)
    a=p.parse_args();root=a.integration;directory=root/'robot_scene'
    manifest=json.loads((directory/'robot_manifest.json').read_text());m=mujoco.MjModel.from_xml_path(str(directory/'scene.xml'));d=mujoco.MjData(m)
    d.qpos[:]=manifest['initial_qpos'];mujoco.mj_forward(m,d)
    tool=[i for i in range(m.ngeom) if m.geom(i).name.startswith('wrist_tool_')]
    socket=[i for i in range(m.ngeom) if m.geom(i).name.startswith('sim_socket_') and m.geom_group[i]<3]
    module=[i for i in range(m.ngeom) if m.geom(i).name.startswith('sim_module_') and m.geom_group[i]<3]
    assert len(tool)==49 and len(module)==17
    def manager(ids):
        cm=trimesh.collision.CollisionManager()
        for i in ids:
            k=m.geom_dataid[i];va,vn=m.mesh_vertadr[k],m.mesh_vertnum[k];fa,fn=m.mesh_faceadr[k],m.mesh_facenum[k]
            mesh=trimesh.Trimesh(m.mesh_vert[va:va+vn],m.mesh_face[fa:fa+fn],process=False)
            cm.add_object(m.geom(i).name,mesh,transform=pose(d.geom_xpos[i],d.geom_xmat[i].reshape(3,3)))
        return cm
    tc,sc,mc=manager(tool),manager(socket),manager(module)
    def update(cm,ids):
        for i in ids:cm.set_transform(m.geom(i).name,pose(d.geom_xpos[i],d.geom_xmat[i].reshape(3,3)))
    initial_collision,initial_pairs=tc.in_collision_other(mc,return_names=True)
    initial_gap=float(tc.min_distance_other(mc)*1000)
    camera=m.camera('wrist_rgb').id;tcp=m.body('TCP_Link_L').id
    Twt=pose(d.xpos[tcp],d.xmat[tcp].reshape(3,3));Twc=pose(d.cam_xpos[camera],d.cam_xmat[camera].reshape(3,3))
    camera_relative=np.linalg.inv(Twt)@Twc
    jaw_tests=[]
    for name,body,desired_sign in [('Arm_L10_Joint','Arm_L10_Link',-1),('Arm_L11_Joint','Arm_L11_Link',1)]:
        qref=float(d.joint(name).qpos[0]);before=d.xpos[m.body(body).id].copy()
        d.joint(name).qpos[0]=qref+.001;mujoco.mj_forward(m,d)
        axis=Twt[:3,:3].T@(d.xpos[m.body(body).id]-before)/.001
        sign=float(np.sign(axis[1])*desired_sign);qopen=qref+sign*.012
        assert m.joint(name).range[0]<=qopen<=m.joint(name).range[1]
        d.joint(name).qpos[0]=qopen;mujoco.mj_forward(m,d)
        moved=Twt[:3,:3].T@(d.xpos[m.body(body).id]-before)
        newcam=pose(d.cam_xpos[camera],d.cam_xmat[camera].reshape(3,3))
        assert np.max(np.abs(newcam-Twc))<1e-10
        jaw_tests.append(dict(joint=name,reference_qpos_m=qref,open_qpos_m=qopen,
            requested_extra_opening_mm=12.,actual_displacement_tcp_mm=(moved*1000).tolist(),camera_unchanged=True))
        d.joint(name).qpos[0]=qref;mujoco.mj_forward(m,d)
    rows=[]
    for state in json.loads((root/'ik_path.json').read_text()):
        for i,q in enumerate(state['left_arm_qpos'],1):d.joint(f'Arm_L{i}_Joint').qpos[0]=q
        mujoco.mj_forward(m,d);update(tc,tool)
        hit,pairs=tc.in_collision_other(sc,return_names=True)
        rows.append(dict(depth_mm=state['depth_mm'],tool_socket_surface_intersection=bool(hit),
            minimum_surface_distance_mm=float(tc.min_distance_other(sc)*1000),pairs=[list(p) for p in sorted(pairs)]))
    result=dict(tool_parts=len(tool),module_parts=len(module),socket_visual_parts=len(socket),
        preinsert_tool_module_intersection=bool(initial_collision),preinsert_tool_module_gap_mm=initial_gap,
        preinsert_pairs=[list(p) for p in sorted(initial_pairs)],camera_tcp_gl=camera_relative.tolist(),jaw_tests=jaw_tests,
        path_samples=rows,all_sampled_tool_socket_clear=all(not x['tool_socket_surface_intersection'] for x in rows),
        limitations=['Static IK samples only, not continuous collision or dynamics validation',
                    'Tool collision disabled, inherited URDF inertia; no physical grasp',
                    'New handle visual-only; robot arm self/contact with table not fully audited'])
    (root/'mount_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['path_samples','camera_tcp_gl']}),flush=True)


if __name__=='__main__':main()
