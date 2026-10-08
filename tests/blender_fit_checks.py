"""Body extremes, joined garments, sleeve coverage and repeatable fitting."""
import sys,json,hashlib
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from chibi_generator import scene,model,anatomy
from chibi_generator.deformation import deform
from render_fit_study import BODY_CASES,LOOKS,reference_spec
AUDIT='--audit' in sys.argv
OUT=ROOT/'build/test-reports';OUT.mkdir(parents=True,exist_ok=True)

def data(ob,neutral=False):
    if neutral:return scene.rest_points(ob)
    ev=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh()
    p=np.array([tuple(ev.matrix_world@v.co) for v in me.vertices]);faces=[f.vertices[:] for f in me.polygons]
    attr=me.attributes.get('FitNeutralPosition');rest=np.empty(len(me.vertices)*3)
    if attr:attr.data.foreach_get('vector',rest);rest=rest.reshape(-1,3)
    else:rest=None
    ev.to_mesh_clear();assert np.isfinite(p).all()
    return p,faces,rest

def neutral_attribute(ob):
    if ob.data.attributes.get('FitNeutralPosition'):return
    attr=ob.data.attributes.new('FitNeutralPosition','FLOAT_VECTOR','POINT');attr.data.foreach_set('vector',scene.rest_points(ob).ravel())

def coverage(skin,garment,lo,hi):
    p,_,rest=data(skin);q,faces,_=data(garment)
    mask=(rest[:,2]>lo)&(rest[:,2]<hi)
    if garment.get('chibi_part')=='arm':
        neutral=scene.rest_points(garment)
        for face in garment.data.polygons:
            if len(face.vertices)<12:continue
            ring=neutral[list(face.vertices)];center=ring.mean(axis=0)
            normal=np.cross(ring-center,np.roll(ring,-1,axis=0)-center).sum(axis=0)
            normal/=np.linalg.norm(normal)
            if normal@(center-neutral.mean(axis=0))<0:normal=-normal
            # Sleeve openings are oblique; a Z-only cutoff includes bare skin.
            mask&=((rest-center)@normal<-.015)
    sample=p[mask][::max(1,int(mask.sum()/240))]
    tree=BVHTree.FromPolygons([Vector(v) for v in q],faces)
    distances=[]
    for v in sample:
        hit,normal,_,dist=tree.find_nearest(Vector(v))
        # Folded sleeves are non-convex: the nearest face normal alone can
        # classify an enclosed point as outside. Use signed ray crossings instead (overlapping legs can enclose a point twice).
        votes=[]
        for direction in (Vector((.137,1,.219)).normalized(),Vector((-.231,-1,.173)).normalized(),Vector((1,.317,-.183)).normalized()):
            origin=Vector(v);crossings=0
            for _ in range(128):
                point,hit_normal,index,_=tree.ray_cast(origin,direction)
                if point is None:break
                crossings+=1 if hit_normal.dot(direction)>0 else -1;origin=point+direction*2e-6
            else:raise AssertionError('Ray winding did not converge')
            votes.append(crossings!=0)
            if len(votes)==2 and votes[0]==votes[1]:break
        inside=sum(votes)>len(votes)/2
        distances.append(-dist if inside else dist)
    return max([0,*distances])

