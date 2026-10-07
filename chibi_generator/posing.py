"""Deterministic standing poses and independent, articulated hand gestures."""
import math
import bpy
from mathutils import Vector,Matrix,Quaternion
from . import model
from .deformation import deform

def orient(rig,name,y,z):
    pb=rig.pose.bones[name];y=Vector(y).normalized();z=Vector(z);z-=y*z.dot(y)
    if z.length<.001:z=y.cross(Vector((1,0,0)))
    z.normalize();x=y.cross(z).normalized();z=x.cross(y).normalized();desired=Matrix((x,y,z)).transposed()
    parent=pb.parent.matrix.to_3x3() if pb.parent else Matrix.Identity(3)
    rest=(pb.parent.bone.matrix_local.inverted()@pb.bone.matrix_local).to_3x3() if pb.parent else pb.bone.matrix_local.to_3x3()
    pb.rotation_mode='QUATERNION';pb.rotation_quaternion=((parent@rest).inverted()@desired).to_quaternion()
    bpy.context.view_layer.update()

def solve_arm(rig,side,target,pole,direction=None,palm=None):
    upper=rig.pose.bones['upper_arm.'+side];fore=rig.pose.bones['forearm.'+side]
    start=upper.head.copy();target=Vector(target);pole=Vector(pole);a=upper.bone.length;b=fore.bone.length;d=target-start;distance=min(a+b-.001,max(abs(a-b)+.001,d.length));axis=d.normalized();target=start+axis*distance
    along=(a*a-b*b+distance*distance)/(2*distance);off=math.sqrt(max(0,a*a-along*along));bend=pole-start-axis*(pole-start).dot(axis)
    if bend.length<.001:bend=Vector((0,-1,0))-axis*axis.dot(Vector((0,-1,0)))
    bend.normalize();elbow=start+axis*along+bend*off
    normal=(elbow-start).cross(target-elbow)
    if normal.length<.001:normal=Vector((0,-1,0))
    orient(rig,'upper_arm.'+side,elbow-start,(0,-1,0));orient(rig,'forearm.'+side,target-elbow,(0,-1,0))
    if direction is not None:orient(rig,'hand.'+side,direction,palm or (0,-1,0))

def gesture(rig,side,key):
    # Root, middle and distal curl angles; open digits retain a slight natural curve.
    values={'open':[0,0,0],'relaxed':[12,18,12],'fist':[66,82,58],'peace':[67,85,60],'rock':[67,85,60],'point':[66,84,58]}
    for name in ('index','middle','ring','pinky'):
        angles=values[key]
        if (key=='peace' and name in ('index','middle')) or (key=='rock' and name in ('index','pinky')) or (key=='point' and name=='index'):angles=[0,0,0]
        spread=0
        if key=='peace':spread={'index':-12,'middle':12}.get(name,0)
        elif key=='open':spread={'index':-5,'middle':0,'ring':3,'pinky':7}[name]
        for j,angle in enumerate(angles,1):
            pb=rig.pose.bones[f'{name}{j}.{side}'];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion((1,0,0),math.radians(angle))
            if j==1 and spread:pb.rotation_quaternion=Quaternion((0,0,1),math.radians(spread*(1 if side=='L' else -1)))@pb.rotation_quaternion
    for j in (1,2,3):
        pb=rig.pose.bones[f'thumb{j}.{side}'];pb.rotation_mode='QUATERNION';angle=(20,28,20)[j-1] if key in ('fist','peace','rock','point') else (0,5,5)[j-1];pb.rotation_quaternion=Quaternion((1,0,0),math.radians(angle))
        if j==1 and key in ('fist','peace','rock','point'):pb.rotation_quaternion=Quaternion((0,0,1),math.radians(48*(1 if side=='L' else -1)))@pb.rotation_quaternion
    bpy.context.view_layer.update()

def apply(rig,spec):
    pose=spec['pose'];cfg=model.POSE_PRESETS[pose['preset']];mirror=pose['mirror'];body=spec['body']
    for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    # Subtle upper-body attitude keeps the feet planted for all standing presets.
    for bone,key in [('chest','chest'),('head','head')]:
        angle=cfg.get(key,0)*(-1 if mirror else 1);pb=rig.pose.bones[bone];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion((0,0,1),math.radians(angle))
    if pose['preset']=='weight_shift':
        # Small pelvis sway with both feet held at their rest position by leg IK below.
        pb=rig.pose.bones['pelvis'];pb.location.x=.018*(-1 if mirror else 1);pb.location.y=-.003
    bpy.context.view_layer.update()
    arms=cfg.get('arms',{})
    def point(p):
        p=list(p)
        if mirror:p[0]*=-1
        return deform([p],body,'body')[0]
    def direction(p):
        p=list(p)
        if mirror:p[0]*=-1
        return p
    for source,arm in arms.items():
        side=({'L':'R','R':'L'}[source] if mirror else source)
        solve_arm(rig,side,point(arm['target']),point(arm['pole']),direction(arm['direction']) if arm.get('direction') else None,direction(arm.get('palm',[0,-1,0])))
    # For neutral arms retain the authored rest roll; fingers have an explicit curl axis.
    for side in ('L','R'):
        source=({'L':'R','R':'L'}[side] if mirror else side);choice=pose['left' if side=='L' else 'right']
        if choice=='auto':choice=arms.get(source,{}).get('gesture','relaxed')
        gesture(rig,side,choice)
    ground(rig)

def ground(rig):
    """A slight pelvis sway must not make either sole float or penetrate the floor."""
    for side in ('L','R'):
        upper=rig.pose.bones['thigh.'+side];lower=rig.pose.bones['shin.'+side];foot=rig.pose.bones['foot.'+side]
        start=upper.head.copy();target=foot.bone.head_local.copy();a=upper.bone.length;b=lower.bone.length;v=target-start;distance=min(a+b-.00001,max(.001,v.length));axis=v.normalized();along=(a*a-b*b+distance*distance)/(2*distance);height=math.sqrt(max(0,a*a-along*along));bend=Vector((0,-1,0));bend-=axis*bend.dot(axis);bend.normalize();knee=start+axis*along+bend*height
        # Keep rest legs unchanged when no actual pelvis displacement occurred.
        if (target-foot.head).length<1e-6:continue
        orient(rig,'thigh.'+side,knee-start,(0,1,0));orient(rig,'shin.'+side,target-knee,(0,1,0));orient(rig,'foot.'+side,foot.bone.tail_local-foot.bone.head_local,foot.bone.matrix_local.to_3x3().col[2])
    bpy.context.view_layer.update()
