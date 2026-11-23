"""Freeze evaluated MuJoCo geometry/kinematics for a separate PhysX experiment.

Run with omi_sim_train. This exports data only; Isaac never advances MuJoCo.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


def export(source, output, manifest_path=None):
    source, output = Path(source).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    m = mujoco.MjModel.from_xml_path(str(source))
    d = mujoco.MjData(m)
    mujoco.mj_forward(m, d)
    def pose(p, q):
        return dict(position=np.asarray(p).tolist(), quaternion=np.asarray(q).tolist())
    bodies = []
    for i in range(m.nbody):
        bodies.append(dict(id=i, name=m.body(i).name, parent=int(m.body_parentid[i]),
            **pose(m.body_pos[i], m.body_quat[i]), mass=float(m.body_mass[i]),
            inertia=m.body_inertia[i].tolist(), com=m.body_ipos[i].tolist(),
            inertia_quaternion=m.body_iquat[i].tolist(), gravcomp=float(m.body_gravcomp[i]),
            world_position=d.xpos[i].tolist(), world_rotation=d.xmat[i].reshape(3,3).tolist()))
    joints=[]
    for j in range(m.njnt):
        if m.jnt_type[j] not in (2,3):
            raise ValueError('Only scalar slide/hinge joints supported')
        a=np.flatnonzero(m.actuator_trnid[:,0] == j)
        kp=float(m.jnt_stiffness[j]);kd=float(m.dof_damping[m.jnt_dofadr[j]])
        force=1e6
        if len(a):
            a=int(a[0]);kp+=float(m.actuator_gainprm[a,0]);kd+=float(-m.actuator_biasprm[a,2])
            if m.actuator_forcelimited[a]:force=float(max(abs(m.actuator_forcerange[a])))
        joints.append(dict(name=m.joint(j).name,body=int(m.jnt_bodyid[j]),kind=int(m.jnt_type[j]),
            axis=m.jnt_axis[j].tolist(),position=m.jnt_pos[j].tolist(),limited=bool(m.jnt_limited[j]),
            limits=m.jnt_range[j].tolist(),kp=kp,kd=kd,max_force=force,qpos_index=int(m.jnt_qposadr[j])))
    arrays={};geoms=[]
    for g in range(m.ngeom):
        mesh=int(m.geom_dataid[g]) if m.geom_type[g]==7 else -1
        if mesh>=0 and f'v{mesh}' not in arrays:
            va,vn=m.mesh_vertadr[mesh],m.mesh_vertnum[mesh]
            fa,fn=m.mesh_faceadr[mesh],m.mesh_facenum[mesh]
            arrays[f'v{mesh}']=m.mesh_vert[va:va+vn].copy()
            arrays[f'f{mesh}']=m.mesh_face[fa:fa+fn].copy()
            na,nn=m.mesh_normaladr[mesh],m.mesh_normalnum[mesh]
            normal_indices=m.mesh_facenormal[fa:fa+fn].copy()
            if nn and normal_indices.min()>=0 and normal_indices.max()<nn:
                arrays[f'n{mesh}']=m.mesh_normal[na:na+nn].copy()
                arrays[f'fn{mesh}']=normal_indices
        geoms.append(dict(name=m.geom(g).name or f'geom_{g}',body=int(m.geom_bodyid[g]),
            kind=int(m.geom_type[g]),mesh=mesh,size=m.geom_size[g].tolist(),
            **pose(m.geom_pos[g],m.geom_quat[g]),rgba=m.geom_rgba[g].tolist(),
            contact=bool(m.geom_contype[g] or m.geom_conaffinity[g]),group=int(m.geom_group[g]),
            friction=m.geom_friction[g].tolist()))
    cameras=[dict(name=m.camera(c).name,body=int(m.cam_bodyid[c]),
        **pose(m.cam_pos[c],m.cam_quat[c]),fovy=float(m.cam_fovy[c])) for c in range(m.ncam)]
    sites=[dict(name=m.site(s).name,body=int(m.site_bodyid[s]),**pose(m.site_pos[s],m.site_quat[s])) for s in range(m.nsite)]
    source_manifest=json.loads(Path(manifest_path).read_text()) if manifest_path else {}
    dependencies={str(source):hashlib.sha256(source.read_bytes()).hexdigest()}
    # The chosen scene has explicit file references; preserve their identities.
    for element in ET.parse(source).getroot().findall('asset/mesh'):
        path=Path(element.get('file'))
        if not path.is_absolute():path=source.parent/path
        dependencies[str(path.resolve())]=hashlib.sha256(path.read_bytes()).hexdigest()
    packet=dict(version=1,source=str(source),mujoco_version=mujoco.__version__,units='m',up_axis='Z',
        bodies=bodies,joints=joints,geoms=geoms,cameras=cameras,sites=sites,
        initial_qpos=source_manifest.get('initial_qpos',m.qpos0.tolist()),manifest=source_manifest,
        dependencies_sha256=dependencies,
        limitations=['MuJoCo contact solref/solimp have no direct PhysX equivalent',
                    'Joint mimic relations are not ported; fingers are held at fixed opening',
                    'Visual material is RGBA approximation; textures not transferred'])
    np.savez_compressed(output/'meshes.npz',**arrays)
    packet['meshes_sha256']=hashlib.sha256((output/'meshes.npz').read_bytes()).hexdigest()
    (output/'transfer.json').write_text(json.dumps(packet,indent=2)+'\n')
    print(json.dumps(dict(output=str(output),bodies=len(bodies),joints=len(joints),geoms=len(geoms))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--manifest',type=Path)
    a=p.parse_args();export(a.source,a.output,a.manifest)
