from direct.gui.DirectGui import DirectLabel, DirectButton, DirectSlider, DirectOptionMenu, DirectFrame
from panda3d.core import NodePath, CardMaker, TextNode, WindowProperties

class OptionsMenuUI:
    def __init__(self, app):
        self.app = app

        self.frame = DirectFrame(
            parent=self.app.aspect2d,
            frameSize=(-self.app.getAspectRatio(), self.app.getAspectRatio(), -1, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0)
        )

        cm = CardMaker("options_background")
        cm.setFrameFullscreenQuad()
        background = self.frame.attachNewNode(cm.generate())
        background.setColor(0.1, 0.15, 0.2, 0.9)
        background.setBin('background', 10)
        background.setTransparency(True)
        background.setDepthTest(False)
        background.setDepthWrite(False)
        background.setScale(self.app.getAspectRatio() * 1.1, 1, 1.1)

        self.title = DirectLabel(
            parent=self.frame,
            text="OPTIONS",
            scale=0.12,
            pos=(0, 0, 0.8),
            text_fg=(1, 1, 1, 1),
            frameColor=(0, 0, 0, 0)
        )

        self.sens_label = DirectLabel(
            parent=self.frame,
            text="Mouse Sensitivity:",
            scale=0.07,
            pos=(-0.6, 0, 0.5),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0)
        )
        self.min_sens = 1.0
        self.max_sens = 100.0
        initial_sens = self.app.settings_manager.get_effective_sensitivity()
        initial_sens_normalized = max(0, min(1,
            (initial_sens - self.min_sens) / max(0.01, (self.max_sens - self.min_sens))
        ))
        self.sensitivity_slider = DirectSlider(
            parent=self.frame,
            pos=(0.3, 0, 0.475),
            scale=0.4,
            value=initial_sens_normalized,
            pageSize=0.1,
            thumb_relief=1,
            thumb_frameColor=(0.6, 0.6, 0.8, 1),
            frameColor=(0.2, 0.3, 0.5, 0.7),
            command=self.update_sensitivity
        )
        self.sens_value_label = DirectLabel(
             parent=self.frame,
             text=f"{initial_sens:.1f}",
             scale=0.06,
             pos=(0.75, 0, 0.5),
             text_fg=(1, 1, 1, 1),
             text_align=TextNode.ARight,
             frameColor=(0, 0, 0, 0)
        )

        self.fov_label = DirectLabel(
            parent=self.frame, text="Field of View (FOV):", scale=0.07, pos=(-0.6, 0, 0.4),
            text_fg=(1, 1, 1, 1), text_align=TextNode.ALeft, frameColor=(0, 0, 0, 0)
        )
        self.min_fov = self.app.settings_manager.get_constant('camera', 'MIN_FOV', 60.0)
        self.max_fov = self.app.settings_manager.get_constant('camera', 'MAX_FOV', 110.0)
        initial_fov = self.app.settings_manager.get_fov()
        fov_range = max(0.01, self.max_fov - self.min_fov)
        initial_fov_normalized = max(0, min(1, (initial_fov - self.min_fov) / fov_range))

        self.fov_slider = DirectSlider(
            parent=self.frame, pos=(0.3, 0, 0.375), scale=0.4,
            value=initial_fov_normalized, pageSize=0.1, thumb_relief=1,
            thumb_frameColor=(0.6, 0.8, 0.6, 1),
            frameColor=(0.2, 0.5, 0.3, 0.7),
            command=self.update_fov
        )
        self.fov_value_label = DirectLabel(
             parent=self.frame, text=f"{initial_fov:.0f}", scale=0.06, pos=(0.75, 0, 0.45),
             text_fg=(1, 1, 1, 1), text_align=TextNode.ARight, frameColor=(0, 0, 0, 0)
        )

        self.res_label = DirectLabel(
            parent=self.frame,
            text="Resolution:",
            scale=0.07,
            pos=(-0.6, 0, 0.3),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0)
        )
        self.resolutions = ["800x600", "1024x768", "1280x720", "1600x900", "1920x1080"]
        try:
            default_res = self.app.settings_manager._default_settings['user_settings']['resolution']
            initial_res_str = self.app.settings_manager.get_user_setting('resolution', default_res)
            initial_item_index = self.resolutions.index(initial_res_str)
        except (ValueError, KeyError):
             initial_item_index = 2
        self.resolution_menu = DirectOptionMenu(
            parent=self.frame,
            pos=(0.3, 0, 0.275),
            scale=0.08,
            items=self.resolutions,
            initialitem=initial_item_index,
            command=self.change_resolution,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.3, 0.5, 0.7),
            highlightColor=(0.4, 0.5, 0.8, 1),
            relief=1
        )

        self.fullscreen_button = DirectButton(
            parent=self.frame,
            text="Toggle Fullscreen",
            scale=0.08,
            pos=(0, 0, 0.1),
            command=self.toggle_fullscreen,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.3, 0.5, 0.7),
            relief=1,
            pressEffect=1
        )

        self.camera_mode_label = DirectLabel(
            parent=self.frame,
            text="Camera Mode:",
            scale=0.07,
            pos=(-0.6, 0, -0.1),
            text_fg=(1, 1, 1, 1),
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0)
        )

        self.camera_modes = ["Third-Person", "First-Person"]
        try:
            default_mode = 0
            current_mode = self.app.settings_manager.get_user_setting('camera_mode', default_mode)
            initial_item_index = current_mode
        except (ValueError, KeyError):
            initial_item_index = 0

        self.camera_mode_menu = DirectOptionMenu(
            parent=self.frame,
            pos=(0.3, 0, -0.09),
            scale=0.08,
            items=self.camera_modes,
            initialitem=initial_item_index,
            command=self.change_camera_mode,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.3, 0.5, 0.7),
            highlightColor=(0.4, 0.5, 0.8, 1),
            relief=1
        )

        self.back_button = DirectButton(
            parent=self.frame,
            text="Back",
            scale=0.09,
            pos=(0, 0, -0.7),
            command=self.back_to_previous,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.5, 0.2, 0.2, 0.8),
            relief=1,
            pressEffect=1
        )

        self.previous_menu = None
        self.hide()

    def show(self, from_menu=None):
        print("Showing Options Menu")
        if not self.app or not hasattr(self, 'frame') or not self.frame:
             print("Warning: OptionsMenuUI.show() called with invalid app or frame reference.")
             return
        self.frame.show()

        if from_menu: self.previous_menu = from_menu

        current_sens = self.app.settings_manager.get_effective_sensitivity()
        if hasattr(self, 'sensitivity_slider') and self.sensitivity_slider:
            current_sens_normalized = max(0, min(1, (current_sens - self.min_sens) / max(0.01, (self.max_sens - self.min_sens))))
            self.sensitivity_slider['value'] = current_sens_normalized
        else: print("Warning: Sensitivity slider not found in OptionsMenuUI.show()")

        if hasattr(self, 'sens_value_label') and self.sens_value_label:
             self.sens_value_label['text'] = f"{current_sens:.1f}"
        else: print("Warning: Sensitivity value label not found in OptionsMenuUI.show()")

        current_fov = self.app.settings_manager.get_fov()
        if hasattr(self, 'fov_slider') and self.fov_slider:
            fov_range = max(0.01, self.max_fov - self.min_fov)
            current_fov_normalized = max(0, min(1, (current_fov - self.min_fov) / fov_range))
            self.fov_slider.setValue(current_fov_normalized)
        else: print("Warning: FOV slider not found in OptionsMenuUI.show()")
        if hasattr(self, 'fov_value_label') and self.fov_value_label:
             self.fov_value_label['text'] = f"{current_fov:.0f}"
        else: print("Warning: FOV value label not found in OptionsMenuUI.show()")

        if hasattr(self, 'resolution_menu') and self.resolution_menu and self.app.win:
            try:
                props = self.app.win.getProperties()
                if props.hasSize():
                    current_res_str = f"{props.getXSize()}x{props.getYSize()}"
                    initial_item_index = self.resolutions.index(current_res_str) if current_res_str in self.resolutions else 2
                    self.resolution_menu.set(initial_item_index, fCommand=0)
                else:
                     print("Warning: Window has no size property in OptionsMenuUI.show()")
                     self.resolution_menu.set(2, fCommand=0)
            except Exception as e:
                print(f"Could not update resolution menu: {e}")
                self.resolution_menu.set(2, fCommand=0)
        else: print("Warning: Resolution menu or app window not found in OptionsMenuUI.show()")


        if hasattr(self, 'fullscreen_button') and self.fullscreen_button and self.app.win:
            try:
                props = self.app.win.getProperties()
                if props.hasFullscreen():
                    is_fullscreen = props.getFullscreen()
                    self.fullscreen_button['text'] = f"Fullscreen: {'ON' if is_fullscreen else 'OFF'}"
                else:
                     print("Warning: Window has no fullscreen property in OptionsMenuUI.show()")
                     self.fullscreen_button['text'] = "Fullscreen: UNKNOWN"
            except Exception as e:
                print(f"Could not get fullscreen property: {e}")
                self.fullscreen_button['text'] = "Fullscreen: UNKNOWN"
        else: print("Warning: Fullscreen button or app window not found in OptionsMenuUI.show()")

        if hasattr(self, 'camera_mode_menu') and self.camera_mode_menu:
            try:
                current_mode = self.app.settings_manager.get_user_setting('camera_mode', 0)
                self.camera_mode_menu.set(current_mode, fCommand=0)
            except Exception as e:
                print(f"Could not update camera mode menu: {e}")
                self.camera_mode_menu.set(0, fCommand=0)
        else:
            print("Warning: Camera mode menu not found in OptionsMenuUI.show()")

        self.app._set_menu_mouse_properties()

    def hide(self):
        print("Hiding Options Menu")
        if hasattr(self, 'frame') and self.frame:
            self.frame.hide()

    def back_to_previous(self):
        print("Options Back button pressed")
        self.hide()
        if self.previous_menu and hasattr(self.previous_menu, 'show'):
            print(f"Returning to {type(self.previous_menu).__name__}")
            if hasattr(self.previous_menu, 'frame') and self.previous_menu.frame:
                 self.previous_menu.show()
            else:
                 print("Warning: Previous menu seems destroyed, returning to Main Menu")
                 if self.app and self.app.main_menu: self.app.main_menu.show()

        elif self.app and self.app.main_menu:
            print("No valid previous menu found, returning to Main Menu")
            self.app.main_menu.show()
        else:
            print("Error: Cannot return to previous menu or main menu.")


    def update_sensitivity(self):
        if not hasattr(self, 'sensitivity_slider') or not self.sensitivity_slider: return

        value = self.sensitivity_slider['value']
        new_sensitivity = round(max(self.min_sens, min(self.max_sens, self.min_sens + value * (self.max_sens - self.min_sens))), 1)
        print(f"Updating sensitivity to: {new_sensitivity}")

        self.app.settings_manager.user_settings['sensitivity'] = new_sensitivity

        if hasattr(self, 'sens_value_label') and self.sens_value_label:
            self.sens_value_label['text'] = f"{new_sensitivity:.1f}"

        self.app.settings_manager.save_settings()

    def update_fov(self):
        if not hasattr(self, 'fov_slider') or not self.fov_slider: return

        value = self.fov_slider['value']
        fov_range = max(0.01, self.max_fov - self.min_fov)
        new_fov = round(self.min_fov + value * fov_range, 0)
        new_fov = max(self.min_fov, min(self.max_fov, new_fov))

        self.app.settings_manager.user_settings['fov'] = new_fov

        if hasattr(self, 'fov_value_label') and self.fov_value_label:
            self.fov_value_label['text'] = f"{new_fov:.0f}"

        if self.app.game_active and hasattr(self.app, 'camera_system') and self.app.camera_system:
            self.app.camera_system.set_fov(new_fov)

    def change_resolution(self, resolution_str):
        print(f"Changing resolution to: {resolution_str}")
        if not self.app.win: return
        try:
            width, height = map(int, resolution_str.split('x'))
            props = WindowProperties(); props.setSize(width, height)
            self.app.win.requestProperties(props)
            self.app.settings_manager.user_settings['resolution'] = resolution_str
            self.app.settings_manager.save_settings()
        except Exception as e: print(f"Error changing resolution: {e}")

    def toggle_fullscreen(self):
        if not self.app.win: return
        try:
             props = self.app.win.getProperties()
             if not props.hasFullscreen():
                  print("Warning: Cannot get fullscreen property.")
                  return
             is_fullscreen = props.getFullscreen()
             new_fullscreen_state = not is_fullscreen
             props = WindowProperties(); props.setFullscreen(new_fullscreen_state)
             print(f"Toggling fullscreen to: {new_fullscreen_state}")
             self.app.win.requestProperties(props)

             if hasattr(self, 'fullscreen_button') and self.fullscreen_button:
                  self.fullscreen_button['text'] = f"Fullscreen: {'ON' if new_fullscreen_state else 'OFF'}"

             self.app.settings_manager.user_settings['fullscreen'] = new_fullscreen_state
             self.app.settings_manager.save_settings()
        except Exception as e: print(f"Error toggling fullscreen: {e}")

    def change_camera_mode(self, mode_str):
        print(f"Changing camera mode to: {mode_str}")
        mode_index = self.camera_modes.index(mode_str)
        self.app.settings_manager.user_settings['camera_mode'] = mode_index
        self.app.settings_manager.save_settings()
        
        if self.app.game_active and hasattr(self.app, 'camera_system') and self.app.camera_system:
            if mode_index == self.app.camera_system.FIRST_PERSON:
                self.app.camera_system.set_first_person_mode()
            else:
                self.app.camera_system.set_third_person_mode()

    def cleanup(self):
        print("Cleaning up Options Menu...")
        if hasattr(self, 'frame') and self.frame:
            self.frame.destroy()
        self.frame = None
        self.title = None; self.sens_label = None; self.sensitivity_slider = None
        self.sens_value_label = None; self.res_label = None; self.resolution_menu = None
        self.fov_label = None; self.fov_slider = None; self.fov_value_label = None
        self.fullscreen_button = None; self.back_button = None
        self.camera_mode_label = None
        self.camera_mode_menu = None
        self.previous_menu = None; self.app = None