import os
from panda3d.core import (
    BitMask32, Vec3, ClockObject, Filename, Texture, TextureStage, PNMImage
)
from direct.interval.IntervalGlobal import Sequence

from .static_generators.manager import StaticEnvironmentManager
from .reactive_manager import ReactiveManager

# get the global clock for consistent timing
globalClock = ClockObject.getGlobalClock()
MASK_ENVIRONMENT = BitMask32(1)   # ← platforms, terrain, walls, etc.
MASK_PLAYER      = BitMask32(2)   # ← your capsule
MASK_TRIGGER     = BitMask32(4)   # ← reactive triggers
MASK_CAMERA      = BitMask32(8)   # ← camera collisions if any

class EnvironmentManager:
    """
    Top-level manager for the game environment, responsible for initializing
    static and reactive components, and injecting a simple parkour map.
    """
    def __init__(self, app):
        self.app = app
        self.render = app.render
        self.loader = app.loader

        # roots for static and reactive elements
        self.static_root = self.render.attachNewNode("StaticEnvironmentRoot")
        self.platforms_root = self.render.attachNewNode("PlatformsRoot")
        # disable lighting for all static elements to preserve true texture colors
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
            {
                'name': 'launch_pad',
                'pos': (2, 2, 2),
                'size': (2, 1, 0.2),
                'texture': 'wood_plank.png',
            },
            {
                'name': 'spinner',
                'pos': (4, 6, 10),
                'size': (3, 3, 0.3),
                'texture': 'metal_plate.png',
                'rotation': { 'axis': (0, 0, 1), 'speed': 60 },
            },
            {
                'name': 's1',
                'pos': (0, 0, 16),
                'size': (1, 1, 1),
                'texture': 'wood_plank.png',
            },
            {
                'name': 's2',
                'pos': (-8, -4, 18),
                'size': (8, 1, 0.2),
                'texture': 'wood_plank.png',
            },
            {
                'name': 's3',
                'pos': (-25, -4, 20),
                'size': (8, 1, 0.2),
                'texture': 'wood_plank.png',
            },
            {
                'name': 'w1',
                'pos': (-13.5, -8, 16),
                'size': (0.2, 8, 8),
                'texture': 'wood_plank.png',
            },
            {
                'name': 'm1',
                'pos': (-25, 2, 22),
                'size': (3, 3, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(-25, 2, 22), (-17, 2, 22)],
                    'duration': 20,
                }
            },
            {
                'name': 'm2',
                'pos': (-25, 10, 24),
                'size': (3, 3, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(-25, 10, 24), (-17, 10, 24)],
                    'duration': 13,
                }
            },
            {
                'name': 'm3',
                'pos': (-25, 18, 26),
                'size': (3, 3, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(-25, 18, 26), (-17, 18, 26)],
                    'duration': 7,
                }
            },
            {
                'name': 'm4',
                'pos': (-25, 26, 28),
                'size': (4, 4, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(-25, 26, 28), (-17, 26, 28)],
                    'duration': 3,
                }
            },
            {
                'name': 'm5',
                'pos': (-30, 32, 32),
                'size': (4, 4, 0.2),
                'texture': 'concrete.jpg',
                'movement': {
                    'points': [(-30, 32, 32), (-12, 32, 32)],
                    'duration': 2,
                }
            },
            {
                'name': 's3',
                'pos': (-28, 40, 36),
                'size': (13, 13, 0.2),
                'texture': 'yob.png',
            },
            {
                'name': 'r2',
                'pos': (-16, 52, 39),
                'size': (4, 4, 1),
                'texture': 'ebet.png',
                'rotation': { 'axis': (1, 0, 0), 'speed': 40 },
            },
            {
                'name': 'r2',
                'pos': (-22, 44, 42),
                'size': (4, 4, 1),
                'texture': 'ebet.png',
                'rotation': { 'axis': (1, 0, 0), 'speed': 50 },
            },
            {
                'name': 's4',
                'pos': (-22, 24, 42),
                'size': (4, 4, 4),
                'texture': 'falter.png',
            },
            {
                'name': 's5',
                'pos': (-2, 24, 44),
                'size': (4, 4, 2),
                'texture': 'falter.png',
            },
            {
                'name': 's6',
                'pos': (-2, 44, 44),
                'size': (2, 2, 1),
                'texture': 'falter.png',
            },
            {
                'name': 's7',
                'pos': (-2, 60, 42),
                'size': (1, 1, 1),
                'texture': 'falter.png',
            },
            {
                'name': 'm5',
                'pos': (-30, 60, 44),
                'size': (4, 4, 0.2),
                'texture': 'falter.png',
                'movement': {
                    'points': [(-30, 60, 44), (-6, 60, 44)],
                    'duration': 6.4,
                }
            },
            {
                'name': 's7',
                'pos': (-32, 60, 46),
                'size': (1, 1, 1),
                'texture': 'falter.png',
            },
            {
                'name': 'r2',
                'pos': (-24, 54, 52),
                'size': (3, 3, 3),
                'texture': 'mandbrot.png',
                'rotation': { 'axis': (1, 1, 1), 'speed': 20 },
            },
            {
                'name': 'r3',
                'pos': (-20, 50, 60),
                'size': (3, 3, 3),
                'texture': 'mandbrot.png',
                'rotation': { 'axis': (1, 1, 1), 'speed': 27 },
            },
            {
                'name': 'r4',
                'pos': (-15, 48, 69),
                'size': (3, 3, 3),
                'texture': 'mandbrot.png',
                'rotation': { 'axis': (1, 1, 1), 'speed': 41 },
            },
            {
                'name': 'r5',
                'pos': (-14, 40, 70),
                'size': (3, 3, 3),
                'texture': 'losing.png',
                'rotation': { 'axis': (1, 0, 0), 'speed': 160 },
            },
            {
                'name': 's8',
                'pos': (-20, 8, 70),
                'size': (10, 10, 0.2),
                'texture': 'PASTEL.png',
            },
            {
                'name': 's9',
                'pos': (-20, 8, 71),
                'size': (0.1, 5, 5),
                'texture': 'PASTEL.png',
            },
            {
                'name': 's10',
                'pos': (-20, 13, 71),
                'size': (0.1, 5, 5),
                'texture': 'PASTEL.png',
            },
            {
                'name': 's11',
                'pos': (-10, 13, 71),
                'size': (0.1, 5, 5),
                'texture': 'PASTEL.png',
            },
            {
                'name': 's12',
                'pos': (-10, 8, 71),
                'size': (0.1, 5, 5),
                'texture': 'PASTEL.png',
            },
        ]

        for cfg in platforms:
            self._spawn_platform(cfg)

    def _spawn_platform(self, cfg):
        # load the cube
        platform = self.loader.loadModel('models/box')
        platform.reparentTo(self.platforms_root)
        platform.setPos(*cfg['pos'])
        sx, sy, sz = cfg['size']
        platform.setScale(sx, sy, sz)

        # 1) turn off all lighting/shaders so nothing else tints it
        platform.setShaderOff()
        platform.setLightOff()

        # 2) create a 1×1 solid-white texture on the fly
        img = PNMImage(1, 1, 4)
        img.setXelA(0, 0, 1, 1, 1, 1)
        white_tex = Texture()
        white_tex.load(img)

        # 3) apply it with a REPLACE texture stage (this *replaces* any vertex colour)
        ts = TextureStage('flat_replace')
        ts.setMode(TextureStage.MReplace)
        platform.setTexture(ts, white_tex)

        # now you have a perfect 3D cube (all 6 faces) with zero noise on it
        platform.setCollideMask(MASK_ENVIRONMENT)

        if cfg.get('texture'):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'textures'))
            tex_file = cfg['texture']
            tex_path = os.path.join(base_dir, tex_file)
            if not os.path.isfile(tex_path):
                tex_path = cfg['texture']
            tex = self.loader.loadTexture(Filename.fromOsSpecific(tex_path))
            # ensure no lighting/material distortion
            stage = TextureStage('ts')
            stage.setMode(TextureStage.MReplace)
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