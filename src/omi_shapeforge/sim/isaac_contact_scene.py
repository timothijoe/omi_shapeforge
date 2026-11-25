"""Explicit, audited USD authoring from a frozen evaluated geometry packet.

Imported only inside Isaac after SimulationApp. Fixed links are merged for
inertia/collision; their named frames remain available for cameras and TCP.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation
from pxr import Gf, Sdf, UsdGeom, UsdLux, UsdPhysics, UsdShade, PhysxSchema, Vt


def rotation(q):
    return Rotation.from_quat(np.roll(q,-1)).as_matrix()


def quaternion(r):
    return np.roll(Rotation.from_matrix(r).as_quat(),1)


def transform(p,r):
    t=np.eye(4);t[:3,:3]=r;t[:3,3]=p
    return t


def local_pose(item):
    return transform(item['position'],rotation(item['quaternion']))


def set_pose(prim,t):
    x=UsdGeom.Xformable(prim);x.ClearXformOpOrder()
    x.AddTranslateOp().Set(Gf.Vec3d(*t[:3,3]))
    q=quaternion(t[:3,:3]);x.AddOrientOp().Set(Gf.Quatf(float(q[0]),Gf.Vec3f(*q[1:])))


def build(stage, transfer, output, *, contact_offset=1e-5, locked=False, lateral_mm=0., yaw_deg=0., movable_socket=False):
    directory=Path(transfer);packet=json.loads((directory/'transfer.json').read_text())
    if hashlib.sha256((directory/'meshes.npz').read_bytes()).hexdigest()!=packet['meshes_sha256']:
        raise ValueError('geometry packet hash mismatch')
    meshes=np.load(directory/'meshes.npz',allow_pickle=False)
    bs=packet['bodies'];js=packet['joints'];robot=any(j['name']=='Arm_L1_Joint' for j in js)
    UsdGeom.SetStageMetersPerUnit(stage,1);UsdGeom.SetStageUpAxis(stage,UsdGeom.Tokens.z)
    world=UsdGeom.Xform.Define(stage,'/World');stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Xform.Define(stage,'/World/Robot');UsdGeom.Xform.Define(stage,'/World/Joints')
    ids={b['name']:b['id'] for b in bs}
    # A new experiment may change local start offset, never the frozen input.
    rest=[transform(b['world_position'],np.asarray(b['world_rotation'])) for b in bs]
    if not robot:
        i=ids['sim_module'];rest[i]=rest[i].copy();rest[i][0,3]+=lateral_mm/1000
        rest[i][:3,:3]=rest[i][:3,:3]@Rotation.from_euler('z',yaw_deg,degrees=True).as_matrix()
    joint_bodies={j['body'] for j in js}
    owners=[0]*len(bs)
    for b in bs[1:]:
        i=b['id'];owners[i]=i if i in joint_bodies or b['parent']==0 else owners[b['parent']]
    paths={0:'/World'}
    roots=set(owners)-{0}
    for i in sorted(roots):
        b=bs[i];prefix='/World/Robot/' if robot and (i<ids['sim_socket']) else '/World/'
        paths[i]=prefix+b['name']
        body=UsdGeom.Xform.Define(stage,paths[i]);set_pose(body.GetPrim(),rest[i])
        socket_base=movable_socket and b['name']=='sim_socket'
        free_body=b['name'] in packet.get('free_bodies',[])
        dynamic=i in joint_bodies or (robot and b['name']=='ZJ_Robot_link') or socket_base or free_body
        if not dynamic:continue
        rigid=UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        if socket_base:rigid.CreateKinematicEnabledAttr(True)
        rb=PhysxSchema.PhysxRigidBodyAPI.Apply(body.GetPrim())
        rb.CreateDisableGravityAttr(not free_body)  # free module uses gravity; robot retains source gravcomp
        rb.CreateSolverPositionIterationCountAttr(128 if packet.get('free_bodies') else 32)
        rb.CreateSolverVelocityIterationCountAttr(32 if packet.get('free_bodies') else 4)
        rb.CreateSleepThresholdAttr(0.0)
        rb.CreateStabilizationThresholdAttr(0.0)
        if socket_base:
            # Kinematic holder has infinite effective mass; positive authored
            # placeholders avoid deriving inertia from the zero-mass static USD.
            ma=UsdPhysics.MassAPI.Apply(body.GetPrim());ma.CreateMassAttr(1.)
            ma.CreateDiagonalInertiaAttr(Gf.Vec3f(.001,.001,.001))
            PhysxSchema.PhysxContactReportAPI.Apply(body.GetPrim()).CreateThresholdAttr(0.)
            continue
        members=[n for n in range(1,len(bs)) if owners[n]==i]
        masses=np.array([bs[n]['mass'] for n in members]);total=float(sum(masses))
        centers=[];inertias=[]
        for n in members:
            rel=np.linalg.inv(rest[i])@rest[n]
            centers.append(rel[:3,3]+rel[:3,:3]@bs[n]['com'])
            rr=rel[:3,:3]@rotation(bs[n]['inertia_quaternion'])
            inertias.append(rr@np.diag(bs[n]['inertia'])@rr.T)
        center=np.average(centers,axis=0,weights=masses)
        inertia=sum(ii+mass*((delta@delta)*np.eye(3)-np.outer(delta,delta))
                    for ii,mass,delta in zip(inertias,masses,np.asarray(centers)-center))
        vals,axes=np.linalg.eigh(inertia)
        if np.linalg.det(axes)<0:axes[:,0]*=-1
        ma=UsdPhysics.MassAPI.Apply(body.GetPrim());ma.CreateMassAttr(total)
        ma.CreateCenterOfMassAttr(Gf.Vec3f(*center));ma.CreateDiagonalInertiaAttr(Gf.Vec3f(*vals))
        q=quaternion(axes);ma.CreatePrincipalAxesAttr(Gf.Quatf(float(q[0]),Gf.Vec3f(*q[1:])))
        PhysxSchema.PhysxContactReportAPI.Apply(body.GetPrim()).CreateThresholdAttr(0.)
    frame_paths={}
    for b in bs[1:]:
        i=b['id'];o=owners[i]
        frame_paths[b['name']]=paths[o]+'/Frames/'+b['name']
        f=UsdGeom.Xform.Define(stage,frame_paths[b['name']]);set_pose(f.GetPrim(),np.linalg.inv(rest[o])@rest[i])
    material_cache={}
    def material(rgba,friction):
        key=(tuple(round(c,5) for c in rgba),round(friction,5))
        if key in material_cache:return material_cache[key]
        p=f'/World/Looks/m{len(material_cache)}';mat=UsdShade.Material.Define(stage,p)
        surf=UsdShade.Shader.Define(stage,p+'/Surface');surf.CreateIdAttr('UsdPreviewSurface')
        surf.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*rgba[:3]))
        surf.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(.4)
        surf.CreateInput('metallic',Sdf.ValueTypeNames.Float).Set(.5 if max(rgba[:3])-min(rgba[:3])<.15 else .0)
        mat.CreateSurfaceOutput().ConnectToSource(surf.ConnectableAPI(),'surface')
        phys=UsdPhysics.MaterialAPI.Apply(mat.GetPrim());phys.CreateStaticFrictionAttr(friction)
        phys.CreateDynamicFrictionAttr(friction);phys.CreateRestitutionAttr(0.)
        material_cache[key]=mat;return mat
    geom_paths={};collider_count=0
    for g in packet['geoms']:
        b=g['body'];o=owners[b];p=paths[o]+'/Geom/'+g['name'];kind=g['kind']
        t=np.linalg.inv(rest[o])@rest[b]@local_pose(g)
        if kind==7:
            obj=UsdGeom.Mesh.Define(stage,p);v=meshes[f'v{g["mesh"]}'];f=meshes[f'f{g["mesh"]}']
            # Cook in mm-sized local coordinates, compensate in the prim transform.
            # PhysX default convex tolerances otherwise expand sub-mm thin parts.
            vertex_scale=1000. if g['contact'] else 1.
            obj.CreatePointsAttr(Vt.Vec3fArray.FromNumpy((v*vertex_scale).astype(np.float32)))
            obj.CreateFaceVertexCountsAttr([3]*len(f));obj.CreateFaceVertexIndicesAttr(f.flatten().tolist())
            obj.CreateSubdivisionSchemeAttr('none');obj.CreateDoubleSidedAttr(True)
            if f'uv{g["mesh"]}' in meshes:
                uv=meshes[f'uv{g["mesh"]}'];indices=meshes[f'fuv{g["mesh"]}']
                primvar=UsdGeom.PrimvarsAPI(obj).CreatePrimvar('st',Sdf.ValueTypeNames.TexCoord2fArray,UsdGeom.Tokens.faceVarying)
                primvar.Set(Vt.Vec2fArray.FromNumpy(uv[indices].reshape(-1,2).astype(np.float32)))
        elif kind==2:
            obj=UsdGeom.Sphere.Define(stage,p);obj.CreateRadiusAttr(g['size'][0])
        elif kind==5:
            obj=UsdGeom.Cylinder.Define(stage,p);obj.CreateRadiusAttr(g['size'][0]);obj.CreateHeightAttr(2*g['size'][1]);obj.CreateAxisAttr('Z')
        elif kind==6:
            obj=UsdGeom.Cube.Define(stage,p);obj.CreateSizeAttr(2.)
        elif kind==0:
            obj=UsdGeom.Cube.Define(stage,p);obj.CreateSizeAttr(1.)
            # Finite floor; source plane lies at its upper surface.
            t[:3,3]-=t[:3,:3]@np.array([0.,0.,.01])
        else:raise ValueError(f'Unsupported geom type {kind}')
        set_pose(obj.GetPrim(),t)
        if kind==7 and g['contact'] and vertex_scale==1000.:UsdGeom.Xformable(obj).AddScaleOp().Set(Gf.Vec3f(.001,.001,.001))
        if kind==6:UsdGeom.Xformable(obj).AddScaleOp().Set(Gf.Vec3f(*g['size']))
        if kind==0:UsdGeom.Xformable(obj).AddScaleOp().Set(Gf.Vec3f(4,4,.02))
        if g['group']>=3 or g['rgba'][3]==0:obj.CreateVisibilityAttr('invisible')
        mat=material(g['rgba'],g['friction'][0]);binding=UsdShade.MaterialBindingAPI.Apply(obj.GetPrim());binding.Bind(mat)
        if g['contact']:
            collider_count+=1;UsdPhysics.CollisionAPI.Apply(obj.GetPrim());binding.Bind(mat,materialPurpose='physics')
            if kind==7:
                UsdPhysics.MeshCollisionAPI.Apply(obj.GetPrim()).CreateApproximationAttr('convexHull')
                cooking=PhysxSchema.PhysxConvexHullCollisionAPI.Apply(obj.GetPrim())
                cooking.CreateHullVertexLimitAttr(256)
                cooking.CreateMinThicknessAttr(0.)
            collision=PhysxSchema.PhysxCollisionAPI.Apply(obj.GetPrim())
            collision.CreateContactOffsetAttr(g.get('contact_offset_m',contact_offset));collision.CreateRestOffsetAttr(0.)
            if g.get('torsional_patch_radius_m') and not packet['manifest'].get('grasp_contract',{}).get('spin_contact_model'):
                collision.CreateTorsionalPatchRadiusAttr(g['torsional_patch_radius_m'])
                collision.CreateMinTorsionalPatchRadiusAttr(g['torsional_patch_radius_m'])
        geom_paths[g['name']]=p
    joint_paths={}
    for j in js:
        b=j['body'];parent=owners[bs[b]['parent']];path='/World/Joints/'+j['name']
        hinge=j['kind']==3
        joint=(UsdPhysics.RevoluteJoint if hinge else UsdPhysics.PrismaticJoint).Define(stage,path)
        joint.CreateBody1Rel().SetTargets([Sdf.Path(paths[b])]);joint.CreateAxisAttr('X')
        frame=rest[b]@transform(j['position'],Rotation.align_vectors([j['axis']],[[1.,0,0]])[0].as_matrix())
        dynamic_parent=parent in joint_bodies or (robot and bs[parent]['name']=='ZJ_Robot_link') or (movable_socket and bs[parent]['name']=='sim_socket')
        if dynamic_parent:joint.CreateBody0Rel().SetTargets([Sdf.Path(paths[parent])])
        for side,t in [(0,np.linalg.inv(rest[parent])@frame if dynamic_parent else frame),(1,np.linalg.inv(rest[b])@frame)]:
            getattr(joint,f'CreateLocalPos{side}Attr')().Set(Gf.Vec3f(*t[:3,3]))
            q=quaternion(t[:3,:3]);getattr(joint,f'CreateLocalRot{side}Attr')().Set(Gf.Quatf(float(q[0]),Gf.Vec3f(*q[1:])))
        factor=180/np.pi if hinge else 1.
        if j['limited']:
            joint.CreateLowerLimitAttr(j['limits'][0]*factor)
            joint.CreateUpperLimitAttr((0. if locked and j['name'].startswith('pad_') else j['limits'][1])*factor)
        drive=UsdPhysics.DriveAPI.Apply(joint.GetPrim(),'angular' if hinge else 'linear')
        drive.CreateTypeAttr('force');drive.CreateStiffnessAttr(j['kp']/factor);drive.CreateDampingAttr(j['kd']/factor)
        drive.CreateMaxForceAttr(j['max_force']);drive.CreateTargetPositionAttr(0.)
        joint_paths[j['name']]=path
    if robot:
        base=ids['ZJ_Robot_link'];anchor=UsdPhysics.FixedJoint.Define(stage,'/World/Joints/RobotAnchor')
        anchor.CreateBody1Rel().SetTargets([Sdf.Path(paths[base])])
        anchor.CreateLocalPos0Attr(Gf.Vec3f(*rest[base][:3,3]))
        q=quaternion(rest[base][:3,:3]);anchor.CreateLocalRot0Attr(Gf.Quatf(float(q[0]),Gf.Vec3f(*q[1:])))
        UsdPhysics.ArticulationRootAPI.Apply(anchor.GetPrim())
        aa=PhysxSchema.PhysxArticulationAPI.Apply(anchor.GetPrim())
        aa.CreateEnabledSelfCollisionsAttr(False)
        aa.CreateSolverPositionIterationCountAttr(128 if packet.get('free_bodies') else 32)
        aa.CreateSolverVelocityIterationCountAttr(32 if packet.get('free_bodies') else 4)
        aa.CreateSleepThresholdAttr(0.)
        aa.CreateStabilizationThresholdAttr(0.)
    cameras={}
    for c in packet['cameras']:
        b=c['body'];o=owners[b];path=paths[o]+'/Cameras/'+c['name']
        camera=UsdGeom.Camera.Define(stage,path);set_pose(camera.GetPrim(),np.linalg.inv(rest[o])@rest[b]@local_pose(c))
        camera.CreateFocalLengthAttr(10.);ap=20*np.tan(np.deg2rad(c['fovy'])/2)
        camera.CreateVerticalApertureAttr(ap);camera.CreateHorizontalApertureAttr(ap)
        camera.CreateClippingRangeAttr(Gf.Vec2f(.001,20.));cameras[c['name']]=path
    if robot:
        path='/World/Overview';cam=UsdGeom.Camera.Define(stage,path)
        cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(1.4,-1.3,1.6),Gf.Vec3d(.35,.05,.75),Gf.Vec3d(0,0,1)).GetInverse())
        cam.CreateFocalLengthAttr(24.);cam.CreateClippingRangeAttr(Gf.Vec2f(.001,20));cameras['overview']=path
    else:
        cam=UsdGeom.Camera.Define(stage,'/World/Overview')
        cam.AddTransformOp().Set(Gf.Matrix4d().SetLookAt(Gf.Vec3d(.12,.17,.12),Gf.Vec3d(0,-.015,0),Gf.Vec3d(0,0,1)).GetInverse())
        cam.CreateFocalLengthAttr(35.);cam.CreateClippingRangeAttr(Gf.Vec2f(.001,20));cameras['overview']='/World/Overview'
    UsdLux.DomeLight.Define(stage,'/World/Light').CreateIntensityAttr(1000.)
    audit=dict(version=1,robot=robot,body_paths={bs[k]['name']:v for k,v in paths.items()},
        owners=owners,frame_paths=frame_paths,joint_paths=joint_paths,geom_paths=geom_paths,cameras=cameras,
        collider_count=collider_count,contact_offset_m=contact_offset,rest_offset_m=0.,
        per_collider_contact_offsets_m={g['name']:g['contact_offset_m'] for g in packet['geoms'] if g['contact'] and 'contact_offset_m' in g},
        collision_vertex_scale=1000.,collision_prim_scale=.001,
        locked_pads=locked,lateral_mm=lateral_mm,yaw_deg=yaw_deg,movable_socket=movable_socket,
        transfer=str(directory),transfer_sha256=hashlib.sha256((directory/'transfer.json').read_bytes()).hexdigest(),
        limitations=packet['limitations']+['PhysX convex cooking and drives require dynamic validation',
            'Mimic joints held independently; no physical grasp or robot self contact'])
    Path(output,'scene_manifest.json').write_text(json.dumps(audit,indent=2)+'\n')
    stage.GetRootLayer().Export(str(Path(output,'scene.usda')))
    return packet,audit
