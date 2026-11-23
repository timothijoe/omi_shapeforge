"""Metric, explicitly framed geometry for the local head/wrist annotation tool."""
import itertools
import numpy as np
import cv2
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares


def matrix(pose):
    """UI: mm, degrees; extrinsic xyz Euler, R = Rz(yaw) Ry(pitch) Rx(roll)."""
    p = np.asarray(pose, dtype=float)
    if p.shape != (6,) or not np.isfinite(p).all():
        raise ValueError('Expected six finite pose numbers')
    T = np.eye(4)
    T[:3, :3] = Rotation.from_euler('xyz', p[3:], degrees=True).as_matrix()
    T[:3, 3] = p[:3] / 1000
    return T


def pose(T):
    T = validate_matrix(T)
    return np.r_[T[:3, 3] * 1000, Rotation.from_matrix(T[:3, :3]).as_euler('xyz', degrees=True)].tolist()


def validate_matrix(T):
    T = np.asarray(T, dtype=float)
    if T.shape != (4, 4) or not np.isfinite(T).all():
        raise ValueError('Invalid transform')
    if not np.allclose(T[3], [0, 0, 0, 1], atol=1e-7) or not np.allclose(T[:3,:3].T @ T[:3,:3], np.eye(3), atol=1e-5) or abs(np.linalg.det(T[:3,:3])-1)>1e-5:
        raise ValueError('Transform must be rigid SE(3)')
    return T


def transform(points, T):
    return np.asarray(points) @ T[:3, :3].T + T[:3, 3]


def project(points, T, calibration):
    xyz = transform(points, T)
    K = np.array(calibration['K'], float).reshape(3, 3)
    D = np.array(calibration.get('D', []), float)
    if calibration.get('distortion_model') == 'opencv_fisheye':
        uv = cv2.fisheye.projectPoints(xyz.reshape(-1,1,3), np.zeros(3), np.zeros(3), K, D)[0].reshape(-1,2)
    else:
        uv = cv2.projectPoints(xyz, np.zeros(3), np.zeros(3), K, D if len(D) else None)[0].reshape(-1,2)
    return uv, xyz[:, 2] > .001


def optical_extrinsic(metadata):
    """T_color_from_left = T_color_from_depth @ inverse(T_left_from_depth)."""
    def read(key):
        e = metadata['extrinsics'][key]
        T = np.eye(4)
        T[:3,:3] = np.array(e['rotation']).reshape(3,3,order='F' if e.get('rotation_order','column-major') == 'column-major' else 'C')
        T[:3,3] = e['translation']
        return validate_matrix(T)
    return read('depth_to_color') @ np.linalg.inv(read('depth_to_infra1'))


def roi_cloud(points, metadata, rect):
    rect = np.asarray(rect,float)
    if rect.shape != (4,) or not np.isfinite(rect).all():
        raise ValueError('Draw a head RGB rectangle first')
    uv, valid = project(points, optical_extrinsic(metadata), metadata['calibration']['color'])
    x0,y0,x1,y1 = rect
    take = valid & (uv[:,0]>=min(x0,x1)) & (uv[:,0]<=max(x0,x1)) & (uv[:,1]>=min(y0,y1)) & (uv[:,1]<=max(y0,y1))
    q = points[take]
    if len(q)<40:
        raise ValueError('ROI has fewer than 40 depth points; enlarge or regenerate cloud')
    q = q[np.abs(q[:,2]-np.median(q[:,2])) < .07]
    if len(q)<40: raise ValueError('Insufficient coherent depth support')
    return q[np.linspace(0,len(q)-1,min(2500,len(q))).astype(int)]


def rigid_fit(a,b):
    ac,bc=a.mean(0),b.mean(0)
    u,_,vt=np.linalg.svd((a-ac).T@(b-bc)); R=vt.T@u.T
    if np.linalg.det(R)<0: vt[-1]*=-1;R=vt.T@u.T
    T=np.eye(4);T[:3,:3]=R;T[:3,3]=bc-R@ac
    return T


