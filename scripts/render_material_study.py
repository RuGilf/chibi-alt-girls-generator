#!/usr/bin/env python3
"""Run inside Blender to render three reproducible clothed material studies."""
import argparse, json, sys
from pathlib import Path
import bpy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chibi_generator import scene, model, studio

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/material-study')
    parser.add_argument('--samples', type=int, default=32)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    args.output.mkdir(parents=True, exist_ok=True)
    for ob in list(bpy.context.scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    looks = [
        ('knit-denim', dict(top='grungesweater', bottom='baggyjeans', dress='none', shoes='skateshoes', legwear='bare'), 'copper', 'ivory', 'shag'),
        ('leather-metal', dict(top='biker', bottom='lace_mini', dress='none', shoes='combat', legwear='bare'), 'silver', 'caramel', 'short_bob'),
        ('velvet-skin', dict(dress='romantic', shoes='maryjane', legwear='bare'), 'burgundy', 'porcelain', 'romantic_curls'),
    ]
    for i, (name, outfit, color, skin, hair) in enumerate(looks):
        spec = model.generate_spec(400 + i)
        spec = model.update_body(spec, height=.5, thigh_size=.55, calf_size=.5, breast_size=.5, glute_size=.5, curve_severity=0)
        spec = model.update_outfit(spec, **outfit, palette='default')
        spec = model.update_hair(spec, preset=hair, color=color, secondary='orchid', pattern='solid')
        spec = model.update_skin(spec, preset=skin, shade=0, undertone=0)
        spec = model.update_face(spec, preset='heart', expression='cheerful', eye_color='jade')
        spec = model.update_makeup(spec, preset='peach' if i==0 else 'berry', freckles=.6 if i==0 else .1)
        spec = model.update_accessories(spec, ['earring', 'moon'] if i<2 else ['cameo'])
        character = scene.generate_character(spec=spec)
        studio.set_view(bpy.context, character, 'hero')
        sc = bpy.context.scene
        sc.cycles.samples = args.samples
        sc.cycles.seed = 23
        sc.render.resolution_x = 600
        sc.render.resolution_y = 750
        sc.render.filepath = str(args.output / (name + '.png'))
        bpy.ops.render.render(write_still=True)
        character.save_preset(args.output / (name + '.json'))
        print('MATERIAL_RENDER', name, flush=True)
        character.delete()
    print('MATERIAL_STUDY_PASS', flush=True)

if __name__ == '__main__':
    main()
