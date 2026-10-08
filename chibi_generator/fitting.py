"""Neutral garment fitting operations; always run before morphs and armature binding."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def conform_trims(surface,objects,labels):
    """Seat a stitched tube on the joined garment without flattening its cross-section."""
    mesh=surface.data;tree=BVHTree.FromPolygons([v.co for v in mesh.vertices],[p.vertices[:] for p in mesh.polygons])
    for ob in objects:
        if not any(ob.get('chibi_asset','').endswith(label) or (' • '+label+' ') in ob.get('chibi_asset','') for label in labels):continue
        sides=ob.get('chibi_tube_sides');radius=ob.get('chibi_tube_radius')
        if not sides or not radius:continue
        points=np.array([v.co[:] for v in ob.data.vertices]);rings=points.reshape(-1,sides,3)
        for ring in rings:
            center=ring.mean(axis=0);hit,normal,_,_=tree.find_nearest(Vector(center))
            if hit is not None:ring+=np.asarray(hit+normal*radius*.65)-center
        ob.data.vertices.foreach_set('co',rings.ravel());ob.data.update();ob['chibi_conformed_trim']=True
