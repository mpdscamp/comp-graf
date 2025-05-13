import math
from collections import deque

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

        self.player_consts = self.app.settings_manager.constants.get('player', {})
        self.collision_consts = self.app.settings_manager.constants.get('collision', {})

        self.player_root = self.render.attachNewNode("PlayerRoot")
        # Posição inicial do jogador para uma plataforma existente
        self.player_root.setPos(-40, 40, 37.0)  # Plataforma segura com nome 's3'
        print(f"PlayerRoot (Physics Root at Feet) created at {self.player_root.getPos()}")

        self.player_model, self.player_anims = create_player_model("PlayerVisualModel")
        if not self.player_model:
            raise RuntimeError("failed to load player model")
        
        self.player_model.reparentTo(self.player_root)
        self.move_speed = 5.0
        self.sprint_multiplier = 1.7  # Sprint speed multiplier
        self.dash_force = 15.0  # Dash speed
        self.dash_duration = 0.3  # How long the dash lasts in seconds
        self.dash_cooldown = 2.0  # Cooldown between dashes in seconds
        self.current_dash_cooldown = 0.0  # Current dash cooldown timer
        self.is_dashing = False  # Flag to track if currently dashing
        self.dash_timer = 0.0  # Timer to track dash duration
        self.dash_direction = Vec3(0)  # Direction of the dash
        self.is_sprinting = False  # Flag to track if sprinting
        
        # Variáveis para o double-tap shift
        self._last_shift_time = 0.0
        self._shift_tap_threshold = 0.3
        self._dash_timer = 0.0
        self._dash_cd_timer = 0.0
        
        self.turn_rate = self.player_consts.get('TURN_RATE', 360.0)
        self.current_heading = 0.0
        self.target_heading = 0.0
        self.move_forward = False
        self.move_backward = False
        self.strafe_left = False
        self.strafe_right = False
        self.is_walking = False

        self.collider_node = None
        self.collider_np = None
        self.pusher = None
        self.ground_ray_node = None
        self.ground_ray_np = None
        self.ground_handler = None
        self._setup_collision()

        self.dt_buffer_size = 5
        self.dt_buffer = deque([1.0/60.0] * self.dt_buffer_size, maxlen=self.dt_buffer_size)

        self.jump_force = self.player_consts.get('JUMP_FORCE', 8.0)
        self.gravity = self.player_consts.get('GRAVITY', 20.0)
        self.vertical_velocity = 0.0
        self.is_grounded = False
        self.air_time = 0.0
        self.ground_check_dist = self.player_consts.get('GROUND_CHECK_DIST', 0.3)
        self.jump_cooldown = 0
        self.debug_mode = True
        
        # Death handling
        self.is_dead = False
        self.death_height = -20.0  # Death trigger when player falls below this height
        self.max_air_time = 5.0     # Death trigger when player falls for this long

        self._setup_input()

        self.taskMgr.add(self._update_movement, "playerMoveTask", sort=20)

        print("PlayerController initialized.")

    def _setup_collision(self):
        print("Setting up player collision...")
        player_tag = self.collision_consts.get('TAG_PLAYER', 'Player')
        player_height = self.player_consts.get('HEIGHT', 1.8)
        player_radius = self.player_consts.get('RADIUS', 0.4)
        mask_ground = MASK_ENVIRONMENT
        mask_player = MASK_PLAYER        
        mask_trigger = MASK_TRIGGER
        mask_camera = MASK_CAMERA
        default_ground_check_dist = self.player_consts.get('GROUND_CHECK_DIST', 0.3)

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
        self.ground_ray_node.setIntoCollideMask(BitMask32.allOff())

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
        """ Configuração de eventos de input para teclas de movimento e ações. """
        # Teclas de movimento WASD
        self.accept("w", self._set_move_forward, [True])
        self.accept("w-up", self._set_move_forward, [False])
        self.accept("s", self._set_move_backward, [True])
        self.accept("s-up", self._set_move_backward, [False])
        self.accept("a", self._set_strafe_left, [True])
        self.accept("a-up", self._set_strafe_left, [False])
        self.accept("d", self._set_strafe_right, [True])
        self.accept("d-up", self._set_strafe_right, [False])
        
        # Teclas de ação
        self.accept("shift", self._on_shift, [True])
        self.accept("shift-up", self._on_shift, [False])
        self.accept("space", self.jump)
        self.accept("shift-space", self.jump)
    
    # Métodos para definir movimentos
    def _set_move_forward(self, is_down):
        self.move_forward = is_down
        
    def _set_move_backward(self, is_down):
        self.move_backward = is_down
        
    def _set_strafe_left(self, is_down):
        self.strafe_left = is_down
        
    def _set_strafe_right(self, is_down):
        self.strafe_right = is_down

    def _on_shift(self, is_down):
        now = globalClock.getFrameTime()
        if is_down:
            self.is_sprinting = True
            # double-tap detection
            if now - self._last_shift_time < self._shift_tap_threshold \
               and self._dash_cd_timer <= 0:
                self._dash_timer = self.dash_duration
                self._dash_cd_timer = self.dash_cooldown
            self._last_shift_time = now
        else:
            self.is_sprinting = False

    def jump(self):
        """Initiates a jump if the player is grounded."""
        if self.debug_mode:
            print(f"Jump button pressed. Is grounded: {self.is_grounded}, Cooldown: {self.jump_cooldown}, Sprinting: {self.is_sprinting}")
        
        if self.is_grounded and self.jump_cooldown <= 0:
            if self.debug_mode:
                print(f"Starting jump with force: {self.jump_force}")
            
            # Apply additional jump force when sprinting
            jump_force = self.jump_force
            if self.is_sprinting:
                jump_force *= 1.2  # Optional: Give a bit more height to sprint jumps
                if self.debug_mode:
                    print(f"Sprint jump with increased force: {jump_force}")
            
            self.vertical_velocity = jump_force
            self.is_grounded = False
            
            self.player_root.setZ(self.player_root.getZ() + 0.2)
            self.jump_cooldown = 5
            
            self.air_time = 0.0
            if self.debug_mode:
                print(f"Set vertical velocity to: {self.vertical_velocity}")
                print(f"Initial position: {self.player_root.getZ():.2f}")


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
        if not self.app or self.app.game_paused or self.player_root.isEmpty() or self.is_dead:
            return Task.cont

        raw_dt = globalClock.getDt()
        if raw_dt == 0: return Task.cont
        if raw_dt > 0.1: raw_dt = 0.1

        self.dt_buffer.append(raw_dt)
        dt = sum(self.dt_buffer) / len(self.dt_buffer)

        pos_before_update = self.player_root.getPos()
        was_grounded = self.is_grounded

        # Update timers and cooldowns
        if self.jump_cooldown > 0:
            self.jump_cooldown -= 1
            if self.debug_mode:
                print(f"Jump cooldown: {self.jump_cooldown}, Height: {self.player_root.getZ():.2f}")
        
        # Update dash cooldown
        if self._dash_cd_timer > 0:
            self._dash_cd_timer -= dt
            if self._dash_cd_timer < 0:
                self._dash_cd_timer = 0
                if self.debug_mode:
                    print("Dash cooldown reset - ready to dash again")
        
        # Update dash timer if dashing
        if self._dash_timer > 0:
            self._dash_timer -= dt
            self.is_dashing = True
            if self._dash_timer <= 0:
                self._dash_timer = 0
                self.is_dashing = False
                if self.debug_mode:
                    print("Dash complete")
        else:
            self.is_dashing = False

        if not self.is_grounded or self.vertical_velocity > 0:
            self.vertical_velocity -= self.gravity * dt

        # Determine movement direction
        move_direction = Vec3(0)
        is_moving = False
        if self.app.camera:
            cam_quat = self.app.camera.getQuat(self.render)
            cam_forward = cam_quat.getForward()
            cam_right = cam_quat.getRight()
            cam_forward.z = 0
            cam_right.z = 0
            cam_forward.normalize()
            cam_right.normalize()

            if self.move_forward: move_direction += cam_forward
            if self.move_backward: move_direction -= cam_forward
            if self.strafe_left: move_direction -= cam_right
            if self.strafe_right: move_direction += cam_right

            is_moving = move_direction.lengthSquared() > 0.01

        # Turn the player model to face the movement direction
        if is_moving and not self.is_dashing:
            move_direction.normalize()
            self.target_heading = math.degrees(math.atan2(-move_direction.x, move_direction.y))

            current_h = self.player_root.getH()
            delta_h = (self.target_heading - current_h + 180) % 360 - 180
            max_turn = self.turn_rate * dt
            turn_amount = max(-max_turn, min(max_turn, delta_h))
            new_h = (current_h + turn_amount) % 360
            self.player_root.setH(new_h)
            self.current_heading = new_h

        # Calculate horizontal movement
        horizontal_move_delta = Vec3(0)
        
        # Dash takes precedence over normal movement
        if self.is_dashing:
            if self.dash_direction.lengthSquared() > 0.01:
                horizontal_move_delta = self.dash_direction * self.dash_force * dt
            else:
                # Se dash_direction não estiver definido, usar a direção de movimento atual
                self.dash_direction = move_direction if move_direction.lengthSquared() > 0.01 else Vec3(0, 1, 0)
                horizontal_move_delta = self.dash_direction * self.dash_force * dt
        elif is_moving:
            # Apply sprint multiplier if sprinting
            current_speed = self.move_speed
            if self.is_sprinting:
                current_speed *= self.sprint_multiplier
                
            horizontal_move_delta = move_direction * current_speed * dt
        else:
            horizontal_move_delta = Vec3(0)

        # Calculate vertical movement (gravity/jumping)
        vertical_move_delta = Vec3(0, 0, self.vertical_velocity * dt)

        # Combine movements
        final_delta = horizontal_move_delta + vertical_move_delta
        self.player_root.setPos(pos_before_update + final_delta)

        # Ground detection
        if self.jump_cooldown > 0:
            is_now_grounded = False
            ground_z_world = None
            if self.debug_mode and self.vertical_velocity > 0:
                print(f"Skipping ground check - jump cooldown active. Current height: {self.player_root.getZ():.2f}")
        else:
            is_now_grounded, ground_z_world = self._check_ground()

        # Ground handling
        if is_now_grounded:
            current_z = self.player_root.getZ()
            z_diff = ground_z_world - current_z
            if z_diff > 0.001 or (not was_grounded and self.vertical_velocity < 0):
                 self.player_root.setZ(ground_z_world)
                 if self.vertical_velocity < -0.1:
                     pass

            if self.vertical_velocity <= 0:
                 self.vertical_velocity = 0
            self.is_grounded = True
            self.air_time = 0.0
        else:
            if was_grounded and self.jump_cooldown <= 0:
                self.air_time = 0.0
                if self.vertical_velocity <= 0 and self.debug_mode:
                     print(f"Left ground (walked off edge?). Vertical velocity: {self.vertical_velocity:.2f}")
            else:
                self.air_time += dt
            self.is_grounded = False
            
            # Check for death conditions
            current_height = self.player_root.getZ()
            
            # Death by falling below the death height threshold
            if current_height < self.death_height:
                if self.debug_mode:
                    print(f"Player died: Fell below death height {self.death_height}")
                self.die("You fell into the void!")
                return Task.cont
                
            # Death by falling for too long
            if self.air_time > self.max_air_time and self.vertical_velocity < 0:
                if self.debug_mode:
                    print(f"Player died: Fell for too long ({self.air_time:.2f} seconds)")
                self.die("You fell to your death!")
                return Task.cont

        # Animation handling
        if isinstance(self.player_model, Actor) and self.player_anims:
            walk_anim = self.player_anims[0]
            if is_moving:
                if not self.is_walking:
                    self.player_model.loop(walk_anim)
                    self.is_walking = True
            else:
                if self.is_walking:
                    try:
                        self.player_model.stop()
                        self.is_walking = False
                    except:
                        # Fallback se unloadAnims causar erro
                        self.is_walking = False
        
        return Task.cont
        
    def die(self, message="You died!"):
        """Handle player death"""
        if self.is_dead:
            return
            
        print(f"Player died: {message}")
        self.is_dead = True
        
        # Stop all player movement
        self.move_forward = False
        self.move_backward = False
        self.strafe_left = False
        self.strafe_right = False
        self.vertical_velocity = 0
        
        # Get the elapsed time from the HUD
        elapsed_time = 0
        if hasattr(self.app, 'hud') and self.app.hud:
            elapsed_time = self.app.hud.get_elapsed_time()
            
        # Show the game over screen with the time survived
        if hasattr(self.app, 'game_over') and self.app.game_over:
            self.app.game_over.show(elapsed_time)
            # Hide HUD but keep the game technically active
            if hasattr(self.app, 'hud') and self.app.hud:
                if hasattr(self.app.hud, 'hide_all'):
                    self.app.hud.hide_all()
                elif hasattr(self.app.hud, 'hide'):
                    self.app.hud.hide()
                
        # Set menu mouse properties
        if hasattr(self.app, '_set_menu_mouse_properties'):
            self.app._set_menu_mouse_properties()

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