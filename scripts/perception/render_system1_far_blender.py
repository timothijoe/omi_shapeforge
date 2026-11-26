"""Wide inspection scene: source meshes plus frozen decoded approach curves."""
import json
from pathlib import Path
import sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix,Vector
import numpy as np


def main():
    root=Path(sys.argv[sys.argv.index('--')+1]);s=json.loads((root/'scene_packet.json').read_text());geom=np.load(root/'asset_geometry.npz')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1450;scene.render.resolution_y=850;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
    shading=scene.display.shading;shading.light='STUDIO';shading.color_type='OBJECT';shading.show_shadows=True;shading.show_cavity=True
    shading.cavity_type='BOTH';shading.background_type='WORLD';scene.world.color=(.85,.89,.94);scene.display.render_aa='32'
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
    objects=[]
    for i,part in enumerate(s['parts']):
        mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata((geom[f'v{i}']*1000).tolist(),[],geom[f'f{i}'].tolist());mesh.update()
        ob=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(ob);ob.color=part['rgba'];objects.append(ob)
    data=bpy.data.cameras.new('WideView');camera=bpy.data.objects.new('WideView',data);bpy.context.collection.objects.link(camera);scene.camera=camera
    data.type='ORTHO';data.clip_start=.1;data.clip_end=2000
    for case in s['cases']:
        i=case['id'];T=np.array(case['socket_from_tcp']);T[:3,3]*=1000
        for ob,part in zip(objects,s['parts']):ob.matrix_world=Matrix(T) if part['category']=='tool' else Matrix.Identity(4)
        tip=np.array(case['paths_mm']['tip'][0])
        target=np.array([tip[0]*.25,35+tip[1]*.45,0.])
        camera.location=Vector(target+np.array([-270,180,230]))
        camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=260
        bpy.context.view_layer.update()
        def screen(p):
            q=world_to_camera_view(scene,camera,Vector(p));return [q.x*1450,(1-q.y)*850]
        pixels={key:[screen(p) for p in pts] for key,pts in case['approach_mm'].items()}
        (root/f'case_{i:02d}_wide.json').write_text(json.dumps(dict(pixels=pixels,tip=screen(tip),camera_world=list(map(list,camera.matrix_world)),ortho_scale=data.ortho_scale),indent=2)+'\n')
        scene.render.filepath=str(root/f'case_{i:02d}_wide.png');bpy.ops.render.render(write_still=True)
        paths=[]
        for key,points in case['approach_mm'].items():
            curve=bpy.data.curves.new(key+'_approach','CURVE');curve.dimensions='3D';curve.bevel_depth=.45;curve.bevel_resolution=3
            spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
            for v,p in zip(spline.points,points):v.co=(*p,1)
            ob=bpy.data.objects.new(key+'_approach',curve);bpy.context.collection.objects.link(ob)
            ob.color=(.08,.42,.8,1) if key=='pred' else (.6,.2,.8,1);paths.append(ob)
        for area in bpy.context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.color_type='OBJECT'
        bpy.ops.wm.save_as_mainfile(filepath=str(root/f'case_{i:02d}_wide.blend'))
        for ob in paths:bpy.data.objects.remove(ob,do_unlink=True)


if __name__=='__main__':main()