def coarse_candidates(model, observed, initial=None):
    """ROI-assisted fixed-scale fitting, including orientation ambiguity.

    Partial observed cloud -> complete model distances avoid requiring occluded
    surfaces to have observations. Ranking is NOT pose accuracy.
    """
    model=np.asarray(model); observed=np.asarray(observed)
    if len(observed)<40: raise ValueError('Insufficient point cloud support')
    if initial is not None:
        return [refine_local_cloud(model, observed, initial)]
    tree=cKDTree(model)
    seeds=[]
    if initial is not None: seeds.append(validate_matrix(initial))
    _,_,vm=np.linalg.svd(model-model.mean(0),full_matrices=False)
    _,_,vo=np.linalg.svd(observed-observed.mean(0),full_matrices=False)
    for order in itertools.permutations(range(3)):
        for signs in itertools.product([-1,1],repeat=3):
            R=vo.T[:,order] @ np.diag(signs) @ vm
            if np.linalg.det(R)<.99: continue
            T=np.eye(4);T[:3,:3]=R;T[:3,3]=np.median(observed,axis=0)-np.median(model@R.T,axis=0);seeds.append(T)
    candidates=[]
    for seed in seeds:
        T=seed.copy()
        for _ in range(22):
            local=transform(observed,np.linalg.inv(T));dist,ix=tree.query(local)
            use=dist<=max(.001,np.quantile(dist,.85))
            new=rigid_fit(model[ix[use]],observed[use])
            if np.linalg.norm(new[:3,3]-T[:3,3])<1e-7: T=new;break
            T=new
        dist,_=tree.query(transform(observed,np.linalg.inv(T)))
        candidates.append({'T':T.tolist(),'median_mm':float(np.median(dist)*1000),'p90_mm':float(np.quantile(dist,.9)*1000),'coverage_3mm':float(np.mean(dist<.003))})
    candidates.sort(key=lambda c:c['p90_mm'])
    distinct=[]
    for c in candidates:
        T=np.array(c['T'])
        if all(Rotation.from_matrix(T[:3,:3]@np.array(d['T'])[:3,:3].T).magnitude()>.2 or np.linalg.norm(T[:3,3]-np.array(d['T'])[:3,3])>.004 for d in distinct): distinct.append(c)
    return distinct[:8]


def fit_metrics(model, observed, T):
    dist,_=cKDTree(model).query(transform(observed,np.linalg.inv(T)))
    return {'median_mm':float(np.median(dist)*1000),'p90_mm':float(np.quantile(dist,.9)*1000),
            'coverage_3mm':float(np.mean(dist<.003))}


def refine_local_cloud(model, observed, initial):
    """Refine locally; never restart orientation search from an edited pose."""
    initial=validate_matrix(initial);tree=cKDTree(model)
    initial_dist,_=tree.query(transform(observed,np.linalg.inv(initial)))
    observed=observed[initial_dist<max(.004,min(.015,np.quantile(initial_dist,.8)))]
    if len(observed)<40:raise ValueError('Current pose is too far from ROI; use the four-point initializer first')
    def trial(x):
        T=initial.copy();T[:3,:3]=Rotation.from_rotvec(x[3:]).as_matrix()@initial[:3,:3];T[:3,3]+=x[:3];return T
    def residual(x):
        d,_=tree.query(transform(observed,np.linalg.inv(trial(x))))
        return np.r_[d/.002,x[:3]/.003,x[3:]/np.deg2rad(3)]
    bound=np.r_[np.full(3,.004),np.full(3,np.deg2rad(4))]
    fit=least_squares(residual,np.zeros(6),bounds=(-bound,bound),loss='soft_l1',f_scale=1,max_nfev=45,x_scale=bound)
    T=trial(fit.x)
    if np.linalg.norm(fit.x[:3])>.005 or np.linalg.norm(fit.x[3:])>np.deg2rad(5):
        raise ValueError('点云微调试图偏离初值过远，已保留当前位姿。请检查选区或用滑条精调。')
    return {'T':T.tolist(),**fit_metrics(model,observed,T),'method':'bounded_local_cloud_refinement',
            'translation_change_mm':float(np.linalg.norm(fit.x[:3])*1000),'rotation_change_deg':float(np.rad2deg(np.linalg.norm(fit.x[3:]))),
            'physical_accuracy_validated':False}


