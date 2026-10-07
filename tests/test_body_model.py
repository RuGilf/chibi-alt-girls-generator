"""Run with ordinary Python; body sampling needs no Blender installation."""
import copy,importlib.util,json,math,statistics,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'chibi_generator'
spec=importlib.util.spec_from_file_location('chibi_body_model',ROOT/'model.py');model=importlib.util.module_from_spec(spec);spec.loader.exec_module(model)
class BodySampling(unittest.TestCase):
    def test_seed_and_global_random_independence(self):
        import random
        a=model.generate_spec(389);random.seed(8);[random.random() for _ in range(500)];self.assertEqual(a,model.generate_spec(389))
    def test_curvature_frequency(self):
        bodies=[model.sample_body(i) for i in range(10000)];curved=sum(b['curve_severity']>0 for b in bodies)
        self.assertGreater(curved,320);self.assertLess(curved,480)
        self.assertTrue(all(model.sample_body(i,0)['curve_severity']==0 for i in range(100)))
        self.assertTrue(all(model.sample_body(i,1)['curve_severity']>0 for i in range(100)))
    def test_continuous_values_and_leg_balance(self):
        bodies=[model.sample_body(i) for i in range(1000)]
        for k in ('height','thigh_size','calf_size'):
            self.assertGreater(len(set(round(b[k],4) for b in bodies)),850)
            self.assertTrue(all(0<=b[k]<=1 for b in bodies))
        self.assertTrue(all(0<abs(b['leg_asymmetry'])<=.085 for b in bodies))
        self.assertGreater(sum(b['leg_asymmetry']>0 for b in bodies),400)
        self.assertGreater(sum(b['leg_asymmetry']<0 for b in bodies),400)
    def test_json_and_manual_values(self):
        a=model.update_body(model.generate_spec(389),height=.65,leg_asymmetry=-.04)
        with tempfile.TemporaryDirectory() as path:
            p=Path(path)/'preset.json';model.save_preset(a,p);self.assertEqual(a,model.load_preset(p))
    def test_invalid_inputs(self):
        for seed in (-1,2**31,True,'1'):
            with self.assertRaises(ValueError):model.generate_spec(seed)
        for k,v in [('height',1.1),('leg_asymmetry',.2),('curve_severity',float('nan')),('curve_direction',0)]:
            with self.assertRaises(ValueError):model.update_body(model.generate_spec(1),**{k:v})
if __name__=='__main__':unittest.main(verbosity=2)
