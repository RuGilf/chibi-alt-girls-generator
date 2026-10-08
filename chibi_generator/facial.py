"""Continuous face morphs and separate, conforming cosmetic layers."""
import math
import bpy
import numpy as np
from . import model

PROFILE=np.array([(1.205,.040,.047,.015),(1.223,.095,.090,.005),(1.25,.160,.132,.002),(1.29,.225,.178,.002),(1.34,.277,.212,.008),(1.41,.307,.237,.014),(1.50,.324,.254,.020),(1.60,.325,.255,.023),(1.69,.305,.243,.026),(1.77,.255,.208,.029),(1.83,.174,.148,.030),(1.865,.080,.072,.030),(1.875,.003,.003,.030)])
def face_y(x,z):
    x=np.asarray(x);z=np.asarray(z);i=np.clip(np.searchsorted(PROFILE[:,0],z,side='right')-1,0,len(PROFILE)-2)
    lo=PROFILE[i];hi=PROFILE[i+1];before=PROFILE[np.maximum(0,i-1)];after=PROFILE[np.minimum(len(PROFILE)-1,i+2)]
    dz=hi[...,0]-lo[...,0];t=np.clip((z-lo[...,0])/dz,0,1)
    m0=(hi[...,1:]-before[...,1:])/(hi[...,0]-before[...,0])[...,None];m1=(after[...,1:]-lo[...,1:])/(after[...,0]-lo[...,0])[...,None]
    v=(2*t**3-3*t*t+1)[...,None]*lo[...,1:]+((t**3-2*t*t+t)*dz)[...,None]*m0+(-2*t**3+3*t*t)[...,None]*hi[...,1:]+((t**3-t*t)*dz)[...,None]*m1
    return v[...,2]-v[...,1]*np.maximum(.001,1-(x/v[...,0])**2)**.36

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def morph(points,face,asset,part,makeup):
    q=np.asarray(points,dtype=np.float64).copy()
    if part!='head':return q
    old=q.copy();name=asset.split('.')[0]
    if name.startswith('Freckle colour layer'):
        patches=q.reshape(-1,8,3);centers=patches.mean(axis=1,keepdims=True)
        # Density changes without pale, raised-looking dots at low opacity.
        order=(np.arange(len(patches))*37)%len(patches)
        keep=(order<makeup['freckles']*len(patches)).astype(float)
        patches[:]=centers+(patches-centers)*keep[:,None,None]
        q[:,1]=face_y(q[:,0],q[:,2])-.0011
    eye=name.startswith(('Almond sclera','Large violet iris','Pupil','Main catchlight','Secondary catchlight','Upper eyeliner','Lower lid','Winged liner','Outer lash'))
    if eye:
        side=1 if q[:,0].mean()>0 else -1;cx=side*.128;cz=1.581
        x=q[:,0]-cx;z=q[:,2]-cz
        if name.startswith('Winged liner'):
            outer=side*(q[:,0]-cx)-.076;scale=model.MAKEUP_PRESETS[makeup['preset']][-2]
            q[:,0]=cx+side*(.076+outer*scale);x=q[:,0]-cx
        scale=face['eye_size'];height=.91 if face['expression']=='dreamy' else 1.03 if face['expression'] in ('cheerful','wink') else 1
        if face['expression']=='wink' and side==1:
            if name.startswith('Upper eyeliner'):
                # Translate each tube ring rather than flattening its cross-section.
                centers=old.reshape(-1,10,3).mean(axis=1)
                local_z=old[:,2]-np.repeat(centers[:,2],10)
                u=np.repeat((centers[:,0]-cx)/.080,10)
                z=local_z+.006*u*u-.003
            else:z=z*.20+.004*((x/.076)**2-.35)
            height=1
        angle=side*face['eye_tilt']*.15
        q[:,0]=cx+side*face['eye_spacing']*.012+scale*(x*np.cos(angle)-z*np.sin(angle))
        q[:,2]=cz+scale*(x*np.sin(angle)+z*np.cos(angle)*height)
    elif name.startswith('Brow'):
        side=1 if q[:,0].mean()>0 else -1;cx=side*.128
        q[:,0]+=side*face['eye_spacing']*.012
        outer=side*(q[:,0]-cx)/.06
        q[:,2]+=face['eye_tilt']*.006*outer+face.get('brow_height',0)*.016+face.get('brow_arch',0)*.010*np.maximum(0,1-outer**2)
        if face['expression'] in ('cheerful','wink'):q[:,2]+=.006+.004*(1-outer**2)
        elif face['expression']=='serious':q[:,2]+=.006*outer-.004
        elif face['expression']=='dreamy':q[:,2]-=.004
    elif name.startswith(('Quiet rose smile','Lower lip highlight','Lip colour layer')):
        if name.startswith('Quiet rose smile'):
            centers=old.reshape(-1,8,3).mean(axis=1)
            q[:,2]+=np.repeat(1.412+.0015*(centers[:,0]/.035)**2-centers[:,2],8)
        u=np.clip(q[:,0]/.035,-1.25,1.25)
        q[:,0]*=1+.30*face.get('mouth_width',0)
        q[:,2]=1.412+(q[:,2]-1.412)*(1+.45*face.get('lip_fullness',0))
        if face['expression'] in ('cheerful','wink'):q[:,2]+=.010*u*u-.0025
        elif face['expression']=='serious':q[:,2]-=.004*u*u-.001
    elif name.startswith('Button nose'):
        center=(q[:,2].min()+q[:,2].max())*.5
        q[:,0]*=1+.30*face.get('nose_width',0)
        q[:,2]=center+(q[:,2]-center)*(1+.15*face.get('nose_projection',0))
        depth=old[:,1]-face_y(old[:,0],old[:,2])
        q[:,1]=face_y(q[:,0],q[:,2])+depth*(1+.45*face.get('nose_projection',0))
    # Reproject facial features onto their new position before changing the head silhouette.
    if eye or name.startswith(('Brow','Quiet rose smile','Lower lip highlight','Lip colour layer')):
        q[:,1]+=face_y(q[:,0],q[:,2])-face_y(old[:,0],old[:,2])
    z=q[:,2];blend=smooth(1.205,1.25,z)
    width=1+blend*(face['width']*.085+face['jaw']*.14*np.exp(-((z-1.315)/.105)**2)+face['cheeks']*.065*np.exp(-((z-1.47)/.095)**2))
    q[:,0]*=width
    q[:,2]-=.022*face['chin']*np.exp(-((z-1.31)/.10)**2)*blend
    return q

