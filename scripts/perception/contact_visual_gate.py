"""Check actual rigid visible surfaces separately from convex collision proxies."""
import json
from pathlib import Path
import numpy as np
import trimesh

class VisibleGraspGate:
    def __init__(self):
        self.tool=json.loads(Path('/data/omi_runtime/assets/daimon/wrist_gripper_logo_r15/asset_manifest.json').read_text())['parts']
        module=json.loads(Path('/data/omi_runtime/assets/optical_module_v4/r08/asset_manifest.json').read_text())['parts']
        self.manager=trimesh.collision.CollisionManager();self.modules=[]
        for i,p in enumerate(module):
            if p.get('component')=='pull_handle':continue
            self.manager.add_object(str(i),trimesh.load(p['mesh'],force='mesh',process=False));self.modules.append(str(i))
        self.meshes=[trimesh.load(p['mesh'],force='mesh',process=False) for p in self.tool]
    def check(self,T_tool_module,jaws):
        for key in self.modules:self.manager.set_transform(key,T_tool_module)
        intersections=[];pads={}
        for p,mesh in zip(self.tool,self.meshes):
            side=p['component'].removeprefix('jaw_');T=np.eye(4)
            if side in jaws:T[1,3]=jaws[side]*(-1 if side=='left' else 1)
            hits=self.manager.in_collision_single(mesh,transform=T)
            if '24 convex black contact pad' in p['name']:pads[side]={'distance_mm':float(self.manager.min_distance_single(mesh,transform=T)*1000),'touch_or_overlap':bool(hits)}
            elif hits:intersections.append(p['name'])
        return {'accepted':len(intersections)==0 and len(pads)==2 and all(-.05<=p['distance_mm']<.02 for p in pads.values()),'nonpad_intersections':intersections,'pads':pads,'excludes_articulated_green_handle':True}
