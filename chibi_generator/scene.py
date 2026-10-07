"""Editable chibi instances, skinning, and independent body, face and cosmetics."""
import json, math, uuid
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector,Matrix
from . import model,facial,clothing,wardrobe,hair,appearance,hands,posing,surfaces
from .deformation import deform
ASSET=Path(__file__).resolve().parent/'assets/chibi_base.blend'
SECTIONS=('01 Body','02 Face','03 Hair','04 Outfit','05 Jewelry')
_CACHE=[]

def part_for(name,section):
    if section in ('02 Face','03 Hair') or name.startswith(('Head','Ear','Crescent hair','Lavender hair','Silver hoop earring','Earring orchid')):return 'head'
    if name.startswith(('Matte tights','Platform sole','Combat boot','Rolled boot','Sole groove','Tread block','Steel boot','Crossed lilac','Boot pull','Toe cap')):return 'leg'
    if name.startswith(('Sixteen tailored','Orchid skirt','High waistband','Silver belt','Buckle pin','Belt keeper','Waist chain')):return 'skirt'
    if name.startswith(('Neck','Slim charcoal choker','Choker silver')):return 'neck'
    if name.startswith(('Soft jacket sleeve','Ribbed cuff','Sleeve accent','Palm','Rounded finger','Thumb','Short nail')):return 'arm'
    return 'body'

def bone_specs():
    b=[('root',(0,0,.02),(0,0,.15),None),('pelvis',(0,0,.75),(0,0,.90),'root'),('spine',(0,0,.90),(0,0,1.06),'pelvis'),('chest',(0,0,1.06),(0,0,1.19),'spine'),('neck',(0,0,1.19),(0,0,1.28),'chest'),('head',(0,0,1.28),(0,0,1.83),'neck')]
    for side,s in [('L',1),('R',-1)]:
        def p(x,y,z):return(s*x,y,z)
        b.extend([(f'clavicle.{side}',p(.025,0,1.19),p(.175,0,1.176),'chest'),(f'upper_arm.{side}',p(.175,0,1.176),p(.254,.002,1.03),f'clavicle.{side}'),(f'forearm.{side}',p(.254,.002,1.03),p(.302,-.015,.86),f'upper_arm.{side}'),(f'hand.{side}',p(.302,-.015,.86),p(.309,-.015,.785),f'forearm.{side}'),(f'thigh.{side}',p(.082,0,.75),p(.097,-.002,.51),'pelvis'),(f'shin.{side}',p(.097,-.002,.51),p(.105,0,.22),f'thigh.{side}'),(f'foot.{side}',p(.105,0,.22),p(.105,-.12,.09),f'shin.{side}'),(f'toe.{side}',p(.105,-.12,.09),p(.105,-.16,.09),f'foot.{side}')])
        for name in (*hands.FINGERS,'thumb'):
            pts=hands.finger_points(side,name)
            for j in range(3):b.append((f'{name}{j+1}.{side}',pts[j],pts[j+1],f'hand.{side}' if j==0 else f'{name}{j}.{side}'))
    return b
BONES=bone_specs()

def templates():
    # File > New, opening a scene and Undo can invalidate cached Blender IDs.
    try:
        if any(bpy.data.objects.get(ob.name) != ob or ob.data is None for _, ob in _CACHE):
            _CACHE.clear()
    except ReferenceError:
        _CACHE.clear()
    if not _CACHE:
        if bpy.data.filepath and Path(bpy.data.filepath).resolve()==ASSET.resolve():
            collections=[bpy.data.collections.get(s) for s in SECTIONS]
            if any(c is None for c in collections):raise ValueError('Neutral collections are missing from the open base file')
        else:
            with bpy.data.libraries.load(str(ASSET),link=False) as (src,dst):
                missing=set(SECTIONS)-set(src.collections)
                if missing:raise ValueError('Missing asset collections: '+str(missing))
                dst.collections=list(SECTIONS)
            collections=dst.collections
        for section,col in zip(SECTIONS,collections):
            for ob in col.objects:
                if ob.type=='MESH':ob.use_fake_user=True;_CACHE.append((section,ob))
    return _CACHE

