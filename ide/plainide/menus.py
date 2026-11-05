"""The menu bar."""

import os
import tkinter as tk

from .paths import ROOT
from .theme import THEMES


def build_menu(app):
    menu = tk.Menu(app.root)
    docs, projects = app.documents, app.projects

    file_menu = tk.Menu(menu, tearoff=False)
    file_menu.add_command(label="New tab", accelerator="Ctrl+N", command=lambda: docs.new())
    file_menu.add_command(label="New file in project...", command=lambda: app.explorer.new_entry())
    file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=docs.open_dialog)
    file_menu.add_command(label="Go to file...", accelerator="Ctrl+P", command=app.quick_open)
    file_menu.add_separator()
    file_menu.add_command(label="New project...", command=projects.new_dialog)
    file_menu.add_command(label="Open project...", command=projects.open_dialog)
    app.recent_menu = tk.Menu(file_menu, tearoff=False, postcommand=lambda: fill_recent(app))
    file_menu.add_cascade(label="Open recent project", menu=app.recent_menu)
    file_menu.add_command(label="Open folder...", command=projects.open_folder_dialog)
    file_menu.add_command(label="Close project", command=projects.close)
    file_menu.add_separator()
    file_menu.add_command(label="Save", accelerator="Ctrl+S", command=docs.save)
    file_menu.add_command(label="Save as...", accelerator="Ctrl+Shift+S", command=docs.save_as)
    file_menu.add_command(label="Save all", command=docs.save_all)
    file_menu.add_separator()
    file_menu.add_command(label="Close tab", accelerator="Ctrl+W", command=docs.close)
    file_menu.add_command(label="Exit", command=app.quit)
    menu.add_cascade(label="File", menu=file_menu)

    edit_menu = tk.Menu(menu, tearoff=False)
    edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=app.undo)
    edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=lambda: app.undo(redo=True))
    edit_menu.add_separator()
    edit_menu.add_command(label="Find...", accelerator="Ctrl+F", command=app.find)
    edit_menu.add_command(label="Replace...", accelerator="Ctrl+H", command=lambda: app.find(replace=True))
    edit_menu.add_command(label="Find next", accelerator="F3", command=lambda: app.find_step(1))
    edit_menu.add_command(label="Find previous", accelerator="Shift+F3", command=lambda: app.find_step(-1))
    edit_menu.add_separator()
    edit_menu.add_command(label="Go to line...", accelerator="Ctrl+G", command=app.go_to_line)
    menu.add_cascade(label="Edit", menu=edit_menu)

    examples_menu = tk.Menu(menu, tearoff=False)
    examples = os.path.join(ROOT, "examples")
    if os.path.isdir(examples):
        for name in sorted(os.listdir(examples)):
            if name.endswith(".plain"):
                examples_menu.add_command(label=name[:-6],
                                          command=lambda n=name: docs.open_example(os.path.join(examples, n)))
    menu.add_cascade(label="Examples", menu=examples_menu)

    run_menu = tk.Menu(menu, tearoff=False)
    run_menu.add_command(label="Run", accelerator="F5", command=app.running.run)
    run_menu.add_command(label="Stop", accelerator="Shift+F5", command=app.running.stop)
    menu.add_cascade(label="Run", menu=run_menu)

    build_menu = tk.Menu(menu, tearoff=False)
    build_menu.add_command(label="Build Python file", accelerator="F6", command=app.building.build)
    build_menu.add_command(label="Release: make a program (exe)", accelerator="F7", command=app.building.release)
    build_menu.add_separator()
    build_menu.add_command(label="Show build folder", command=app.building.show_folder)
    build_menu.add_command(label="Project settings...", command=projects.settings)
    menu.add_cascade(label="Build", menu=build_menu)

    view_menu = tk.Menu(menu, tearoff=False)
    view_menu.add_command(label="Explorer", accelerator="Ctrl+Shift+E", command=app.focus_explorer)
    view_menu.add_command(label="Show / hide the sidebar", accelerator="Ctrl+B", command=app.toggle_sidebar)
    view_menu.add_separator()
    view_menu.add_command(label="Bigger text", accelerator="Ctrl++", command=lambda: app.zoom(1))
    view_menu.add_command(label="Smaller text", accelerator="Ctrl+-", command=lambda: app.zoom(-1))
    view_menu.add_separator()
    app.theme_var = tk.StringVar(master=app.root, value=app.theme_name)
    for name in THEMES:
        view_menu.add_radiobutton(label=f"{name} theme", variable=app.theme_var, value=name,
                                  command=lambda n=name: app.apply_theme(n))
    view_menu.add_separator()
    view_menu.add_checkbutton(label="Live values in the code", variable=app.live_var)
    view_menu.add_checkbutton(label="List of values", variable=app.watch_var, command=app.toggle_values)
    menu.add_cascade(label="View", menu=view_menu)

    help_menu = tk.Menu(menu, tearoff=False)
    help_menu.add_command(label="Quick reference", accelerator="F1", command=app.show_help)
    help_menu.add_command(label="Open crash log folder", command=app.session.open_data_folder)
    menu.add_cascade(label="Help", menu=help_menu)
    return menu


def fill_recent(app):
    menu = app.recent_menu
    menu.delete(0, "end")
    paths = app.projects.recent()
    for path in paths:
        label = f"{os.path.splitext(os.path.basename(path))[0]}    ({os.path.dirname(path)})"
        menu.add_command(label=label, command=lambda p=path: app.projects.open_info_file(p))
    if paths:
        menu.add_separator()
        menu.add_command(label="Clear this list", command=app.projects.clear_recent)
    else:
        menu.add_command(label="(no projects yet)", state="disabled")
