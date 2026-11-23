"""Pinned OpenCV fisheye ray model and six-face sampling, independent of engine."""
import numpy as np

FACES=np.array([np.eye(3),[[-1,0,0],[0,1,0],[0,0,-1]],
    [[0,0,1],[0,1,0],[-1,0,0]],[[0,0,-1],[0,1,0],[1,0,0]],
    [[1,0,0],[0,0,1],[0,-1,0]],[[1,0,0],[0,0,-1],[0,1,0]]],dtype=float)
CV_TO_GL=np.diag([1.,-1.,-1.])


def inverse_theta(radius,distortion):
    d=np.asarray(distortion);theta=np.asarray(radius,dtype=float).copy()
    for _ in range(15):
        t=theta*theta
        theta-=(theta*(1+d[0]*t+d[1]*t*t+d[2]*t**3+d[3]*t**4)-radius)/(1+3*d[0]*t+5*d[1]*t*t+7*d[2]*t**3+9*d[3]*t**4)
    return theta


def maps(projection,face_size):
    K=np.asarray(projection['K']);D=np.asarray(projection['D']);W,H=projection['image_size']
    y,x=np.indices((H,W));xn=(x-K[0,2])/K[0,0];yn=(y-K[1,2])/K[1,1];rd=np.hypot(xn,yn)
    th=inverse_theta(rd,D);scale=np.sin(th)/np.maximum(rd,1e-12)
    directions=np.stack([xn*scale,yn*scale,np.cos(th)],-1);directions[rd<1e-12]=[0,0,1]
    selected=np.argmax(directions@np.stack([f[:,2] for f in FACES]).T,axis=-1)
    result=[]
    for i,face in enumerate(FACES):
        mask=selected==i;local=directions[mask]@face
        u=np.clip((face_size-1)/2+face_size/2*local[:,0]/local[:,2],0,face_size-1.001)
        v=np.clip((face_size-1)/2+face_size/2*local[:,1]/local[:,2],0,face_size-1.001)
        result.append((mask,u,v))
    return result


def reproject(faces,sampling):
    output=np.zeros((*sampling[0][0].shape,3),np.uint8)
    for image,(mask,u,v) in zip(faces,sampling):
        ix=np.floor(u).astype(int);iy=np.floor(v).astype(int);wx=(u-ix)[:,None];wy=(v-iy)[:,None]
        image=np.asarray(image,dtype=float)
        pixels=image[iy,ix,:3]*(1-wx)*(1-wy)+image[iy,ix+1,:3]*wx*(1-wy)+image[iy+1,ix,:3]*(1-wx)*wy+image[iy+1,ix+1,:3]*wx*wy
        output[mask]=np.rint(pixels).clip(0,255).astype(np.uint8)
    return output
