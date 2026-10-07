"""Behaviour checks for the actual creator operators, not a UI mock-up."""
import bpy,sys,tempfile,json,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'chibi_generator';sys.path.insert(0,str(ROOT.parent))
import chibi_generator as cg
from chibi_generator import model,ui,studio
cg.register();c=cg.generate_character(seed=418);ui.focus(bpy.context,c);s=bpy.context.scene.chibi_settings
s.seed=812;s.lock_face=True;s.lock_body=True;before=c.parameters
assert bpy.ops.chibi.random_all(use_seed=True)=={'FINISHED'}
assert c.parameters['face']==before['face'] and c.parameters['body']==before['body']
assert c.parameters['makeup']==model.sample_makeup(812)
assert bpy.ops.chibi.previous()=={'FINISHED'} and c.parameters==before
s.lock_makeup=True;s.lock_outfit=True;s.lock_accessories=True;s.lock_hair=True;s.lock_skin=True;before=c.parameters;assert bpy.ops.chibi.random_all(use_seed=True)=={'CANCELLED'} and c.parameters==before
s.lock_body=False;s.lock_face=False;s.lock_makeup=False;s.lock_outfit=False;s.lock_accessories=False;s.lock_hair=False;s.lock_skin=False;s.seed=812
assert bpy.ops.chibi.random_all(use_seed=True)=={'FINISHED'}
assert c.parameters['body']==model.sample_body(812) and c.parameters['face']==model.sample_face(812)
# Clicking the floor must not make the creator lose its character.
studio.ensure(bpy.context);floor=next(o for o in bpy.context.scene.objects if o.name.startswith('Studio floor'))
bpy.context.view_layer.objects.active=floor
s.eye_size=1.09;assert abs(c.parameters['face']['eye_size']-1.09)<1e-6 and ui.current().rig==c.rig
assert bpy.ops.chibi.snapshot()=={'FINISHED'};before=c.parameters;s.height=.93
assert bpy.ops.chibi.previous()=={'FINISHED'} and c.parameters==before
for view in studio.VIEWS:
    assert bpy.ops.chibi.view(view=view)=={'FINISHED'}
    assert bpy.context.scene.camera and bpy.context.scene['chibi_view']==view
with tempfile.TemporaryDirectory() as folder:
    s.library_path=folder;s.character_name='../Моя альтушка';saved=c.parameters
    assert bpy.ops.chibi.favourite_save()=={'FINISHED'};assert bpy.ops.chibi.favourite_save()=={'FINISHED'}
    assert len(list(Path(folder).glob('*.json')))==2
    Path(folder,'broken.json').write_text('{');bpy.ops.chibi.favourite_refresh();assert len(s.favourites)==2
    c.randomize_face(31);c.randomize_body(392);assert bpy.ops.chibi.favourite_load()=={'FINISHED'}
    for group in ('body','face','makeup','outfit'):assert c.parameters[group]==saved[group]
    assert sum(o.type=='ARMATURE' and bool(o.get('chibi_spec')) for o in bpy.context.scene.objects)==1
    path=Path(folder)/'manual.json';assert bpy.ops.chibi.save_preset(filepath=str(path))=={'FINISHED'}
    c.randomize_makeup(100);assert bpy.ops.chibi.load_preset(filepath=str(path))=={'FINISHED'}
    for group in ('body','face','makeup','outfit'):assert c.parameters[group]==saved[group]
report={'status':'PASS','random_all':True,'group_locks':True,'all_locked_no_op':True,'manual_controls':True,'selection_fallback':True,'previous_look':True,'camera_views':5,'favourites_non_overwriting':True,'invalid_library_file_skipped':True,'load_reuses_character':True,'JSON_save_load':True,'preview_icons':len(ui._PREVIEWS)}
output=ROOT.parent/'build/test-reports/app.json';output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(report,indent=2));print(json.dumps(report));cg.unregister()
