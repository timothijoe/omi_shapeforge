"""Offline Tianji CCS left-arm IK, in the transfer's world/metre/radian contract.

Loads only fx_kine.py/libKine.so. No robot transport or hardware initialization.
The vendor library owns process-global arm slots; this adapter serializes access
and reinstalls its math configuration when a different adapter uses that slot.
"""
import ctypes
import hashlib
import importlib.util
from pathlib import Path
import threading

import numpy as np

from .isaac_contact_kinematics import Kinematics, axis_rotation, local_pose, transform


_LOCK = threading.RLock()
_ACTIVE = None
ARM_NAMES = tuple(f'Arm_L{i}_Joint' for i in range(1, 8))


class IKError(RuntimeError):
    """Rejected target/solution; callers must not send a joint command."""


def rigid(value):
    value = np.asarray(value, dtype=float)
    if (value.shape != (4, 4) or not np.isfinite(value).all()
            or not np.allclose(value[3], [0, 0, 0, 1], atol=1e-9, rtol=0)
            or not np.allclose(value[:3, :3].T @ value[:3, :3], np.eye(3), atol=1e-6, rtol=0)
            or abs(np.linalg.det(value[:3, :3])-1) > 1e-6):
        raise ValueError('finite rigid 4x4 pose required')
    return value.copy()


def pose_error(a, b):
    # Chordal SO(3) distance remains accurate near zero and at pi.
    angle = 2*np.arcsin(np.clip(np.linalg.norm(a[:3, :3]-b[:3, :3])/(2*np.sqrt(2)), 0, 1))
    return float(np.linalg.norm(a[:3, 3]-b[:3, 3])), float(angle)


def mdh(row):
    alpha, a, d, theta = row
    rx = axis_rotation(np.array([1., 0, 0]), np.deg2rad(alpha))
    rz = axis_rotation(np.array([0., 0, 1]), np.deg2rad(theta))
    return transform([a/1000, 0, 0], rx) @ transform([0, 0, d/1000], rz)


