"""Tests for metric image-to-surface geometry, shape constraints and label gates."""
import inspect
import json
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
import torch
from image_to_surface_network import ImageToCompleteSurface,rotation_6d,fisheye_rays,project_fisheye,supervised_surface_loss,require_reviewed_annotation


class SurfaceNetworkTests(unittest.TestCase):
    def test_rotation_is_so3_including_degenerate_inputs(self):
        torch.manual_seed(3);x=torch.randn(64,6);x[0]=0;x[1]=torch.tensor([1,0,0,2,0,0]);R=rotation_6d(x)
        torch.testing.assert_close(R@R.transpose(-1,-2),torch.eye(3).expand(64,-1,-1),atol=1e-5,rtol=1e-5)
        torch.testing.assert_close(torch.linalg.det(R),torch.ones(64),atol=1e-5,rtol=1e-5)
        torch.testing.assert_close(rotation_6d(R[:,:2].reshape(64,6)),R,atol=1e-5,rtol=1e-5)

    def test_fisheye_projection_matches_opencv_and_roundtrip(self):
        K=torch.tensor([[656.,0,969],[0,661,551],[0,0,1]],dtype=torch.float64);D=torch.tensor([-.027,-.004,-.002,.003],dtype=torch.float64)
        pixels=torch.tensor([[969,551],[800,700],[1200,950]],dtype=torch.float64,requires_grad=True)
        rays=fisheye_rays(pixels,K,D);projected=project_fisheye(rays*.25,K,D)
        torch.testing.assert_close(projected,pixels,atol=1e-6,rtol=1e-8)
        uv=cv2.fisheye.projectPoints((rays.detach().numpy()*.25).reshape(-1,1,3),np.zeros(3),np.zeros(3),K.numpy(),D.numpy())[0].reshape(-1,2)
        np.testing.assert_allclose(projected.detach().numpy(),uv,atol=1e-6)
        projected.sum().backward();self.assertTrue(torch.isfinite(pixels.grad).all())

    def test_metric_correspondence_loss_and_invalid_labels(self):
        p=torch.tensor([[0.,0,0],[.01,0,0],[0,.02,0]])
        T=torch.eye(4)[None];T[:,2,3]=.3;gt=p[None]+T[:,None,:3,3]
        pred={'module':{'points_m':gt.clone().requires_grad_()}}
        self.assertEqual(float(supervised_surface_loss(pred,{'module':T},{'module':p})),0)
        moved={'module':{'points_m':gt+.01}}
        self.assertGreater(float(supervised_surface_loss(moved,{'module':T},{'module':p})),9)
        with self.assertRaises(ValueError):supervised_surface_loss(pred,{'module':T},{'module':p},{'module':torch.tensor([False])})
        for value in [False,None,'false']:
            with self.assertRaises(ValueError):require_reviewed_annotation({'reviewed':True,'training_label_valid':value})

    def test_forward_image_only_complete_rigid_outputs(self):
        torch.set_num_threads(4)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);counts={'module':16,'socket':32};(folder/'manifest.json').write_text(json.dumps({'recommended_counts':counts}))
            for name,n in counts.items():
                rng=np.random.default_rng(n);points=rng.uniform(-.01,.01,(n,3)).astype('float32');normals=np.tile([0,0,1],(n,1)).astype('float32');np.savez(folder/f'{name}_{n}.npz',points_m=points,normals=normals)
            cal={'K':[[50,0,48],[0,50,32],[0,0,1]],'D':[0,0,0,0],'image_width':96,'image_height':64}
            model=ImageToCompleteSurface(folder,cal).eval()
            self.assertEqual(list(inspect.signature(model.forward).parameters),['images'])
            with torch.no_grad():result=model(torch.rand(1,3,64,96))
            for name,n in counts.items():
                r=result[name];self.assertEqual(tuple(r['points_m'].shape),(1,n,3));self.assertEqual(tuple(r['visibility_logits'].shape),(1,n))
                T=r['T_camera_from_model'];p=getattr(model,name+'_template');expected=p[None]@T[:,:3,:3].transpose(-1,-2)+T[:,None,:3,3]
                torch.testing.assert_close(expected,r['points_m'])
                # cdist's float32 matrix-product path can produce a nonzero
                # diagonal after translating a small object far from origin.
                torch.testing.assert_close(torch.cdist(p[None].double(),p[None].double()),torch.cdist(r['points_m'].double(),r['points_m'].double()),atol=2e-5,rtol=1e-4)
            with self.assertRaises(ValueError):model(torch.ones(1,3,64,96)*255)
            with self.assertRaises(ValueError):model(torch.zeros(1,3,48,48))


if __name__=='__main__':unittest.main()
