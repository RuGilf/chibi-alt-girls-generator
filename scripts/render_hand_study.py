#!/usr/bin/env python3
"""Render palm, back, fist and peace gesture in a disposable Blender scene."""
import argparse,sys
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from chibi_generator import scene,studio,model

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'build/hand-study')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.output.mkdir(parents=True,exist_ok=True)
    for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
    spec=model.generate_spec(91);spec=model.update_skin(spec,preset='peach',shade=0,undertone=0)
    c=scene.generate_character(spec=spec)
    camera=studio.ensure(bpy.context)
    for name,gesture,back in [('palm','open',False),('nails','relaxed',True),('fist','fist',False),('peace','peace',False)]:
        c.set_pose(preset='neutral',left=gesture,right='relaxed')
        hand=next(o for o in c.objects if o.get('chibi_hand')=='L' and not o.get('chibi_digit') and not o.hide_render)
        for ob in c.objects:
            keep=ob.get('chibi_hand')=='L' and ob.get('chibi_hand_rev')==hand['chibi_hand_rev']
            keep=keep or ob.get('chibi_asset')=='Underlying arm 1'
            ob.hide_render=not keep
        bpy.context.view_layer.update();ev=hand.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=ev.to_mesh();points=np.array([tuple(ev.matrix_world@v.co) for v in mesh.vertices]);ev.to_mesh_clear()
        center=Vector((points.min(axis=0)+points.max(axis=0))*.5)
        offset=Vector((-.8,3,.9) if back else (.5,-3,.8));camera.location=center+offset
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=.215
        s=bpy.context.scene;s.cycles.samples=40;s.render.resolution_x=520;s.render.resolution_y=600;s.render.filepath=str(args.output/(name+'.png'))
        bpy.ops.render.render(write_still=True);print('HAND_RENDER',name,flush=True)
    print('HAND_STUDY_PASS',flush=True)

if __name__=='__main__':main()
