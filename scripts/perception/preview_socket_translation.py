"""Translate the unchanged socket assembly, keeping one identical robot reset."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def preview(a):
    import numpy as np
    from PIL import Image,ImageDraw
    from omi_hil_rl.training.isaac_client import IsaacClient
    from omi_hil_rl.training.hierarchical_insertion.reference import pose,tcp_pose,socket_pose
    from omi_hil_rl.training.hierarchical_insertion.system1 import image_input
    from omi_shapeforge.sim.isaac_contact_kinematics import local_pose
    from render_system1_paths import project
    from render_system1_assets import label
    packet=json.loads((a.transfer/'transfer.json').read_text());m=packet['manifest']
    cam=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    C=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(cam))
    K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    cx,cz=m['nominal_module_center_xz_mm'];point=np.array([cx,m['mouth_y_mm'],cz,1000.])/1000
    c=IsaacClient(a.output/'worker.sock');rows=[];images=[];tcp0=None;socket0=None;goal0=None
    board=Image.new('RGB',(2300,700),(246,248,251))
    label(board,(35,20),'只改变插口位置  /  同一个模型、同一个机器人起点',35,(27,39,55))
    label(board,(35,78),'插口朝向、尺寸、材质保持；绿色标记为孔口中心。位移按世界X／Y轴定义。',23,(101,118,137))
    settings=[(0,0),(a.offset_mm,0),(-a.offset_mm,0),(0,a.offset_mm),(0,-a.offset_mm)]
    try:
        for i,(dx,dy) in enumerate(settings):
            requested=dict(dx_mm=dx,dy_mm=dy,yaw_deg=0.)
            obs,info=c.reset(a.seed,socket_pose=requested)
            tcp=tcp_pose(info);socket=socket_pose(info,m);goal=np.array(info['task_goal_position'])
            native=json.loads((a.output/'worker/kinematics_check.json').read_text())
            if tcp0 is None:tcp0=tcp.copy();socket0=socket.copy();goal0=goal.copy()
            delta=(socket[:3,3]-socket0[:3,3])*1000
            np.testing.assert_allclose(delta,[dx,dy,0],atol=1e-8)
            np.testing.assert_allclose(socket[:3,:3],socket0[:3,:3],atol=1e-12)
            np.testing.assert_allclose((goal-goal0)*1000,[dx,dy,0],atol=1e-8)
            uv,valid=project((np.linalg.inv(tcp)@socket@point)[None,:3],C,K,D)
            rgb=image_input(obs);images.append(rgb)
            im=Image.fromarray(rgb[3:].transpose(1,2,0)).resize((420,420),Image.Resampling.LANCZOS)
            if valid[0]:
                u,v=(uv[0]+.5)*(420/128)-.5;d=ImageDraw.Draw(im)
                d.ellipse((u-7,v-7,u+7,v+7),outline=(20,170,95),width=3)
                d.line((u-10,v,u+10,v),fill=(20,170,95),width=2);d.line((u,v-10,u,v+10),fill=(20,170,95),width=2)
            x=35+i*452
            label(board,(x,135),'原位置' if i==0 else f'X {dx:+.0f} / Y {dy:+.0f} mm',24,(27,39,55))
            board.paste(im,(x,185));im.save(a.output/f'case_{i:02d}.png')
            item=dict(id=i,seed=a.seed,requested=requested,actual_world_delta_mm=delta.tolist(),
                robot_tcp_delta_mm=float(np.linalg.norm(tcp[:3,3]-tcp0[:3,3])*1000),
                robot_tcp_rotation_matrix_delta=float(np.max(np.abs(tcp[:3,:3]-tcp0[:3,:3]))),
                socket_position_m=socket[:3,3].tolist(),socket_rotation=socket[:3,:3].tolist(),
                goal_position_m=goal.tolist(),native_position_error_mm=native['socket_native_position_error_m']*1000,
                native_rotation_error_rad=native['socket_native_rotation_error_rad'])
            rows.append(item);write_json(a.output/f'case_{i:02d}.json',dict(summary=item,info=info,native=native))
        label(board,(35,635),'五次均使用相同机器人初始化种子；本次只检查目标位置切换，未开始训练或执行插入。',24,(101,118,137))
        board.save(a.output/'socket_translation.png')
        np.savez_compressed(a.output/'observations.npz',images=np.stack(images))
        assert max(r['robot_tcp_delta_mm'] for r in rows)<.05
        write_json(a.output/'report.json',dict(cases=rows,max_robot_tcp_delta_mm=max(r['robot_tcp_delta_mm'] for r in rows),
             source_transfer=str(a.transfer),translation_only=True,geometry_changed=False,training=False,
             recommended_runtime_options=dict(system1='gt',socket_range_mm=a.offset_mm,socket_yaw_deg=0)))
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['transfer','output','tianji-sdk']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--offset-mm',type=float,default=3.);p.add_argument('--seed',type=int,default=160000)
    a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    if not 0<a.offset_mm<=5:raise ValueError('current translation contract supports 0..5mm')
    protected={str(a.transfer/n):hashlib.sha256((a.transfer/n).read_bytes()).hexdigest() for n in ['transfer.json','meshes.npz']}
    env=dict(os.environ)
    for key in ['CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH']:env.pop(key,None)
    for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:env[key]='1'
    worker=None;failed=False;error=None
    previous={}
    def interrupt(signum,frame):raise KeyboardInterrupt(str(signum))
    for sig in [signal.SIGINT,signal.SIGTERM]:previous[sig]=signal.signal(sig,interrupt)
    try:
        worker=OwnedProcess(['/data/isaac-sim-5.1.0/python.sh','-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
            '--transfer',str(a.transfer),'--output',str(a.output/'worker'),'--socket',str(a.output/'worker.sock'),
            '--max-steps','10','--physics-substeps','5','--ik-backend','tianji','--tianji-sdk',str(a.tianji_sdk),
            '--socket-pose-range-mm',str(a.offset_mm),'--socket-yaw-range-deg','0'],directory=a.output,name='worker',env=env,cwd=ROOT)
        deadline=time.monotonic()+240
        while not (a.output/'worker.sock').exists():
            if worker.poll() is not None:raise RuntimeError('worker exited before ready')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.2)
        preview(a)
        assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in protected.items())
    except BaseException as exc:failed=True;error=repr(exc);raise
    finally:
        if worker and worker.poll() is None:
            try:
                from omi_hil_rl.training.isaac_client import IsaacClient
                c=IsaacClient(a.output/'worker.sock');c.request('shutdown');c.close()
                if worker.wait(45)!=0:failed=True
            except BaseException:failed=True;worker.stop()
        write_json(a.output/'result.json',dict(complete=not failed,error=error,worker=worker.record if worker else None,source_hashes=protected))
        for sig,handler in previous.items():signal.signal(sig,handler)


if __name__=='__main__':main()
