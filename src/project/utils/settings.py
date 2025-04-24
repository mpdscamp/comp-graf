import json
import os
from panda3d.core import WindowProperties, loadPrcFileData, Vec4, Vec3, BitMask32

class SettingsManager:
    def __init__(self, app):
        self.app = app
        self.settings_file = 'settings.json'
        self._default_settings = self._get_default_settings()
        self.user_settings = self._default_settings['user_settings'].copy()
        self.constants = {}
        self.load_settings()

    def _get_default_settings(self):
        return {
            "user_settings": {
                "sensitivity": 30.0,
                "resolution": "1280x720",
                "fullscreen": False,
                "fov": 75.0,
                "camera_mode": 0
            },
            "game_constants": {
                "player": {
                    "MOVE_SPEED": 10.0, "HEIGHT": 1.8, "RADIUS": 0.4, "JUMP_FORCE": 12.0, "GRAVITY": 30.0, "TURN_RATE": 360.0, "HEAD_HEIGHT_OFFSET": -0.2
                },
                "camera": {
                    "MIN_PITCH": -40.0,
                    "MAX_PITCH": 70.0,
                    "DEFAULT_SENSITIVITY": 30.0,
                    "DISTANCE": 5.0,
                    "LOOK_AT_HEIGHT": 1.0,
                    "MIN_DISTANCE": 2.0,
                    "MAX_DISTANCE": 10.0,
                    "MIN_FOV": 60.0,
                    "MAX_FOV": 120.0,
                    "FIRST_PERSON_MIN_PITCH": -85.0,
                    "FIRST_PERSON_MAX_PITCH": 85.0
                },
                "collision": {
                    "MASK_GROUND": 1, "MASK_PLAYER": 2, "MASK_REACTIVE_TRIGGER": 4, "MASK_CAMERA": 8,
                    "TAG_PLAYER": "Player", "TAG_REACTIVE": "ReactiveElement", "TAG_GEOMETRY": "Geometry",
                    "TAG_GEOMETRY_KEY": "Geometry"
                },
                "environment": {
                    "TERRAIN_SIZE": 200.0, "TERRAIN_GRID_SIZE": 15,
                    "SKY_DOME_SCALE": 500.0, "FOG_DENSITY": 0.004,
                    "PALETTE": {
                        "sky_top": [0.1, 0.0, 0.2, 1.0],
                        "sky_horizon": [0.3, 0.2, 0.5, 1.0],
                        "fog": [0.15, 0.1, 0.25, 1.0],
                        "ambient": [0.15, 0.1, 0.25, 1.0],
                        "directional": [0.6, 0.5, 0.7, 1.0],
                        "terrain_low": [0.2, 0.3, 0.5, 1.0],
                        "terrain_mid": [0.4, 0.4, 0.7, 1.0],
                        "terrain_high": [0.7, 0.7, 0.9, 1.0],
                        "structure_primary": [0.3, 0.4, 0.8, 1.0],
                        "structure_secondary": [0.5, 0.3, 0.7, 1.0],
                        "crystal": [0.6, 0.8, 1.0, 0.8],
                        "accent_glow": [1.0, 0.7, 0.3, 1.0],
                        "accent_beam": [1.0, 0.8, 0.5, 0.7]
                    },
                    "procedural_generation": {
                        "sky": {
                            "gradient_texture_size": 64,
                            "celestial_count": 7,
                            "celestial_segments": 8,
                            "celestial_dist_range": [0.8, 0.98],
                            "celestial_max_elevation_factor": 2.1,
                            "celestial_scale_range": [5.0, 15.0],
                            "celestial_color_scale_multiplier": 1.5,
                            "celestial_drift_offset_xy_range": [-0.1, 0.1],
                            "celestial_drift_offset_z_range": [-0.05, 0.05],
                            "celestial_drift_duration_range": [40.0, 80.0]
                        },
                        "terrain_features": {
                            "island_height_threshold": -1.0,
                            "island_probability_base": 0.3,
                            "island_probability_dist_factor": 0.3,
                            "crystal_height_threshold": 0.0,
                            "crystal_probability": 0.08,
                            "terrain_color_low_mid_threshold": 0.33,
                            "terrain_color_mid_high_threshold": 0.66,
                            "terrain_min_height": -5.0,
                            "terrain_max_height": 5.0
                        },
                        "floating_island": {
                            "base_segments": 8,
                            "base_scale_xy_range": [4.0, 10.0],
                            "base_scale_z_range": [1.5, 4.0],
                            "shard_probability": 0.4,
                            "shard_count_range": [1, 3],
                            "shard_scale_base_range": [0.3, 1.0],
                            "shard_scale_height_range": [1.5, 3.0],
                            "shard_pos_factor": 0.333,
                            "shard_hpr_h_range": [0.0, 360.0],
                            "shard_hpr_p_range": [-15.0, 15.0],
                            "float_height_range": [0.5, 2.0],
                            "float_duration_range": [8.0, 15.0]
                        },
                        "crystal_pillar": {
                            "height_range": [10.0, 30.0],
                            "width_range": [0.5, 2.5],
                            "hpr_h_range": [0.0, 360.0],
                            "glow_probability": 0.5,
                            "glow_scale_multiplier": 1.5,
                            "glow_duration_range": [4.0, 8.0],
                            "glow_wait_range": [1.0, 3.0]
                        },
                        "static_structures": {
                            "platform_count": 12,
                            "sculpture_count": 15,
                            "spawn_area_factor": 0.45,
                            "spawn_height_threshold": -2.0,
                            "platform_z_offset_range": [10.0, 40.0],
                            "sculpture_z_offset_range": [0.5, 2.0],
                            "column_formation_radius": 50.0,
                            "column_formation_count": 9
                        },
                        "platform": {
                            "width_range": [6.0, 15.0],
                            "depth_range": [6.0, 15.0],
                            "height_range": [1.0, 2.5],
                            "float_height_range": [1.0, 3.0],
                            "float_duration_range": [10.0, 18.0]
                        },
                        "abstract_sculpture": {
                            "stacked": {
                                "element_count_range": [4, 8],
                                "base_scale_range": [2.0, 4.0],
                                "scale_reduction_factor": 0.8,
                                "position_jitter_range": [-0.2, 0.2],
                                "rotation_probability": 0.3,
                                "rotation_duration_range": [20.0, 40.0]
                            },
                            "sphere_cluster": {
                                "center_z_range": [1.0, 3.0],
                                "orb_count_range": [6, 15],
                                "placement_radius_base": 0.5,
                                "placement_radius_exponent": 1.5,
                                "placement_radius_max_factor": 2.5,
                                "size_range": [0.2, 0.8],
                                "pulse_scale_multiplier_range": [1.3, 1.8],
                                "pulse_duration_range": [3.0, 7.0],
                                "pulse_wait_range": [0.5, 2.0]
                            },
                            "rings": {
                                "count_range": [3, 5],
                                "max_radius_range": [4.0, 7.0],
                                "radius_reduction_factor": 0.4,
                                "segment_count_factor": 8.0,
                                "segment_scale_range": [0.2, 0.4],
                                "rotation_hpr_range": [-15.0, 15.0],
                                "rotation_duration_range": [15.0, 35.0]
                            },
                            "crystal_growth": {
                                "count_range": [5, 12],
                                "base_pos_z": 0.1,
                                "placement_dist_base": 0.0,
                                "placement_dist_exponent": 1.5,
                                "placement_dist_max_factor": 3.0,
                                "placement_z_factor": 2.0,
                                "height_base": 1.0,
                                "height_range": [1.0, 5.0],
                                "height_dist_factor": 0.2,
                                "width_base": 0.1,
                                "width_range": [0.2, 0.8],
                                "width_dist_factor": 0.25,
                                "lookat_jitter_range": [-1.0, 1.0],
                                "alpha_scale_range": [0.6, 0.9]
                            }
                        },
                        "column_formation": {
                            "radius_jitter_range": [0.9, 1.1],
                            "angle_jitter_range": [-0.1, 0.1],
                            "segments": 12,
                            "height_range": [12.0, 30.0],
                            "width_range": [1.2, 2.8],
                            "glow_probability": 0.4,
                            "glow_duration_range": [5.0, 10.0],
                            "glow_intensity_range": [0.2, 0.5],
                            "glow_fade_in_factor": 0.1,
                            "glow_fade_out_factor": 0.4,
                            "glow_wait_factor": 0.5
                        },
                        "central_structure": {
                            "base_radius": 18.0,
                            "base_height": 1.5,
                            "base_segment_factor": 2,
                            "tower_height": 50.0,
                            "tower_radius": 4.0,
                            "ring_count": 5,
                            "ring_radius_base": 8.0,
                            "ring_radius_reduction_factor": 5.0,
                            "ring_height_factor": 0.9,
                            "ring_segment_base_count": 12,
                            "ring_segment_increment": 2,
                            "ring_segment_scale": 0.5,
                            "ring_rotation_duration_base": 25.0,
                            "ring_rotation_duration_increment": 5.0,
                            "orb_z_offset": 5.0,
                            "orb_radius": 3.0,
                            "orb_pulse_color_low_factor": 0.8,
                            "orb_pulse_color_high_factor": 1.5,
                            "orb_pulse_duration": 3.5,
                            "orb_pulse_fade_in_factor": 0.4,
                            "orb_pulse_fade_out_factor": 0.6,
                            "orb_pulse_wait": 1.0,
                            "orb_light_attenuation": [1.0, 0.0, 0.0001],
                            "orb_light_color_factor": 1.2,
                            "beam_count": 6,
                            "beam_length": 25.0,
                            "beam_width": 0.15,
                            "beam_lookat_z": 0.5,
                            "beam_scale_duration_range": [4.0, 7.0],
                            "beam_scale_xy_factor": 1.2,
                            "beam_scale_z_range": [0.8, 1.3],
                            "beam_scale_fade_in_factor": 0.4,
                            "beam_scale_fade_out_factor": 0.6,
                            "beam_scale_wait_factor": 0.2
                        }
                    }
                },
                "procedural_geometry": {
                    "SPHERE_SEGMENTS": 24, "CYLINDER_SEGMENTS": 12
                },
                "reactive_elements": {
                    "DEFAULT_TRIGGER_RADIUS": 8.0, "DEFAULT_REACTION_STRENGTH": 1.0, "DEFAULT_REACTION_SPEED": 1.0,
                    "DEFAULT_PARAMS": {
                        "size": 1.5, "color": [0.6, 0.6, 0.9, 1.0], "shape": "sphere",
                        "trigger_radius": 8.0, "reaction_strength": 1.0, "reaction_speed": 1.0
                    },
                    "PYTHON_TAG_ROOT": "element_root", "PYTHON_TAG_GEOM": "geometry",
                    "PYTHON_TAG_TYPE": "reaction_type", "PYTHON_TAG_PARAMS": "params",
                    "COLLISION_NODE_PREFIX": "trigger_",
                    "COLLISION_EVENT_IN": "player-into-trigger", "COLLISION_EVENT_OUT": "player-out-trigger"
                },
                "lighting": {
                    "AMBIENT_LIGHT_COLOR": [0.15, 0.1, 0.25, 1.0],
                    "DIRECTIONAL_LIGHT_COLOR": [0.6, 0.5, 0.7, 1.0]
                }
            }
        }

    def _get_nested_dict(self, data_dict, keys, default=None):
        current = data_dict
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
            if current is None:
                return default
        return current

    def _parse_vec(self, data, expected_len=4):
        if isinstance(data, list) and len(data) == expected_len:
            try:
                if expected_len == 4:
                    return Vec4(*map(float, data))
                elif expected_len == 3:
                    return Vec3(*map(float, data))
                else:
                     return None
            except (ValueError, TypeError) as e:
                 print(f"Warning: Could not parse list {data} into Vec{expected_len}: {e}")
                 return None
        elif isinstance(data, (Vec3, Vec4)):
            return data
        return None

    def _parse_bitmask(self, data):
        if isinstance(data, int):
            return BitMask32(data)
        elif isinstance(data, BitMask32):
            return data
        return None

    def _deep_update(self, source, overrides):
        for key, value in overrides.items():
            if isinstance(value, dict) and key in source and isinstance(source[key], dict):
                self._deep_update(source[key], value)
            elif key in source:
                 source[key] = value
        return source

    def _parse_constants(self, constants_dict_to_parse):
        parsed = json.loads(json.dumps(self._default_settings['game_constants']))
        self._deep_update(parsed, constants_dict_to_parse)
        default_consts = self._default_settings['game_constants']

        col_consts = parsed.get('collision', {})
        def_col_consts = default_consts.get('collision', {})
        for key in ['MASK_GROUND', 'MASK_PLAYER', 'MASK_REACTIVE_TRIGGER', 'MASK_CAMERA']:
             default_val = def_col_consts.get(key, 0)
             col_consts[key] = self._parse_bitmask(col_consts.get(key)) or BitMask32(default_val)
        parsed['collision'] = col_consts

        re_consts = parsed.get('reactive_elements', {})
        re_params = re_consts.get('DEFAULT_PARAMS', {})
        def_re_params = self._get_nested_dict(default_consts, ['reactive_elements', 'DEFAULT_PARAMS'], {})
        def_color_fallback = def_re_params.get('color', [0.6, 0.6, 0.9, 1.0])
        re_params['color'] = self._parse_vec(re_params.get('color')) or Vec4(*def_color_fallback)
        re_consts['DEFAULT_PARAMS'] = re_params
        parsed['reactive_elements'] = re_consts

        light_consts = parsed.get('lighting', {})
        def_light_consts = default_consts.get('lighting', {})
        def_ambient_fallback = def_light_consts.get('AMBIENT_LIGHT_COLOR', [0.15, 0.1, 0.25, 1.0])
        def_dir_fallback = def_light_consts.get('DIRECTIONAL_LIGHT_COLOR', [0.6, 0.5, 0.7, 1.0])
        light_consts['AMBIENT_LIGHT_COLOR'] = self._parse_vec(light_consts.get('AMBIENT_LIGHT_COLOR')) or Vec4(*def_ambient_fallback)
        light_consts['DIRECTIONAL_LIGHT_COLOR'] = self._parse_vec(light_consts.get('DIRECTIONAL_LIGHT_COLOR')) or Vec4(*def_dir_fallback)
        parsed['lighting'] = light_consts

        env_consts = parsed.get('environment', {})
        palette_in_parsed = env_consts.get('PALETTE', {})
        def_palette = default_consts.get('environment', {}).get('PALETTE', {})

        if def_palette:
            for key, default_value_list in def_palette.items():
                value_to_parse = palette_in_parsed.get(key, default_value_list)
                parsed_color = self._parse_vec(value_to_parse) or self._parse_vec(default_value_list)
                if not parsed_color:
                    print(f"Warning: Could not parse palette color '{key}'. Using fallback white.")
                    palette_in_parsed[key] = Vec4(1, 1, 1, 1)
                else:
                    palette_in_parsed[key] = parsed_color
        else:
             print("Error: Default palette definition is missing or invalid!")

        env_consts['PALETTE'] = palette_in_parsed
        parsed['environment'] = env_consts

        final_palette = parsed.get('environment', {}).get('PALETTE', {})
        light_consts = parsed.get('lighting', {})
        env_consts = parsed.get('environment', {})

        final_palette = parsed.get('environment', {}).get('PALETTE', {})
        if 'ambient' in final_palette: light_consts['AMBIENT_LIGHT_COLOR'] = final_palette['ambient']
        if 'directional' in final_palette: light_consts['DIRECTIONAL_LIGHT_COLOR'] = final_palette['directional']
        if 'fog' in final_palette: env_consts['FOG_COLOR'] = final_palette['fog']

        parsed['lighting'] = light_consts
        parsed['environment'] = env_consts

        cs_consts = self._get_nested_dict(parsed, ['environment', 'procedural_generation', 'central_structure'], {})
        def_cs_consts = self._get_nested_dict(default_consts, ['environment', 'procedural_generation', 'central_structure'], {})
        def_atten_fallback = def_cs_consts.get('orb_light_attenuation', [1.0, 0.0, 0.0001])
        cs_consts['orb_light_attenuation'] = self._parse_vec(cs_consts.get('orb_light_attenuation'), 3) or Vec3(*def_atten_fallback)

        cam_consts = parsed.get('camera', {})
        def_cam_consts = default_consts.get('camera', {})
        for key in ['MIN_FOV', 'MAX_FOV', 'MIN_PITCH', 'MAX_PITCH', 'FIRST_PERSON_MIN_PITCH', 'FIRST_PERSON_MAX_PITCH']:
             default_val = def_cam_consts.get(key, 0.0)
             try:
                 cam_consts[key] = float(cam_consts.get(key, default_val))
             except (ValueError, TypeError):
                 print(f"Warning: Invalid value for camera constant '{key}'. Using default {default_val}.")
                 cam_consts[key] = float(default_val)
        parsed['camera'] = cam_consts

        player_consts = parsed.get('player', {})
        def_player_consts = default_consts.get('player', {})
        key = 'HEAD_HEIGHT_OFFSET'
        default_val = def_player_consts.get(key, -0.2)
        try:
            player_consts[key] = float(player_consts.get(key, default_val))
        except (ValueError, TypeError):
            print(f"Warning: Invalid value for player constant '{key}'. Using default {default_val}.")
            player_consts[key] = float(default_val)
        parsed['player'] = player_consts

        return parsed


    def load_settings(self):
        if not os.path.exists(self.settings_file):
            print("No settings file found. Using default settings and constants.")
            self.user_settings = self._default_settings['user_settings'].copy()
            self.constants = self._parse_constants(self._default_settings['game_constants'])
        else:
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_data = json.load(f)

                default_user = self._default_settings['user_settings'].copy()
                loaded_user = loaded_data.get('user_settings', {})
                self._deep_update(default_user, loaded_user)
                self.user_settings = default_user

                loaded_constants_dict = loaded_data.get('game_constants', {})
                self.constants = self._parse_constants(loaded_constants_dict)

                print("Settings and constants loaded successfully from file.")

            except Exception as e:
                print(f"Error loading settings file: {e}. Falling back to default settings and constants.")
                self.user_settings = self._default_settings['user_settings'].copy()
                self.constants = self._parse_constants(self._default_settings['game_constants'])


    def save_settings(self):
        print("Attempting to save settings...")
        self.user_settings['sensitivity'] = self.get_effective_sensitivity()
        self.user_settings['fov'] = self.get_fov()
        if self.app.win:
             props = self.app.win.getProperties()
             if props.hasSize():
                 self.user_settings['resolution'] = f"{props.getXSize()}x{props.getYSize()}"
             if props.hasFullscreen():
                 self.user_settings['fullscreen'] = props.getFullscreen()

        full_data_to_save = {}
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    full_data_to_save = json.load(f)
                    if not isinstance(full_data_to_save, dict):
                        print(f"Warning: Content of {self.settings_file} is not a dictionary. Will overwrite using defaults.")
                        full_data_to_save = json.loads(json.dumps(self._default_settings))
            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Error reading/decoding {self.settings_file}: {e}. Will overwrite using defaults.")
                full_data_to_save = json.loads(json.dumps(self._default_settings))
        else:
            print(f"Settings file {self.settings_file} not found. Creating new one based on defaults.")
            full_data_to_save = json.loads(json.dumps(self._default_settings))

        if 'user_settings' not in full_data_to_save or not isinstance(full_data_to_save.get('user_settings'), dict):
            full_data_to_save['user_settings'] = {}

        full_data_to_save['user_settings'].update(self.user_settings)

        try:
            os.makedirs(os.path.dirname(self.settings_file) or '.', exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(full_data_to_save, f, indent=4)
            print(f"Settings saved successfully to {self.settings_file} (user_settings updated).")
        except Exception as e:
            print(f"Error saving settings to {self.settings_file}: {e}")


    def get_constant(self, category, key, default=None):
        value = self._get_nested_dict(self.constants, [category, key])

        if value is not None:
            return value
        else:
            print(f"Warning: Constant ['{category}']['{key}'] not found in parsed constants. Trying default definition.")
            default_value = self._get_nested_dict(self._default_settings['game_constants'], [category, key])

            if default_value is not None:
                if isinstance(default_value, list):
                    parsed_vec = self._parse_vec(default_value)
                    if parsed_vec: return parsed_vec
                    parsed_vec3 = self._parse_vec(default_value, 3)
                    if parsed_vec3: return parsed_vec3
                    return default_value if default is None else default
                elif key.startswith("MASK_"):
                    parsed_mask = self._parse_bitmask(default_value)
                    return parsed_mask if parsed_mask is not None else default
                return default_value
            else:
                print(f"Error: Constant ['{category}']['{key}'] also not found in default definitions.")
                return default


    def get_user_setting(self, key, default=None):
        val = self.user_settings.get(key)
        if val is None:
            val = self._default_settings['user_settings'].get(key, default)
        return val

    def get_effective_sensitivity(self):
        sens = self.user_settings.get('sensitivity')
        if sens is None:
            sens = self.get_constant('camera', 'DEFAULT_SENSITIVITY', 30.0)

        try:
            return float(sens)
        except (ValueError, TypeError):
            print(f"Warning: Invalid sensitivity value '{sens}', using default.")
            default_sens = self.get_constant('camera', 'DEFAULT_SENSITIVITY', 30.0)
            return float(default_sens)
        
    def get_fov(self):
        """Gets the current FOV setting, falling back to defaults and clamping."""
        fov = self.get_user_setting('fov')
        if fov is None:
            fov = self._default_settings['user_settings'].get('fov', 75.0)

        min_fov = self.get_constant('camera', 'MIN_FOV', 60.0)
        max_fov = self.get_constant('camera', 'MAX_FOV', 120.0)

        try:
            fov = float(fov)
            return max(min_fov, min(max_fov, fov))
        except (ValueError, TypeError):
            print(f"Warning: Invalid FOV value '{fov}', using default.")
            default_fov = self._default_settings['user_settings'].get('fov', 75.0)
            return max(min_fov, min(max_fov, float(default_fov)))

    def get_palette_color(self, key, default=Vec4(1,1,1,1)):
        color = self.get_constant('environment', 'PALETTE', {}).get(key)

        if isinstance(color, Vec4):
            return color
        else:
            print(f"Warning: Palette color '{key}' resolved to non-Vec4 type ({type(color)}) or None. Using fallback.")
            return default

    def apply_config_vars(self):
        res_str = self.get_user_setting('resolution')
        if res_str:
            try:
                width, height = map(int, res_str.split('x'))
                loadPrcFileData("", f"win-size {width} {height}")
                print(f"Applied config resolution: {width}x{height}")
            except Exception as e:
                print(f"Invalid resolution format '{res_str}' in settings: {e}. Using Panda default.")
        else:
            print("Warning: Resolution setting not found, using Panda default.")


        fullscreen = self.get_user_setting('fullscreen')
        if fullscreen is not None:
            loadPrcFileData("", f"fullscreen {'#t' if fullscreen else '#f'}")
            print(f"Applied config fullscreen: {fullscreen}")
        else:
             print("Warning: Fullscreen setting not found, using Panda default (False).")


    def apply_runtime_settings(self):
        if not self.app.win:
            print("Warning: apply_runtime_settings called before window exists.")
            return

        props = WindowProperties()
        changed = False

        res_str = self.get_user_setting('resolution')
        if res_str:
            try:
                width, height = map(int, res_str.split('x'))
                props.setSize(width, height)
                changed = True
            except Exception: pass

        fullscreen = self.get_user_setting('fullscreen')
        if fullscreen is not None:
            props.setFullscreen(fullscreen)
            changed = True

        if changed:
            self.app.win.requestProperties(props)

        if hasattr(self.app, 'camera_system') and self.app.camera_system:
             current_fov = self.get_fov()
             self.app.camera_system.set_fov(current_fov)
             print(f"Applied runtime FOV: {current_fov:.1f}")