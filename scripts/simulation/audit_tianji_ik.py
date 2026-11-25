"""Audit native Tianji IK against an immutable transfer, without Isaac or hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
import numpy as np
from omi_shapeforge.sim.tianji_ik import TianjiIK, ARM_NAMES, pose_error
from omi_shapeforge.sim.isaac_contact_kinematics import axis_rotation


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--transfer', type=Path, required=True)
    p.add_argument('--tianji-sdk', type=Path, required=True)
    p.add_argument('--tianji-config', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    source = a.transfer/'transfer.json'
    k = TianjiIK(json.loads(source.read_text()), a.tianji_sdk, a.tianji_config)
    rng = np.random.default_rng(20261125)
    errors = [];timings = [];failures = [];steps = []
    for sample in range(500):
        q = dict(k.initial)
        q.update({n:q[n]+rng.uniform(-.02, .02) for n in ARM_NAMES})
        target = k.kin.tcp(q)
        target[:3, 3] += rng.uniform(-.0005, .0005, 3)
        axis = rng.normal(size=3)
        target[:3, :3] = axis_rotation(axis, rng.uniform(-.005, .005)) @ target[:3, :3]
        start = time.perf_counter()
        try:result = k.solve(q, target)
        except Exception as exc:
            failures.append(dict(sample=sample, error=repr(exc)));continue
        timings.append((time.perf_counter()-start)*1000)
        errors.append(pose_error(k.kin.tcp(result), target))
        steps.append(max(abs(result[n]-q[n]) for n in ARM_NAMES))
    report = dict(transfer=str(source.resolve()), transfer_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        sdk_directory=str(a.tianji_sdk.resolve()), metadata=k.metadata, samples=500, successes=len(errors), failures=failures,
        max_position_error_mm=max((e[0]*1000 for e in errors), default=None),
        max_rotation_error_rad=max((e[1] for e in errors), default=None),
        max_joint_step_rad=max(steps, default=None),
        solve_ms=dict(mean=float(np.mean(timings)), median=float(np.median(timings)), p95=float(np.percentile(timings, 95))) if timings else None,
        communication_library_loaded='libMarvinSDK' in Path('/proc/self/maps').read_text(),
        scope='offline world-delta targets near insertion pose; no collision or hardware validation')
    (a.output/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if failures or report['communication_library_loaded']:raise SystemExit(1)


if __name__ == '__main__':main()
