from panda3d.core import (
    Point3, Vec3, CollisionRay, CollisionNode, CollisionHandlerQueue,
    CollisionTraverser, BitMask32, WindowProperties, Lens, PerspectiveLens, LensNode
)
from direct.task import Task
import math

class CameraController:
    """Unified camera controller supporting both first-person and third-person modes."""

    THIRD_PERSON = 0
    FIRST_PERSON = 1

    def __init__(self, app):
        self.app = app
        self.render = app.render
        self.camera = app.camera
        print(f"CameraController Initialized. self.camera type: {type(self.camera)}, node type: {type(self.camera.node())}")
        self.taskMgr = app.taskMgr
        self.settings_manager = app.settings_manager
        self.player = None

        self._setup_camera_config()

        self.camera_mode = self.settings_manager.get_user_setting('camera_mode', self.THIRD_PERSON)

        self.cam_pivot = None
        self.cam_dist = self.camera_config["distance"]
        self.cam_target_dist = self.cam_dist
        self.cam_min_dist = self.camera_config["min_distance"]
        self.cam_max_dist = self.camera_config["max_distance"]
        self.cam_lookat_height = self.camera_config["look_at_height"]

        self.cam_heading = 0.0
        self.cam_pitch = 20.0
        self.cam_min_pitch = self.camera_config["min_pitch"]
        self.cam_max_pitch = self.camera_config["max_pitch"]

        player_height = self.settings_manager.get_constant('player', 'HEIGHT', 1.8)
        head_offset = self.settings_manager.get_constant('player', 'HEAD_HEIGHT_OFFSET', -0.2)
        self.fp_head_height = player_height + head_offset


        self.mouse_dead_zone = 0.01


        self.current_fov = self.settings_manager.get_fov()
        self.min_fov = self.settings_manager.get_constant('camera', 'MIN_FOV', 60.0)
        self.max_fov = self.settings_manager.get_constant('camera', 'MAX_FOV', 110.0)

        self._setup_collision_resources()

        self.app.accept('wheel_up', self.zoom_camera, [True])
        self.app.accept('wheel_down', self.zoom_camera, [False])

        self.app.accept('v', self.toggle_camera_mode)

    def _setup_camera_config(self):
        """Load camera settings from settings manager."""
        self.camera_config = {
            "distance": self.settings_manager.get_constant('camera', 'DISTANCE', 5.0),
            "min_distance": self.settings_manager.get_constant('camera', 'MIN_DISTANCE', 2.0),
            "max_distance": self.settings_manager.get_constant('camera', 'MAX_DISTANCE', 10.0),
            "look_at_height": self.settings_manager.get_constant('camera', 'LOOK_AT_HEIGHT', 1.0),
            "min_pitch": self.settings_manager.get_constant('camera', 'MIN_PITCH', -40.0),
            "max_pitch": self.settings_manager.get_constant('camera', 'MAX_PITCH', 70.0),
            "first_person_min_pitch": self.settings_manager.get_constant('camera', 'FIRST_PERSON_MIN_PITCH', -85.0),
            "first_person_max_pitch": self.settings_manager.get_constant('camera', 'FIRST_PERSON_MAX_PITCH', 85.0),
        }

    def _setup_collision_resources(self):
        """Create collision resources without attaching them yet."""
        self.cam_coll_ray = CollisionRay()
        self.cam_coll_node = CollisionNode('camera-collider')
        self.cam_coll_node.addSolid(self.cam_coll_ray)
        mask_camera = self.settings_manager.get_constant('collision', 'MASK_CAMERA', BitMask32(8))
        self.cam_coll_node.setFromCollideMask(mask_camera)
        self.cam_coll_node.setIntoCollideMask(BitMask32.allOff())
        self.cam_coll_np = None
        self.cam_coll_handler = CollisionHandlerQueue()
        self.cam_coll_traverser = CollisionTraverser('camera_collision_trav')

    def setup(self, player=None):
        """Initialize the camera for in-game use."""
        print("Setting up camera system...")
        self.app.disableMouse()

        if player:
            self.player = player

        self.cam_pivot = self.render.attachNewNode("camera_pivot")
        print(f"Created camera pivot: {self.cam_pivot}")

        self.cam_coll_np = self.camera.attachNewNode(self.cam_coll_node)
        self.cam_coll_traverser.addCollider(self.cam_coll_np, self.cam_coll_handler)

        self.camera.reparentTo(self.render)
        self.cam_dist = self.camera_config["distance"]
        self.cam_target_dist = self.cam_dist
        self.cam_heading = 0.0
        self.cam_pitch = 20.0

        self.set_fov(self.current_fov)

        if self.player and self.player.player_root and not self.player.player_root.isEmpty():
            if self.camera_mode == self.FIRST_PERSON:
                print("Starting in first-person mode")
                self.set_first_person_mode()
            else:
                print("Starting in third-person mode")
                self.set_third_person_mode()

            self.update_camera_position()

        self.camera_task = self.taskMgr.add(self._update_camera, "updateCameraTask", priority=-5)

        print("Camera system setup complete.")
        return self.camera_task

    def set_fov(self, fov_value):
        """Sets the horizontal field of view for the camera."""
        try:
            main_cam_np = self.app.cam
            if not main_cam_np or main_cam_np.isEmpty():
                 print("Error: Cannot set FOV, self.app.cam is invalid.")
                 return

            cam_node = main_cam_np.node()
            if not isinstance(cam_node, LensNode) or not cam_node.getLens():
                 print(f"Error: Cannot set FOV, self.app.cam node ({type(cam_node)}) is not a valid LensNode with a Lens.")
                 return

            clamped_fov = max(self.min_fov, min(self.max_fov, float(fov_value)))

            lens = cam_node.getLens()
            if isinstance(lens, PerspectiveLens):
                lens.setFov(clamped_fov)
                self.current_fov = clamped_fov
            else:
                print(f"Warning: Camera lens is not a PerspectiveLens (type: {type(lens)}). Cannot set FOV.")

        except (AttributeError, ValueError, TypeError, Exception) as e:
            print(f"Error setting FOV to {fov_value}: {e}")
            print(f"  Debug Info:")
            print(f"    self.app: {self.app}")
            if self.app:
                print(f"    self.app.cam: {self.app.cam}")
                if self.app.cam and not self.app.cam.isEmpty():
                     print(f"    self.app.cam.node type: {type(self.app.cam.node())}")
                print(f"    self.camera (CameraController's variable): {self.camera}")
                if self.camera and not self.camera.isEmpty():
                     print(f"    self.camera.node type: {type(self.camera.node())}")

    def toggle_camera_mode(self):
        """Toggle between first-person and third-person camera modes."""
        if not self.app.game_active or self.app.game_paused:
            return

        if self.camera_mode == self.THIRD_PERSON:
            self.set_first_person_mode()
        else:
            self.set_third_person_mode()

        self.settings_manager.user_settings['camera_mode'] = self.camera_mode
        self.settings_manager.save_settings()

        camera_mode_name = "First-Person" if self.camera_mode == self.FIRST_PERSON else "Third-Person"
        print(f"Camera mode changed to {camera_mode_name}")

    def set_first_person_mode(self):
        """Switch to first-person camera mode."""
        self.cam_min_pitch = self.camera_config["first_person_min_pitch"]
        self.cam_max_pitch = self.camera_config["first_person_max_pitch"]

        self.cam_pitch = max(self.cam_min_pitch, min(self.cam_max_pitch, self.cam_pitch))

        self.camera_mode = self.FIRST_PERSON

        if self.player and hasattr(self.player, 'player_model') and self.player.player_model:
            self.player.player_model.hide()

        self.update_camera_position()

    def set_third_person_mode(self):
        """Switch to third-person camera mode."""
        self.cam_min_pitch = self.camera_config["min_pitch"]
        self.cam_max_pitch = self.camera_config["max_pitch"]

        self.cam_pitch = max(self.cam_min_pitch, min(self.cam_max_pitch, self.cam_pitch))

        self.camera_mode = self.THIRD_PERSON

        if self.player and hasattr(self.player, 'player_model') and self.player.player_model:
            self.player.player_model.show()

        self.camera.reparentTo(self.render)

        self.update_camera_position()

    def zoom_camera(self, zoom_in):
        """Adjusts the target camera distance based on mouse wheel."""
        if self.app.game_paused or self.camera_mode == self.FIRST_PERSON:
            return
        if not self.cam_pivot or self.cam_pivot.isEmpty():
             return

        zoom_amount = 0.5
        if zoom_in:
            self.cam_target_dist = max(self.cam_min_dist, self.cam_target_dist - zoom_amount)
        else:
            self.cam_target_dist = min(self.cam_max_dist, self.cam_target_dist + zoom_amount)

    def _update_camera(self, task):
        """Task to update camera position and orientation based on mouse input and player position."""
        if (self.app.game_paused or not self.player or not self.player.player_root
            or self.player.player_root.isEmpty()):
            return Task.cont

        if self.camera_mode == self.THIRD_PERSON and (not self.cam_pivot or self.cam_pivot.isEmpty()):
            return Task.cont

        heading_changed = False
        pitch_changed = False

        if self.app.mouseWatcherNode.hasMouse():
            md = self.app.mouseWatcherNode.getMouse()
            dx = md.getX()
            dy = md.getY()

            sensitivity = self.settings_manager.get_effective_sensitivity()

            if abs(dx) > self.mouse_dead_zone:
                heading_delta = dx * sensitivity * 0.5
                self.cam_heading = (self.cam_heading - heading_delta) % 360
                heading_changed = True

                if self.camera_mode == self.FIRST_PERSON:
                    self.player.player_root.setH(self.cam_heading)

            if abs(dy) > self.mouse_dead_zone:
                pitch_delta = dy * sensitivity * 0.5 * (-1 if self.camera_mode == self.THIRD_PERSON else 1)

                self.cam_pitch += pitch_delta
                self.cam_pitch = max(self.cam_min_pitch, min(self.cam_max_pitch, self.cam_pitch))
                pitch_changed = True

            if (heading_changed or pitch_changed) and self.app.win:
                props = self.app.win.getProperties()
                if props.hasSize():
                    self.app.win.movePointer(0,
                                        int(props.getXSize() / 2),
                                        int(props.getYSize() / 2))

        self.update_camera_position()

        return Task.cont

    def update_camera_position(self):
        """Calculate and set the camera's final position, handling collision."""
        if not self.player or not self.player.player_root or self.player.player_root.isEmpty():
            return

        if self.camera_mode == self.FIRST_PERSON:
            self._update_first_person_camera()
        else:
            self._update_third_person_camera()

    def _update_first_person_camera(self):
        """Position camera for first-person view."""
        if not self.player or not self.player.player_root:
             return

        player_pos = self.player.player_root.getPos(self.render)

        cam_pos = Point3(player_pos.x, player_pos.y, player_pos.z + self.fp_head_height)

        self.camera.setPos(cam_pos)
        self.camera.setHpr(self.cam_heading, self.cam_pitch, 0)

    def _update_third_person_camera(self):
        """Position camera for third-person view with collision detection."""
        if not self.cam_pivot or self.cam_pivot.isEmpty() or not self.player or not self.player.player_root:
            return

        player_pos = self.player.player_root.getPos(self.render)
        self.cam_pivot.setPos(player_pos)
        self.cam_pivot.setH(self.cam_heading)

        distance_smoothing = 0.1
        self.cam_dist = self.cam_dist + (self.cam_target_dist - self.cam_dist) * distance_smoothing

        rad_pitch = math.radians(self.cam_pitch)
        cam_offset_y = -self.cam_dist * math.cos(rad_pitch)
        cam_offset_z = self.cam_dist * math.sin(rad_pitch)
        ideal_cam_pos_rel = Point3(0, cam_offset_y, cam_offset_z)
        ideal_cam_pos_world = self.render.getRelativePoint(self.cam_pivot, ideal_cam_pos_rel)

        cam_look_at_pos = player_pos + Point3(0, 0, self.cam_lookat_height)
        final_cam_pos = ideal_cam_pos_world

        self.cam_coll_ray.setOrigin(cam_look_at_pos)
        direction_vector = ideal_cam_pos_world - cam_look_at_pos
        if direction_vector.lengthSquared() > 0.001:
            self.cam_coll_ray.setDirection(direction_vector.normalized())
        else:
            self.cam_coll_ray.setDirection(Vec3(0, -1, 0))

        self.cam_coll_traverser.traverse(self.render)

        actual_cam_dist = self.cam_dist
        if self.cam_coll_handler.getNumEntries() > 0:
            self.cam_coll_handler.sortEntries()
            hit_entry = self.cam_coll_handler.getEntry(0)
            hit_dist_sq = (hit_entry.getSurfacePoint(self.render) - cam_look_at_pos).lengthSquared()
            ideal_dist_sq = direction_vector.lengthSquared()

            if hit_dist_sq < ideal_dist_sq - 0.01:
                hit_pos = hit_entry.getSurfacePoint(self.render)
                hit_vector = hit_pos - cam_look_at_pos
                actual_cam_dist = max(self.cam_min_dist, hit_vector.length() * 0.95)

        actual_cam_dist = max(self.cam_min_dist, actual_cam_dist)
        final_direction = direction_vector.normalized() if direction_vector.lengthSquared() > 0.001 else Vec3(0,-1,0)
        final_cam_pos = cam_look_at_pos + final_direction * actual_cam_dist


        self.camera.setPos(final_cam_pos)
        self.camera.lookAt(cam_look_at_pos)

    def cleanup(self):
        """Clean up camera resources."""
        print("Cleaning up camera system...")
        if hasattr(self, 'camera_task') and self.camera_task:
            self.taskMgr.remove(self.camera_task)
            self.camera_task = None

        if hasattr(self, 'cam_coll_traverser') and self.cam_coll_traverser:
            self.cam_coll_traverser.clearColliders()

        if hasattr(self, 'cam_coll_np') and self.cam_coll_np and not self.cam_coll_np.isEmpty():
            self.cam_coll_np.removeNode()
            self.cam_coll_np = None

        if hasattr(self, 'cam_pivot') and self.cam_pivot and not self.cam_pivot.isEmpty():
            self.cam_pivot.removeNode()
            self.cam_pivot = None

        self.player = None

        print("Camera system cleanup complete.")