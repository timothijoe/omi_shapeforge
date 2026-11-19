"""Author the same optical-module prototype as MuJoCo MJCF and Isaac-compatible USD."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import numpy as np


def text(values):
    return ' '.join(format(float(x), '.10g') for x in values)


def mjcf(output, asset, placements, fixtures, table_halfsize):
    root = ET.Element('mujoco', model='omi_optical_module_prototype')
    ET.SubElement(root, 'compiler', angle='radian', autolimits='true', meshdir='meshes')
    ET.SubElement(root, 'option', timestep=str(1 / 120), gravity='0 0 -9.81',
                  iterations='100', tolerance='1e-10', cone='elliptic')
    visual = ET.SubElement(root, 'visual')
    ET.SubElement(visual, 'global', offwidth='960', offheight='720')
    assets = ET.SubElement(root, 'asset')
    for index, part in enumerate(asset['parts']):
        ET.SubElement(assets, 'mesh', name=f'part_{index}', file=Path(part['mesh']).name)
    world = ET.SubElement(root, 'worldbody')
    ET.SubElement(world, 'light', pos='0 -0.15 0.3', dir='0 0 -1', diffuse='0.8 0.8 0.8')
    ET.SubElement(world, 'geom', name='table', type='box', size=text(table_halfsize),
                  pos=f'0 0 {-table_halfsize[2]}', rgba='0.3 0.33 0.38 1',
                  friction='0.6 0.005 0.0001')
    for index, fixture in enumerate(fixtures):
        ET.SubElement(world, 'geom', name=f'fixture_proxy_{index}', type='box',
                      size=text(fixture['halfsize']), pos=text(fixture['position']),
                      rgba='0.12 0.16 0.21 1', friction='0.6 0.005 0.0001')
    for index, position in enumerate(placements):
        body = ET.SubElement(world, 'body', name=f'optical_module_{index}', pos=text(position))
        ET.SubElement(body, 'freejoint', name=f'module_free_{index}')
        ET.SubElement(body, 'geom', name=f'module_collision_{index}', type='box',
                      size=text(asset['collision_box_halfsize_m']),
                      pos=text(asset['collision_box_center_m']), mass=str(asset['mass_kg']),
                      rgba='0.7 0.2 0.1 0', friction='0.6 0.005 0.0001', group='3')
        for part_index, part in enumerate(asset['parts']):
            ET.SubElement(body, 'geom', name=f'visual_{index}_{part_index}', type='mesh',
                          mesh=f'part_{part_index}', rgba=text(part['rgba']),
                          contype='0', conaffinity='0', mass='0', group='1')
    ET.indent(root)
    ET.ElementTree(root).write(output / 'scene.xml', encoding='unicode')


def read_obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'v':
            vertices.append([float(x) for x in fields[1:4]])
        elif fields[0] == 'f':
            faces.append([int(x.split('/')[0]) - 1 for x in fields[1:4]])
    return vertices, faces


def usd(output, asset, placements, fixtures, table_halfsize):
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, Vt

    stage = Usd.Stage.CreateNew(str(output / 'scene.usda'))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    stage.SetTimeCodesPerSecond(120)
    world = UsdGeom.Xform.Define(stage, '/World')
    stage.SetDefaultPrim(world.GetPrim())
    physics = UsdPhysics.Scene.Define(stage, '/World/PhysicsScene')
    physics.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    physics.CreateGravityMagnitudeAttr(9.81)
    contact = UsdShade.Material.Define(stage, '/World/ContactMaterial')
    physical = UsdPhysics.MaterialAPI.Apply(contact.GetPrim())
    physical.CreateStaticFrictionAttr(0.6)
    physical.CreateDynamicFrictionAttr(0.6)
    physical.CreateRestitutionAttr(0.0)

    def material(path, rgba, metallic=0.0):
        material = UsdShade.Material.Define(stage, path)
        shader = UsdShade.Shader.Define(stage, path + '/Surface')
        shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgba[:3]))
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(metallic)
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(0.35)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        return material

    dark = material('/World/Looks/Support', [0.17, 0.20, 0.25, 1])

    def cube(path, position, halfsize, visible=True):
        obj = UsdGeom.Cube.Define(stage, path)
        obj.CreateSizeAttr(1.0)
        obj.AddTranslateOp().Set(Gf.Vec3d(*position))
        obj.AddScaleOp().Set(Gf.Vec3f(*[2 * x for x in halfsize]))
        UsdPhysics.CollisionAPI.Apply(obj.GetPrim())
        UsdShade.MaterialBindingAPI.Apply(obj.GetPrim()).Bind(contact, materialPurpose='physics')
        if visible:
            UsdShade.MaterialBindingAPI.Apply(obj.GetPrim()).Bind(dark)
        else:
            obj.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
        return obj

    cube('/World/Table', [0, 0, -table_halfsize[2]], table_halfsize)
    for index, fixture in enumerate(fixtures):
        cube(f'/World/FixtureProxy_{index}', fixture['position'], fixture['halfsize'])
    meshes = [read_obj(output / part['mesh']) for part in asset['parts']]
    for index, position in enumerate(placements):
        path = f'/World/OpticalModule_{index}'
        body = UsdGeom.Xform.Define(stage, path)
        body.AddTranslateOp().Set(Gf.Vec3d(*position))
        UsdPhysics.RigidBodyAPI.Apply(body.GetPrim()).CreateRigidBodyEnabledAttr(True)
        mass = UsdPhysics.MassAPI.Apply(body.GetPrim())
        mass.CreateMassAttr(asset['mass_kg'])
        mass.CreateCenterOfMassAttr(Gf.Vec3f(*asset['collision_box_center_m']))
        size = np.array(asset['collision_box_halfsize_m']) * 2
        inertia = asset['mass_kg'] / 12 * np.array([size[1]**2 + size[2]**2,
            size[0]**2 + size[2]**2, size[0]**2 + size[1]**2])
        mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*inertia))
        cube(path + '/CollisionBox', asset['collision_box_center_m'],
             asset['collision_box_halfsize_m'], visible=False)
        for part_index, (part, (vertices, faces)) in enumerate(zip(asset['parts'], meshes)):
            mesh = UsdGeom.Mesh.Define(stage, path + f'/Visual_{part_index}')
            mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*v) for v in vertices]))
            mesh.CreateFaceVertexCountsAttr([3] * len(faces))
            mesh.CreateFaceVertexIndicesAttr([i for face in faces for i in face])
            mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
            mesh.CreateDoubleSidedAttr(True)
            surface = material(f'/World/Looks/Part_{part_index}', part['rgba'],
                               0.0 if part['rgba'][1] > part['rgba'][0] * 1.3 else 0.6)
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(surface)
    light = UsdLux.DomeLight.Define(stage, '/World/Light')
    light.CreateIntensityAttr(800.0)
    camera = UsdGeom.Camera.Define(stage, '/World/Camera')
    view = Gf.Matrix4d().SetLookAt(Gf.Vec3d(0.18, -0.22, 0.18), Gf.Vec3d(0, 0, 0.025), Gf.Vec3d(0, 0, 1))
    camera.AddTransformOp().Set(view.GetInverse())
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.001, 10.0))
    camera.CreateFocalLengthAttr(40.0)
    stage.GetRootLayer().Save()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--rows', type=int, default=1)
    p.add_argument('--columns', type=int, default=1)
    args = p.parse_args()
    if not 1 <= args.rows * args.columns <= 16 or min(args.rows, args.columns) < 1:
        p.error('Use between 1 and 16 modules')
    asset = json.loads((args.asset / 'asset.json').read_text())
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(args.asset / 'meshes', output / 'meshes')
    placements, fixtures = [], []
    for row in range(args.rows):
        for column in range(args.columns):
            x = (column - (args.columns - 1) / 2) * 0.12
            y = (row - (args.rows - 1) / 2) * 0.14
            placements.append([x, y, 0.055])
            for sign in (-1, 1):
                fixtures.append({'position': [x + sign * 0.025, y, 0.008],
                                 'halfsize': [0.004, 0.045, 0.008]})
    table_halfsize = [max(0.15, args.columns * 0.07), max(0.13, args.rows * 0.08), 0.01]
    mjcf(output, asset, placements, fixtures, table_halfsize)
    usd(output, asset, placements, fixtures, table_halfsize)
    manifest = {'asset': asset, 'initial_positions_m': placements, 'rows': args.rows,
                'columns': args.columns, 'gravity_m_s2': 9.81, 'timestep_s': 1 / 120,
                'fixture': 'Illustrative support rails; not reconstructed fixture CAD.',
                'physics': 'Assumed 20 g mass, friction 0.6, box collision; not calibrated.',
                'files_sha256': {n: hashlib.file_digest((output / n).open('rb'), 'sha256').hexdigest()
                                 for n in ('scene.xml', 'scene.usda')}}
    (output / 'scene_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'status': 'authored_both_scene_formats', 'output': str(output),
                      'modules': len(placements), 'visual_parts_per_module': len(asset['parts'])}, indent=2))


if __name__ == '__main__':
    main()
