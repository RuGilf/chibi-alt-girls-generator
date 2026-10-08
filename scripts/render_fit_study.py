#!/usr/bin/env python3
"""Render clothed body extremes and reusable fit reference presets in Blender."""
import argparse,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from chibi_generator import scene,model,studio

BODY_CASES={
 'petite':dict(height=0,breast_size=0,glute_size=0,thigh_size=0,calf_size=0,leg_asymmetry=-.10,curve_severity=1,curve_direction=-1,shoulder_tilt=-.02),
 'full':dict(height=1,breast_size=1,glute_size=1,thigh_size=1,calf_size=1,leg_asymmetry=.10,curve_severity=1,curve_direction=1,shoulder_tilt=.02),
 'mixed':dict(height=.5,breast_size=.6,glute_size=.8,thigh_size=.8,calf_size=.2,leg_asymmetry=-.10,curve_severity=0,shoulder_tilt=0),
 'balanced':dict(height=.5,breast_size=.4,glute_size=.5,thigh_size=.5,calf_size=.5,leg_asymmetry=0,curve_severity=0,shoulder_tilt=0)}
LOOKS={
 'petite_denim':('petite','bandtee','skinnyjeans','none','sneakers','short_bob','wave'),
 'full_corset':('full','corset','shorts','none','boots','short_bob','hip'),
 'full_knit':('full','hoodie','baggyjeans','none','platforms','short_bob','weight_shift'),
 'mixed_skirt':('mixed','egirlcrop','pleated','none','platforms','twin_tails','peace'),
 'full_goth':('full','bandtee','pleated','goth_maxi','platforms','goth_long','celebrate'),
 'balanced_shirt':('balanced','flannel','baggyjeans','none','sneakers','shag','neutral')}

def reference_spec(key):
 body,top,bottom,dress,shoes,hair,pose=LOOKS[key]
 spec=model.generate_spec(720);spec=model.update_body(spec,**BODY_CASES[body]);spec=model.update_face(spec,preset='round',expression='calm')
 spec=model.update_skin(spec,preset='peach',shade=0,undertone=0);spec=model.update_hair(spec,preset=hair,color='burgundy',secondary='pink',pattern='solid')
 spec=model.update_outfit(spec,top=top,bottom=bottom,dress=dress,shoes=shoes,legwear='bare',palette='default')
 spec=model.update_makeup(spec,preset='natural',freckles=0);spec=model.update_accessories(spec,[])
 return model.update_pose(spec,preset=pose)

def main():
 print("FIT_RENDERER_LOADED",flush=True)
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/body-fit/current');p.add_argument('--looks',nargs='+',choices=list(LOOKS),default=list(LOOKS));p.add_argument('--views',nargs='+',choices=['front','side','back','hero'],default=['front','side','back']);p.add_argument('--samples',type=int,default=24)
 args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);args.output.mkdir(parents=True,exist_ok=True)
 for ob in list(bpy.context.scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
 for key in args.looks:
  c=scene.generate_character(spec=reference_spec(key));c.save_preset(args.output/(key+'.json'))
  for view in args.views:
   studio.set_view(bpy.context,c,view);s=bpy.context.scene;s.cycles.samples=args.samples;s.cycles.seed=53;s.render.resolution_x=440;s.render.resolution_y=640;s.render.filepath=str(args.output/(key+'-'+view+'.png'));bpy.ops.render.render(write_still=True);print('FIT_RENDER',key,view,flush=True)
  c.delete()
 print('FIT_STUDY_PASS',flush=True)
if __name__=='__main__':main()
