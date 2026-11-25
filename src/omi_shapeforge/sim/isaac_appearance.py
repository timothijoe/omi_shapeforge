"""Appearance-only improvements. No mesh points or collision parameters are changed."""
import hashlib
import json
import re
import struct
from pathlib import Path
import numpy as np
from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdShade, Vt


def geometry_digest(stage):
    h=hashlib.sha256()
    for prim in stage.Traverse():
        if str(prim.GetPath()).startswith(('/World/ReviewLights','/World/ReviewLooks')):continue
        if prim.IsA(UsdGeom.Mesh):
            for name in ('points','faceVertexCounts','faceVertexIndices'):
                h.update(str(prim.GetPath()).encode());h.update(np.asarray(prim.GetAttribute(name).Get()).tobytes())
        if prim.IsA(UsdGeom.Xformable):
            h.update(str(prim.GetPath()).encode())
            h.update(np.asarray(UsdGeom.Xformable(prim).GetLocalTransformation()).tobytes())
    return h.hexdigest()


def apply_recipe(stage,packet,audit,transfer,recipe='refined'):
    arrays=np.load(Path(transfer)/'meshes.npz',allow_pickle=False)
    normals_count=0;assignments=[]
    mapping=json.loads(Path(packet['manifest']['contact_asset_dir'],'asset_manifest.json').read_text())['mappings']
    module_root=Path('/data/omi_runtime/assets/optical_module_v4/r07')
    overrides=packet['manifest'].get('visual_material_overrides',{})
    module_materials={}
    needs_legacy_module=any(g['name'].startswith('sim_module_') and g['group']<3 and g['rgba'][3]>0
        and g['name'] not in overrides for g in packet['geoms'])
    if needs_legacy_module:
        glb=(module_root/'OM-001-V4-r07.glb').read_bytes()
        gltf=json.loads(glb[20:20+struct.unpack_from('<I',glb,12)[0]])
        from PIL import Image
        for index,mesh_info in enumerate(gltf['meshes']):
            material=gltf['materials'][mesh_info['primitives'][0]['material']]
            pbr=material['pbrMetallicRoughness'];linear=np.array(pbr.get('baseColorFactor',[1,1,1,1])[:3],dtype=float)
            if 'baseColorTexture' in pbr:
                suffix=material['name'].rsplit(' ',1)[1]
                texture=np.asarray(Image.open(module_root/'textures'/f'{suffix}_uniform.png').convert('RGB'))
                if np.ptp(texture.reshape(-1,3),axis=0).max()!=0:raise ValueError('Expected approved uniform r07 texture')
                rgb=texture[0,0].astype(float)/255
                linear*=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
            module_materials[index]=(linear,pbr.get('metallicFactor',1.),pbr.get('roughnessFactor',1.),material['name'])
    for g in packet['geoms']:
        if g['group']>=3 or g['rgba'][3]==0:continue
        prim=stage.GetPrimAtPath(audit['geom_paths'][g['name']])
        mesh=g['mesh']
        # Raw MuJoCo normal mappings are an explicit ablation, not the adopted recipe.
        # The first mapping trial produced shading artifacts; keep native USD normals
        # in the refined recipe until that conversion is independently verified.
        if recipe=='normals' and mesh>=0 and f'n{mesh}' in arrays and f'fn{mesh}' in arrays:
            values=arrays[f'n{mesh}'][arrays[f'fn{mesh}'].reshape(-1)]
            if not np.isfinite(values).all():raise ValueError('invalid source normals')
            obj=UsdGeom.Mesh(prim);obj.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(values.astype(np.float32)))
            obj.SetNormalsInterpolation('faceVarying');normals_count+=1
        if recipe=='normals':continue
        name=g['name'];color=np.array(g['rgba'][:3]);metal=0.;rough=.5;category='painted_robot';linear_override=None
        if name in overrides:
            part=overrides[name];linear_override=np.asarray(part['color_linear'])
            metal=part['metallic'];rough=part['roughness'];category=part['source_part']
            color=np.where(linear_override<=.0031308,12.92*linear_override,1.055*linear_override**(1/2.4)-.055)
        elif name.startswith('sim_module_'):
            index=int(name.split('_')[2]);linear_override,metal,rough,category=module_materials[index]
            color=np.where(linear_override<=.0031308,12.92*linear_override,1.055*linear_override**(1/2.4)-.055)
        elif name.startswith('sim_socket_'):
            prefix='_'.join(name.split('_')[:3]);part=next((v['part'] for k,v in mapping.items() if k.startswith(prefix+'_collision')),'')
            low=part.lower()
            if any(x in low for x in ('polymer','printed','housing','dark insert','package')):
                metal=0.;rough=.62;category='socket_polymer'
            elif 'soldermask' in low:
                metal=0.;rough=.42;category='pcb_soldermask'
            else:metal=.8;rough=.34;category='socket_metal'
        elif name=='floor':color=np.array([.28,.30,.32]);rough=.86;category='floor'
        elif name=='work_table':color=np.array([.63,.65,.62]);rough=.58;category='table'
        elif name=='table_leg':rough=.55;category='painted_support'
        # Source display colors are treated as sRGB approximations, not measured albedo.
        linear=linear_override if linear_override is not None else np.where(color<=.04045,color/12.92,((color+.055)/1.055)**2.4)
        path='/World/ReviewLooks/'+re.sub(r'\W','_',name)
        mat=UsdShade.Material.Define(stage,path);shader=UsdShade.Shader.Define(stage,path+'/Surface')
        shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*linear))
        shader.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(metal)
        shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(rough)
        texture=overrides.get(name,{}).get('base_color_texture')
        if texture:
            if not prim.HasAttribute('primvars:st'):raise ValueError('textured gripper mesh has no UV coordinates')
            tex=UsdShade.Shader.Define(stage,path+'/Texture');tex.CreateIdAttr('UsdUVTexture')
            tex.CreateInput('file',Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath(texture))
            tex.CreateInput('sourceColorSpace',Sdf.ValueTypeNames.Token).Set('sRGB')
            reader=UsdShade.Shader.Define(stage,path+'/UV');reader.CreateIdAttr('UsdPrimvarReader_float2')
            reader.CreateInput('varname',Sdf.ValueTypeNames.Token).Set('st')
            reader.CreateOutput('result',Sdf.ValueTypeNames.Float2)
            tex.CreateInput('st',Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(),'result')
            tex.CreateOutput('rgb',Sdf.ValueTypeNames.Float3)
            shader.GetInput('diffuseColor').ConnectToSource(tex.ConnectableAPI(),'rgb')
        mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(),'surface')
        UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)  # universal visual binding; physics binding retained
        assignments.append(dict(geom=name,category=category,color_srgb=color.tolist(),metallic=metal,roughness=rough))
    if recipe!='normals':
        # Broad area lights give metal surfaces an environment to reflect.
        dome=UsdLux.DomeLight.Get(stage,'/World/Light');dome.CreateIntensityAttr(350.)
        lights=[('Key',[.6,-.3,2.3],[.25,.05,.8],1.5,1.0,5000.),
                ('Fill',[-.8,.5,1.7],[.2,0,.8],1.8,1.2,2500.)]
        for name,position,target,width,height,intensity in lights:
            light=UsdLux.RectLight.Define(stage,'/World/ReviewLights/'+name)
            light.CreateWidthAttr(width);light.CreateHeightAttr(height);light.CreateIntensityAttr(intensity)
            light.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*position),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
    return dict(source_normals_mesh_count=normals_count,materials=assignments,
        normals_policy='raw-source experimental mapping' if recipe=='normals' else 'renderer geometry normals; raw mapping rejected',
        lighting='estimated broad area lights; no photometric calibration',
        module_material_reference=str(module_root/'OM-001-V4-r07.glb') if needs_legacy_module else packet['manifest'].get('module_visual_asset'),
        added_grain_texture=False)
