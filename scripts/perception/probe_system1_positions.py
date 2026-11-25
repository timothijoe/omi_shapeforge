"""Move a simulated robot to nine held-out pre-entry poses and inspect System1.

Ordinary IK/PhysX steps prepare each pose; the frozen model only predicts references.
No predicted path is executed. Existing policy and worker defaults are unchanged.
"""
import argparse,hashlib,json,os,signal,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src'),str(Path(__file__).parent)]
from omi_shapeforge.sim.process_supervisor import OwnedProcess,write_json


def probe(args):
    import numpy as np
    import torch
    from PIL import Image,ImageDraw
    from omi_hil_rl.training.isaac_client import IsaacClient
    from omi_hil_rl.training.hierarchical_insertion.reference import pose,tcp_pose,socket_pose,log_rotation
    from omi_hil_rl.training.hierarchical_insertion.system1 import VisualPredictor,image_input
    from omi_shapeforge.sim.isaac_contact_kinematics import local_pose
    from render_system1_paths import references,camera_panel,scene_panel,transform,lines,text,BG,FG,MUTED,GT,PRED,CURRENT
    torch.set_num_threads(2)
    packet=json.loads((args.transfer/'transfer.json').read_text());m=packet['manifest']
    digest=hashlib.sha256((args.transfer/'transfer.json').read_bytes()).hexdigest()
    predictor=VisualPredictor(args.checkpoint,digest)
    socket=args.output/'worker.sock'
    client=IsaacClient(socket,digest)
    camera=next(c for c in packet['cameras'] if c['name']=='wrist_rgb')
    cam=np.diag([1.,-1.,-1.,1.])@np.linalg.inv(local_pose(camera))
    K=np.array(m['observation_projection']['K']);D=np.array(m['observation_projection']['D'])
    tip=pose(m['tool_to_module']['position_m'],m['tool_to_module']['rotation'])@np.array([0,m['leading_tip_y_mm']/1000,0,1.])
    R=np.array(m['socket_to_world']['rotation']);axis=-R[:,1]
    scale=np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
    rows=[];record=[];images=[];predictions=[];truths=[];paths=[]
    board=Image.new('RGB',(1560,1550),BG)
    text(board,(30,18),'同一个 System1 · 九个机器人起点',32)
    text(board,(30,69),'插座固定｜机器人经实际IK / PhysX移动｜橙：预测短段  绿：GT参考  紫：当前尖端',20,MUTED)
    text(board,(30,105),'左右 / 上下各 −3、0、+3 mm；孔口前约8 mm。冻结模型测试，预测路径未执行。',19,MUTED)
    try:
        for z in (3.,0.,-3.):
            for x in (-3.,0.,3.):
                idx=len(rows);seed=130000+idx
                if seed in predictor.used_seeds:raise ValueError('test seed overlaps training')
                obs,info=client.reset(seed)
                target=np.array(m['preinsert_tcp_position'])+R[:,0]*x/1000+R[:,2]*z/1000-axis*.003
                goalR=np.array(m['goal_tcp_rotation']);previous=np.zeros(6)
                trace=[];reached=False
                for step in range(140):
                    current=tcp_pose(info)
                    err=np.r_[target-current[:3,3],log_rotation(goalR@current[:3,:3].T)]
                    if np.linalg.norm(err[:3])<.00005 and np.linalg.norm(err[3:])<.0005:
                        reached=True;break
                    desired=np.clip(err/scale,-.5,.5);action=(previous+np.clip(desired-previous,-.2,.2)).astype(np.float32);previous=action
                    obs,reward,term,trunc,info=client.step(action)
                    trace.append(dict(step=step,action=action.tolist(),tcp_position=info['tcp_position'],depth_mm=info['insertion_depth_mm']))
                    if term or trunc:break
                if not reached:raise RuntimeError(f'failed physical setup at {(x,z)}')
                for _ in range(3):
                    obs,_,term,trunc,info=client.step(np.zeros(6,np.float32))
                    if term or trunc:raise RuntimeError('setup terminated during hold')
                current=tcp_pose(info);gt_world=socket_pose(info,m)
                predicted_world=predictor(obs,current)
                gt=np.linalg.inv(current)@gt_world;predicted=np.linalg.inv(current)@predicted_world
                gp,gf=references(m,gt,tip);pp,pf=references(m,predicted,tip)
                error=float(np.linalg.norm(predicted[:3,3]-gt[:3,3])*1000)
                angle=float(np.rad2deg(np.linalg.norm(log_rotation(gt[:3,:3].T@predicted[:3,:3]))))
                pe=float(np.linalg.norm(pp-gp,axis=1).mean()*1000)
                row=dict(seed=seed,index=0,image=image_input(obs),gt_socket=gt,pred_socket=predicted,gt=gp,pred=pp,full_gt=gf,full_pred=pf,translation_mm=error,path_error_mm=pe)
                rows.append(row);images.append(row['image']);predictions.append(predicted);truths.append(gt);paths.append(pp)
                item=dict(id=idx,seed=seed,requested_lateral_mm=x,requested_vertical_mm=z,target_tcp_m=target.tolist(),actual_tcp_m=current[:3,3].tolist(),
                    setup_position_error_mm=float(np.linalg.norm(current[:3,3]-target)*1000),actual_depth_mm=info['insertion_depth_mm'],
                    translation_error_mm=error,rotation_error_deg=angle,preview_tip_error_mm=pe,teacher_requests=info.get('teacher_requests',0),prediction_executed=False)
                record.append(item);print(json.dumps(item),flush=True)
                write_json(args.output/f'case_{idx:02d}.json',dict(summary=item,setup_trace=trace))
                col=idx%3;rowid=idx//3;left=30+col*510;top=165+rowid*450
                text(board,(left,top),f'起点 {idx+1}   左右 {x:+.0f} / 上下 {z:+.0f} mm',20)
                board.paste(camera_panel(row,cam,K,D,tip).resize((245,245)),(left,top+45))
                board.paste(scene_panel(row,tip,m).resize((245,245)),(left+250,top+45))
                text(board,(left,top+305),f'位姿误差 {error:.2f} mm   短段差 {pe:.2f} mm',19)
                text(board,(left,top+342),f'实际入口前距离 {-info["insertion_depth_mm"]:.2f} mm',17,MUTED)
                board.save(args.output/'nine_positions.png')
        # Unified 3D plot: all nine actual starts, same socket coordinate system.
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.font_manager import FontProperties
        font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
        fig=plt.figure(figsize=(12,9));ax=fig.add_subplot(111,projection='3d')
        def task(t,points):
            q=transform(np.linalg.inv(t),points)*1000
            return np.column_stack([q[:,0],m['mouth_y_mm']-q[:,1],q[:,2]])
        for i,r in enumerate(rows):
            for key,color,style in [('gt','#15966b','--'),('pred','#ef8e20','-')]:
                q=task(r['gt_socket'],r[key]);ax.plot(*q.T,color=color,linestyle=style,marker='o',markersize=3,label=('GT参考' if key=='gt' else '模型预测') if i==0 else None)
            q=task(r['gt_socket'],tip[None,:3])[0];ax.scatter(*q,color='#9260c8');ax.text(*q,str(i+1),fontproperties=font)
        w=m['channel_width_mm']/2;h=m['channel_height_mm']/2;cx,cz=m['nominal_module_center_xz_mm']
        q=np.array([[cx-w,0,cz-h],[cx+w,0,cz-h],[cx+w,0,cz+h],[cx-w,0,cz+h],[cx-w,0,cz-h]])
        ax.plot(*q.T,color='#15966b',alpha=.4)
        ax.set_xlim(-10,10);ax.set_ylim(-12,2);ax.set_zlim(-6,6);ax.set_box_aspect((20,14,12));ax.view_init(elev=24,azim=-63)
        ax.set_xlabel('左右 X / mm',fontproperties=font);ax.set_ylabel('插入深度 / mm',fontproperties=font);ax.set_zlabel('上下 Z / mm',fontproperties=font)
        ax.set_title('九个实际起点的 System1 短段参考\n插座坐标系 · 模型未针对这些位置重训',fontproperties=font,fontsize=16)
        ax.legend(prop=font);fig.savefig(args.output/'paths_3d.png',dpi=150,bbox_inches='tight');plt.close(fig)
        np.savez_compressed(args.output/'samples.npz',images=np.stack(images),predicted_socket=np.stack(predictions),target_socket=np.stack(truths),predicted_tip_path=np.stack(paths))
        write_json(args.output/'report.json',dict(cases=record,checkpoint=str(args.checkpoint),checkpoint_sha256=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
            mean_translation_error_mm=float(np.mean([r['translation_error_mm'] for r in record])),max_translation_error_mm=max(r['translation_error_mm'] for r in record),
            scope='nine physically reached pre-entry test poses; frozen visual model; no predicted-path execution or insertion success claim'))
    finally:client.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--transfer',type=Path,required=True)
    p.add_argument('--tianji-sdk',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    sock=a.output/'worker.sock'
    if len(str(sock))>=104:raise ValueError('socket path too long')
    env=dict(os.environ)
    for k in ('CONDA_PREFIX','CONDA_DEFAULT_ENV','PYTHONHOME','PYTHONPATH','LD_LIBRARY_PATH'):env.pop(k,None)
    for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):env[k]='1'
    worker=None;failed=False;error=None
    previous={}
    def stop(signum,frame):raise KeyboardInterrupt(str(signum))
    for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.signal(sig,stop)
    try:
        worker=OwnedProcess(['/data/isaac-sim-5.1.0/python.sh','-u',str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
            '--transfer',str(a.transfer.resolve()),'--output',str(a.output/'worker'),'--socket',str(sock),'--max-steps','200','--physics-substeps','5',
            '--ik-backend','tianji','--tianji-sdk',str(a.tianji_sdk.resolve()),'--teacher-min-step-mm','.05','--target-overtravel-mm','.1'],directory=a.output,name='worker',env=env,cwd=ROOT)
        deadline=time.monotonic()+240
        while not sock.exists():
            if worker.poll() is not None:raise RuntimeError('worker exited')
            if time.monotonic()>deadline:raise TimeoutError('worker startup')
            time.sleep(.2)
        probe(a)
    except BaseException as exc:failed=True;error=repr(exc);raise
    finally:
        if worker and worker.poll() is None:
            try:
                from omi_hil_rl.training.isaac_client import IsaacClient
                c=IsaacClient(sock);c.request('shutdown');c.close();code=worker.wait(45)
                if code:failed=True
            except BaseException:failed=True;worker.stop()
        write_json(a.output/'result.json',dict(complete=not failed,error=error,worker=worker.record if worker else None))
        for sig,handler in previous.items():signal.signal(sig,handler)
if __name__=='__main__':main()
