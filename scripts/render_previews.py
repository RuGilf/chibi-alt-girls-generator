#!/usr/bin/env python3
"""Refresh face/hair selection thumbnails from real Blender renders."""
import argparse,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from chibi_generator import scene,model,studio

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--groups',nargs='+',choices=['face','hair'],default=['face','hair'])
    parser.add_argument('--keys',nargs='+',choices=sorted(set(model.FACE_PRESETS)|set(model.HAIR_PRESETS)))
    parser.add_argument('--output',type=Path,default=ROOT/'build/previews')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.output.mkdir(parents=True,exist_ok=True)
    for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for group in args.groups:
        for key in model.FACE_PRESETS if group=='face' else model.HAIR_PRESETS:
            if args.keys and key not in args.keys:continue
            spec=model.generate_spec(708)
            spec=model.update_body(spec,height=.5,curve_severity=0)
            spec=model.update_face(spec,preset=key if group=='face' else 'classic',expression='calm')
            spec=model.update_hair(spec,preset=key if group=='hair' else 'short_bob',color='silver',secondary='orchid',pattern='dipped')
            spec=model.update_skin(spec,preset='peach',shade=0,undertone=0)
            spec=model.update_makeup(spec,preset='natural',freckles=0)
            spec=model.update_outfit(spec,dress='none',top='bandtee',bottom='baggyjeans',palette='default')
            spec=model.update_accessories(spec,[])
            c=scene.generate_character(spec=spec);studio.set_view(bpy.context,c,'face')
            s=bpy.context.scene;s.camera.data.ortho_scale=.80 if group=='face' else 1.25
            if group=='hair' and key in ('high_pony','low_pony','braid','half_up','mohawk'):
                center=s.camera.location-Vector((.16,-5,.065));s.camera.location=center+Vector((4,-3,.14))
                s.camera.rotation_euler=(center-s.camera.location).to_track_quat('-Z','Y').to_euler()
            s.cycles.samples=16;s.render.resolution_x=180;s.render.resolution_y=200;s.render.filepath=str(args.output/f'{group}_{key}.png')
            bpy.ops.render.render(write_still=True);c.delete();print('PREVIEW_RENDER',group,key,flush=True)
    print('PREVIEWS_PASS',flush=True)

if __name__=='__main__':main()
