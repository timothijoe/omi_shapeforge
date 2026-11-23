"""Materialize the NEW simulation asset as an editable Blender authoring file."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Quaternion, Vector


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--asset-dir',type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);directory=a.asset_dir.resolve()
    manifest=json.loads((directory/'asset_manifest.json').read_text())
    destination=directory/(manifest['asset_id']+'.blend')
    if destination.exists():raise FileExistsError(destination)
    root=ET.parse(directory/'scene.xml').getroot()
    meshes={x.get('name'):Path(x.get('file')) for x in root.findall('asset/mesh')}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene['asset_id']=manifest['asset_id'];scene['simulation_approximation']=True
    scene['original_meshes_modified']=False;scene['contact_model']='seven independent bounded spherical spring contacts'
    visual=bpy.data.collections.new('Simulation visuals');scene.collection.children.link(visual)
    collision=bpy.data.collections.new('Collision proxies');scene.collection.children.link(collision)
    def material(name,rgba):
        m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.diffuse_color=rgba
        return m
    def add_mesh(geom,transform):
        name=geom.get('name');is_proxy=geom.get('group')=='3'
        collection=collision if is_proxy else visual
        if geom.get('type')=='mesh':
            vertices=[];faces=[]
            for line in meshes[geom.get('mesh')].read_text().splitlines():
                words=line.split()
                if words and words[0]=='v':vertices.append(tuple(map(float,words[1:4])))
                elif words and words[0]=='f':faces.append(tuple(int(w.split('/')[0])-1 for w in words[1:]))
            mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
            obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
        elif geom.get('type')=='sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,radius=float(geom.get('size')))
            obj=bpy.context.object;obj.name=name
            for c in list(obj.users_collection):c.objects.unlink(obj)
            collection.objects.link(obj)
            obj['stroke_m']=manifest['pads'][0]['stroke_m'];obj['stiffness_N_m']=100.;obj['damping_Ns_m']=.63
        else:raise ValueError(geom.attrib)
        obj.matrix_world=transform
        rgba=tuple(map(float,geom.get('rgba','.25 .6 .9 1').split()))
        obj.data.materials.append(material(name+'_material',rgba))
        obj['role']='collision' if is_proxy else 'visual_or_equivalent_contact'
    def body(element,parent):
        pos=Vector(tuple(map(float,element.get('pos','0 0 0').split())))
        quat=Quaternion(tuple(map(float,element.get('quat','1 0 0 0').split())))
        transform=parent@Matrix.Translation(pos)@quat.to_matrix().to_4x4()
        for geom in element.findall('geom'):add_mesh(geom,transform)
        for child in element.findall('body'):body(child,transform)
    for b in root.findall('worldbody/body'):body(b,Matrix.Identity(4))
    collision.hide_render=True;collision.hide_viewport=True
    scene.world=bpy.data.worlds.new('World');scene.world.color=(.08,.08,.08)
    bpy.ops.object.camera_add(location=(.16,.22,.15));camera=bpy.context.object
    camera.rotation_euler=(Vector((-.005,-.01,-.035))-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=.27;camera.data.clip_start=.0001;scene.camera=camera
    for pos,energy in [((.1,.15,.3),100),((-.2,-.1,.2),60)]:
        bpy.ops.object.light_add(type='AREA',location=pos);bpy.context.object.data.energy=energy;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=.3
    scene.render.engine='BLENDER_EEVEE_NEXT';scene.render.resolution_x=1200;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    bpy.ops.wm.save_as_mainfile(filepath=str(destination))
    (directory/'blender_authoring.json').write_text(json.dumps(dict(file=str(destination),objects=len(bpy.data.objects),
        asset_id=manifest['asset_id'],source_geometry_files_modified=False),indent=2)+'\n')
    print('NEW_SIMULATION_BLEND_READY',destination,flush=True)


if __name__=='__main__':main()
