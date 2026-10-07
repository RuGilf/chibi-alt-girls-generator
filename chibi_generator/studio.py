"""Native Blender presentation workspace and camera views."""
from mathutils import Vector
import bpy
from .scene import ASSET
from .deformation import deform

VIEWS={'hero':((2.6,-6,2.6),False),'front':((0,-6,1.5),False),'side':((6,0,1.5),False),'back':((0,6,1.5),False),'face':((.16,-5,1.63),True)}

def ensure(context):
    sc=context.scene
    col=next((c for c in sc.collection.children if c.get('chibi_studio')),None)
    if col is None:
        # Reuse the approved studio if it already belongs to this scene.
        col=next((c for c in sc.collection.children if c.name.startswith('06 Studio')),None)
        if col is None:
            with bpy.data.libraries.load(str(ASSET),link=False) as (_,dst):dst.collections=['06 Studio']
            col=dst.collections[0];sc.collection.children.link(col)
        col['chibi_studio']=True
    camera=next((o for o in col.objects if o.type=='CAMERA'),None)
    if camera is None:
        camera=bpy.data.objects.new('Character camera',bpy.data.cameras.new('Character camera'));col.objects.link(camera)
    sc.camera=camera
    if not sc.world or not sc.world.get('chibi_studio'):
        world=bpy.data.worlds.new('Character studio');world.use_nodes=True;world['chibi_studio']=True
        bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.32,.30,.40,1);bg.inputs['Strength'].default_value=.35;sc.world=world
    sc.render.engine='CYCLES';sc.cycles.samples=80;sc.cycles.use_denoising=True
    sc.render.resolution_x=1000;sc.render.resolution_y=1250;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='AgX'
    return camera

def set_view(context,character,view='hero'):
    camera=ensure(context);sc=context.scene;offset,portrait=VIEWS[view];body=character.parameters['body']
    center=Vector(deform([[0,0,1.565 if portrait else 1.0]],body,'head' if portrait else 'body')[0]);center=character.rig.matrix_world@center
    direction=Vector(offset)-Vector((0,0,1.565 if portrait else 1.0))
    camera.location=center+direction;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO';camera.data.ortho_scale=.9 if portrait else 2.25+(body['height']-.5)*.42
    sc.render.resolution_x=900 if portrait else 1000;sc.render.resolution_y=1000 if portrait else 1250
    for area in context.screen.areas if context.screen else []:
        if area.type=='VIEW_3D':
            space=area.spaces.active;space.region_3d.view_perspective='CAMERA';space.region_3d.view_camera_zoom=10
    sc['chibi_view']=view

def configure_area(area):
    space=area.spaces.active;space.show_region_ui=True;space.show_region_toolbar=False
    space.overlay.show_overlays=False;space.show_gizmo=False
    space.shading.type='MATERIAL';space.shading.use_scene_lights=True;space.shading.use_scene_world=True
    space.region_3d.view_perspective='CAMERA';space.region_3d.view_camera_zoom=10

def open_workspace(context,character):
    ensure(context)
    if context.workspace:context.workspace.name='АЛЬТУШКА'
    for area in context.screen.areas:
        if area.type=='VIEW_3D':configure_area(area)
    if context.area and context.area.type=='VIEW_3D' and not context.screen.show_fullscreen:
        bpy.ops.screen.screen_full_area(use_hide_panels=False)
    set_view(context,character,context.scene.get('chibi_view','hero'))
