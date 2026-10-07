import importlib.util,unittest,copy,tempfile
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'chibi_generator/model.py';s=importlib.util.spec_from_file_location('appearance_model',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Appearance(unittest.TestCase):
    def test_catalog_and_style_weights(self):
        self.assertEqual(len(m.HAIR_PRESETS),30);self.assertEqual(len(m.SKIN_TONES),12)
        self.assertEqual(set(m.HAIR_CONFIG['style_weights']),set(m.STYLES))
        for weights in m.HAIR_CONFIG['style_weights'].values():self.assertFalse(set(weights)-set(m.HAIR_PRESETS));self.assertTrue(all(v>0 for v in weights.values()))
    def test_seed_diversity_and_independent_groups(self):
        samples=[m.generate_spec(i) for i in range(1000)]
        self.assertEqual({x['hair']['preset'] for x in samples},set(m.HAIR_PRESETS));self.assertEqual({x['skin']['preset'] for x in samples},set(m.SKIN_TONES))
        self.assertEqual(samples[50],m.generate_spec(50))
        old=samples[0];new=m.randomize_spec(old,50,locked=('hair','skin'))
        self.assertEqual(new['hair'],old['hair']);self.assertEqual(new['skin'],old['skin'])
        new=m.apply_style(old,{'egirl':1},50,include_hair=True)
        for group in ('body','face','skin'):self.assertEqual(new[group],old[group])
        self.assertIn(new['hair']['preset'],m.HAIR_CONFIG['style_weights']['egirl'])
    def test_legacy_and_JSON(self):
        spec=m.generate_spec(7);del spec['hair'];del spec['skin'];old=copy.deepcopy(spec);new=m.validate(spec)
        self.assertEqual(spec,old);self.assertEqual(new['hair'],m.default_hair());self.assertEqual(new['skin'],m.default_skin())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'preset.json';m.save_preset(new,path);self.assertEqual(m.load_preset(path),new)
    def test_colors_and_validation(self):
        self.assertEqual(m.skin_rgb(m.default_skin()),(.66,.36,.265))
        for preset in m.SKIN_TONES:
            for shade in (-.25,.25):
                for undertone in (-.25,.25):self.assertTrue(all(0<c<1 for c in m.skin_rgb(dict(preset=preset,shade=shade,undertone=undertone))))
        for values in ({'preset':'bad'},{'pattern':'bad'},{'color':'bad'}):
            with self.assertRaises(ValueError):m.update_hair(m.generate_spec(1),**values)
        for values in ({'shade':float('nan')},{'undertone':.3},{'preset':'bad'}):
            with self.assertRaises(ValueError):m.update_skin(m.generate_spec(1),**values)
if __name__=='__main__':unittest.main()
