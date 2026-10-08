"""Config-driven wardrobe factories with lazy, neutral, skinned assets."""
import math
import bpy
from math import sin,cos,pi,sqrt
from . import model,clothing,anatomy,fitting
REVISION=4
Mesh=clothing.Mesh
interpolate=clothing.interpolate
COLORS={'black':(.014,.013,.022),'charcoal':(.035,.039,.050),'burgundy':(.19,.018,.043),'pink':(.65,.23,.40),'lilac':(.36,.18,.52),'cyan':(.04,.46,.52),'acid':(.25,.80,.045),'ivory':(.72,.65,.57),'denim':(.025,.040,.065),'blue':(.075,.16,.26),'olive':(.105,.115,.055),'moss':(.10,.20,.14),'brown':(.12,.065,.043),'mustard':(.48,.28,.055),'gold':(.52,.32,.09),'silver':(.55,.59,.66),'skin':(.66,.36,.265)}
PALETTE={'black':('black','silver'),'burgundy':('burgundy','black'),'pastel':('pink','lilac'),'neon':('black','acid'),'earthy':('moss','brown')}

def material(name,color,accent=None,pattern=None,rough=None,metal=0,surface=None):
    surface=surface or ('skin' if color=='skin' and not pattern else 'cloth')
    col=COLORS.get(color,color);m=clothing.fabric(name,col,rough,metal,surface)
    if not pattern:return m
    alt=COLORS.get(accent or 'ivory',accent);nodes=m.node_tree.nodes;links=m.node_tree.links
    tex=nodes.new('ShaderNodeTexCoord');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(tex.outputs['Object'],xyz.inputs[0])
    def op(kind,a,b=0):
        n=nodes.new('ShaderNodeMath');n.operation=kind
        if hasattr(a,'bl_idname'):links.new(a,n.inputs[0])
        else:n.inputs[0].default_value=a
        if hasattr(b,'bl_idname'):links.new(b,n.inputs[1])
        else:n.inputs[1].default_value=b
        return n.outputs[0]
    # Node sockets have no bl_idname on some Blender builds.
    def calc(kind,a,b=0):
        n=nodes.new('ShaderNodeMath');n.operation=kind
        for i,v in enumerate((a,b)):
            if isinstance(v,(int,float)):n.inputs[i].default_value=v
            else:links.new(v,n.inputs[i])
        return n.outputs[0]
    z=xyz.outputs['Z'];x=xyz.outputs['X'];y=xyz.outputs['Y']
    if pattern=='stripes':mask=calc('LESS_THAN',calc('FRACT',calc('MULTIPLY',z,15)),.5)
    elif pattern=='plaid':
        a=calc('LESS_THAN',calc('FRACT',calc('MULTIPLY',x,25)),.24);b=calc('LESS_THAN',calc('FRACT',calc('MULTIPLY',z,25)),.24)
        mask=calc('MAXIMUM',a,b)
    elif pattern=='mesh':
        xy=calc('ADD',x,y);a=calc('SINE',calc('MULTIPLY',calc('ADD',xy,z),155));b=calc('SINE',calc('MULTIPLY',calc('SUBTRACT',xy,z),155))
        mask=calc('MAXIMUM',calc('GREATER_THAN',a,.91),calc('GREATER_THAN',b,.91));col=COLORS['skin'];alt=COLORS['black']
    else:mask=0
    mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(*col,1);mix.inputs[2].default_value=(*alt,1)
    if isinstance(mask,(int,float)):mix.inputs[0].default_value=mask
    else:links.new(mask,mix.inputs[0])
    links.new(mix.outputs[0],nodes.get('Principled BSDF').inputs['Base Color']);return m

