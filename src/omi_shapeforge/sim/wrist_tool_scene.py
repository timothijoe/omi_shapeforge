"""Mount a separately authored wrist camera/gripper visual kit in a new scene.

The kit has no calibrated collision/inertia model. Preserve existing URDF
dynamics and module/socket contacts; record the fixed-attachment limitation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from .vision_scene import numbers, quaternion


def build(source, tool, mount_solution, output, module=None):
    source, tool, mount_solution, output = map(lambda p: Path(p).resolve(),
                                              (source, tool, mount_solution, output))
    original = json.loads((source/'robot_manifest.json').read_text())
    kit = json.loads((tool/'asset_manifest.json').read_text())
    solution = json.loads(mount_solution.read_text())
    if solution['position_error_mm'] > .01 or solution['angle_error_rad'] > .0001:
        raise ValueError('tool mount initial IK did not converge')
    protected = {str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                 for folder in (source,tool) for p in folder.rglob('*') if p.is_file()}
    output.mkdir(parents=True,exist_ok=False)
    root = ET.parse(source/'scene.xml').getroot()
    root.set('model','OMI measured V4 with video-informed wrist camera and gripper')
    model = mujoco.MjModel.from_xml_path(str(source/'scene.xml'))
    data = mujoco.MjData(model)
    data.qpos[:] = original['initial_qpos']
    for i,q in enumerate(solution['left_arm_qpos'],1):
        data.qpos[model.jnt_qposadr[model.joint(f'Arm_L{i}_Joint').id]] = q
    for name in ['Arm_L10_Joint','Arm_L11_Joint']:
        data.qpos[model.jnt_qposadr[model.joint(name).id]] = kit['integration_joint_reference_qpos_m']
    mujoco.mj_forward(model,data)
    tcp_id=model.body('TCP_Link_L').id
    tcp_R=data.xmat[tcp_id].reshape(3,3);tcp_p=data.xpos[tcp_id]
    hidden=[]
    for name in ['Link8_L','Link_Left_wrist','Arm_L9_Link','Arm_L10_Link','Arm_L11_Link']:
        body=root.find(f".//body[@name='{name}']")
        for geom in list(body.findall('geom')):
            hidden.append(dict(body=name,mesh=geom.get('mesh')));body.remove(geom)
    for item in root.find('asset'):
        if item.get('file'):
            item.set('file',str((source/item.get('file')).resolve()))
    parents={'base':'TCP_Link_L','camera':'TCP_Link_L','camera_mount':'TCP_Link_L',
             'jaw_left':'Arm_L10_Link','jaw_right':'Arm_L11_Link'}
    bindings=[]
    visual_materials={}
    for i,part in enumerate(kit['parts']):
        parent=parents[part['component']];pid=model.body(parent).id
        R=data.xmat[pid].reshape(3,3).T@tcp_R
        p=data.xmat[pid].reshape(3,3).T@(tcp_p-data.xpos[pid])
        name=f'wrist_tool_{i:03d}'
        # A copied asset keeps its original manifest byte-for-byte. Resolve mesh
        # paths against the consumer copy without rewriting the published manifest.
        mesh=tool/'meshes'/Path(part['mesh']).name
        if not mesh.is_file():raise FileNotFoundError(mesh)
        ET.SubElement(root.find('asset'),'mesh',name=name,file=str(mesh),inertia='shell')
        body=root.find(f".//body[@name='{parent}']")
        ET.SubElement(body,'geom',name=name,type='mesh',mesh=name,pos=numbers(p),quat=numbers(quaternion(R)),
                      group='1',contype='0',conaffinity='0',mass='0',rgba=numbers(part.get('mujoco_rgba',part['color'])))
        bindings.append(dict(name=name,part=part['name'],parent=parent,visual_only=True))
        visual_materials[name]=dict(color_linear=part['color'][:3],metallic=part.get('metallic',0.),
            roughness=part.get('roughness',.5),source_part=part['name'],asset=kit['asset_id'])
    tcp=root.find(".//body[@name='TCP_Link_L']")
    camera=tcp.find("camera[@name='wrist_rgb']")
    if camera is None:raise ValueError('original wrist camera is missing')
    previous_camera=dict(camera.attrib)
    for key in ('quat','euler','axisangle','zaxis'):camera.attrib.pop(key,None)
    camera.set('pos',numbers(kit['camera']['optical_position_m']))
    camera.set('xyaxes',numbers(kit['camera']['xyaxes_tcp']))
    camera.set('fovy',str(kit['camera']['fovy_degrees']))
    held=tcp.find("body[@name='sim_module']")
    held.set('pos',numbers(solution['tool_to_module']['position_m']))
    held.set('quat',numbers(quaternion(np.asarray(solution['tool_to_module']['rotation']))))
    module_info=None
    if module is not None:
        module=Path(module).resolve();module_info=json.loads((module/'asset_manifest.json').read_text())
        patch=json.loads((module/'mujoco_visual_patch.json').read_text())
        removed=[]
        for geom in list(held.findall('geom')):
            name=geom.get('name','')
            if name in patch['remove_visual_geoms'] or name.startswith(('sim_module_008_collision','sim_module_010_collision')):
                held.remove(geom);removed.append(name)
        material_root=ET.parse(module/'mujoco_materials.xml').getroot()
        for item in material_root:
            if item.get('file'):
                local=module/'textures'/Path(item.get('file')).name
                if not local.exists():raise FileNotFoundError(local)
                item.set('file',str(local))
            root.find('asset').append(item)
        for part in module_info['parts']:
            mesh=module/'meshes'/Path(part['mesh']).name
            index=part.get('source_part_index')
            if index is not None:
                name=f'sim_module_{index:03d}_visual'
                root.find(f"asset/mesh[@name='{name}']").set('file',str(mesh))
                geom=held.find(f"geom[@name='{name}']")
            else:
                name='sim_module_u_handle_visual'
                ET.SubElement(root.find('asset'),'mesh',name=name,file=str(mesh),inertia='shell')
                angle=np.deg2rad(patch['inspection_angle_deg']);c,s=np.cos(angle),np.sin(angle)
                R=np.array([[1.,0,0],[0,c,-s],[0,s,c]]);pivot=np.asarray(patch['hinge_pivot_m'])
                body=ET.SubElement(held,'body',name='module_u_handle',pos=numbers(pivot-R@pivot),quat=numbers(quaternion(R)))
                geom=ET.SubElement(body,'geom',name=name,type='mesh',mesh=name,group='1',contype='0',conaffinity='0',mass='0')
            role=part['material_role']
            if role in ('silver','green','rubber'):
                geom.set('material',f'v4r08_{role}')
            geom.set('rgba',numbers(part.get('mujoco_rgba',part['color'])))
            visual_materials[name]=dict(color_linear=part['color'][:3],metallic=part.get('metallic',0.),roughness=part.get('roughness',.5),
                source_part=part['name'],asset='OM-001/V4 r08',source_part_index=index)
        module_info=dict(asset_id='OM-001/V4 r08',manifest=str(module/'asset_manifest.json'),
            handle_angle_deg=patch['inspection_angle_deg'],removed_geoms=removed,handle_collision_enabled=False,
            note='16 retained main visuals and inherited main collisions; new U handle is visual-only')
    pre=np.asarray(solution['preinsert_tcp_position'])
    Rs=np.asarray(original['socket_to_world']['rotation'])
    seated=pre+Rs@[0.,-(original['shoulder_depth_mm']+5.)/1000,0.]
    goal=seated+Rs@[0.,-.00015,0.]
    root.find(".//site[@name='reach_goal']").set('pos',numbers(goal))
    ET.indent(root);ET.ElementTree(root).write(output/'scene.xml',encoding='unicode')
    new_model=mujoco.MjModel.from_xml_path(str(output/'scene.xml'))
    if new_model.nq!=model.nq:raise ValueError('visual mounting changed the joint state layout')
    manifest=dict(original,scene=str(output/'scene.xml'),scene_sha256=hashlib.sha256((output/'scene.xml').read_bytes()).hexdigest(),
        parent_scene=str(source/'scene.xml'),parent_scene_sha256=protected[str(source/'scene.xml')],
        initial_qpos=data.qpos.tolist(),preinsert_tcp_position=pre.tolist(),seated_tcp_position=seated.tolist(),
        goal_tcp_position=goal.tolist(),goal_tcp_rotation=solution['goal_tcp_rotation'],tool_to_module=solution['tool_to_module'],
        wrist_tool_asset=kit['asset_id'],wrist_tool_asset_manifest=str(tool/'asset_manifest.json'),
        wrist_tool_asset_manifest_sha256=protected[str(tool/'asset_manifest.json')],
        wrist_tool_bindings=bindings,removed_old_left_tool_visuals=hidden,previous_wrist_camera=previous_camera,
        camera_calibrated=False,grasp='fixed module attachment aligned with visual jaws; no calibrated contact grasp',
        wrist_tool_collision_enabled=False,robot_inertias='inherited URDF, not identified for handmade video tool',
        scope='measured module/socket contact with real arm URDF and video-informed visual wrist tool; wrist optics uncalibrated pinhole; no tactile simulation',
        mesh_dependencies_sha256={x.get('file'):hashlib.sha256(Path(x.get('file')).read_bytes()).hexdigest() for x in root.findall('asset/mesh')})
    manifest.update(visual_material_overrides=visual_materials,module_visual_asset=module_info,
        observation_projection=kit.get('observation_projection'),wrist_tool_to_module_candidate=True,
        new_tool_contact_path_validated=False,new_tool_training_validated=False)
    manifest['cameras']=dict(original['cameras'],wrist_rgb=dict(kit['camera']))
    (output/'robot_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['source','tool','mount-solution','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--module',type=Path)
    a=p.parse_args();print(build(a.source,a.tool,a.mount_solution,a.output,a.module)['scene'])


if __name__=='__main__':main()
