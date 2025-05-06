from panda3d.core import NodePath
from .static_generators.manager import StaticEnvironmentManager
from .reactive_manager import ReactiveManager

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

        self.terrain_update_task = self.app.taskMgr.add(
            self._update_terrain_chunks, "update_terrain_chunks_task"
        )

        num_elements_to_create = 30
        self.reactive_manager.populate_reactive_elements(
            self.static_manager,
            num_elements=num_elements_to_create
        )

        print("EnvironmentManager initialized.")

    def _update_terrain_chunks(self, task):
        """Task that updates visible terrain chunks based on player position"""
        if (self.app.game_paused or not self.app.game_active or 
            not hasattr(self, 'static_manager') or 
            not self.static_manager or
            not hasattr(self.static_manager, 'terrain_generator') or
            not self.static_manager.terrain_generator):
            return task.cont
        
        # Get player position
        player_pos = None
        if self.player and hasattr(self.player, 'player_root') and self.player.player_root:
            player_pos = self.player.player_root.getPos(self.render)
        
        # Update terrain chunks if player position available
        if player_pos:
            self.static_manager.terrain_generator.update_visible_chunks(player_pos)
        
        # Run this task every 0.5 seconds
        return task.again
    
    def set_player(self, player):
        """Set the player reference for terrain updates"""
        self.player = player
        
        # Force an initial terrain update
        if (self.player and hasattr(self.static_manager, 'terrain_generator') and 
            self.static_manager.terrain_generator):
            player_pos = self.player.player_root.getPos(self.render)
            self.static_manager.terrain_generator.update_visible_chunks(player_pos)

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