import random
import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, Texture, TextureStage, TexGenAttrib,
    TransformState, CullFaceAttrib, BitMask32, TransparencyAttrib
)
# Removed LerpColorScaleInterval as it was only for star twinkling
# from direct.interval.IntervalGlobal import Sequence, LerpColorScaleInterval 
from direct.interval.IntervalGlobal import Sequence # Sequence might be used by other things later
# Assuming geometry_utils is in project.utils
from ...utils import geometry_utils # Make sure this import path is correct

def _rand_uniform(range_list):
    """Helper function to get a random uniform number within a specified range."""
    if not isinstance(range_list, list) or len(range_list) != 2:
        return random.uniform(0, 1)
    return random.uniform(range_list[0], range_list[1])

class SkyGenerator:
    """Generates the sky dome and gradient."""
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
        self.animating_intervals = [] # Kept in case other animations are added to sky later

    def _get_palette_color(self, key, default=Vec4(1,1,1,1)):
        """Retrieves a color from the palette or returns a default."""
        return self.settings_manager.get_palette_color(key, default)

    def generate_sky(self):
        """Generates a beautiful sky dome with a smoother gradient."""
        print("Generating sky dome (stars removed)...")
        
        # Sky dome setup
        sky_dome_scale = self.env_consts.get('SKY_DOME_SCALE', 500.0)
        sky_top_color = self._get_palette_color('sky_top', Vec4(0.05, 0.15, 0.35, 1.0))
        sky_horizon_color = self._get_palette_color('sky_horizon', Vec4(0.5, 0.65, 0.85, 1.0))
        
        sphere_segments = self.proc_geom_consts.get('SKY_SPHERE_SEGMENTS', 32)

        try:
            # Create a texture for the sky gradient
            img_size = 128
            sky_texture = Texture("sky_gradient")
            sky_texture.setup_1d_texture(img_size, Texture.TUnsignedByte, Texture.FRgba)
            sky_texture.setWrapU(Texture.WMClamp)
            
            # Fill gradient texture
            img_data = bytearray(img_size * 4)
            for i in range(img_size):
                ratio_raw = i / max(1, img_size - 1)
                ratio_interp = 0.5 * (1.0 - math.cos(math.pi * ratio_raw))
                color = sky_horizon_color + (sky_top_color - sky_horizon_color) * ratio_interp
                idx = i * 4
                img_data[idx:idx+4] = bytes([int(max(0, min(255, c * 255))) for c in color])
            
            sky_texture.setRamImage(bytes(img_data))
            
            # Create sky dome sphere
            sky_sphere = geometry_utils.create_procedural_sphere(
                name="sky_dome", radius=1.0, segments=sphere_segments
            )
            
            if not sky_sphere:
                print("Failed to create sky sphere, skipping sky generation.")
                return
            
            # Set up the sky sphere
            sky_sphere.reparentTo(self.root_node)
            sky_sphere.setScale(sky_dome_scale)
            sky_sphere.setPos(self.app.camera, 0, 0, 0) 
            sky_sphere.setCompass()

            # Apply texture mapping for gradient
            ts = TextureStage('sky_ts')
            ts.setMode(TextureStage.MReplace)
            sky_sphere.setTexture(ts, sky_texture)
            
            z_scale_for_tex = 1.0 / max(0.01, sky_dome_scale) 
            z_offset_for_tex = 0.5
            
            sky_sphere.setTexGen(ts, TexGenAttrib.MWorldPosition)
            sky_sphere.setTexProjector(ts, self.render, sky_sphere) 
            sky_sphere.setTexTransform(ts, TransformState.makeScale(Vec3(1, 1, z_scale_for_tex)))
            sky_sphere.setTexPos(ts, 0, 0, z_offset_for_tex)
            
            # Prepare sky dome for rendering
            sky_sphere.setBin("background", 0)
            sky_sphere.setDepthWrite(False)
            sky_sphere.setDepthTest(False)
            sky_sphere.setTwoSided(False)
            sky_sphere.setAttrib(CullFaceAttrib.makeReverse())
            sky_sphere.setLightOff(1)
            sky_sphere.setCollideMask(BitMask32(0))
            
            self.static_elements.append(sky_sphere)
            
            # Star generation and add_enhanced_stars method call REMOVED
            
            print("Sky dome generation complete (stars removed).")
            
        except Exception as e:
            import traceback
            print(f"Error creating sky: {e}")
            traceback.print_exc()
            print("Continuing without sky or with partial sky elements...")

    # add_enhanced_stars method REMOVED

    def cleanup(self):
        """Cleans up all generated sky elements and stops animations."""
        print("Cleaning up SkyGenerator...")
        for interval in self.animating_intervals: # Still here if other animations are added
            if interval:
                interval.finish() 
        self.animating_intervals.clear()

        for element_np in reversed(self.static_elements): 
            if element_np and not element_np.isEmpty():
                element_np.removeNode()
        self.static_elements.clear()
        print("SkyGenerator cleanup complete.")
