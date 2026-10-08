"""Public face controls must migrate, round-trip and remain independently seeded."""
import copy,importlib.util,unittest
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'chibi_generator/model.py'
spec=importlib.util.spec_from_file_location('face_detail_model',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class FaceDetails(unittest.TestCase):
    def test_old_presets_get_neutral_details_without_mutation(self):
        old=m.generate_spec(9100)
        for key in m.FACE_DETAIL_DEFAULTS:del old['face'][key]
        before=copy.deepcopy(old);new=m.validate(old)
        self.assertEqual(old,before)
        for key,value in m.FACE_DETAIL_DEFAULTS.items():self.assertEqual(new['face'][key],value)
        self.assertEqual(m.validate(new),new)
    def test_independent_details_and_limits(self):
        source=m.generate_spec(14)
        for key in m.FACE_DETAIL_DEFAULTS:
            for value in (-1,1):
                changed=m.update_face(source,**{key:value})
                self.assertEqual(changed['face'][key],value)
                for group in (*m.GROUPS,'pose'):
                    if group!='face':self.assertEqual(source[group],changed[group])
            for value in (None,True,'1',1.01,float('nan')):
                with self.assertRaises(ValueError):m.update_face(source,**{key:value})
    def test_face_presets_and_determinism(self):
        self.assertEqual(m.sample_face(12),m.sample_face(12))
        source=m.generate_spec(10)
        for key in m.FACE_PRESETS:
            changed=m.update_face(source,preset=key,expression='wink')
            self.assertEqual(changed['face']['expression'],'wink')
            for field in m.FACE_DETAIL_DEFAULTS:self.assertEqual(changed['face'][field],m.FACE_PRESETS[key][1][field])

if __name__=='__main__':unittest.main()
