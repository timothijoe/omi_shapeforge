"""Isaac WG-r10/OM-r08 mount, jaw actuation and pinned fisheye observation preview."""
import argparse,hashlib,json,os,shutil,sys,traceback
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transfer',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mount-audit',type=Path,required=True);p.add_argument('--face-size',type=int,default=2048)
    p.add_argument('--static-only',action='store_true');p.add_argument('--audit-right-visibility',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    repo=Path(__file__).resolve().parents[2];sys.path[:0]=['/data/omi_runtime/envs/isaac_contact_support',str(repo/'src')]
    snapshot=a.output/'code_snapshot';snapshot.mkdir()
    for path in [Path(__file__),*[repo/'src/omi_shapeforge/sim'/n for n in ['isaac_contact_scene.py','isaac_contact_runtime.py','isaac_contact_kinematics.py','isaac_appearance.py','wrist_fisheye.py']]]:
        shutil.copy2(path,snapshot/path.name)
    import omi_shapeforge.sim
    omi_shapeforge.sim.__path__=[str(snapshot)]
    sys.argv=[sys.argv[0]];root=Path('/data/isaac-sim-5.1.0')
    from isaacsim import SimulationApp
    extra=['--/app/extensions/registryEnabled=false']
    for f in ('exts','extscache','kit/exts','kit/extscore'):extra+=['--ext-folder',str(root/f)]
    app=SimulationApp(dict(headless=True,width=1280,height=960,limit_cpu_threads=4,multi_gpu=False,extra_args=extra),experience=str(root/'apps/isaacsim.exp.base.python.kit'))
    failed=False
    try:
        import numpy as np
        from PIL import Image,ImageDraw
        import omni.usd,omni.replicator.core as rep
        from pxr import Gf,UsdGeom,UsdPhysics,PhysxSchema
        from omi_shapeforge.sim.isaac_contact_scene import build,set_pose
        from omi_shapeforge.sim.isaac_contact_runtime import DirectWorld,TensorArticulation,matrix
        from omi_shapeforge.sim.isaac_appearance import apply_recipe,geometry_digest
        from omi_shapeforge.sim.wrist_fisheye import FACES,CV_TO_GL,maps,reproject
        context=omni.usd.get_context();context.new_stage();world=DirectWorld(context.get_stage(),app,.0002)
        physics=UsdPhysics.Scene.Define(world.stage,'/World/PhysicsScene');physics.CreateGravityDirectionAttr(Gf.Vec3f(0,0,-1));physics.CreateGravityMagnitudeAttr(9.81)
        settings=PhysxSchema.PhysxSceneAPI.Apply(physics.GetPrim());settings.CreateEnableGPUDynamicsAttr(False)
        settings.CreateBroadphaseTypeAttr('MBP');settings.CreateSolverTypeAttr('PGS');settings.CreateTimeStepsPerSecondAttr(5000);settings.CreateEnableStabilizationAttr(False)
        packet,audit=build(world.stage,a.transfer,a.output,contact_offset=1e-7)
        before=geometry_digest(world.stage);appearance=apply_recipe(world.stage,packet,audit,a.transfer,'refined')
        assert geometry_digest(world.stage)==before
        (a.output/'appearance.json').write_text(json.dumps(appearance,indent=2)+'\n')
        world.reset();robot=TensorArticulation(world);names=robot.dof_names;joints={j['name']:j for j in packet['joints']}
        q=np.array([[packet['initial_qpos'][joints[n]['qpos_index']] for n in names]],np.float32)
        robot.set_joint_positions(q);robot.set_joint_velocities(np.zeros_like(q));robot.set_joint_position_targets(q)
        for _ in range(3):world.step()
        world.sync()
        for name,value in zip(names,q[0]):
            angular=joints[name]['kind']==3
            UsdPhysics.DriveAPI(world.stage.GetPrimAtPath(audit['joint_paths'][name]),'angular' if angular else 'linear').GetTargetPositionAttr().Set(float(np.degrees(value) if angular else value))
        world.stage.GetRootLayer().Export(str(a.output/'WG-r10_OM-r08_robot.usdc'))
        rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
        cameras={};products=[];overview_seg=None
        if a.audit_right_visibility:
            from pxr import Semantics
            for geom in packet['geoms']:
                b=geom['body'];right=False
                while b:
                    if packet['bodies'][b]['name']=='Link1_R':right=True;break
                    b=packet['bodies'][b]['parent']
                if right and geom['group']<3 and geom['rgba'][3]>0:
                    sem=Semantics.SemanticsAPI.Apply(world.stage.GetPrimAtPath(audit['geom_paths'][geom['name']]),'RightArmVisibility')
                    sem.CreateSemanticTypeAttr().Set('class');sem.CreateSemanticDataAttr().Set('inactive_right_arm')
        for name,resolution in [('overview',(1280,960)),('head_rgb',(768,768)),('wrist_rgb',(768,768))]:
            product=rep.create.render_product(audit['cameras'][name],resolution);products.append(product)
            annot=rep.AnnotatorRegistry.get_annotator('rgb');annot.attach(product);cameras[name]=annot
            if a.audit_right_visibility and name=='overview':
                overview_seg=rep.AnnotatorRegistry.get_annotator('semantic_segmentation',init_params={'colorize':False});overview_seg.attach(product)
        cube_paths=[];cube_annots=[];cube_seg=[]
        for i in range(6):
            path=f'/World/WristCube_{i}';cam=UsdGeom.Camera.Define(world.stage,path)
            cam.CreateFocalLengthAttr(10.);cam.CreateHorizontalApertureAttr(20.);cam.CreateVerticalApertureAttr(20.)
            cam.CreateClippingRangeAttr(Gf.Vec2f(.0001,20.));cube_paths.append(path)
            product=rep.create.render_product(path,(a.face_size,a.face_size));products.append(product)
            annot=rep.AnnotatorRegistry.get_annotator('rgb');annot.attach(product);cube_annots.append(annot)
            if a.audit_right_visibility:
                segment=rep.AnnotatorRegistry.get_annotator('semantic_segmentation',init_params={'colorize':False});segment.attach(product);cube_seg.append(segment)
        projection=packet['manifest']['observation_projection'];sampling=maps(projection,a.face_size)
        tcp_path=audit['frame_paths']['TCP_Link_L'];module_path=audit['frame_paths']['sim_module']
        camera_path=audit['cameras']['wrist_rgb'];tool=packet['manifest']['tool_to_module']
        expected=np.eye(4);expected[:3,:3]=tool['rotation'];expected[:3,3]=tool['position_m']
        baseline_camera=np.linalg.inv(matrix(world.stage,tcp_path))@matrix(world.stage,camera_path)
        jaw_tests=json.loads(a.mount_audit.read_text())['jaw_tests'];target_open=q.copy()
        for j in jaw_tests:target_open[0,names.index(j['joint'])]=j['open_qpos_m']
        rows=[];frames=[];visibility=[]
        def capture(label,with_fisheye=False):
            world.sync();current=robot.get_joint_positions().copy()
            Twc_gl=matrix(world.stage,camera_path);Twc_cv=Twc_gl.copy();Twc_cv[:3,:3]=Twc_gl[:3,:3]@CV_TO_GL
            for path,Rface in zip(cube_paths,FACES):
                t=Twc_cv.copy();t[:3,:3]=Twc_cv[:3,:3]@Rface@CV_TO_GL
                set_pose(world.stage.GetPrimAtPath(path),t)
            for _ in range(2):rep.orchestrator.step(delta_time=0.,pause_timeline=True,rt_subframes=2)
            np.testing.assert_allclose(robot.get_joint_positions(),current,atol=1e-9,rtol=0.)
            images={n:x.get_data()[:,:,:3].copy() for n,x in cameras.items()}
            for name,im in images.items():assert im.size and np.ptp(im)>0
            if with_fisheye:
                fish=reproject([x.get_data() for x in cube_annots],sampling)
                assert fish.shape==(1080,1920,3)
                Image.fromarray(fish).save(a.output/f'{label}_wrist_fisheye_1920.png')
                Image.fromarray(fish).crop((600,510,1350,1060)).save(a.output/f'{label}_wrist_detail.png')
                for name,im in images.items():Image.fromarray(im).save(a.output/f'{label}_{name}.png')
                if cube_seg:
                    right_mask=np.zeros((1080,1920),np.uint8);cube_pixels=0
                    for annot,(selection,u,v) in zip(cube_seg,sampling):
                        seg=annot.get_data();ids=[int(i) for i,value in seg['info']['idToLabels'].items() if value.get('class')=='inactive_right_arm']
                        mask=np.isin(seg['data'],ids).reshape(a.face_size,a.face_size);cube_pixels+=int(mask.sum())
                        right_mask[selection]=mask[np.rint(v).astype(int),np.rint(u).astype(int)]
                    overview_data=overview_seg.get_data()
                    overview_ids=[int(i) for i,value in overview_data['info']['idToLabels'].items() if value.get('class')=='inactive_right_arm']
                    overview_pixels=int(np.isin(overview_data['data'],overview_ids).sum())
                    (a.output/f'{label}_semantic_labels.json').write_text(json.dumps(overview_data['info']['idToLabels'],indent=2)+'\n')
                    assert overview_pixels>0,'right-arm semantic label not detected in the overview control image'
                    Image.fromarray(right_mask*255).save(a.output/f'{label}_right_arm_mask.png')
                    visibility.append(dict(label=label,right_arm_overview_pixels=overview_pixels,right_arm_cube_pixels=cube_pixels,right_arm_fisheye_pixels=int(right_mask.sum())))
            panel=Image.new('RGB',(1792,1024),'#15212b');panel.paste(Image.fromarray(images['overview']),(0,32))
            panel.paste(Image.fromarray(images['head_rgb']).resize((512,512)),(1280,0));panel.paste(Image.fromarray(images['wrist_rgb']).resize((512,512)),(1280,512))
            draw=ImageDraw.Draw(panel);draw.text((12,10),'WG-r10 + OM-r08 | jaw drive preview | wrist panel: PINHOLE CHECK (fisheye saved separately)',fill='white')
            draw.text((12,1000),f'{label} | fixed module attachment; tool collision disabled; no insertion/training claim',fill='white')
            frames.append(np.asarray(panel))
            relative_camera=np.linalg.inv(matrix(world.stage,tcp_path))@matrix(world.stage,camera_path)
            relative_module=np.linalg.inv(matrix(world.stage,tcp_path))@matrix(world.stage,module_path)
            row=dict(label=label,joint_positions=robot.get_joint_positions()[0].tolist(),
                camera_relative_matrix_error=float(np.max(np.abs(relative_camera-baseline_camera))),
                module_attachment_matrix_error=float(np.max(np.abs(relative_module-expected))),camera_cv_to_world=Twc_cv.tolist())
            rows.append(row);print('CAPTURE',label,flush=True)
        capture('closed',True)
        for phase,start,end in ([] if a.static_only else [('opening',q,target_open),('closing',target_open,q)]):
            for i in range(1,11):
                robot.set_joint_position_targets(start+(end-start)*i/10)
                for _ in range(500):world.step()
                capture(f'{phase}_{i:02d}',i==10)
        import subprocess
        encoder=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size','1792x1024','-framerate','5','-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(a.output/'jaw_preview.mp4')],stdin=subprocess.PIPE)
        for f in frames:encoder.stdin.write(f.tobytes())
        encoder.stdin.close()
        if encoder.wait():raise RuntimeError('video encoding failed')
        Image.fromarray(frames[0]).save(a.output/'preview.png')
        report=dict(tool_asset=packet['manifest']['wrist_tool_asset'],module_asset=packet['manifest']['module_visual_asset'],
            visual_tool_parts=49,visual_module_parts=17,physics_steps=round(world.time/world.dt),controlled_dof=0 if a.static_only else 2,
            joint_names=names,reference_joint_positions=q[0].tolist(),open_joint_targets=target_open[0].tolist(),
            camera_projection=projection,cube_face_size=a.face_size,frames=rows,
            max_camera_binding_error=max(x['camera_relative_matrix_error'] for x in rows),
            max_attachment_error=max(x['module_attachment_matrix_error'] for x in rows),
            handoff_projection_preserved=True,tool_collision_enabled=False,new_handle_collision_enabled=False,
            inactive_right_arm=packet['manifest'].get('inactive_right_arm'),right_arm_visibility=visibility,static_only=a.static_only,
            robot_insertion_validated=False,physical_grasp_validated=False,training_executed=False,
            scope='new assets mounted in full robot USD; limited jaw actuation/render preview; candidate fisheye, not hardware calibration')
        assert report['max_camera_binding_error']<1e-5 and report['max_attachment_error']<1e-5
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        for ann in [*cameras.values(),*cube_annots,*cube_seg]:ann.detach()
        if overview_seg:overview_seg.detach()
        for product in products:product.destroy()
    except BaseException as exc:
        failed=True;traceback.print_exc();(a.output/'failure.json').write_text(json.dumps(dict(error=repr(exc),traceback=traceback.format_exc()),indent=2)+'\n')
    finally:app._app.post_quit(1 if failed else 0);app.close()


if __name__=='__main__':main()