def guided_initialize(anchors, pixels, cloud, metadata):
    """Four ordered real geometry corners in head RGB + local metric depth.

    Human correspondences resolve the sign/axis ambiguity of partial-cloud PCA.
    Depth provides a scale/translation check; this is not automatic detection or
    independently calibrated ground truth. The upper surface must be visible.
    """
    anchors=np.asarray(anchors,float);pixels=np.asarray(pixels,float)
    if anchors.shape!=(4,3) or pixels.shape!=(4,2) or not np.isfinite(pixels).all():
        raise ValueError('Click all four indicated corners, in order')
    if len(np.unique(pixels,axis=0))!=4:
        raise ValueError('Choose four distinct structure corners')
    if np.linalg.svd(pixels-pixels.mean(0),compute_uv=False)[1]<5:
        raise ValueError('Image corners are too close or collinear; choose four visible corners')
    cal=metadata['calibration']['color'];Tch=optical_extrinsic(metadata)
    uv,valid=project(cloud,Tch,cal);projected_tree=cKDTree(uv[valid]);q=cloud[valid]
    lifted=[];support=[]
    for p in pixels:
        ids=projected_tree.query_ball_point(p,8.)
        if len(ids)<5:raise ValueError('One corner has insufficient stereo depth; click a visible surface nearby')
        points=q[ids];z=transform(points,Tch)[:,2]
        # Use the observed local surface near the click, not a whole-ROI median.
        # Edge pixels often mix foreground and background. The median of two
        # surfaces lies on neither. Select the nearest well-supported mode.
        support_counts=np.array([np.count_nonzero(abs(z-center)<.006) for center in z])
        eligible=z[support_counts>=max(5,.55*support_counts.max())]
        median=float(eligible.min()) if len(eligible) else float(np.median(z))
        band=np.abs(z-median)<.006
        if band.sum()<5:raise ValueError('Depth around a corner is discontinuous; choose a clearer point')
        selected=points[band];zc=float(np.median(transform(selected,Tch)[:,2]))
        ray=cv2.undistortPoints(p.reshape(1,1,2),np.array(cal['K']).reshape(3,3),np.array(cal['D'])).reshape(2)
        lifted.append(transform(np.array([[ray[0]*zc,ray[1]*zc,zc]]),np.linalg.inv(Tch))[0])
        support.append({'points':int(band.sum()),'depth_m':zc,'depth_mad_mm':float(np.median(abs(z[band]-zc))*1000),'selection':'nearest_supported_local_depth_mode','radius_px':8})
    lifted=np.array(lifted);initial=rigid_fit(anchors,lifted)
    seeds=[initial]
    ok,rvecs,tvecs,_=cv2.solvePnPGeneric(anchors,pixels,np.array(cal['K']).reshape(3,3),np.array(cal['D']),flags=cv2.SOLVEPNP_SQPNP)
    if ok:
        for r,t in zip(rvecs,tvecs):
            Tc=np.eye(4);Tc[:3,:3]=cv2.Rodrigues(r)[0];Tc[:3,3]=t.ravel();seeds.append(np.linalg.inv(Tch)@Tc)
    results=[]
    for seed in seeds:
        def trial(x):
            T=seed.copy();T[:3,:3]=Rotation.from_rotvec(x[3:]).as_matrix()@seed[:3,:3];T[:3,3]+=x[:3];return T
        def residual(x):
            T=trial(x);image,visible=project(anchors,Tch@T,cal)
            if not visible.all():return np.full(12,1e5)
            # Pixel annotations locate the corners; stereo depth prevents a
            # small planar patch from drifting arbitrarily along the view ray.
            depth=transform(anchors,Tch@T)[:,2]
            measured=np.array([s['depth_m'] for s in support])
            return np.r_[(image-pixels).ravel()/1.5,(depth-measured)/.004]
        bound=np.r_[np.full(3,.06),np.full(3,.6)]
        fit=least_squares(residual,np.zeros(6),bounds=(-bound,bound),loss='soft_l1',f_scale=1,max_nfev=100,x_scale=bound)
        T=trial(fit.x);image,visible=project(anchors,Tch@T,cal);cam=Tch@T
        if not visible.all() or np.dot(cam[:3,2],cam[:3,3])>=0:continue
        rms=float(np.sqrt(np.mean(np.sum((image-pixels)**2,axis=1))))
        depth_error=float(np.median(np.abs(transform(anchors,Tch@T)[:,2]-[s['depth_m'] for s in support]))*1000)
        results.append({'T':T.tolist(),'pixel_rms':rms,'depth_median_error_mm':depth_error,'score':rms+depth_error/3})
    if not results:raise ValueError('Corner order implies the wrong visible face; follow the diagram, or use manual pose')
    best=min(results,key=lambda r:r['score'])
    if best['pixel_rms']>8 or best['depth_median_error_mm']>20:
        raise ValueError('Corners and depth disagree too strongly; check corner identities and depth coverage')
    best.update(method='four_ordered_corners_with_stereo_depth',depth_support=support,
                observed_points_head_m=lifted.tolist(),image_points=pixels.tolist(),
                model_points_m=anchors.tolist(),physical_accuracy_validated=False)
    return best


