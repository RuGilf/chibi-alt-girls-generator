"""Thirty neutral, editable hairstyles with broad sculpted locks and vertex tints."""
import math
import bpy,numpy as np
from math import sin,cos,pi
from mathutils import Vector
from . import model,clothing,facial
REVISION=4

def curve(control,steps=10):
    p=[Vector(v) for v in control];out=[]
    for i in range(len(p)-1):
        a,b,c,d=p[max(0,i-1)],p[i],p[i+1],p[min(len(p)-1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out+[p[-1]]

def tint_material(rig):
    name='Hair tint • '+rig['chibi_character_id']
    m=bpy.data.materials.get(name)
    if m:return m
    m=clothing.fabric(name,(.021,.017,.039),.36,surface='hair')
    # Clean polished locks; fabric bump would look like rough felt.
    bs=m.node_tree.nodes.get('Principled BSDF')
    for link in list(m.node_tree.links):
        if link.to_socket==bs.inputs['Normal']:m.node_tree.links.remove(link)
    bs.inputs['Specular IOR Level'].default_value=.32
    n=m.node_tree.nodes.new('ShaderNodeVertexColor');n.layer_name='HairTint';m.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color'])
    m['chibi_hair_material']=True;return m

class Builder:
    def __init__(self,col,rig,key):
        self.col,self.rig,self.key=col,rig,key;self.cfg=model.HAIR_PRESETS[key];self.objects=[];self.mat=tint_material(rig)
    def obj(self,mesh,name,accent=False,light=False):
        ob=mesh.object('Hair • '+self.key+' • '+name,self.mat,self.col,self.rig,'hair',self.key,'head')
        del ob['chibi_slot'];del ob['chibi_option'];ob['chibi_section']='03 Hair';ob['chibi_hair']=self.key;ob['chibi_hair_rev']=REVISION
        ob['chibi_hair_accent']=accent;ob['chibi_hair_light']=light;self.objects.append(ob);return ob
    def lock(self,name,control,width=.045,depth=.015,accent=False,light=False,axis=(1,0,0)):
        if 'fringe' in name:
            root=Vector(control[0]);rx=self.cfg.get('width',.347);ry=.280+(rx-.347)*.55
            root.y=.026-ry*math.sqrt(max(.001,1-(root.x/rx)**2-((root.z-1.534)/.379)**2))+.010
            control=[tuple(root),*control[1:]]
        elif name.startswith('feathered layer'):
            root=Vector(control[0]);rx=self.cfg.get('width',.35)
            crown=1.534+.379*math.sqrt(max(.001,1-(root.x/rx)**2-((root.y-.026)/.28)**2))
            root.z=min(root.z,crown-.022)
            control=[tuple(root),*control[1:]]
        pts=curve(control)
        if 'fringe' in name:
            # Follow the rounded crown instead of bridging it with a flat visor.
            rx=self.cfg.get('width',.347);ry=.280+(rx-.347)*.55
            for p in pts:
                if p.z<=1.73:continue
                shell=.026-ry*math.sqrt(max(.001,1-(p.x/rx)**2-((p.z-1.534)/.379)**2))
                if p.z<=1.875:shell=min(shell,float(facial.face_y(np.array([p.x]),np.array([p.z]))[0])-.014)
                blend=float(facial.smooth(1.73,1.82,p.z))
                p.y=p.y*(1-blend)+(shell-.003)*blend
        m=clothing.Mesh();seg=12;last=None
        for i,p in enumerate(pts):
            t=i/(len(pts)-1);tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();u=Vector(axis) if last is None else last
            u=u-tangent*u.dot(tangent)
            if u.length<.01:u=tangent.cross(Vector((0,1,0)))
            u.normalize();last=u.copy();n=tangent.cross(u).normalized()
            # Broad embedded roots blend into the cap; gradual tips avoid bead-like bangs.
            taper=float(facial.smooth(.48,1.,t))
            w=width*(.72+.28*sin(pi*t))*(1-.98*taper)
            d=depth*(.65+.35*sin(pi*t))*(1-.96*taper)
            if 'fringe' in name:d*=.72
            else:
                root_blend=.08+.92*float(facial.smooth(0,.14,t))
                w*=root_blend;d*=root_blend
            for j in range(seg):a=2*pi*j/seg;m.v.append(tuple(p+w*cos(a)*u+d*sin(a)*n))
        for i in range(len(pts)-1):
            for j in range(seg):a=i*seg+j;b=i*seg+(j+1)%seg;m.f.append((a,b,b+seg,a+seg))
        m.f.extend([tuple(reversed(range(seg))),tuple((len(pts)-1)*seg+j for j in range(seg))]);return self.obj(m,name,accent,light)
    def cap(self,short=False,shaved=False):
        m=clothing.Mesh();seg=96;rows=38;cfg=self.cfg;rx=cfg.get('width',.347);ry=.280+(rx-.347)*.55
        if shaved:rx=.332;ry=.266
        for i in range(rows):
            t=i/(rows-1)
            for j in range(seg):
                phi=2*pi*j/seg;front=max(0,-sin(phi));back=1.75 if short else min(1.94,math.acos(max(-.99,min(.99,(cfg.get('end',1.35)-1.534)/.379))))
                end=back-(back-.97)*front**1.2
                theta=.012+(end-.012)*t;z=1.534+(.374 if shaved else .379)*cos(theta)
                m.v.append((rx*sin(theta)*cos(phi),.026+ry*sin(theta)*sin(phi),z))
        for i in range(rows-1):
            for j in range(seg):a=i*seg+j;b=i*seg+(j+1)%seg;m.f.append((a,b,b+seg,a+seg))
        # The approved head has a broad cheek/temple cross-section, not an ellipsoid.
        # Enclose that exact surface before applying the shared face and body morphs.
        a=np.array(m.v);z=a[:,2];rxhead=np.interp(z,facial.PROFILE[:,0],facial.PROFILE[:,1]);cy=np.interp(z,facial.PROFILE[:,0],facial.PROFILE[:,3])
        if shaved:
            # Keep close-cropped temples outside the head at the widest side of every ring.
            ring_width=np.repeat(np.max(np.abs(a[:,0].reshape(rows,seg)),axis=1),seg)
            a[:,0]*=np.where(z<=1.875,np.maximum(1,(rxhead+.018)/np.maximum(.001,ring_width)),1)
        front=facial.face_y(a[:,0],z);back=2*cy-front;inside=(z<=1.875)&(np.abs(a[:,0])<rxhead)
        frontside=a[:,1]<cy;a[inside&frontside,1]=np.minimum(a[inside&frontside,1],front[inside&frontside]-.014)
        a[inside&~frontside,1]=np.maximum(a[inside&~frontside,1],back[inside&~frontside]+.014);m.v=a.tolist()
        ob=self.obj(m,'scalp foundation');ob['chibi_hair_shaved']=shaved;sol=ob.modifiers.new('Hair silhouette thickness','SOLIDIFY');sol.thickness=.008;sol.offset=0
    def bangs(self):
        kind=self.cfg.get('bangs','curtain')
        if kind=='none':return
        if kind=='side':
            for i in range(4):
                x=.11-i*.062
                self.lock('swept fringe '+str(i),[(x,-.11,1.895),(x-.05,-.235,1.825),(x-.13,-.274,1.739),(x-.18,-.243,1.665+i*.012)],.057,.017,accent=i==3,light=i==1)
        elif kind in ('blunt','short','choppy'):
            count=9
            for i in range(count):
                x=-.24+.48*i/(count-1);side=abs(x)/.24;end=1.716 if kind=='blunt' else 1.755 if kind=='short' else 1.705+.026*sin(i*2.1)
                # Forehead shell stays outside the facial surface; eyes remain visible.
                self.lock('fringe panel '+str(i),[(x*.45,-.13,1.89),(x*.80,-.235,1.82),(x,-.274+.055*side**2,end+.035),(x+(.008 if i%2 else -.008),-.271+.060*side**2,end)],.040 if kind!='choppy' else .045,.015,accent=i in (1,7),light=i%3==0)
        else:
            for side in (-1,1):
                for i in range(3):
                    self.lock('curtain fringe '+str((side,i)),[(side*(.025+i*.022),-.09,1.904),(side*(.08+i*.046),-.229,1.835),(side*(.185+i*.035),-.257+i*.018,1.735),(side*(.265+i*.025),-.179+i*.02,1.575-i*.040)],.048,.015,accent=i==2,light=i==1)
    def loose(self):
        cfg=self.cfg;end=cfg.get('end',1.20);rx=cfg.get('width',.35);wave=cfg.get('wave',0);curl=cfg.get('curl',0)
        m=clothing.Mesh();rows=34;seg=64;start_phi=.5*pi if cfg.get('shave') else -.10;span=pi+.10-start_phi
        for i in range(rows):
            t=i/(rows-1)
            for j in range(seg+1):
                phi=start_phi+span*j/seg;bottom=end+cfg.get('asym',0)*cos(phi)+.012*sin(phi*7)
                z=1.57+(bottom-1.57)*t;fold=1+.014*sin(12*phi)*t
                r=rx*(1-.09*t)+wave*sin(t*3*pi+phi)*t
                m.v.append((r*cos(phi)*fold,.026+(.279-.055*t)*sin(phi)*fold,z))
        for i in range(rows-1):
            for j in range(seg):a=i*(seg+1)+j;m.f.append((a,a+1,a+seg+2,a+seg+1))
        ob=self.obj(m,'continuous back curtain');sol=ob.modifiers.new('Back hair thickness','SOLIDIFY');sol.thickness=.012
        for j in range(13):
            phi=start_phi+span*j/12;bottom=end+cfg.get('asym',0)*cos(phi)+.018*sin(j*2.1);pts=[]
            for k in range(9):
                t=k/8
                if t<.33:
                    theta=.57+(1.53-.57)*t/.33;r=rx*sin(theta);y=.026+.288*sin(theta)*sin(phi);z=1.534+.384*cos(theta);x=r*cos(phi)
                else:
                    u=(t-.33)/.67;z=1.55+(bottom-1.55)*u;r=rx*(1-.09*u)+wave*sin(u*3*pi+phi)*u;x=r*cos(phi);y=.026+(.287-.048*u)*sin(phi)
                    if curl:x+=curl*sin(5*pi*u+j)*u;y+=curl*cos(5*pi*u+j)*u
                pts.append((x,y,z))
            self.lock('back sculpted lock '+str(j),pts,.050 if not curl else .043,.016,accent=j in (1,11),light=j%3==1,axis=(-sin(phi),cos(phi),0))
        for side in (-1,1):
            if cfg.get('shave') and side==1:continue
            bottom=max(.78,end+.03+cfg.get('asym',0)*side)
            start=max(1.39,bottom+.05);controls=[(side*.26,-.132,1.78),(side*(rx+.002),-.135,1.61),(side*(rx+.005),-.121,start)]
            for k in range(1,6):
                t=k/5;z=start+(bottom-start)*t;w=(wave+.7*curl)*sin(t*(3 if curl else 2)*pi)*sin(pi*t*.8)
                controls.append((side*(rx+.005-.050*t+w),-.13+curl*cos(t*5*pi)*t,z))
            self.lock('face frame '+str(side),controls,.047,.018,accent=side==1,axis=(.45,.90,0))
        if cfg.get('bun'):self.bun((0,.10,1.94),.10,'half-up bun')
    def layered(self):
        self.loose();cfg=self.cfg;rx=cfg.get('width',.35)
        for side in (-1,1):
            for tier in range(3 if not cfg.get('mullet') else 2):
                end=1.54-tier*.13;root=1.90-tier*.10
                self.lock('feathered layer '+str((side,tier)),[(side*.13,.035,root),(side*(rx-.02),-.03,root-.08),(side*(rx+.035),-.02,end+.045),(side*(rx+.055),-.012,end)],.060 if cfg.get('scene') else .050,.021,accent=tier==2,light=tier==1,axis=(.6,.8,0))
    def short(self):
        for j in range(14):
            phi=-.1+(pi+.2)*j/13;pts=[]
            for k in range(6):theta=.30+1.32*k/5;pts.append((.340*sin(theta)*cos(phi),.027+.279*sin(theta)*sin(phi),1.534+.388*cos(theta)))
            self.lock('short textured lock '+str(j),pts,.043,.014,accent=j==2,light=j%3==1,axis=(-sin(phi),cos(phi),0))
    def bun(self,center,r,label):
        x,y,z=center
        # Broad interwoven arcs show a tied-up bun rather than a plain sphere.
        m=clothing.Mesh();m.loft([(x,y,z+r*cos(pi*i/24),max(.001,r*sin(pi*i/24)),max(.001,r*.86*sin(pi*i/24))) for i in range(25)],48,True);self.obj(m,label)
        for i in range(7):
            a=2*pi*i/7;self.lock(label+' wrapped lock '+str(i),[(x+r*.6*cos(a),y+r*.5*sin(a),z+r*.65),(x+r*1.01*cos(a+.5),y+r*.88*sin(a+.5),z),(x+r*.6*cos(a+1),y+r*.6*sin(a+1),z-r*.65)],.035,.012,accent=i==1,light=i%3==0,axis=(cos(a),sin(a),0))
    def tied(self):
        cfg=self.cfg;n=cfg.get('tails',1);high=cfg.get('high',True)
        for side in ((-1,1) if n==2 else (0,)):
            root=(side*.292,.13,1.79) if n==2 and high else (side*.282,.12,1.49) if n==2 else (0,.24,1.93 if high else 1.48)
            for j in range(7):
                a=2*pi*j/7;dx=.055*cos(a);dy=.035*sin(a);rx,ry,rz=root;end=cfg['end']+.025*sin(j)
                controls=[root,(rx+side*.15+dx,ry+.065+dy,rz-.14),(rx+side*.18+dx,ry+.07+dy,(rz+end)/2),(rx+side*.14+dx*.7,ry+.02+dy*.7,end)]
                if n==1:controls=[root,(dx+.14,ry+.115+dy,rz-.17),(dx+.20,ry+.105+dy,(rz+end)/2),(dx*.6+.15,ry+.04+dy,end)]
                self.lock('pony lock '+str((side,j)),controls,.051,.027,accent=j==1,light=j%3==0,axis=(1,0,0))
            ring=clothing.Mesh().tube([(root[0]+.059*cos(2*pi*j/48),root[1]+.050*sin(2*pi*j/48),root[2]-.018) for j in range(49)],.008,10);self.obj(ring,'hair tie '+str(side),True)
    def braids(self):
        cfg=self.cfg;n=cfg['count'];end=cfg['end']
        for side in ((-1,1) if n==2 else (0,)):
            x=side*.315;y=.10 if n==2 else .29;top=1.46
            for strand in range(3):
                pts=[]
                for k in range(85):
                    t=k/84;phase=2*pi*5*t+strand*2*pi/3;r=.036*(1-.45*t)
                    pts.append((x+r*cos(phase)+side*.04*t,y+r*.75*sin(phase),top+(end-top)*t))
                self.lock('braid strand '+str((side,strand)),pts,.026,.024,accent=strand==2,axis=(1,0,0))
            self.lock('braid tip '+str(side),[(x+side*.04,y,end+.01),(x+side*.055,y,end-.07),(x+side*.05,y,end-.11)],.035,.025,True)
    def dreads(self):
        cfg=self.cfg
        for j in range(22):
            phi=-.55+(pi+1.10)*j/21;end=cfg['end']+.10*sin(j*1.4);pts=[]
            for k in range(19):
                t=k/18
                if t<.36:
                    theta=.16+1.39*t/.36;r=cfg.get('width',.37)*sin(theta);z=1.534+.391*cos(theta);y=.026+.29*sin(theta)*sin(phi)
                else:
                    u=(t-.36)/.64;r=cfg.get('width',.37)+.025*sin(pi*u);z=1.542+(end-1.542)*u;y=.026+(.29+.045*u)*sin(phi)
                pts.append((r*cos(phi)+.005*sin(t*7*pi+j),y,z))
            self.lock('dread '+str(j),pts,.026,.025,accent=j%3==0,light=j%4==1,axis=(-sin(phi),cos(phi),0))
    def build(self):
        family=self.cfg['family'];self.cap(short=family in ('short','mohawk','tied','buns','braids') or self.cfg.get('shave',False),shaved=family=='mohawk' or self.cfg.get('undercut',False) or self.cfg.get('shave',False))
        if family=='loose':self.loose()
        elif family=='layered':self.layered()
        elif family=='short':self.short()
        elif family=='tied':self.tied()
        elif family=='braids':self.braids()
        elif family=='buns':
            if self.cfg['count']==2:
                for side in (-1,1):self.bun((side*.265,.08,1.87),.105,'space bun '+str(side))
            else:self.bun((0,.16,1.985),.12,'messy bun')
        elif family=='mohawk':
            for j in range(8):
                y=-.17+.40*j/7;z=1.92+.07*sin(pi*j/7)
                self.lock('crest '+str(j),[(0,y,1.80),(0,y-.03,z),(0,y+.015,z+.13),(0,y+.055,z+.10)],.027,.042,accent=j%3==0,axis=(1,0,0))
        elif family=='dreads':self.dreads()
        self.bangs();return self.objects

def ensure(col,rig,spec):
    key=spec['hair']['preset']
    if key=='bob':return []
    if any(o.get('chibi_hair')==key and o.get('chibi_hair_rev')==REVISION for o in col.objects):return []
    return Builder(col,rig,key).build()

def visibility(objects,spec):
    key=spec['hair']['preset']
    for ob in objects:
        if ob.get('chibi_section')!='03 Hair':continue
        selected=ob.get('chibi_hair','bob')==key and (not ob.get('chibi_hair') or ob.get('chibi_hair_rev')==REVISION)
        ob.hide_render=not selected;ob.hide_viewport=not selected

def paint(ob,points,spec,rig):
    if ob.get('chibi_section')!='03 Hair':return
    original=not ob.get('chibi_hair');name=ob['chibi_asset'];hair=spec['hair'];a=np.array(model.HAIR_COLORS[hair['color']][1]);b=np.array(model.HAIR_COLORS[hair['secondary']][1]);p=np.asarray(points)
    accent=ob.get('chibi_hair_accent',False) or (original and ('underlayer' in name or 'accent lock' in name))
    light=ob.get('chibi_hair_light',False) or (original and any(m and m.name.startswith('Plum light planes') for m in ob.data.materials))
    # Cache the role before replacing original shared materials with the owned tint.
    if original:ob['chibi_hair_accent']=accent;ob['chibi_hair_light']=light
    blend=np.zeros(len(p));pattern=hair['pattern']
    if pattern=='streaks' and accent:blend[:]=1
    elif pattern=='split':blend=np.clip((p[:,0]+.005)/.01,0,1)
    elif pattern in ('ombre','dipped'):
        end=model.HAIR_PRESETS[hair['preset']].get('end',1.34);low=end+(.18 if pattern=='ombre' else .08);high=1.76 if pattern=='ombre' else end+.25
        blend=1-np.clip((p[:,2]-low)/max(.03,high-low),0,1);blend=blend*blend*(3-2*blend)
    rgb=a[None,:]*(1-blend[:,None])+b[None,:]*blend[:,None]
    if light:
        if hair['color']=='ink' and pattern in ('solid','streaks') and not accent:rgb[:]=(.037,.025,.064)
        else:rgb=np.clip(rgb*1.18+.004,0,1)
    if ob.get('chibi_hair_shaved'):rgb*=.48
    attr=ob.data.color_attributes.get('HairTint') or ob.data.color_attributes.new(name='HairTint',type='FLOAT_COLOR',domain='POINT');attr.data.foreach_set('color',np.column_stack((rgb,np.ones(len(rgb)))).ravel())
    mat=tint_material(rig)
    if len(ob.data.materials)!=1 or ob.data.materials[0]!=mat:ob.data.materials.clear();ob.data.materials.append(mat)


def fit_accessory(points,ob,spec):
    if spec['hair']['preset']=='bob':return points
    name=ob.get('chibi_asset','');q=np.asarray(points).copy()
    if name.startswith(('Crescent hair clip','Lavender hair bar')):q+=(-.020,.100,.035)
    elif name.startswith(('Silver hoop earring','Earring orchid')):q+=(.005,.030,.100)
    return q
