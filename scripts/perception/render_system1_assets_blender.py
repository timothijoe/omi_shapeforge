"""Blender backend for render_system1_assets.py; exact frozen mesh reconstruction."""
import json
from pathlib import Path
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import numpy as np


def curve(name, points, color, radius):
    mesh=bpy.data.curves.new(name, 'CURVE');mesh.dimensions='3D'
    mesh.bevel_depth=radius;mesh.bevel_resolution=2
    s=mesh.splines.new('POLY');s.points.add(len(points)-1)
    for p,co in zip(s.points, points):p.co=(*co,1)
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    ob.color=(*color,1)
    return ob


def main():
    root=Path(sys.argv[sys.argv.index('--')+1])
    packet=json.loads((root/'scene_packet.json').read_text())
    geom=np.load(root/'asset_geometry.npz',allow_pickle=False)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='BLENDER_WORKBENCH'
    scene.render.resolution_x=1520;scene.render.resolution_y=400;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world.color=(.12,.12,.12)
    scene.view_settings.view_transform='Standard'
    shading=scene.display.shading
    shading.light='STUDIO';shading.studiolight_rotate_z=.4
    shading.color_type='OBJECT';shading.show_shadows=True;shading.show_cavity=True
    shading.cavity_type='BOTH';shading.curvature_ridge_factor=1.3
    shading.background_type='WORLD';scene.world.color=(.045,.065,.09)
    scene.display.render_aa='16'
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
    meshes=[]
    for i,part in enumerate(packet['parts']):
        data=bpy.data.meshes.new(part['name']);data.from_pydata((geom[f'v{i}']*1000).tolist(),[],geom[f'f{i}'].tolist());data.update()
        ob=bpy.data.objects.new(part['name'],data);bpy.context.collection.objects.link(ob)
        ob.color=tuple(part['rgba']);meshes.append(ob)
    cdata=bpy.data.cameras.new('InspectionCamera');camera=bpy.data.objects.new('InspectionCamera',cdata)
    bpy.context.collection.objects.link(camera);scene.camera=camera
    cdata.type='ORTHO';cdata.clip_start=.1;cdata.clip_end=2000
    mouth=packet['mouth_y_mm'];cx,cz=packet['center_xz_mm']
    for case in packet['cases']:
        i=case['id'];T=np.array(case['socket_from_tcp']);T[:3,3]*=1000
        for ob,part in zip(meshes,packet['parts']):ob.matrix_world=Matrix(T) if part['category']=='tool' else Matrix.Identity(4)
        bpy.context.view_layer.update()
        # Ray cast against asset meshes only, excluding path annotation geometry.
        vertices=[];faces=[]
        for ob in meshes:
            offset=len(vertices)
            vertices.extend([ob.matrix_world@v.co for v in ob.data.vertices])
            faces.extend([tuple(offset+j for j in p.vertices) for p in ob.data.polygons])
        tree=BVHTree.FromPolygons(vertices, faces, all_triangles=True)
        path_objects=[]
        for key in ['full_gt','full_pred','gt','pred']:
            color=(.12,.8,.44) if 'gt' in key else (1,.38,.025)
            path_objects.append(curve(key,case['complete_paths_mm'][key],color,.055 if key.startswith('full') else .12))
        # Paths exist as editable 3D curves in the saved scene; PNG annotations are
        # projected from the same coordinates for sharp, legible visibility styles.
        for ob in path_objects:ob.hide_render=True
        tip=np.array(case['paths_mm']['tip'][0])
        for view,target,offset,span in [
            ('overview',np.array([cx,30,cz]),np.array([145,155,115]),190),
            ('detail',(tip+np.array([cx,mouth,cz]))/2,np.array([48,30,30]),72),
        ]:
            camera.location=Vector(target+offset)
            camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler()
            cdata.ortho_scale=span
            bpy.context.view_layer.update()
            pixels={};visible={}
            toward=camera.rotation_euler.to_matrix()@Vector((0,0,1))
            for key,points in case['paths_mm'].items():
                pixels[key]=[];visible[key]=[]
                for p in points:
                    v=Vector(p);screen=world_to_camera_view(scene,camera,v)
                    pixels[key].append([screen.x*1520,(1-screen.y)*400])
                    hit,_,_,dist=tree.ray_cast(v+toward*.15,toward,1000)
                    visible[key].append(hit is None)
            (root/f'case_{i:02d}_{view}.json').write_text(json.dumps(dict(pixels=pixels,visible=visible,camera_world=list(map(list,camera.matrix_world)),ortho_scale=span),indent=2)+'\n')
            scene.render.filepath=str(root/f'case_{i:02d}_{view}.png')
            bpy.ops.render.render(write_still=True)
        for ob in path_objects:ob.hide_render=False
        for area in bpy.context.screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.color_type='OBJECT'
        bpy.ops.wm.save_as_mainfile(filepath=str(root/f'case_{i:02d}.blend'))
        for ob in path_objects:bpy.data.objects.remove(ob,do_unlink=True)
        print('CASE_COMPLETE',i,flush=True)


if __name__=='__main__':main()
