import math
from ..utils.model_importer import import_model
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, CardMaker,
    GeomVertexFormat, GeomVertexData, Geom, GeomTriangles, GeomNode,
    GeomVertexWriter, BitMask32, CullFaceAttrib, Material
)

def create_procedural_plane(name="proc_plane", size=1.0):
    """Creates a plane geometry centered at origin in the XY plane."""
    cm = CardMaker(name)
    # Set frame in XY plane (Panda3D default)
    cm.setFrame(-size / 2, size / 2, -size / 2, size / 2)
    node = cm.generate()
    np = NodePath(node)
    # np.setHpr(0, -90, 0) # REMOVED - Keep plane in XY
    np.setTwoSided(False) # Usually terrain is viewed from above
    # Ensure correct winding order for default culling (Counter-Clockwise)
    # CardMaker default should be correct for XY plane view from +Z
    return np

# --- Keep other functions (create_procedural_cube, sphere, cylinder, etc.) as they are ---
def create_procedural_cube(name="proc_cube"):
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vdata.setNumRows(24)

    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')

    verts = [
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,0.5,-0.5),(-0.5,0.5,-0.5), # Bottom face (-Z)
        (-0.5,-0.5,0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),(0.5,-0.5,0.5),   # Top face (+Z)
        (-0.5,-0.5,-0.5),(0.5,-0.5,-0.5),(0.5,-0.5,0.5),(-0.5,-0.5,0.5), # Front face (-Y)
        (0.5,0.5,-0.5),(-0.5,0.5,-0.5),(-0.5,0.5,0.5),(0.5,0.5,0.5),   # Back face (+Y)
        (-0.5,0.5,-0.5),(-0.5,-0.5,-0.5),(-0.5,-0.5,0.5),(-0.5,0.5,0.5), # Left face (-X)
        (0.5,-0.5,-0.5),(0.5,0.5,-0.5),(0.5,0.5,0.5),(0.5,-0.5,0.5),   # Right face (+X)
    ]
    norms = [
        (0,0,-1),(0,0,-1),(0,0,-1),(0,0,-1), # Bottom face normal
        (0,0,1),(0,0,1),(0,0,1),(0,0,1),   # Top face normal
        (0,-1,0),(0,-1,0),(0,-1,0),(0,-1,0), # Front face normal
        (0,1,0),(0,1,0),(0,1,0),(0,1,0),   # Back face normal
        (-1,0,0),(-1,0,0),(-1,0,0),(-1,0,0), # Left face normal
        (1,0,0),(1,0,0),(1,0,0),(1,0,0)    # Right face normal
    ]

    for i in range(24):
        vertex.addData3f(verts[i])
        normal.addData3f(norms[i])

    tris = GeomTriangles(Geom.UHStatic)
    # Define triangles for each face (ensure counter-clockwise winding from outside view)
    indices = [
        0, 1, 2, 0, 2, 3,  # Bottom face
        4, 5, 6, 4, 6, 7,  # Top face
        8, 9, 10, 8, 10, 11, # Front face
        12, 13, 14, 12, 14, 15, # Back face
        16, 17, 18, 16, 18, 19, # Left face
        20, 21, 22, 20, 22, 23  # Right face
    ]
    for i in range(0, len(indices), 3):
        tris.addVertices(indices[i], indices[i+1], indices[i+2])
    tris.closePrimitive() # Close after adding all triangles for the primitive

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    node = GeomNode(name)
    node.addGeom(geom)
    np = NodePath(node)
    
    # Default cull is M_cull_clockwise, which is correct if winding is counter-clockwise
    # np.setAttrib(CullFaceAttrib.make(CullFaceAttrib.MCullNone)) # Optional: Disable culling for debug
    
    return np

