"""Surface profiles, stable coordinates and cached-material migration in Blender."""
import json, sys
from pathlib import Path
import bpy
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chibi_generator import scene, model, surfaces

c = scene.generate_character(seed=50)
checked = []
for slot, key, kind in [('top','grungesweater','knit'), ('bottom','baggyjeans','denim'),
                         ('top','biker','leather'), ('top','cyberjacket','vinyl'),
                         ('dress','romantic','velvet')]:
    c.set_outfit(dress='none', **{slot:key}) if slot!='dress' else c.set_outfit(dress=key)
    ob = next(o for o in c.objects if not o.hide_render and o.get('chibi_option')==key
              and any(m and m.name.startswith(key+' • fabric') for m in o.data.materials))
    mat = next(m for m in ob.data.materials if m.name.startswith(key+' • fabric'))
    assert mat['chibi_surface']==kind
    attr = ob.data.attributes[surfaces.COORDINATES]
    points = np.empty(len(attr.data)*3);attr.data.foreach_get('vector',points)
    basis = np.empty_like(points);ob.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis)
    assert np.allclose(points,basis,atol=1e-7)
    before=(len(mat.node_tree.nodes),len(mat.node_tree.links))
    c.set_body(height=.8,thigh_size=.8,breast_size=.8)
    c.set_pose(preset='wave',mirror=True)
    after=np.empty_like(points);attr.data.foreach_get('vector',after)
    assert np.array_equal(points,after), 'Rest-space coordinates drifted'
    assert before==(len(mat.node_tree.nodes),len(mat.node_tree.links)), 'Shader nodes accumulated'
    assert np.isfinite(points).all()
    checked.append(kind)
# Simulate a cached v0.8 garment with no surface metadata; preserve mesh and colors.
c.set_outfit(dress='none',top='biker')
ob=next(o for o in c.objects if not o.hide_render and o.get('chibi_option')=='biker'
        and any(m and m.name.startswith('biker • fabric') for m in o.data.materials))
mat=next(m for m in ob.data.materials if m.name.startswith('biker • fabric'))
mesh=ob.data;count=len(c.objects);color=tuple(mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
del mat['chibi_surface'];del mat['chibi_surface_revision']
ob.data.attributes.remove(ob.data.attributes[surfaces.COORDINATES])
c.apply(c.parameters)
assert ob.data==mesh and len(c.objects)==count and mat['chibi_surface']=='leather'
assert color==tuple(mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value)
assert surfaces.COORDINATES in mesh.attributes
assert not any(n.type=='TEX_IMAGE' for o in c.objects if o.type=='MESH'
               for m in o.data.materials if m and m.use_nodes for n in m.node_tree.nodes)
report=dict(status='PASS',distinct_profiles=checked,coordinates_match_basis=True,
            coordinates_stable_across_body_and_pose=True,no_shader_node_growth=True,
            cached_material_migration=True,colors_preserved=True,no_external_textures=True)
out=ROOT/'build/test-reports';out.mkdir(parents=True,exist_ok=True)
(out/'surfaces.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SURFACES_PASS',report,flush=True)
