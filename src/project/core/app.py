from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight, Vec4, Vec3, Point3, WindowProperties,
    CollisionTraverser, CollisionHandlerEvent, CollisionHandlerPusher,
    loadPrcFileData, BitMask32, TextNode
)
from direct.task import Task
from ..ui.main_menu import MainMenuUI
from ..ui.pause_menu import PauseMenuUI
from ..ui.options_menu import OptionsMenuUI
from ..ui.hud import HeadsUpDisplayUI
from ..utils.settings import SettingsManager
from ..game.camera import CameraController
import sys

loadPrcFileData("", "window-title Reactive Abstract Environment (Third Person)")
loadPrcFileData("", "sync-video #t")
loadPrcFileData("", "show-frame-rate-meter #t")

class ReactiveApp(ShowBase):
    def __init__(self):
        self.settings_manager = SettingsManager(self)
        self.settings_manager.apply_config_vars()

        ShowBase.__init__(self)
        self.setBackgroundColor(0.1, 0.2, 0.4, 1)
        print("Initializing ReactiveApp...")

        self.game_active = False
        self.game_paused = False

        self.settings_manager.apply_runtime_settings()

        self.cTrav = CollisionTraverser("CollisionTraverser_Main")
        self.pusher_handler = CollisionHandlerPusher()
        self.event_handler = CollisionHandlerEvent()

        self.environment_manager = None
        self.player = None
        
        self.camera_system = CameraController(self)

        self.main_menu = MainMenuUI(self)
        self.pause_menu = PauseMenuUI(self)
        self.options_menu = OptionsMenuUI(self)
        self.hud = HeadsUpDisplayUI(self)

        self.main_menu.show()
        self.accept('escape', self.handle_escape_key)
        
        self.taskMgr.add(self._run_collisions, "collisionTask", priority=0)

        print("Initialization complete. Showing main menu.")

    def handle_escape_key(self):
        if self.game_active and not self.game_paused:
            self.pause_game()
        elif self.game_active and self.game_paused:
            options_visible = hasattr(self, 'options_menu') and self.options_menu and \
                               hasattr(self.options_menu, 'frame') and self.options_menu.frame and \
                               not self.options_menu.frame.isHidden()

            if options_visible:
                print("Escape: Options visible, returning to previous (Pause Menu)")
                self.options_menu.back_to_previous()
            else:
                print("Escape: In Pause Menu, resuming game.")
                self.resume_game()

        elif hasattr(self.main_menu, 'frame') and not self.main_menu.frame.isHidden() and \
              hasattr(self, 'options_menu') and self.options_menu and \
              hasattr(self.options_menu, 'frame') and self.options_menu.frame and \
              not self.options_menu.frame.isHidden():
              print("Escape: In Main Menu Options, returning to Main Menu")
              self.options_menu.back_to_previous()

    def start_game(self):
        print("Starting new game...")
        self.cleanup_game_session()

        self.main_menu.hide()
        self.options_menu.hide()
        self.pause_menu.hide()

        from ..game.environment import EnvironmentManager
        from ..game.player import PlayerController

        self.environment_manager = EnvironmentManager(self)
        self._setup_collision_events()
        self.player = PlayerController(self)
        
        if self.environment_manager:
            self.environment_manager.set_player(self.player)

        self.camera_system.setup(self.player)

        self.game_active = True
        self.game_paused = False

        self.hud.show()
        self._set_game_mouse_properties()

        self.taskMgr.add(self._update_hud, "updateHudTask", sort=30)

        print("Game started.")

    def cleanup_game_session(self):
        print("Cleaning up active game session...")
        self.taskMgr.remove("playerMoveTask")
        self.taskMgr.remove("updateHudTask")
        
        if hasattr(self, 'camera_system') and self.camera_system:
            self.camera_system.cleanup()

        if self.player:
            self.player.destroy()
            self.player = None
            
        if self.environment_manager:
            event_in = self.settings_manager.get_constant('reactive_elements', 'COLLISION_EVENT_IN', 'player-into-trigger')
            event_out = self.settings_manager.get_constant('reactive_elements', 'COLLISION_EVENT_OUT', 'player-out-trigger')
            self.ignore(f"{event_in}-*")
            self.ignore(f"{event_out}-*")
            self.environment_manager.cleanup()
            self.environment_manager = None

        self.hud.hide()
        self.game_active = False
        self.game_paused = False

    def pause_game(self):
        if not self.game_active or self.game_paused: return
        print("Pausing game...")
        self.game_paused = True
        self._set_menu_mouse_properties()
        self.pause_menu.show()
        self.hud.hide_crosshair()

    def resume_game(self):
        if not self.game_active or not self.game_paused: return
        print("Resuming game...")
        self.game_paused = False
        self.pause_menu.hide()
        self.options_menu.hide()
        self.hud.show_crosshair()
        if self.win:
            props = self.win.getProperties()
            if props.hasSize():
                 self.win.movePointer(0, int(props.getXSize() / 2), int(props.getYSize() / 2))
        self._set_game_mouse_properties()
        print("Game resumed.")

    def _set_game_mouse_properties(self):
        if self.win:
            props = WindowProperties()
            props.setCursorHidden(True)
            props.setMouseMode(WindowProperties.M_relative)
            self.win.requestProperties(props)

    def _set_menu_mouse_properties(self):
        if self.win:
            props = WindowProperties()
            props.setCursorHidden(False)
            props.setMouseMode(WindowProperties.M_absolute)
            self.win.requestProperties(props)

    def _setup_collision_events(self):
        print("Setting up collision event patterns for triggers...")
        self.event_handler.clearInPatterns()
        self.event_handler.clearOutPatterns()
        event_in = self.settings_manager.get_constant('reactive_elements', 'COLLISION_EVENT_IN', 'player-into-trigger')
        event_out = self.settings_manager.get_constant('reactive_elements', 'COLLISION_EVENT_OUT', 'player-out-trigger')
        self.event_handler.addInPattern(f"{event_in}-%in")
        self.event_handler.addOutPattern(f"{event_out}-%in")
        self.accept(f"{event_in}-*", self.handle_collision_event, extraArgs=[True])
        self.accept(f"{event_out}-*", self.handle_collision_event, extraArgs=[False])
        print("Trigger collision event patterns setup complete.")

    def handle_collision_event(self, is_enter, entry):
        if self.game_active and not self.game_paused and self.environment_manager:
            if is_enter:
                self.environment_manager.handle_collision_enter(entry)
            else:
                self.environment_manager.handle_collision_exit(entry)

    def _run_collisions(self, task):
        """Runs the main collision traverser for player physics and triggers."""
        if self.game_active and not self.game_paused:
            self.cTrav.traverse(self.render)
        return Task.cont

    def add_collider_to_main_traverser(self, collider_np, handler):
        """Adds a collider and handler to the main traverser (self.cTrav)."""
        if self.cTrav:
            self.cTrav.addCollider(collider_np, handler)
        else:
            print(f"ERROR: Main CollisionTraverser (cTrav) not available to add {collider_np.getName()}")

    def remove_collider_from_main_traverser(self, collider_np):
        """Removes a collider from the main traverser."""
        if self.cTrav:
            self.cTrav.removeCollider(collider_np)

    def _update_hud(self, task):
        """Task to update HUD elements like the minimap."""
        if self.game_active and not self.game_paused and self.player and self.hud:
            if hasattr(self.player, 'player_root') and self.player.player_root and not self.player.player_root.isEmpty():
                try:
                    player_pos = self.player.player_root.getPos(self.render)
                    self.hud.update_minimap(player_pos)
                except Exception as e:
                    print(f"Error updating minimap: {e}")
        return Task.cont

    def userExit(self):
        print("User requested exit.")
        self.cleanup()
        sys.exit()

    def cleanup(self):
        print("Cleaning up ReactiveApp...")
        self.taskMgr.remove("collisionTask")
        self.taskMgr.remove("updateHudTask")
        self.cleanup_game_session()

        if hasattr(self, 'main_menu') and self.main_menu: self.main_menu.cleanup()
        if hasattr(self, 'pause_menu') and self.pause_menu: self.pause_menu.cleanup()
        if hasattr(self, 'options_menu') and self.options_menu: self.options_menu.cleanup()
        if hasattr(self, 'hud') and self.hud: self.hud.cleanup()

        if hasattr(self, 'settings_manager') and self.settings_manager:
             self.settings_manager.save_settings()

        self.ignoreAll()
        
        if hasattr(self, 'cTrav') and self.cTrav:
            self.cTrav.clearColliders()

        print("ReactiveApp cleanup complete.")