"""Regression tests for relative-pose metrics and image-only train/infer paths."""
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
from image_to_surface_network import ImageToCompleteSurface
from train_sim_wrist_surface import errors,Frames,training_statistics


class SimLearningTests(unittest.TestCase):
    def test_relative_tip_invariant_to_common_camera_transform(self):
        gt=torch.eye(4,dtype=torch.float64).repeat(2,2,1,1);gt[:,0,:3,3]=torch.tensor([.01,.03,.2]);gt[:,1,:3,3]=torch.tensor([.02,-.01,.3])
        S=torch.tensor([[0.,-1,0,.05],[1,0,0,-.03],[0,0,1,.1],[0,0,0,1]],dtype=torch.float64)
        out=errors(S[None,None]@gt,gt)
        self.assertLess(float(out['tip_in_socket_error_mm'].max()),1e-9)
        self.assertGreater(float(out['translation_mm'].mean()),10)

    def test_one_mm_module_translation(self):
        gt=torch.eye(4,dtype=torch.float64).repeat(1,2,1,1);gt[:,:,2,3]=.25;pred=gt.clone();pred[:,0,0,3]+=.001
        e=errors(pred,gt);self.assertAlmostEqual(float(e['translation_mm'][0,0]),1);self.assertAlmostEqual(float(e['tip_in_socket_error_mm'][0]),1)

    def test_untrusted_real_candidate_not_accepted_as_sim_label(self):
        d=Frames('/nonexistent',[{'training_label_valid':False,'real_world_ground_truth':False}])
        with self.assertRaises(ValueError):d[0]

    def test_prior_and_fast_path_survive_state_restore(self):
        torch.set_num_threads(4)
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);counts={'module':16,'socket':32};(folder/'manifest.json').write_text(json.dumps({'recommended_counts':counts}))
            for name,n in counts.items():np.savez(folder/f'{name}_{n}.npz',points_m=np.zeros((n,3),np.float32),normals=np.tile([0.,0,1],(n,1)).astype(np.float32))
            cal={'K':[[50,0,48],[0,50,32],[0,0,1]],'D':[0,0,0,0],'image_width':96,'image_height':64}
            model=ImageToCompleteSurface(folder,cal).eval();T=torch.diag(torch.tensor([-1.,1,-1,1]));T[2,3]=.3
            model.initialize_from_training_prior({'module':T,'socket':T});x=torch.rand(1,3,64,96)
            with torch.no_grad():fast=model.estimate_poses(x);full=model(x)
            for name in counts:torch.testing.assert_close(fast[name]['T_camera_from_model'],full[name]['T_camera_from_model'])
            other=ImageToCompleteSurface(folder,cal).eval();other.load_state_dict(model.state_dict())
            self.assertTrue(bool(other.attention_prior_enabled))
            with torch.no_grad():restored=other.estimate_poses(x)
            for name in counts:torch.testing.assert_close(fast[name]['T_camera_from_model'],restored[name]['T_camera_from_model'])


if __name__=='__main__':unittest.main()