def rest_points(ob):
    source=ob.data.shape_keys.key_blocks['Basis'].data if ob.data.shape_keys else ob.data.vertices
    a=np.empty(len(source)*3,dtype=np.float64);source.foreach_get('co',a);a=a.reshape(-1,3)
    mat=np.array(ob.matrix_local,dtype=np.float64)
    return a@mat[:3,:3].T+mat[:3,3]

REFINED_GARMENTS=('Orchid knit top','Cropped charcoal jacket')
def refine_garment(ob):
    """Bake the neutral fabric surface so fine knit ribs follow the same morph."""
    if ob.get('chibi_surface_refined') or not ob.get('chibi_asset',ob.name).startswith(REFINED_GARMENTS):return False
    if not any(m.type=='SUBSURF' for m in ob.modifiers):return False
    if ob.data.shape_keys:
        for key in ob.data.shape_keys.key_blocks:
            if key.name!='Basis':key.value=0
    for modifier in list(ob.modifiers):
        if modifier.type=='ARMATURE':ob.modifiers.remove(modifier)
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
    mesh=bpy.data.meshes.new_from_object(ob.evaluated_get(deps),preserve_all_data_layers=True,depsgraph=deps)
    old=ob.data;ob.data=mesh;ob.modifiers.clear();ob['chibi_surface_refined']=True
    if old.users==0:bpy.data.meshes.remove(old)
    return True

def _segment_dist(points,a,b):
    a=np.array(a);b=np.array(b);d=b-a;t=np.clip(((points-a)@d)/(d@d),0,1)
    return np.linalg.norm(points-a-t[:,None]*d,axis=1)

