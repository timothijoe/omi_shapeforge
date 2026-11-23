"""Prior-assisted, occlusion-aware tracking of features bound to a rigid mesh.

Feature bindings inherit the supplied initial pose's errors. Conditional
linearized uncertainty is a diagnostic, not calibrated physical accuracy.
"""
from pathlib import Path
import json
import cv2
import numpy as np
import open3d as o3d
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


class FisheyeCamera:
    def __init__(self, calibration, size, origin=(0, 0), episode_roi=False):
        self.K=np.array(calibration['K'],float);self.D=np.array(calibration['D'],float)
        self.width,self.height=size;self.origin=np.array(origin,float);self.episode_roi=episode_roi
        self.samples=np.rint(np.linspace(0,388,128))

    def to_raw(self,p):
        p=np.asarray(p,float).reshape(-1,2)
        if self.episode_roi:
            return np.c_[766+np.interp(p[:,0],np.arange(128),self.samples),566+np.interp(p[:,1],np.arange(128),self.samples)]
        return p+self.origin

    def from_raw(self,p):
        p=np.asarray(p,float).reshape(-1,2)
        if self.episode_roi:
            # Extrapolate to keep projections outside the ROI outside it.
            result=np.c_[np.interp(p[:,0]-766,self.samples,np.arange(128)),np.interp(p[:,1]-566,self.samples,np.arange(128))]
            for axis,offset in [(0,766),(1,566)]:
                u=p[:,axis]-offset
                result[u<0,axis]=u[u<0]/3
                result[u>388,axis]=127+(u[u>388]-388)/3
            return result
        return p-self.origin

    def rays(self,p):
        xy=cv2.fisheye.undistortPoints(self.to_raw(p)[:,None],self.K,self.D)[:,0]
        return np.c_[xy,np.ones(len(xy))]

    def project(self,p,T):
        rv=cv2.Rodrigues(T[:3,:3])[0]
        uv=cv2.fisheye.projectPoints(np.asarray(p,float).reshape(-1,1,3),rv,T[:3,3],self.K,self.D)[0][:,0]
        return self.from_raw(uv)


class MeshSurface:
    def __init__(self, inputs, object_name='module'):
        inputs=Path(inputs);manifest=json.loads((inputs/'manifest.json').read_text())[object_name]
        self.scene=o3d.t.geometry.RaycastingScene(nthreads=4);self.parts={};self.vertices=[]
        for part in manifest['parts']:
            name=part['file']
            if object_name=='module' and name not in {'000.npz','001.npz','002.npz','003.npz','004.npz','006.npz','008.npz','010.npz','014.npz'}:continue
            if object_name=='socket' and part.get('group') not in {'housing','cage','fasteners'}:continue
            data=np.load(inputs/object_name/name);v=data['vertices']/1000.;f=data['faces']
            mesh=o3d.geometry.TriangleMesh(o3d.utility.Vector3dVector(v),o3d.utility.Vector3iVector(f))
            gid=self.scene.add_triangles(o3d.t.geometry.TriangleMesh.from_legacy(mesh))
            eligible=(name in {'000.npz','001.npz','002.npz','006.npz','014.npz'}) if object_name=='module' else part.get('group') in {'housing','fasteners'}
            self.parts[int(gid)]={**part,'eligible':eligible,'head':name=='006.npz' and object_name=='module'}
            self.vertices.append(v)
        self.vertices=np.concatenate(self.vertices);self.object_name=object_name

    def intersect(self,p,camera,T):
        rays_cam=camera.rays(p);origin=-T[:3,:3].T@T[:3,3]
        directions=rays_cam@T[:3,:3]
        rays=np.c_[np.broadcast_to(origin,directions.shape),directions].astype(np.float32)
        result=self.scene.cast_rays(o3d.core.Tensor(rays));distance=result['t_hit'].numpy();gid=result['geometry_ids'].numpy()
        points=origin+directions*np.where(np.isfinite(distance),distance,0)[:,None]
        return points,gid,np.isfinite(distance)

    def binding_masks(self,camera,T):
        y,x=np.indices((camera.height,camera.width));p=np.c_[x.ravel(),y.ravel()]
        _,ids,valid=self.intersect(p,camera,T)
        eligible=np.zeros(len(p),bool);head=eligible.copy()
        for gid,part in self.parts.items():
            if part['eligible']:eligible|=ids==gid
            if part['head']:head|=ids==gid
        return (eligible&valid).reshape(y.shape), (head&valid).reshape(y.shape)