def _material(name,color,roughness=.5):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.diffuse_color=(*color,1)
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
    return mat

def extra_assets(col,rig):
    """Neutral lip colour and small freckle decals, all attached to the head bone."""
    result=[]
    def create(name,verts,faces,mat):
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(mat)
        ob=bpy.data.objects.new(name,mesh);col.objects.link(ob);ob.parent=rig;ob['chibi_asset']=name;ob['chibi_part']='head'
        ob.shape_key_add(name='Basis');ob.shape_key_add(name='BodyVariation')
        for poly in mesh.polygons:poly.use_smooth=True
        result.append(ob)
    verts=[(0,float(face_y(0,1.412))-.0015,1.412)];faces=[];seg=96;rings=10
    for i in range(1,rings+1):
        r=i/rings
        for j in range(seg):
            a=math.tau*j/seg;x=.034*r*math.cos(a);s=math.sin(a)
            z=1.412+(.008 if s>=0 else .009)*r*s
            if s>=0:z-=.002*r*math.exp(-(x/.008)**2)*s
            verts.append((x,float(face_y(x,z))-.0015,z))
    for j in range(seg):faces.append((0,1+j,1+(j+1)%seg))
    for i in range(rings-1):
        for j in range(seg):a=1+i*seg+j;b=1+i*seg+(j+1)%seg;faces.append((a,b,b+seg,a+seg))
    create('Lip colour layer',verts,faces,_material('Lip colour',(.4,.1,.12),.42))
    verts=[];faces=[];r=np.random.default_rng(1647)
    for side in (-1,1):
        for k in range(32):
            x=side*r.uniform(.055,.245);z=1.505+r.normal(0,.018);radius=r.uniform(.0014,.0034);start=len(verts)
            for j in range(8):
                a=j*math.tau/8;xx=x+radius*math.cos(a);zz=z+radius*math.sin(a);verts.append((xx,float(face_y(xx,zz))-.0011,zz))
            faces.append(tuple(start+j for j in range(8)))
    create('Freckle colour layer',verts,faces,_material('Soft freckles',(.26,.095,.045),.65))
    return result

def own_materials(objects):
    owned={}
    for ob in objects:
        asset=ob.get('chibi_asset','')
        if ob.type!='MESH' or not (asset.startswith('Head') or ob.get('chibi_section')=='02 Face'):continue
        for slot in ob.material_slots:
            if slot.material:
                original=slot.material
                if original.name not in owned:owned[original.name]=original.copy()
                slot.material=owned[original.name]