class Builder:
    def __init__(self,col,rig,slot,key,palette='default'):
        self.col=col;self.rig=rig;self.slot=slot;self.key=key;self.cfg=dict(model.ASSETS[slot][key]);self.objects=[]
        cfg=self.cfg;color=cfg.get('color','black');accent=cfg.get('accent','lilac')
        if palette in PALETTE:color,accent=PALETTE[palette]
        self.main=material(key+' • fabric',color,accent,None if cfg['builder']=='layered' else cfg.get('pattern'),surface=cfg.get('surface','cloth'))
        self.accent=material(key+' • accent',accent);self.dark=material(key+' • piping','black');self.light=material(key+' • lining','ivory');self.silver=material(key+' • hardware','silver',rough=.28,metal=.8)
    def obj(self,mesh,name,mat=None,part=None,smooth=True):
        part=part or ('skirt' if self.slot=='bottom' else 'leg' if self.slot=='shoes' else 'body')
        ob=mesh.object('Wardrobe • '+self.key+' • '+name,mat or self.main,self.col,self.rig,self.slot,self.key,part,smooth);ob['chibi_factory_v2']=True;ob['chibi_recipe_rev']=REVISION;self.objects.append(ob);return ob
    def tube(self,name,pts,r=.002,mat=None,part=None,seg=8):
        ob=self.obj(Mesh().tube(pts,r,seg),name,mat,part);ob['chibi_tube_sides']=seg;ob['chibi_tube_radius']=r;return ob
    def ring(self,name,z,rx,ry,mat=None,part=None,cx=0,cy=0,r=.002):
        return self.tube(name,[(cx+rx*cos(2*pi*j/64),cy+ry*sin(2*pi*j/64),z) for j in range(65)],r,mat,part)
    def surface(self,name,profile,mat=None,part=None,seg=64,caps=True):
        return self.obj(Mesh().loft(interpolate(profile,4),seg,caps),name,mat,part)
    def panel(self,name,pts,mat=None,part=None):
        m=Mesh();m.v=pts;m.f=[tuple(range(len(pts)))];return self.obj(m,name,mat,part,False)
    def front(self,x,z,extra=.004):
        profile=self.profile
        i=next((i for i in range(len(profile)-1) if profile[i][2]<=z<=profile[i+1][2]),0 if z<profile[0][2] else len(profile)-2)
        a,b=profile[i:i+2];t=max(0,min(1,(z-a[2])/(b[2]-a[2])));rx=a[3]*(1-t)+b[3]*t;ry=a[4]*(1-t)+b[4]*t
        return -ry*sqrt(max(.04,1-(x/rx)**2))-extra
    def print(self,kind,center=(0,1.075),size=.036):
        x0,z0=center;pts=[]
        if kind in ('heart','broken_heart'):
            for j in range(65):
                a=2*pi*j/64;x=x0+size*sin(a)**3;z=z0+size*(13*cos(a)-5*cos(2*a)-2*cos(3*a)-cos(4*a))/16;pts.append((x,self.front(x,z,.006),z))
        elif kind=='star':
            for j in range(11):a=pi/2+2*pi*j/10;r=size*(1 if j%2==0 else .44);x=x0+r*cos(a);z=z0+r*sin(a);pts.append((x,self.front(x,z,.006),z))
        elif kind=='bandage':
            for x,z in [(-1,-.30),(1,-.30),(1,.30),(-1,.30),(-1,-.30)]:
                xx=x0+size*(x*.82-z*.5);zz=z0+size*(x*.5+z*.82);pts.append((xx,self.front(xx,zz,.006),zz))
        else:
            for j in range(49):a=.6+(2*pi-1.2)*j/48;x=x0+size*cos(a);z=z0+size*sin(a);pts.append((x,self.front(x,z,.006),z))
        if kind=='moon':self.tube('crescent print',pts,.003,self.accent)
        else:
            m=Mesh();m.v=[(x0,self.front(x0,z0,.006),z0)]+pts[:-1];m.f=[(0,j+1,(j+1)%(len(pts)-1)+1) for j in range(len(pts)-1)];self.obj(m,'graphic print',self.accent,smooth=False)
        if kind=='broken_heart':self.tube('broken heart cut',[(x0-.005,self.front(x0,z0+.023,.008),z0+.023),(x0+.006,self.front(x0,z0,.008),z0),(x0-.004,self.front(x0,z0-.025,.008),z0-.025)],.002,self.dark)
        if kind=='bandage':
            for dx in (-.017,0,.017):self.tube('patch perforation',[(x0+dx,self.front(x0+dx,z0,.008),z0-.002),(x0+dx,self.front(x0+dx,z0,.008),z0+.002)],.0015,self.dark)
    def sleeves(self,mode='long',mat=None,puff=False,bell=False):
        for side in (-1,1):
            controls=[(side*.147,.005,1.155),(side*.198,.005,1.132),(side*.253,.002,1.031),(side*.291,-.010,.914),(side*.302,-.015,.865)]
            if mode=='short':controls=controls[:2]+[(side*.232,.003,1.075)]
            pts=interpolate(controls,8);rs=[]
            for i,p in enumerate(pts):
                t=i/(len(pts)-1);r=(.062+.013*sin(pi*t)-.016*t)*(.65+.35*min(1,t/.12))
                if puff:r+=.020*sin(pi*t)**2
                if bell:r+=.018*t**3
                if mode!='short':r+=.0008*sin(24*pi*t)*sin(pi*t)**2
                rs.append(r)
            self.obj(Mesh().tube(pts,rs,24,.90),'sleeve '+str(side),mat or self.main,'arm')
            if mode!='short':self.tube('cuff '+str(side),[controls[-1],(side*.303,-.016,.851)],.048 if not bell else .067,self.accent,'arm',24)
    def lace(self,z,rx,ry,part='skirt',count=32,asym=0):
        # Small looped scallops are real trim, rather than a flat colour stripe.
        for i in range(count):
            a=2*pi*i/count;pts=[]
            for j in range(9):
                t=pi*j/8;angle=a+(2*pi/count)*j/8;pts.append((rx*cos(angle),ry*sin(angle),z-.010*sin(t)+asym*sin(3*angle)))
            self.tube('scalloped lace',pts,.0017,self.accent,part,6)
    def lacing(self,z0=.98,z1=1.16,half=.040):
        for i in range(7):
            z=z0+(z1-z0)*i/6
            for side in (-1,1):self.tube('corset eyelet',[(side*half+.003*cos(2*pi*j/12),self.front(side*half,z,.007),z+.003*sin(2*pi*j/12)) for j in range(13)],.001,self.silver)
            if i<6:
                zz=z+(z1-z0)/6
                for side in (-1,1):self.tube('corset lace',[(side*half,self.front(side*half,z,.009),z),(-side*half,self.front(-side*half,zz,.009),zz)],.0018,self.accent)
    def torso(self,hem=.89,width=1,mat=None):
        self.profile=[(0,0,hem,.153*width,.110*width),(0,0,max(hem+.018,.94),.151*width,.108*width),(0,0,1.035,.176*width,.118*width),(0,0,1.14,.188*width,.110*width),(0,0,1.195,.170*width,.088*width),(0,0,1.224,.065,.056)]
        self.surface('torso',self.profile,mat,part='body')
        self.ring('collar',1.222,.067,.058,self.accent,part='body',r=.004)
    def build_top(self):
        c=self.cfg;kind=c['builder'];oversize=c.get('oversize');hem=.82 if oversize else .985 if c.get('crop') else .89
        if kind in ('coat','tunic'):hem=.78
        if kind=='layered':
            sleeve_mat=material(self.key+' • sleeve textile','ivory',c.get('accent','black'),c.get('pattern'))
            self.torso(.945,mat=self.dark if c.get('pattern')=='mesh' else sleeve_mat);self.sleeves(mat=sleeve_mat)
            self.torso(1.005 if c.get('crop') else .93,1.02)
        elif kind in ('vest','corset'):
            under=self.dark if c.get('patches') else self.light if kind=='vest' else self.dark
            self.torso(.91,mat=under);self.sleeves(mode='short' if c.get('patches') else 'long',mat=under if kind=='vest' else self.accent,puff=kind=='corset')
            self.torso(.925,1.015);self.lacing() if kind=='corset' else None
        else:
            self.torso(hem,1.06 if oversize else 1)
            self.sleeves('short' if c.get('sleeve')=='short' else 'long',puff=c.get('puff',False),bell=c.get('bell',False))
        if kind in ('shirt','cardigan','vest','blouse') or c.get('buttons'):
            for z in (.955,1.005,1.055,1.105,1.155):self.tube('button',[(0,self.front(0,z,.006),z),(0,self.front(0,z,.009),z)],.003,self.silver)
            for side in (-1,1):self.panel('point collar',[(side*.045,self.front(side*.045,1.20),1.20),(side*.095,self.front(side*.095,1.17),1.17),(side*.055,self.front(side*.055,1.13),1.13)],self.light)
        if kind in ('jacket','coat'):
            for side in (-1,1):
                self.panel('folded lapel',[(side*.045,self.front(side*.045,1.205),1.205),(side*.120,self.front(side*.120,1.16),1.16),(side*.070,self.front(side*.070,1.08),1.08)],self.accent if kind=='coat' else self.dark)
                self.tube('chest pocket',[(side*.08,self.front(side*.08,1.02,.009),1.02),(side*.15,self.front(side*.15,1.04,.009),1.04)],.002,self.silver)
            self.tube('zipper',[(.04 if c.get('asymmetric') else 0,self.front(.04 if c.get('asymmetric') else 0,z,.009),z) for z in (.925,.98,1.04,1.10,1.16)],.002,self.silver)
            if kind=='coat':
                for side in (-1,1):
                    self.panel('coat tail',[(side*.055,-.090,.91),(side*.16,-.045,.91),(side*.21,-.040,.59),(side*.06,-.13,.65 if c.get('asymmetric') and side==1 else .59)],self.main,'skirt')
            if c.get('tech'):
                self.ring('high collar',1.221,.071,.061,self.accent,part='body',r=.010)
                for z in (.975,1.125):self.tube('tech chest strap',[(-.13,self.front(-.13,z,.01),z),(.13,self.front(.13,z+.02,.01),z+.02)],.009,self.dark)
                for side in (-1,1):self.tube('neon seam',[(side*.16,self.front(side*.16,z,.008),z) for z in (.96,1.01,1.08,1.14)],.002,self.accent)
        if kind=='hoodie':
            pts=[(.105*cos(pi*j/32),.032+.083*sin(pi*j/32),1.21+.025*sin(pi*j/32)) for j in range(33)];self.tube('folded hood',pts,.025,self.main,'body',20)
            for side in (-1,1):self.tube('drawstring',[(side*.045,self.front(side*.045,z,.009),z) for z in (1.20,1.15,1.10)],.002,self.light)
            self.panel('kangaroo pocket',[(x,self.front(x,z,.006),z) for x,z in ((-.125,.87),(.125,.87),(.09,.99),(-.09,.99))],self.dark)
        if c.get('print'):self.print(c['print'],size=.042 if oversize else .035)
        if c.get('patches'):
            for side in (-1,1):
                x=side*.09;z=1.075
                self.panel('sewn patch',[(xx,self.front(xx,zz,.009),zz) for xx,zz in ((x-.025,z-.035),(x+.025,z-.035),(x+.025,z+.035),(x-.025,z+.035))],self.accent)
                previous=self.accent;self.accent=self.light;self.print('star',(x,z),.013);self.accent=previous
        if c.get('distressed'):
            for z in (.955,1.01,1.075):self.tube('distressed knit opening',[(x,self.front(x,z,.009),z+.002*sin(x*70)) for x in (-.11,-.07,-.03,.01,.05)],.0025,self.dark)
        if c.get('lace'):self.lace(max(.90,hem),.157,.114,'body',24)
        if c.get('studs'):
            for side in (-1,1):
                for z in (1.08,1.11,1.14):self.tube('metal stud',[(side*.13,self.front(side*.13,z,.008),z),(side*.13,self.front(side*.13,z,.015),z)],.003,self.silver)
    def build_skirt(self,profile=None):
        c=self.cfg;bottom=c.get('length',.60);flare=c.get('flare',.25);seg=96;rows=33;pleats=c.get('pleats',8);m=Mesh()
        for i in range(rows):
            t=i/(rows-1);z=.925-(.925-bottom)*t;shape=sin(pi*t/2)**.7 if c.get('bows') or c.get('tiers',1)>1 else t;rx=.153+(flare-.153)*shape;ry=.106+(.66*flare-.106)*shape
            for j in range(seg):
                a=2*pi*j/seg;wave=1+.025*sin(pleats*a)*t*t;zz=z+(.035*sin(3*a)*t*t if c.get('asymmetric') else 0);m.v.append((rx*cos(a)*wave,ry*sin(a)*wave,zz))
        for i in range(rows-1):
            for j in range(seg):a=i*seg+j;b=i*seg+(j+1)%seg;m.f.append((a,b,b+seg,a+seg))
        ob=self.obj(m,'skirt shell',part='skirt');sol=ob.modifiers.new('Fabric hem thickness','SOLIDIFY');sol.thickness=.0015;sol.offset=-1
        self.surface('waistband',[(0,0,.913,.155,.109),(0,0,.944,.150,.105)],self.dark,'skirt',caps=False)
        hempts=[]
        for j in range(97):
            a=2*pi*j/96;wave=1+.025*sin(pleats*a);hempts.append((flare*cos(a)*wave,.66*flare*sin(a)*wave,bottom+.004+(.035*sin(3*a) if c.get('asymmetric') else 0)))
        self.tube('hem',hempts,.002,self.accent,'skirt')
        if c.get('lace'):self.lace(bottom+.003,flare,.66*flare,asym=.035 if c.get('asymmetric') else 0)
        for k in range(1,c.get('tiers',1)):
            t=k/c['tiers'];z=.925-(.925-bottom)*t;shape=sin(pi*t/2)**.7 if c.get('bows') or c.get('tiers',1)>1 else t;rx=.153+(flare-.153)*shape;ry=.106+(.66*flare-.106)*shape
            self.lace(z,rx+.004,ry+.004,count=24)
            # Overlapping flounce bands create a tiered silhouette.
            self.surface('tier flounce',[(0,0,z+.035,rx-.003,ry-.003),(0,0,z-.020,rx+.016,ry+.012)],self.accent,'skirt',caps=False)
    def build_pants(self):
        c=self.cfg;width=c.get('width',.07);hem=c.get('length',.18)
        hip=Mesh();seg=96;rows=21;rxleg=max(width*1.17,.081);ryleg=max(rxleg*.91,.078);cx=.080
        for i in range(rows):
            t=i/(rows-1);z=.778+.162*t;blend=min(1,t/.82);blend=blend*blend*(3-2*blend)
            for j in range(seg):
                a=2*pi*j/seg;cc,ss=cos(a),sin(a);A=cc*cc/(rxleg*rxleg)+ss*ss/(ryleg*ryleg);B=2*abs(cc)*cx/(rxleg*rxleg);C=cx*cx/(rxleg*rxleg)-1
                union=(B+sqrt(max(0,B*B-4*A*C)))/(2*A)
                oval=1/sqrt((cc/(.180-.030*t))**2+(ss/(.125-.020*t))**2)
                r=union*(1-blend)+oval*blend;hip.v.append((r*cc,r*ss,z))
        for i in range(rows-1):
            for j in range(seg):a=i*seg+j;b=i*seg+(j+1)%seg;hip.f.append((a,b,b+seg,a+seg))
        hip.f.extend([tuple(reversed(range(seg))),tuple((rows-1)*seg+j for j in range(seg))]);garment=hip
        self.surface('belt',[(0,0,.913,.154,.109),(0,0,.944,.151,.107)],self.dark,'hip',caps=False)
        for side in (-1,1):
            profile=[]
            for z,center,mult,minrx,minry in ((.18,.105,.92,.051,.054),(.25,.105,1,.055,.056),(.40,.102,1,.059,.059),(.51,.097,1.04,.064,.062),(.62,.091,1.10,.071,.069),(.75,.082,1.17,.080,.077),(.81,.080,1.17,.081,.078)):
                if z<hem:continue
                rx=max(width*mult,minrx);ry=max(rx*.91,minry)
                if z<.4 and self.shoe_height>.30:rx=min(rx,.042);ry=min(ry,.045)
                profile.append((side*center,0,z,rx,ry))
            if hem>.18:profile.insert(0,(side*.091,0,hem,max(width*1.10,.080),max(width,.077)))
            garment.append(Mesh().loft(anatomy.profile(profile).tolist(),48,True))
            # A sewn outseam and angled pocket welt.
            self.tube('outseam',[(x+side*(rx+.001),y,z) for x,y,z,rx,ry in interpolate(profile,3)],.0009,self.accent,'leg',6)
            self.tube('pocket welt',[(side*.045,-.112,.916),(side*.095,-.105,.88),(side*.145,-.075,.86)],.0014,self.accent,'hip')
            if c.get('pockets'):
                x=side*(.102+width*.88)
                self.panel('cargo pocket',[(x,-.048,.47),(x,-.048,.60),(x,.045,.60),(x,.045,.47)],self.dark,'leg')
                self.tube('pocket flap',[(x,-.049,.58),(x,0,.58),(x,.046,.58)],.004,self.accent,'leg')
            if c.get('straps'):
                for z in (.45,.66):self.ring('leg strap',z,width*1.13,width*1.03,self.dark,'leg',cx=side*(.10 if z<.5 else .088),r=.008)
                self.tube('hanging strap',[(side*.17,-.04,.84),(side*.18,-.07,.66),(side*.16,-.06,.47)],.006,self.dark,'leg')
            if c.get('ripped'):
                # Skin-coloured inset patches depict torn denim without exposed gaps.
                x=side*.098;z=.50;ry=width*.95
                self.panel('denim tear inset',[(x-.034,-ry-.003,z-.014),(x+.034,-ry-.003,z-.014),(x+.034,-ry-.003,z+.014),(x-.034,-ry-.003,z+.014)],material(self.key+' • inset skin','skin'),'leg')
                for dz in (-.014,0,.014):self.tube('tear threads',[(x-.036,-ry-.006,z+dz),(x+.036,-ry-.006,z+dz+.002)],.001,self.light,'leg')
            if c.get('patches'):
                x=side*.097;z=.43 if side<0 else .62;ry=width*1.05
                self.panel('denim sewn patch',[(x-.026,-ry-.004,z-.035),(x+.026,-ry-.004,z-.035),(x+.026,-ry-.004,z+.035),(x-.026,-ry-.004,z+.035)],self.accent,'leg')
        ob=self.obj(garment,'continuous trousers',part='pants');clothing.union_surface(ob);ob['chibi_continuous_pants']=True
        self.tube('fly stitching',[(.007,-.123,z) for z in (.79,.83,.87,.91)],.001,self.accent,'hip')
        fitting.conform_trims(ob,self.objects,('outseam','pocket welt','fly stitching'))
        if c.get('chains'):self.chain(.90,.16)
    def build_dress(self):
        c=self.cfg;self.torso(.91);self.sleeves(puff=c.get('puff',False),bell=c.get('bell',False))
        if c.get('corset'):self.lacing(.96,1.15)
        if c.get('collar'):self.surface('raised collar',[(0,0,1.205,.074,.064),(0,0,1.245,.075,.064)],self.accent,'neck',caps=False)
        if c.get('print'):self.print(c['print'])
        if c.get('buttons'):
            for z in (.96,1.01,1.06,1.11,1.16):self.tube('dress button',[(0,self.front(0,z),z),(0,self.front(0,z,.008),z)],.003,self.silver)
        self.build_skirt()
        if c.get('bows'):
            for z in (.945,1.19):self.bow((0,self.front(0,z,.012),z),.031,'body')
    def bow(self,c,size=.04,part='head'):
        x,y,z=c
        for side in (-1,1):
            self.panel('bow loop',[(x,y-.003,z),(x+side*size,y,z+size*.60),(x+side*size,y,z-size*.60)],self.accent,part)
            self.panel('bow ribbon',[(x+side*.007,y,z),(x+side*size*.45,y,z-size*1.20),(x+side*size*.15,y,z-size*1.05)],self.accent,part)
        self.tube('bow knot',[(x,y-.005,z-.006),(x,y-.005,z+.006)],.007,self.dark,part)
    def build_shoe(self):
        c=self.cfg;plat=c['platform'];height=c['height'];sole=material(self.key+' • sole','charcoal',rough=.8,surface='rubber')
        for side in (-1,1):
            x=side*.105
            self.surface('platform sole',[(x,-.049,.018,.064,.111),(x,-.049,.027,.075,.125),(x,-.049,plat,.075,.125),(x,-.049,plat+.008,.072,.122)],sole,'leg',caps=True)
            toeheight=plat+.048
            rings=[(x,-.049,plat+.004,.072,.121),(x,-.047,plat+.022,.074,.122),(x,-.040,toeheight,.069,.109),(x,-.018,toeheight+.035,.058,.073),(x,0,max(toeheight+.060,height-.03),.055,.056),(x,0,max(toeheight+.065,height),.055,.055)]
            if c.get('strap') or c.get('buckle'):
                rings=[(x,-.049,plat+.004,.072,.121),(x,-.047,plat+.022,.074,.122),(x,-.040,toeheight,.069,.109),(x,-.018,toeheight+.018,.056,.073),(x,0,toeheight+.024,.046,.048)]
            self.surface('shoe upper',rings,part='leg',caps=not (c.get('strap') or c.get('buckle')))
            self.ring('sole piping',plat-.008,.075,.125,self.accent,'leg',cx=x,cy=-.049,r=.0015)
            if c.get('buckles'):
                for z in (height-.045,height-.095):
                    self.ring('boot strap',z,.059,.060,self.dark,'leg',cx=x,r=.006)
                    self.tube('strap buckle',[(x+side*.055,-.022,z-.010),(x+side*.055,-.022,z+.010),(x+side*.055,.005,z+.010),(x+side*.055,.005,z-.010),(x+side*.055,-.022,z-.010)],.0018,self.silver,'leg')
            if c.get('strap'):
                self.tube('Mary Jane strap',[(x-.056,-.018,toeheight+.019),(x,-.05,toeheight+.032),(x+.056,-.018,toeheight+.019)],.006,self.dark,'leg')
            if c.get('buckle'):self.tube('loafer bar',[(x-.037,-.100,toeheight+.009),(x+.037,-.100,toeheight+.009)],.004,self.silver,'leg')
            if c.get('laces'):
                for i in range(5):
                    z=toeheight+.020+(max(toeheight+.035,height-.025)-toeheight-.020)*i/4;yy=-.066 if z>toeheight+.05 else -.092
                    self.tube('shoe cross lace',[(x-.022,yy,z),(x+.022,yy+.004,z+.010)],.0018,self.accent,'leg')
            if c.get('tech'):
                for z in (height-.02,height-.07):self.ring('neon band',z,.059,.060,self.accent,'leg',cx=x,r=.003)
    def chain(self,z=.90,width=.16):
        for i in range(16):
            t=i/15;x=.02+width*t;zz=z-.05*sin(pi*t);yy=-.13+.04*t
            self.tube('waist chain link',[(x+.004*cos(2*pi*j/12),yy,zz+.006*sin(2*pi*j/12)) for j in range(13)],.0011,self.silver,'hip',6)
    def build_accessory(self):
        key=self.key;self.profile=[(0,0,.90,.16,.12),(0,0,1.04,.185,.14),(0,0,1.14,.195,.13),(0,0,1.22,.07,.06)]
        if key in ('cross','moon','cameo','crystal'):
            self.tube('necklace',[(x,self.front(x,z,.014),z) for x,z in interpolate([(-.060,1.198),(-.045,1.16),(0,1.108),(.045,1.16),(.060,1.198)],12)],.0018,self.silver,'body')
            x=0;z=1.10;y=self.front(x,z,.018)
            if key=='cross':
                self.tube('cross vertical',[(0,y,z-.026),(0,y,z+.025)],.004,self.silver);self.tube('cross horizontal',[(-.017,y,z+.006),(.017,y,z+.006)],.004,self.silver)
            elif key=='moon':self.tube('moon pendant',[(.020*cos(.6+5.1*j/32),y,z+.020*sin(.6+5.1*j/32)) for j in range(33)],.003,self.silver)
            elif key=='cameo':
                self.tube('cameo frame',[(.018*cos(2*pi*j/32),y,z+.025*sin(2*pi*j/32)) for j in range(33)],.003,self.silver)
                self.panel('cameo jewel',[(-.012,y+.001,z),(0,y-.004,z+.020),(.012,y+.001,z),(0,y-.004,z-.020)],material('Cameo • burgundy','burgundy'))
            else:self.panel('faceted crystal',[(0,y-.004,z+.023),(-.012,y,z+.008),(-.009,y,z-.015),(0,y-.004,z-.030),(.009,y,z-.015),(.012,y,z+.008)],material('Crystal • amethyst','lilac'))
        elif key in ('wristbands','spikes','bracelets'):
            for side in (-1,1):
                for k in range(3 if key=='bracelets' else 1):
                    zz=.875+k*.012;self.tube('wrist band',[(side*.300,-.014,zz),(side*.302,-.015,zz-.009)],.051,self.accent if key=='bracelets' else self.dark,'arm',24)
                if key=='spikes':
                    for j in range(6):
                        a=2*pi*j/6;x=side*.30+.052*cos(a);y=-.015+.047*sin(a)
                        self.tube('metal spike',[(x,y,.88),(x+.009*cos(a),y+.009*sin(a),.884)],.003,self.silver,'arm')
        elif key=='glasses':
            from .facial import face_y
            for side in (-1,1):
                pts=[]
                for j in range(65):a=2*pi*j/64;x=side*.128+.082*cos(a);z=1.582+.062*sin(a);pts.append((x,float(face_y(x,z))-.020,z))
                self.tube('round glasses frame',pts,.003,self.silver,'head')
            self.tube('glasses bridge',[(-.045,-.261,1.588),(0,-.275,1.598),(.045,-.261,1.588)],.0025,self.silver,'head')
        elif key=='goggles':
            for side in (-1,1):
                self.tube('goggle rim',[(side*.092+.063*cos(2*pi*j/48),-.290,1.775+.040*sin(2*pi*j/48)) for j in range(49)],.009,self.dark,'head')
                self.panel('goggle lens',[(side*.092+.052*cos(2*pi*j/32),-.291,1.775+.030*sin(2*pi*j/32)) for j in range(32)],material('Goggles • neon glass','acid',rough=.22),'head')
            self.tube('goggle bridge',[(-.03,-.29,1.775),(.03,-.29,1.775)],.006,self.silver,'head')
        elif key=='mask':
            from .facial import face_y
            vs=[];faces=[]
            for i in range(9):
                z=1.385+.105*i/8
                for j in range(25):x=-.125+.25*j/24;vs.append((x,float(face_y(x,z))-.012,z))
            for i in range(8):
                for j in range(24):a=i*25+j;faces.append((a,a+1,a+26,a+25))
            m=Mesh();m.v=vs;m.f=faces;self.obj(m,'face mask',self.dark,'head')
            for side in (-1,1):self.tube('mask seam',[(side*.095,float(face_y(side*.095,z))-.015,z) for z in (1.39,1.42,1.46,1.485)],.0015,self.accent,'head')
        elif key=='bow':self.bow((-.235,-.221,1.79),.055)
        elif key=='waistchain':self.chain()
        elif key=='legstraps':
            for z in (.49,.61):self.ring('thigh harness',z,.066,.064,self.dark,'leg',cx=.095,r=.005)
            self.tube('leg harness buckle',[(.158,-.020,.49),(.158,-.020,.61)],.003,self.silver,'leg')
        elif key=='bag':
            self.tube('crossbody strap',[(x,self.front(x,z,.030),z) for x,z in ((-.13,1.19),(-.06,1.09),(.02,1.00),(.11,.91),(.18,.86))],.008,self.dark)
            self.surface('satchel',[(.185,-.105,.78,.065,.025),(.185,-.105,.88,.065,.025)],self.main,'hip',caps=True)
            self.tube('satchel flap',[(.125,-.134,.86),(.185,-.137,.83),(.245,-.134,.86)],.003,self.accent,'hip')
        elif key=='safety_pin':
            self.tube('safety pin',[(x,self.front(x,z,.012),z) for x,z in ((.06,1.13),(.08,1.09),(.095,1.10),(.075,1.14),(.06,1.13))],.0018,self.silver)
    def finish(self):
        if self.slot=='accessories':
            for ob in self.objects:ob['chibi_accessory']=self.key;del ob['chibi_slot'];del ob['chibi_option']
        used={m for ob in self.objects for m in ob.data.materials}
        for m in (self.main,self.accent,self.dark,self.light,self.silver):
            if m not in used and m.users==0:bpy.data.materials.remove(m)
        return self.objects

