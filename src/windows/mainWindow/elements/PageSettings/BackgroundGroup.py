"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import Python modules
import cv2
import threading
from loguru import logger as log
from math import floor
from time import sleep

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class BackgroundGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title="Background", description="Applies only to current page", margin_top=15)
        self.add(BackgroundMediaRow(settings_page))


class BackgroundMediaRow(Adw.PreferencesRow):
    def __init__(self, settings_page, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.toggle_box)

        self.toggle_label = Gtk.Label(label="Enable Background", hexpand=True, xalign=0)
        self.toggle_box.append(self.toggle_label)
        self.toggle_switch = Gtk.Switch()
        self.toggle_switch.connect("state-set", self.on_toggle)
        self.toggle_box.append(self.toggle_switch)

        self.media_selector = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.media_selector.set_visible(self.toggle_switch.get_state())
        self.main_box.append(self.media_selector)

        self.media_selector_image = Gtk.Image() # Will be bind to the button by self.set_thumbnail()

        self.media_selector_button = Gtk.Button(label="Select", css_classes=["page-settings-media-selector"])
        self.media_selector_button.connect("clicked", self.choose_with_file_dialog)
        self.media_selector.append(self.media_selector_button)

        self.progress_bar = Gtk.ProgressBar(hexpand=True, margin_top=10, text="Caching...", fraction=0, show_text=True, visible=False)
        self.main_box.append(self.progress_bar)

        self.load_defaults_from_page()

    def load_defaults_from_page(self):
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return
        state = self.settings_page.deck_page.deck_controller.active_page["background"]["show"]
        file_path = self.settings_page.deck_page.deck_controller.active_page["background"]["path"]

        self.toggle_switch.set_active(state)

        if self.settings_page.deck_page.deck_controller.active_page["background"]["path"] in [None, ""]:
            return

        self.set_thumbnail(file_path)

    def on_toggle(self, toggle_switch, state):
        self.media_selector.set_visible(state)
        # Change setting in the active deck page
        self.settings_page.deck_page.deck_controller.active_page["background"]["show"] = state
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.reload_page()

    def choose_with_file_dialog(self, button):
        dialog = ChooseBackgroundDialog(self)

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        # return
        print("abcd")
        print(file_path)
        print(type(gl.media_manager))
        image = gl.media_manager.get_thumbnail(file_path)
        print("finished")
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def set_deck_background(self, file_path):
        # Add background to assets
        asset_id = gl.asset_manager.add(file_path)

        local_path = gl.asset_manager.get_by_id(asset_id)["internal-path"]
        self.set_background_to_page(local_path)

    def set_background_to_page(self, file_path):
        self.settings_page.deck_page.deck_controller.active_page.set_background(file_path)
        self.settings_page.deck_page.deck_controller.reload_page()

        self.update_progress_bar()

    def update_progress_bar(self):
        #TODO: Thread is not the best solution
        def thread(self):
            if self.page_settings.deck_page.deck_controller.set_background_task_id == None:
                return
            # Return if task is directly finished
            progress_dir = self.page_settings.deck_page.deck_controller.media_handler.progress_dir
            if progress_dir[self.page_settings.deck_page.deck_controller.set_background_task_id] >= 1:
                return
            self.progress_bar.set_visible(True)
            while True:
                set_background_task_id = self.page_settings.deck_page.deck_controller.set_background_task_id
                if set_background_task_id == None:
                    print("none")
                progress_dir = self.page_settings.deck_page.deck_controller.media_handler.progress_dir
                self.progress_bar.set_fraction(floor(progress_dir[set_background_task_id]*10)/ 10) # floor to one decimal
                print(progress_dir[set_background_task_id])
                sleep(0.25)

                if progress_dir[set_background_task_id] >= 1:
                    self.progress_bar.set_fraction(1)
                    # Keep the progress bar visible for 2s
                    sleep(2)
                    self.progress_bar.set_visible(False)
                    break

        # Start thread
        threading.Thread(target=thread, args=(self,)).start()



class ChooseBackgroundDialog(Gtk.FileDialog):
    def __init__(self, background_row: BackgroundMediaRow):
        super().__init__(title="Select Background",
                         accept_label="Select")
        self.background_row = background_row
        self.open(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_file = self.open_finish(result)
            file_path = selected_file.get_path()
        except GLib.Error as err:
            log.error(err)
            print("exc")
            return
        
        self.background_row.set_thumbnail(file_path)
        self.background_row.set_deck_background(file_path)