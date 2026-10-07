import bpy,bmesh,sys,json,numpy as np,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'chibi_generator';sys.path.insert(0,str(ROOT.parent))
import chibi_generator as cg
from chibi_generator import scene,model,ui,hands
cg.register();c=scene.generate_character(seed=50);ui.focus(bpy.context,c)
def signature():return np.concatenate([np.array(pb.matrix).ravel() for pb in c.rig.pose.bones])
def check():
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    for ob in c.objects:
        if ob.type!='MESH' or ob.hide_render:continue
        assert not ob.hide_viewport and all(v.groups for v in ob.data.vertices)
        if ob.get('chibi_hand'):
            for v in ob.data.vertices:assert abs(sum(g.weight for g in v.groups)-1)<1e-4
            ev=ob.evaluated_get(deps);mesh=ev.to_mesh();p=np.array([v.co[:] for v in mesh.vertices]);assert np.isfinite(p).all();assert np.max(np.ptp(p,axis=0))<.25;ev.to_mesh_clear()
    assert np.isfinite(signature()).all()
    for side in ('L','R'):
        pb=c.rig.pose.bones['foot.'+side];assert (pb.head-pb.bone.head_local).length<.003,(c.parameters['pose'],c.parameters['body']['height'],side,(pb.head-pb.bone.head_local).length,tuple(pb.head-pb.bone.head_local))
# Exactly one manifold skin surface for each hand, separate attached nail meshes.
for side in ('L','R'):
    ob=next(o for o in c.objects if o.get('chibi_hand')==side and not o.get('chibi_digit'))
    bm=bmesh.new();bm.from_mesh(ob.data);bm.verts.ensure_lookup_table();assert all(e.is_manifold for e in bm.edges)
    seen=set();stack=[bm.verts[0]]
    while stack:
        v=stack.pop()
        if v in seen:continue
        seen.add(v);stack.extend(e.other_vert(v) for e in v.link_edges)
    assert len(seen)==len(bm.verts);bm.free()
    assert len([o for o in c.objects if o.get('chibi_hand')==side and o.get('chibi_digit')])==5
for preset in model.POSE_PRESETS:
    for mirror in (False,True):
        c.set_pose(preset=preset,mirror=mirror,left='auto',right='auto');check();sig=signature();c.apply(c.parameters);assert np.allclose(signature(),sig,atol=1e-6)
    print('POSE_CHECK',preset,flush=True)
for key in model.GESTURES:
    c.set_pose(preset='wave',mirror=False,left=key,right='fist');check()
for h in (0,1):
    c.set_body(height=h,curve_severity=1,shoulder_tilt=.02)
    for key in model.POSE_PRESETS:c.set_pose(preset=key);check()
# Pose JSON captures body pose and both independent gesture choices.
c.set_pose(preset='peace',mirror=True,left='rock',right='point');spec=c.parameters;sig=signature()
with tempfile.TemporaryDirectory() as d:
    p=Path(d)/'pose.json';c.save_preset(p);c.set_pose(**model.default_pose());c.apply(model.load_preset(p));assert c.parameters==spec and np.allclose(signature(),sig,atol=1e-6)
s=bpy.context.scene.chibi_settings;s.pose_preset='wave';s.gesture_left='peace';s.gesture_right='fist';s.pose_mirror=True;assert c.parameters['pose']==dict(preset='wave',left='peace',right='fist',mirror=True)
before=c.parameters;s.seed=900;bpy.ops.chibi.random_all(use_seed=True);assert c.parameters['pose']==before['pose'];bpy.ops.chibi.previous();assert c.parameters==before
assert bpy.ops.chibi.pose_reset()=={'FINISHED'} and c.parameters['pose']==model.default_pose()
# Migration of a deterministic v0.7 fixture, created without personal saves.
with bpy.data.libraries.load(str(ROOT.parent/'tests/fixtures/legacy_v07.blend')) as (src,dst):dst.collections=[next(n for n in src.collections if n.startswith('CHIBI '))]
col=dst.collections[0];bpy.context.scene.collection.children.link(col);old=scene.Character(next(o for o in col.objects if o.get('chibi_spec')));before=old.parameters;old.apply(before);assert old.parameters==before;assert sum(bool(o.get('chibi_hand')) and not o.hide_render for o in old.objects)==12
report=dict(status='PASS',standing_poses=10,mirrored_poses=20,explicit_gestures=6,manifold_connected_hand_surfaces=2,nails_per_hand=5,all_pose_height_posture_extremes=20,finite_evaluated_geometry=True,hand_weight_normalization=True,feet_planted_tolerance_m=.003,no_pose_drift=True,JSON_pose_and_gesture_roundtrip=True,manual_UI=True,random_appearance_preserves_pose=True,legacy_scene_migration=True)
(ROOT.parent/'build/test-reports').mkdir(parents=True,exist_ok=True)
(ROOT.parent/'build/test-reports/poses.json').write_text(json.dumps(report,indent=2));print('POSE_FEATURES_PASS',report,flush=True);cg.unregister()