def ensure_base(col,rig):
    if rig.get('chibi_underbody_v2') and rig.get('chibi_underbody_rev')==REVISION:return []
    skin=material('Adult chibi • underlying skin','skin');created=[]
    def obj(mesh,name,part):
        ob=mesh.object(name,skin,col,rig,'base','base',part);del ob['chibi_slot'];del ob['chibi_option'];ob['chibi_underbody']=True;ob['chibi_underbody_rev']=REVISION;created.append(ob);return ob
    obj(Mesh().loft(interpolate([(0,0,.89,.121,.082),(0,0,.94,.119,.079),(0,0,1.04,.144,.095),(0,0,1.15,.168,.089),(0,0,1.20,.147,.075),(0,0,1.225,.056,.048)],4),64,True),'Underlying torso','body')
    for side in (-1,1):
        pts=interpolate([(side*.162,.005,1.165),(side*.211,.005,1.130),(side*.254,.002,1.030),(side*.291,-.01,.915),(side*.302,-.015,.858)],8)
        obj(Mesh().tube(pts,[.038-.011*i/(len(pts)-1) for i in range(len(pts))],24,.88),'Underlying arm '+str(side),'arm')
        ob=obj(Mesh().loft(anatomy.profile([(side*x,y,z,rx,ry) for x,y,z,rx,ry in anatomy.LEG_PROFILE]).tolist(),48,True),'Legwear base '+str(side),'leg');ob['chibi_legwear_base']=True
    for ob in col.objects:
        if ob.get('chibi_asset','').startswith('Matte tights'):ob['chibi_replaced_legs']=True
    rig['chibi_underbody_v2']=True;rig['chibi_underbody_rev']=REVISION
    if 'chibi_legwear_kind' in rig:del rig['chibi_legwear_kind']
    return created

