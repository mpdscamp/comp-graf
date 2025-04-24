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

        num_elements_to_create = 30
        self.reactive_manager.populate_reactive_elements(
            self.static_manager,
            num_elements=num_elements_to_create
        )

        print("EnvironmentManager initialized with refactored components.")

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