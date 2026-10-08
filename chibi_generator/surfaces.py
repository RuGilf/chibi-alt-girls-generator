"""Small procedural surfaces in neutral mesh space; no external image textures."""
import bpy
import numpy as np

REVISION = 1
COORDINATES = 'ChibiRestPosition'
PREFIX = 'Chibi Surface · '
PROFILES = {
    'cloth': dict(rough=.78, scale=260, strength=.10, distance=.00065, sheen=.12),
    'knit': dict(rough=.82, scale=115, strength=.19, distance=.0011, sheen=.22),
    'denim': dict(rough=.84, scale=310, strength=.16, distance=.00075, sheen=.10),
    'leather': dict(rough=.36, scale=380, strength=.13, distance=.00045, coat=.12),
    'vinyl': dict(rough=.22, scale=430, strength=.025, distance=.00015, coat=.34),
    'velvet': dict(rough=.86, scale=480, strength=.045, distance=.00035, sheen=.65),
    'rubber': dict(rough=.72, scale=260, strength=.07, distance=.0004),
    'skin': dict(rough=.48),
    'hair': dict(rough=.36),
    'metal': dict(rough=.26),
}


def configure(material, kind='cloth', rough=None):
    """Keep colors/patterns intact; replace only managed normal/roughness nodes."""
    if kind not in PROFILES:
        raise ValueError('Unknown surface profile: ' + kind)
    if material.get('chibi_surface_revision') == REVISION and material.get('chibi_surface') == kind:
        return
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bs = nodes.get('Principled BSDF')
    if bs is None:
        return
    for node in list(nodes):
        if node.name.startswith(PREFIX):
            nodes.remove(node)
    # Replace the old generic fabric bump without touching color/pattern nodes.
    for link in list(links):
        if link.to_socket == bs.inputs['Normal'] and link.from_node.type == 'BUMP':
            bump = link.from_node
            links.remove(link)
            nodes.remove(bump)
    profile = PROFILES[kind]
    base_rough = profile['rough'] if rough is None else rough
    bs.inputs['Roughness'].default_value = base_rough
    bs.inputs['Sheen Weight'].default_value = profile.get('sheen', 0)
    bs.inputs['Sheen Roughness'].default_value = .65
    bs.inputs['Coat Weight'].default_value = profile.get('coat', 0)
    bs.inputs['Coat Roughness'].default_value = .19
    if kind == 'skin':
        bs.inputs['Specular IOR Level'].default_value = .28
        bs.inputs['Subsurface Weight'].default_value = .035
        bs.inputs['Subsurface Scale'].default_value = .02
        bs.inputs['Subsurface Radius'].default_value = (1, .45, .25)
    if 'scale' in profile:
        def node(type_name, role):
            result = nodes.new(type_name)
            result.name = PREFIX + role
            result.label = role
            return result
        coordinates = node('ShaderNodeAttribute', 'Neutral coordinates')
        coordinates.attribute_name = COORDINATES
        grain = node('ShaderNodeTexNoise', 'Fine grain')
        grain.inputs['Scale'].default_value = profile['scale']
        grain.inputs['Detail'].default_value = 2
        links.new(coordinates.outputs['Vector'], grain.inputs['Vector'])
        height = grain.outputs['Fac']
        if kind in ('cloth', 'knit', 'denim'):
            waves = []
            for direction in ('X', 'DIAGONAL' if kind == 'denim' else 'Z'):
                wave = node('ShaderNodeTexWave', 'Weave ' + direction)
                wave.wave_type = 'BANDS'
                wave.bands_direction = direction
                wave.wave_profile = 'SIN'
                wave.inputs['Scale'].default_value = profile['scale'] * (.45 if direction == 'Z' else 1)
                wave.inputs['Distortion'].default_value = .25 if kind == 'knit' else .04
                links.new(coordinates.outputs['Vector'], wave.inputs['Vector'])
                waves.append(wave.outputs['Fac'])
            weave = node('ShaderNodeMath', 'Crossed threads')
            weave.operation = 'MULTIPLY'
            links.new(waves[0], weave.inputs[0])
            links.new(waves[1], weave.inputs[1])
            height = weave.outputs[0]
        bump = node('ShaderNodeBump', 'Micro relief')
        bump.inputs['Strength'].default_value = profile['strength']
        bump.inputs['Distance'].default_value = profile['distance']
        links.new(height, bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bs.inputs['Normal'])
        roughness = node('ShaderNodeMapRange', 'Roughness variation')
        roughness.inputs['To Min'].default_value = max(.02, base_rough - .035)
        roughness.inputs['To Max'].default_value = min(1, base_rough + .035)
        links.new(grain.outputs['Fac'], roughness.inputs['Value'])
        links.new(roughness.outputs[0], bs.inputs['Roughness'])
    material['chibi_surface'] = kind
    material['chibi_surface_revision'] = REVISION


def ensure_coordinates(ob):
    """Use Basis rather than posed/deformed coordinates so texture cannot swim."""
    if ob.type != 'MESH' or not any(m and m.get('chibi_surface') in PROFILES and
                                   'scale' in PROFILES[m['chibi_surface']] for m in ob.data.materials):
        return
    mesh = ob.data
    attribute = mesh.attributes.get(COORDINATES)
    if attribute and len(attribute.data) == len(mesh.vertices):
        return
    if attribute:
        mesh.attributes.remove(attribute)
    source = mesh.shape_keys.key_blocks['Basis'].data if mesh.shape_keys else mesh.vertices
    points = np.empty(len(source) * 3, dtype=np.float32)
    source.foreach_get('co', points)
    attribute = mesh.attributes.new(COORDINATES, 'FLOAT_VECTOR', 'POINT')
    attribute.data.foreach_set('vector', points)


def upgrade_cached(objects, catalog):
    """Upgrade known generated materials in old saves without rebuilding meshes."""
    legacy = {'Wardrobe • oat knit': 'knit', 'Wardrobe • mulberry stripe': 'knit',
              'Wardrobe • black denim': 'denim', 'Wardrobe • ivory rubber': 'rubber'}
    for ob in objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        slot, key = ob.get('chibi_slot'), ob.get('chibi_option')
        cfg = catalog.get(slot, {}).get(key, {})
        for mat in ob.data.materials:
            if not mat or not mat.use_nodes or mat.get('chibi_hair_material'):
                continue
            kind = mat.get('chibi_surface') or next((v for k, v in legacy.items() if mat.name.startswith(k)), None)
            if not kind and key and mat.name.startswith(key + ' • fabric'):
                kind = cfg.get('surface', 'cloth')
            if kind:
                configure(mat, kind)
        ensure_coordinates(ob)
