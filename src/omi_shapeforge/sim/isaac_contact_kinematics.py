"""Independent forward kinematics for the frozen scalar-joint transfer contract."""
import numpy as np

def transform(p,r):
    t=np.eye(4);t[:3,:3]=r;t[:3,3]=p
    return t

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
        s=self.sites['urdf_tcp_L'];return self.frames(q)[s['body']]@local_pose(s)
