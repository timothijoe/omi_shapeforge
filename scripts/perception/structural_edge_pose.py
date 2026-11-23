"""Marker-free structural line observations and a local rigid-pose prototype.

The printed patch is erased BEFORE gradients are computed, and its surrounding
band is excluded from matching. Search regions and face are explicit priors for
this wrist/grasp view. This is not general object detection or metrology.
"""
from pathlib import Path
import json
import cv2
import numpy as np
import open3d as o3d
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


class StructuralModel:
    def __init__(self,inputs):
        self.inputs=Path(inputs);manifest=json.loads((self.inputs/'manifest.json').read_text())
        self.parts={p['file']:p for p in manifest['module']['parts']};self.arrays={}
        for filename in ['000.npz','001.npz','002.npz','003.npz','004.npz','006.npz','007.npz','008.npz','010.npz','014.npz']:
            d=np.load(self.inputs/'module'/filename);self.arrays[filename]=(d['vertices']/1000,d['faces'])
        shaft=self.arrays['014.npz'][0];head=self.arrays['006.npz'][0];cap=self.arrays['007.npz'][0]
        lines={};sources={}
        for label,sign in [('left',1),('right',-1)]:
            x=shaft[:,0].max() if sign>0 else shaft[:,0].min()
            z=shaft[np.isclose(shaft[:,0],x,atol=1e-8),2].max()
            lines['shaft_'+label]=np.array([[x,-.025,z],[x,.003,z]]);sources['shaft_'+label]='014.npz'
            x=head[:,0].max() if sign>0 else head[:,0].min()
            z=head[np.isclose(head[:,0],x,atol=1e-8),2].max()
            q=head[np.isclose(head[:,0],x,atol=1e-8)&np.isclose(head[:,2],z,atol=1e-8)]
            lines['head_'+label]=np.array([[x,q[:,1].min()+.0005,z],[x,q[:,1].max()-.0005,z]]);sources['head_'+label]='006.npz'
        z=cap[:,2].min();y=cap[np.isclose(cap[:,2],z,atol=1e-8),1].max()
        lines['black_cap_bottom']=np.array([[-.005,y,z],[.005,y,z]]);sources['black_cap_bottom']='007.npz'
        self.lines=lines;self.sources=sources
        self.vertices=np.concatenate([v for v,_ in self.arrays.values()])
        self.scene=o3d.t.geometry.RaycastingScene(nthreads=4)
        for vertices,faces in self.arrays.values():
            m=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(vertices),o3d.utility.Vector3iVector(faces))
            self.scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(m))

    def catalogue(self):
        result=[]
        for name,points in self.lines.items():
            v,f=self.arrays[self.sources[name]];scene=o3d.t.geometry.RaycastingScene(nthreads=2)
            scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v),o3d.utility.Vector3iVector(f))))
            samples=np.linspace(points[0],points[1],50).astype(np.float32)
            maximum=float(scene.compute_distance(o3d.core.Tensor(samples)).numpy().max()*1000)
            if maximum>.015:raise ValueError((name,'feature line not on source mesh',maximum))
            result.append({'id':name,'part':self.parts[self.sources[name]]['name'],'endpoints_model_m':points.tolist(),'max_distance_to_source_mesh_mm':maximum,'physical_geometry_accuracy_verified':False})
        top=head=self.arrays['006.npz'][0];ztop=top[:,2].max();ytop=top[np.isclose(top[:,2],ztop,atol=1e-8),1].min()
        return {'active_lines':result,'head_shoulder_candidate':{'part':'006.npz','plane_y_m':float(ytop),'z_m':float(ztop),'enabled_for_fit':False,'reason':'Not independently identifiable in current wrist view; printed patch/low contrast can hide it'},
                'tip_notch_candidates':{'part':'014.npz','region':'Y < -26 mm','enabled_for_fit':False,'reason':'Not reliably observed near the socket; no occlusion boundary used as a notch'},
                'black_cap_step_2d':{'enabled_for_fit':False,'reason':'Observed line can be tracked in 2D; its exact CAD correspondence is not verified'},
                'excluded':['added black-white printed patch','green pull accessory','flexible spring/contact features'],
                'units':'m','mesh_scale_changed':False}


