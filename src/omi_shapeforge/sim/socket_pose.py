"""Episode-local planar socket placement, independent of robot and policy state."""
from copy import deepcopy
from dataclasses import asdict, dataclass
import math

import numpy as np

from .isaac_contact_kinematics import transform


@dataclass(frozen=True)
class SocketPoseRange:
    translation_mm: float = .5
    yaw_deg: float = .2

    def __post_init__(self):
        if not math.isfinite(self.translation_mm) or not 0 <= self.translation_mm <= 5:
            raise ValueError('socket planar translation range must be within 0..5 mm')
        if not math.isfinite(self.yaw_deg) or not 0 <= self.yaw_deg <= 2:
            raise ValueError('socket yaw range must be within 0..2 degrees')

    def resolve(self, seed, value=None):
        if value is None:
            rng = np.random.default_rng(int(seed) ^ 0x50C0E7)
            value = dict(dx_mm=float(rng.uniform(-self.translation_mm, self.translation_mm)),
                         dy_mm=float(rng.uniform(-self.translation_mm, self.translation_mm)),
                         yaw_deg=float(rng.uniform(-self.yaw_deg, self.yaw_deg)))
        if set(value) != {'dx_mm', 'dy_mm', 'yaw_deg'}:
            raise ValueError('socket pose requires dx_mm, dy_mm, yaw_deg')
        result = {k:float(v) for k,v in value.items()}
        if not all(math.isfinite(v) for v in result.values()):
            raise ValueError('finite socket pose required')
        if (abs(result['dx_mm']) > self.translation_mm or abs(result['dy_mm']) > self.translation_mm
                or abs(result['yaw_deg']) > self.yaw_deg):
            raise ValueError('socket pose exceeds registered range')
        return result

    def contract(self):
        return dict(version='planar-socket-assembly-v1', **asdict(self), plane='world XY, fixed world Z',
                    rotation='world Z yaw about nominal socket origin', distribution='uniform per-axis at reset',
                    robot_initialization='original joint reset and jitter; not co-transformed',
                    policy_pose_input=False)


def relocate_socket_manifest(nominal, pose):
    """Return a fresh manifest and a common world transform for socket/pads.

    Relative tool/module geometry and socket-local assessment thresholds stay
    fixed. Always derive from the original manifest, never the previous reset.
    """
    center = np.asarray(nominal['socket_to_world']['position_m'], dtype=float)
    yaw = math.radians(pose['yaw_deg']);c,s = math.cos(yaw),math.sin(yaw)
    rotation = np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])
    delta = np.array([pose['dx_mm']/1000, pose['dy_mm']/1000, 0.])
    world_change = transform(center+delta-rotation@center, rotation)
    manifest = deepcopy(nominal)
    for name in ('goal_tcp_position','preinsert_tcp_position','seated_tcp_position'):
        manifest[name] = (rotation@np.asarray(nominal[name])+world_change[:3,3]).tolist()
    manifest['goal_tcp_rotation'] = (rotation@np.asarray(nominal['goal_tcp_rotation'])).tolist()
    manifest['socket_to_world'] = dict(position_m=(center+delta).tolist(),
        rotation=(rotation@np.asarray(nominal['socket_to_world']['rotation'])).tolist())
    manifest['episode_socket_pose'] = dict(pose)
    return manifest, world_change
