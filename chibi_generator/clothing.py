"""Neutral modular garments. Each mesh shares the character's deformation field."""
import math
import bpy,bmesh
from mathutils import Vector
from math import pi,sin,cos,sqrt

class Mesh:
    def __init__(self):self.v=[];self.f=[]
    def append(self,other):
        offset=len(self.v);self.v.extend(other.v);self.f.extend(tuple(offset+i for i in face) for face in other.f);return self
    def loft(self,rings,seg=64,caps=False,power=2):
        offset=len(self.v)
        for x,y,z,rx,ry in rings:
            for j in range(seg):
                a=2*pi*j/seg;c,s=cos(a),sin(a)
                self.v.append((x+rx*math.copysign(abs(c)**(2/power),c),y+ry*math.copysign(abs(s)**(2/power),s),z))
        for i in range(len(rings)-1):
            for j in range(seg):
                a=offset+i*seg+j;b=offset+i*seg+(j+1)%seg;self.f.append((a,b,b+seg,a+seg))
        if caps:self.f.extend([tuple(offset+j for j in reversed(range(seg))),tuple(offset+(len(rings)-1)*seg+j for j in range(seg))])
        return self
    def tube(self,points,radius=.002,seg=10,flatten=1):
        points=[Vector(p) for p in points];offset=len(self.v);last=None
        for i,p in enumerate(points):
            tangent=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
            axis=Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
            u=tangent.cross(axis).normalized() if last is None else (last-tangent*last.dot(tangent)).normalized();last=u
            w=tangent.cross(u).normalized();r=radius[i] if isinstance(radius,list) else radius
            for j in range(seg):a=2*pi*j/seg;self.v.append(tuple(p+r*(u*cos(a)+w*sin(a)*flatten)))
        for i in range(len(points)-1):
            for j in range(seg):
                a=offset+i*seg+j;b=offset+i*seg+(j+1)%seg;self.f.append((a,b,b+seg,a+seg))
        self.f.extend([tuple(offset+j for j in reversed(range(seg))),tuple(offset+(len(points)-1)*seg+j for j in range(seg))]);return self
    def object(self,name,material,col,rig,slot,option,part,smooth=True):
        me=bpy.data.meshes.new(name);me.from_pydata(self.v,[],self.f);me.update()
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
        ob=bpy.data.objects.new(name,me);col.objects.link(ob);me.materials.append(material)
        for p in me.polygons:p.use_smooth=smooth
        ob.parent=rig;ob['chibi_asset']=name;ob['chibi_part']=part;ob['chibi_section']='04 Outfit';ob['chibi_slot']=slot;ob['chibi_option']=option
        return ob

def union_surface(ob,voxel=.003,iterations=3):
    """Bake overlapping closed volumes into a single editable outer surface."""
    old=bpy.context.view_layer.objects.active;bpy.context.view_layer.objects.active=ob
    rem=ob.modifiers.new('Joined garment surface','REMESH');rem.mode='VOXEL';rem.voxel_size=voxel;rem.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=rem.name)
    sm=ob.modifiers.new('Soft sewn transition','SMOOTH');sm.factor=.55;sm.iterations=iterations
    bpy.ops.object.modifier_apply(modifier=sm.name);bpy.context.view_layer.objects.active=old
    for p in ob.data.polygons:p.use_smooth=True

def interpolate(profile,steps=4):
    rings=[]
    for a,b in zip(profile,profile[1:]):
        for i in range(steps):t=i/steps;rings.append(tuple(x*(1-t)+y*t for x,y in zip(a,b)))
    return rings+[profile[-1]]

def fabric(name,color,rough=None,metal=0,surface='cloth'):
    from . import surfaces
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal
    surfaces.configure(m,'metal' if metal else surface,rough)
    return m