class StructuralDetector:
    def __init__(self,calibration,require_ownership=True):
        self.K=np.array(calibration['K'],float);self.D=np.array(calibration['D'],float)
        self.require_ownership=require_ownership
        # Explicit known-view search prior, in ORIGINAL 1920x1080 pixels.
        self.regions={'shaft_left':([934,688,954,726],True,12),'shaft_right':([990,688,1010,726],True,12),
                      'head_left':([930,734,943,769],True,12),'head_right':([1003,734,1017,769],True,12),
                      'black_cap_bottom':([949,797,998,817],False,20),
                      'black_cap_step_2d':([949,779,998,794],False,15)}
        self.exclude_polygon=np.array([[949,736],[995,735],[999,760],[946,763]],np.int32)

    def exclusion_mask(self,shape):
        mask=np.zeros(shape[:2],np.uint8);cv2.fillConvexPoly(mask,self.exclude_polygon,255)
        return cv2.dilate(mask,np.ones((9,9),np.uint8))

    def detect(self,image,ownership=None):
        if image.shape[:2]!=(1080,1920):raise ValueError('This known-view detector requires original 1920x1080 pixels')
        if ownership is None and self.require_ownership:
            raise ValueError('Module/cap/gripper ownership masks are required; ROI membership alone is not a structural correspondence')
        exclude=self.exclusion_mask(image.shape);clean=image.copy();clean[exclude>0]=128
        gray=cv2.cvtColor(clean,cv2.COLOR_BGR2GRAY);smooth=cv2.GaussianBlur(gray,(3,3),.7)
        edges=cv2.Canny(smooth,25,65);edges[cv2.dilate(exclude,np.ones((5,5),np.uint8))>0]=0
        gx=cv2.Sobel(smooth,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(smooth,cv2.CV_32F,0,1,ksize=3)
        if ownership is not None:
            for key in ['metal','cap','gripper']:
                if np.asarray(ownership[key]).shape!=image.shape[:2]:raise ValueError('Ownership mask shape mismatch')
            gripper_margin=cv2.dilate(ownership['gripper'].astype(np.uint8),np.ones((3,3),np.uint8))>0
            hsv=cv2.cvtColor(clean,cv2.COLOR_BGR2HSV)
            green=(hsv[:,:,0]>35)&(hsv[:,:,0]<95)&(hsv[:,:,1]>65)&(hsv[:,:,2]>30)
            green_margin=cv2.dilate(green.astype(np.uint8),np.ones((3,3),np.uint8))>0
        results={}
        for sequence,(name,(box,vertical,minimum)) in enumerate(self.regions.items()):
            x0,y0,x1,y1=box;yy,xx=np.where(edges[y0:y1,x0:x1]>0)
            points=np.c_[xx+x0,yy+y0].astype(float);strength=np.hypot(gx[yy+y0,xx+x0],gy[yy+y0,xx+x0])
            evidence={}
            if ownership is not None:
                target=ownership['metal'] if vertical else ownership['cap']
                target=np.asarray(target)>0
                near=cv2.dilate(target.astype(np.uint8),np.ones((3,3),np.uint8))>0
                px=points[:,0].astype(int);py=points[:,1].astype(int)
                inward=[]
                for distance in [1,2,3]:
                    dx=(distance if name.endswith('left') else -distance) if vertical else 0
                    dy=0 if vertical else (-distance if name=='black_cap_bottom' else distance)
                    inward.append(target[np.clip(py+dy,0,image.shape[0]-1),np.clip(px+dx,0,image.shape[1]-1)])
                inside=np.sum(inward,axis=0)>=2
                wrong_gripper=gripper_margin[py,px]
                wrong_green=green_margin[py,px]
                owned=near[py,px]&inside&~wrong_gripper&~wrong_green
                evidence={'ownership_checked':True,'raw_edge_candidates':len(points),'owned_edge_candidates':int(owned.sum()),
                          'rejected_candidate_points_raw_px':points[~owned].tolist(),
                          'rejected_gripper_or_contact_margin':int(wrong_gripper.sum()),
                          'rejected_no_module_boundary_support':int((~near[py,px]|~inside).sum()),
                          'rejected_green_accessory_margin':int(wrong_green.sum()),
                          'ownership_note':'Image segmentation/first-frame semantic prompts, not physical ground truth; ambiguous support is excluded'}
                points=points[owned];strength=strength[owned]
            rng=np.random.default_rng(100+sequence);best=None
            for _ in range(300):
                if len(points)<minimum:break
                a,b=points[rng.choice(len(points),2,False)];v=b-a;length=np.linalg.norm(v)
                if length<10 or (abs(v[0])>abs(v[1])*.35 if vertical else abs(v[1])>abs(v[0])*.20):continue
                n=np.array([-v[1],v[0]])/length;distance=abs((points-a)@n);keep=distance<1.05
                score=np.minimum(strength[keep]/100,2).sum()
                if best is None or score>best[0]:best=(score,keep)
            if best is None or best[1].sum()<minimum:
                results[name]={'status':'not_observed','search_region':box,**evidence};continue
            selected=points[best[1]];span=float(np.ptp(selected[:,1 if vertical else 0]))
            if span<(12 if vertical else 24):
                results[name]={'status':'insufficient_span','search_region':box,**evidence};continue
            normalized=cv2.fisheye.undistortPoints(selected[:,None],self.K,self.D)[:,0]
            mean=normalized.mean(0);_,_,axes=np.linalg.svd(normalized-mean,full_matrices=False);normal=axes[-1]
            line=np.r_[normal,-normal@mean]
            residual=(normalized@normal-normal@mean)*(self.K[0,0]+self.K[1,1])/2
            results[name]={'status':'observed','search_region':box,'points_raw_px':selected.tolist(),
                           'line_normalized':line.tolist(),'point_count':len(selected),'span_raw_px':span,
                           'line_fit_rms_pixel_equivalent':float(np.sqrt(np.mean(residual**2))),'used_marker':False,**evidence}
        return results,exclude,edges


def load_ownership_masks(directory,index,shape=(1080,1920)):
    directory=Path(directory);info=json.loads((directory/'inputs.json').read_text())
    x0,y0=info['crop_origin'];w,h=info['crop_size'];output={}
    ids_by_name=info['object_ids']
    for name,ids in [('metal',[ids_by_name['metal_module']]),('cap',[ids_by_name['rigid_black_end']]),('gripper',[ids_by_name['left_gripper'],ids_by_name['right_gripper']])]:
        crop=np.zeros((h,w),bool)
        for identifier in ids:
            mask=cv2.imread(str(directory/'masks'/str(identifier)/f'{index:06d}.png'),0)
            if mask is None or mask.shape!=(h,w):raise ValueError('Missing or mismatched semantic mask')
            crop|=mask>0
        full=np.zeros(shape,bool);full[y0:y0+h,x0:x0+w]=crop;output[name]=full
    return output


class StructuralPoseSolver:
    def __init__(self,model,calibration,initial_pose):
        self.model=model;self.K=np.array(calibration['K']);self.D=np.array(calibration['D'])
        self.initial=np.array(initial_pose,float);self.pivot=np.array([0,.035,.003]);self.center=self.initial[:3,:3]@self.pivot+self.initial[:3,3]
        self.last_delta=np.zeros(6);self.face_sign=np.sign(self.initial[:3,2]@-self.initial[:3,3])

    def pose(self,x):
        T=np.eye(4);T[:3,:3]=Rotation.from_rotvec(x[:3]).as_matrix()@self.initial[:3,:3];T[:3,3]=self.center+x[3:]-T[:3,:3]@self.pivot;return T

    def solve(self,features,multistart=False):
        names=[name for name in self.model.lines if features.get(name,{}).get('status')=='observed' and features[name].get('ownership_checked',False)]
        if len(names)<3 or 'black_cap_bottom' not in names:
            return {'status':'insufficient_structural_constraints','observed_lines':names,'T_camera_from_model':None,'physical_accuracy_validated':False}
        focal=(self.K[0,0]+self.K[1,1])/2
        def residual(x,prior=True):
            T=self.pose(x);values=[]
            for name in names:
                q=self.model.lines[name]@T[:3,:3].T+T[:3,3]
                values.extend(q@np.array(features[name]['line_normalized'])/np.maximum(q[:,2],.01)*focal)
            return np.r_[values,.05*x[:3]/.3,.05*x[3:]/.02] if prior else np.array(values)
        starts=[self.last_delta.copy()]
        if multistart:starts.extend([np.array([.25,0,0,0,.008,0]),np.array([-.25,0,0,0,.008,0])])
        candidates=[]
        for start in starts:
            fit=least_squares(residual,start,bounds=(np.r_[[-.6]*3,[-.03]*3],np.r_[[.6]*3,[.03]*3]),loss='soft_l1',f_scale=1.,max_nfev=160,x_scale=np.r_[[.1]*3,[.01]*3])
            T=self.pose(fit.x);data_error=residual(fit.x,False)
            positive=np.min((self.model.vertices@T[:3,:3].T+T[:3,3])[:,2])>.02
            face=self.face_sign*(T[:3,2]@-T[:3,3])>0
            if not positive or not face:continue
            candidates.append((float(np.linalg.norm(residual(fit.x))),fit,T,data_error))
        if not candidates:return {'status':'pose_geometry_rejected','observed_lines':names,'T_camera_from_model':None,'physical_accuracy_validated':False}
        _,fit,T,error=min(candidates,key=lambda x:x[0]);epsilon=np.r_[np.full(3,1e-5),np.full(3,1e-6)];J=[]
        for j in range(6):
            step=np.zeros(6);step[j]=epsilon[j];J.append((residual(fit.x+step,False)-residual(fit.x-step,False))/(2*epsilon[j]))
        J=np.array(J).T*np.r_[np.full(3,.01),np.full(3,.001)];singular=np.linalg.svd(J,compute_uv=False);condition=float(singular[0]/max(singular[-1],1e-12));rank=int(np.sum(singular>singular[0]*1e-5))
        rms=float(np.sqrt(np.mean(error*error)));valid=fit.success and rank==6 and rms<2. and len(names)>=4
        if valid:self.last_delta=fit.x.copy()
        return {'status':'structural_pose_candidate' if valid else ('partial_structure_requires_prior' if len(names)<4 else 'structural_pose_requires_review'),'observed_lines':names,
                'T_camera_from_model':T.tolist() if valid else None,'diagnostic_candidate_T_camera_from_model':T.tolist(),'line_residual_rms_pixel_equivalent':rms,'line_residuals_pixel_equivalent':error.tolist(),
                'measurement_jacobian_rank':rank,'measurement_jacobian_condition':condition,
                'rotation_change_from_prior_deg':float(np.degrees(Rotation.from_rotvec(fit.x[:3]).magnitude())),
                'head_pivot_translation_change_mm':float(np.linalg.norm(fit.x[3:])*1000),
                'printed_patch_used':False,'physical_accuracy_validated':False,'model_scale_changed':False,
                'limits':['Known grasp-view search regions','Structural line identities assumed and must be reviewed','No independent pose truth','Model feature dimensions not metrology-certified']}
