#!/usr/bin/env python3
"""Render the three polish reference characters in an isolated Blender process."""
import argparse, sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from chibi_generator import scene,model,studio

def reference_specs():
    looks=[('goth','oval','calm','goth_long','black','burgundy','streaks','porcelain','berry',
            dict(dress='goth_maxi',shoes='platforms'),['choker','earring','moon'],'hip'),
           ('pastel','round','wink','twin_tails','pink','cyan','split','peach','lavender',
            dict(dress='none',top='egirlcrop',bottom='pleated',shoes='platforms',legwear='striped',palette='pastel'),['choker','earring'],'peace'),
           ('grunge','soft_square','cheerful','shag','copper','honey','dipped','olive','freckles',
            dict(dress='none',top='flannel',bottom='baggyjeans',shoes='sneakers',legwear='bare'),['earring','waistchain'],'weight_shift')]
    for i,(name,face,expression,hair,color,secondary,pattern,skin,makeup,outfit,acc,pose) in enumerate(looks):
        spec=model.generate_spec(9100+i,style='goth' if name=='goth' else 'egirl' if name=='pastel' else 'grunge')
        spec=model.update_body(spec,height=.45+i*.055,thigh_size=.55,calf_size=.50,breast_size=.50,glute_size=.50,curve_severity=0)
        spec=model.update_face(spec,preset=face,expression=expression,eye_color=('jade','violet','amber')[i])
        spec=model.update_makeup(spec,preset=makeup,freckles=.75 if name=='grunge' else .08)
        spec=model.update_hair(spec,preset=hair,color=color,secondary=secondary,pattern=pattern)
        spec=model.update_skin(spec,preset=skin,shade=0,undertone=0)
        spec=model.update_outfit(spec,**outfit)
        spec=model.update_accessories(spec,acc)
        spec=model.update_pose(spec,preset=pose)
        yield name,spec

def render(character,view,path,samples):
    studio.set_view(bpy.context,character,'face' if view=='portrait' else view)
    s=bpy.context.scene;s.cycles.samples=samples;s.cycles.seed=37
    s.render.resolution_x=700 if view=='portrait' else 600
    s.render.resolution_y=780 if view=='portrait' else 800
    s.render.filepath=str(path);bpy.ops.render.render(write_still=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/character-study')
    parser.add_argument('--views',nargs='+',choices=['hero','front','side','back','portrait'],default=['hero','front','side','back','portrait'])
    parser.add_argument('--samples',type=int,default=40)
    parser.add_argument('--looks',nargs='+',choices=['goth','pastel','grunge'],default=['goth','pastel','grunge'])
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    args.output.mkdir(parents=True,exist_ok=True)
    for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for name,spec in reference_specs():
        if name not in args.looks:continue
        c=scene.generate_character(spec=spec)
        c.save_preset(args.output/f'{name}.json')
        for view in args.views:
            render(c,view,args.output/f'{name}-{view}.png',args.samples)
            print('CHARACTER_RENDER',name,view,flush=True)
        c.delete()
    print('CHARACTER_STUDY_PASS',flush=True)

if __name__=='__main__':main()