def create_procedural_sphere(name="proc_sphere", radius=0.5, segments=24):
    if segments < 3: segments = 3
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, 'vertex')
    normal = GeomVertexWriter(vdata, 'normal')

    # Top pole
    vertex.addData3f(0, 0, radius); normal.addData3f(0, 0, 1)

    # Middle rings
    for i in range(1, segments): # Iterate through latitude rings
        theta = (i / segments) * math.pi
        z = radius * math.cos(theta)
        r_slice = radius * math.sin(theta)
        for j in range(segments): # Iterate through longitude lines
            phi = (j / segments) * 2 * math.pi
            x = r_slice * math.cos(phi)
            y = r_slice * math.sin(phi)
            n = Vec3(x, y, z)
            if n.lengthSquared() > 1e-6: n.normalize()
            else: n = Vec3(0, 0, 1 if z > 0 else -1)
            vertex.addData3f(x, y, z); normal.addData3f(n)

    # Bottom pole
    vertex.addData3f(0, 0, -radius); normal.addData3f(0, 0, -1)
    bottom_pole_idx = vdata.getNumRows() - 1

    tris = GeomTriangles(Geom.UHStatic)

    # Top cap triangles
    for j in range(segments):
        v1 = 1 + j
        v2 = 1 + (j + 1) % segments
        tris.addVertices(0, v2, v1) # Flipped order for CCW winding
    tris.closePrimitive()

    # Middle band triangles
    for i in range(0, segments - 2):
        row_start1 = 1 + i * segments
        row_start2 = 1 + (i + 1) * segments
        for j in range(segments):
            v0 = row_start1 + j
            v1 = row_start1 + (j + 1) % segments
            v2 = row_start2 + j
            v3 = row_start2 + (j + 1) % segments
            # Quad split into two triangles (ensure consistent winding)
            tris.addVertices(v0, v1, v2)
            tris.addVertices(v1, v3, v2)
        tris.closePrimitive()

    # Bottom cap triangles
    row_start = 1 + (segments - 2) * segments
    for j in range(segments):
        v1 = row_start + j
        v2 = row_start + (j + 1) % segments
        tris.addVertices(bottom_pole_idx, v1, v2) # Flipped order for CCW winding
    tris.closePrimitive()

    geom = Geom(vdata); geom.addPrimitive(tris); node = GeomNode(name); node.addGeom(geom)
    return NodePath(node)