def refine_pixels(points, pixels, T, calibration):
    """Optimize only human-specified mesh-to-pixel correspondences, fixed scale."""
    points=np.asarray(points,float);pixels=np.asarray(pixels,float);T=validate_matrix(T)
    if len(points)<4 or points.shape!=(len(points),3) or pixels.shape!=(len(points),2) or not np.isfinite(points).all() or not np.isfinite(pixels).all():
        raise ValueError('At least four finite 3D/2D correspondences required')
    if len(np.unique(points,axis=0))<4 or np.linalg.svd(points-points.mean(0),compute_uv=False)[1]<.001:
        raise ValueError('Choose distinct, non-collinear mesh points')
    def trial(x):
        Q=T.copy();Q[:3,:3]=Rotation.from_rotvec(x[3:]).as_matrix()@T[:3,:3];Q[:3,3]+=x[:3];return Q
    def residual(x):
        uv,visible=project(points,trial(x),calibration)
        return (uv-pixels).ravel() if visible.all() else np.full(2*len(points),1e4)
    bounds=np.r_[np.full(3,.02),np.full(3,np.deg2rad(20))]
    fit=least_squares(residual,np.zeros(6),bounds=(-bounds,bounds),loss='soft_l1',f_scale=2,max_nfev=150,x_scale=np.r_[np.full(3,.01),np.full(3,.1)])
    Q=trial(fit.x);sv=np.linalg.svd(fit.jac,compute_uv=False)
    if not project(points,Q,calibration)[1].all() or np.any(abs(fit.x)>.999*bounds):
        raise ValueError('Solution behind camera or at adjustment bound; correct coarse pose first')
    return {'T':Q.tolist(),'rms_before_px':float(np.sqrt(np.mean(residual(np.zeros(6))**2))), 'rms_after_px':float(np.sqrt(np.mean(residual(fit.x)**2))), 'jacobian_singular_values':sv.tolist(),'correspondence_count':len(points),'physical_accuracy_validated':False,'status':'manual_correspondence_candidate'}
