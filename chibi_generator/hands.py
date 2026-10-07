"""Continuous chibi hands, explicit finger skinning and attached short nails."""
import bpy,math,numpy as np
from mathutils import Vector
from . import clothing
REVISION=5
FINGERS=('index','middle','ring','pinky')
# Root x, total length and relaxed spread; palm is centered at x=.309.
DIGITS=[(-.024,.061,-.004),(-.007,.068,0),(.010,.062,.003),(.026,.049,.006)]

def finger_points(side,name):
    sign=1 if side=='L' else -1
    if name=='thumb':return [(sign*x,y,z) for x,y,z in [( .279,-.014,.819),(.264,-.014,.810),(.255,-.014,.797),(.252,-.014,.784)]]
    x,length,spread=DIGITS[FINGERS.index(name)]
    return [(sign*(.309+x+spread*t),-.014, .796-length*t) for t in (0,.36,.71,1)]

def _sphere(mesh,center,scale,seg=24,rows=18):
    start=len(mesh.v)
    for i in range(rows+1):
        a=math.pi*i/rows
        for j in range(seg):
            p=math.tau*j/seg;mesh.v.append((center[0]+scale[0]*math.sin(a)*math.cos(p),center[1]+scale[1]*math.sin(a)*math.sin(p),center[2]+scale[2]*math.cos(a)))
    for i in range(rows):
        for j in range(seg):a=start+i*seg+j;b=start+i*seg+(j+1)%seg;mesh.f.append((a,b,b+seg,a+seg))

def make(col,rig):
    result=[];mat=clothing.fabric('Chibi hand skin',(.66,.36,.265),.50,surface='skin')
    bs=mat.node_tree.nodes.get('Principled BSDF')
    for link in list(mat.node_tree.links):
        if link.to_socket==bs.inputs['Normal']:mat.node_tree.links.remove(link)
    nailmat=clothing.fabric('Short lilac manicure',(.31,.16,.46),.30,surface='vinyl')
    for side,sign in [('L',1),('R',-1)]:
        m=clothing.Mesh();_sphere(m,(sign*.309,-.014,.824),(.039,.0225,.035))
        # Narrow wrist, rounded knuckles, fleshy thumb root.
        _sphere(m,(sign*.302,-.014,.847),(.031,.028,.040))
        _sphere(m,(sign*.282,-.014,.816),(.019,.023,.026))
        for name in (*FINGERS,'thumb'):
            points=finger_points(side,name);r=.0072 if name!='pinky' else .0068
            if name=='thumb':r=.0095
            # A continuous tube avoids scalloped contours from overlapping spheres.
            path=[];radii=[]
            for joint,(a,b) in enumerate(zip(points,points[1:])):
                a,b=Vector(a),Vector(b)
                for k in range(6):
                    path.append(a.lerp(b,k/6));radii.append(r*(1.12-.22*(joint+k/6)/3))
            path.append(Vector(points[-1]));radii.append(r*.90)
            m.tube(path,radii,seg=20,flatten=.91)
            for p,radius in ((path[0],radii[0]),(path[-1],radii[-1])):
                _sphere(m,p,(radius,radius*.91,radius),20,14)
        ob=m.object('Chibi unified hand '+side,mat,col,rig,'hands','unified','arm');del ob['chibi_slot'];del ob['chibi_option'];ob['chibi_section']='01 Body';ob['chibi_hand']=side;ob['chibi_hand_rev']=REVISION
        # Voxel union removes intersections between palm and digits, producing one skin surface.
        old=bpy.context.view_layer.objects.active;bpy.context.view_layer.objects.active=ob;ob.select_set(True)
        rem=ob.modifiers.new('Continuous hand surface','REMESH');rem.mode='VOXEL';rem.voxel_size=.0015;rem.use_smooth_shade=True
        bpy.ops.object.modifier_apply(modifier=rem.name)
        smooth=ob.modifiers.new('Soft hand contours','SMOOTH');smooth.factor=.65;smooth.iterations=6;bpy.ops.object.modifier_apply(modifier=smooth.name)
        bpy.context.view_layer.objects.active=old
        for poly in ob.data.polygons:poly.use_smooth=True
        result.append(ob)
        for name in (*FINGERS,'thumb'):
            a,b=map(Vector,finger_points(side,name)[-2:]);p=a.lerp(b,.57)
            p.y+=.0053 if name!='thumb' else .0071
            m=clothing.Mesh();_sphere(m,(0,0,0),(.0045 if name!='thumb' else .0055,.0013,.0062),20,14)
            direction=(b-a).normalized();rotation=Vector((0,0,-1)).rotation_difference(direction)
            m.v=[tuple(p+rotation@Vector(v)) for v in m.v]
            nail=m.object('Chibi nail '+name+'.'+side,nailmat,col,rig,'hands','unified','arm');del nail['chibi_slot'];del nail['chibi_option'];nail['chibi_section']='05 Jewelry';nail['chibi_hand']=side;nail['chibi_digit']=name;nail['chibi_hand_rev']=REVISION;result.append(nail)
    return result