def ensure(col,rig,spec):
    created=ensure_base(col,rig);outfit=spec['outfit'];shoeheight=model.ASSETS['shoes'][outfit['shoes']].get('height',.34 if outfit['shoes']=='boots' else .22);fit='tucked' if shoeheight>.30 else 'loose'
    existing={(o.get('chibi_slot'),o.get('chibi_option'),o.get('chibi_palette','default'),o.get('chibi_fit','any'),o.get('chibi_recipe_rev')) for o in col.objects}
    chosen=[('dress',outfit['dress'])] if outfit['dress']!='none' else [('top',outfit['top']),('bottom',outfit['bottom'])]
    chosen.append(('shoes',outfit['shoes']))
    for slot,key in chosen:
        cfg=model.ASSETS[slot][key];palette=outfit['palette'];assetfit=fit if cfg['builder']=='pants' else 'any'
        if cfg['builder'] in ('legacy','none') or (slot,key,palette,assetfit,REVISION) in existing:continue
        b=Builder(col,rig,slot,key,palette);b.shoe_height=shoeheight
        if slot=='top':b.build_top()
        elif slot=='bottom':b.build_pants() if cfg['builder']=='pants' else b.build_skirt()
        elif slot=='dress':b.build_dress()
        else:b.build_shoe()
        for ob in b.finish():ob['chibi_palette']=palette;ob['chibi_fit']=assetfit;created.append(ob)
    existing_acc={o.get('chibi_accessory') for o in col.objects if not o.get('chibi_factory_v2') or o.get('chibi_recipe_rev')==REVISION}
    for key in spec['accessories']:
        if key in ('choker','earring','hairclip') or key in existing_acc:continue
        b=Builder(col,rig,'accessories',key);b.build_accessory();created.extend(b.finish())
    return created

