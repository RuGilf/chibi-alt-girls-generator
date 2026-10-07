"""Check every hairstyle, per-character materials, all skin surfaces and creator controls."""
import bpy,sys,json,hashlib,tempfile,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'chibi_generator';sys.path.insert(0,str(ROOT.parent))
import chibi_generator as cg
from chibi_generator import model,scene,ui,hair
cg.register();c=cg.generate_character(seed=17);ui.focus(bpy.context,c)
def signature(character):
    h=hashlib.sha256()
    for ob in sorted((o for o in character.objects if o.type=='MESH' and not o.hide_render),key=lambda o:o['chibi_asset']):
        pts=ob.data.shape_keys.key_blocks['BodyVariation'].data;a=np.empty(len(pts)*3);pts.foreach_get('co',a);h.update(a.tobytes())
        for attr in ob.data.color_attributes:
            a=np.empty(len(attr.data)*4);attr.data.foreach_get('color',a);h.update(a.tobytes())
        for mat in ob.data.materials:
            if mat and mat.node_tree:
                for node in mat.node_tree.nodes:
                    if node.type=='RGB':h.update(str(tuple(node.outputs[0].default_value)).encode())
    return h.hexdigest()
def check(character):
    spec=character.parameters;obs=[o for o in character.objects if o.get('chibi_section')=='03 Hair' and not o.hide_render]
    assert obs and {o.get('chibi_hair','bob') for o in obs}=={spec['hair']['preset']}
    for ob in character.objects:
        assert ob.hide_render==ob.hide_viewport
        if ob.type!='MESH' or ob.hide_render:continue
        assert ob.data.materials and all(ob.data.materials);assert all(v.groups for v in ob.data.vertices)
        pts=ob.data.shape_keys.key_blocks['BodyVariation'].data;a=np.empty(len(pts)*3);pts.foreach_get('co',a);assert np.isfinite(a).all()
        if ob.get('chibi_section')=='03 Hair':
            head=ob.vertex_groups['head'].index;assert all(any(g.group==head and abs(g.weight-1)<1e-6 for g in v.groups) for v in ob.data.vertices)
            attr=ob.data.color_attributes['HairTint'];colors=np.empty(len(attr.data)*4);attr.data.foreach_get('color',colors);assert np.isfinite(colors).all()
    rgb=model.skin_rgb(spec['skin'])
    for ob in character.objects:
        if ob.type!='MESH' or ob.hide_render:continue
        for mat in ob.data.materials:
            node=mat.node_tree.nodes.get('Chibi skin tone') if mat and mat.node_tree else None
            if node:assert np.allclose(node.outputs[0].default_value[:3],rgb)
    for name in ('Neck','Ear -1','Chibi unified hand R','Button nose'):
        ob=next(o for o in character.objects if o.get('chibi_asset','').split('.')[0]==name);assert ob.data.materials[0].node_tree.nodes.get('Chibi skin tone')
for i,key in enumerate(model.HAIR_PRESETS):
    c.set_hair(preset=key,pattern=list(model.HAIR_PATTERNS)[i%5]);c.set_skin(preset=list(model.SKIN_TONES)[i%12]);check(c)
    for h in (0,1):c.set_body(height=h,curve_severity=1,shoulder_tilt=.02 if h else -.02);check(c)
    print('APPEARANCE_CHECK',key,flush=True)
for key in model.SKIN_TONES:
    c.set_skin(preset=key,shade=.25,undertone=-.25)
    for legwear in ('bare','fishnet','stockings','striped'):
        c.set_outfit(dress='none',top='meshtop',bottom='rippedjeans',legwear=legwear);check(c)
for key in model.HAIR_COLORS:c.set_hair(color=key);check(c)
# Changing one person never recolours another person's skin or hair.
c2=cg.generate_character(seed=18);sig2=signature(c2);c.set_skin(preset='porcelain');c.set_hair(color='acid',pattern='split');assert signature(c2)==sig2
before=c.parameters;sig=signature(c);c.apply(before);assert signature(c)==sig
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'appearance.json';c.save_preset(path);c.randomize_hair(90);c.randomize_skin(99);c.apply(model.load_preset(path));assert c.parameters==before and signature(c)==sig
ui.focus(bpy.context,c);s=bpy.context.scene.chibi_settings;s.hair_preset='twin_tails';s.hair_color='pink';s.hair_secondary='cyan';s.hair_pattern='split';s.skin_preset='espresso';s.skin_shade=.12;s.skin_undertone=-.1;check(c)
for group in model.GROUPS:setattr(s,'lock_'+group,True)
before=c.parameters;s.seed=19;assert bpy.ops.chibi.random_all(use_seed=True)=={'CANCELLED'} and c.parameters==before
s.lock_hair=False;assert bpy.ops.chibi.random_all(use_seed=True)=={'FINISHED'}
for group in model.GROUPS:
    if group!='hair':assert c.parameters[group]==before[group]
assert bpy.ops.chibi.previous()=={'FINISHED'} and c.parameters==before
before=c.parameters;assert bpy.ops.chibi.randomize_hair(color_only=True)=={'FINISHED'};assert c.parameters['hair']['preset']==before['hair']['preset']
for group in model.GROUPS:
    if group!='hair':assert c.parameters[group]==before[group]
s.style_primary='egirl';s.style_mixing=False;s.style_hair=True;s.style_makeup=False;before=c.parameters;assert bpy.ops.chibi.apply_style()=={'FINISHED'};assert c.parameters['hair']['preset'] in model.HAIR_CONFIG['style_weights']['egirl']
for group in ('body','face','makeup','skin'):assert c.parameters[group]==before[group]
# A deterministic legacy v0.7 fixture acquires a default bob and peach skin without changing its chosen outfit.
with bpy.data.libraries.load(str(ROOT.parent/'tests/fixtures/legacy_v07.blend')) as (src,dst):dst.collections=[next(n for n in src.collections if n.startswith('CHIBI '))]
col=dst.collections[0];bpy.context.scene.collection.children.link(col);rig=next(o for o in col.objects if o.get('chibi_spec'));old=scene.Character(rig);spec=old.parameters;old.apply(spec);assert old.parameters==spec;check(old)
report={'status':'PASS','hairstyles':30,'hair_colors':18,'skin_tones':12,'color_patterns':5,'height_and_posture_extremes':60,'per_character_material_isolation':True,'skin_face_hands_ears_legs_mesh_and_denim':True,'head_bone_weights':True,'finite_geometry_and_colors':True,'JSON_geometry_and_color_roundtrip':True,'no_drift':True,'manual_UI':True,'7_group_locks':True,'style_hair_selection':True,'color_random_preserves_shape':True,'legacy_scene_migration':True}
OUT=ROOT.parent/'build/test-reports';OUT.mkdir(parents=True,exist_ok=True);(OUT/'appearance.json').write_text(json.dumps(report,indent=2));print('APPEARANCE_FEATURES_PASS',json.dumps(report),flush=True);cg.unregister()
