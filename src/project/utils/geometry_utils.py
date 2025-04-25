import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, CardMaker,
    GeomVertexFormat, GeomVertexData, Geom, GeomTriangles, GeomNode,
    GeomVertexWriter, BitMask32, CullFaceAttrib
)

def create_procedural_plane(name="proc_plane", size=1.0):
    cm = CardMaker(name)
    cm.setFrame(-size / 2, size / 2, -size / 2, size / 2)
    node = cm.generate()
    np = NodePath(node)
    np.setHpr(0, -90, 0)
    return np

def create_procedural_cube(name="proc_cube"):
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vdata.setNumRows(24)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')

    verts = [
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5),
        (-0.5,-0.5,0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),(0.5,-0.5,0.5),
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,-0.5,0.5),(-0.5,-0.5,0.5),
        (0.5,0.5,-0.5),(-0.5,0.5,-0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),
        (-0.5,0.5,-0.5),(-0.5,-0.5,-0.5),(-0.5,-0.5,0.5),(-0.5,0.5,0.5),
        (0.5,-0.5,-0.5),(0.5,0.5,-0.5),(0.5,0.5,0.5),(0.5,-0.5,0.5),
    ]
    norms = [
        (0,0,-1),(0,0,-1),(0,0,-1),(0,0,-1),
        (0,0,1),(0,0,1),(0,0,1),(0,0,1),
        (0,-1,0),(0,-1,0),(0,-1,0),(0,-1,0),
        (0,1,0),(0,1,0),(0,1,0),(0,1,0),
        (-1,0,0),(-1,0,0),(-1,0,0),(-1,0,0),
        (1,0,0),(1,0,0),(1,0,0),(1,0,0)
    ]

    for i in range(24):
        vertex.addData3f(verts[i])
        normal.addData3f(norms[i])

    tris = GeomTriangles(Geom.UHStatic)
    for i in range(0, 24, 4):
        tris.addVertices(i + 0, i + 2, i + 1)
        tris.addVertices(i + 0, i + 3, i + 2)
        tris.closePrimitive()

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    np = NodePath(node)
    
    np.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullNone))
    
    return np

def create_procedural_sphere(name="proc_sphere", radius=0.5, segments=24):
    if segments < 3: segments = 3
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')

    vertex.addData3f(0, 0, radius); normal.addData3f(0, 0, 1)
    for i in range(1, segments):
        theta = (i / segments) * math.pi; z = radius * math.cos(theta); r_slice = radius * math.sin(theta)
        for j in range(segments):
            phi = (j / segments) * 2 * math.pi; x = r_slice * math.cos(phi); y = r_slice * math.sin(phi)
            n = Vec3(x, y, z)
            if n.lengthSquared() > 0.0001: n.normalize()
            else: n = Vec3(0, 0, 1 if z > 0 else -1)
            vertex.addData3f(x, y, z); normal.addData3f(n)
    vertex.addData3f(0, 0, -radius); normal.addData3f(0, 0, -1)
    bottom_pole_idx = vdata.getNumRows() - 1

    tris = GeomTriangles(Geom.UHStatic)
    for j in range(segments):
        v1 = 1 + j
        v2 = 1 + (j + 1) % segments
        tris.addVertices(0, v1, v2)
    tris.closePrimitive()

    for i in range(0, segments - 2):
        row_start1 = 1 + i * segments
        row_start2 = 1 + (i + 1) * segments
        for j in range(segments):
            v0 = row_start1 + j
            v1 = row_start1 + (j + 1) % segments
            v2 = row_start2 + j
            v3 = row_start2 + (j + 1) % segments
            tris.addVertices(v0, v2, v1); tris.addVertices(v1, v2, v3)
        tris.closePrimitive()

    row_start = 1 + (segments - 2) * segments
    for j in range(segments):
        v1 = row_start + j
        v2 = row_start + (j + 1) % segments
        tris.addVertices(bottom_pole_idx, v2, v1)
    tris.closePrimitive()

    geom = Geom(vdata); geom.addPrimitive(tris); node = GeomNode(name); node.addGeom(geom)
    return NodePath(node)

