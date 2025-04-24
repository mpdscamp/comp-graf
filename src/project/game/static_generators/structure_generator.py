import random
import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, BitMask32, TransparencyAttrib,
    ColorBlendAttrib, PointLight
)
from direct.interval.IntervalGlobal import (
    Sequence, LerpPosInterval, LerpHprInterval, LerpColorScaleInterval,
    LerpScaleInterval, Wait, Func
)
from ...utils import geometry_utils

def _rand_uniform(range_list):
    if not isinstance(range_list, list) or len(range_list) != 2: return random.uniform(0, 1)
    return random.uniform(range_list[0], range_list[1])

def _rand_int(range_list):
    if not isinstance(range_list, list) or len(range_list) != 2: return random.randint(0, 1)
    try: return random.randint(int(range_list[0]), int(range_list[1]))
    except ValueError: return random.randint(0, 1)

class StructureGenerator:
    """Generates static structures like platforms, sculptures, formations."""
    def __init__(self, app, root_node, settings_manager, palette, proc_geom_consts,
                 proc_gen_consts, collision_consts, terrain_generator, **kwargs):
        self.app = app
        self.render = app.render
        self.root_node = root_node
        self.settings_manager = settings_manager
        self.palette = palette
        self.proc_geom_consts = proc_geom_consts
        self.proc_gen_consts = proc_gen_consts
        self.collision_consts = collision_consts
        self.terrain_generator = terrain_generator
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

    def _get_terrain_height(self, nx, ny):
        if self.terrain_generator:
            return self.terrain_generator.calculate_terrain_height(nx, ny)
        return 0

    def populate_structures(self):
        print("Populating static structures (Using Settings)...")
        struct_consts = self._get_proc_const(['static_structures'], {})
        num_platforms = struct_consts.get('platform_count', 12)
        num_sculptures = struct_consts.get('sculpture_count', 15)
        spawn_factor = struct_consts.get('spawn_area_factor', 0.45)
        spawn_h_thresh = struct_consts.get('spawn_height_threshold', -2.0)
        plat_z_range = struct_consts.get('platform_z_offset_range', [10.0, 40.0])
        sculpt_z_range = struct_consts.get('sculpture_z_offset_range', [0.5, 2.0])
        col_radius = struct_consts.get('column_formation_radius', 50.0)
        col_count = struct_consts.get('column_formation_count', 9)

        valid_spawn_points = []
        terrain_size = self.env_consts.get('TERRAIN_SIZE', 200.0)
        half_terrain = terrain_size * 0.5
        spawn_radius = half_terrain * spawn_factor

        for _ in range((num_platforms + num_sculptures) * 5):
             x = random.uniform(-spawn_radius, spawn_radius)
             y = random.uniform(-spawn_radius, spawn_radius)
             nx = x / half_terrain if half_terrain else 0
             ny = y / half_terrain if half_terrain else 0
             height = self._get_terrain_height(nx, ny)
             if height > spawn_h_thresh:
                 valid_spawn_points.append(Point3(x, y, height))

        random.shuffle(valid_spawn_points)

        for i in range(min(num_platforms, len(valid_spawn_points))):
            z_offset = _rand_uniform(plat_z_range)
            spawn_pos = valid_spawn_points.pop(0)
            self._create_platform(spawn_pos + Point3(0,0,z_offset), i)

        points_needed = min(num_sculptures, len(valid_spawn_points))
        for i in range(points_needed):
            spawn_pos = valid_spawn_points.pop(0)
            z_offset = _rand_uniform(sculpt_z_range)
            self._create_abstract_sculpture(spawn_pos + Point3(0,0,z_offset), i)

        self._create_column_formation(radius=col_radius, num_columns=col_count)
        self._create_central_structure()
        print("Static structures populated.")

    def _create_platform(self, pos, index):
        plat_consts = self._get_proc_const(['platform'], {})
        platform_root = self.root_node.attachNewNode(f"platform_{index}")
        platform_root.setPos(pos)
        platform_base = geometry_utils.create_procedural_cube(f"platform_base_{index}")
        if not platform_base:
             platform_root.removeNode(); return None

        platform_base.reparentTo(platform_root)
        width_range = plat_consts.get('width_range', [6.0, 15.0])
        depth_range = plat_consts.get('depth_range', [6.0, 15.0])
        height_range = plat_consts.get('height_range', [1.0, 2.5])
        width = _rand_uniform(width_range)
        depth = _rand_uniform(depth_range)
        height = _rand_uniform(height_range)
        platform_base.setScale(width, depth, height)

        base_color = random.choice([self._get_palette_color('structure_primary'),
                                    self._get_palette_color('structure_secondary')])
        platform_base.setColor(base_color)
        self._set_geometry_collision(platform_base)

        float_h_range = plat_consts.get('float_height_range', [1.0, 3.0])
        float_dur_range = plat_consts.get('float_duration_range', [10.0, 18.0])
        float_height = _rand_uniform(float_h_range)
        duration = _rand_uniform(float_dur_range)
        end_pos = pos + Point3(0,0,float_height)
        pos_seq = Sequence(
             LerpPosInterval(platform_root, duration / 2, end_pos, startPos=pos, blendType='easeInOut'),
             LerpPosInterval(platform_root, duration / 2, pos, startPos=end_pos, blendType='easeInOut'),
             name=f"platform_move_{index}"
        )
        pos_seq.loop()
        self.animating_intervals.append(pos_seq)

        self.static_elements.append(platform_root)
        return platform_root

    def _create_abstract_sculpture(self, pos, index):
        sculpt_consts_base = self._get_proc_const(['abstract_sculpture'], {})
        sculpture_root = self.root_node.attachNewNode(f"sculpture_{index}")
        sculpture_root.setPos(pos)
        available_types = [k for k in sculpt_consts_base.keys() if isinstance(sculpt_consts_base[k], dict)]
        if not available_types:
            print("Warning: No abstract sculpture types defined in settings.")
            sculpture_root.removeNode()
            return None
        sculpture_type = random.choice(available_types)
        sculpt_consts = sculpt_consts_base.get(sculpture_type, {})

        sphere_segments = self.proc_geom_consts.get('SPHERE_SEGMENTS', 12)
        primary_color = self._get_palette_color('structure_primary')
        secondary_color = self._get_palette_color('structure_secondary')
        accent_color = self._get_palette_color('accent_glow')
        crystal_color = self._get_palette_color('crystal')

        if sculpture_type == 'stacked':
             count_range = sculpt_consts.get('element_count_range', [4, 8])
             base_scale_range = sculpt_consts.get('base_scale_range', [2.0, 4.0])
             scale_reduct_factor = sculpt_consts.get('scale_reduction_factor', 0.8)
             pos_jitter_range = sculpt_consts.get('position_jitter_range', [-0.2, 0.2])
             rot_prob = sculpt_consts.get('rotation_probability', 0.3)
             rot_dur_range = sculpt_consts.get('rotation_duration_range', [20.0, 40.0])

             current_height = 0
             num_elements = _rand_int(count_range)
             base_scale = _rand_uniform(base_scale_range)
             colors = [primary_color, secondary_color]
             for i in range(num_elements):
                 shape_key = random.choice(['cube', 'sphere'])
                 element = geometry_utils.get_procedural_shape(
                     shape_key, f"sculpt_stack_{index}_{i}",
                     segments=sphere_segments if shape_key == 'sphere' else None
                 )
                 if not element: continue
                 element.reparentTo(sculpture_root)
                 scale_factor = base_scale * (1.0 - (i / max(1, num_elements)) * scale_reduct_factor)
                 element.setScale(scale_factor * random.uniform(0.9, 1.1))
                 element.setPos(_rand_uniform(pos_jitter_range),
                                _rand_uniform(pos_jitter_range),
                                current_height + element.getBounds().getRadius() * 0.8)
                 current_height += element.getBounds().getRadius() * 1.5
                 element.setHpr(0, 0, 0)
                 element.setColor(colors[i % len(colors)])
                 self._set_geometry_collision(element); self.static_elements.append(element)
                 if i > 0 and random.random() < rot_prob:
                     duration = _rand_uniform(rot_dur_range)
                     hpr_seq = LerpHprInterval(element, duration, Vec3(0, 0, 360), startHpr=Vec3(0,0,0), name=f"sculpt_stack_rot_{index}_{i}")
                     hpr_seq.loop()
                     self.animating_intervals.append(hpr_seq)

        elif sculpture_type == 'sphere_cluster':
             center_z_range = sculpt_consts.get('center_z_range', [1.0, 3.0])
             orb_count_range = sculpt_consts.get('orb_count_range', [6, 15])
             rad_base = sculpt_consts.get('placement_radius_base', 0.5)
             rad_exp = sculpt_consts.get('placement_radius_exponent', 1.5)
             rad_max_f = sculpt_consts.get('placement_radius_max_factor', 2.5)
             size_range = sculpt_consts.get('size_range', [0.2, 0.8])
             pulse_mult_range = sculpt_consts.get('pulse_scale_multiplier_range', [1.3, 1.8])
             pulse_dur_range = sculpt_consts.get('pulse_duration_range', [3.0, 7.0])
             pulse_wait_range = sculpt_consts.get('pulse_wait_range', [0.5, 2.0])

             center_pos = Point3(0,0, _rand_uniform(center_z_range))
             num_orbs = _rand_int(orb_count_range)
             for i in range(num_orbs):
                 sphere = geometry_utils.create_procedural_sphere(f"sculpt_cluster_{index}_{i}", segments=8)
                 if not sphere: continue
                 sphere.reparentTo(sculpture_root)
                 radius = (rad_base + random.random() * (rad_max_f - rad_base))**rad_exp
                 phi, theta = random.uniform(0, 2*math.pi), random.uniform(0, math.pi)
                 pos_offset = Point3(radius*math.sin(theta)*math.cos(phi),
                                     radius*math.sin(theta)*math.sin(phi),
                                     radius*math.cos(theta))
                 sphere.setPos(center_pos + pos_offset)
                 size = _rand_uniform(size_range)
                 sphere.setScale(size)
                 sphere.setColorScale(accent_color.getX(), accent_color.getY(), accent_color.getZ(), 0.8)
                 sphere.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
                 sphere.setTransparency(TransparencyAttrib.MAlpha)
                 sphere.setLightOff()
                 sphere.setCollideMask(BitMask32(0))
                 self.static_elements.append(sphere)
                 base_scale = sphere.getColorScale()
                 target_scale = base_scale * _rand_uniform(pulse_mult_range)
                 target_scale.setW(base_scale.getW())
                 duration = _rand_uniform(pulse_dur_range)
                 wait_time = _rand_uniform(pulse_wait_range)
                 pulse_ival = Sequence(
                     LerpColorScaleInterval(sphere, duration/2, target_scale, startColorScale=base_scale, blendType='easeInOut'),
                     LerpColorScaleInterval(sphere, duration/2, base_scale, startColorScale=target_scale, blendType='easeInOut'),
                     Wait(wait_time),
                     name=f"sculpt_orb_pulse_{index}_{i}"
                 )
                 pulse_ival.loop()
                 self.animating_intervals.append(pulse_ival)

        elif sculpture_type == 'rings':
             count_range = sculpt_consts.get('count_range', [3, 5])
             max_rad_range = sculpt_consts.get('max_radius_range', [4.0, 7.0])
             rad_reduct_factor = sculpt_consts.get('radius_reduction_factor', 0.4)
             seg_count_factor = sculpt_consts.get('segment_count_factor', 8.0)
             seg_scale_range = sculpt_consts.get('segment_scale_range', [0.2, 0.4])
             rot_hpr_range = sculpt_consts.get('rotation_hpr_range', [-15.0, 15.0])
             rot_dur_range = sculpt_consts.get('rotation_duration_range', [15.0, 35.0])

             num_rings = _rand_int(count_range)
             max_radius = _rand_uniform(max_rad_range)
             colors = [primary_color, secondary_color]
             for i in range(num_rings):
                 ring_root = sculpture_root.attachNewNode(f"sculpture_ring_{index}_{i}")
                 ring_root.setPos(0, 0, i * 2.5 + 1)
                 ring_root.setHpr(_rand_uniform(rot_hpr_range),
                                  _rand_uniform(rot_hpr_range),
                                  _rand_uniform(rot_hpr_range))

                 ring_radius = max_radius * (1 - i / max(1, num_rings) * rad_reduct_factor)
                 num_segments = max(8, int(seg_count_factor * ring_radius))
                 segment_scale = _rand_uniform(seg_scale_range)
                 for j in range(num_segments):
                     angle = j * (2 * math.pi / num_segments)
                     x, y = ring_radius * math.cos(angle), ring_radius * math.sin(angle)
                     segment = geometry_utils.create_procedural_cube(f"sculpt_ring_seg_{index}_{i}_{j}")
                     if not segment: continue
                     segment.reparentTo(ring_root); segment.setPos(x, y, 0)
                     segment.setScale(segment_scale); segment.lookAt(Point3(0,0,0))
                     segment.setColor(colors[i % len(colors)])
                     self._set_geometry_collision(segment); self.static_elements.append(segment)

                 duration = _rand_uniform(rot_dur_range) * random.choice([-1, 1])
                 start_hpr = ring_root.getHpr()
                 end_hpr = Vec3(start_hpr.x, start_hpr.y, start_hpr.z + 360*math.copysign(1, duration))
                 hpr_seq = LerpHprInterval(ring_root, abs(duration), end_hpr, startHpr=start_hpr, name=f"sculpt_ring_rot_{index}_{i}")
                 hpr_seq.loop()
                 self.animating_intervals.append(hpr_seq)
                 self.static_elements.append(ring_root)

        elif sculpture_type == 'crystal_growth':
             count_range = sculpt_consts.get('count_range', [5, 12])
             base_z = sculpt_consts.get('base_pos_z', 0.1)
             dist_base = sculpt_consts.get('placement_dist_base', 0.0)
             dist_exp = sculpt_consts.get('placement_dist_exponent', 1.5)
             dist_max_f = sculpt_consts.get('placement_dist_max_factor', 3.0)
             place_z_factor = sculpt_consts.get('placement_z_factor', 2.0)
             h_base = sculpt_consts.get('height_base', 1.0)
             h_range = sculpt_consts.get('height_range', [1.0, 5.0])
             h_dist_factor = sculpt_consts.get('height_dist_factor', 0.2)
             w_base = sculpt_consts.get('width_base', 0.1)
             w_range = sculpt_consts.get('width_range', [0.2, 0.8])
             w_dist_factor = sculpt_consts.get('width_dist_factor', 0.25)
             lookat_jitter = sculpt_consts.get('lookat_jitter_range', [-1.0, 1.0])
             alpha_range = sculpt_consts.get('alpha_scale_range', [0.6, 0.9])

             num_crystals = _rand_int(count_range)
             base_pos = Point3(0,0,base_z)
             for i in range(num_crystals):
                 crystal = geometry_utils.create_procedural_cube(f"sculpt_crystal_{index}_{i}")
                 if not crystal: continue
                 crystal.reparentTo(sculpture_root)
                 dist = (dist_base + random.random() * (dist_max_f - dist_base))**dist_exp
                 angle = random.uniform(0, 2*math.pi)
                 c_pos = base_pos + Point3(dist * math.cos(angle),
                                           dist * math.sin(angle),
                                           random.uniform(0, dist * place_z_factor))
                 c_height = (h_base + _rand_uniform(h_range)) * (1.0 + dist * h_dist_factor)
                 c_width = max(w_base, (_rand_uniform(w_range)) * (1.0 - dist * w_dist_factor))
                 crystal.setScale(c_width, c_width, c_height)
                 crystal.setPos(c_pos + Point3(0,0,c_height/2))
                 crystal.lookAt(base_pos + Point3(_rand_uniform(lookat_jitter),
                                                  _rand_uniform(lookat_jitter),0))
                 crystal.setColorScale(crystal_color.getX(), crystal_color.getY(), crystal_color.getZ(),
                                       _rand_uniform(alpha_range))
                 crystal.setTransparency(TransparencyAttrib.MAlpha)
                 self._set_geometry_collision(crystal)
                 self.static_elements.append(crystal)

        self.static_elements.append(sculpture_root)
        return sculpture_root

    def _create_column_formation(self, radius=50, num_columns=9):
        form_consts = self._get_proc_const(['column_formation'], {})
        formation_root = self.root_node.attachNewNode("column_formation")
        terrain_size = self.env_consts.get('TERRAIN_SIZE', 200.0)
        half_terrain = terrain_size * 0.5
        primary_color = self._get_palette_color('structure_primary')
        secondary_color = self._get_palette_color('structure_secondary')

        rad_jitter_range = form_consts.get('radius_jitter_range', [0.9, 1.1])
        ang_jitter_range = form_consts.get('angle_jitter_range', [-0.1, 0.1])
        segments = form_consts.get('segments', 12)
        height_range = form_consts.get('height_range', [12.0, 30.0])
        width_range = form_consts.get('width_range', [1.2, 2.8])
        glow_prob = form_consts.get('glow_probability', 0.4)
        glow_dur_range = form_consts.get('glow_duration_range', [5.0, 10.0])
        glow_int_range = form_consts.get('glow_intensity_range', [0.2, 0.5])
        glow_fade_in_f = form_consts.get('glow_fade_in_factor', 0.1)
        glow_fade_out_f = form_consts.get('glow_fade_out_factor', 0.4)
        glow_wait_f = form_consts.get('glow_wait_factor', 0.5)

        for i in range(num_columns):
            angle = i * (2 * math.pi / num_columns) + _rand_uniform(ang_jitter_range)
            current_radius = radius * _rand_uniform(rad_jitter_range)
            x = current_radius * math.cos(angle); y = current_radius * math.sin(angle)
            nx = x / half_terrain if half_terrain else 0
            ny = y / half_terrain if half_terrain else 0
            ground_height = self._get_terrain_height(nx, ny)

            column = geometry_utils.create_procedural_cylinder(f"column_{i}", segments=segments)
            if not column: continue
            column.reparentTo(formation_root)
            column_height = _rand_uniform(height_range)
            column_width = _rand_uniform(width_range)
            column.setScale(column_width, column_width, column_height)
            column.setPos(x, y, ground_height + column_height / 2)
            column.setColor(primary_color if i % 2 == 0 else secondary_color)
            self._set_geometry_collision(column); self.static_elements.append(column)

            if random.random() < glow_prob:
                glow_color = self._get_palette_color('accent_glow')
                duration = _rand_uniform(glow_dur_range)
                intensity = _rand_uniform(glow_int_range)

                glow_node = column.attachNewNode(f"column_glow_effect_{i}")
                glow_node.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd,
                                                         ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
                glow_node.setTransparency(True)
                start_color_scale = Vec4(0,0,0,0)
                glow_node.setColorScale(start_color_scale)
                target_color_scale = Vec4(glow_color.getX()*intensity,
                                          glow_color.getY()*intensity,
                                          glow_color.getZ()*intensity,
                                          intensity*0.5)

                glow_ival = Sequence(
                    Wait(random.uniform(0, duration)),
                    LerpColorScaleInterval(glow_node, duration*glow_fade_in_f, target_color_scale, startColorScale=start_color_scale, blendType='easeIn'),
                    LerpColorScaleInterval(glow_node, duration*glow_fade_out_f, start_color_scale, startColorScale=target_color_scale, blendType='easeOut'),
                    Wait(duration*glow_wait_f),
                    name=f"column_glow_{i}"
                 )
                glow_ival.loop()
                self.animating_intervals.append(glow_ival)
                self.static_elements.append(glow_node)

        self.static_elements.append(formation_root)
        return formation_root

    def _create_central_structure(self):
        cs_consts = self._get_proc_const(['central_structure'], {})
        central_root = self.root_node.attachNewNode("central_structure")
        central_root.setPos(0, 0, 0)

        primary_color = self._get_palette_color('structure_primary')
        secondary_color = self._get_palette_color('structure_secondary')
        accent_color = self._get_palette_color('accent_glow')
        beam_color = self._get_palette_color('accent_beam')
        cyl_segments = self.proc_geom_consts.get('CYLINDER_SEGMENTS', 24)
        sphere_segments = self.proc_geom_consts.get('SPHERE_SEGMENTS', 24)

        base_radius = cs_consts.get('base_radius', 18.0)
        base_height = cs_consts.get('base_height', 1.5)
        base_seg_factor = cs_consts.get('base_segment_factor', 2)
        base_platform = geometry_utils.create_procedural_cylinder(
            "central_base", radius=base_radius, height=base_height, segments=cyl_segments * base_seg_factor
        )
        if base_platform:
            base_platform.reparentTo(central_root); base_platform.setZ(base_height / 2)
            base_platform.setColor(primary_color * 0.8)
            self._set_geometry_collision(base_platform); self.static_elements.append(base_platform)

        tower_height = cs_consts.get('tower_height', 50.0)
        tower_radius = cs_consts.get('tower_radius', 4.0)
        tower = geometry_utils.create_procedural_cylinder(
            "central_tower", radius=tower_radius, height=tower_height, segments=cyl_segments
        )
        if tower:
            tower.reparentTo(central_root); tower.setPos(0, 0, tower_height / 2 + base_height)
            tower.setColor(primary_color); self._set_geometry_collision(tower); self.static_elements.append(tower)

        num_rings = cs_consts.get('ring_count', 5)
        ring_rad_base = cs_consts.get('ring_radius_base', 8.0)
        ring_rad_reduct = cs_consts.get('ring_radius_reduction_factor', 5.0)
        ring_h_factor = cs_consts.get('ring_height_factor', 0.9)
        ring_seg_base = cs_consts.get('ring_segment_base_count', 12)
        ring_seg_inc = cs_consts.get('ring_segment_increment', 2)
        ring_seg_scale = cs_consts.get('ring_segment_scale', 0.5)
        ring_rot_dur_base = cs_consts.get('ring_rotation_duration_base', 25.0)
        ring_rot_dur_inc = cs_consts.get('ring_rotation_duration_increment', 5.0)
        ring_colors = [primary_color, secondary_color]

        for i in range(num_rings):
            ring_root = central_root.attachNewNode(f"central_ring_{i}")
            height_ratio = (i + 1) / (num_rings + 1)
            ring_radius = tower_radius + ring_rad_base - height_ratio * ring_rad_reduct
            ring_z = base_height + height_ratio * (tower_height * ring_h_factor)
            ring_root.setPos(0, 0, ring_z)

            num_segments = ring_seg_base + i * ring_seg_inc
            for j in range(num_segments):
                angle = j * (2 * math.pi / num_segments)
                x = ring_radius * math.cos(angle); y = ring_radius * math.sin(angle)
                segment = geometry_utils.create_procedural_cube(f"central_ring_seg_{i}_{j}")
                if not segment: continue
                segment.reparentTo(ring_root); segment.setPos(x, y, 0)
                segment.setScale(ring_seg_scale)
                segment.lookAt(Point3(0,0,0))
                segment.setColor(ring_colors[i % len(ring_colors)] * random.uniform(0.9, 1.1))
                segment.setCollideMask(BitMask32(0)); self.static_elements.append(segment)

            duration = ring_rot_dur_base + i * ring_rot_dur_inc
            start_h = (i * 360 / num_rings) % 360
            hpr_seq = LerpHprInterval(ring_root, duration, Vec3(start_h + 360, 0, 0), startHpr=Vec3(start_h,0,0), name=f"central_ring_rot_{i}")
            hpr_seq.loop()
            self.animating_intervals.append(hpr_seq)
            self.static_elements.append(ring_root)

        orb_z_offset = cs_consts.get('orb_z_offset', 5.0)
        orb_radius = cs_consts.get('orb_radius', 3.0)
        orb_pos_z = base_height + tower_height + orb_z_offset
        orb = geometry_utils.create_procedural_sphere("central_orb", radius=orb_radius, segments=sphere_segments)
        if orb:
            orb.reparentTo(central_root); orb.setPos(0, 0, orb_pos_z)
            orb.setColorScale(1,1,1,1)
            orb.setLightOff()
            orb.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
            orb.setTransparency(TransparencyAttrib.MAlpha)
            orb.setCollideMask(BitMask32(0))
            self.static_elements.append(orb)

            pulse_low_f = cs_consts.get('orb_pulse_color_low_factor', 0.8)
            pulse_high_f = cs_consts.get('orb_pulse_color_high_factor', 1.5)
            pulse_dur = cs_consts.get('orb_pulse_duration', 3.5)
            pulse_fade_in = cs_consts.get('orb_pulse_fade_in_factor', 0.4)
            pulse_fade_out = cs_consts.get('orb_pulse_fade_out_factor', 0.6)
            pulse_wait = cs_consts.get('orb_pulse_wait', 1.0)

            base_col_scale = Vec4(accent_color.getX() * pulse_low_f, accent_color.getY() * pulse_low_f, accent_color.getZ() * pulse_low_f, accent_color.getW())
            pulse_col_scale = Vec4(accent_color.getX() * pulse_high_f, accent_color.getY() * pulse_high_f, accent_color.getZ() * pulse_high_f, accent_color.getW())

            pulse_ival = Sequence(
                Func(orb.setColorScale, base_col_scale),
                LerpColorScaleInterval(orb, pulse_dur*pulse_fade_in, pulse_col_scale, startColorScale=base_col_scale, blendType='easeInOut'),
                LerpColorScaleInterval(orb, pulse_dur*pulse_fade_out, base_col_scale, startColorScale=pulse_col_scale, blendType='easeInOut'),
                Wait(pulse_wait),
                name="central_orb_pulse"
            )
            pulse_ival.loop()
            self.animating_intervals.append(pulse_ival)

            atten_list = cs_consts.get('orb_light_attenuation', [1.0, 0.0, 0.0001])
            light_color_f = cs_consts.get('orb_light_color_factor', 1.2)
            orb_light = PointLight("orb_light")
            orb_light.setColor(accent_color * light_color_f)
            attenuation = Vec3(atten_list[0], atten_list[1], atten_list[2]) if len(atten_list) == 3 else Vec3(1,0,0.0001)
            orb_light.setAttenuation(attenuation)
            orb_light_np = orb.attachNewNode(orb_light)
            self.render.setLight(orb_light_np)
            self.static_elements.append(orb_light_np)

        num_beams = cs_consts.get('beam_count', 6)
        beam_length = cs_consts.get('beam_length', 25.0)
        beam_width = cs_consts.get('beam_width', 0.15)
        beam_look_z = cs_consts.get('beam_lookat_z', 0.5)
        beam_dur_range = cs_consts.get('beam_scale_duration_range', [4.0, 7.0])
        beam_xy_f = cs_consts.get('beam_scale_xy_factor', 1.2)
        beam_z_range = cs_consts.get('beam_scale_z_range', [0.8, 1.3])
        beam_fade_in = cs_consts.get('beam_scale_fade_in_factor', 0.4)
        beam_fade_out = cs_consts.get('beam_scale_fade_out_factor', 0.6)
        beam_wait = cs_consts.get('beam_scale_wait_factor', 0.2)

        for i in range(num_beams):
            angle = i * (2 * math.pi / num_beams)
            beam = geometry_utils.create_procedural_cube(f"central_beam_{i}")
            if not beam: continue
            beam.reparentTo(orb)
            beam.setScale(beam_width, beam_width, beam_length)
            beam.lookAt(Point3(math.cos(angle), math.sin(angle), beam_look_z))
            beam.setY(beam, beam_length / 2.0)
            beam.setColorScale(beam_color)
            beam.setLightOff(); beam.setTransparency(True)
            beam.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd))
            beam.setCollideMask(BitMask32(0)); self.static_elements.append(beam)

            duration = _rand_uniform(beam_dur_range)
            base_scale = beam.getScale()
            target_scale = Vec3(base_scale.x * beam_xy_f,
                                base_scale.y * beam_xy_f,
                                base_scale.z * _rand_uniform(beam_z_range))
            beam_ival = Sequence(
                Wait(random.uniform(0, duration/2)),
                LerpScaleInterval(beam, duration*beam_fade_in, target_scale, startScale=base_scale, blendType='easeInOut'),
                LerpScaleInterval(beam, duration*beam_fade_out, base_scale, startScale=target_scale, blendType='easeInOut'),
                Wait(duration*beam_wait),
                name=f"central_beam_scale_{i}"
            )
            beam_ival.loop()
            self.animating_intervals.append(beam_ival)

        self.static_elements.append(central_root)
        return central_root

    def cleanup(self):
        print("Cleaning up StructureGenerator...")
        for interval in self.animating_intervals:
            if interval and hasattr(interval, 'finish') and callable(interval.finish):
                interval.finish()
        self.animating_intervals.clear()

        for element_np in reversed(self.static_elements):
            if element_np and not element_np.isEmpty():
                light = element_np.node()
                if isinstance(light, PointLight):
                    if self.render.hasLight(element_np):
                         self.render.clearLight(element_np)
                element_np.removeNode()
        self.static_elements.clear()
        print("StructureGenerator cleanup complete.")