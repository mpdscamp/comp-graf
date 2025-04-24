from direct.gui.DirectGui import DirectLabel, DirectButton, DirectFrame
from panda3d.core import NodePath, CardMaker
from direct.task import Task

class PauseMenuUI:
    def __init__(self, app):
        self.app = app

        self.frame = DirectFrame(
            parent=self.app.aspect2d,
            frameSize=(-self.app.getAspectRatio(), self.app.getAspectRatio(), -1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0)
        )

        cm = CardMaker("pause_background")
        cm.setFrameFullscreenQuad()
        background = self.frame.attachNewNode(cm.generate())
        background.setColor(0.1, 0.1, 0.1, 0.7)
        background.setBin('fixed', 40)
        background.setTransparency(True)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setScale(self.app.getAspectRatio() * 1.1, 1, 1.1)


        self.title = DirectLabel(
            parent=self.frame,
            text="PAUSED",
            scale=0.12,
            pos=(0, 0, 0.5),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0)
        )

        button_props = {
            'scale': 0.08,
            'frameColor': (0.2, 0.3, 0.5, 0.7),
            'text_fg': (1, 1, 1, 1),
            'relief': 1,
            'pressEffect': 1
        }

        self.resume_button = DirectButton(
            parent=self.frame,
            text="Resume",
            pos=(0, 0, 0.2),
            command=self.resume_game,
            **button_props
        )

        self.options_button = DirectButton(
            parent=self.frame,
            text="Options",
            pos=(0, 0, 0),
            command=self.schedule_show_options,
            **button_props
        )

        self.main_menu_button = DirectButton(
            parent=self.frame,
            text="Main Menu",
            pos=(0, 0, -0.2),
            command=self.schedule_return_to_main_menu,
            **button_props
        )

        self.hide()

    def show(self):
        print("Showing Pause Menu")
        if not self.app:
            print("Warning: PauseMenuUI.show() called with invalid app reference.")
            return
        self.frame.show()
        self.app._set_menu_mouse_properties()

    def hide(self):
        print("Hiding Pause Menu")
        if hasattr(self, 'frame') and self.frame:
            self.frame.hide()

    def resume_game(self):
        if not self.app: return
        self.app.resume_game()


    def schedule_show_options(self):
        if not self.app: return
        print("Scheduling show options...")
        self.hide()
        self.app.taskMgr.doMethodLater(0.01, self.do_show_options, "task_show_options")

    def do_show_options(self, task):
        if not self.app: return Task.done
        print("Executing show options task...")
        self.app.options_menu.show(from_menu=self)
        return Task.done

    def schedule_return_to_main_menu(self):
        if not self.app: return
        print("Scheduling return to main menu...")
        self.hide()
        self.app.taskMgr.doMethodLater(0.01, self.do_return_to_main_menu, "task_return_to_main")

    def do_return_to_main_menu(self, task):
        if not self.app: return Task.done
        print("Executing return to main menu task...")
        self.app.cleanup_game_session()
        self.app.main_menu.show()
        return Task.done

    def cleanup(self):
        print("Cleaning up Pause Menu...")
        if hasattr(self, 'app') and self.app and self.app.taskMgr:
             self.app.taskMgr.remove("task_show_options")
             self.app.taskMgr.remove("task_return_to_main")
        if hasattr(self, 'frame') and self.frame:
            self.frame.destroy()
        self.frame = None
        self.title = None
        self.resume_button = None
        self.options_button = None
        self.main_menu_button = None
        self.app = None