def create_procedural_cylinder(name="proc_cylinder", radius=0.5, height=1.0, segments=24):
    if segments < 3: segments = 3
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, 'vertex'); normal = GeomVertexWriter(vdata, 'normal')
    half_h = height / 2.0

    for j in range(segments):
        angle = (j / segments) * 2 * math.pi
        x = radius * math.cos(angle); y = radius * math.sin(angle)
        side_normal = Vec3(x, y, 0)
        if side_normal.lengthSquared() > 0.0001: side_normal.normalize()
        else: side_normal = Vec3(1,0,0)

        vertex.addData3f(x, y, -half_h); normal.addData3f(side_normal)
        vertex.addData3f(x, y, half_h); normal.addData3f(side_normal)

    top_center_idx = vdata.getNumRows(); vertex.addData3f(0, 0, half_h); normal.addData3f(0, 0, 1)
    bottom_center_idx = vdata.getNumRows(); vertex.addData3f(0, 0, -half_h); normal.addData3f(0, 0, -1)

    top_cap_start_idx = vdata.getNumRows()
    for j in range(segments):
        angle=(j/segments)*2*math.pi; x=radius*math.cos(angle); y=radius*math.sin(angle)
        vertex.addData3f(x, y, half_h); normal.addData3f(0, 0, 1)

    bottom_cap_start_idx = vdata.getNumRows()
    for j in range(segments):
        angle=(j/segments)*2*math.pi; x=radius*math.cos(angle); y=radius*math.sin(angle)
        vertex.addData3f(x, y, -half_h); normal.addData3f(0, 0, -1)

    tris = GeomTriangles(Geom.UHStatic)

    for j in range(segments):
        v0 = j * 2
        v1 = j * 2 + 1
        v2 = ((j + 1) % segments) * 2
        v3 = ((j + 1) % segments) * 2 + 1
        tris.addVertices(v0, v2, v1); tris.addVertices(v1, v2, v3)
    tris.closePrimitive()

    for j in range(segments):
        v0 = top_center_idx
        v1 = top_cap_start_idx + j
        v2 = top_cap_start_idx + (j + 1) % segments
        tris.addVertices(v0, v1, v2)
    tris.closePrimitive()

    for j in range(segments):
        v0 = bottom_center_idx
        v1 = bottom_cap_start_idx + (j + 1) % segments
        v2 = bottom_cap_start_idx + j
        tris.addVertices(v0, v1, v2)
    tris.closePrimitive()

    geom = Geom(vdata); geom.addPrimitive(tris); node = GeomNode(name); node.addGeom(geom)
    return NodePath(node)

PROCEDURAL_SHAPES = {
    'cube': create_procedural_cube,
    'sphere': create_procedural_sphere,
    'cylinder': create_procedural_cylinder,
    'plane': create_procedural_plane,
}

def get_procedural_shape(shape_key, name="proc_shape", **kwargs):
    shape_func = PROCEDURAL_SHAPES.get(shape_key)
    if shape_func:
        relevant_args = {}
        if shape_key == 'plane':
            if 'size' in kwargs: relevant_args['size'] = kwargs['size']
        elif shape_key == 'cube':
             pass
        elif shape_key == 'sphere':
            if 'radius' in kwargs: relevant_args['radius'] = kwargs['radius']
            if 'segments' in kwargs: relevant_args['segments'] = kwargs['segments']
        elif shape_key == 'cylinder':
            if 'radius' in kwargs: relevant_args['radius'] = kwargs['radius']
            if 'height' in kwargs: relevant_args['height'] = kwargs['height']
            if 'segments' in kwargs: relevant_args['segments'] = kwargs['segments']

        try:
            return shape_func(name=name, **relevant_args)
        except Exception as e:
            print(f"Error calling procedural shape function for '{shape_key}' with {relevant_args}: {e}")
            return None
    else:
        print(f"Warning: Unknown procedural shape key '{shape_key}'.")
        return None
    
def create_simple_player_model(name="player_model", body_color=Vec4(0.3, 0.5, 0.8, 1), head_color=Vec4(0.8, 0.7, 0.6, 1)):
    """Creates a simple snowman-like player model."""
    player_geom_root = NodePath(name)

    body_radius = 0.35
    body_height = 1.0
    body = create_procedural_cylinder(name + "_body", radius=body_radius, height=body_height, segments=12)
    if body:
        body.reparentTo(player_geom_root)
        body.setPos(0, 0, body_height / 2)
        body.setColor(body_color)
        body.setCollideMask(BitMask32(0))

    head_radius = 0.3
    head = create_procedural_sphere(name + "_head", radius=head_radius, segments=16)
    if head:
        head.reparentTo(player_geom_root)
        head.setPos(0, 0, body_height + head_radius * 0.8)
        head.setColor(head_color)
        head.setCollideMask(BitMask32(0))

    return player_geom_root
