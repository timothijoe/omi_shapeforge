"""Actual zero-time RTX capture for insertion-rule demonstrations.

This module is imported only after SimulationApp. Images are rendered from the
current PhysX state, never from target joints or generated imagery.
"""
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import Gf, UsdGeom
import omni.replicator.core as rep

from .wrist_fisheye import inverse_theta


class RuleDemoRecorder:
    phases={
        'preview':'初始姿态预览（不计测试）',
        'initial':'开始：预插入姿态',
        'offset_outside':'实验准备：设置入口外偏差',
        'approach_offset_outside':'保持偏差，靠近入口',
        'push_misaligned':'偏置试探：检查入口是否挡住',
        'retreat_same_offset':'已受阻：保持偏置退回',
        'align_outside':'入口外重新对准',
        'enter_guide':'对准后进入导向段',
        'slide_with_contact':'内部轻擦并继续前进',
        'insert_aligned':'对准后插入／末端稳定',
        'withdraw_aligned':'到位后退出',
    }

    def __init__(self,world,env,packet,audit,output):
        self.world,self.env=world,env
        self.output=Path(output)
        self.frames=0;self.hold_frames=0;self.last=None;self.closed=False
        rotation=np.asarray(packet['manifest']['socket_to_world']['rotation'])
        position=np.asarray(packet['manifest']['socket_to_world']['position_m'])
        eye=position+rotation@np.array([.12,.07,.06])
        target=position+rotation@np.array([0.,-.010,.001])
        camera=UsdGeom.Camera.Define(world.stage,'/World/RuleDemoClose')
        camera.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(*eye),Gf.Vec3d(*target),Gf.Vec3d(0,0,1)).GetInverse())
        camera.CreateFocalLengthAttr(28.)
        camera.CreateHorizontalApertureAttr(24.)
        camera.CreateVerticalApertureAttr(18.)
        camera.CreateClippingRangeAttr(Gf.Vec2f(.001,20.))
        rep.settings.set_render_rtx_realtime(antialiasing='DLAA')
        self.products=[];self.annotators={}
        specs={'close':('/World/RuleDemoClose',(960,720)),
               'overview':(audit['cameras']['overview'],(480,360)),
               'wrist_front':(audit['cameras']['wrist_rgb'],(1024,1024))}
        for name,(path,size) in specs.items():
            product=rep.create.render_product(path,size);self.products.append(product)
            ann=rep.AnnotatorRegistry.get_annotator('rgb');ann.attach(product);self.annotators[name]=ann
        projection=packet['manifest']['observation_projection']
        k=np.asarray(projection['K']);distortion=np.asarray(projection['D'])
        x,y=np.meshgrid(np.linspace(766,1154,480),np.linspace(566,954,480))
        xn=(x-k[0,2])/k[0,0];yn=(y-k[1,2])/k[1,1];rd=np.hypot(xn,yn)
        theta=inverse_theta(rd,distortion);factor=np.sin(theta)/np.maximum(rd,1e-12)
        rays=np.stack([xn*factor,yn*factor,np.cos(theta)],-1)
        assert np.all(rays[:,:,2]>np.max(np.abs(rays[:,:,:2]),axis=2))
        u=511.5+512*rays[:,:,0]/rays[:,:,2];v=511.5+512*rays[:,:,1]/rays[:,:,2]
        self.ix=np.floor(u).astype(int);self.iy=np.floor(v).astype(int)
        self.wx=(u-self.ix)[...,None];self.wy=(v-self.iy)[...,None]
        assert self.ix.min()>=0 and self.iy.min()>=0 and self.ix.max()<1023 and self.iy.max()<1023
        font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
        self.font=ImageFont.truetype(font,22);self.small=ImageFont.truetype(font,19)
        self.metadata=dict(fps=10,width=1440,height=960,renderer='actual Isaac RTX, zero simulation time during capture',
            close_eye_world=eye.tolist(),close_target_world=target.tolist(),
            wrist_projection=projection,wrist_roi=[766,566,1155,955],wrist_front_resolution=1024,
            wrist_display_resolution=480,views=['close','overview','fisheye_wrist_roi'],
            teacher='scripted privileged controller, not learned policy',pose_invariance_checked=True)
        (self.output/'recording.json').write_text(json.dumps(self.metadata,indent=2)+'\n')
        self.encoder=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24',
            '-video_size','1440x960','-framerate','10','-i','-','-an','-c:v','libx264',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(self.output/'demo.mp4')],stdin=subprocess.PIPE)
        for _ in range(3):self.render_checked()
        world.stage.GetRootLayer().Export(str(self.output/'recording_scene.usda'))

    def render_checked(self):
        positions=self.env.robot.get_joint_positions().copy()
        velocities=self.env.robot.view.get_dof_velocities().copy()
        time=self.world.time
        self.world.render()
        np.testing.assert_allclose(self.env.robot.get_joint_positions(),positions,atol=1e-9,rtol=0)
        np.testing.assert_allclose(self.env.robot.view.get_dof_velocities(),velocities,atol=1e-9,rtol=0)
        assert self.world.time==time

    def capture(self,row,phase):
        self.render_checked()
        views={name:ann.get_data()[:,:,:3].astype(np.uint8) for name,ann in self.annotators.items()}
        assert all(x.ndim==3 and x.shape[2]==3 and x.std()>1 for x in views.values())
        front=views['wrist_front'].astype(float);ix,iy,wx,wy=self.ix,self.iy,self.wx,self.wy
        wrist=np.rint(front[iy,ix]*(1-wx)*(1-wy)+front[iy,ix+1]*wx*(1-wy)+front[iy+1,ix]*(1-wx)*wy+front[iy+1,ix+1]*wx*wy).clip(0,255).astype(np.uint8)
        panel=Image.new('RGB',(1440,960),'#14202b');draw=ImageDraw.Draw(panel)
        panel.paste(Image.fromarray(views['close']),(0,80))
        panel.paste(Image.fromarray(views['overview']),(960,80))
        panel.paste(Image.fromarray(wrist),(960,440))
        title=self.phases.get(phase,phase)
        if row.get('is_success') and phase=='insert_aligned':title+='  —  已稳定到位'
        elif row.get('failed'):title+='  —  失败／保护停止'
        elif row.get('recovery_required'):title+='  —  检测到受阻'
        draw.text((16,8),'Isaac实际仿真｜规则控制｜WG-r10＋OM-r08｜右臂水平停放',font=self.font,fill='white')
        draw.text((16,42),title,font=self.font,fill='#ffdd8c')
        draw.text((16,810),f"深度 {row['insertion_depth_mm']:.3f} mm   横偏 {row['lateral_error_mm']:.3f} mm   姿态误差 {np.degrees(row['alignment_angle_rad']):.3f}°",font=self.font,fill='white')
        draw.text((16,845),f"平均接触指标 {row['contact_force_mean_N']:.3f} N   子步峰值 {row['step_peak_contact_force_N']:.2f} N",font=self.font,fill='white')
        draw.text((16,880),f"任务阶段：{row.get('contact_phase','尚未更新')}   入口资格：{'已通过' if row.get('entry_qualified') else '未通过'}   控制步 {row.get('step',0)}",font=self.font,fill='white')
        draw.text((16,930),'左：插口近景｜右上：机械臂全景｜右下：腕部鱼眼ROI｜力为仿真接触指标，非真机净插入力',font=self.small,fill='#d7dde5')
        array=np.asarray(panel);self.encoder.stdin.write(array.tobytes());self.frames+=1;self.last=array.copy()
        if self.frames==1:panel.save(self.output/'preview.png')
        if row.get('is_success') and phase=='insert_aligned':panel.save(self.output/'seated.png')
        with (self.output/'render_audit.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(frame=self.frames,control_step=row.get('step',0),phase=phase,simulation_time_s=self.world.time,pose_unchanged=True))+'\n')

    def close(self,accepted=False):
        if self.closed:return
        self.closed=True
        if self.last is not None:
            Image.fromarray(self.last).save(self.output/'last_frame.png')
            for _ in range(15):self.encoder.stdin.write(self.last.tobytes());self.hold_frames+=1
        self.encoder.stdin.close()
        code=self.encoder.wait(timeout=60)
        self.metadata.update(captured_frames=self.frames,display_only_hold_frames=self.hold_frames,
                             encoder_exit_code=code,task_accepted=accepted)
        (self.output/'recording.json').write_text(json.dumps(self.metadata,indent=2)+'\n')
        if code:raise RuntimeError(f'video encoder failed: {code}')
