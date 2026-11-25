import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'omi_proj/src'))
try:
    import torch
    from copy import deepcopy
    from stable_baselines3.common.type_aliases import DictReplayBufferSamples as Batch
    from omi_hil_rl.hil.networks import SAC,VERSION
    from omi_hil_rl.training.frozen_sac import update_features
except ImportError:torch=None


@unittest.skipIf(torch is None,'optional torch and training dependencies required')
class FrozenSACTests(unittest.TestCase):
    def test_cached_update_matches_real_sac_parameters_and_losses(self):
        torch.set_num_threads(2);torch.manual_seed(3)
        recipe=dict(encoder='synthetic-test');contract=dict(config=dict(transport='fake'))
        a=SAC(recipe,contract,freeze_encoder=True,image_augmentation=False,critic_warmup_updates=1,bc_weight=10.,gamma=.995)
        state=dict(version=VERSION,recipe=recipe,contract=contract,actor=a.actor.state_dict())
        a.initialize_bc(state);b=SAC.restore(a.checkpoint(),expected_contract=contract)
        obs=dict(state=torch.randn(4,10,14),tactile=torch.randn(4,10,10,16,24));nxt={k:v+.01 for k,v in obs.items()}
        batch=Batch(observations=obs,next_observations=nxt,actions=torch.randn(4,6).tanh(),rewards=torch.tensor([[0.],[1.],[-1.],[.2]]),dones=torch.tensor([[0.],[1.],[1.],[0.]]))
        with torch.no_grad():x=a.actor.encoder(obs).clone();nx=a.actor.encoder(nxt).clone()
        cached=Batch(observations={'features':x},next_observations={'features':nx},actions=batch.actions,rewards=batch.rewards,dones=batch.dones)
        for i in range(4):
            torch.manual_seed(100+i);ma=a.update(batch,demonstration_batch=batch)
            torch.manual_seed(100+i);mb=update_features(b,cached,demonstration_batch=cached)
            for name in ['actor','critic','target']:
                for key,value in getattr(a,name).state_dict().items():torch.testing.assert_close(value,getattr(b,name).state_dict()[key],atol=1e-7,rtol=1e-6)
            torch.testing.assert_close(a.temperature_raw,b.temperature_raw,atol=1e-7,rtol=1e-6)
            self.assertAlmostEqual(ma['critic_loss'],mb['critic_loss'],places=6)
            self.assertEqual(a.updates,b.updates)
        b.image_augmentation=True
        with self.assertRaises(ValueError):update_features(b,cached,demonstration_batch=cached)


if __name__=='__main__':unittest.main()
