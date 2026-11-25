"""Independent forward kinematics for the frozen scalar-joint transfer contract."""
import numpy as np

def transform(p,r):
    t=np.eye(4);t[:3,:3]=r;t[:3,3]=p
    return t

def free_module_servo_target(tcp,module,nominal_goal_tcp,nominal_tcp_module):
    """Keep the task's module goal fixed while compensating measured grasp slip."""
    measured_tcp_module=np.linalg.inv(tcp)@module
    return nominal_goal_tcp@nominal_tcp_module@np.linalg.inv(measured_tcp_module)

def bounded_contact_spin_torque(angle,speed,inertia,normal_left,normal_right,radius=.003,time_constant=.002):
    """Finite soft-finger stick torque, bounded by contact normal load times radius."""
    if min(normal_left,normal_right)<.1:return 0.,0.
    limit=radius*(normal_left+normal_right)
    stiffness=inertia/(time_constant*time_constant)
    damping=2*inertia/time_constant
    return float(np.clip(-stiffness*angle-damping*speed,-limit,limit)),float(limit)

def local_pose(item):
    w,x,y,z=np.asarray(item['quaternion'])/np.linalg.norm(item['quaternion'])
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
    return transform(item['position'],r)

def axis_rotation(axis,value):
    x,y,z=axis/np.linalg.norm(axis)
    cross=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
    return np.eye(3)+np.sin(value)*cross+(1-np.cos(value))*(cross@cross)


class Kinematics:
    def __init__(self,packet):
        self.bodies=packet['bodies'];self.joints=packet['joints']
        self.bybody={j['body']:j for j in self.joints}
        self.sites={s['name']:s for s in packet['sites']}
        # The transfer is immutable. Only q changes during a rollout. Recreate
        # Kinematics after changing body/site transforms or joint definitions.
        self._tcp_chain=None
        if 'urdf_tcp_L' not in self.sites:return
        site=self.sites['urdf_tcp_L'];self._tcp_site=local_pose(site)
        chain=[];index=site['body']
        while index:
            body=self.bodies[index];chain.append(body);index=body['parent']
        self._tcp_chain=[]
        for body in reversed(chain):
            joint=self.bybody.get(body['id']);motion=None
            if joint:
                axis=np.asarray(joint['axis'],dtype=float)
                if joint['kind']==2:motion=(joint['name'],2,axis,None,None,None)
                else:
                    pivot=np.asarray(joint['position']);x,y,z=axis/np.linalg.norm(axis)
                    cross=np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
                    motion=(joint['name'],joint['kind'],axis,pivot,cross,cross@cross)
            self._tcp_chain.append((local_pose(body),motion))
    def frames(self,q):
        ts=[np.eye(4)]
        for b in self.bodies[1:]:
            t=local_pose(b);j=self.bybody.get(b['id'])
            if j:
                value=q[j['name']];axis=np.array(j['axis'])
                if j['kind']==2:t=t@transform(axis*value,np.eye(3))
                else:
                    pivot=np.asarray(j['position']);r=axis_rotation(axis,value)
                    t=t@transform(pivot-r@pivot,r)
            ts.append(ts[b['parent']]@t)
        return ts
    def tcp(self,q):
        if self._tcp_chain is None:raise KeyError('urdf_tcp_L')
        result=np.eye(4)
        for local,motion in self._tcp_chain:
            if motion:
                name,kind,axis,pivot,cross,squared=motion;value=q[name]
                if kind==2:joint=transform(axis*value,np.eye(3))
                else:
                    rotation=np.eye(3)+np.sin(value)*cross+(1-np.cos(value))*squared
                    joint=transform(pivot-rotation@pivot,rotation)
                result=result@(local@joint)
            else:result=result@local
        return result@self._tcp_site
