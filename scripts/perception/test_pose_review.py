"""Geometry/persistence checks, run in the foundation_stereo environment."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from pose_review_geometry import matrix, pose, project, optical_extrinsic, refine_pixels, validate_matrix, guided_initialize, transform, coarse_candidates
from pose_review_server import Review, GUIDES


CAL={'K':[[656,0,969],[0,661,551],[0,0,1]],'D':[-.027,-.004,-.002,.003],'distortion_model':'opencv_fisheye'}


class Geometry(unittest.TestCase):
    def test_euler_metric_roundtrip(self):
        T=matrix([20,-30,650,21,-35,140])
        np.testing.assert_allclose(matrix(pose(T)),T,atol=1e-12)
        np.testing.assert_allclose(T[:3,3],[.02,-.03,.65])

    def test_cross_camera_and_object_invariance(self):
        hm=matrix([10,20,650,30,40,50]);hs=matrix([30,-80,710,10,20,30]);wh=matrix([30,-50,180,45,-15,4])
        wm=wh@hm;ws=wh@hs
        np.testing.assert_allclose(wm@np.linalg.inv(hm),wh,atol=1e-12)
        np.testing.assert_allclose(np.linalg.inv(ws)@wm,np.linalg.inv(hs)@hm,atol=1e-12)

    def test_extrinsic_column_major(self):
        a=matrix([15,2,-3,5,10,15]);b=matrix([0,0,1,0,0,0])
        def entry(T):return {'rotation':T[:3,:3].flatten(order='F').tolist(),'translation':T[:3,3].tolist(),'rotation_order':'column-major'}
        np.testing.assert_allclose(optical_extrinsic({'extrinsics':{'depth_to_color':entry(a),'depth_to_infra1':entry(b)}}),a@np.linalg.inv(b))

    def test_fisheye_analytic(self):
        q=np.array([[.03,.04,.1],[0,0,.2]])
        uv,good=project(q,np.eye(4),CAL);theta=np.arctan(.5);rad=theta*sum([1]+[d*theta**(2*i+2) for i,d in enumerate(CAL['D'])])
        np.testing.assert_allclose(uv[0],[969+656*.6*rad,551+661*.8*rad],atol=1e-8)
        np.testing.assert_allclose(uv[1],[969,551]);self.assertTrue(good.all())

    def test_correspondence_recovery_and_degeneracy(self):
        p=np.array([[-.009,-.03,-.004],[.009,-.03,-.004],[-.009,.03,.006],[.009,.03,.006],[0,0,.005],[.005,.02,-.003]])
        truth=matrix([3,40,200,-20,10,4]);uv,_=project(p,truth,CAL);initial=matrix([5,38,203,-18,9,5])
        r=refine_pixels(p,uv,initial,CAL)
        self.assertLess(r['rms_after_px'],1e-4)
        np.testing.assert_allclose(r['T'],truth,atol=1e-5)
        with self.assertRaises(ValueError):refine_pixels(np.zeros((4,3)),np.zeros((4,2)),truth,CAL)
        with self.assertRaises(ValueError):refine_pixels(p[:3],uv[:3],truth,CAL)

    def test_invalid_pose_rejected(self):
        with self.assertRaises(ValueError):matrix([0,0,float('nan'),0,0,0])
        with self.assertRaises(ValueError):validate_matrix(np.zeros((4,4)))

    def test_guided_seed_uses_camera_and_depth_without_flip(self):
        cal={'K':[1300,0,960,0,1300,540,0,0,1],'D':[0]*5,'distortion_model':'plumb_bob'}
        identity={'rotation':np.eye(3).ravel().tolist(),'translation':[0,0,0],'rotation_order':'column-major'}
        meta={'calibration':{'color':cal},'extrinsics':{'depth_to_color':identity,'depth_to_infra1':identity}}
        anchors=np.array(GUIDES['module']['points']);truth=matrix([20,-40,700,-130,3,175])
        rng=np.random.default_rng(4);patches=[]
        for p in anchors:
            q=np.repeat(p[None],400,axis=0);q[:,:2]+=rng.uniform(-.004,.004,(400,2));patches.append(q)
        cloud=transform(np.concatenate(patches),truth);pixels,_=project(anchors,truth,cal)
        result=guided_initialize(anchors,pixels,cloud,meta);estimated=np.array(result['T'])
        self.assertLess(result['pixel_rms'],1)
        self.assertLess(np.linalg.norm(estimated[:3,3]-truth[:3,3]),.003)
        from scipy.spatial.transform import Rotation
        self.assertLess(Rotation.from_matrix(estimated[:3,:3]@truth[:3,:3].T).magnitude(),np.deg2rad(3))
        with self.assertRaises(ValueError):guided_initialize(anchors,np.repeat(pixels[:1],4,axis=0),cloud,meta)

    def test_local_fit_never_restarts_global_orientation_search(self):
        rng=np.random.default_rng(2);model=rng.uniform(-.02,.02,(1000,3));initial=matrix([20,30,700,-125,1,170])
        observed=transform(model,initial)+[.001,0,0]
        candidates=coarse_candidates(model,observed,initial)
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]['method'],'bounded_local_cloud_refinement')
        self.assertLess(candidates[0]['translation_change_mm'],5)
        self.assertLess(candidates[0]['rotation_change_deg'],5)


class CloudColors(unittest.TestCase):
    def test_projected_color_and_outside_fov(self):
        import cv2
        with tempfile.TemporaryDirectory() as temp:
            app=Review.__new__(Review);p=Path(temp);im=np.zeros((10,10,3),np.uint8);im[:]=[0,0,255];cv2.imwrite(str(p/'head.png'),im)
            ident={'rotation':np.eye(3).ravel().tolist(),'translation':[0,0,0]}
            meta={'images':{'color':{'file':'head.png'}},'calibration':{'color':{'K':[10,0,5,0,10,5,0,0,1],'D':[0]*5}},'extrinsics':{'depth_to_color':ident,'depth_to_infra1':ident}}
            app.samples={'test':{'path':p,'meta':meta}}
            app.cloud=lambda _: (np.array([[0,0,1],[10,0,1.]]),np.zeros((2,3)))
            xyz,rgb,uv=app.colored_cloud('test')
            np.testing.assert_array_equal(rgb[0],[1,0,0])
            np.testing.assert_array_equal(rgb[1],[.25,.25,.25])
            np.testing.assert_array_equal(uv[1],[-10000,-10000])
            np.testing.assert_array_equal(xyz,[[0,0,1],[10,0,1]])

    def test_display_keeps_dense_roi_points_and_eight_column_schema(self):
        app=Review.__new__(Review);n=200000;xyz=np.zeros((n,3));rgb=np.ones((n,3));uv=np.full((n,2),-10000.)
        uv[100001:100401]=[100,100]
        app.colored_cloud=lambda _: (xyz,rgb,uv)
        app.state=lambda _: {'objects':{'module':{'roi':[90,90,110,110]},'socket':{'roi':None}}}
        payload=app.display_cloud('test')
        self.assertEqual(payload.shape[1],8)
        self.assertEqual(np.sum(payload[:,6]==100),400)


class Persistence(unittest.TestCase):
    def test_atomic_save_identity_conflict_and_history(self):
        import threading
        with tempfile.TemporaryDirectory() as temp:
            app=Review.__new__(Review);app.output=Path(temp);app.lock=threading.RLock();app.binding={'new_capture_identity_verified':False}
            app.samples={'one':{'meta':{'images':{}},'metadata_sha256':'hash','legacy':None},'two':{'meta':{'images':{}},'metadata_sha256':'other','legacy':None}}
            app.models={k:{'vertices':np.zeros((5,3)),'version':'test'} for k in ['module','socket']}
            d=app.blank('one');d['objects']['module']['head']=matrix([0,0,600,0,0,0]).tolist()
            r=app.save('one',d);self.assertEqual(r['revision'],1);self.assertFalse(r['training_label_valid'])
            self.assertIsNone(app.state('two')['objects']['module']['head'])
            with self.assertRaises(ValueError):app.save('one',d)
            with self.assertRaises(ValueError):app.save('two',r)
            r['notes']='second';r=app.save('one',r);self.assertEqual(len(list((Path(temp)/'history/one').glob('*.json'))),2)
            self.assertEqual(app.state('one')['notes'],'second')


if __name__=='__main__':unittest.main()