def bind(ob,rig,part):
    pts=rest_points(ob);side='L' if pts[:,0].mean()>=0 else 'R'
    if part=='head':candidates=['head']
    elif part=='neck':candidates=['neck','head','chest']
    elif part=='leg':candidates=[f'{k}.{side}' for k in ('thigh','shin','foot','toe')]
    elif part=='skirt':candidates=['pelvis']
    elif part=='arm':
        candidates=[f'{k}.{side}' for k in ('clavicle','upper_arm','forearm','hand')]
        if 'Palm' in ob.name or 'finger' in ob.name or 'Thumb' in ob.name or 'nail' in ob.name:
            candidates+=[f'{f}{j}.{side}' for f in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
    else:candidates=['pelvis','spine','chest','neck','clavicle.L','clavicle.R']
    ob.vertex_groups.clear()
    for name,_,_,_ in BONES:
        if name!='root':ob.vertex_groups.new(name=name)
    if len(candidates)==1:ob.vertex_groups[candidates[0]].add(list(range(len(pts))),1,'REPLACE')
    else:
        segments={name:(a,b) for name,a,b,_ in BONES}
        distances=np.stack([_segment_dist(pts,*segments[n]) for n in candidates],axis=1)
        near=np.argsort(distances,axis=1)[:,:min(3,len(candidates))];selected=np.take_along_axis(distances,near,axis=1)
        weights=np.exp(-100*(selected-selected[:,0,None]));weights/=weights.sum(axis=1)[:,None]
        for i in range(len(pts)):
            for j,w in zip(near[i],weights[i]):
                if w>.002:ob.vertex_groups[candidates[j]].add([i],float(w),'REPLACE')
    modifier=ob.modifiers.new('Chibi humanoid skin','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=True

def update_rest(rig,body):
    active=bpy.context.view_layer.objects.active
    if bpy.context.object and bpy.context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    for name,a,b,parent in BONES:
        bone=rig.data.edit_bones.get(name) or rig.data.edit_bones.new(name)
        part='leg' if name.startswith(('thigh','shin','foot','toe')) else 'body'
        positions=deform([a,b],body,part);bone.head=positions[0];bone.tail=positions[1];bone.use_deform=name!='root'
        if parent:bone.parent=rig.data.edit_bones[parent]
        if name.startswith((*hands.FINGERS,'thumb','hand.','upper_arm.','forearm.')):bone.align_roll(Vector((0,-1,0)))
    bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.objects.active=active or rig

class Character:
    def __init__(self,rig):self.rig=rig
    @property
    def parameters(self):return model.validate(json.loads(self.rig['chibi_spec']))
    @property
    def collection(self):return next(c for c in self.rig.users_collection if c.get('chibi_character_id'))
    @property
    def objects(self):return list(self.collection.objects)
    def set_pose(self,**values):return self.apply(model.update_pose(self.parameters,**values))
    def set_hair(self,**values):return self.apply(model.update_hair(self.parameters,**values))
    def set_skin(self,**values):return self.apply(model.update_skin(self.parameters,**values))
    def randomize_hair(self,seed=None,color_only=False):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;fresh=model.sample_hair(seed,spec['style'])
        if color_only:fresh['preset']=spec['hair']['preset']
        spec['hair']=fresh;spec['hair_seed']=seed;return self.apply(spec)
    def randomize_skin(self,seed=None):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;spec['skin']=model.sample_skin(seed);spec['skin_seed']=seed;return self.apply(spec)
    def set_body(self,**values):
        return self.apply(model.update_body(self.parameters,**values))
    def set_face(self,preset=None,**values):
        return self.apply(model.update_face(self.parameters,preset,**values))
    def set_outfit(self,**values):
        return self.apply(model.update_outfit(self.parameters,**values))
    def randomize_outfit(self,seed=None):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;spec['outfit']=model.sample_outfit(seed,spec['style']);spec['outfit_seed']=seed;return self.apply(spec)
    def set_accessories(self,values):return self.apply(model.update_accessories(self.parameters,values))
    def randomize_accessories(self,seed=None):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;spec['accessories']=model.sample_accessories(seed,spec['style']);spec['accessories_seed']=seed;return self.apply(spec)
    def set_style(self,style=None,style_mix=None,seed=None,include_makeup=False,include_hair=False):
        return self.apply(model.apply_style(self.parameters,style_mix if style_mix is not None else {style:1},seed,include_makeup,include_hair))
    def set_makeup(self,preset=None,**values):
        return self.apply(model.update_makeup(self.parameters,preset,**values))
    def apply(self,spec):
        spec=model.validate(spec);bpy.context.view_layer.update()
        if not any(ob.get('chibi_asset')=='Lip colour layer' for ob in self.objects):
            facial.own_materials(self.objects)
            extras=facial.extra_assets(self.collection,self.rig);bpy.context.view_layer.update()
            for ob in extras:bind(ob,self.rig,'head')
        if not self.rig.get('chibi_wardrobe_v1'):
            clothing.tag_original(self.objects)
            for ob in clothing.create(self.collection,self.rig):
                ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation');bind(ob,self.rig,ob['chibi_part'])
            self.rig['chibi_wardrobe_v1']=True
        for ob in hands.ensure(self.collection,self.rig):
            ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation');hands.bind(ob,self.rig)
        wardrobe.tag_original(self.objects)
        for ob in wardrobe.ensure(self.collection,self.rig,spec):
            ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation');bind(ob,self.rig,ob['chibi_part'])
        for ob in hair.ensure(self.collection,self.rig,spec):
            ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation');bind(ob,self.rig,'head')
        wardrobe.visibility(self.objects,spec);hair.visibility(self.objects,spec);hands.visibility(self.objects);facial.visibility(self.objects,spec);wardrobe.legwear(self.objects,self.rig,spec['outfit']['legwear']);appearance.apply_materials(self.objects,self.rig,spec)
        surfaces.upgrade_cached(self.objects,model.ASSETS)
        for ob in self.objects:
            if ob.type!='MESH' or ob.hide_render:continue
            if refine_garment(ob):
                ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation');bind(ob,self.rig,ob['chibi_part'])
            original=rest_points(ob);hair.paint(ob,original,spec,self.rig);facial.paint(ob,original,spec);shaped=facial.morph(hair.fit_accessory(original,ob,spec),spec['face'],ob['chibi_asset'],ob['chibi_part'],spec['makeup']);changed=deform(shaped,spec['body'],ob['chibi_part']);mat=np.array(ob.matrix_local.inverted(),dtype=np.float64);local=changed@mat[:3,:3].T+mat[:3,3]
            key=ob.data.shape_keys.key_blocks['BodyVariation'];key.data.foreach_set('co',local.ravel());key.value=1;ob.data.update()
        wardrobe.visibility(self.objects,spec);hair.visibility(self.objects,spec);hands.visibility(self.objects)
        update_rest(self.rig,spec['body']);posing.apply(self.rig,spec);self.rig['chibi_spec']=json.dumps(spec,ensure_ascii=False,sort_keys=True);bpy.context.view_layer.update();return self
    def randomize_body(self,seed=None,curvature_probability=None):
        spec=self.parameters
        if curvature_probability is not None:spec['curvature_probability']=curvature_probability
        fresh=model.generate_spec(seed,spec['curvature_probability']);spec['body']=fresh['body'];spec['seed']=fresh['seed'];return self.apply(spec)
    def randomize_face(self,seed=None):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;spec['face']=model.sample_face(seed);spec['face_seed']=seed;return self.apply(spec)
    def randomize_makeup(self,seed=None):
        import secrets
        spec=self.parameters;seed=secrets.randbelow(2**31) if seed is None else seed;spec['makeup']=model.sample_style_makeup(seed,spec['style']);spec['makeup_seed']=seed;return self.apply(spec)
    def save_preset(self,path):model.save_preset(self.parameters,path)
    def delete(self):
        col=self.collection;materials={m for ob in col.objects if ob.type=='MESH' for m in ob.data.materials if m}
        for ob in list(col.objects):
            data=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
            if data and data.users==0:
                if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
                elif isinstance(data,bpy.types.Armature):bpy.data.armatures.remove(data)
        bpy.data.collections.remove(col)
        for m in materials:
            if m.users==0:bpy.data.materials.remove(m)

def generate_character(seed=None,curvature_probability=model.CURVATURE_CHANCE,body=None,spec=None,style=None,style_mix=None):
    spec=model.validate(spec) if spec is not None else model.generate_spec(seed,curvature_probability,style,style_mix)
    if body:spec=model.update_body(spec,**body)
    col=bpy.data.collections.new('CHIBI '+str(spec['seed']));col['chibi_character_id']=str(uuid.uuid4());bpy.context.scene.collection.children.link(col)
    arm=bpy.data.armatures.new('Chibi Humanoid');rig=bpy.data.objects.new('CHIBI_Rig',arm);col.objects.link(rig);rig.show_in_front=True;arm.display_type='OCTAHEDRAL'
    rig['chibi_spec']=json.dumps(spec);rig['chibi_character_id']=col['chibi_character_id'];rig['adult_age']=spec['age']
    neutral=dict(spec['body']);neutral.update(height=.5,thigh_size=.5,calf_size=.5,leg_asymmetry=0,shoulder_tilt=0,curve_severity=0)
    try:
        update_rest(rig,neutral)
        for section,src in templates():
            ob=src.copy();ob.data=src.data.copy();ob.use_fake_user=False;ob.name=src.name;col.objects.link(ob);ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4)
            part=src.get('chibi_part') or part_for(src.name,section)
            if part not in ('body','head','leg','skirt','neck','arm','hip'):raise ValueError('Unknown body attachment part: '+str(part))
            ob['chibi_part']=part;ob['chibi_asset']=src.name;ob['chibi_section']=section
            if ob.data.shape_keys:raise ValueError('Neutral asset unexpectedly contains shape keys')
            refine_garment(ob)
            ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation')
        facial.own_materials(list(col.objects));facial.extra_assets(col,rig)
        bpy.context.view_layer.update()
        for ob in list(col.objects):
            if ob.type=='MESH':bind(ob,rig,ob['chibi_part'])
        result=Character(rig).apply(spec)
    except Exception:
        Character(rig).delete();raise
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    return result

def active_character(context=None):
    ob=(context or bpy.context).object
    while ob:
        if ob.type=='ARMATURE' and ob.get('chibi_spec'):return Character(ob)
        ob=ob.parent
    return None

def load_character(path):return generate_character(spec=model.load_preset(path))