def create(col,rig):
    """Create only neutral geometry; binding and morph keys are managed by scene.py."""
    created=[]
    dark=fabric('Wardrobe • washed charcoal',(.032,.030,.046));lilac=fabric('Wardrobe • lilac fleece',(.31,.16,.46));light=fabric('Wardrobe • oat knit',(.68,.60,.52),surface='knit');stripe=fabric('Wardrobe • mulberry stripe',(.20,.055,.26),surface='knit')
    denim=fabric('Wardrobe • black denim',(.018,.025,.037),surface='denim');seam=fabric('Wardrobe • grey stitch',(.15,.16,.19));rubber=fabric('Wardrobe • ivory rubber',(.54,.51,.58),.72,surface='rubber');silver=fabric('Wardrobe • silver',(.55,.59,.66),.28,.8)
    # All sweater pieces use the same local Z stripe pattern, including sleeves.
    nodes=light.node_tree.nodes;links=light.node_tree.links
    coords=nodes.new('ShaderNodeTexCoord');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(coords.outputs['Object'],xyz.inputs[0])
    mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=1/.068;links.new(xyz.outputs['Z'],mul.inputs[0])
    phase=nodes.new('ShaderNodeMath');phase.operation='ADD';phase.inputs[1].default_value=-.93/.068;links.new(mul.outputs[0],phase.inputs[0])
    fract=nodes.new('ShaderNodeMath');fract.operation='FRACT';links.new(phase.outputs[0],fract.inputs[0])
    band=nodes.new('ShaderNodeMath');band.operation='LESS_THAN';band.inputs[1].default_value=.5;links.new(fract.outputs[0],band.inputs[0])
    mix=nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.68,.60,.52,1);mix.inputs[2].default_value=(.20,.055,.26,1);links.new(band.outputs[0],mix.inputs[0]);links.new(mix.outputs[0],nodes.get('Principled BSDF').inputs['Base Color'])
    def obj(mesh,name,mat,slot,option,part='body',smooth=True):
        ob=mesh.object('Wear • '+name,mat,col,rig,slot,option,part,smooth);created.append(ob);return ob
    def tube(name,points,r,mat,slot,option,part='body',seg=10):return obj(Mesh().tube(points,r,seg),name,mat,slot,option,part)
    def ring(name,z,rx,ry,mat,slot,option,part='body',cx=0,cy=0,r=.002):
        return tube(name,[(cx+rx*cos(2*pi*j/64),cy+ry*sin(2*pi*j/64),z) for j in range(65)],r,mat,slot,option,part)
    def torso(name,profile,mat,option):return obj(Mesh().loft(interpolate([(0,0,z,rx,ry) for z,rx,ry in profile]),64,True),name,mat,'top',option)
    for option in ('hoodie','sweater'):
        hood=option=='hoodie';mat=lilac if hood else light
        profile=[(.875 if hood else .90,.163,.119),(.895 if hood else .92,.171,.123),(1.00,.185,.132),(1.10,.192,.128),(1.17,.193,.111),(1.20,.158,.088),(1.224,.064,.055)]
        ob=torso(option+' torso',profile,mat,option)
        # Ribbed lower band, collar and long relaxed sleeves.
        z=.878 if hood else .902
        obj(Mesh().loft([(0,0,z,.164,.120),(0,0,z+.024,.169,.123)],64),option+' ribbed hem',dark if hood else stripe,'top',option)
        ring(option+' neckline',1.222,.066,.057,dark if hood else stripe,'top',option,r=.007)
        for side in (-1,1):
            controls=[(side*.150,.005,1.155),(side*.198,.005,1.132),(side*.253,.002,1.031),(side*.291,-.010,.914),(side*.302,-.015,.868)]
            pts=interpolate(controls,8);radii=[((.070 if hood else .065)+.012*sin(pi*i/(len(pts)-1))-.018*i/(len(pts)-1))*(.65+.35*min(1,i/(len(pts)-1)/.12)) for i in range(len(pts))]
            sleeve=obj(Mesh().tube(pts,radii,24,.91),option+' sleeve '+str(side),mat,'top',option,'arm')
            obj(Mesh().tube([(side*.298,-.013,.891),(side*.303,-.015,.859)],.049,32,.91),option+' cuff '+str(side),dark if hood else stripe,'top',option,'arm')
            for j in range(12):
                a=2*pi*j/12
                tube(option+' cuff rib',[(side*.298+.049*cos(a),-.013+.044*sin(a),.887),(side*.303+.049*cos(a),-.015+.044*sin(a),.862)],.0008,seam,'top',option,'arm',6)
        if hood:
            # Folded hood stays below the bob, with a visible padded rim at the neck.
            pts=[(.106*cos(pi*j/40),.035+.082*sin(pi*j/40),1.207+.026*sin(pi*j/40)) for j in range(41)]
            obj(Mesh().tube(pts,.025,20,.72),'hood fold',lilac,'top',option)
            tube('hood seam',[(p[0],p[1]+.018,p[2]+.005) for p in pts],.0014,dark,'top',option)
            for side in (-1,1):
                pts=[(side*.043,-.060,1.205),(side*.047,-.106,1.157),(side*.052,-.129,1.095)]
                tube('hood cord '+str(side),interpolate(pts,10),.0025,light,'top',option)
                tube('hood cord tip '+str(side),[(side*.052,-.129,1.095),(side*.052,-.129,1.082)],.0032,silver,'top',option)
            # Kangaroo pocket, lying on the neutral garment surface.
            vs=[];fs=[];rows=9;cols=33
            for i in range(rows):
                t=i/(rows-1);zz=.920+.118*t;half=.126-.040*t
                for j in range(cols):
                    xx=half*(2*j/(cols-1)-1);rx=.178+.012*t;ry=.129
                    yy=-ry*sqrt(max(.1,1-(xx/rx)**2))-.004
                    vs.append((xx,yy,zz))
            for i in range(rows-1):
                for j in range(cols-1):a=i*cols+j;fs.append((a,a+1,a+1+cols,a+cols))
            pocket=Mesh();pocket.v=vs;pocket.f=fs;obj(pocket,'kangaroo pocket',dark,'top',option)
            for side in (-1,1):
                pts=[]
                for i in range(17):t=i/16;zz=.928+.104*t;xx=side*(.126-.040*t);yy=-.129*sqrt(max(.1,1-(xx/(.178+.012*t))**2))-.006;pts.append((xx,yy,zz))
                tube('pocket opening '+str(side),pts,.0022,light,'top',option)
        else:
            # Small silver crescent on the sweater chest.
            pts=[(.060+.016*cos(.65+5.0*j/32),-.128,1.151+.016*sin(.65+5.0*j/32)) for j in range(33)]
            tube('sweater crescent pin',pts,.0022,silver,'top',option)
    # A flowing A-line skirt, with broad soft folds and a double contrast hem.
    skater=Mesh();seg=96;rows=29
    for i in range(rows):
        t=i/(rows-1);zz=.923-.315*t
        for j in range(seg):
            a=2*pi*j/seg;fold=1+.038*sin(8*a)*t*t
            skater.v.append(((.151+.096*t)*cos(a)*fold,(.104+.068*t)*sin(a)*fold,zz))
    for i in range(rows-1):
        for j in range(seg):a=i*seg+j;b=i*seg+(j+1)%seg;skater.f.append((a,b,b+seg,a+seg))
    obj(skater,'A-line skirt',dark,'bottom','skater','skirt')
    for zz,t in [(.612,.988),(.628,.937)]:
        pts=[]
        for j in range(97):a=2*pi*j/96;fold=1+.038*sin(8*a)*t*t;pts.append(((.151+.096*t)*cos(a)*fold,(.104+.068*t)*sin(a)*fold,zz))
        tube('A-line double hem',pts,.0022,lilac,'bottom','skater','skirt')
    obj(Mesh().loft([(0,0,.909,.153,.106),(0,0,.941,.149,.104)],64),'A-line waistband',denim,'bottom','skater','skirt')
    # High-waisted denim shorts: a joined hip section and two separate leg openings.
    obj(Mesh().loft(interpolate([(0,0,.765,.165,.110),(0,0,.815,.170,.117),(0,0,.89,.156,.108),(0,0,.938,.147,.101)]),64,False),'shorts hip panel',denim,'bottom','shorts','hip')
    for side in (-1,1):
        obj(Mesh().loft(interpolate([(side*.091,0,.625,.080,.077),(side*.088,0,.65,.084,.081),(side*.084,0,.74,.090,.090),(side*.080,0,.805,.091,.096)]),48,False),'shorts leg '+str(side),denim,'bottom','shorts','leg')
        obj(Mesh().loft([(side*.091,0,.623,.083,.080),(side*.090,0,.650,.086,.084)],48),'shorts turned cuff '+str(side),dark,'bottom','shorts','leg')
        for j in (-1,1):
            pts=[]
            for k in range(25):a=(0 if j==1 else pi)+pi*k/24;pts.append((side*.091+.084*cos(a),.081*sin(a),.631))
            tube('shorts cuff stitch',pts,.0009,seam,'bottom','shorts','leg',6)
        # Angled pocket welt and two metal rivets.
        pts=[(side*.047,-.105,.912),(side*.090,-.100,.879),(side*.140,-.072,.856)]
        tube('denim pocket welt',interpolate(pts,10),.0016,seam,'bottom','shorts','hip')
        for xx,yy,zz in (pts[0],pts[-1]):
            tube('denim rivet',[(xx,yy-.002,zz-.002),(xx,yy-.002,zz+.002)],.003,silver,'bottom','shorts','hip')
    obj(Mesh().loft([(0,0,.912,.150,.105),(0,0,.944,.148,.103)],64),'shorts waistband',dark,'bottom','shorts','hip')
    tube('shorts fly seam',[(.006,-.113,z) for z in (.785,.81,.84,.87,.908)],.0011,seam,'bottom','shorts','hip',6)
    tube('shorts button',[(0,-.109,.925),(0,-.112,.925)],.005,silver,'bottom','shorts','hip')
    # Low platform sneakers: different silhouette, broad toe, toe cap and laces.
    for side in (-1,1):
        cx=side*.105
        obj(Mesh().loft(interpolate([(cx,-.049,.018,.064,.111),(cx,-.049,.025,.074,.123),(cx,-.049,.068,.075,.124),(cx,-.049,.079,.071,.120)]),64,True,3),'sneaker platform '+str(side),rubber,'shoes','sneakers','leg')
        obj(Mesh().loft(interpolate([(cx,-.049,.076,.071,.119),(cx,-.048,.10,.073,.118),(cx,-.040,.137,.069,.109),(cx,-.020,.171,.059,.081),(cx,0,.202,.054,.058),(cx,0,.220,.052,.054)]),64,True,2.7),'sneaker canvas '+str(side),dark,'shoes','sneakers','leg')
        ring('sneaker collar',.218,.053,.055,lilac,'shoes','sneakers','leg',cx=cx,r=.004)
        ring('sneaker sole line',.056,.075,.125,denim,'shoes','sneakers','leg',cx=cx,cy=-.049,r=.0012)
        # Toe-cap patch is a real surface on the toe-facing half of the shoe.
        cap=Mesh();ss=32
        for zz,rx,ry,cy in ((.079,.074,.122,-.049),(.105,.074,.120,-.047),(.132,.072,.114,-.042)):
            for j in range(ss+1):a=pi+.18+(pi-.36)*j/ss;cc,ssn=cos(a),sin(a);cap.v.append((cx+rx*math.copysign(abs(cc)**(2/2.7),cc),cy+ry*math.copysign(abs(ssn)**(2/2.7),ssn)-.002,zz))
        for i in range(2):
            for j in range(ss):a=i*(ss+1)+j;cap.f.append((a,a+1,a+ss+2,a+ss+1))
        obj(cap,'sneaker toe cap '+str(side),rubber,'shoes','sneakers','leg')
        for i in range(4):
            zz=.143+i*.017;yy=-.129+i*.020
            for direction in (-1,1):
                xx=cx+direction*.023
                tube('sneaker eyelet',[(xx+.003*cos(2*pi*j/16),yy,zz+.003*sin(2*pi*j/16)) for j in range(17)],.0011,silver,'shoes','sneakers','leg',6)
            if i<3:
                for direction in (-1,1):tube('sneaker cross lace',[(cx+direction*.022,yy-.003,zz),(cx-direction*.022,yy+.017,zz+.017)],.0019,lilac,'shoes','sneakers','leg')
        tube('sneaker side stripe',[(cx+side*.071,-.086,.104),(cx+side*.066,-.025,.145),(cx+side*.056,.022,.174)],.004,lilac,'shoes','sneakers','leg')
    return created

TOP_PREFIXES=('Orchid knit top','Fine knit rib','Knit neckline','Cropped charcoal jacket','Folded lapel','Front zipper','Angled pocket','Soft jacket sleeve','Ribbed cuff','Sleeve accent')
SHOE_PREFIXES=('Platform sole','Combat boot','Rolled boot','Sole groove','Tread block','Steel boot','Crossed lilac','Boot pull','Toe cap')

def tag_original(objects):
    for ob in objects:
        if ob.get('chibi_slot'):continue
        name=ob.get('chibi_asset','')
        if name.startswith(TOP_PREFIXES):ob['chibi_slot']='top';ob['chibi_option']='classic'
        elif ob.get('chibi_part')=='skirt':ob['chibi_slot']='bottom';ob['chibi_option']='pleated'
        elif name.startswith(SHOE_PREFIXES):ob['chibi_slot']='shoes';ob['chibi_option']='boots'

def visibility(objects,outfit):
    for ob in objects:
        slot=ob.get('chibi_slot')
        if slot:
            hidden=outfit[slot]!=ob['chibi_option'];ob.hide_render=hidden;ob.hide_viewport=hidden
