import os
from panda3d.core import (
    Texture, TextureStage, BitMask32, Vec3, ClockObject, Filename
)
from direct.interval.IntervalGlobal import Sequence

from .static_generators.manager import StaticEnvironmentManager
from .reactive_manager import ReactiveManager

# get the global clock for consistent timing
globalClock = ClockObject.getGlobalClock()



class EnvironmentManager:
    """
    Top-level manager for the game environment, responsible for initializing
    static and reactive components.
    """
    def __init__(self, app):
        self.app = app
        self.render = app.render
        self.loader = app.loader

        self.static_root = self.render.attachNewNode("StaticEnvironmentRoot")
        self.reactive_root = self.render.attachNewNode("ReactiveEnvironmentRoot")

        self.static_manager = StaticEnvironmentManager(app, self.static_root)
        self.reactive_manager = ReactiveManager(app, self.reactive_root)
        self.player = None

        # build a simple parkour course
        self._create_parkour_map()

        # terrain update loop
        self.terrain_update_task = self.app.taskMgr.add(
            self._update_terrain_chunks, "update_terrain_chunks_task"
        )

        print("EnvironmentManager initialized with parkour map.")

    def _create_parkour_map(self):
        """
        Define platforms with positions, sizes, textures, and optional behaviors.
        All texture images (.png, .jpg, .jpeg) will stretch to platform dimensions.
        """
        platforms = [
            # static launch pad
            {
                'name': 'launch_pad',
                'pos': (5, 10, 2),
                'size': (2, 1, 0.2),
                'texture': 'wood_plank.png',  # filename only
            },
            # rotating spinner
            {
                'name': 'spinner',
                'pos': (12, 15, 3),
                'size': (3, 3, 0.3),
                'texture': 'metal_plate.png',
                'rotation': { 'axis': (0, 0, 1), 'speed': 30 },
            },
            # moving platform
            {
                'name': 'shuttle',
                'pos': (20, 5, 1),
                'size': (2, 1, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(20, 5, 1), (25, 5, 1), (25, 10, 1), (20, 10, 1)],
                    'duration': 8,
                }
            },
        ]

        for cfg in platforms:
            self._spawn_platform(cfg)

    def _spawn_platform(self, cfg):
        """
        Create a rectangular platform from a unit cube, apply texture from your
        project/textures folder, and add behaviors.
        """
        # load a simple cube model and scale it
        platform = self.loader.loadModel('models/box')
        platform.reparentTo(self.static_root)
        platform.setName(cfg.get('name', 'platform'))
        platform.setPos(*cfg['pos'])
        platform.setScale(*cfg['size'])
        platform.setCollideMask(BitMask32.bit(1))

        # determine full texture path
        if cfg.get('texture'):
            # locate textures directory relative to this file:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'textures'))
            tex_file = cfg['texture']
            tex_path = os.path.join(base_dir, tex_file)
            # fallback to raw path if not found
            if not os.path.isfile(tex_path):
                tex_path = cfg['texture']
            # load texture
            tex = self.loader.loadTexture(Filename.fromOsSpecific(tex_path))
            tex.setWrapU(Texture.WMClamp)
            tex.setWrapV(Texture.WMClamp)
            stage = TextureStage('ts')
            platform.setTexture(stage, tex)

        # add rotation behavior
        if 'rotation' in cfg:
            axis = Vec3(*cfg['rotation']['axis'])
            speed = cfg['rotation']['speed']
            def spin(task, node=platform, ax=axis, sp=speed):
                node.setHpr(node.getHpr() + ax * (sp * globalClock.getDt()))
                return task.cont
            self.app.taskMgr.add(spin, f"spin_{cfg['name']}_task")

        # add movement behavior using posInterval
        if 'movement' in cfg:
            pts = cfg['movement']['points']
            dur = cfg['movement']['duration']
            seq = Sequence()
            num_pts = len(pts)
            for i in range(num_pts):
                start = Vec3(*pts[i])
                end = Vec3(*pts[(i + 1) % num_pts])
                interval = platform.posInterval(dur / num_pts, end, startPos=start)
                seq.append(interval)
            seq.loop()

    def _update_terrain_chunks(self, task):
        if (self.app.game_paused or not self.app.game_active or 
            not getattr(self, 'static_manager', None) or
            not getattr(self.static_manager, 'terrain_generator', None)):
            return task.cont

        player_pos = None
        if self.player and getattr(self.player, 'player_root', None):
            player_pos = self.player.player_root.getPos(self.render)

        if player_pos:
            self.static_manager.terrain_generator.update_visible_chunks(player_pos)

        return task.again

    def set_player(self, player):
        self.player = player
        if (self.player and 
            getattr(self.static_manager, 'terrain_generator', None)):
            pos = self.player.player_root.getPos(self.render)
            self.static_manager.terrain_generator.update_visible_chunks(pos)

    def handle_collision_enter(self, entry):
        if self.reactive_manager:
            self.reactive_manager.handle_collision_enter(entry)

    def handle_collision_exit(self, entry):
        if self.reactive_manager:
            self.reactive_manager.handle_collision_exit(entry)

    def cleanup(self):
        print("Cleaning up EnvironmentManager...")
        if self.reactive_manager:
            self.reactive_manager.cleanup()
            self.reactive_manager = None
        if self.static_manager:
            self.static_manager.cleanup()
            self.static_manager = None
        if self.reactive_root and not self.reactive_root.isEmpty():
            self.reactive_root.removeNode()
            self.reactive_root = None
        if self.static_root and not self.static_root.isEmpty():
            self.static_root.removeNode()
            self.static_root = None
        print("EnvironmentManager cleanup complete.")
