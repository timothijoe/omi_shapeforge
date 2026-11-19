"""Bounded Isaac Sim/PhysX CPU test of a local USD scene, without the RTX renderer."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--scene', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--isaac-root', type=Path, required=True)
p.add_argument('--steps', type=int, default=240)
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
scene_path = args.scene.resolve()
root = args.isaac_root.resolve()
sys.argv = [sys.argv[0]]
from isaacsim import SimulationApp

extra = ['--/app/extensions/registryEnabled=false']
for folder in ['exts', 'extscache', 'kit/exts', 'kit/extscore']:
    extra += ['--ext-folder', str(root / folder)]
for extension in ['omni.physx', 'omni.usd', 'omni.kit.loop', 'omni.kit.usd.layers', 'omni.kit.usd.mdl']:
    extra += ['--enable', extension]
app = SimulationApp({'headless': True, 'create_new_stage': False,
                     'limit_cpu_threads': 4, 'multi_gpu': False,
                     'disable_viewport_updates': False, 'extra_args': extra}, experience=None)
code = 0
try:
    import carb.settings
    import numpy as np
    import omni.usd
    from omni.physx import get_physx_interface, get_physx_simulation_interface
    from pxr import Gf, PhysxSchema, Usd, UsdGeom, UsdPhysics, UsdUtils

    context = omni.usd.get_context()
    if not context.open_stage(str(scene_path)):
        raise RuntimeError('Could not open local scene')
    for _ in range(5):
        app.update()
    stage = context.get_stage()
    physics_prim = stage.GetPrimAtPath('/World/PhysicsScene')
    physx_scene = PhysxSchema.PhysxSceneAPI.Apply(physics_prim)
    physx_scene.CreateEnableGPUDynamicsAttr(False)
    physx_scene.CreateBroadphaseTypeAttr('MBP')
    carb.settings.get_settings().set('/physics/updateToUsd', True)
    carb.settings.get_settings().set('/physics/updateVelocitiesToUsd', True)
    bodies = [prim for prim in stage.Traverse() if prim.HasAPI(UsdPhysics.RigidBodyAPI)]
    if not bodies:
        raise RuntimeError('Scene contains no rigid bodies')

    def position(prim):
        return np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation())

    initial = [position(body) for body in bodies]
    interface = get_physx_interface()
    simulation = get_physx_simulation_interface()
    stage_id = UsdUtils.StageCache.Get().Insert(stage).ToLongInt()
    if not simulation.attach_stage(stage_id):
        raise RuntimeError('Could not attach the USD stage to PhysX')
    dt = 1 / 120
    for step in range(args.steps):
        simulation.simulate(dt, step * dt)
        simulation.fetch_results()
        interface.update_transformations(False, True, True, False)
    final = [position(body) for body in bodies]
    velocities = [np.array(UsdPhysics.RigidBodyAPI(body).GetVelocityAttr().Get()) for body in bodies]
    (args.output / 'states.json').write_text(json.dumps({
        'initial': [v.tolist() for v in initial], 'final': [v.tolist() for v in final],
        'velocities': [v.tolist() for v in velocities]}, indent=2))
    for before, after, velocity in zip(initial, final, velocities):
        if not np.isfinite(after).all() or not np.isfinite(velocity).all():
            raise RuntimeError('Non-finite body state')
        if after[2] >= before[2] - 0.01:
            raise RuntimeError('Body did not fall under gravity')
        if np.max(np.abs(velocity)) > 0.05:
            raise RuntimeError('Body did not settle')
    for body in bodies:
        collider = UsdGeom.Cube(stage.GetPrimAtPath(str(body.GetPath()) + '/CollisionBox'))
        matrix = UsdGeom.Xformable(collider).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        zs = [matrix.Transform(Gf.Vec3d(x, y, z))[2]
              for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
        if min(zs) < -0.0015 or min(zs) > 0.003:
            raise RuntimeError('Settled collision proxy is not supported by the tabletop')
    stage.GetRootLayer().Export(str(args.output / 'settled.usda'))
    report = {'status': 'passed_isaac_physx_load_step_and_settle',
              'scene': str(scene_path),
              'scene_sha256': hashlib.file_digest(scene_path.open('rb'), 'sha256').hexdigest(),
              'runner_sha256': hashlib.file_digest(Path(__file__).open('rb'), 'sha256').hexdigest(),
              'isaac_version': (root / 'VERSION').read_text().strip(),
              'simulation_backend': 'PhysX CPU', 'renderer_executed': False,
              'steps': args.steps, 'simulated_seconds': args.steps * dt,
              'initial_positions_m': [v.tolist() for v in initial],
              'final_positions_m': [v.tolist() for v in final],
              'final_linear_velocities': [v.tolist() for v in velocities],
              'collision_model': 'Bounding-box proxy; groove contacts are not represented.',
              'physical_accuracy_validated': False}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    simulation.detach_stage()
    context.close_stage()
    for _ in range(3):
        app.update()
except BaseException as exc:
    import traceback
    traceback.print_exc()
    code = 1
    (args.output / 'failure.json').write_text(json.dumps({'error': f'{type(exc).__name__}: {exc}'}, indent=2))
finally:
    app.close()
if code:
    raise SystemExit(code)
