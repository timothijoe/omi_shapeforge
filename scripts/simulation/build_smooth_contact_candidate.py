"""Derive a continuous guide collision candidate; never alter source assets.

The visual meshes are retained. These six native box proxies encode the
user's entrance-obstruction / smooth-interior hypothesis, not measured mechanics.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    protected = {str(source / n): digest(source / n) for n in ('transfer.json', 'meshes.npz')}
    packet = json.loads((source / 'transfer.json').read_text())
    original = copy.deepcopy(packet)
    with np.load(source / 'meshes.npz', allow_pickle=False) as archive:
        arrays = {key: archive[key] for key in archive.files}
    assert digest(source / 'meshes.npz') == packet['meshes_sha256']
    ids = {b['name']: b['id'] for b in packet['bodies']}
    manifest = packet['manifest']
    # Use the measured nominal 18.8 x 8.8 mm throat, without the unmeasured
    # internal support that previously reduced vertical clearance to 0.096 mm.
    width, height, center_x, center_z = 18.8, 8.8, -.3, .3
    mouth = manifest['mouth_y_mm']
    tip = manifest['leading_tip_y_mm']
    shoulder = tip + manifest['shoulder_depth_mm']
    retired = []
    for geom in packet['geoms']:
        if geom['contact'] and (geom['body'] in (ids['sim_module'], ids['sim_socket'])
                                or geom['name'].startswith('pad_contact_')):
            geom['contact'] = False
            retired.append(geom['name'])
    authored = []

    def box(name, body, lower, upper):
        lower, upper = np.asarray(lower)/1000, np.asarray(upper)/1000
        packet['geoms'].append(dict(name=name, body=ids[body], kind=6, mesh=-1,
            size=((upper-lower)/2).tolist(), position=((upper+lower)/2).tolist(),
            quaternion=[1.,0.,0.,0.], rgba=[.5,.5,.5,1.], contact=True,
            group=3, friction=[.2,.001,.0001]))
        authored.append(name)

    # Explicit planar envelope and mouth: no assumed chamfer or mesh cooking.
    box('sim_module_smooth_shaft', 'sim_module', [-9.05,tip,-4.1], [9.05,shoulder,4.1])
    box('sim_module_smooth_shoulder', 'sim_module', [-10.1, shoulder, -4.9],
        [10.1, shoulder+2., 4.9])
    # Keep the shaft's validated narrow contact distance. Only the shoulder
    # needs a wider, fixed reporting envelope for stable stop detection.
    packet['geoms'][-1]['contact_offset_m'] = 5e-6
    # Each wall is one box. No depth-dependent filtering or collision disabling.
    for dim, half, center, labels in (
            (0, width/2, center_x, ('left', 'right')),
            (2, height/2, center_z, ('bottom', 'top'))):
        for sign, label in zip((-1, 1), labels):
            lower = [center_x-width/2-1.5, -60., center_z-height/2-1.5]
            upper = [center_x+width/2+1.5, mouth, center_z+height/2+1.5]
            lower[dim], upper[dim] = sorted((center+sign*half,center+sign*(half+1.5)))
            box('sim_socket_smooth_'+label, 'sim_socket', lower, upper)
    old_center = np.asarray(manifest['nominal_module_center_xz_mm'])
    new_center = np.array([center_x, center_z])
    local_shift = np.array([new_center[0]-old_center[0], 0., new_center[1]-old_center[1]])/1000
    socket_rotation = np.asarray(packet['bodies'][ids['sim_socket']]['world_rotation'])
    world_shift = socket_rotation @ local_shift
    robot = any(j['name'] == 'Arm_L1_Joint' for j in packet['joints'])
    if robot:
        for key in ('goal_tcp_position', 'seated_tcp_position', 'preinsert_tcp_position'):
            manifest[key] = (np.asarray(manifest[key])+world_shift).tolist()
    else:
        body = packet['bodies'][ids['sim_module']]
        assert body['parent'] == 0
        for key in ('position', 'world_position'):
            body[key] = (np.asarray(body[key])+world_shift).tolist()
    manifest['nominal_module_center_xz_mm'] = new_center.tolist()
    # The shoulder stops on any of the four mouth faces. Requiring only the
    # upper face falsely rejects a slightly tilted plate seated on bottom/side.
    manifest['contact_shoulder_pair'] = ['sim_module_smooth_shoulder', 'sim_socket_smooth_']
    manifest['asset_id'] = 'SIM-SMOOTH-GUIDE-candidate-r04'
    manifest['joint_target_interpolation'] = 'linear'
    manifest['contact_candidate'] = dict(
        status='uncalibrated behavioural candidate', source=str(source),
        module_envelope_mm=[18.1, manifest['shoulder_depth_mm'], 8.2],
        throat_mm=[width, height], radial_clearance_mm=[.35, .3],
        nominal_center_shift_world_m=world_shift.tolist(),
        inlet_bevel_axial_mm=0., inlet_bevel_radial_mm=0.,
        module_tip_chamfer_axial_mm=0., module_tip_chamfer_radial_mm=0.,
        collision_representation='six native PhysX boxes; planar entrance and guide, no convex mesh cooking',
        friction=.2, force_calibrated=False, physical_pad_model=False,
        shaft_and_wall_contact_offset_m=1e-7, shoulder_contact_offset_m=5e-6,
        retired_collision_geoms=retired, authored_collision_geoms=authored,
        visual_geometry_changed=False, old_pad_bodies_retained_but_not_contacts=True,
        collisions_always_enabled=True, training_executed=False)
    packet['limitations'].append('Smooth guide: native box envelopes and planar mouth are hypotheses; no calibrated electrical contacts or latch force')
    # All prior geom poses/materials/vertices survive. Only contact flags change.
    for old, new in zip(original['geoms'], packet['geoms']):
        assert {k: v for k, v in old.items() if k != 'contact'} == {k: v for k, v in new.items() if k != 'contact'}
    output.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output/'meshes.npz', **arrays)
    packet['meshes_sha256'] = digest(output/'meshes.npz')
    (output/'transfer.json').write_text(json.dumps(packet, indent=2)+'\n')
    assert all(digest(path) == sha for path, sha in protected.items())
    report = dict(source_sha256=protected, source_unchanged=True,
                  transfer_sha256=digest(output/'transfer.json'),
                  candidate=manifest['contact_candidate'], robot=robot,
                  total_colliders=sum(g['contact'] for g in packet['geoms']))
    (output/'candidate.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != 'candidate'}))
