import math
import random
import numpy as np
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, BitMask32, TransparencyAttrib,
    Texture, TextureStage, PNMImage, CardMaker, GeomVertexWriter,
    GeomVertexData, Geom, GeomNode, GeomTriangles, GeomVertexFormat, GeomVertexRewriter
)
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, LerpColorScaleInterval, Wait
from ...utils import geometry_utils

# Noise implementation for Panda3D (Keep as is)
class NoiseGenerator:
    """Fast Simplex-like noise generator optimized for terrain."""
    
    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 999999)
        self.seed = seed
        random.seed(seed)
        
        # Generate permutation table
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm += self.perm
        
        # Gradient vectors (optimized for 2D)
        self.grad2 = [
            (1, 1), (-1, 1), (1, -1), (-1, -1),
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]
        
    def noise2d(self, x, y):
        """Generate 2D simplex-like noise value in range [-1, 1]"""
        # Integer coordinates
        ix, iy = int(math.floor(x)), int(math.floor(y))
        
        # Fractional coordinates
        fx, fy = x - ix, y - iy
        
        # Wrap to 0-255 range
        ix, iy = ix & 255, iy & 255
        
        # Calculate contributions from 4 corners
        n00 = self._gradient(ix, iy, fx, fy)
        n01 = self._gradient(ix, iy + 1, fx, fy - 1)
        n10 = self._gradient(ix + 1, iy, fx - 1, fy)
        n11 = self._gradient(ix + 1, iy + 1, fx - 1, fy - 1)
        
        # Smoothing
        fx = self._fade(fx)
        fy = self._fade(fy)
        
        # Interpolate
        nx0 = self._lerp(n00, n10, fx)
        nx1 = self._lerp(n01, n11, fx)
        n = self._lerp(nx0, nx1, fy)
        
        # Scale to [-1, 1]
        return n * 0.707 # Simplex scale factor adjustment
    
    def fbm(self, x, y, octaves=6, persistence=0.5, lacunarity=2.0):
        """
        Fractional Brownian Motion - stacks multiple noise layers
        at different frequencies and amplitudes
        """
        total = 0
        frequency = 1
        amplitude = 1
        max_value = 0
        
        # Sum up noise contributions from different octaves
        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity
            
        # Normalize to range [-1, 1] (avoid division by zero)
        return total / max(max_value, 1e-6)
    
    def _gradient(self, ix, iy, fx, fy):
        """Calculate gradient noise contribution"""
        # Get gradient vector
        g_idx = self.perm[(ix + self.perm[iy & 255]) & 255] % 8
        g = self.grad2[g_idx]
        
        # Dot product with distance vector
        return g[0] * fx + g[1] * fy
    
    def _fade(self, t):
        """Smoothing function for better interpolation"""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, a, b, t):
        """Linear interpolation"""
        return a + t * (b - a)
    