def ensure(col,rig):
    if any(o.get('chibi_hand_rev')==REVISION for o in col.objects):return []
    return make(col,rig)

def visibility(objects):
    for ob in objects:
        legacy=ob.get('chibi_asset','').startswith(('Palm','Rounded finger','Thumb','Short nail'))
        if legacy:ob.hide_render=True;ob.hide_viewport=True
        elif ob.get('chibi_hand'):ob.hide_render=ob.get('chibi_hand_rev')!=REVISION;ob.hide_viewport=ob.hide_render

def wrist_weights(z,side):
    t=min(1,max(0,(z-.840)/.045));t=t*t*(3-2*t)
    return {f'hand.{side}':1-t,f'forearm.{side}':t}

def bind_wrist(ob,points):
    """Both surfaces use the same weights across their overlapping wrist area."""
    if ob.get('chibi_wrist_rev')==REVISION:return
    side='L' if points[:,0].mean()>0 else 'R'
    for vertex,p in zip(ob.data.vertices,points):
        if p[2]>=.91:continue
        blend=min(1,max(0,(.91-p[2])/.025))
        weights={ob.vertex_groups[g.group].name:g.weight*(1-blend) for g in vertex.groups}
        for name,value in wrist_weights(p[2],side).items():weights[name]=weights.get(name,0)+blend*value
        total=sum(weights.values())
        for group_index in [g.group for g in vertex.groups]:ob.vertex_groups[group_index].remove([vertex.index])
        for name,value in weights.items():
            if value>1e-7:ob.vertex_groups[name].add([vertex.index],value/total,'REPLACE')
    ob['chibi_wrist_rev']=REVISION

def bind(ob,rig):
    side=ob['chibi_hand'];pts=np.array([v.co[:] for v in ob.data.vertices]);ob.vertex_groups.clear()
    names=[f'hand.{side}',f'forearm.{side}']+[f'{f}{j}.{side}' for f in (*FINGERS,'thumb') for j in (1,2,3)]
    groups={n:ob.vertex_groups.new(name=n) for n in names}
    digit_names=(*FINGERS,'thumb');distances=[]
    for digit in digit_names:
        fp=np.array(finger_points(side,digit));ds=[]
        for a,b in zip(fp,fp[1:]):
            d=b-a;t=np.clip(((pts-a)@d)/(d@d),0,1);ds.append(np.linalg.norm(pts-a-t[:,None]*d,axis=1))
        distances.append(np.min(ds,axis=0))
    closest=np.argmin(distances,axis=0)
    if ob.get('chibi_digit'):
        groups[ob['chibi_digit']+'3.'+side].add(list(range(len(pts))),1,'REPLACE')
    else:
        sign=1 if side=='L' else -1;x=pts[:,0]*sign
        # Every distal vertex belongs to its own digit; neighbouring fingers cannot pull it.
        for i,p in enumerate(pts):
            if p[2]>.840:
                w=wrist_weights(p[2],side)
            else:
                if p[2]<.783:prob=np.eye(5)[closest[i]]
                else:
                    ds=np.array([d[i] for d in distances]);prob=np.exp(-(ds-ds.min())/.003);prob/=prob.sum()
                w={f'hand.{side}':1.}
                for digit_index,name in enumerate(digit_names):
                    if prob[digit_index]<1e-6:continue
                    fp=np.array(finger_points(side,name));root=fp[0,2]
                    if p[2]>root+.006:continue
                    if name=='thumb':activation=min(1,max(0,(.283-x[i])/.018))
                    else:activation=min(1,max(0,(.793-p[2])/.011))
                    activation*=prob[digit_index];w[f'hand.{side}']-=activation
                    weights=[1.,0.,0.]
                    for j,z in enumerate([fp[1,2],fp[2,2]]):
                        t=min(1,max(0,(z+.004-p[2])/.008));t=t*t*(3-2*t)
                        if j==0:weights=[1-t,t,0]
                        else:weights=[weights[0]*(1-t),weights[1]*(1-t),t]
                    for j in (1,2,3):w[f'{name}{j}.{side}']=activation*float(weights[j-1])
            for name,value in w.items():
                if value>1e-6:groups[name].add([i],value,'REPLACE')
    mod=ob.modifiers.new('Articulated chibi hand','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=True

    if not ob.get('chibi_digit'):
        sub=ob.modifiers.new('Soft posed skin','SUBSURF');sub.levels=1;sub.render_levels=1
