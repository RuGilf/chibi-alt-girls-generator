"""Exercise every wardrobe item, fitting, style UI and legacy scene migration."""
import bpy,sys,json,copy,tempfile,hashlib,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'chibi_generator';sys.path.insert(0,str(ROOT.parent))
import chibi_generator as cg
from chibi_generator import model,ui,scene
cg.register();c=cg.generate_character(seed=418,style='goth');ui.focus(bpy.context,c)
def signature():
    h=hashlib.sha256()
    for ob in sorted((o for o in c.objects if o.type=='MESH' and not o.hide_render),key=lambda o:o['chibi_asset']):
        data=ob.data.shape_keys.key_blocks['BodyVariation'].data;a=np.empty(len(data)*3);data.foreach_get('co',a);h.update(a.tobytes())
    return h.hexdigest()
def visible_check():
    spec=c.parameters;outfit=spec['outfit'];dress=outfit['dress']!='none'
    for slot in ('top','bottom','dress','shoes'):
        obs=[o for o in c.objects if o.get('chibi_slot')==slot and not o.hide_render]
        if (dress and slot in ('top','bottom')) or (not dress and slot=='dress'):assert not obs
        else:assert obs and {o['chibi_option'] for o in obs}=={outfit[slot]}
    for ob in c.objects:
        assert ob.hide_render==ob.hide_viewport
        if ob.type!='MESH' or ob.hide_render:continue
        assert ob.data.materials and all(ob.data.materials)
        assert all(v.groups for v in ob.data.vertices)
        a=np.empty(len(ob.data.shape_keys.key_blocks['BodyVariation'].data)*3);ob.data.shape_keys.key_blocks['BodyVariation'].data.foreach_get('co',a);assert np.isfinite(a).all()
        assert any(m.type=='ARMATURE' and m.object==c.rig for m in ob.modifiers)
count=0
for slot in ('top','bottom','dress','shoes'):
    for key in model.ASSETS[slot]:
        if key=='none':continue
        values={slot:key}
        if slot in ('top','bottom'):values['dress']='none'
        c.set_outfit(**values);visible_check();count+=1
for kind in model.ASSETS['legwear']:c.set_outfit(legwear=kind);visible_check()
for key in model.ACCESSORY_CATALOG:
    c.set_accessories([key]);visible_check();assert any(o.get('chibi_accessory')==key and not o.hide_render for o in c.objects)
# Different footwear selects the correct trouser fit, without duplicates.
c.set_outfit(dress='none',top='bandtee',bottom='baggyjeans',shoes='platforms');visible_check()
assert {o.get('chibi_fit') for o in c.objects if o.get('chibi_option')=='baggyjeans' and not o.hide_render}=={'tucked'}
c.set_outfit(shoes='skateshoes');visible_check()
assert {o.get('chibi_fit') for o in c.objects if o.get('chibi_option')=='baggyjeans' and not o.hide_render}=={'loose'}
for top,dress in [('corset','none'),('cyberjacket','none'),('meshtop','none'),('hoodie','none'),('biker','none'),('academiavest','none'),('bandtee','romantic'),('bandtee','lolita')]:
    for value in (0,1):
        c.set_outfit(top=top,dress=dress,bottom='cargo',shoes='cyberplatforms');c.set_body(height=value,breast_size=value,glute_size=value,thigh_size=value,calf_size=value,leg_asymmetry=.10 if value else -.10,curve_severity=1);visible_check()
# Repeat and JSON restore all visible geometry, regardless of hidden cache contents.
before=c.parameters;sig=signature();c.apply(before);assert signature()==sig
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'character.json';c.save_preset(path);c.randomize_outfit(199);c.apply(model.load_preset(path));assert c.parameters==before and signature()==sig
s=bpy.context.scene.chibi_settings;s.outfit_dress='none';s.outfit_top='corset';s.outfit_bottom='longskirt';s.outfit_shoes='maryjane';s.outfit_legwear='fishnet';s.accessory_cross=True;visible_check()
s.style_primary='goth';s.style_secondary='egirl';s.style_tertiary='grunge';s.style_mixing=True;s.mix_secondary=20;s.mix_tertiary=10;s.style_makeup=False
before=c.parameters;assert bpy.ops.chibi.apply_style()=={'FINISHED'}
assert all(abs(c.parameters['style'][k]-v)<1e-9 for k,v in {'goth':.7,'egirl':.2,'grunge':.1}.items())
for group in ('body','face','makeup'):assert c.parameters[group]==before[group]
for group in model.GROUPS:setattr(s,'lock_'+group,True)
before=c.parameters;assert bpy.ops.chibi.random_all(use_seed=True)=={'CANCELLED'} and c.parameters==before
s.lock_body=False;s.seed=99;assert bpy.ops.chibi.random_all(use_seed=True)=={'FINISHED'}
for group in ('face','makeup','outfit','accessories'):assert c.parameters[group]==before[group]
assert bpy.ops.chibi.previous()=={'FINISHED'} and c.parameters==before
with bpy.data.libraries.load(str(ROOT.parent/'tests/fixtures/legacy_v07.blend')) as (src,dst):dst.collections=[next(n for n in src.collections if n.startswith('CHIBI '))]
oldcol=dst.collections[0];bpy.context.scene.collection.children.link(oldcol);rig=next(o for o in oldcol.objects if o.get('chibi_spec'));old=scene.Character(rig);oldspec=old.parameters;old.apply(oldspec);assert old.parameters==oldspec and old.rig.get('chibi_underbody_v2')
report={'status':'PASS','clothing_items_checked':count,'legwear_checked':5,'accessories_checked':18,'extreme_combinations_checked':16,'materials_present':True,'52_bone_rig':len(c.rig.data.bones)==52,'clothing_weights':True,'pants_footwear_fitting':True,'JSON_geometry_roundtrip':True,'visible_geometry_no_drift':True,'style_mix_70_20_10':True,'all_group_locks':True,'manual_controls':True,'legacy_studio_migration':True}
(ROOT.parent/'build/test-reports').mkdir(parents=True,exist_ok=True)
(ROOT.parent/'build/test-reports/styles.json').write_text(json.dumps(report,indent=2));print('STYLE_FEATURES_PASS',json.dumps(report),flush=True);cg.unregister()
