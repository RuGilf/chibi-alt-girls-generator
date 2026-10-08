"""Face shape controls, eyelid volume, material ownership and old saves."""
import json,sys,tempfile
from pathlib import Path
import bpy,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import chibi_generator as cg
from chibi_generator import model,scene,ui
cg.register();c=scene.generate_character(seed=9100);ui.focus(bpy.context,c)
c.set_face(preset='classic',expression='calm')
def obj(name):return next(o for o in c.objects if o.get('chibi_asset','').split('.')[0]==name and not o.hide_render)
def points(ob):return np.array([v.co[:] for v in ob.data.shape_keys.key_blocks['BodyVariation'].data])
fields={'nose_width':('Button nose',0),'nose_projection':('Button nose',1),
        'mouth_width':('Lip colour layer',0),'lip_fullness':('Lip colour layer',2),
        'brow_height':('Brow 1',2),'brow_arch':('Brow 1',2)}
for field,(name,axis) in fields.items():
    before=c.parameters
    c.set_face(**{field:-1});low=points(obj(name))
    c.set_face(**{field:1});high=points(obj(name))
    assert np.isfinite(high).all() and not np.allclose(low[:,axis],high[:,axis]),field
    c.apply(before)
# Lip seam/highlight own their colors independently from nose and lower eyelid.
assert obj('Quiet rose smile').data.materials[0]!=obj('Lower lid 1').data.materials[0]
assert obj('Lower lip highlight').data.materials[0]!=obj('Button nose').data.materials[0]
nose=obj('Button nose').data.materials[0];tone=tuple(nose.node_tree.nodes['Chibi skin tone'].outputs[0].default_value)
c.set_makeup(preset='berry');assert tone==tuple(nose.node_tree.nodes['Chibi skin tone'].outputs[0].default_value)
for preset in model.FACE_PRESETS:
    c.set_face(preset=preset,expression='wink')
    for name in ('Almond sclera','Large violet iris','Pupil','Main catchlight','Lower lid'):
        closed=next(o for o in c.objects if o.get('chibi_asset','').split('.')[0]==name+' 1')
        assert closed.hide_render and closed.hide_viewport
        assert not obj(name+' -1').hide_render
    liner=points(obj('Upper eyeliner 1')).reshape(-1,10,3)
    cross_section=liner-liner.mean(axis=1,keepdims=True)
    assert np.median(np.linalg.svd(cross_section,compute_uv=False)[:,1])>.003,'Closed eyelid lost its tube volume'
    for expression in model.EXPRESSIONS:
        c.set_face(expression=expression)
        for ob in c.objects:
            if ob.type=='MESH' and not ob.hide_render:assert np.isfinite(points(ob)).all()
    c.set_face(expression='calm');assert not obj('Almond sclera 1').hide_render
for field in fields:
    setattr(bpy.context.scene.chibi_settings,field,.37)
    assert abs(c.parameters['face'][field]-.37)<1e-6
old=c.parameters
for key in model.FACE_DETAIL_DEFAULTS:del old['face'][key]
c.apply(old)
assert all(c.parameters['face'][k]==0 for k in model.FACE_DETAIL_DEFAULTS)
before=c.parameters;geometry=points(obj('Lip colour layer'));counts=(len(c.objects),len(bpy.data.materials))
for _ in range(3):c.apply(before)
assert counts==(len(c.objects),len(bpy.data.materials)) and np.array_equal(geometry,points(obj('Lip colour layer')))
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'face.json';c.save_preset(p);c.set_face(nose_width=.8,expression='wink');c.apply(model.load_preset(p));assert c.parameters==before
report=dict(status='PASS',six_independent_face_controls=True,closed_eyelid_keeps_volume=True,
            wink_visibility_roundtrip=True,all_face_presets_and_expressions=True,
            lip_materials_isolated=True,manual_UI=True,old_JSON_defaults=True,no_geometry_or_material_drift=True,JSON_roundtrip=True)
out=ROOT/'build/test-reports';out.mkdir(parents=True,exist_ok=True);(out/'face_details.json').write_text(json.dumps(report,indent=2))
print('FACE_DETAILS_PASS',report,flush=True);cg.unregister()