def normalized_patch(gray,p,radius):
    x,y=p
    if x<radius or y<radius or x>=gray.shape[1]-radius or y>=gray.shape[0]-radius:return None
    patch=cv2.getRectSubPix(gray,(radius*2+1,radius*2+1),(float(x),float(y))).astype(np.float32)
    deviation=patch.std()
    if deviation<4:return None
    return (patch-patch.mean())/deviation


class MeshFeatureTracker:
    def __init__(self,image,camera,surface,initial_pose,visible_mask=None,time_s=0.,binding_mode='head',enable_se3_updates=False):
        self.camera=camera;self.surface=surface;self.pose=np.array(initial_pose,float);self.initial_pose=self.pose.copy()
        if self.pose.shape!=(4,4) or not np.isfinite(self.pose).all() or not np.allclose(self.pose[3],[0,0,0,1],atol=1e-8) or not np.allclose(self.pose[:3,:3].T@self.pose[:3,:3],np.eye(3),atol=1e-5) or not np.isclose(np.linalg.det(self.pose[:3,:3]),1,atol=1e-5):
            raise ValueError('Initial pose must be rigid, with translations in metres')
        self.binding_mode=binding_mode
        self.enable_se3_updates=enable_se3_updates
        self.small=camera.width<=256;self.radius=2 if self.small else 4
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        eligible,head=surface.binding_masks(camera,self.pose)
        if visible_mask is not None:eligible&=visible_mask>0;head&=visible_mask>0
        if surface.object_name=='module' and binding_mode=='head':eligible=head.copy()
        kernel=np.ones((3,3),np.uint8);eligible=cv2.erode(eligible.astype(np.uint8),kernel)>0;head=cv2.erode(head.astype(np.uint8),kernel)>0
        points=[]
        for region,maximum in [(head,70),(eligible&~head,35)]:
            found=cv2.goodFeaturesToTrack(gray,maxCorners=maximum,qualityLevel=.012,minDistance=2 if self.small else 3,mask=region.astype(np.uint8)*255,blockSize=3)
            if found is not None:points.extend(found[:,0])
        if not points:raise ValueError('No usable image features on eligible rigid surfaces')
        points=np.asarray(points,np.float32);objects,ids,valid=surface.intersect(points,camera,self.pose)
        keep=[];patches=[]
        for i,p in enumerate(points):
            patch=normalized_patch(gray,p,self.radius)
            if valid[i] and patch is not None and surface.parts[int(ids[i])]['eligible']:
                keep.append(i);patches.append(patch)
        self.points=points[keep];self.object_points=objects[keep];self.surface_ids=ids[keep];self.patches=np.asarray(patches)
        if len(keep)<3:raise ValueError('Fewer than three textured mesh-bound features')
        self.head=np.array([surface.parts[int(i)]['head'] for i in self.surface_ids]);self.reference_points=self.points.copy()
        self.alive=np.ones(len(keep),bool);self.previous_gray=gray;self.last_time=time_s;self.last_observed_time=time_s
        self.reference_gray=gray.copy()
        self.last_full_pose_time=None
        self.pivot=np.median(self.object_points[self.head] if self.head.any() else self.object_points,axis=0)
        self.tip=np.array([0.,-.035093169659,0.]) if surface.object_name=='module' else np.array([-.0005,.00185,.0007])
        self.reference_image=image.copy();self.last_record=None
        self.face_sign=np.sign(np.dot(self.initial_pose[:3,2],-self.initial_pose[:3,3]))
        self.head_template=None
        hy,hx=np.where(head)
        if len(hx)>20:
            x0,x1=int(hx.min()),int(hx.max()+1);y0,y1=int(hy.min()),int(hy.max()+1)
            template=gray[y0:y1,x0:x1].astype(np.float32);support=head[y0:y1,x0:x1].astype(np.uint8)
            center=np.array([(x0+x1-1)/2,(y0+y1-1)/2])
            anchor,gid,hit=surface.intersect(center[None],camera,self.initial_pose)
            if hit[0] and template[support>0].std()>5:
                self.head_template=(template,support,anchor[0],center)

    def atlas(self):
        return {'binding_source':'Ray intersection with current mesh under supplied initial pose; absolute binding accuracy unverified',
                'initial_pose':self.initial_pose.tolist(),'feature_count':len(self.points),'head_feature_count':int(self.head.sum()),
                'binding_mode':self.binding_mode,
                'experimental_se3_updates_enabled':self.enable_se3_updates,
                'rigid_head_patch_available':self.head_template is not None,
                'green_handle_excluded':True,'features':[{'id':i,'surface':self.surface.parts[int(self.surface_ids[i])]['name'],
                    'reference_native_xy':self.reference_points[i].tolist(),'reference_raw_xy':self.camera.to_raw(self.reference_points[i:i+1])[0].tolist(),
                    'model_xyz_m':self.object_points[i].tolist(),'rigid_head':bool(self.head[i])} for i in range(len(self.points))]}

    def save_reference_pack(self,directory,metadata=None):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        path=directory/'reference_features.npz'
        if path.exists():raise FileExistsError(path)
        fields={'model_xyz_m':self.object_points,'native_reference_xy':self.reference_points,
                'surface_ids':self.surface_ids,'head_flags':self.head,
                'normalized_reference_patches':self.patches,'T_camera_from_model':self.initial_pose}
        if self.head_template is not None:
            template,support,anchor,center=self.head_template
            fields.update(head_template_gray=template,head_template_support=support,
                          head_template_anchor_model_m=anchor,head_template_center_native_px=center)
        np.savez_compressed(path,**fields)
        atlas=self.atlas();atlas.update(metadata or {});atlas.update(feature_pack=str(path),physical_binding_verified=False)
        (directory/'feature_atlas.json').write_text(json.dumps(atlas,indent=2))

    def _estimate(self,indices,observed,dt):
        old=self.pose.copy();pivot_cam=old[:3,:3]@self.pivot+old[:3,3]
        def pose(delta):
            R=Rotation.from_rotvec(delta[:3]).as_matrix()@old[:3,:3]
            T=np.eye(4);T[:3,:3]=R;T[:3,3]=pivot_cam+delta[3:]-R@self.pivot;return T
        scale=max(1.,min(dt/.1,3.))
        bounds=np.r_[np.full(3,np.deg2rad(5)*scale),np.full(3,.004*scale)]
        def residual(delta,ids,uv,prior=True):
            reproj=(self.camera.project(self.object_points[ids],pose(delta))-uv).ravel()
            if prior:return np.r_[reproj,.25*delta[:3]/(np.deg2rad(2)*scale),.25*delta[3:]/(.0015*scale)]
            return reproj
        fit=least_squares(residual,np.zeros(6),args=(indices,observed),bounds=(-bounds,bounds),loss='soft_l1',f_scale=.7,max_nfev=35,x_scale=np.r_[np.full(3,.02),np.full(3,.001)])
        error=np.linalg.norm(residual(fit.x,indices,observed,False).reshape(-1,2),axis=1)
        keep=error<(1.0 if self.small else 2.)
        if keep.sum()>=6 and not keep.all():
            indices=indices[keep];observed=observed[keep]
            fit=least_squares(residual,fit.x,args=(indices,observed),bounds=(-bounds,bounds),loss='soft_l1',f_scale=.7,max_nfev=30,x_scale=np.r_[np.full(3,.02),np.full(3,.001)])
        T=pose(fit.x);errors=np.linalg.norm(residual(fit.x,indices,observed,False).reshape(-1,2),axis=1)
        if len(indices)<6 or not fit.success or np.sqrt(np.mean(errors**2))>(.8 if self.small else 1.8):return None
        if self.face_sign*np.dot(T[:3,2],-T[:3,3])<=0:return None
        # Measurement-only local covariance: deliberately exclude the temporal prior.
        eps=np.r_[np.full(3,1e-5),np.full(3,1e-6)];J=[]
        for j in range(6):
            perturb=np.zeros(6);perturb[j]=eps[j]
            J.append((residual(fit.x+perturb,indices,observed,False)-residual(fit.x-perturb,indices,observed,False))/(2*eps[j]))
        J=np.array(J).T;units=np.r_[np.full(3,.01),np.full(3,.001)];scaled=J*units
        _,singular,vh=np.linalg.svd(scaled,full_matrices=False);condition=float(singular[0]/max(singular[-1],1e-12))
        sigma=max(.5 if self.small else .3,float(np.sqrt(np.mean(errors**2))))
        tip_sigma=None;orientation_sigma=None
        if len(singular)==6 and singular[-1]>1e-5 and condition<1e6:
            covariance=(vh.T@np.diag((sigma/singular)**2)@vh)*units[:,None]*units[None,:]
            lever=T[:3,:3]@(self.tip-self.pivot);x,y,z=lever;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0.]])
            G=np.c_[-skew,np.eye(3)];tip_cov=G@covariance@G.T
            tip_sigma=float(np.sqrt(max(0,np.linalg.eigvalsh(tip_cov).max()))*1000)
            orientation_sigma=np.degrees(np.sqrt(np.maximum(0,np.diag(covariance)[:3]))).tolist()
        return T,indices,{'fit_rms_native_px':float(np.sqrt(np.mean(errors**2))),'measurement_jacobian_condition':condition,
                          'conditional_tip_sigma_mm':tip_sigma,'conditional_rotation_sigma_deg_xyz':orientation_sigma,
                          'conditional_uncertainty_note':'Linearized feature-noise diagnostic only; excludes initial pose, model, calibration and correlated-feature errors'}

    def _estimate_image_translation(self,indices,observed):
        """Only correct camera X/Y; retain depth and orientation as explicit priors."""
        if len(indices)<3:return None
        old=self.pose.copy()
        def pose(delta):
            T=old.copy();T[:2,3]+=delta;return T
        def residual(delta):
            return np.r_[(self.camera.project(self.object_points[indices],pose(delta))-observed).ravel(),.2*delta/.002]
        fit=least_squares(residual,np.zeros(2),bounds=(-.004,.004),loss='soft_l1',f_scale=.5,max_nfev=25,x_scale=.001)
        T=pose(fit.x);errors=np.linalg.norm(self.camera.project(self.object_points[indices],T)-observed,axis=1)
        if not fit.success or np.sqrt(np.mean(errors**2))>(.8 if self.small else 1.8):return None
        return T,indices,{'fit_rms_native_px':float(np.sqrt(np.mean(errors**2))),'conditional_tip_sigma_mm':None,
                          'conditional_uncertainty_note':'Only image-plane translation constrained; camera X/Y conversion assumes the current depth and model binding',
                          'observed_dofs':['image_u','image_v'],'optimized_pose_dofs':['camera_x','camera_y'],'prior_dofs':['camera_z','rotation_x','rotation_y','rotation_z']}

    def _head_patch_translation(self,gray,visible_mask):
        if self.head_template is None:return None
        template,support,anchor,reference_center=self.head_template
        th,tw=template.shape;pred=self.camera.project(anchor[None],self.pose)[0]
        search=5 if self.small else 12
        x0=max(0,int(np.floor(pred[0]-(tw-1)/2))-search);y0=max(0,int(np.floor(pred[1]-(th-1)/2))-search)
        x1=min(gray.shape[1],int(np.ceil(pred[0]+(tw-1)/2))+search+1);y1=min(gray.shape[0],int(np.ceil(pred[1]+(th-1)/2))+search+1)
        if x1-x0<tw or y1-y0<th:return None
        scores=cv2.matchTemplate(gray[y0:y1,x0:x1].astype(np.float32),template,cv2.TM_CCOEFF_NORMED,mask=support)
        scores=np.where(np.isfinite(scores),scores,-1.)
        _,score,_,loc=cv2.minMaxLoc(scores)
        if score<.88:return None
        lx,ly=loc;sub=np.zeros(2)
        if 0<lx<scores.shape[1]-1:
            a,b,c=scores[ly,lx-1:lx+2];den=a-2*b+c
            if den<-.0001:sub[0]=np.clip(.5*(a-c)/den,-.75,.75)
        if 0<ly<scores.shape[0]-1:
            a,b,c=scores[ly-1:ly+2,lx];den=a-2*b+c
            if den<-.0001:sub[1]=np.clip(.5*(a-c)/den,-.75,.75)
        center=np.array([x0+lx+(tw-1)/2,y0+ly+(th-1)/2])+sub
        if visible_mask is not None:
            region=visible_mask[y0+ly:y0+ly+th,x0+lx:x0+lx+tw]>0
            if region.shape!=support.shape or np.mean(region[support>0])<.8:return None
        current=self.pose[:3,:3]@anchor+self.pose[:3,3];ray=self.camera.rays(center[None])[0]
        desired=ray*current[2];delta=desired-current
        if np.linalg.norm(delta[:2])>.004:return None
        T=self.pose.copy();T[:2,3]+=delta[:2]
        return T,{'head_patch_ncc':float(score),'head_patch_center_native_xy':center.tolist(),
                  'observed_dofs':['image_u','image_v'],'optimized_pose_dofs':['camera_x','camera_y'],'prior_dofs':['camera_z','rotation_x','rotation_y','rotation_z'],
                  'conditional_tip_sigma_mm':None,'conditional_uncertainty_note':'Dense head patch constrains image position; metric X/Y conversion depends on retained depth and model binding'}

    def update(self,image,time_s,visible_mask=None):
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);dt=max(time_s-self.last_time,.001)
        indices=np.arange(len(self.points));tracked=np.full_like(self.points,np.nan);accepted=np.zeros(len(self.points),bool);correlations=np.zeros(len(self.points))
        if len(indices):
            p=self.reference_points[indices,None].astype(np.float32)
            guess=self.camera.project(self.object_points,self.pose).astype(np.float32)
            guess[self.alive]=self.points[self.alive]
            forward,status,_=cv2.calcOpticalFlowPyrLK(self.reference_gray,gray,p,guess[:,None].copy(),flags=cv2.OPTFLOW_USE_INITIAL_FLOW,winSize=(11,11) if self.small else (21,21),maxLevel=2,criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,30,.01))
            backward,bs,_=cv2.calcOpticalFlowPyrLK(gray,self.reference_gray,forward,p.copy(),flags=cv2.OPTFLOW_USE_INITIAL_FLOW,winSize=(11,11) if self.small else (21,21),maxLevel=2,criteria=(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,30,.01))
            fb=np.linalg.norm(backward[:,0]-p[:,0],axis=1)
            for j,index in enumerate(indices):
                point=forward[j,0];patch=normalized_patch(gray,point,self.radius)
                if not status[j,0] or not bs[j,0] or fb[j]>(.7 if self.small else 1.) or patch is None:continue
                corr=float(np.mean(patch*self.patches[index]));correlations[index]=corr
                u,v=np.rint(point).astype(int)
                if visible_mask is not None and (not 0<=u<self.camera.width or not 0<=v<self.camera.height or not visible_mask[v,u]):continue
                if corr<(.50 if self.small else .60):continue
                tracked[index]=point;accepted[index]=True
        # Re-acquire only reference-identified patches near their predicted image
        # position; do not invent new 3-D anchors from the current uncertain pose.
        recovered=0
        if accepted.sum()<max(10,len(self.points)//2):
            predicted=self.camera.project(self.object_points,self.pose);search=3 if self.small else 10
            for index in np.where(~accepted)[0]:
                x,y=np.rint(predicted[index]).astype(int);radius=self.radius
                x0=max(0,x-search-radius);y0=max(0,y-search-radius);x1=min(gray.shape[1],x+search+radius+1);y1=min(gray.shape[0],y+search+radius+1)
                if x1-x0<2*radius+1 or y1-y0<2*radius+1:continue
                scores=cv2.matchTemplate(gray[y0:y1,x0:x1].astype(np.float32),self.patches[index],cv2.TM_CCOEFF_NORMED)
                _,score,_,location=cv2.minMaxLoc(scores)
                if score<(.88 if self.small else .85):continue
                point=np.array([x0+location[0]+radius,y0+location[1]+radius],np.float32);u,v=point.astype(int)
                if visible_mask is not None and not visible_mask[v,u]:continue
                tracked[index]=point;accepted[index]=True;correlations[index]=score;recovered+=1
        ids=np.where(accepted)[0];fit_ids=ids[ids%5!=0];check_ids=ids[ids%5==0]
        result=self._estimate(fit_ids,tracked[fit_ids],dt) if self.enable_se3_updates and len(fit_ids)>=6 else None
        partial=False
        if result is None and len(fit_ids)>=3:
            result=self._estimate_image_translation(fit_ids,tracked[fit_ids]);partial=result is not None
        metrics={};measurement=False;check_rms=None
        if result is not None:
            candidate,inlier_ids,metrics=result
            if len(check_ids):
                error=self.camera.project(self.object_points[check_ids],candidate)-tracked[check_ids];check_rms=float(np.sqrt(np.mean(np.sum(error*error,axis=1))))
            if check_rms is None or check_rms<(1.2 if self.small else 2.5):
                self.pose=candidate;self.last_observed_time=time_s;measurement=True
                if not partial:self.last_full_pose_time=time_s
                state='observed_update' if not partial and metrics['conditional_tip_sigma_mm'] is not None and metrics['conditional_tip_sigma_mm']<=3 else 'prior_assisted_update'
            else:state='prediction_only'
        else:state='prediction_only'
        if not measurement:
            patch_result=self._head_patch_translation(gray,visible_mask)
            if patch_result is not None:
                self.pose,patch_metrics=patch_result;metrics.update(patch_metrics)
                self.last_observed_time=time_s;measurement=True;partial=True;state='prior_assisted_update'
        age=time_s-self.last_observed_time
        if not measurement and age>.5:state='lost'
        if measurement and len(check_ids):
            error=self.camera.project(self.object_points[check_ids],self.pose)-tracked[check_ids]
            check_rms=float(np.sqrt(np.mean(np.sum(error*error,axis=1))))
        elif not measurement:
            if check_rms is not None:metrics['rejected_candidate_check_rms_native_px']=check_rms
            check_rms=None
        self.points[accepted]=tracked[accepted];self.alive=accepted;self.previous_gray=gray;self.last_time=time_s
        shift=self.pose[:3,3]-self.initial_pose[:3,3];rotation=Rotation.from_matrix(self.initial_pose[:3,:3].T@self.pose[:3,:3]).magnitude()
        record={'time_s':time_s,'state':state,'measurement_update':measurement,'time_since_observation_s':age,
                'measurement_dof_count':2 if measurement and partial else (6 if measurement else 0),
                'pose_update_mode':('xy_only_fixed_depth_rotation' if partial else 'local_se3_with_prior') if measurement else 'hold_last_unobserved',
                'time_since_full_pose_measurement_s':time_s-self.last_full_pose_time if self.last_full_pose_time is not None else None,
                'tracked_features':len(ids),'tracked_head_features':int(np.sum(self.head&accepted)),'tracked_other_rigid_features':int(np.sum(~self.head&accepted)),
                'reference_patch_reacquired':recovered,'check_feature_rms_native_px':check_rms,
                'T_camera_from_model':self.pose.tolist() if state!='lost' else None,
                'prediction_for_display_only':self.pose.tolist(),'translation_from_initial_mm':float(np.linalg.norm(shift)*1000),
                'rotation_from_initial_deg':float(np.degrees(rotation)),'features':[{'id':int(i),'native_xy':tracked[i].tolist(),'head':bool(self.head[i]),'patch_ncc':float(correlations[i])} for i in ids],
                'physical_pose_accuracy_validated':False,**metrics}
        self.last_record=record;return record