c=scene.generate_character(spec=reference_spec('petite_denim'));rows=[];meshes_checked=set()
for look in LOOKS:
    for body_key,body in BODY_CASES.items():
        spec=model.update_body(reference_spec(look),**body)
        for pose in ('neutral','wave','hip','celebrate'):
            c.apply(model.update_pose(spec,preset=pose));bpy.context.view_layer.update()
            visible=[o for o in c.objects if o.type=='MESH' and not o.hide_render]
            for o in visible:
                if o.get('chibi_continuous_arm') or o.get('chibi_legwear_base') or o.get('chibi_asset')=='Underlying torso':neutral_attribute(o)
                if o.get('chibi_continuous_pants') and o.name not in meshes_checked:
                    bm=bmesh.new();bm.from_mesh(o.data);bm.verts.ensure_lookup_table();assert all(e.is_manifold for e in bm.edges),'Nonmanifold trousers'
                    seen=set();stack=[bm.verts[0]]
                    while stack:
                        v=stack.pop()
                        if v in seen:continue
                        seen.add(v);stack.extend(e.other_vert(v) for e in v.link_edges)
                    assert len(seen)==len(bm.verts),'Disconnected trouser panels';bm.free();meshes_checked.add(o.name)
                assert all(v.groups for v in o.data.vertices),o.name
            bpy.context.view_layer.update()
            metrics={}
            for side in ('L','R'):
                skin=next(o for o in visible if o.get('chibi_continuous_arm') and o.get('chibi_hand')==side)
                sleeve=next(o for o in visible if o.get('chibi_part')=='arm' and 'sleeve ' in o.get('chibi_asset','') and (scene.rest_points(o)[:,0].mean()>0)==(side=='L'))
                bounds=scene.rest_points(sleeve)[:,2]
                metrics['arm_'+side]=coverage(skin,sleeve,bounds.min()+.028,min(1.125,bounds.max()-.025))
                for o in (skin,sleeve):
                    for v in list(o.data.vertices)[::max(1,len(o.data.vertices)//1000)]:assert abs(sum(g.weight for g in v.groups)-1)<1e-5
            pants=next((o for o in visible if o.get('chibi_continuous_pants')),None)
            if pants:
                hem=scene.rest_points(pants)[:,2].min();shoe=model.ASSETS['shoes'][spec['outfit']['shoes']].get('height',.34 if spec['outfit']['shoes']=='boots' else .22)
                for side in (-1,1):
                    skin=next(o for o in visible if o.get('chibi_legwear_base') and (scene.rest_points(o)[:,0].mean()>0)==(side==1))
                    metrics['leg_'+str(side)]=coverage(skin,pants,max(hem,shoe)+.035,.70)
            for o in visible:
                values=np.empty(len(o.data.vertices)*3);o.data.shape_keys.key_blocks['BodyVariation'].data.foreach_get('co',values);assert np.isfinite(values).all()
            rows.append(dict(look=look,body=body_key,pose=pose,max_skin_outside_m=metrics))
        print('FIT_CHECK',look,body_key,'max_skin_outside_m',max(max(r['max_skin_outside_m'].values()) for r in rows[-4:]),flush=True)
# The joined crotch must remain continuous at x=0 for both asymmetry directions.
for body in BODY_CASES.values():
    b=model.update_body(model.generate_spec(7),**body)['body']
    for z in (.66,.72,.79,.81,.9):
        near=deform([[-1e-6,.07,z],[1e-6,.07,z]],b,'pants');assert np.linalg.norm(near[1]-near[0])<.0001
    pts=[[.17,.09,.81],[.06,-.06,.86]]
    assert np.allclose(deform(pts,b,'pants'),deform(pts,b,'hip'),atol=1e-7)
# Reapplying and restoring a spec must not accumulate modifiers, geometry or materials.
before=c.parameters;counts=(len(c.objects),len(bpy.data.materials))
def signature():
    h=hashlib.sha256()
    for o in c.objects:
        if o.type=='MESH' and not o.hide_render:
            p=np.empty(len(o.data.vertices)*3);o.data.shape_keys.key_blocks['BodyVariation'].data.foreach_get('co',p);h.update(p.tobytes())
    return h.hexdigest()
sig=signature()
for _ in range(2):c.apply(before)
assert counts==(len(c.objects),len(bpy.data.materials)) and sig==signature()
failures=[r for r in rows if max(r['max_skin_outside_m'].values())>.004]
report=dict(status='AUDIT' if AUDIT else 'PASS' if not failures else 'FAIL',cases=len(rows),body_profiles=list(BODY_CASES),poses=['neutral','wave','hip','celebrate'],joined_garments_checked=len(meshes_checked),sampled_coverage_tolerance_m=.004,failures=failures,rows=rows,crotch_continuity=True,shared_hip_deformation=True,no_drift=True)
(OUT/'fit.json').write_text(json.dumps(report,indent=2));print('FIT_RESULT',report['status'],'cases',len(rows),'coverage_failures',len(failures),flush=True)
assert AUDIT or not failures,failures[:3]
