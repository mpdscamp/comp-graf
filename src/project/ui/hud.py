from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame
from panda3d.core import NodePath, TextNode, Point3

class HeadsUpDisplayUI:
    def __init__(self, app):
        self.app = app

        # Timer tracking
        self.game_time = 0.0
        self.start_time = 0.0
        self.is_timer_active = False

        self.minimap_anchor = self.app.aspect2d.attachNewNode("MinimapAnchor")

        self.minimap_frame_radius = 0.2
        self.minimap_padding = 0.02
        self.minimap_display_radius = self.minimap_frame_radius - self.minimap_padding
        margin = 0.05

        aspect_ratio = self.app.getAspectRatio()
        anchor_x = aspect_ratio - self.minimap_frame_radius - margin
        anchor_z = 1.0 - self.minimap_frame_radius - margin
        self.minimap_anchor.setPos(anchor_x, 0, anchor_z)

        self.crosshair = OnscreenText(
            text="+", pos=(0, 0), scale=0.05, fg=(1, 1, 1, 0.7),
            shadow=(0, 0, 0, 0.5),
            parent=self.app.render2d,
            align = TextNode.ACenter
        )
        self.crosshair.setDepthTest(False); self.crosshair.setDepthWrite(False)

        self.interaction_prompt = OnscreenText(
            text="Press E to interact", pos=(0, -0.7), scale=0.05,
            fg=(1, 1, 1, 0.9), shadow=(0, 0, 0, 0.5), mayChange=True,
            parent=self.app.render2d,
            align=TextNode.ACenter
        )
        self.interaction_prompt.hide()
        
        # Timer display
        self.timer_display = OnscreenText(
            text="Time: 0:00",
            pos=(-aspect_ratio + 0.15, 0.9),  # Top-left corner
            scale=0.05,
            fg=(1, 1, 1, 0.9),
            shadow=(0, 0, 0, 0.5),
            mayChange=True,
            parent=self.app.aspect2d,
            align=TextNode.ALeft
        )
        self.timer_display.setDepthTest(False)
        self.timer_display.setDepthWrite(False)
        self.timer_display.hide()

    def show(self):
        if hasattr(self, 'crosshair') and self.crosshair: self.crosshair.show()
        if hasattr(self, 'minimap') and self.minimap: self.minimap.unstash()
        for label in getattr(self, 'minimap_labels', []):
             if label: label.unstash()

    def hide(self):
        if hasattr(self, 'crosshair') and self.crosshair: self.crosshair.hide()
        if hasattr(self, 'minimap') and self.minimap: self.minimap.stash()
        for label in getattr(self, 'minimap_labels', []):
             if label: label.stash()

    def show_crosshair(self):
        if hasattr(self, 'crosshair') and self.crosshair:
             self.crosshair.show()

    def hide_crosshair(self):
        if hasattr(self, 'crosshair') and self.crosshair:
             self.crosshair.hide()

    def show_interaction_prompt(self, text=None):
        if hasattr(self, 'interaction_prompt') and self.interaction_prompt:
            if text:
                self.interaction_prompt.setText(text)
            self.interaction_prompt.show()

    def hide_interaction_prompt(self):
        if hasattr(self, 'interaction_prompt') and self.interaction_prompt:
             self.interaction_prompt.hide()

    def update_minimap(self, player_pos_world):
        if not hasattr(self, 'player_indicator') or not self.player_indicator:
            return
        if not self.app or not hasattr(self.app, 'settings_manager'):
             print("Warning: HUD cannot access app or settings_manager for minimap update.")
             return

        terrain_size = self.app.settings_manager.get_constant('environment', 'TERRAIN_SIZE', 200.0)
        half_terrain = terrain_size / 2.0
        if half_terrain <= 0:
             return

        scale_factor = self.minimap_display_radius / half_terrain

        indicator_x = player_pos_world.x * scale_factor
        indicator_y = player_pos_world.y * scale_factor

        indicator_x = max(-self.minimap_display_radius, min(self.minimap_display_radius, indicator_x))
        indicator_y = max(-self.minimap_display_radius, min(self.minimap_display_radius, indicator_y))

        self.player_indicator.setPos(indicator_x, 0, indicator_y)

    def cleanup(self):
        print("Cleaning up HUD...")
        for label in getattr(self, 'minimap_labels', []):
             if label: label.destroy()
        self.minimap_labels = []
        self.north_label = None; self.south_label = None; self.east_label = None; self.west_label = None

        if hasattr(self, 'crosshair') and self.crosshair: self.crosshair.destroy(); self.crosshair = None
        if hasattr(self, 'interaction_prompt') and self.interaction_prompt: self.interaction_prompt.destroy(); self.interaction_prompt = None
        if hasattr(self, 'player_indicator') and self.player_indicator: self.player_indicator.destroy(); self.player_indicator = None
        if hasattr(self, 'minimap') and self.minimap: self.minimap.destroy(); self.minimap = None

        if hasattr(self, 'minimap_anchor') and self.minimap_anchor and not self.minimap_anchor.isEmpty():
            self.minimap_anchor.removeNode()
        self.minimap_anchor = None

        if hasattr(self, 'root') and self.root and not self.root.isEmpty():
             print("Warning: Old HUDRoot node still exists during cleanup.")
             self.root.removeNode()
        self.root = None
        self.app = None