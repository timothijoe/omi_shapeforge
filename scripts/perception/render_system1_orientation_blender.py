"""Add true 3D module-axis arrows to copies of the saved wide-view scenes."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main():
    root=Path(sys.argv[sys.argv.index('--')+1]);s=json.loads((root/'orientation.json').read_text())
    colors=[(.85,.045,.055,1),(.025,.65,.17,1),(.035,.23,.85,1)]
    for case in s['cases']:
        i=case['id'];bpy.ops.wm.open_mainfile(filepath=str(Path(s['source'])/f'case_{i:02d}_wide.blend'))
        if s.get('only_gt'):
            ob=bpy.data.objects.get('pred_approach')
            if ob:bpy.data.objects.remove(ob,do_unlink=True)
        # Replace only the displayed curves: body-center and tip traces differ
        # under rotation, even though the underlying TCP poses are unchanged.
        for key,points in case.get('paths_mm',{}).items():
            ob=bpy.data.objects[key+'_approach'];spline=ob.data.splines[0]
            assert len(spline.points)==len(points)
            for p,co in zip(spline.points,points):p.co=(*co,1)
            if s.get('only_gt'):ob.color=(.6,.2,.8,1)
        for key,frames in case['frames'].items():
            coll=bpy.data.collections.new(f'{key}_module_orientation');bpy.context.scene.collection.children.link(coll)
            for f in frames:
                points=list(map(Vector,f['points_mm']));origin=points[0]
                for axis,end in enumerate(points[1:]):
                    direction=end-origin;rotation=direction.to_track_quat('Z','Y')
                    bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.18,depth=direction.length-1.2,location=origin+direction.normalized()*(direction.length-1.2)/2)
                    shaft=bpy.context.object;shaft.rotation_mode='QUATERNION';shaft.rotation_quaternion=rotation
                    bpy.ops.mesh.primitive_cone_add(vertices=16,radius1=.55,radius2=0,depth=1.2,location=end-direction.normalized()*.6)
                    head=bpy.context.object;head.rotation_mode='QUATERNION';head.rotation_quaternion=rotation
                    for name,ob in [('shaft',shaft),('head',head)]:
                        ob.name=f'{key}_{f["index"]}_{"XYZ"[axis]}_{name}';ob.color=colors[axis]
                        for c in list(ob.users_collection):c.objects.unlink(ob)
                        coll.objects.link(ob)
        bpy.ops.wm.save_as_mainfile(filepath=str(root/f'case_{i:02d}_orientation.blend'))


if __name__=='__main__':main()
