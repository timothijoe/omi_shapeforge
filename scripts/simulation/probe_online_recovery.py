"""Exercise the training RPC/gate with synthetic proposals, not a learned policy.

Start isaac_rl_worker with the staged input, rendered RGB, max-steps 900,
teacher-min-step-mm .05 and target-overtravel-mm .1. Outputs are append-only
per run; all fault injection uses ordinary accepted actions after one reset.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT.parent / 'omi_proj/src')]
from omi_hil_rl.training.isaac_client import IsaacClient, make_contract
from omi_hil_rl.training.isaac_intervention import Gate
from omi_shapeforge.sim.isaac_contact_approach import limit_approach


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--transfer', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    cases = [('normal', 800, 0.), ('recovery_plus', 801, 1.), ('recovery_minus', 802, -1.)]
    protocol = dict(cases=cases, max_steps=900, reset_per_case=1,
                    policy='synthetic geometric proposals; no learned actor or training',
                    fault_injection='normal RPC actions; gate enabled after actual entrance obstruction',
                    acceptance='normal seating with zero teacher queries; both recovery sequences and handback before seating',
                    transfer=str(args.transfer.resolve()))
    (args.output / 'protocol.json').write_text(json.dumps(protocol, indent=2) + '\n')
    snapshot = args.output / 'code_snapshot'; snapshot.mkdir()
    sources = [Path(__file__), ROOT.parent / 'omi_proj/src/omi_hil_rl/training/isaac_client.py',
               ROOT.parent / 'omi_proj/src/omi_hil_rl/training/isaac_intervention.py',
               ROOT / 'src/omi_shapeforge/sim/isaac_contact_approach.py']
    for path in sources:shutil.copy2(path, snapshot / path.name)
    (args.output / 'source_hashes.json').write_text(json.dumps(
        {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}, indent=2) + '\n')
    manifest = json.loads((args.transfer / 'transfer.json').read_text())['manifest']
    axis = -np.asarray(manifest['socket_to_world']['rotation'])[:, 1]
    side = np.asarray(manifest['socket_to_world']['rotation'])[:, 0]
    outside = np.asarray(manifest['preinsert_tcp_position'])
    goal_rotation = np.asarray(manifest['goal_tcp_rotation'])
    scale = np.array([.001 / np.sqrt(3)] * 3 + [np.pi / 180 / np.sqrt(3)] * 3)
    env = IsaacClient(args.socket, hashlib.sha256((args.transfer / 'transfer.json').read_bytes()).hexdigest())
    reports = []
    try:
        contract = make_contract(args.transfer, env.metadata, 900)
        assert contract['recovery_controller']['version'] == 'retreat-align-reenter-v1'
        config = contract['execution_config']
        assert config['teacher_min_step_mm'] == .05 and config['target_overtravel_mm'] == .1
        (args.output / 'contract.json').write_text(json.dumps(contract, indent=2) + '\n')
        for name, seed, offset_mm in cases:
            directory = args.output / name; directory.mkdir()
            obs, info = env.reset(seed)
            assert info['step'] == 0 and obs['history_mask'].sum() == 1
            assert not obs['state'].any() and not obs['tactile'].any()
            task_goal = np.asarray(info['task_goal_position'])
            episode = info['episode']
            previous = np.zeros(6)
            rows = []; seen = set(); handback = False; gate = Gate()
            phase = 'offset_outside' if offset_mm else 'finish'
            blocked_step = None
            def save_frame(label):
                rgb = np.concatenate([obs[k][-1].transpose(1, 2, 0) for k in ('rgb', 'wrist_rgb')], axis=1)
                Image.fromarray(rgb).save(directory / (label + '.png'))
            save_frame('initial')
            for _ in range(900):
                if phase == 'offset_outside':target = outside + side * offset_mm / 1000
                elif phase == 'approach_offset':target = outside + axis * .004 + side * offset_mm / 1000
                elif phase in ('push_offset', 'blocked_without_teacher'):
                    target = np.asarray(manifest['seated_tcp_position']) - axis * ((manifest['shoulder_depth_mm'] - 3.) / 1000) + side * offset_mm / 1000
                else:target = task_goal
                current_rotation = np.asarray(info['tcp_rotation'])
                error = np.r_[target - info['tcp_position'],
                              .5 * sum(np.cross(current_rotation[:, i], goal_rotation[:, i]) for i in range(3))]
                desired = np.clip(error / scale, -.85, .85)
                proposal = previous + np.clip(desired - previous, -.3, .3)
                if phase == 'push_offset':proposal = np.clip(proposal, -.05, .05)
                if phase == 'blocked_without_teacher':proposal = np.zeros(6)
                if phase in ('recover', 'finish'):
                    proposal, _ = limit_approach(proposal, scale, axis,
                        manifest['shoulder_depth_mm'] - info['insertion_depth_mm'], 'insert', minimum_mm=.05)
                audit = {}
                if phase == 'recover':
                    action, source, audit = gate.choose(env, info, proposal)
                    if source == 'policy':
                        handback = True
                        assert info['recovery_completed'] == 1 and info['entry_qualified']
                        source = 'synthetic_probe'
                else:action, source = proposal, 'synthetic_probe'
                old = info
                obs, reward, term, trunc, info = env.step(np.asarray(action, np.float32))
                previous = np.asarray(action)
                np.testing.assert_array_equal(np.asarray(info['executed_action'], np.float32), np.asarray(action, np.float32))
                np.testing.assert_array_equal(info['task_goal_position'], task_goal)
                assert info['episode'] == episode and info['step'] == len(rows) + 1
                assert info['simulation_time_ns'] == old['simulation_time_ns'] + 100_000_000
                expected = -10 * np.linalg.norm(task_goal - info['tcp_position']) - .5 * info['alignment_angle_rad']
                assert abs(expected - info['reward_terms']['potential_after']) < 1e-10
                row = dict(info, probe_phase=phase, action_source=source, gate_audit=audit, reward=reward)
                rows.append(row)
                with (directory / 'trajectory.jsonl').open('a') as stream:stream.write(json.dumps(row) + '\n')
                stage = info['recovery_stage']
                if stage not in seen:
                    seen.add(stage); save_frame(stage)
                    print(name, 'stage', stage, 'step', info['step'], 'depth', info['insertion_depth_mm'], flush=True)
                if info['failed'] or trunc:break
                if phase in ('offset_outside', 'approach_offset') and np.linalg.norm(target - info['tcp_position']) < .00008:
                    phase = 'approach_offset' if phase == 'offset_outside' else 'push_offset'
                    previous = np.zeros(6)
                elif phase == 'push_offset' and info.get('recovery_required'):
                    assert info['insertion_depth_mm'] < 2 and info['step_any_module_contact']
                    blocked_step = info['step']; phase = 'blocked_without_teacher'; save_frame('blocked')
                elif phase == 'blocked_without_teacher' and info['step'] >= blocked_step + 3:
                    assert info['teacher_requests'] == 0 and not info['recovery_active']
                    phase = 'recover'; previous = np.zeros(6)
                if info['step'] % 100 == 0:print(name, phase, info['step'], info['insertion_depth_mm'], flush=True)
                if term:break
            save_frame('final')
            accepted = bool(info['is_success'] and not info['failed'])
            if offset_mm:
                accepted &= (seen >= {'retreat', 'align_outside', 'reinsert'} and handback and info['recovery_completed'] == 1)
                assert not any(r['is_success'] for r in rows if r['recovery_active'])
            else:accepted &= info['teacher_requests'] == 0
            report = dict(case=name, seed=seed, offset_mm=offset_mm, accepted=accepted,
                          reset_count=1, steps=len(rows), success=info['is_success'], failure=info['failure'],
                          final_depth_mm=info['insertion_depth_mm'], recovery_completed=info['recovery_completed'],
                          handback=handback, stages=sorted(seen), blocked_step=blocked_step,
                          teacher_requests=info['teacher_requests'], learned_policy_evaluated=False,
                          max_mean_force_N=max(r['contact_force_mean_N'] for r in rows),
                          max_substep_force_N=max(r['step_peak_contact_force_N'] for r in rows))
            reports.append(report)
            (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            (args.output / 'summary.json').write_text(json.dumps(dict(cases=reports, accepted=all(r['accepted'] for r in reports)), indent=2) + '\n')
            print('RESULT', json.dumps(report), flush=True)
        if not all(r['accepted'] for r in reports):raise RuntimeError('one or more preregistered cases failed')
    finally:
        env.close()


if __name__ == '__main__':main()
