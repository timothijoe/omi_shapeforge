"""Compare persisted scripted SAC replay with actual RPC/action trace records."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT.parent/'omi_proj/src')]
from omi_hil_rl.training.hierarchical_insertion.intervention import ScriptedInterventionSAC


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--experiment',type=Path,required=True)
    p.add_argument('--parent-trace',type=Path,action='append',default=[])
    p.add_argument('--previous-model',type=Path)
    a=p.parse_args();root=a.experiment
    model=ScriptedInterventionSAC.load(root/'system0.zip',device='cpu');model.load_replay_buffer(root/'replay.pkl');b=model.replay_buffer
    rows={}
    for path in [*a.parent_trace,root/'trace.jsonl']:
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if row['event']!='step':continue
            key=(row['seed'],row['step'])
            if key in rows:raise ValueError('duplicate transition provenance')
            rows[key]=row
    for i in range(b.size()):
        row=rows[int(b.episode_seeds[i,0]),int(b.episode_steps[i,0])]
        np.testing.assert_array_equal(b.actions[i,0],np.array(row['action'],np.float32))
        np.testing.assert_array_equal(b.proposed_actions[i,0],np.array(row['policy_action'],np.float32))
        assert bool(b.scripted[i,0])==(row['action_source']=='scripted_intervention')
        assert bool(b.dones[i,0])==bool(row['terminated'] or row['truncated'])
        assert bool(b.timeouts[i,0])==bool(row['truncated'] and not row['terminated'])
        assert abs(float(b.rewards[i,0])-row['reward'])<1e-5
        last=b.next_observations['history'][i,0].reshape(4,19)[-1]
        np.testing.assert_array_equal(last[6:12],b.actions[i,0])
        if row['wrist_wrench_valid']:
            np.testing.assert_allclose(last[12:18],np.array(row['wrist_wrench'])/[10,10,10,1,1,1],atol=1e-6)
            assert last[18]==1
    report=dict(transitions=b.size(),all_actions_and_proposals_match_trace=True,history_uses_executed_action=True,
        reward_terminal_timeout_and_wrench_verified=True,replay=b.counts(),num_timesteps=model.num_timesteps,
        sac_updates=model._n_updates,correction_updates=model.intervention_bc_updates)
    if a.previous_model:
        old=ScriptedInterventionSAC.load(a.previous_model,device='cpu');old.load_replay_buffer(a.previous_model.with_name('replay.pkl'))
        assert old.replay_buffer.size()<b.buffer_size
        np.testing.assert_array_equal(b.actions[:old.replay_buffer.size()],old.replay_buffer.actions[:old.replay_buffer.size()])
        delta=max(float((v-old.actor.state_dict()[k]).abs().max()) for k,v in model.actor.state_dict().items())
        assert delta>0
        report.update(previous_num_timesteps=old.num_timesteps,actor_parameter_max_change=delta,previous_replay_retained=True)
    (root/'replay_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
