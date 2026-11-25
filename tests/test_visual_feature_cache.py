import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'omi_proj/src'))
try:
    import torch
    from omi_hil_rl.hil.networks import Actor
    from omi_hil_rl.training.eef_bc_grid import GridProfile
    from omi_hil_rl.training.visual_feature_cache import configure_visual_bc,frozen_parts,project_cached
except ImportError:torch=None


@unittest.skipIf(torch is None,'optional torch / OMI training dependencies required')
class VisualFeatureCacheTests(unittest.TestCase):
    def test_missing_history_cache_parity_and_trainable_layers(self):
        torch.set_num_threads(2);torch.manual_seed(13)
        recipe=dict(encoder='current9stack',base_contract=GridProfile('required').CONTRACT,
                    normalization=dict(tactile_mean=[0.]*10,tactile_std=[1.]*10,state_mean=[0.]*14,state_std=[1.]*14))
        actor=Actor(recipe);parameters=configure_visual_bc(actor)
        obs=dict(rgb=torch.randint(0,256,(2,10,3,128,128),dtype=torch.uint8),
                 wrist_rgb=torch.randint(0,256,(2,10,3,128,128),dtype=torch.uint8),
                 tactile=torch.zeros(2,10,10,16,24),state=torch.zeros(2,10,14),
                 camera_mask=torch.ones(2,10,2),history_mask=torch.ones(2,10,dtype=torch.uint8))
        obs['history_mask'][0,:9]=0
        cached=frozen_parts(actor,obs)
        with torch.no_grad():direct=actor.encoder(obs)
        result=project_cached(actor,cached)
        torch.testing.assert_close(result,direct,atol=2e-6,rtol=2e-5)
        result.square().mean().backward()
        for module in (actor.encoder.model.current_projection,actor.encoder.model.history_projection,actor.encoder.model.head):
            self.assertTrue(any(p.grad is not None and torch.any(p.grad!=0) for p in module.parameters()))
        self.assertFalse(any(p.requires_grad or p.grad is not None for p in actor.encoder.model.backbone.parameters()))
        self.assertFalse(any(p.requires_grad for p in actor.encoder.model.history_stem.parameters()))
        actor.encoder.model.history_stem.requires_grad_(True)
        with self.assertRaises(ValueError):frozen_parts(actor,obs)


if __name__=='__main__':unittest.main()