def tag_original(objects):
    clothing.tag_original(objects)
    for ob in objects:
        name=ob.get('chibi_asset','')
        if name.startswith('Waist chain'):ob['chibi_retired_detail']=True
        if name.startswith(('Slim charcoal choker','Choker silver')):ob['chibi_accessory']='choker'
        elif name.startswith(('Silver hoop earring','Earring orchid')):ob['chibi_accessory']='earring'
        elif name.startswith(('Crescent hair clip','Lavender hair bar')):ob['chibi_accessory']='hairclip'

def visibility(objects,spec):
    outfit=spec['outfit'];dress=outfit['dress']!='none';palette=outfit['palette'];shoeheight=model.ASSETS['shoes'][outfit['shoes']].get('height',.34 if outfit['shoes']=='boots' else .22);fit='tucked' if shoeheight>.30 else 'loose'
    for ob in objects:
        slot=ob.get('chibi_slot');hidden=False
        if not (slot or ob.get('chibi_accessory') or ob.get('chibi_replaced_legs') or ob.get('chibi_retired_detail') or ob.get('chibi_underbody')):
            continue
        if slot:
            hidden=(dress and slot in ('top','bottom')) or (not dress and slot=='dress') or (outfit.get(slot)!=ob.get('chibi_option'))
            if ob.get('chibi_option')=='shorts' and not ob.get('chibi_factory_v2'):hidden=True
            if ob.get('chibi_factory_v2'):
                hidden=hidden or ob.get('chibi_palette','default')!=palette or ob.get('chibi_recipe_rev')!=REVISION
                if ob.get('chibi_fit','any')!='any':hidden=hidden or ob['chibi_fit']!=fit
        if ob.get('chibi_accessory'):hidden=ob['chibi_accessory'] not in spec['accessories'] or (ob.get('chibi_factory_v2') and ob.get('chibi_recipe_rev')!=REVISION)
        if ob.get('chibi_replaced_legs') or ob.get('chibi_retired_detail'):hidden=True
        if ob.get('chibi_underbody') and ob.get('chibi_underbody_rev')!=REVISION:hidden=True
        ob.hide_render=bool(hidden);ob.hide_viewport=bool(hidden)

