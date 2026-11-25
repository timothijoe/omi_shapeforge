import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'scripts/simulation/run_isaac_diverse_study.py'
spec=importlib.util.spec_from_file_location('diverse_study_plan',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class DiversePlanTests(unittest.TestCase):
    def test_fifty_slots_disjoint_splits_and_fixed_retries(self):
        train=module.scenarios('training',20000,[('normal',16),('alignment',16),('recovery',8)])
        val=module.scenarios('validation',40000,[('normal',4),('alignment',4),('recovery',2)])
        test=module.scenarios('test',60000,[('normal',4),('alignment',2),('recovery',2)],retries=1)
        self.assertEqual([len(train),len(val),len(test)],[40,10,8])
        sets=[{c['seed'] for s in group for c in s['candidates']} for group in (train,val,test)]
        self.assertTrue(sets[0].isdisjoint(sets[1]) and sets[0].isdisjoint(sets[2]) and sets[1].isdisjoint(sets[2]))
        self.assertEqual(len(sets[0]),120);self.assertEqual(len(sets[1]),30)
        alignment=[s['candidates'][0] for s in train if s['candidates'][0]['kind']=='alignment']
        self.assertEqual(len({(c['x_mm'],c['z_mm']) for c in alignment}),16)
        for slot in train+val:
            self.assertEqual(len(slot['candidates']),3)
            self.assertEqual(len({(c['kind'],c['x_mm'],c['z_mm']) for c in slot['candidates']}),1)


if __name__=='__main__':unittest.main()
