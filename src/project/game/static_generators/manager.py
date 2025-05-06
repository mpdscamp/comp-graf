import random
import math
from panda3d.core import (
    NodePath, AmbientLight, DirectionalLight, Fog, BitMask32, Vec4
)
from direct.interval.IntervalManager import ivalMgr

from .sky_generator import SkyGenerator
from .terrain_generator import TerrainGenerator

class StaticEnvironmentManager:
    """
    Manages the creation and cleanup of the static (non-reactive)
    parts of the game environment by coordinating various generator classes.
    Handles global effects like lighting and fog.
    """
    def __init__(self, app, root_node):
        self.app = app
        self.render = app.render
        self.loader = app.loader
        self.root_node = root_node
        self.settings_manager = app.settings_manager
        self.static_elements = []
        self.animating_intervals = []

        self.env_consts = self.settings_manager.constants.get('environment', {})
        self.collision_consts = self.settings_manager.constants.get('collision', {})
        self.proc_geom_consts = self.settings_manager.constants.get('procedural_geometry', {})
        self.proc_gen_consts = self.env_consts.get('procedural_generation', {})
        self.palette = self.env_consts.get('PALETTE', {})

        common_args = {
            'app': self.app,
            'settings_manager': self.settings_manager,
            'palette': self.palette,
            'proc_geom_consts': self.proc_geom_consts,
            'proc_gen_consts': self.proc_gen_consts,
            'collision_consts': self.collision_consts
        }

        self.sky_generator = SkyGenerator(root_node=self.render, **common_args)
        self.terrain_generator = TerrainGenerator(root_node=self.root_node, **common_args)

        self._setup_lighting()
        self._add_fog_effect()

        self.sky_generator.generate_sky()
        self.terrain_generator.generate_terrain_and_features()

        print("StaticEnvironmentManager initialized.")

    def _get_palette_color(self, key, default=Vec4(1,1,1,1)):
       return self.settings_manager.get_palette_color(key, default)

    def _setup_lighting(self):
        print("Setting up global lighting...")
        ambient_color = self._get_palette_color('ambient')
        dir_color = self._get_palette_color('directional')
        
        ambient_light = AmbientLight("ambient_light")
        ambient_light.setColor(ambient_color * 1.2)
        self.ambient_light_np = self.render.attachNewNode(ambient_light)
        self.render.setLight(self.ambient_light_np)
        self.static_elements.append(self.ambient_light_np)

        directional_light = DirectionalLight("directional_light")
        directional_light.setColor(dir_color)
        directional_light.setShadowCaster(True, 1024, 1024)
        self.directional_light_np = self.render.attachNewNode(directional_light)
        self.directional_light_np.setHpr(-30, -60, 0)
        self.render.setLight(self.directional_light_np)
        self.static_elements.append(self.directional_light_np)
        
        fill_light = DirectionalLight("fill_light")
        fill_color = dir_color * 0.4
        fill_light.setColor(fill_color)
        self.fill_light_np = self.render.attachNewNode(fill_light)
        self.fill_light_np.setHpr(120, -30, 0)
        self.render.setLight(self.fill_light_np)
        self.static_elements.append(self.fill_light_np)

        print("Global lighting setup complete.")

    def _add_fog_effect(self):
        print("Adding global fog...")
        fog_color = self.env_consts.get('FOG_COLOR', self._get_palette_color('fog'))
        fog_density = self.env_consts.get('FOG_DENSITY', 0.004)

        self.fog = Fog("scene_fog")
        self.fog.setColor(fog_color)
        self.fog.setExpDensity(fog_density)
        self.render.setFog(self.fog)
        print("Global fog added.")

    def get_terrain_height(self, nx, ny):
        if self.terrain_generator:
            # Convert from normalized coordinates to world coordinates
            terrain_size = self.env_consts.get('TERRAIN_SIZE', 200.0)
            world_x = nx * terrain_size / 2
            world_z = ny * terrain_size / 2
            return self.terrain_generator.calculate_terrain_height(world_x, world_z)
        return 0

    def cleanup(self):
        print("Cleaning up StaticEnvironmentManager...")

        if hasattr(self, 'terrain_generator') and self.terrain_generator:
            self.terrain_generator.cleanup()
            self.terrain_generator = None
        if hasattr(self, 'sky_generator') and self.sky_generator:
            self.sky_generator.cleanup()
            self.sky_generator = None

        print(f"Removing {len(self.static_elements)} manager-tracked static elements (lights)...")
        for element_np in reversed(self.static_elements):
            if element_np and not element_np.isEmpty():
                light = element_np.node()
                if isinstance(light, (AmbientLight, DirectionalLight)):
                    if self.render.hasLight(element_np):
                         self.render.clearLight(element_np)
                element_np.removeNode()
        self.static_elements.clear()

        self.render.clearFog()
        print("Cleared fog and global lights.")

        if self.root_node and not self.root_node.isEmpty() and self.root_node != self.render:
            self.root_node.removeNode()
        self.root_node = None
        print("StaticEnvironmentManager cleanup complete.")