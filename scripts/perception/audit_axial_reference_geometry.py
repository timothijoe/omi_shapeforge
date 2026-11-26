"""Discrete visual-mesh intersection audit for candidate approach references."""
import argparse
import json
from pathlib import Path
import numpy as np
import trimesh


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);root=p.parse_args().output
    report=json.loads((root/'axial_reference.json').read_text());source=Path(report['source'])
    scene=json.loads((source/'scene_packet.json').read_text());arrays=np.load(source/'asset_geometry.npz',allow_pickle=False)
    static=trimesh.collision.CollisionManager();moving=trimesh.collision.CollisionManager();names=[];module=[]
    for i,part in enumerate(scene['parts']):
        mesh=trimesh.Trimesh(vertices=arrays[f'v{i}'],faces=arrays[f'f{i}'],process=False)
        if part['category']=='socket':static.add_object(part['name'],mesh)
        else:
            moving.add_object(part['name'],mesh);names.append(part['name'])
            if part['name'].startswith('sim_module_'):module.append(np.array(mesh.vertices))
    vertices=np.concatenate(module);mouth=scene['mouth_y_mm']/1000;rows=[]
    for case in report['cases']:
        collisions=[];minimum=float('inf');max_step=0.
        poses=np.array(case['tcp_poses_socket_m'])
        for j,T in enumerate(poses):
            for name in names:moving.set_transform(name,T)
            hit,pairs=moving.in_collision_other(static,return_names=True)
            if hit:collisions.append(dict(index=j,pairs=sorted([list(v) for v in pairs])))
            surface=vertices@T[:3,:3].T+T[:3,3]
            minimum=min(minimum,float(surface[:,1].min()-mouth))
            if j:max_step=max(max_step,float(np.linalg.norm(T[:3,3]-poses[j-1,:3,3])))
        rows.append(dict(id=case['id'],sample_count=len(poses),collision_samples=collisions,
                         minimum_module_surface_gap_to_mouth_plane_mm=minimum*1000,max_tcp_sample_step_mm=max_step*1000))
        print('CASE',case['id'],'collision_samples',len(collisions),'minimum_gap_mm',minimum*1000,flush=True)
    output=dict(cases=rows,all_sampled_visual_mesh_pairs_clear=all(not r['collision_samples'] for r in rows),
                scope='discrete gripper/module visual meshes against socket assembly only; no continuous sweep, robot self-collision, full environment or dynamics verification')
    (root/'geometry_audit.json').write_text(json.dumps(output,indent=2)+'\n')


if __name__=='__main__':main()
