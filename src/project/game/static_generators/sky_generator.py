import random
import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, Texture, TextureStage, TexGenAttrib,
    TransformState, CullFaceAttrib, BitMask32
)
from direct.interval.IntervalGlobal import Sequence, LerpPosInterval
from ...utils import geometry_utils

def _rand_uniform(range_list):
    if not isinstance(range_list, list) or len(range_list) != 2: return random.uniform(0, 1)
    return random.uniform(range_list[0], range_list[1])

class SkyGenerator:
    """Generates the sky dome, gradient, and celestial bodies."""
    def __init__(self, app, root_node, settings_manager, palette, proc_geom_consts, proc_gen_consts, **kwargs):
        self.app = app
        self.render = app.render
        self.root_node = root_node
        self.settings_manager = settings_manager
        self.palette = palette
        self.proc_geom_consts = proc_geom_consts
        self.proc_gen_consts = proc_gen_consts.get('sky', {})
        self.env_consts = settings_manager.constants.get('environment', {})

        self.static_elements = []
        self.animating_intervals = []

    def _get_palette_color(self, key, default=Vec4(1,1,1,1)):
       return self.settings_manager.get_palette_color(key, default)

    def generate_sky(self):
        print("Generating sky...")
        sky_dome_scale = self.env_consts.get('SKY_DOME_SCALE', 500.0)
        sky_top_color = self._get_palette_color('sky_top')
        sky_horizon_color = self._get_palette_color('sky_horizon')
        sphere_segments = self.proc_geom_consts.get('SPHERE_SEGMENTS', 32)

        try:
             img_size = self.proc_gen_consts.get('gradient_texture_size', 64)
             sky_texture = Texture("sky_gradient")
             sky_texture.setup_1d_texture(img_size, Texture.TUnsignedByte, Texture.FRgba)
             sky_texture.setWrapU(Texture.WMClamp)
             img_data = bytearray(img_size * 4)
             for i in range(img_size):
                 ratio = i / max(1, img_size - 1)
                 color = sky_horizon_color + (sky_top_color - sky_horizon_color) * ratio
                 idx = i * 4
                 img_data[idx:idx+4] = bytes([int(c * 255) for c in color])
             sky_texture.setRamImage(bytes(img_data))

             sky_sphere = geometry_utils.create_procedural_sphere(
                 name="sky_dome_sphere", radius=1.0, segments=sphere_segments
             )
             if not sky_sphere: raise ValueError("Failed to create sky sphere geom")

             sky_sphere.reparentTo(self.root_node)
             sky_sphere.setScale(sky_dome_scale)
             sky_sphere.setPos(self.app.camera, 0, 0, 0)
             sky_sphere.setCompass()

             ts = TextureStage('sky_ts')
             ts.setMode(TextureStage.MReplace)
             sky_sphere.setTexture(ts, sky_texture)
             z_scale_for_tex = 1.0 / max(0.01, sky_dome_scale)
             z_offset_for_tex = 0.5
             sky_sphere.setTexGen(ts, TexGenAttrib.MWorldPosition)
             sky_sphere.setTexProjector(ts, self.render, sky_sphere)
             sky_sphere.setTexTransform(ts, TransformState.makeScale(Vec3(1, 1, z_scale_for_tex)))
             sky_sphere.setTexPos(ts, 0, 0, z_offset_for_tex)

             sky_sphere.setBin("background", 10)
             sky_sphere.setDepthWrite(False)
             sky_sphere.setDepthTest(False)
             sky_sphere.setTwoSided(False)
             sky_sphere.setAttrib(CullFaceAttrib.makeReverse())
             sky_sphere.setLightOff()
             sky_sphere.setCollideMask(BitMask32(0))
             self.static_elements.append(sky_sphere)

        except Exception as e:
             print(f"Error creating sky gradient: {e}. Creating solid color sky.")
             sky_sphere = geometry_utils.create_procedural_sphere(
                 name="sky_dome_sphere_solid", radius=1.0, segments=sphere_segments
             )
             if sky_sphere:
                  sky_sphere.reparentTo(self.root_node)
                  sky_sphere.setScale(sky_dome_scale); sky_sphere.setPos(self.app.camera, 0, 0, 0); sky_sphere.setCompass()
                  sky_sphere.setColor(sky_horizon_color)
                  sky_sphere.setBin("background", 10); sky_sphere.setDepthWrite(False); sky_sphere.setDepthTest(False); sky_sphere.setTwoSided(False); sky_sphere.setAttrib(CullFaceAttrib.makeReverse()); sky_sphere.setLightOff(); sky_sphere.setCollideMask(BitMask32(0))
                  self.static_elements.append(sky_sphere)

        if sky_sphere and not sky_sphere.isEmpty():
            accent_color = self._get_palette_color('accent_glow')
            num_celestial = self.proc_gen_consts.get('celestial_count', 7)
            celestial_segments = self.proc_gen_consts.get('celestial_segments', 8)
            dist_range = self.proc_gen_consts.get('celestial_dist_range', [0.8, 0.98])
            max_elev_factor = self.proc_gen_consts.get('celestial_max_elevation_factor', 2.1)
            scale_range = self.proc_gen_consts.get('celestial_scale_range', [5.0, 15.0])
            color_scale_mult = self.proc_gen_consts.get('celestial_color_scale_multiplier', 1.5)
            drift_xy_range = self.proc_gen_consts.get('celestial_drift_offset_xy_range', [-0.1, 0.1])
            drift_z_range = self.proc_gen_consts.get('celestial_drift_offset_z_range', [-0.05, 0.05])
            drift_dur_range = self.proc_gen_consts.get('celestial_drift_duration_range', [40.0, 80.0])

            for i in range(num_celestial):
                shape_key = random.choice(['sphere', 'cube'])
                body = geometry_utils.get_procedural_shape(
                    shape_key, f"celestial_{i}", segments=celestial_segments
                )
                if not body: continue
                body.reparentTo(sky_sphere)

                dist_factor = _rand_uniform(dist_range)
                phi = random.uniform(0, 2 * math.pi)
                theta = random.uniform(0, math.pi / max(0.1, max_elev_factor))
                x = dist_factor * math.sin(theta) * math.cos(phi)
                y = dist_factor * math.sin(theta) * math.sin(phi)
                z = dist_factor * math.cos(theta)
                body.setPos(x, y, z)

                body_scale = _rand_uniform(scale_range) * (sky_dome_scale / 500.0)
                body.setScale(body_scale / 0.5 if shape_key=='sphere' else body_scale)
                body.lookAt(Point3(0,0,0))

                body.setColor(accent_color * 0.5)
                body.setColorScale(color_scale_mult, color_scale_mult, color_scale_mult, 1)
                body.setLightOff()
                body.setBin("background", 11)
                body.setDepthWrite(False); body.setDepthTest(False)
                body.setCollideMask(BitMask32(0))

                drift_target_offset = Point3(_rand_uniform(drift_xy_range),
                                             _rand_uniform(drift_xy_range),
                                             _rand_uniform(drift_z_range))
                start_pos = body.getPos()
                end_pos = start_pos + drift_target_offset
                duration = _rand_uniform(drift_dur_range)
                drift_ival = Sequence(
                     LerpPosInterval(body, duration/2, end_pos, startPos=start_pos, blendType='easeInOut'),
                     LerpPosInterval(body, duration/2, start_pos, startPos=end_pos, blendType='easeInOut'),
                     name=f"celestial_drift_{i}"
                )
                drift_ival.loop()
                self.animating_intervals.append(drift_ival)
                self.static_elements.append(body)

        print("Sky generation complete.")

    def cleanup(self):
        print("Cleaning up SkyGenerator...")
        for interval in self.animating_intervals:
            if interval and hasattr(interval, 'finish') and callable(interval.finish):
                interval.finish()
        self.animating_intervals.clear()

        for element_np in reversed(self.static_elements):
            if element_np and not element_np.isEmpty():
                element_np.removeNode()
        self.static_elements.clear()
        print("SkyGenerator cleanup complete.")