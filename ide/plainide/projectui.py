"""The project of the IDE: which folder is open, and everything you can do with it.

A project is a folder with a .plainproject file (see projects.py). A folder without that file can be
opened too; it becomes a project when you build or change the project settings.
"""

import os
from tkinter import filedialog, messagebox

from . import TITLE
from . import projects as PROJECTS
from .dialogs import project_settings_dialog
from .documents import same_path
from .language import NEW_PROGRAM
from .paths import DATA_DIR


class ProjectController:
    def __init__(self, app):
        self.app = app
        self.folder = None          # the folder shown in the Explorer
        self.info = None            # its project definition (a .plainproject file), if it has one

    # ---- opening and closing ---------------------------------------------------

    def open_folder(self, folder):
        self.folder = os.path.abspath(folder)
        self.info = PROJECTS.Project.find(self.folder)
        if self.info:
            PROJECTS.add_recent(DATA_DIR, self.info.path)
        self.changed(show_explorer=True)

    def close(self):
        self.folder = None
        self.info = None
        self.app.explorer.seen.clear()
        self.changed()

    def changed(self, show_explorer=False):
        """Tell the rest of the IDE that the project is another one, or has other settings."""
        self.app.explorer.refresh()
        if show_explorer:
            self.app.show_view("explorer")
        self.app.update_titles()

    def open_folder_dialog(self):
        folder = filedialog.askdirectory(title="Open a folder with Plain programs")
        if folder:
            self.open_folder(folder)

    def open_dialog(self):
        path = filedialog.askopenfilename(title="Open a Plain project",
                                          filetypes=[("Plain projects", "*" + PROJECTS.EXT), ("All files", "*.*")])
        if path:
            self.open_info_file(path)

    def open_info_file(self, path):
        """Open the project that a .plainproject file describes, and its main program."""
        try:
            info = PROJECTS.Project.load(path)
        except ValueError as exc:
            messagebox.showerror(TITLE, str(exc))
            return False
        self.open_folder(info.folder)
        if self.info is None:       # the file has another name than the one the folder holds
            self.info = info
            PROJECTS.add_recent(DATA_DIR, path)
            self.changed()
        if os.path.isfile(self.info.main_path):
            self.app.documents.open_path(self.info.main_path)
        return True

    def recent(self):
        return PROJECTS.recent_projects(DATA_DIR)

    def clear_recent(self):
        PROJECTS.clear_recent(DATA_DIR)

    # ---- making a project -------------------------------------------------------

    def new_dialog(self, tab=None):
        """Make a project in a folder you choose. With a tab: the program in it becomes the main program."""
        folder = filedialog.askdirectory(title="Choose the folder for your project (make a new one if you like)",
                                         mustexist=False)
        if not folder:
            return False
        folder = os.path.abspath(folder)
        os.makedirs(folder, exist_ok=True)
        info = PROJECTS.Project.find(folder)
        if info is None:
            name = os.path.basename(folder) or "program"
            main = "main.plain"
            if tab is not None and tab.path and os.path.dirname(os.path.abspath(tab.path)) == folder:
                main = os.path.basename(tab.path)
            info = PROJECTS.Project(folder, name, main)
            try:
                info.save()
            except OSError as exc:
                messagebox.showerror(TITLE, f"I cannot create the project: {exc.strerror}")
                return False
        if tab is not None and tab.path is None:
            target = info.main_path
            if os.path.exists(target):
                n = 2
                while os.path.exists(os.path.join(folder, f"program{n}.plain")):
                    n += 1
                target = os.path.join(folder, f"program{n}.plain")
            if not self.app.documents.write(tab, target):
                return False
        elif tab is None and not os.path.exists(info.main_path):
            try:
                with open(info.main_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(NEW_PROGRAM)
            except OSError as exc:
                messagebox.showerror(TITLE, f"I cannot create the program: {exc.strerror}")
                return False
        self.open_folder(folder)
        if tab is None and os.path.isfile(info.main_path):
            self.app.documents.open_path(info.main_path)
        self.app.output.write(f"Project '{info.name}' is ready in {folder}\n", "info")
        return True

    def make_here(self):
        """Builds need a project. Turn the open folder into one, or ask for a folder."""
        doc = self.app.documents.current()
        if self.folder is None and doc is not None and doc.path:
            self.open_folder(os.path.dirname(os.path.abspath(doc.path)))      # the folder of the program
            if self.info:
                return True
        if self.folder is None:
            return self.new_dialog(doc if doc is not None and doc.path is None else None) and self.info is not None
        if not messagebox.askyesno(TITLE, "This folder is not a project yet.\n\nMake it a project, so that the "
                                          "program can be built?"):
            return False
        main = "main.plain"
        if doc is not None and doc.path and os.path.dirname(os.path.abspath(doc.path)) == self.folder:
            main = os.path.basename(doc.path)
        elif not os.path.exists(os.path.join(self.folder, main)) and self.files():
            main = self.files()[0]
        info = PROJECTS.Project(self.folder, os.path.basename(self.folder), main)
        try:
            info.save()
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot create the project: {exc.strerror}")
            return False
        self.open_folder(self.folder)
        return True

    def files(self):
        return PROJECTS.Project(self.folder).plain_files() if self.folder else []

    # ---- changing the project ---------------------------------------------------

    def settings(self):
        if self.info is None and not self.make_here():
            return
        project_settings_dialog(self.app, self.info, self.after_settings)

    def after_settings(self, old_path):
        info = self.info
        PROJECTS.add_recent(DATA_DIR, info.path)
        # the project file may have a new name: a tab that shows it follows
        if old_path != info.path:
            self.app.documents.path_renamed(old_path, info.path)
        self.changed()

    def set_main(self, path):
        """Make a program the main program: the one that Build and Release use."""
        if self.info is None and not self.make_here():
            return
        info = self.info
        info.main = os.path.relpath(path, info.folder).replace("\\", "/")
        try:
            info.save()
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot save the project: {exc.strerror}")
            return
        self.app.output.write(f"The main program is now {info.main}\n", "info")
        self.changed()

    def path_renamed(self, old, new):
        """A file or folder was renamed in the Explorer: the main program follows."""
        info = self.info
        if info is None:
            return
        main = os.path.normcase(info.main_path)
        base = os.path.normcase(os.path.abspath(old))
        if main == base:
            info.main = os.path.relpath(new, info.folder).replace("\\", "/")
        elif main.startswith(base + os.sep):
            info.main = os.path.relpath(os.path.join(new, os.path.relpath(info.main_path, old)),
                                        info.folder).replace("\\", "/")
        else:
            return
        try:
            info.save()
        except OSError:
            pass

    def file_saved(self, path):
        """The project file was edited as text and saved: read it again."""
        if not path.endswith(PROJECTS.EXT) or self.folder is None:
            return
        if os.path.dirname(os.path.abspath(path)) != self.folder:
            return
        try:
            info = PROJECTS.Project.load(path)
        except ValueError as exc:
            self.app.output.write(f"The project file has a mistake: {exc}\n", "err")
            self.app.status.set("Project file has a mistake", False)
            return
        self.info = info
        PROJECTS.add_recent(DATA_DIR, info.path)
        self.app.output.write(f"Project '{info.name}' updated (main program: {info.main})\n", "info")
        self.changed()
