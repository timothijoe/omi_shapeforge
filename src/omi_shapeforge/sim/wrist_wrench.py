"""Ideal compensated external-contact wrench, distinct from summed impulse norms.

The reference sensor axes follow TCP. Its origin is configurable in TCP metres.
This does not simulate gravity/inertial sensor load, electronics, or calibration.
PhysX contact impulses are world-space impulses on collider0; reverse for collider1.
"""
import numpy as np


class WrenchAccumulator:
    def __init__(self):self.clear()

    def clear(self):
        self.impulse=np.zeros(3);self.moment=np.zeros(3);self.contacts=0

    def add(self,position,impulse,on_first=True):
        p=np.asarray(position,float);j=np.asarray(impulse,float)*(1 if on_first else -1)
        if p.shape!=(3,) or j.shape!=(3,) or not np.isfinite(np.r_[p,j]).all():raise ValueError('invalid contact vector')
        self.impulse+=j;self.moment+=np.cross(p,j);self.contacts+=1

    def measure(self,sensor_world,interval):
        if interval<=0:raise ValueError('positive measurement interval required')
        sensor_world=np.asarray(sensor_world,float)
        r=sensor_world[:3,:3];p=sensor_world[:3,3]
        force=self.impulse/interval
        torque=(self.moment-np.cross(p,self.impulse))/interval
        return np.r_[r.T@force,r.T@torque]


def attach_wrist_wrench(env,offset_m):
    """Explicit opt-in, instance-local instrumentation; never changes control."""
    import omni.physx
    from pxr import PhysicsSchemaTools
    offset=np.asarray(offset_m,float)
    if offset.shape!=(3,) or not np.isfinite(offset).all():raise ValueError('finite sensor offset required')
    if env.packet.get('free_bodies'):raise ValueError('v1 wrist sensor supports fixed module only')
    accumulator=WrenchAccumulator()
    original_step,original_measurements=env.step,env.measurements
    def callback(headers,data):
        for h in headers:
            names=[str(PhysicsSchemaTools.intToSdfPath(h.collider0)),str(PhysicsSchemaTools.intToSdfPath(h.collider1))]
            held=['sim_module' in n for n in names]
            if sum(held)!=1 or any('grasp_pad_' in n for n in names):continue
            for contact in data[h.contact_data_offset:h.contact_data_offset+h.num_contact_data]:
                accumulator.add(contact.position,contact.impulse,on_first=held[0])
    env._wrist_subscription=omni.physx.get_physx_simulation_interface().subscribe_contact_report_events(callback)
    env._wrist_valid=False
    def measurements():
        result=original_measurements()
        sensor=env.tcp().copy();sensor[:3,3]+=sensor[:3,:3]@offset
        result.update(wrist_wrench=accumulator.measure(sensor,.1).tolist() if env._wrist_valid else [0.]*6,
            wrist_wrench_valid=env._wrist_valid,wrist_wrench_contact_points=accumulator.contacts,
            wrist_wrench_frame='tcp-aligned virtual wrist; origin=tcp+R_tcp*offset',
            wrist_wrench_kind='ideal-compensated-module-external-contact-interval-mean-v1')
        return result
    def step(action):
        accumulator.clear();env._wrist_valid=True
        return original_step(action)
    original_reset=env.reset
    def reset(*args,**kwargs):
        accumulator.clear();env._wrist_valid=False
        return original_reset(*args,**kwargs)
    env.measurements=measurements;env.step=step;env.reset=reset
    return dict(version='ideal-compensated-module-external-contact-interval-mean-v1',
        origin_offset_tcp_m=offset.tolist(),axes='TCP',units=['N']*3+['Nm']*3,interval_s=.1,
        sign='external environment wrench on held module; transferred to virtual sensor origin',
        scope='fixed module external contacts only; no gravity/inertia/electronics; not calibrated hardware wrench')