def create_procedural_cylinder(name="proc_cylinder", radius=0.5, height=1.0, segments=24):
    if segments < 3: segments = 3
    format = GeomVertexFormat.getV3n3()
    vdata = GeomVertexData(name, format, Geom.UHStatic)
    vertex = GeomVertexWriter(vdata, 'vertex'); normal = GeomVertexWriter(vdata, 'normal')
    half_h = height / 2.0

    # --- Vertices for the side ---
    side_start_idx = vdata.getNumRows()
    for j in range(segments):
        angle = (j / segments) * 2 * math.pi
        x = radius * math.cos(angle); y = radius * math.sin(angle)
        side_normal = Vec3(x, y, 0)
        if side_normal.lengthSquared() > 1e-6: side_normal.normalize()
        else: side_normal = Vec3(1,0,0) # Fallback for center case (shouldn't happen)

        vertex.addData3f(x, y, -half_h); normal.addData3f(side_normal) # Bottom vertex for segment j
        vertex.addData3f(x, y, half_h); normal.addData3f(side_normal)  # Top vertex for segment j

    # --- Vertices for the top cap ---
    top_center_idx = vdata.getNumRows(); vertex.addData3f(0, 0, half_h); normal.addData3f(0, 0, 1)
    top_cap_start_idx = vdata.getNumRows()
    for j in range(segments):
        angle=(j/segments)*2*math.pi; x=radius*math.cos(angle); y=radius*math.sin(angle)
        vertex.addData3f(x, y, half_h); normal.addData3f(0, 0, 1)

    # --- Vertices for the bottom cap ---
    bottom_center_idx = vdata.getNumRows(); vertex.addData3f(0, 0, -half_h); normal.addData3f(0, 0, -1)
    bottom_cap_start_idx = vdata.getNumRows()
    for j in range(segments):
        angle=(j/segments)*2*math.pi; x=radius*math.cos(angle); y=radius*math.sin(angle)
        vertex.addData3f(x, y, -half_h); normal.addData3f(0, 0, -1)

    # --- Triangles ---
    tris = GeomTriangles(Geom.UHStatic)

    # Side triangles
    for j in range(segments):
        v0_bottom = side_start_idx + j * 2
        v1_top    = side_start_idx + j * 2 + 1
        v2_bottom = side_start_idx + ((j + 1) % segments) * 2
        v3_top    = side_start_idx + ((j + 1) % segments) * 2 + 1
        # Quad split into two triangles (ensure consistent winding)
        tris.addVertices(v0_bottom, v1_top, v2_bottom)
        tris.addVertices(v1_top, v3_top, v2_bottom)
    tris.closePrimitive()

    # Top cap triangles
    for j in range(segments):
        v0 = top_center_idx
        v1 = top_cap_start_idx + j
        v2 = top_cap_start_idx + (j + 1) % segments
        tris.addVertices(v0, v2, v1) # Flipped order for CCW
    tris.closePrimitive()

    # Bottom cap triangles
    for j in range(segments):
        v0 = bottom_center_idx
        v1 = bottom_cap_start_idx + j
        v2 = bottom_cap_start_idx + (j + 1) % segments
        tris.addVertices(v0, v1, v2) # Correct order for CCW from below
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
        # Pass arguments based on shape type
        if shape_key == 'plane':
            if 'size' in kwargs: relevant_args['size'] = kwargs['size']
        elif shape_key == 'cube':
             pass # Cube takes no size args currently, uses unit size
        elif shape_key == 'sphere':
            if 'radius' in kwargs: relevant_args['radius'] = kwargs['radius']
            if 'segments' in kwargs: relevant_args['segments'] = kwargs['segments']
        elif shape_key == 'cylinder':
            if 'radius' in kwargs: relevant_args['radius'] = kwargs['radius']
            if 'height' in kwargs: relevant_args['height'] = kwargs['height']
            if 'segments' in kwargs: relevant_args['segments'] = kwargs['segments']

        try:
            # Create the geometry
            geom_np = shape_func(name=name + "_geom", **relevant_args)
            if not geom_np:
                 print(f"Error: Shape function for '{shape_key}' returned None.")
                 return None
            # Apply default material settings
            apply_default_material(geom_np)
            return geom_np
        except Exception as e:
            print(f"Error calling procedural shape function for '{shape_key}' with {relevant_args}: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print(f"Warning: Unknown procedural shape key '{shape_key}'.")
        return None

def apply_default_material(nodepath, shininess=16, specular_color=Vec4(0.2, 0.2, 0.2, 1)): # Reduced shininess/specular
    """Apply a default material with proper lighting properties to a NodePath."""
    if not nodepath or nodepath.isEmpty():
        return
    material = Material()
    material.setShininess(shininess)
    material.setSpecular(specular_color)
    # Make sure ambient/diffuse are not black by default
    material.setAmbient(Vec4(0.6, 0.6, 0.6, 1)) # Allow ambient light influence
    material.setDiffuse(Vec4(1, 1, 1, 1))    # Allow diffuse light influence
    nodepath.setMaterial(material, 1) # Apply with override

    nodepath.setTwoSided(False) # Ensure single-sided rendering unless needed

def create_player_model(name="player_model", body_color=Vec4(0.3, 0.5, 0.8, 1), head_color=Vec4(0.8, 0.7, 0.6, 1)):
    path = "shrek.glb"
    root = NodePath(name)
    model_node, anim_names = import_model(path, parent=root, scale=0.02)
    model_node.setHpr(180, 0, 0)
    return model_node, anim_names

def apply_crystal_material(nodepath, shininess=40, specular_color=Vec4(0.8, 0.8, 1.0, 1)):
    """Apply a shiny material suitable for crystals."""
    if not nodepath or nodepath.isEmpty():
        return
    material = Material()
    material.setShininess(shininess)
    material.setSpecular(specular_color)
    # Crystals might reflect ambient less, depending on desired look
    material.setAmbient(Vec4(0.4, 0.4, 0.5, 1))
    material.setDiffuse(Vec4(1, 1, 1, 1))
    nodepath.setMaterial(material, 1)