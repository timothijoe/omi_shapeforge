"""One real PhysX episode: visibly misaligned, align outside, then insert.

Preparation uses normal RPC actions. Preserve its prefix separately, and film
the contiguous suffix beginning at the settled misaligned state. No teleport,
task modification, learned policy or training is involved.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from omi_shapeforge.sim.isaac_ipc import send, receive
from omi_shapeforge.sim.isaac_contact_kinematics import transform,free_module_servo_target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--transfer',type=Path,default=Path('/data/shapeforge/runtime/runs/staged_contact_20261123/robot_transfer'))
    p.add_argument('--asset-contract',choices=['legacy-r10','wva01-gc01-free-grasp-v1','wva01-closed-reference-fixture-v1'],default='legacy-r10')
    p.add_argument('--physics-substeps',type=int,choices=[5,20,100,500],default=5)
    p.add_argument('--physics-device',choices=['cpu','gpu'],default='cpu')
    p.add_argument('--solver',choices=['PGS','TGS'],default=None)
    p.add_argument('--grasp-smoke-only',action='store_true')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    transfer = a.transfer
    manifest = json.loads((transfer/'transfer.json').read_text())['manifest']
    sock_path = a.output/'worker.sock'
    if len(str(sock_path).encode())>=100:
        sock_path=Path('/tmp')/f'omi-grasp-{os.getpid()}-{uuid.uuid4().hex[:8]}.sock'
    command = ['/data/isaac-sim-5.1.0/python.sh', '-u', str(ROOT/'scripts/simulation/isaac_rl_worker.py'),
               '--transfer', str(transfer), '--output', str(a.output/'worker'), '--socket', str(sock_path),
               '--max-steps', '1800', '--physics-substeps',str(a.physics_substeps), '--physics-device',a.physics_device, '--no-render',
               '--teacher-min-step-mm', '.05', '--target-overtravel-mm', '.1', '--entry-guidance',
               '--asset-contract',a.asset_contract,'--ik-backend', 'tianji', '--tianji-sdk', str(ROOT.parent/'omi_proj/local/vendor/optical_module_pu/source/OpticalModule_PU/Arm_control')]
    command+=['--solver',a.solver or ('TGS' if a.asset_contract=='wva01-gc01-free-grasp-v1' else 'PGS')]
    (a.output/'command.json').write_text(json.dumps(command, indent=2))
    environment = dict(os.environ)
    for k in ('PYTHONPATH', 'PYTHONHOME', 'CONDA_PREFIX', 'CONDA_DEFAULT_ENV', 'LD_LIBRARY_PATH'):
        environment.pop(k, None)
    for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        environment[k] = '1'
    log = (a.output/'worker.log').open('wb')
    worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
    sock = None
    def request(command, **kwargs):
        send(sock, dict(command=command, **kwargs))
        reply, arrays = receive(sock)
        if not reply.get('ok'):
            raise RuntimeError(reply)
        assert not arrays, 'This diagnostic intentionally records physics only; rendering follows separately.'
        return reply
    try:
        deadline = time.monotonic()+180
        while not sock_path.exists():
            if worker.poll() is not None:
                raise RuntimeError(f'worker exited {worker.returncode}')
            if time.monotonic() > deadline:
                raise TimeoutError('worker startup')
            time.sleep(.2)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(180)
        sock.connect(str(sock_path))
        meta = request('hello')['metadata']
        assert meta['rendered'] is False
        assert meta['transfer_sha256'] == hashlib.sha256((transfer/'transfer.json').read_bytes()).hexdigest()
        info = request('reset', seed=94000)['info']
        if a.grasp_smoke_only:
            assert a.asset_contract!='legacy-r10'
            states=[]
            for _ in range(20):
                state=request('step',action=[0.]*6)['info'];states.append(state)
                if state['failed']:break
            held=all(s['grasp_held'] and not s['failed'] for s in states)
            before=np.array(states[-1]['world_from_module'])[:3,3]
            request('grasp',closed=False)
            released=request('step',action=[0.]*6)['info'] if held else None
            drop=float(before[2]-np.array(released['world_from_module'])[2,3]) if released else 0.
            result=dict(held=held,hold_states=states,released_state=released,release_drop_m=drop,
                        accepted=bool(held and not released['grasp_held'] and drop>.001))
            (a.output/'grasp_smoke.json').write_text(json.dumps(result,indent=2))
            print('GRASP_SMOKE',held,'drop_m',drop,flush=True)
            if not result['accepted']:raise RuntimeError('grasp hold/release smoke failed')
            return
        identity, goal = info['episode'], info['task_goal_position']
        rotation = np.asarray(manifest['socket_to_world']['rotation'])
        axis, side, up = -rotation[:, 1], rotation[:, 0], rotation[:, 2]
        outside = np.asarray(manifest['preinsert_tcp_position'])-axis*.012
        aligned_rotation = np.asarray(manifest['goal_tcp_rotation'])
        misaligned_position = outside+side*.008+up*.003
        misaligned_rotation = Rotation.from_rotvec(up*np.deg2rad(2.5)).as_matrix()@aligned_rotation
        scale = np.array([.001/np.sqrt(3)]*3+[np.pi/180/np.sqrt(3)]*3)
        previous = np.zeros(6)
        all_rows = []
        case = a.output/'case'
        case.mkdir()

        def step(action, phase):
            nonlocal info, previous
            reply = request('step', action=np.asarray(action, dtype=float).tolist())
            info = reply['info']
            assert info['episode'] == identity and info['task_goal_position'] == goal
            assert info['step'] == len(all_rows)+1
            assert not info['failed'] and not info['truncated'], info
            previous = np.asarray(action).copy()
            row = dict(info, showcase_phase=phase)
            all_rows.append(row)
            with (case/'all_states.jsonl').open('a') as stream:
                stream.write(json.dumps(row)+'\n')
            return row

        def move(target, target_rotation, phase):
            nonlocal previous
            previous = np.zeros(6)
            for _ in range(450):
                R = np.asarray(info['tcp_rotation'])
                actual_target,actual_rotation=target,target_rotation
                if phase=='aligning' and info.get('world_from_module') is not None:
                    current_tcp=transform(np.asarray(info['tcp_position']),R)
                    nominal=transform(np.asarray(manifest['tool_to_module']['position_m']),np.asarray(manifest['tool_to_module']['rotation']))
                    desired=free_module_servo_target(current_tcp,np.asarray(info['world_from_module']),
                                                     transform(target,target_rotation),nominal)
                    actual_target,actual_rotation=desired[:3,3],desired[:3,:3]
                angular = .5*sum(np.cross(R[:, j], actual_rotation[:, j]) for j in range(3))
                error = np.r_[actual_target-info['tcp_position'], angular]
                desired = np.clip(error/scale, -.85, .85)
                action = previous+np.clip(desired-previous, -.3, .3)
                row = step(action, phase)
                if np.linalg.norm(np.asarray(info['tcp_position'])-actual_target) < .00004 and Rotation.from_matrix(R@actual_rotation.T).magnitude() < .0002:
                    return row
            raise RuntimeError(f'{phase} target not reached')

        move(outside, aligned_rotation, 'preparation_retreat')
        move(misaligned_position, misaligned_rotation, 'preparation_offset')
        for _ in range(3):
            initial = step(np.zeros(6), 'misaligned')
        assert initial['insertion_depth_mm'] < -10
        assert initial['lateral_error_mm'] > 10
        assert initial['alignment_angle_rad'] > np.deg2rad(2)
        start = len(all_rows)-1
        print('MISALIGNED', initial['step'], initial['lateral_error_mm'], initial['insertion_depth_mm'], flush=True)
        move(outside, aligned_rotation, 'aligning')
        assert info['insertion_depth_mm'] < 0 and info['lateral_error_mm'] < .1
        assert info['alignment_angle_rad'] < .0015
        aligned_step = info['step']
        for _ in range(5):
            step(np.zeros(6), 'aligned')
        print('ALIGNED', aligned_step, info['lateral_error_mm'], flush=True)
        for _ in range(1000):
            action = np.asarray(request('teacher')['action'])
            row = step(action, 'approaching' if info['insertion_depth_mm'] < 0 else 'inserting')
            if info['step']%100 == 0:
                print('STEP', info['step'], round(info['insertion_depth_mm'], 3), flush=True)
            if row['is_success']:
                row['showcase_phase'] = 'seated'
                break
        assert info['is_success'] and info['entry_qualified'] and info['stable_samples'] >= 3
        selected = all_rows[start:]
        (case/'trajectory.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in selected))
        report = dict(success=True, seed=94000, source='real PhysX / scripted geometric controller',
                      total_physics_steps=len(all_rows), video_states=len(selected), reset_count=1,
                      video_start_source_step=initial['step'], aligned_source_step=aligned_step,
                      initial_lateral_error_mm=initial['lateral_error_mm'],
                      initial_angle_deg=float(np.rad2deg(initial['alignment_angle_rad'])),
                      initial_depth_mm=initial['insertion_depth_mm'], final_depth_mm=info['insertion_depth_mm'],
                      nominal_offset_mm=[8, 3], nominal_yaw_deg=2.5, retreat_extra_mm=12,
                      network_inference=False, training=False, setup_prefix_preserved=True)
        (case/'report.json').write_text(json.dumps(report, indent=2))
        print('COMPLETE', json.dumps(report), flush=True)
    finally:
        if sock is not None:
            try:
                request('shutdown')
            finally:
                sock.close()
        code = worker.wait(timeout=60)
        (a.output/'worker_exit.json').write_text(json.dumps(dict(returncode=code)))
        log.close()
        if code:
            raise RuntimeError(f'worker exited {code}')


if __name__ == '__main__':
    main()
