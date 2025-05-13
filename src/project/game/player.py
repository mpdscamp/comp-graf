from collections import deque
import math

from panda3d.core import (
    Point3, Vec3, BitMask32, CollisionNode, CollisionCapsule,
    CollisionRay, CollisionHandlerPusher, CollisionHandlerQueue,
    ClockObject, KeyboardButton, CollisionHandlerFloor
)
from direct.task.Task import Task
from direct.actor.Actor import Actor
from direct.showbase.DirectObject import DirectObject

from ..utils.geometry_utils import create_player_model

globalClock = ClockObject.getGlobalClock()
MASK_ENVIRONMENT = BitMask32(1)   # ← platforms, terrain, walls, etc.
MASK_PLAYER      = BitMask32(2)   # ← your capsule
MASK_TRIGGER     = BitMask32(4)   # ← reactive triggers
MASK_CAMERA      = BitMask32(8)   # ← camera collisions if any

class PlayerController(DirectObject):

    def __init__(self, app):
        print("Initializing PlayerController...")
        self.app = app
        self.render = app.render
        self.taskMgr = app.taskMgr

        # load constants
        self.player_const = self.app.settings_manager.constants.get('player', {})
        self.collision_const = self.app.settings_manager.constants.get('collision', {})

        # root & visual model
        self.player_root = self.render.attachNewNode("PlayerRoot")
        self.player_root.setPos(0, 0, 5.0)
        model, anims = create_player_model("PlayerVisualModel")
        if not model:
            raise RuntimeError("failed to load player model")
        self.player_model, self.player_anims = model, anims
        self.player_model.reparentTo(self.player_root)

        # ---- MOVEMENT / ROTATION ----
        self.move_speed      = 4.0
        self.turn_rate       = self.player_const.get('TURN_RATE', 360.0)
        self.current_heading = 0.0
        self.target_heading  = 0.0
        self.is_walking      = False
        self._space_last     = False


        # ---- SPRINT & DASH ----
        self.sprint_multiplier     = 1.5
        self.is_sprinting          = False

        self.dash_speed_multiplier = 6.0
        self.dash_duration         = 0.18
        self.dash_cooldown         = 1.0
        self._dash_timer           = 0.0
        self._dash_cd_timer        = 0.0
        self._last_shift_time      = 0.0
        self._shift_tap_threshold  = 0.3

        # ---- JUMP & DOUBLE-JUMP ----
        self.jump_force         = self.player_const.get('JUMP_FORCE', 8.0)
        self.gravity            = self.player_const.get('GRAVITY', 20.0)
        self.vertical_velocity  = 0.0
        self.is_grounded        = False
        self.air_time           = 0.0

        # after any jump, ignore ground for this many secs
        self.jump_ignore_time   = 0.2
        self._jump_ignore_timer = 0.0

        # allow one double jump per air session
        self.can_double_jump    = False

        # ---- COLLISION SETUP (unchanged) ----
        self.collision_consts = self.collision_const
        self._setup_collision()
        self._pusher_enabled = True

        # ---- INPUT ----
        self._setup_input()

        # ---- SMOOTH TIMING ----
        self.dt_buffer = deque([1/60]*5, maxlen=5)

        # ---- START UPDATE TASK ----
        self.taskMgr.add(self._update_movement, "playerMoveTask", sort=20)
        print("PlayerController initialized.")

    def _setup_collision(self):
        print("Setting up player collision...")
        player_tag = self.collision_consts.get('TAG_PLAYER', 'Player')
        player_height = self.player_const.get('HEIGHT', 1.8)
        player_radius = self.player_const.get('RADIUS', 0.4)
        mask_ground = MASK_ENVIRONMENT
        mask_player = MASK_PLAYER        
        mask_trigger = MASK_TRIGGER
        mask_camera = MASK_CAMERA
        default_ground_check_dist = self.player_const.get('GROUND_CHECK_DIST', 0.3)

        self.collider_node = CollisionNode(player_tag)
        capsule_shape = CollisionCapsule(
            Point3(0, 0, player_radius),
            Point3(0, 0, player_height - player_radius),
            player_radius
        )
        self.collider_node.addSolid(capsule_shape)
        self.collider_node.setFromCollideMask(mask_player)
        self.collider_np = self.player_root.attachNewNode(self.collider_node)

        self.pusher = CollisionHandlerPusher()
        self.pusher.addCollider(self.collider_np, self.player_root)
        self.collider_node.setIntoCollideMask(mask_trigger | mask_camera | mask_ground)

        self.app.add_collider_to_main_traverser(self.collider_np, self.pusher)
        self.app.add_collider_to_main_traverser(self.collider_np, self.app.event_handler)

        self.ground_ray_node = CollisionNode('player-ground-ray')

        self.ray_start_z_offset = player_radius
        self.ground_check_dist = self.ground_check_dist = default_ground_check_dist

        ray_shape = CollisionRay(0, 0, self.ray_start_z_offset, 0, 0, -1)
        self.ground_ray_node.addSolid(ray_shape)

        self.ground_ray_node.setFromCollideMask(mask_ground)
        self.ground_ray_node.setIntoCollideMask(BitMask32(0))

        self.ground_ray_np = self.player_root.attachNewNode(self.ground_ray_node)
        # self.ground_ray_np.show()

        # ——— Floor handler to automatically ride up slopes ———
        self.floor_handler = CollisionHandlerFloor()
        self.floor_handler.addCollider(self.ground_ray_np, self.player_root)
        self.app.add_collider_to_main_traverser(self.ground_ray_np, self.floor_handler)
        # ——— Ground handler to detect ground hits ———
        self.ground_handler = CollisionHandlerQueue()
        self.app.add_collider_to_main_traverser(self.ground_ray_np, self.ground_handler)

        print("Player collision setup complete.")
        print(f"  Capsule: Z={player_radius:.2f} to Z={player_height - player_radius:.2f}, R={player_radius:.2f}")
        print(f"  Ground Ray: Starts at Z={self.ray_start_z_offset:.2f} relative to root (feet)")
        print(f"  Ground Check Distance Threshold: {self.ground_check_dist:.2f}")
        print(f"  Pusher Into Mask: {self.collider_node.getIntoCollideMask()}")
        print(f"  Ground Ray From Mask: {self.ground_ray_node.getFromCollideMask()}")

    def _setup_input(self):
        """ Only Shift (for sprint/dash) and Space (for jump). """
        self.accept("shift",    self._on_shift,  [True])
        self.accept("shift-up", self._on_shift,  [False])
        self.accept("space",    self.jump)
        self.accept("shift-space", self.jump)

    def _on_shift(self, is_down):
        now = globalClock.getFrameTime()
        if is_down:
            self.is_sprinting = True
            # double-tap detection
            if now - self._last_shift_time < self._shift_tap_threshold \
               and self._dash_cd_timer <= 0:
                self._dash_timer    = self.dash_duration
                self._dash_cd_timer = self.dash_cooldown
            self._last_shift_time = now
        else:
            self.is_sprinting = False

    def jump(self):
        """ Handles jump and one double-jump. """
        # first jump
        if self.is_grounded and self._jump_ignore_timer <= 0:
            self.vertical_velocity = self.jump_force
            self.is_grounded       = False
            self.can_double_jump   = True
            self._jump_ignore_timer = self.jump_ignore_time
            # lift slightly to avoid immediate ground‐hit
            self.player_root.setZ(self.player_root.getZ() + 0.2)

        # double jump
        elif not self.is_grounded and self.can_double_jump:
            self.vertical_velocity = self.jump_force
            self.can_double_jump   = False

    def _check_ground(self):
        """
        Performs the ray cast downwards from slightly above the player's feet.
        Returns: (is_grounded, ground_z_world)
                 is_grounded: Boolean indicating if ground is detected within range.
                 ground_z_world: The Z coordinate of the hit ground in world space, or None.
        """
        if not self.ground_handler or not self.ground_ray_np:
            return False, None

        num_entries = self.ground_handler.getNumEntries()

        if num_entries > 0:
            self.ground_handler.sortEntries()
            ground_entry = self.ground_handler.getEntry(0)
            hit_node = ground_entry.getIntoNodePath().node()

            mask_ground = self.collision_consts.get('MASK_GROUND', BitMask32(1))
            if (hit_node.getIntoCollideMask() & mask_ground):
                hit_pos_world = ground_entry.getSurfacePoint(self.render)
                ray_origin_world = self.ground_ray_np.getPos(self.render)

                hit_distance = ray_origin_world.getZ() - hit_pos_world.getZ()

                if hit_distance < self.ground_check_dist:
                    return True, hit_pos_world.getZ()

        if self.vertical_velocity != 0:
            ray_origin_world = self.ground_ray_np.getPos(self.render)
            player_z = self.player_root.getZ()

        return False, None

    def _update_movement(self, task):
        # skip if paused / invalid
        if not self.app or self.app.game_paused or self.player_root.isEmpty():
            return Task.cont

        # compute smoothed dt
        raw_dt = globalClock.getDt()
        raw_dt = max(0, min(raw_dt, 0.1))
        self.dt_buffer.append(raw_dt)
        dt = sum(self.dt_buffer) / len(self.dt_buffer)

        # decrement all timers
        if self._dash_timer   > 0: self._dash_timer   -= dt
        if self._dash_cd_timer > 0: self._dash_cd_timer -= dt
        if self._jump_ignore_timer > 0: self._jump_ignore_timer -= dt

        # apply gravity when airborne
        if not self.is_grounded or self.vertical_velocity > 0:
            self.vertical_velocity -= self.gravity * dt

        # --- build move_direction by polling WASD each frame ---
        mw = self.app.mouseWatcherNode
        cam_q   = self.app.camera.getQuat(self.render)
        cam_fwd = cam_q.getForward();  cam_fwd.z = 0; cam_fwd.normalize()
        cam_right = cam_q.getRight(); cam_right.z = 0; cam_right.normalize()

        move_dir = Vec3(0)
        if mw.is_button_down(KeyboardButton.ascii_key('w')): move_dir += cam_fwd
        if mw.is_button_down(KeyboardButton.ascii_key('s')): move_dir -= cam_fwd
        if mw.is_button_down(KeyboardButton.ascii_key('a')): move_dir -= cam_right
        if mw.is_button_down(KeyboardButton.ascii_key('d')): move_dir += cam_right

        is_moving = move_dir.lengthSquared() > 0.01
        if is_moving:
            move_dir.normalize()
            # smooth turn-to-direction
            self.target_heading = math.degrees(math.atan2(-move_dir.x, move_dir.y))
            cur_h = self.player_root.getH()
            d_h = (self.target_heading - cur_h + 180) % 360 - 180
            max_turn = self.turn_rate * dt
            turn_amt = max(-max_turn, min(max_turn, d_h))
            new_h = (cur_h + turn_amt) % 360
            self.player_root.setH(new_h)
            self.current_heading = new_h

        # --- decide horizontal speed & direction ---
        if self._dash_timer > 0:
            # dash: even from standstill, dash forward
            if not is_moving:
                dash_dir = self.player_root.getQuat(self.render).getForward()
                dash_dir.z = 0; dash_dir.normalize()
            else:
                dash_dir = move_dir
            speed = self.move_speed * self.dash_speed_multiplier
            horizontal_delta = dash_dir * speed * dt

        elif is_moving and self.is_sprinting:
            speed = self.move_speed * self.sprint_multiplier
            horizontal_delta = move_dir * speed * dt

        elif is_moving:
            horizontal_delta = move_dir * self.move_speed * dt

        else:
            horizontal_delta = Vec3(0)

        # vertical movement
        vertical_delta = Vec3(0, 0, self.vertical_velocity * dt)

        # apply movement
        pos_before = self.player_root.getPos()
        self.player_root.setPos(pos_before + horizontal_delta + vertical_delta)

        # --- ground check & landing detection ---
        prev_grounded = self.is_grounded

        # skip ground‐hits while in jump‐ignore window OR while dashing
        if self._jump_ignore_timer <= 0:
            grounded, ground_z = self._check_ground()
        else:
            grounded, ground_z = False, None

        if grounded:
            # snap to exactly the floor height
            self.player_root.setZ(ground_z)
            if self.vertical_velocity <= 0:
                self.vertical_velocity = 0

            # only on the *transition* from air→ground do we reset timers
            if not prev_grounded:
                self.air_time        = 0.0
                self.can_double_jump = False
                self._dash_cd_timer  = 0.0
                # note: we do *not* zero out self._dash_timer here—let it finish!
            self.is_grounded = True
        else:
            # still in air
            if prev_grounded:
                # just left ground
                self.air_time = 0.0
            else:
                self.air_time += dt
            self.is_grounded = False

        # --- walking animation ---
        if isinstance(self.player_model, Actor):
            anim = self.player_anims[0]
            if is_moving:
                if not self.is_walking:
                    self.player_model.loop(anim)
                    self.is_walking = True
                rate = 1.0
                rate = 3.0 if self.is_sprinting else rate
                rate = 10 if self._dash_timer > 0 else rate
                self.player_model.setPlayRate(rate, anim)
            else:
                if self.is_walking:
                    self.player_model.unloadAnims()
                    self.is_walking = False

        return Task.cont

    def get_collider_nodepath(self):
        return self.collider_np

    def destroy(self):
        print("Destroying PlayerController...")
        self.taskMgr.remove("playerMoveTask")
        self.ignoreAll()
        if self.player_model: self.player_model.removeNode()
        if self.player_root:  self.player_root.removeNode()
        # clear references
        self.app = self.player_model = self.player_root = None
        print("PlayerController destroyed.")