class TianjiIK:
    version = 'tianji-ccs-left-world-v1'
    position_tolerance_m = 1e-5
    rotation_tolerance_rad = 1e-4
    max_joint_step_rad = .1

    def __init__(self, packet, sdk_directory, config_path=None):
        self.kin = Kinematics(packet)
        self.joints = {j['name']: j for j in packet['joints']}
        self.initial = {j['name']: packet['initial_qpos'][j['qpos_index']] for j in packet['joints']}
        sdk = Path(sdk_directory).resolve()
        config = Path(config_path).resolve() if config_path else sdk/'ccs_m6_40.MvKDCfg'
        files = [sdk/'fx_kine.py', sdk/'libKine.so', config]
        self.hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        spec = importlib.util.spec_from_file_location('_shapeforge_tianji_math', files[0])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.parameters = module.FX_InvKineSolvePara
        with _LOCK:
            global _ACTIVE
            _ACTIVE = None
            self.sdk = module.Marvin_Kine()
            self.sdk.log_switch(0)
            self.config = self.sdk.load_config(0, str(config))
            if not self.config or self.config['TYPE'][0] != 1017:
                raise ValueError('adapter requires Tianji CCS model 1017, left arm 0')
            # load_config itself touches the global slot: invalidate on every load.
            self._activate()
        self.world_from_base, self.flange_from_tcp = self._mapping(packet)
        self.base_from_world = np.linalg.inv(self.world_from_base)
        self.tcp_from_flange = np.linalg.inv(self.flange_from_tcp)
        self.validation = self._audit_mapping()
        self.metadata = dict(version=self.version, arm=0, model_type=1017,
            joint_names=list(ARM_NAMES), joint_signs=[1]*7, joint_zero_offsets_rad=[0]*7,
            input_units='world metres / joint radians', sdk_units='base millimetres / joint degrees',
            world_from_base=self.world_from_base.tolist(), flange_from_tcp=self.flange_from_tcp.tolist(),
            source_sha256=self.hashes, position_tolerance_m=self.position_tolerance_m,
            rotation_tolerance_rad=self.rotation_tolerance_rad, max_joint_step_rad=self.max_joint_step_rad,
            singularity_policy='reject any SDK singular flag', fallback='none', mapping_validation=self.validation)

    def _activate(self):
        global _ACTIVE
        if _ACTIVE is self:
            return
        c = self.config
        if not self.sdk.initial_kine(c['TYPE'][0], c['DH'][0], c['PNVA'][0], c['BD'][0]):
            raise IKError('SDK math initialization failed')
        if not self.sdk.set_tool_kine(np.eye(4).tolist()) or not self.sdk.set_user_frame_kine(np.eye(4).tolist()):
            raise IKError('SDK identity tool/user-frame initialization failed')
        _ACTIVE = self

    def _mapping(self, packet):
        bodies = packet['bodies']
        ids = [self.joints[n]['body'] for n in ARM_NAMES]
        for index, name in enumerate(ARM_NAMES):
            joint = self.joints[name]
            if (joint['kind'] != 3 or not np.allclose(joint['axis'], [0, 0, 1])
                    or not np.allclose(joint['position'], 0)
                    or (index and bodies[ids[index]]['parent'] != ids[index-1])):
                raise ValueError('unsupported left-arm joint order/axis/pivot')
        parent = bodies[ids[0]]['parent']
        ancestors = parent
        while ancestors:
            if ancestors in self.kin.bybody:
                raise ValueError('moving arm base is not supported')
            ancestors = bodies[ancestors]['parent']
        world_parent = self.kin.frames(self.initial)[parent]
        base = world_parent @ local_pose(bodies[ids[0]]) @ np.linalg.inv(mdh(self.config['DH'][0][0]))
        site = self.kin.sites['urdf_tcp_L']
        tail = local_pose(site)
        index = site['body']
        while index != ids[-1]:
            if not index or index in self.kin.bybody:
                raise ValueError('TCP must be a fixed descendant of left joint 7')
            tail = local_pose(bodies[index]) @ tail
            index = bodies[index]['parent']
        return rigid(base), rigid(np.linalg.inv(mdh(self.config['DH'][0][7])) @ tail)

    def _reference(self, q):
        values = np.array([q[n] for n in ARM_NAMES], dtype=float)
        limits = np.array([self.joints[n]['limits'] for n in ARM_NAMES])
        if not np.isfinite(values).all() or np.any(values < limits[:, 0]) or np.any(values > limits[:, 1]):
            raise IKError('reference joints invalid or outside transfer limits')
        return values

    def fk(self, q):
        values = self._reference(q)
        with _LOCK:
            self._activate()
            result = self.sdk.fk(np.rad2deg(values).tolist())
        if result is False or result is None:
            raise IKError('SDK FK failed')
        result = rigid(result)
        result[:3, 3] /= 1000
        return self.world_from_base @ result @ self.flange_from_tcp

    def _audit_mapping(self):
        rng = np.random.default_rng(20261124)
        limits = np.array([self.joints[n]['limits'] for n in ARM_NAMES])
        poses = [self._reference(self.initial), np.zeros(7)]
        poses.extend(rng.uniform(limits[:, 0]*.9, limits[:, 1]*.9, (64, 7)))
        errors = []
        for values in poses:
            q = dict(self.initial)
            q.update(zip(ARM_NAMES, values))
            errors.append(pose_error(self.fk(q), self.kin.tcp(q)))
        maxima = np.max(errors, axis=0)
        if maxima[0] > self.position_tolerance_m or maxima[1] > self.rotation_tolerance_rad:
            raise IKError(f'SDK/transfer FK mismatch: {maxima.tolist()} (metres, radians)')
        return dict(samples=len(poses), max_position_error_m=float(maxima[0]), max_rotation_error_rad=float(maxima[1]))

    def solve(self, q, target_world):
        """Return a new full q mapping. Never clamp, silently fall back, or mutate q."""
        target_world = rigid(target_world)
        reference = self._reference(q)
        target = self.base_from_world @ target_world @ self.tcp_from_flange
        target[:3, 3] *= 1000
        sp = self.parameters()
        sp.set_input_ik_target_tcp(target.ravel().tolist())
        sp.set_input_ik_ref_joint(np.rad2deg(reference).tolist())
        sp.set_input_ik_zsp_type(0)  # SDK NEAR_REF redundancy mode
        with _LOCK:
            self._activate()
            ok = self.sdk.kine.FX_Robot_Kine_IK(ctypes.c_int32(self.sdk.robot_tag), ctypes.byref(sp))
        if not ok or sp.m_Output_IsOutRange or sp.m_Output_IsJntExd or any(sp.m_Output_IsDeg):
            raise IKError(f'SDK IK rejected: ok={ok}, unreachable={bool(sp.m_Output_IsOutRange)}, '
                          f'joint_limit={bool(sp.m_Output_IsJntExd)}, singular={list(sp.m_Output_IsDeg)}')
        result = dict(q)
        result.update(zip(ARM_NAMES, np.deg2rad(sp.m_Output_RetJoint.to_list()).tolist()))
        values = self._reference(result)
        if np.max(np.abs(values-reference)) > self.max_joint_step_rad:
            raise IKError('SDK solution exceeds 0.1 rad per-control joint continuity bound')
        error = pose_error(self.kin.tcp(result), target_world)
        if error[0] > self.position_tolerance_m or error[1] > self.rotation_tolerance_rad:
            raise IKError(f'SDK solution fails transfer FK backcheck: {error} (metres, radians)')
        return result
