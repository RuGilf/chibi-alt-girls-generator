"""State regressions: cosmetic visibility, preserved poses and invalidated IDs."""
import json, sys, tempfile
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import chibi_generator as cg
from chibi_generator import scene, model, ui, studio
cg.register()
c = scene.generate_character(seed=42)
layer = next(o for o in c.objects if o.get('chibi_asset') == 'Freckle colour layer')
for amount in (1, 0, .4, 0, 1):
    c.set_makeup(preset='freckles', freckles=amount)
    assert layer.hide_render == (amount <= .001)
    assert layer.hide_viewport == layer.hide_render
    if amount:
        key = layer.data.shape_keys.key_blocks['BodyVariation']
        assert max(v.co.x for v in key.data) > .05
# Wardrobe updates must not reveal manually hidden unrelated meshes.
head = next(o for o in c.objects if o.get('chibi_asset', '').startswith('Head'))
head.hide_render = True
c.set_outfit(top='biker')
assert head.hide_render
head.hide_render = False
c.set_pose(preset='wave', mirror=True, left='rock', right='fist')
pose = c.parameters['pose']
ui.focus(bpy.context, c)
assert bpy.ops.chibi.regenerate() == {'FINISHED'}
assert c.parameters['pose'] == pose
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / 'preset.json'
    c.save_preset(path)
    c.delete()
    bpy.context.scene.camera = None
    assert bpy.ops.chibi.load_preset(filepath=str(path)) == {'FINISHED'}
    assert bpy.context.scene.camera and bpy.context.scene.camera.type == 'CAMERA'
    assert scene.active_character().parameters['pose'] == pose
# File replacement invalidates Python references retained by imported modules.
bpy.ops.wm.read_factory_settings(use_empty=True)
c = scene.generate_character(seed=17)
assert len(c.rig.data.bones) == 52
studio.set_view(bpy.context, c)
assert bpy.context.scene.camera
report = dict(status='PASS', freckles_off_on=True, hidden_mesh_preserved=True,
              seed_preserves_pose=True, JSON_load_prepares_camera=True,
              generate_after_new_file=True)
folder = ROOT / 'build/test-reports'
folder.mkdir(parents=True, exist_ok=True)
(folder / 'regressions.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('REGRESSIONS_PASS', report, flush=True)