def legwear(objects,rig,kind):
    if rig.get('chibi_legwear_kind')==kind:return
    if kind=='fishnet':m=material('Legwear • diamond fishnet','skin','black','mesh')
    elif kind=='striped':m=material('Legwear • striped stockings','black','lilac','stripes')
    else:m=material('Legwear • '+kind,'skin' if kind in ('bare','stockings') else 'black')
    if kind in ('stockings','striped'):
        # Below the knee use fabric; above the knee keep the skin colour.
        nodes=m.node_tree.nodes;links=m.node_tree.links;bs=nodes.get('Principled BSDF')
        tex=nodes.new('ShaderNodeTexCoord');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(tex.outputs['Object'],xyz.inputs[0]);mask=nodes.new('ShaderNodeMath');mask.operation='LESS_THAN';mask.inputs[1].default_value=.57;links.new(xyz.outputs['Z'],mask.inputs[0]);mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(*COLORS['skin'],1);mix.inputs[2].default_value=(*COLORS['black'],1)
        old=next((l.from_socket for l in links if l.to_node==bs and l.to_socket==bs.inputs['Base Color']),None)
        if old:links.new(old,mix.inputs[2])
        links.new(mask.outputs[0],mix.inputs[0]);links.new(mix.outputs[0],bs.inputs['Base Color'])
    oldmats=set()
    for ob in objects:
        if ob.get('chibi_legwear_base') and ob.get('chibi_underbody_rev')==REVISION:
            oldmats.update(ob.data.materials);ob.data.materials.clear();ob.data.materials.append(m)
    for old in oldmats:
        if old and old.users==0:bpy.data.materials.remove(old)
    rig['chibi_legwear_kind']=kind
