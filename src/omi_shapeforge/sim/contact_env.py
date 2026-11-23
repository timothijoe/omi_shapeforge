"""Real-URDF insertion with live optical contact and two rendered cameras."""
import mujoco
import numpy as np

from .vision_env import DualCameraPreinsertEnv


class ContactInsertionEnv(DualCameraPreinsertEnv):
    task_id = "sim-contact-insertion-v1"

    def __init__(self, scene_dir, render_mode=None, max_steps=500):
        super().__init__(scene_dir, render_mode, max_steps)
        self.module_id = self.model.body("sim_module").id
        self.socket_id = self.model.body("sim_socket").id
        self.pad_qids = np.array([self.model.jnt_qposadr[self.model.joint(f"pad_slide_{i}").id] for i in range(7)])
        self._rest_pad_gaps_mm = np.asarray(self.manifest.get("pad_rest_static_gap_mm", [.4] * 7), dtype=float)
        self._nominal_module_center_xz = np.asarray(self.manifest.get("nominal_module_center_xz_mm", [-.5, .7]), dtype=float) / 1000
        self.phase = "insert"
        self._stable = 0
        self._is_module=np.array([self.model.geom(i).name.startswith('sim_module') for i in range(self.model.ngeom)])
        self._step_peak_penetration_mm=0.
        self._step_min_floor_gap_mm=float(self._rest_pad_gaps_mm.min())

    def _advance_physics(self,count):
        self._step_peak_penetration_mm=0.
        self._step_min_floor_gap_mm=float(self._rest_pad_gaps_mm.min())
        for _ in range(count):
            mujoco.mj_step(self.model,self.data)
            self._step_min_floor_gap_mm=min(self._step_min_floor_gap_mm,float(np.min(self._rest_pad_gaps_mm-self.data.qpos[self.pad_qids]*1000)))
            if self.data.ncon:
                # Include pad/socket contacts as well as module contacts.
                self._step_peak_penetration_mm=max(self._step_peak_penetration_mm,float(-np.min(self.data.contact.dist)*1000))

    def measurements(self):
        Rs = self.data.xmat[self.socket_id].reshape(3,3)
        Rm = self.data.xmat[self.module_id].reshape(3,3)
        local = Rs.T @ (self.data.xpos[self.module_id] - self.data.xpos[self.socket_id])
        relative_rotation = Rs.T @ Rm
        tip = local + relative_rotation @ [0., self.manifest["leading_tip_y_mm"]/1000, 0.]
        depth = self.manifest["mouth_y_mm"] - tip[1]*1000
        lateral = float(np.linalg.norm(local[[0,2]] - self._nominal_module_center_xz))
        angle = float(np.arccos(np.clip((np.trace(relative_rotation)-1)/2,-1,1)))
        shoulder, pad_contact, force, penetration = False, False, 0., 0.
        for i,c in enumerate(self.data.contact):
            names=[self.model.geom(int(g)).name for g in c.geom]
            if any(n.startswith("sim_module") for n in names):
                penetration=max(penetration,float(-c.dist*1000))
                f=np.zeros(6);mujoco.mj_contactForce(self.model,self.data,i,f);force+=float(np.linalg.norm(f[:3]))
                shoulder |= any(n.startswith("sim_module_006_collision") for n in names) and any(n.startswith("sim_socket_008_collision") for n in names)
                pad_contact |= any(n.startswith("pad_contact") for n in names)
        return dict(insertion_depth_mm=float(depth), lateral_error_mm=lateral*1000, alignment_angle_rad=angle,
                    shoulder_contact=bool(shoulder), pad_contact=bool(pad_contact), contact_force_N=force,
                    penetration_mm=penetration, pad_travel_mm=(self.data.qpos[self.pad_qids]*1000).tolist())

    def reset(self, *, seed=None, options=None):
        self.phase, self._stable = "insert", 0
        if options is None:
            options={'joint_offset':np.random.default_rng(seed).uniform(-.0005,.0005,7)}
        obs,info=super().reset(seed=seed,options=options)
        info.update(self.measurements(),contacts_enabled=True,asset_id=self.manifest['asset_id'])
        return obs,info

    def _info(self):
        return dict(super()._info(),contacts_enabled=True,asset_id=self.manifest['asset_id'])

    def begin_withdrawal(self):
        """Continue physics from seated state for a separate withdrawal audit."""
        if not self._finished or self.phase != "insert" or self._stable < 3:
            raise RuntimeError("withdrawal audit requires a completed stable insertion")
        self.phase="withdraw"
        self.goal_pos=np.array(self.manifest['preinsert_tcp_position'])
        self._steps,self._stable,self._finished=0,0,False

    def step(self,action):
        obs,_,_,_,info=super().step(action)
        m=self.measurements()
        if self.phase=='insert':
            settled=(abs(m['insertion_depth_mm']-self.manifest['shoulder_depth_mm'])<.15 and
                     m['lateral_error_mm']<.35 and m['alignment_angle_rad']<.01 and m['shoulder_contact'])
        else:
            settled=(m['insertion_depth_mm'] < -4.8 and np.linalg.norm(self._error()[:3])<.0003)
        self._stable=self._stable+1 if settled else 0
        success=self._stable>=3
        failed=self._step_peak_penetration_mm>.05 or self._step_min_floor_gap_mm<.025 or not np.isfinite(self.data.qpos).all()
        truncated=self._steps>=self.max_steps and not(success or failed)
        terminated=bool(success or failed)
        self._finished=bool(terminated or truncated)
        error=float(np.linalg.norm(self._error()[:3]))
        reward=-error*10 - .001 + float(success) - float(failed)
        info.update(m,is_success=bool(success),phase=self.phase,stable_samples=self._stable,
                    step_peak_penetration_mm=self._step_peak_penetration_mm,step_min_floor_gap_mm=self._step_min_floor_gap_mm,
                    task=self.task_id,contacts_enabled=True,failure="excess_penetration" if failed else None)
        return obs,float(reward),terminated,bool(truncated),info
