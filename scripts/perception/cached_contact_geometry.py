"""Reuse FCL acceleration structures; preserve the original mesh gate rules."""
import numpy as np
import trimesh
from contact_visual_gate import VisibleGraspGate

class CachedGraspGate(VisibleGraspGate):
 def __init__(self):
  super().__init__();self.nonpad=trimesh.collision.CollisionManager();self.pads={}
  for i,(p,mesh) in enumerate(zip(self.tool,self.meshes)):
   if '24 convex black contact pad' in p['name']:
    side=p['component'].removeprefix('jaw_');manager=trimesh.collision.CollisionManager();manager.add_object(str(i),mesh);self.pads[side]=(i,manager)
   else:self.nonpad.add_object(str(i),mesh)
 def check(self,T_tool_module,jaws):
  for key in self.modules:self.manager.set_transform(key,T_tool_module)
  for i,p in enumerate(self.tool):
   side=p['component'].removeprefix('jaw_');T=np.eye(4)
   if side in jaws:T[1,3]=jaws[side]*(-1 if side=='left' else 1)
   if '24 convex black contact pad' in p['name']:self.pads[side][1].set_transform(str(i),T)
   else:self.nonpad.set_transform(str(i),T)
  hits,names=self.nonpad.in_collision_other(self.manager,return_names=True);intersections=sorted({self.tool[int(pair[0])]['name'] for pair in names}) if hits else []
  pads={s:{'distance_mm':float(manager.min_distance_other(self.manager)*1000),'touch_or_overlap':bool(manager.in_collision_other(self.manager))} for s,(_,manager) in self.pads.items()}
  return {'accepted':not intersections and len(pads)==2 and all(-.05<=p['distance_mm']<.02 for p in pads.values()),'nonpad_intersections':intersections,'pads':pads,'excludes_articulated_green_handle':True}