class TerrainGenerator:
    """Generates an infinite-looking terrain using chunked noise generation."""
    
    def __init__(self, app, root_node, settings_manager, palette, proc_gen_consts, collision_consts, **kwargs):
        self.app = app
        self.render = app.render
        self.loader = app.loader
        self.root_node = root_node
        self.settings_manager = settings_manager
        self.palette = palette
        self.proc_gen_consts = proc_gen_consts
        self.collision_consts = collision_consts
        self.env_consts = settings_manager.constants.get('environment', {})
        
        # Get terrain settings or use defaults with PERFORMANCE OPTIMIZATIONS
        self.terrain_settings = self._get_terrain_settings()
        
        # Override specific settings for better performance
        # OPTIMIZATION 1: Increase mesh size to reduce segment count
        self.terrain_settings['detail_mesh_size'] = 2.0  # Was likely 1.0
        
        # OPTIMIZATION 2: Reduce view distance to load fewer chunks
        self.terrain_settings['view_distance'] = 3  # Was likely 5
        
        # OPTIMIZATION 3: Reduce feature density
        self.terrain_settings['feature_density'] = 0.01  # Was likely 0.03
        
        # Initialize noise generator
        seed = self.terrain_settings.get('seed', random.randint(0, 999999))
        self.noise_gen = NoiseGenerator(seed)
        
        # Track loaded chunks and features
        self.loaded_chunks = {}  # (x, y) -> NodePath
        self.static_elements = []
        self.animating_intervals = []
        
        # Chunk manager
        self.chunk_size = self.terrain_settings.get('chunk_size', 16)
        self.view_distance = self.terrain_settings.get('view_distance', 3)  # Modified in constructor
        self.height_scale = self.terrain_settings.get('height_scale', 15.0)
        self.current_center_chunk = None
        
        # OPTIMIZATION 4: Larger height cache for better memory usage vs CPU tradeoff
        self.height_cache = {}
        
    def _get_terrain_settings(self):
        """Get terrain settings from configuration"""
        default_settings = {
            'seed': random.randint(0, 999999),
            'chunk_size': 16,  # Size of each terrain chunk
            'view_distance': 3,  # OPTIMIZED: Reduced from 5 to 3
            'height_scale': 15.0,  # Maximum terrain height
            'noise_scale': 0.01,  # Scale factor for noise (smaller = more gradual)
            'octaves': 4,  # OPTIMIZED: Reduced from 6 to 4
            'persistence': 0.5,  # How much each octave contributes
            'lacunarity': 2.0,  # How frequency increases with each octave
            'water_level': -2.0,  # Height of water plane
            'biome_scale': 0.005,  # Scale of biome variation
            'feature_density': 0.01,  # OPTIMIZED: Reduced from 0.03 to 0.01
            'detail_mesh_size': 2.0,  # OPTIMIZED: Increased from 1.0 to 2.0
            'use_textures': False,  # Whether to use textures or color
            'generate_features': True  # Whether to generate additional features
        }
        
        # Check if terrain settings exist in environment constants
        terrain_proc_gen = self._get_proc_const(['terrain_generation'], {})
        
        # Update default settings with any config values
        for key, default_val in default_settings.items():
            if key in terrain_proc_gen:
                default_settings[key] = terrain_proc_gen[key]
        
        return default_settings
    
    def _get_proc_const(self, keys, default=None):
        """Get a nested constant from proc_gen_consts"""
        current = self.proc_gen_consts
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
            if current is None:
                return default
        return current
        
    def _get_palette_color(self, key, default=Vec4(1,1,1,1)):
        """Get a color from the palette"""
        return self.settings_manager.get_palette_color(key, default)
    
    def _set_geometry_collision(self, node_path):
        """Set collision properties for terrain geometry"""
        mask_ground = self.collision_consts.get('MASK_GROUND', BitMask32(1))
        node_path.setCollideMask(mask_ground)
    
    def calculate_terrain_height(self, world_x, world_y):
        """Calculate terrain height at a specific world coordinate (X, Y)"""
        # Check if height is already cached
        cache_key = (world_x, world_y)
        if cache_key in self.height_cache:
            return self.height_cache[cache_key]
        
        # Scale coordinates to noise space
        noise_scale = self.terrain_settings.get('noise_scale', 0.01)
        nx, ny = world_x * noise_scale, world_y * noise_scale
        
        # Get noise settings
        octaves = self.terrain_settings.get('octaves', 4)  # OPTIMIZED: Using fewer octaves
        persistence = self.terrain_settings.get('persistence', 0.5)
        lacunarity = self.terrain_settings.get('lacunarity', 2.0)
        
        # Calculate base height using FBM noise
        height = self.noise_gen.fbm(nx, ny, octaves, persistence, lacunarity)
        
        # Add some large-scale variation
        large_scale = self.noise_gen.noise2d(nx * 0.2, ny * 0.2) * 0.3
        
        # Add some medium-scale details
        medium_scale = self.noise_gen.noise2d(nx * 2.0, ny * 2.0) * 0.15
        
        # Combine all scales with main height
        combined_height = height + large_scale + medium_scale
        
        # Scale to desired height range
        height_scale = self.terrain_settings.get('height_scale', 15.0)
        final_height = combined_height * height_scale

        # Cache the result
        self.height_cache[cache_key] = final_height
        return final_height
    
    def get_terrain_color(self, world_x, world_y, height):
        """Determine terrain color based on height and additional factors"""
        # OPTIMIZATION: Simplified terrain color calculation
        # Get slope by sampling nearby heights (using larger sample distance)
        sample_dist = 2.0  # OPTIMIZED: Increased from 1.0 to 2.0
        h_px = self.calculate_terrain_height(world_x + sample_dist, world_y)
        h_nx = self.calculate_terrain_height(world_x - sample_dist, world_y)
        h_py = self.calculate_terrain_height(world_x, world_y + sample_dist)
        h_ny = self.calculate_terrain_height(world_x, world_y - sample_dist)
        
        slope_x = (h_px - h_nx) / (2 * sample_dist)
        slope_y = (h_py - h_ny) / (2 * sample_dist)
        slope = math.sqrt(slope_x**2 + slope_y**2)
        
        # Reference heights for color transitions
        water_level = self.terrain_settings.get('water_level', -2.0)
        beach_level = water_level + 1.0
        grass_level = beach_level + 2.0
        mountain_level = grass_level + 8.0
        snow_level = mountain_level + 4.0
        
        # Get base colors from palette
        water_color = self._get_palette_color('water', Vec4(0.1, 0.3, 0.6, 1.0))
        beach_color = self._get_palette_color('beach', Vec4(0.8, 0.7, 0.5, 1.0))
        grass_color = self._get_palette_color('grass', Vec4(0.3, 0.5, 0.2, 1.0))
        rock_color = self._get_palette_color('rock', Vec4(0.5, 0.4, 0.3, 1.0))
        snow_color = self._get_palette_color('snow', Vec4(0.9, 0.9, 0.95, 1.0))
        
        # Determine base color by height
        color = grass_color # Default
        if height < water_level:
            color = water_color
        elif height < beach_level:
            t = (height - water_level) / max(1e-6, beach_level - water_level)
            color = water_color * (1 - t) + beach_color * t
        elif height < grass_level:
            t = (height - beach_level) / max(1e-6, grass_level - beach_level)
            color = beach_color * (1 - t) + grass_color * t
        elif height < mountain_level:
            # Blend between grass and rock based on height and slope
            t_height = (height - grass_level) / max(1e-6, mountain_level - grass_level)
            t_slope = min(1.0, max(0.0, (slope - 0.3) / 0.5))
            t = max(t_height, t_slope)
            color = grass_color * (1 - t) + rock_color * t
        elif height < snow_level:
            t = (height - mountain_level) / max(1e-6, snow_level - mountain_level)
            color = rock_color * (1 - t) + snow_color * t
        else:
            color = snow_color
        
        # OPTIMIZATION: Skip biome variation to save calculations
        return Vec4(
            max(0, min(1, color[0])),
            max(0, min(1, color[1])),
            max(0, min(1, color[2])),
            1.0
        )
    
    def create_terrain_chunk(self, chunk_x, chunk_y):
        """Create a single terrain chunk at the specified chunk coordinates (X, Y)"""
        chunk_key = (chunk_x, chunk_y)
        if chunk_key in self.loaded_chunks:
            # Chunk already loaded
            return self.loaded_chunks[chunk_key]
        
        # Create a node for this chunk
        chunk_root = self.root_node.attachNewNode(f"terrain_chunk_{chunk_x}_{chunk_y}")
        
        # Convert chunk coordinates to world coordinates
        world_x_base = chunk_x * self.chunk_size
        world_y_base = chunk_y * self.chunk_size
        
        # Get mesh detail size
        mesh_size = self.terrain_settings.get('detail_mesh_size', 2.0)  # OPTIMIZED: Using larger segments
        
        # Calculate number of mesh segments in each direction
        mesh_segments = int(self.chunk_size / mesh_size)
        
        # Generate terrain mesh grid
        for i in range(mesh_segments):
            for j in range(mesh_segments):
                # Calculate world position for this mesh segment's corner
                x_pos = world_x_base + i * mesh_size
                y_pos = world_y_base + j * mesh_size

                # Calculate heights for the 4 corners of this mesh segment
                h_bl = self.calculate_terrain_height(x_pos, y_pos)
                h_br = self.calculate_terrain_height(x_pos + mesh_size, y_pos)
                h_tr = self.calculate_terrain_height(x_pos + mesh_size, y_pos + mesh_size)
                h_tl = self.calculate_terrain_height(x_pos, y_pos + mesh_size)

                # Store heights in the order expected by create_terrain_segment
                heights = [h_bl, h_br, h_tr, h_tl]

                # Skip creating mesh if all corners are deep underwater
                water_level = self.terrain_settings.get('water_level', -2.0)
                if all(h < water_level - 1.0 for h in heights):
                    continue
                
                # Create a terrain mesh segment
                segment = self.create_terrain_segment(
                    x_pos, y_pos, mesh_size,
                    heights,
                    f"terrain_mesh_{i}_{j}"
                )
                
                if segment:
                    segment.reparentTo(chunk_root)
                    self._set_geometry_collision(segment)
        
        # Store the chunk
        self.loaded_chunks[chunk_key] = chunk_root
        
        # Generate additional features if enabled
        if self.terrain_settings.get('generate_features', True):
            # OPTIMIZATION: Only generate features for central chunks to reduce load
            center_dist = math.sqrt(chunk_x**2 + chunk_y**2)
            if center_dist < self.view_distance - 1:
                self.generate_chunk_features(chunk_root, chunk_x, chunk_y)
        
        return chunk_root
    
    def create_terrain_segment(self, x, y, size, heights, name):
        """Create a single terrain mesh segment (XY plane) with the given corner heights"""
        # Create a simple plane (ensure it's XY)
        segment_geom = geometry_utils.create_procedural_plane(name, size)
        if not segment_geom:
            print(f"Failed to create plane geometry for {name}")
            return None

        # Position the segment node at the center of the base square in XY plane, height 0
        segment_node = NodePath(f"segment_node_{name}")
        segment_node.setPos(x + size / 2, y + size / 2, 0)
        segment_geom.reparentTo(segment_node)

        # Get vertex data to modify heights
        geom_node = segment_geom.node()
        if geom_node.getNumGeoms() == 0:
             print(f"Error: No geoms found in {name}")
             segment_node.removeNode()
             return None

        geom = geom_node.modifyGeom(0)
        vdata = geom.modifyVertexData()
        
        # Get a vertex writer for position
        vertex = GeomVertexWriter(vdata, 'vertex')
        
        # Update heights of the 4 corners (relative to the node's origin)
        # Assumes vertex order from create_procedural_plane: BL, BR, TR, TL
        h_bl, h_br, h_tr, h_tl = heights

        if vdata.getNumRows() >= 4:
            vertex.setRow(0) # Bottom-Left
            vertex.setData3f(-size / 2, -size / 2, h_bl)
            
            vertex.setRow(1) # Bottom-Right
            vertex.setData3f( size / 2, -size / 2, h_br)
            
            vertex.setRow(2) # Top-Right
            vertex.setData3f( size / 2,  size / 2, h_tr)
            
            vertex.setRow(3) # Top-Left
            vertex.setData3f(-size / 2,  size / 2, h_tl)
        else:
            print(f"Error: Not enough vertices ({vdata.getNumRows()}) in {name}")
            segment_node.removeNode()
            return None

        # Calculate average height and position for coloring
        avg_height = sum(heights) / 4.0
        avg_x = x + size/2
        avg_y = y + size/2
        
        # Set color based on height and other factors (OPTIMIZED: faster color calculation)
        color = self.get_terrain_color(avg_x, avg_y, avg_height)
        segment_geom.setColor(color)

        # OPTIMIZATION: More efficient normal calculation
        normal_rewriter = GeomVertexRewriter(vdata, 'normal')
        
        # Calculate two edges of the quad
        v1 = Vec3(size, 0, h_br - h_bl)  # Edge from BL to BR
        v2 = Vec3(0, size, h_tl - h_bl)  # Edge from BL to TL
        
        # Cross product gives the normal
        normal = v1.cross(v2)
        normal.normalize()
        
        # Apply the normal to all vertices (OPTIMIZATION: Only update if needed)
        try:
            for i in range(vdata.getNumRows()):
                normal_rewriter.setRow(i)
                normal_rewriter.setData3f(normal)
        except Exception as e:
            # Fallback if normal writing fails
            print(f"Warning: Normal writing failed: {e}, continuing without normal update")

        return segment_node
    
    def generate_chunk_features(self, chunk_root, chunk_x, chunk_y):
        """Generate additional features like rocks, trees, etc. in a chunk"""
        # OPTIMIZATION: Skip feature generation for distant chunks
        center_dist = math.sqrt(chunk_x**2 + chunk_y**2)
        if center_dist > self.view_distance - 1:
            return  # Skip features for distant chunks
        
        world_x_base = chunk_x * self.chunk_size
        world_y_base = chunk_y * self.chunk_size
        
        # Seeds for consistent feature placement
        feature_seed = self.terrain_settings.get('seed', 0) + chunk_x * 1000 + chunk_y
        random.seed(feature_seed)
        
        # OPTIMIZATION: Reduced feature density
        density = self.terrain_settings.get('feature_density', 0.01)  # Lower density
        expected_features = int(self.chunk_size * self.chunk_size * density)
        
        # Generate features
        for i in range(expected_features):
            # Random position within chunk
            x_offset = random.uniform(0, self.chunk_size)
            y_offset = random.uniform(0, self.chunk_size)
            
            x_pos = world_x_base + x_offset
            y_pos = world_y_base + y_offset
            
            # Get height at this position
            height = self.calculate_terrain_height(x_pos, y_pos)
            
            # Skip if underwater or too steep
            water_level = self.terrain_settings.get('water_level', -2.0)
            if height <= water_level:
                continue
                
            # Sample heights around to check slope
            sample_dist = 0.5
            h_px = self.calculate_terrain_height(x_pos + sample_dist, y_pos)
            h_nx = self.calculate_terrain_height(x_pos - sample_dist, y_pos)
            h_py = self.calculate_terrain_height(x_pos, y_pos + sample_dist)
            h_ny = self.calculate_terrain_height(x_pos, y_pos - sample_dist)
            
            slope_x = (h_px - h_nx) / (2 * sample_dist)
            slope_y = (h_py - h_ny) / (2 * sample_dist)
            slope = math.sqrt(slope_x**2 + slope_y**2)
            
            # Skip if slope is too steep for features
            if slope > 0.7:
                continue
    
    def update_visible_chunks(self, player_pos):
        """Update which chunks are visible based on player position"""
        if player_pos is None: return

        # Convert player position to chunk coordinates (Using X and Y)
        chunk_x = int(math.floor(player_pos.x / self.chunk_size))
        chunk_y = int(math.floor(player_pos.y / self.chunk_size))

        # Skip if player hasn't moved to a new chunk
        if self.current_center_chunk == (chunk_x, chunk_y):
            return
            
        self.current_center_chunk = (chunk_x, chunk_y)
        
        # Calculate chunks that should be visible
        visible_chunks = set()
        for x in range(chunk_x - self.view_distance, chunk_x + self.view_distance + 1):
            for y in range(chunk_y - self.view_distance, chunk_y + self.view_distance + 1):
                # Check if chunk is within view distance (circular)
                dist_sq = (x - chunk_x)**2 + (y - chunk_y)**2
                if dist_sq <= self.view_distance**2:
                    visible_chunks.add((x, y))
        
        # Find chunks to unload (currently loaded but not visible)
        chunks_to_unload = set(self.loaded_chunks.keys()) - visible_chunks
        
        # Unload chunks
        for chunk_key in chunks_to_unload:
            if chunk_key in self.loaded_chunks:
                chunk_node = self.loaded_chunks.pop(chunk_key)
                if chunk_node and not chunk_node.isEmpty():
                    chunk_node.removeNode()
        
        # Load new visible chunks (OPTIMIZATION: Prioritize loading closest chunks first)
        chunk_distances = []
        for chunk_key in visible_chunks:
            if chunk_key not in self.loaded_chunks:
                x, y = chunk_key
                dist_sq = (x - chunk_x)**2 + (y - chunk_y)**2
                chunk_distances.append((dist_sq, chunk_key))
        
        # Sort by distance (closest first)
        chunk_distances.sort()
        for _, chunk_key in chunk_distances:
            self.create_terrain_chunk(*chunk_key)

    def generate_terrain_and_features(self):
        """Initial terrain generation centered at origin"""
        print("Generating initial terrain chunks with noise-based height map...")
        
        # Fallback: Generate initial grid manually if update doesn't run first
        if not self.current_center_chunk:
            print("Generating fallback initial grid...")
            # OPTIMIZATION: Generate only essential chunks at first
            for x in range(-self.view_distance, self.view_distance + 1):
                for y in range(-self.view_distance, self.view_distance + 1):
                    # Check if within view distance from origin
                    dist_sq = x**2 + y**2
                    if dist_sq <= self.view_distance**2:
                        self.create_terrain_chunk(x, y)
            self.current_center_chunk = (0, 0)

        print("Initial terrain generation complete.")

    def cleanup(self):
        print("Cleaning up TerrainGenerator...")
        
        # Stop all animations
        for interval in self.animating_intervals:
            if interval and hasattr(interval, 'finish') and callable(interval.finish):
                interval.finish()
        self.animating_intervals.clear()
        
        # Remove all loaded chunks
        chunk_keys = list(self.loaded_chunks.keys())
        for chunk_key in chunk_keys:
            chunk_node = self.loaded_chunks.pop(chunk_key, None)
            if chunk_node and not chunk_node.isEmpty():
                chunk_node.removeNode()
        self.loaded_chunks.clear()
        
        # Remove other static elements
        static_elems = list(self.static_elements)
        for element_np in reversed(static_elems):
            if element_np and not element_np.isEmpty():
                element_np.removeNode()
        self.static_elements.clear()

        # Clear height cache
        self.height_cache.clear()
        
        print("TerrainGenerator cleanup complete.")