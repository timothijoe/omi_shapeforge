"""Repose copies of the source assets at three unexecuted GT reference poses."""
import json
from pathlib import Path
import sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix,Vector
import numpy as np


def main():
    root=Path(sys.argv[sys.argv.index('--')+1]);p=json.loads((root/'explanation.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(Path(p['source'])/f"case_{p['case']:02d}_wide.blend"))
    scene=bpy.context.scene;camera=scene.camera
    scene.render.resolution_x=1000;scene.render.resolution_y=650;scene.display.render_aa='16'
    ob=bpy.data.objects.get('pred_approach')
    if ob:bpy.data.objects.remove(ob,do_unlink=True)
    ob=bpy.data.objects.get('gt_approach')
    if ob:
        ob.data.splines.clear();spline=ob.data.splines.new('POLY');spline.points.add(len(p['path_mm'])-1)
        for point,co in zip(spline.points,p['path_mm']):point.co=(*co,1)
        ob.hide_render=True
    if p.get('tip_path_mm'):
        data=bpy.data.curves.new('module_tip_reference','CURVE');data.dimensions='3D';data.bevel_depth=.3
        spline=data.splines.new('POLY');spline.points.add(len(p['tip_path_mm'])-1)
        for point,co in zip(spline.points,p['tip_path_mm']):point.co=(*co,1)
        ob=bpy.data.objects.new('module_tip_reference',data);bpy.context.collection.objects.link(ob)
        ob.color=(1,.4,.04,1);ob.hide_render=True
    # One fixed camera for all three states.
    target=Vector((0,65,0));camera.location=target+Vector((-270,180,230))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=250
    for snap in p['snapshots']:
        T=np.array(snap['tcp_socket_m']);T[:3,3]*=1000
        for name in p['tool_names']:bpy.data.objects[name].matrix_world=Matrix(T)
        bpy.context.view_layer.update()
        def screen(point):
            uv=world_to_camera_view(scene,camera,Vector(point));return [uv.x*1000,(1-uv.y)*650]
        uv=dict(path=[screen(x) for x in p['path_mm']],axes=[screen(x) for x in snap['axes_mm']],tip=screen(snap['tip_mm']))
        (root/f"pose_{snap['index']:02d}.json").write_text(json.dumps(uv,indent=2)+'\n')
        scene.render.filepath=str(root/f"pose_{snap['index']:02d}.png");bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(root/'gt_endpoint.blend'))


if __name__=='__main__':main()
