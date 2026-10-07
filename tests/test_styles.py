import importlib.util,copy,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'chibi_generator/model.py';s=importlib.util.spec_from_file_location('style_model',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Styles(unittest.TestCase):
    def test_catalog_references(self):
        self.assertEqual(len(m.STYLES),25)
        for style in m.STYLES.values():
            for slot,weights in style['weights'].items():
                self.assertFalse(set(weights)-set(m.OUTFIT_CATALOG[slot]));self.assertTrue(all(w>0 for w in weights.values()))
            self.assertFalse(set(style['accessories'])-set(m.ACCESSORY_CATALOG))
    def test_reproducibility_and_diversity(self):
        for style in m.STYLES:
            samples=[m.generate_spec(i,style=style) for i in range(80)]
            self.assertEqual(samples[35],m.generate_spec(35,style=style))
            self.assertGreater(len({str(s['outfit']) for s in samples}),10)
    def test_mix_probabilities(self):
        a=m.style_weights({'goth':.7,'egirl':.2,'grunge':.1},'top')
        b={}
        for style,share in [('goth',.7),('egirl',.2),('grunge',.1)]:
            for key,w in m.style_weights({style:1},'top').items():b[key]=b.get(key,0)+w*share
        self.assertEqual(set(a),set(b))
        for key in a:self.assertAlmostEqual(a[key],b[key])
    def test_backward_compatibility_and_independent_groups(self):
        spec=m.generate_spec(7);old=copy.deepcopy(spec)
        for k in ('style','accessories'):del old[k]
        old['outfit']={k:old['outfit'][k] for k in ('top','bottom','shoes')}
        new=m.validate(old);self.assertEqual(new['outfit']['dress'],'none');self.assertEqual(new['accessories'],m.default_accessories());self.assertNotIn('accessories',old)
        fresh=m.apply_style(spec,{'goth':.7,'egirl':.2,'grunge':.1},seed=88)
        for group in ('body','face','makeup'):self.assertEqual(spec[group],fresh[group])
        self.assertEqual(fresh,m.randomize_spec(fresh,98,locked=m.GROUPS))
    def test_invalid_selection(self):
        for style in ({'bad':1},{'goth':-1},{'goth':0},{'goth':float('nan')}):
            with self.assertRaises(ValueError):m.validate_style(style)
        with self.assertRaises(ValueError):m.update_outfit(m.generate_spec(1),dress='bad')
if __name__=='__main__':unittest.main()
