import importlib.util,unittest,tempfile,copy
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'chibi_generator/model.py';s=importlib.util.spec_from_file_location('pose_model',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Poses(unittest.TestCase):
    def test_legacy_and_roundtrip(self):
        spec=m.generate_spec(7);del spec['pose'];old=copy.deepcopy(spec);v=m.validate(spec);self.assertEqual(spec,old);self.assertEqual(v['pose'],m.default_pose())
        v=m.update_pose(v,preset='peace',mirror=True,left='fist',right='point')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pose.json';m.save_preset(v,p);self.assertEqual(m.load_preset(p),v)
    def test_appearance_preserves_pose(self):
        spec=m.update_pose(m.generate_spec(50),preset='wave',mirror=True,left='peace')
        for changed in (m.randomize_spec(spec,90),m.apply_style(spec,{'punk':1},72,True,True),m.update_body(spec,height=.8),m.update_hair(spec,preset='braid')):self.assertEqual(changed['pose'],spec['pose'])
    def test_validation(self):
        spec=m.generate_spec(4)
        for kwargs in ({'preset':'missing'},{'mirror':1},{'left':'missing'},{'right':None},{'surprise':3}):
            with self.assertRaises(ValueError):m.update_pose(spec,**kwargs)
        self.assertEqual(len(m.POSE_PRESETS),10)
        for cfg in m.POSE_PRESETS.values():
            for arm in cfg.get('arms',{}).values():self.assertIn(arm.get('gesture','relaxed'),m.GESTURES)
