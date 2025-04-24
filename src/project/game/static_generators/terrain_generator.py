import random
import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, BitMask32, TransparencyAttrib, ColorBlendAttrib
)
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval, LerpColorScaleInterval, Wait
from ...utils import geometry_utils

def _rand_uniform(range_list):
    if not isinstance(range_list, list) or len(range_list) != 2: return random.uniform(0, 1)
    return random.uniform(range_list[0], range_list[1])

def _rand_int(range_list):
    if not isinstance(range_list, list) or len(range_list) != 2: return random.randint(0, 1)
    try: return random.randint(int(range_list[0]), int(range_list[1]))
    except ValueError: return random.randint(0, 1)

class TerrainGenerator:
    """Generates the terrain mesh and related features like islands and pillars."""
    def __init__(self, app, root_node, settings_manager, palette, proc_gen_consts, collision_consts, **kwargs):
        self.app = app
        self.render = app.render
        self.root_node = root_node
        self.settings_manager = settings_manager
        self.palette = palette
        self.proc_gen_consts = proc_gen_consts
        self.collision_consts = collision_consts
        self.env_consts = settings_manager.constants.get('environment', {})

        self.static_elements = []
        self.animating_intervals = []

    def _get_palette_color(self, key, default=Vec4(1,1,1,1)):
       return self.settings_manager.get_palette_color(key, default)

    def _get_proc_const(self, keys, default=None):
        current = self.proc_gen_consts
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else: return default
            if current is None: return default
        return current

    def _set_geometry_collision(self, node_path):
        mask_ground = self.collision_consts.get('MASK_GROUND', BitMask32(1))
        node_path.setCollideMask(mask_ground)

    def calculate_terrain_height(self, nx, ny):
        height = 0
        height += 2.5 * math.sin(nx * 2.5) * math.cos(ny * 2.0)
        height += 1.8 * math.sin(nx * 4.0 + 0.5) * math.sin(ny * 3.5)
        height += 0.9 * math.cos(nx * 8.0) * math.sin(ny * 9.0)
        dist_from_center = math.sqrt(nx*nx + ny*ny)
        flatten_factor = 1.0 - min(1.0, dist_from_center * 1.5)**2
        height *= flatten_factor
        edge_start_norm = 0.8
        edge_width_norm = 0.15
        edge_drop_factor = 8.0
        edge_exponent = 1.5
        if dist_from_center > edge_start_norm:
            edge_factor = min(1.0, (dist_from_center - edge_start_norm) / max(0.01, edge_width_norm))**edge_exponent
            height -= edge_factor * edge_drop_factor
        return height

    def generate_terrain_and_features(self):
        print("Generating terrain and features...")
        terrain_root = self.root_node.attachNewNode("terrain_root")
        terrain_size = self.env_consts.get('TERRAIN_SIZE', 200.0)
        grid_size = self.env_consts.get('TERRAIN_GRID_SIZE', 15)
        segment_size = terrain_size / max(1, grid_size)

        feature_consts = self._get_proc_const(['terrain_features'], {})
        min_h = feature_consts.get('terrain_min_height', -5.0)
        max_h = feature_consts.get('terrain_max_height', 5.0)
        island_h_thresh = feature_consts.get('island_height_threshold', -1.0)
        island_prob_base = feature_consts.get('island_probability_base', 0.3)
        island_prob_dist = feature_consts.get('island_probability_dist_factor', 0.3)
        crystal_h_thresh = feature_consts.get('crystal_height_threshold', 0.0)
        crystal_prob = feature_consts.get('crystal_probability', 0.08)
        color_thresh1 = feature_consts.get('terrain_color_low_mid_threshold', 0.33)
        color_thresh2 = feature_consts.get('terrain_color_mid_high_threshold', 0.66)

        for x_idx in range(-grid_size, grid_size + 1):
            for y_idx in range(-grid_size, grid_size + 1):
                x_pos = x_idx * segment_size
                y_pos = y_idx * segment_size
                nx = x_idx / grid_size if grid_size != 0 else 0
                ny = y_idx / grid_size if grid_size != 0 else 0
                height = self.calculate_terrain_height(nx, ny)
                world_pos = Point3(x_pos, y_pos, height)

                rand_val = random.random()
                dist_from_center = math.sqrt(nx**2 + ny**2)

                island_probability = island_prob_base + dist_from_center * island_prob_dist
                if height < island_h_thresh and rand_val < island_probability:
                    self._create_floating_island(terrain_root, world_pos, (x_idx * 100 + y_idx))
                elif height > crystal_h_thresh and rand_val < crystal_prob:
                    self._create_crystal_pillar(terrain_root, world_pos, (x_idx * 100 + y_idx))
                elif height > min_h:
                    segment = geometry_utils.create_procedural_plane(
                        name=f"terrain_{x_idx}_{y_idx}", size=segment_size
                    )
                    if not segment: continue
                    segment.reparentTo(terrain_root)
                    segment.setPos(world_pos)

                    color_ratio = max(0, min(1, (height - min_h) / max(0.1, max_h - min_h)))
                    if color_ratio < color_thresh1:
                        color = self._get_palette_color('terrain_low')
                    elif color_ratio < color_thresh2:
                        color1 = self._get_palette_color('terrain_low')
                        color2 = self._get_palette_color('terrain_mid')
                        lerp_ratio = (color_ratio - color_thresh1) / max(0.01, color_thresh2 - color_thresh1)
                        color = color1 + (color2 - color1) * lerp_ratio
                    else:
                        color1 = self._get_palette_color('terrain_mid')
                        color2 = self._get_palette_color('terrain_high')
                        lerp_ratio = (color_ratio - color_thresh2) / max(0.01, 1.0 - color_thresh2)
                        color = color1 + (color2 - color1) * lerp_ratio
                    segment.setColor(color)
                    self._set_geometry_collision(segment)
                    self.static_elements.append(segment)

        self.static_elements.append(terrain_root)
        print("Terrain and features generation complete.")

    def _create_floating_island(self, parent_node, pos, index):
        island_consts = self._get_proc_const(['floating_island'], {})
        island_root = parent_node.attachNewNode(f"island_{index}")
        island_root.setPos(pos)

        base_segments = island_consts.get('base_segments', 8)
        base_shape = geometry_utils.create_procedural_sphere(f"island_base_{index}", radius=1.0, segments=base_segments)
        if not base_shape:
            island_root.removeNode(); return
        base_shape.reparentTo(island_root)

        scale_xy_range = island_consts.get('base_scale_xy_range', [4.0, 10.0])
        scale_z_range = island_consts.get('base_scale_z_range', [1.5, 4.0])
        sx, sy, sz = _rand_uniform(scale_xy_range), _rand_uniform(scale_xy_range), _rand_uniform(scale_z_range)
        base_shape.setScale(sx, sy, sz)

        feature_consts = self._get_proc_const(['terrain_features'], {})
        min_h = feature_consts.get('terrain_min_height', -5.0)
        max_h = feature_consts.get('terrain_max_height', 5.0)
        color_ratio = max(0, min(1, (pos.z - min_h) / max(0.1, max_h - min_h)))
        color = self._get_palette_color('terrain_low') + (self._get_palette_color('terrain_mid') - self._get_palette_color('terrain_low')) * color_ratio
        base_shape.setColor(color * 0.9)
        self._set_geometry_collision(base_shape)

        shard_prob = island_consts.get('shard_probability', 0.4)
        if random.random() < shard_prob:
             shard_count_range = island_consts.get('shard_count_range', [1, 3])
             num_shards = _rand_int(shard_count_range)
             shard_scale_base_range = island_consts.get('shard_scale_base_range', [0.3, 1.0])
             shard_scale_h_range = island_consts.get('shard_scale_height_range', [1.5, 3.0])
             shard_pos_factor = island_consts.get('shard_pos_factor', 0.333)
             shard_h_range = island_consts.get('shard_hpr_h_range', [0.0, 360.0])
             shard_p_range = island_consts.get('shard_hpr_p_range', [-15.0, 15.0])

             for i in range(num_shards):
                 shard = geometry_utils.create_procedural_cube(f"island_shard_{index}_{i}")
                 if shard:
                     shard.reparentTo(island_root)
                     shard_scale_base = _rand_uniform(shard_scale_base_range)
                     shard_scale_h = _rand_uniform(shard_scale_h_range)
                     shard.setScale(shard_scale_base * 0.5, shard_scale_base * 0.5, shard_scale_base * shard_scale_h)
                     shard_pos_x = random.uniform(-sx * shard_pos_factor, sx * shard_pos_factor)
                     shard_pos_y = random.uniform(-sy * shard_pos_factor, sy * shard_pos_factor)
                     shard.setPos(shard_pos_x, shard_pos_y, sz * 0.5 + shard.getScale().z * 0.5)
                     shard.setHpr(_rand_uniform(shard_h_range), _rand_uniform(shard_p_range), 0)
                     base_crystal_color = self._get_palette_color('crystal')
                     final_shard_color = Vec4(base_crystal_color.getX(),
                                             base_crystal_color.getZ(),
                                             base_crystal_color.getY(),
                                             base_crystal_color.getW() * 0.8)
                     shard.setColor(final_shard_color)
                     shard.setTransparency(TransparencyAttrib.MAlpha)
                     shard.setCollideMask(BitMask32(0))
                     self.static_elements.append(shard)

        float_h_range = island_consts.get('float_height_range', [0.5, 2.0])
        float_dur_range = island_consts.get('float_duration_range', [8.0, 15.0])
        float_height = _rand_uniform(float_h_range)
        duration = _rand_uniform(float_dur_range)
        end_pos = Point3(pos.x, pos.y, pos.z + float_height)
        pos_seq = Sequence(
            LerpPosInterval(island_root, duration / 2, end_pos, startPos=pos, blendType='easeInOut'),
            LerpPosInterval(island_root, duration / 2, pos, startPos=end_pos, blendType='easeInOut'),
            name=f"island_float_{index}"
        )
        pos_seq.loop()
        self.animating_intervals.append(pos_seq)
        self.static_elements.append(island_root)


    def _create_crystal_pillar(self, parent_node, pos, index):
        pillar_consts = self._get_proc_const(['crystal_pillar'], {})
        pillar = geometry_utils.create_procedural_cube(f"crystal_{index}")
        if not pillar: return
        pillar.reparentTo(parent_node)

        height_range = pillar_consts.get('height_range', [10.0, 30.0])
        width_range = pillar_consts.get('width_range', [0.5, 2.5])
        h_range = pillar_consts.get('hpr_h_range', [0.0, 360.0])
        height = _rand_uniform(height_range)
        width = _rand_uniform(width_range)
        pillar.setScale(width, width, height)
        pillar.setPos(pos + Point3(0,0,height/2))
        pillar.setHpr(_rand_uniform(h_range), 0, 0)

        color = self._get_palette_color('crystal')
        pillar.setColorScale(color.getX(), color.getY(), color.getZ(), color.getW())
        pillar.setTransparency(TransparencyAttrib.MAlpha)
        pillar.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd,
                                               ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))

        glow_prob = pillar_consts.get('glow_probability', 0.5)
        if random.random() < glow_prob:
            glow_mult = pillar_consts.get('glow_scale_multiplier', 1.5)
            glow_dur_range = pillar_consts.get('glow_duration_range', [4.0, 8.0])
            glow_wait_range = pillar_consts.get('glow_wait_range', [1.0, 3.0])

            base_scale = Vec4(color.getX(), color.getY(), color.getZ(), color.getW())
            target_scale = base_scale * glow_mult
            target_scale.setW(base_scale.getW())
            duration = _rand_uniform(glow_dur_range)
            wait_time = _rand_uniform(glow_wait_range)

            glow_ival = Sequence(
                LerpColorScaleInterval(pillar, duration/2, target_scale, startColorScale=base_scale, blendType='easeInOut'),
                LerpColorScaleInterval(pillar, duration/2, base_scale, startColorScale=target_scale, blendType='easeInOut'),
                Wait(wait_time),
                name=f"crystal_glow_{index}"
            )
            glow_ival.loop()
            self.animating_intervals.append(glow_ival)

        self._set_geometry_collision(pillar)
        self.static_elements.append(pillar)

    def cleanup(self):
        print("Cleaning up TerrainGenerator...")
        for interval in self.animating_intervals:
            if interval and hasattr(interval, 'finish') and callable(interval.finish):
                interval.finish()
        self.animating_intervals.clear()

        for element_np in reversed(self.static_elements):
            if element_np and not element_np.isEmpty():
                element_np.removeNode()
        self.static_elements.clear()
        print("TerrainGenerator cleanup complete.")