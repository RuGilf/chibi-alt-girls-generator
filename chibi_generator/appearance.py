"""Per-character skin ownership, including skin visible through procedural fabric."""
import bpy,numpy as np
from . import model
OLD=(.66,.36,.265)

def is_skin_socket(socket):
    try:return len(socket.default_value)==4 and all(abs(a-b)<1e-5 for a,b in zip(socket.default_value[:3],OLD))
    except (TypeError,AttributeError):return False

def apply_materials(objects,rig,spec):
    owner=rig['chibi_character_id'];color=model.skin_rgb(spec['skin']);owned={};visited=set()
    for ob in objects:
        if ob.type!='MESH' or ob.hide_render:continue
        for slot in ob.material_slots:
            mat=slot.material
            if not mat or not mat.use_nodes or mat.get('chibi_hair_material'):continue
            source=mat
            sockets=[sock for node in mat.node_tree.nodes for sock in node.inputs if node.type in ('BSDF_PRINCIPLED','MIX_RGB') and is_skin_socket(sock)]
            if not sockets and not mat.node_tree.nodes.get('Chibi skin tone'):continue
            if mat.get('chibi_skin_owner')!=owner:
                if source not in owned:owned[source]=source.copy();owned[source]['chibi_skin_owner']=owner
                mat=owned[source];slot.material=mat
            if mat in visited:continue
            visited.add(mat);nodes=mat.node_tree.nodes;links=mat.node_tree.links
            rgb=nodes.get('Chibi skin tone')
            if rgb is None:
                sockets=[sock for node in nodes for sock in node.inputs if node.type in ('BSDF_PRINCIPLED','MIX_RGB') and is_skin_socket(sock)]
                rgb=nodes.new('ShaderNodeRGB');rgb.name='Chibi skin tone';rgb.label='Общий оттенок кожи'
                for sock in sockets:
                    if not sock.is_linked:links.new(rgb.outputs[0],sock)
            rgb.outputs[0].default_value=(*color,1);mat.diffuse_color=(*color,1)
    # Brows receive their own material, independent from the sculpted hair meshes.
    brow=np.array(model.HAIR_COLORS[spec['hair']['color']][1])*.43+np.array([.008,.005,.010])
    for ob in objects:
        if ob.type=='MESH' and ob.get('chibi_asset','').startswith('Brow'):
            mat=ob.data.materials[0]
            if mat.get('chibi_brow_owner')!=owner:
                mat=mat.copy();mat['chibi_brow_owner']=owner;ob.data.materials[0]=mat
            bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*brow,1);mat.diffuse_color=(*brow,1)

    for source in owned:
        if source.users==0 and not source.use_fake_user:bpy.data.materials.remove(source)
