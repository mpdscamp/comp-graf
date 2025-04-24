from direct.gui.DirectGui import DirectLabel, DirectButton, DirectFrame
from panda3d.core import NodePath, CardMaker, TextNode

class MainMenuUI:
    def __init__(self, app):
        self.app = app

        self.frame = DirectFrame(
            parent=self.app.aspect2d,
            frameSize=(-1, 1, -1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0)
        )

        cm = CardMaker("menu_background")
        cm.setFrameFullscreenQuad()
        self.frame['frameSize'] = (-self.app.getAspectRatio(), self.app.getAspectRatio(), -1, 1)
        background = self.frame.attachNewNode(cm.generate())
        background.setColor(0.1, 0.2, 0.4, 1)
        background.setBin('background', 10)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setScale(self.app.getAspectRatio() * 1.1, 1, 1.1)


        self.title = DirectLabel(
            parent=self.frame,
            text="Abstract Ascent",
            scale=0.1,
            pos=(0, 0, 0.5),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0)
        )

        button_props = {
            'scale': 0.07,
            'frameColor': (0.2, 0.3, 0.5, 0.7),
            'text_fg': (1, 1, 1, 1),
            'relief': 1,
            'pressEffect': 1
        }

        self.start_button = DirectButton(
            parent=self.frame,
            text="Start Game",
            pos=(0, 0, 0.2),
            command=self.app.start_game,
            **button_props
        )

        self.options_button = DirectButton(
            parent=self.frame,
            text="Options",
            pos=(0, 0, 0),
            command=self.show_options,
             **button_props
        )

        self.quit_button = DirectButton(
            parent=self.frame,
            text="Quit",
            pos=(0, 0, -0.2),
            command=self.app.userExit,
             **button_props
        )

        self.hide()

    def show(self):
        print("--- MainMenuUI.show() called ---")
        self.frame.show()
        self.app._set_menu_mouse_properties()

    def hide(self):
        print("--- MainMenuUI.hide() called ---")
        self.frame.hide()

    def show_options(self):
        self.hide()
        self.app.options_menu.show(from_menu=self)

    def cleanup(self):
        print("Cleaning up Main Menu...")
        if hasattr(self, 'frame') and self.frame:
            self.frame.destroy()
        self.frame = None
        self.title = None
        self.start_button = None
        self.options_button = None
        self.quit_button = None
        self.app = None