from direct.gui.DirectGui import DirectLabel, DirectButton, DirectFrame
from panda3d.core import NodePath, CardMaker, TextNode

class GameOverUI:
    def __init__(self, app):
        self.app = app

        self.frame = DirectFrame(
            parent=self.app.aspect2d,
            frameSize=(-self.app.getAspectRatio(), self.app.getAspectRatio(), -1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0)
        )

        cm = CardMaker("game_over_background")
        cm.setFrameFullscreenQuad()
        background = self.frame.attachNewNode(cm.generate())
        background.setColor(0.1, 0.05, 0.05, 0.85)  # Dark red tint for death screen
        background.setBin('background', 10)
        background.setTransparency(True)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setScale(self.app.getAspectRatio() * 1.1, 1, 1.1)

        self.title = DirectLabel(
            parent=self.frame,
            text="GAME OVER",
            scale=0.15,
            pos=(0, 0, 0.6),
            text_fg=(1, 0.3, 0.3, 1),  # Red text
            frameColor=(0, 0, 0, 0)
        )
        
        # Time survived label - will be updated when showing the screen
        self.time_label = DirectLabel(
            parent=self.frame,
            text="Time Survived: 0:00",
            scale=0.08,
            pos=(0, 0, 0.3),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0)
        )

        # Message about what happened
        self.death_message = DirectLabel(
            parent=self.frame,
            text="You fell into the void!",
            scale=0.07,
            pos=(0, 0, 0.1),
            text_fg=(1, 0.8, 0.8, 1),
            frameColor=(0, 0, 0, 0)
        )

        button_props = {
            'scale': 0.08,
            'frameColor': (0.6, 0.2, 0.2, 0.7),
            'text_fg': (1, 1, 1, 1),
            'relief': 1,
            'pressEffect': 1
        }

        self.restart_button = DirectButton(
            parent=self.frame,
            text="Try Again",
            pos=(0, 0, -0.1),
            command=self.restart_game,
            **button_props
        )

        self.main_menu_button = DirectButton(
            parent=self.frame,
            text="Main Menu",
            pos=(0, 0, -0.3),
            command=self.return_to_main_menu,
            **button_props
        )

        self.hide()

    def show(self, time_survived=0):
        """
        Show the game over screen with the time survived
        """
        if not self.app:
            print("Warning: GameOverUI.show() called with invalid app reference.")
            return
            
        # Format time as minutes:seconds
        minutes = int(time_survived // 60)
        seconds = int(time_survived % 60)
        self.time_label.setText(f"Time Survived: {minutes}:{seconds:02d}")
        
        self.frame.show()
        self.app._set_menu_mouse_properties()

    def hide(self):
        """Hide the game over screen"""
        if hasattr(self, 'frame') and self.frame:
            self.frame.hide()

    def restart_game(self):
        """Restart the game"""
        if not self.app: 
            return
        
        self.hide()
        # First cleanup the current game session
        self.app.cleanup_game_session()
        # Then start a new game
        self.app.start_game()

    def return_to_main_menu(self):
        """Return to the main menu"""
        if not self.app: 
            return
            
        self.hide()
        self.app.cleanup_game_session()
        self.app.main_menu.show()

    def cleanup(self):
        """Clean up resources"""
        print("Cleaning up Game Over UI...")
        if hasattr(self, 'frame') and self.frame:
            self.frame.destroy()
        self.frame = None
        self.title = None
        self.time_label = None
        self.death_message = None
        self.restart_button = None
        self.main_menu_button = None
        self.app = None