"""Summarize actual learner artifacts and policy-only evaluation, including failures."""
import argparse,csv,json,hashlib,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image,ImageDraw,ImageFont,ImageSequence
    r=a.root/'study'
    read=lambda path:json.loads(path.read_text())
    dataset=read(r/'demonstrations/dataset.json');bc=read(r/'bc/report.json');rl=read(r/'rl/report.json');metrics=read(r/'rl/metrics.json');protocol=read(r/'protocol.json')
    bce=read(r/'evaluation_bc/report.json');rle=read(r/'evaluation_rl/report.json');reload=read(r/'final_reload_audit.json');receipts=read(a.root/'pipeline_receipts.json')
    required={'bc','evaluate_bc','rl','resume','evaluate_rl'}
    assert required.issubset({x['stage'] for x in receipts})
    assert all(x['returncode']==0 for x in receipts if x['stage'] in required)
    unsuccessful=[x for x in receipts if x['returncode']!=0]
    if unsuccessful:
        assert all(x['stage']=='collect' for x in unsuccessful) and protocol.get('collection_quota_revision')
        assert all(sum(e['split']==split for e in dataset['episodes'])==target for split,target in protocol['demonstration_targets'].items())
    assert all(x['teacher_requests']==0 for x in bce['cases']+rle['cases'])
    assert len(metrics)==rl['updates']==reload['updates']
    seeds=protocol['test_seeds'];count=len(seeds)
    assert [x['seed'] for x in bce['cases']]==seeds and [x['seed'] for x in rle['cases']]==seeds
    assert all(reload['network_and_optimizer_exact_reload'].values())
    result=dict(schema_version=1,experiment=a.root.name,run_root=str(a.root),protocol=protocol,
        training_samples=bc['training_samples'],validation_samples=bc['validation_samples'],bc_updates=protocol['bc_steps'],bc_selected_step=bc['selected_step'],
        critic_updates=len(metrics),actor_updates=sum('actor_loss' in x for x in metrics),
        replay_samples=reload['replay_size'],action_sources=reload['action_sources'],human_actions=0,
        online_episodes=rl['episodes'],assisted_successes=sum(x['assisted_success'] for x in rl['episodes']),
        independent_reload=reload,bc_evaluation=bce,rl_evaluation=rle,stage_receipts=receipts,
        demonstration_attempts=dataset['attempts'],initial_collection_quota_met=not unsuccessful,
        collection_quota_revision=protocol.get('collection_quota_revision'),
        pipeline_validated=True,autonomous_policy_validated=all(x['is_success'] for x in rle['cases']),physical_accuracy_validated=False,
        limitations=['Small fixed-scene study; frozen visual encoder; not a converged or real-robot policy',
            'Feedback from privileged rules, distinct from human operator labels',
            'Current visual assets with fixed attachment and uncalibrated contact/camera assumptions',
            'Clean episode-boundary resume tested; arbitrary crash recovery not claimed'],
        artifacts={str(path.relative_to(r)):dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in [r/'bc/actor.pt',r/'rl/actor.pt',r/'rl/learner.pt',r/'contract.json',r/'protocol.json']})
    (a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.output/'evaluation_comparison.csv').open('w',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['policy','seed','success','steps','depth_mm','failure','control_sample_force_max_N','substep_force_max_N','point_penetration_max_mm'])
        for label,report in [('BC',bce),('RL',rle)]:
            for case in report['cases']:
                writer.writerow([label,case['seed'],case['is_success'],case['steps'],case['depth_mm'],case['failure'],case['max_control_force_N'],case.get('max_substep_force_N'),case.get('max_point_penetration_mm')])
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    axes[0,0].semilogy([x['step'] for x in bc['history']],[x['validation_weighted_mse'] for x in bc['history']],marker='o');axes[0,0].set_title('BC validation weighted action MSE (encoder frozen)');axes[0,0].set_xlabel('BC update')
    warmup=protocol['critic_warmup']
    axes[0,1].plot([x['update'] for x in metrics],[x['critic_loss'] for x in metrics]);axes[0,1].axvline(warmup,color='gray',linestyle='--');axes[0,1].set_title(f'Actual SAC Critic loss; {warmup} warm-up updates');axes[0,1].set_xlabel('SAC update')
    episodes=rl['episodes'];pos=np.arange(len(episodes));axes[1,0].bar(pos,[x['policy_steps'] for x in episodes],label='Policy actions');axes[1,0].bar(pos,[x['intervention_steps'] for x in episodes],bottom=[x['policy_steps'] for x in episodes],label='Rule feedback');axes[1,0].set_xticks(pos,[f"seed {x['seed']}" for x in episodes]);axes[1,0].set_title(f"Assisted training: {sum(x['assisted_success'] for x in episodes)}/{len(episodes)} successful");axes[1,0].legend()
    for index,episode in enumerate(episodes):
        axes[1,0].text(index,episode['steps']+5,'OK' if episode['assisted_success'] else 'fail',ha='center',fontsize=8)
    axes[1,0].set_ylim(0,max(x['steps'] for x in episodes)*1.15)
    pos=np.arange(count);axes[1,1].bar(pos-.18,[x['depth_mm'] for x in bce['cases']],.36,label='BC');axes[1,1].bar(pos+.18,[x['depth_mm'] for x in rle['cases']],.36,label='After SAC');axes[1,1].axhline(51.2817,color='gray',linestyle='--',label='Nominal shoulder');axes[1,1].set_xticks(pos,[f'seed {seed}' for seed in seeds]);axes[1,1].set_ylabel('Final insertion depth (mm)');axes[1,1].set_title(f"No takeover: BC {sum(x['is_success'] for x in bce['cases'])}/{count}; SAC {sum(x['is_success'] for x in rle['cases'])}/{count}");axes[1,1].legend()
    for shift,report in [(-.18,bce),(.18,rle)]:
        for index,case in enumerate(report['cases']):
            axes[1,1].text(index+shift,case['depth_mm']+.5,'OK' if case['is_success'] else 'fail',ha='center',fontsize=8)
    depths=[x['depth_mm'] for x in bce['cases']+rle['cases']]
    axes[1,1].set_ylim(min(0.,min(depths))-3,max(55.,max(depths)+3))
    for ax in axes.flat:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Isaac WG-r10 / OM-r08: actual learning and separate autonomous evaluation',fontsize=14)
    fig.tight_layout();fig.savefig(a.output/'learning_summary.png',dpi=160);fig.savefig(a.output/'learning_summary.pdf');plt.close(fig)
    clips=[]
    for seed in seeds:
        for name in ['bc','rl']:
            directory=r/f'evaluation_{name}';trace=read(directory/f'trace_{seed}.json');images=[];durations=[]
            with Image.open(directory/f'policy_{seed}.gif') as gif:
                for frame in ImageSequence.Iterator(gif):images.append(frame.convert('RGB').copy());durations.append(frame.info.get('duration',100))
            clips.append(dict(seed=seed,name=name,trace=trace,images=images,times=np.cumsum(durations)))
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20)
    output=a.output/'policy_evaluation_comparison.mp4'
    height=80+count*320
    encoder=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pixel_format','rgb24','-video_size',f'1024x{height}','-framerate','10','-i','-','-an','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(output)],stdin=subprocess.PIPE)
    length=max(len(c['trace']) for c in clips)
    for t in range(length):
        image=Image.new('RGB',(1024,height),'#14202b');draw=ImageDraw.Draw(image)
        draw.text((12,8),'Isaac无接管评估：实际128px策略输入；每格左头部、右腕部',font=font,fill='white')
        for k,clip in enumerate(clips):
            col=k%2;row=k//2;x=col*512;y=50+row*320
            index=min(int(np.searchsorted(clip['times'],t*100,side='right')),len(clip['images'])-1)
            image.paste(clip['images'][index].resize((512,256),Image.Resampling.NEAREST),(x,y+28))
            data=clip['trace'][min(t,len(clip['trace'])-1)];ended=t>=len(clip['trace'])-1
            title=f"{clip['name'].upper()} / seed {clip['seed']}"+((' / 已结束：成功' if data['is_success'] else ' / 已结束：失败') if ended else '')
            if ended and not data['is_success']:
                reason={'physics_guard':'穿透保护','control_force_limit':'力越限',None:'超时'}.get(data.get('failure'),str(data.get('failure')))
                title+=' / '+reason
            draw.text((x+10,y),title,font=font,fill='#ffb1a0' if ended else 'white')
            draw.text((x+10,y+284),f"depth {data['insertion_depth_mm']:.2f} mm | force {data['contact_force_N']:.2f} N",font=font,fill='white')
        draw.text((12,height-24),'结束后保持末帧；图中力为控制采样值，小样本不证明广泛可靠性。',font=font,fill='#ffdca0')
        encoder.stdin.write(np.asarray(image).tobytes())
        if t==length-1:image.save(a.output/'evaluation_summary.png')
    encoder.stdin.close()
    if encoder.wait():raise RuntimeError('comparison video encoding failed')
    print(json.dumps({k:result[k] for k in ['training_samples','validation_samples','critic_updates','actor_updates','replay_samples','pipeline_validated','autonomous_policy_validated']}))

if __name__=='__main__':main()