def detail_materials(objects,rig):
    """Lip details must not recolor the shared lower-lid or nose materials."""
    for ob in objects:
        role=ob.get('chibi_asset','').split('.')[0]
        if role not in ('Quiet rose smile','Lower lip highlight'):continue
        source=ob.data.materials[0]
        if source.get('chibi_lip_detail')==role and source.get('chibi_lip_owner')==rig['chibi_character_id']:continue
        mat=source.copy();mat['chibi_lip_detail']=role;mat['chibi_lip_owner']=rig['chibi_character_id'];ob.data.materials[0]=mat
        bs=mat.node_tree.nodes.get('Principled BSDF')
        for link in list(mat.node_tree.links):
            if link.to_socket==bs.inputs['Base Color']:mat.node_tree.links.remove(link)
        tone=mat.node_tree.nodes.get('Chibi skin tone')
        if tone and not tone.outputs[0].links:mat.node_tree.nodes.remove(tone)
        if source.users==0 and not source.use_fake_user:bpy.data.materials.remove(source)

def visibility(objects,spec):
    """Cosmetic layers own their visibility, independently from wardrobe caches."""
    hidden=spec['makeup']['freckles']<=.001
    for ob in objects:
        name=ob.get('chibi_asset','').split('.')[0]
        if name=='Freckle colour layer':
            ob.hide_render=hidden;ob.hide_viewport=hidden
        elif name.startswith(('Almond sclera','Large violet iris','Pupil','Main catchlight','Secondary catchlight','Lower lid')):
            closed=spec['face']['expression']=='wink' and name.endswith(' 1')
            ob.hide_render=closed;ob.hide_viewport=closed

def paint(ob,points,spec):
    face=spec['face'];cosmetics=spec['makeup'];name=ob['chibi_asset'];preset=model.MAKEUP_PRESETS[cosmetics['preset']]
    _,shadow,shadow_strength,blush,blush_strength,lip,lip_strength,wing,freckles=preset
    intensity=cosmetics['intensity'];base=np.array(model.skin_rgb(spec['skin']))
    if name.startswith('Head'):
        x,y,z=np.asarray(points).T;front=smooth(.03,.17,-y)
        colors=np.tile(base,(len(x),1))
        def mix(color,mask):
            nonlocal colors
            mask=np.clip(mask*front,0,1)[:,None];colors=colors*(1-mask)+np.array(color)*mask
        cx=.128+face['eye_spacing']*.012
        # Broad feathered shadow on the upper lid; skin still reads as skin.
        mask=np.exp(-((abs(x)-cx)/(.080*face['eye_size']))**4-((z-1.653)/.029)**2)*smooth(1.624,1.642,z)
        mix(shadow,mask*min(.94,shadow_strength*1.65)*intensity)
        if cosmetics['preset'] in ('smoky','berry','lavender'):
            mix(shadow,np.exp(-((abs(x)-cx)/.077)**4-((z-1.521)/.013)**2)*shadow_strength*.22*intensity)
        mix(blush,np.exp(-((abs(x)-.205)/.065)**2-((z-1.492)/.038)**2)*blush_strength*intensity)
        attr=ob.data.color_attributes.get('FacePaint');rgba=np.column_stack((colors,np.ones(len(x))))
        attr.data.foreach_set('color',rgba.ravel())
    elif name.startswith('Large violet iris'):
        side=1 if points[:,0].mean()>0 else -1;x=points[:,0]-side*.128;z=points[:,2]-1.581
        t=np.clip((z+.048)/.096,0,1);rad=np.sqrt((x/.043)**2+(z/.049)**2);edge=np.clip((rad-.81)/.16,0,1)
        light=np.array(model.EYE_COLORS[face['eye_color']]);dark=light*.16
        f=(1-t)*.85+.10;rgb=(dark[None,:]*(1-f[:,None])+light[None,:]*f[:,None])*(1-.76*edge[:,None])*(.94+.06*np.cos(np.arctan2(z/.049,x/.043)*28))[:,None]
        ob.data.color_attributes['IrisPaint'].data.foreach_set('color',np.column_stack((rgb,np.ones(len(rgb)))).ravel())
    elif name.startswith(('Lip colour layer','Quiet rose smile','Lower lip highlight')):
        color=base*(1-lip_strength**.5*intensity)+np.array(lip)*lip_strength**.5*intensity
        if name.startswith('Quiet rose smile'):color*=.55
        elif name.startswith('Lower lip highlight'):color=color*.65+base*.35
        bs=ob.data.materials[0].node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1)
        bs.inputs['Roughness'].default_value=.36 if cosmetics['preset'] in ('rose','peach','sunset') else .52
    elif name.startswith('Freckle colour layer'):
        amount=cosmetics['freckles'];ob.hide_render=amount<=.001;ob.hide_viewport=amount<=.001
        color=base*.35+np.array([.20,.065,.025])*.65
        ob.data.materials[0].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
