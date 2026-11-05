"""The EXPLORER: the files of the project as a tree, like Visual Studio Code.

Right click for New file, New folder, Rename, Delete, Set as main program. F2 renames, Delete deletes,
Enter opens. The tree keeps its open folders when it refreshes and notices changes made outside the IDE.
Names are typed right in the tree (like in VS Code), not in a dialog.
"""

import os
import shutil
import tkinter as tk
from itertools import islice
from tkinter import messagebox, ttk

from . import TITLE
from .language import NEW_PROGRAM
from .paths import open_in_file_manager
from .projects import EXT
from .theme import style_menu

HIDDEN_FOLDERS = {"__pycache__", "node_modules", "build", "dist"}
HIDDEN_SUFFIXES = (".pyc", ".pyo")
MAX_DEPTH = 8
MAX_ITEMS = 3000
BAD_NAME_CHARACTERS = '\\/:*?"<>|'
INDENT = 20


def check_name(name, folder, current=None):
    """Why a file name cannot be used, in plain words (None when it is fine)."""
    if not name:
        return "The name is empty."
    if name.startswith("."):
        return "A name cannot start with a dot (such files are hidden)."
    if name != name.strip() or name.endswith("."):
        return "This is not a good name for a file."
    bad = [c for c in BAD_NAME_CHARACTERS if c in name]
    if bad:
        return f"A name cannot contain {' '.join(bad)}"
    target = os.path.join(folder, name)
    if os.path.exists(target) and not (current and os.path.normcase(target) == os.path.normcase(current)
                                       and name == os.path.basename(current)):
        return f"'{name}' already exists here."
    return None


class Explorer(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, style="Side.TFrame")
        self.app = app
        self.edit = None            # the entry for a name typed in the tree
        self.seen = set()           # folders that have been shown once (new ones start open)
        self.signature = None
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # header: EXPLORER and the four action buttons
        head = ttk.Frame(self, style="Side.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        ttk.Label(head, text="EXPLORER", style="SideHead.TLabel", padding=(12, 8, 6, 2)).pack(side="left")
        self.actions = []
        for key, tip, command in (("collapse", "Collapse all", self.collapse_all),
                                  ("refresh", "Refresh", self.refresh),
                                  ("new_folder", "New folder", lambda: self.new_entry(is_dir=True)),
                                  ("new_file", "New file", lambda: self.new_entry(is_dir=False))):
            button = tk.Label(head, bd=0, padx=4, pady=2, cursor="hand2")
            button.pack(side="right", padx=(0, 2), pady=(5, 0))
            button.bind("<Button-1>", lambda e, c=command: c())
            button.bind("<Enter>", lambda e, b=button: b.config(bg=self.app.theme["button_hover"]))
            button.bind("<Leave>", lambda e, b=button: b.config(bg=self.app.theme["side_bg"]))
            self.actions.append((button, key))
        self.title = ttk.Label(self, text="", style="SideTitle.TLabel", padding=(12, 4, 6, 6))
        self.title.grid(row=1, column=0, sticky="ew")

        # the tree and the welcome text (shown while no project is open)
        self.body = ttk.Frame(self, style="Side.TFrame")
        self.body.grid(row=2, column=0, sticky="nsew")
        self.body.rowconfigure(0, weight=1)
        self.body.columnconfigure(0, weight=1)
        self.tree_frame = ttk.Frame(self.body, style="Side.TFrame")
        self.tree = ttk.Treeview(self.tree_frame, show="tree", selectmode="browse", columns=("path", "kind"),
                                 displaycolumns=())
        scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.config(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.welcome = ttk.Frame(self.body, style="Side.TFrame", padding=(14, 12))
        self.tree_frame.grid(row=0, column=0, sticky="nsew")
        self.welcome.grid(row=0, column=0, sticky="nsew")

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Return>", lambda e: self.open_selected())
        self.tree.bind("<F2>", lambda e: self.rename())
        self.tree.bind("<Delete>", lambda e: self.delete())
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<Button-1>", self.on_click, add="+")
        self.tree.bind("<<TreeviewOpen>>", lambda e: self.set_folder_icon(opened=True))
        self.tree.bind("<<TreeviewClose>>", lambda e: self.set_folder_icon(opened=False))
        self.menu = tk.Menu(self, tearoff=False)
        self.restyle()
        self.refresh()
        self.after(2000, self.poll)

    # ---- look ----------------------------------------------------------------

    def restyle(self):
        t, icons = self.app.theme, self.app.icons
        for button, key in self.actions:
            button.config(image=getattr(icons, key), bg=t["side_bg"])
        self.tree.tag_configure("main", font=self.app.ui_bold)
        self.tree.tag_configure("other", foreground=t["out_info"])
        style_menu(self.menu, t)
        self.refresh()

    def icon_for(self, path, kind):
        icons = self.app.icons
        if kind == "dir":
            return icons.folder
        if kind == "project":
            return icons.project
        if path.endswith(".plain"):
            return icons.plain_main if self.is_main(path) else icons.plain
        return icons.file

    def is_main(self, path):
        info = self.app.projects.info
        return bool(info) and os.path.normcase(os.path.abspath(path)) == os.path.normcase(info.main_path)

    # ---- filling the tree ----------------------------------------------------

    def list_folder(self, folder):
        """The visible entries of a folder: folders first, then files, each sorted by name."""
        try:
            entries = list(os.scandir(folder))
        except OSError:
            return []
        shown = []
        for entry in entries:
            name = entry.name
            if name.startswith(".") or name.endswith(HIDDEN_SUFFIXES):
                continue
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue
            if is_dir and name in HIDDEN_FOLDERS:
                continue
            shown.append((not is_dir, name.lower(), name, entry.path, is_dir))
        shown.sort()
        return [(name, path, is_dir) for _, _, name, path, is_dir in shown]

    def walk(self, folder, depth=0):
        """Yields (parent folder, name, path, is_dir, depth) for everything shown."""
        for name, path, is_dir in self.list_folder(folder):
            yield folder, name, path, is_dir, depth
            if is_dir and depth < MAX_DEPTH:
                yield from self.walk(path, depth + 1)

    def open_folders(self):
        return {iid for iid in self.all_items() if self.tree.set(iid, "kind") == "dir" and self.tree.item(iid, "open")}

    def all_items(self, parent=""):
        for iid in self.tree.get_children(parent):
            yield iid
            yield from self.all_items(iid)

    def refresh(self):
        """Read the folder again. Open folders, the selection and the scroll position stay as they are."""
        self.cancel_edit()
        root = self.app.projects.folder
        if not root or not os.path.isdir(root):
            self.show_welcome()
            return
        self.show_tree(root)

    def show_tree(self, root):
        self.tree_frame.tkraise()
        info = self.app.projects.info
        self.title.config(text=(info.name if info else os.path.basename(root) or root).upper())
        expanded = self.open_folders()
        selected = self.tree.selection()
        top = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        total = 0
        for parent, name, path, is_dir, depth in self.walk(root):
            total += 1
            if total > MAX_ITEMS:
                break
            parent_iid = "" if parent == root else parent
            kind = "dir" if is_dir else "project" if name.endswith(EXT) else "file"
            opened = False
            if is_dir:
                if path in self.seen:
                    opened = path in expanded
                else:                                   # a folder seen for the first time starts open
                    opened = True
                    self.seen.add(path)
            tags = ()
            if kind == "file" and self.is_main(path):
                tags = ("main",)
            elif kind == "file" and not name.endswith(".plain"):
                tags = ("other",)
            self.tree.insert(parent_iid, "end", iid=path, text=name, values=(path, kind),
                             image=self.icon_for(path, kind), open=opened, tags=tags)
        for iid in selected:
            if self.tree.exists(iid):
                self.tree.selection_set(iid)
        self.tree.yview_moveto(top)
        self.set_folder_icon()
        self.signature = self.make_signature(root)

    def set_folder_icon(self, opened=None):
        """Open folders show an open folder picture."""
        icons = self.app.icons
        for iid in self.all_items():
            if self.tree.set(iid, "kind") == "dir":
                self.tree.item(iid, image=icons.folder_open if self.tree.item(iid, "open") else icons.folder)

    def show_welcome(self):
        self.title.config(text="")
        for child in self.welcome.winfo_children():
            child.destroy()
        projects = self.app.projects
        ttk.Label(self.welcome, text="No project open", style="SideTitle.TLabel").pack(anchor="w")
        ttk.Label(self.welcome, text="A project is a folder with your programs and a .plainproject file.",
                  style="Side.TLabel", justify="left", wraplength=200).pack(anchor="w", pady=(4, 12))
        for text, command in (("New project...", projects.new_dialog), ("Open project...", projects.open_dialog),
                              ("Open folder...", projects.open_folder_dialog)):
            ttk.Button(self.welcome, text=text, style="Tool.TButton", command=command).pack(fill="x", pady=2)
        recent = projects.recent()
        if recent:
            ttk.Label(self.welcome, text="RECENT", style="SideHead.TLabel").pack(anchor="w", pady=(16, 4))
            for path in recent[:6]:
                name = os.path.splitext(os.path.basename(path))[0]
                link = tk.Label(self.welcome, text=name, anchor="w", cursor="hand2", bd=0, padx=2, pady=2,
                                bg=self.app.theme["side_bg"], fg=self.app.theme["accent"], font=self.app.ui_font)
                link.pack(fill="x")
                link.bind("<Button-1>", lambda e, p=path: projects.open_info_file(p))
        self.welcome.tkraise()

    def make_signature(self, root):
        """A cheap fingerprint of the folder, to notice changes made outside the IDE."""
        parts = []
        for _parent, name, path, is_dir, _depth in islice(self.walk(root), MAX_ITEMS):
            try:
                parts.append((path, is_dir, os.stat(path).st_mtime_ns if not is_dir else 0))
            except OSError:
                parts.append((path, is_dir, 0))
        return tuple(parts)

    def poll(self):
        try:
            root = self.app.projects.folder
            if root and self.edit is None and self.make_signature(root) != self.signature:
                self.refresh()
        finally:
            self.after(2000, self.poll)

    def collapse_all(self):
        for iid in self.all_items():
            if self.tree.set(iid, "kind") == "dir":
                self.tree.item(iid, open=False)
        self.set_folder_icon()

    # ---- selection ---------------------------------------------------------------

    def selected(self):
        """(path, kind) of the selected item, or (None, None)."""
        selection = self.tree.selection()
        if not selection:
            return None, None
        return self.tree.set(selection[0], "path"), self.tree.set(selection[0], "kind")

    def select(self, path):
        if self.tree.exists(path):
            parent = self.tree.parent(path)
            while parent:
                self.tree.item(parent, open=True)
                parent = self.tree.parent(parent)
            self.tree.selection_set(path)
            self.tree.see(path)
            self.set_folder_icon()

    def target_folder(self, path=None, kind=None):
        """Where a new file goes: the selected folder, the folder of the selected file, or the project folder."""
        if path is None:
            path, kind = self.selected()
        if path is None:
            return self.app.projects.folder
        return path if kind == "dir" else os.path.dirname(path)

    def on_click(self, event):
        if self.tree.identify_row(event.y) == "":
            self.tree.selection_remove(self.tree.selection())     # a click on the empty area selects nothing

    def on_double_click(self, event):
        row = self.tree.identify_row(event.y)
        if row and self.tree.set(row, "kind") in ("file", "project"):
            self.tree.selection_set(row)
            self.open_selected()
            return "break"
        return None                                     # a folder opens or closes by itself on a double click

    def open_selected(self):
        path, kind = self.selected()
        if kind in ("file", "project"):
            self.app.documents.open_path(path)
        elif kind == "dir":
            iid = self.tree.selection()[0]
            self.tree.item(iid, open=not self.tree.item(iid, "open"))
            self.set_folder_icon()

    # ---- the menu on a right click ------------------------------------------------

    def on_right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
        path, kind = self.selected() if row else (None, None)
        menu = self.menu
        menu.delete(0, "end")
        folder = self.target_folder(path, kind)
        if kind in ("file", "project"):
            menu.add_command(label="Open", command=self.open_selected)
            if kind == "project":
                menu.add_command(label="Project settings...", command=self.app.projects.settings)
            elif path.endswith(".plain"):
                menu.add_command(label="Set as main program", command=lambda: self.app.projects.set_main(path),
                                 state="disabled" if self.is_main(path) else "normal")
            menu.add_separator()
        menu.add_command(label="New file...", command=lambda: self.new_entry(folder, is_dir=False))
        menu.add_command(label="New folder...", command=lambda: self.new_entry(folder, is_dir=True))
        if row:
            menu.add_separator()
            can_change = kind in ("file", "dir")
            menu.add_command(label="Rename", accelerator="F2", command=self.rename,
                             state="normal" if can_change else "disabled")
            menu.add_command(label="Delete", accelerator="Del", command=self.delete,
                             state="normal" if can_change else "disabled")
            menu.add_separator()
            menu.add_command(label="Copy path", command=lambda: self.copy_path(path))
            menu.add_command(label="Show in file manager", command=lambda: open_in_file_manager(path))
        menu.add_separator()
        menu.add_command(label="Refresh", command=self.refresh)
        menu.tk_popup(event.x_root, event.y_root)

    def copy_path(self, path):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(path)

    # ---- typing a name in the tree ---------------------------------------------------

    def begin_edit(self, iid, text, commit, cancel=None, after=None, stem_only=True):
        """Put a text entry over a row. Return commits (commit(name) returns a problem or None; after() runs
        when the name was accepted), Escape cancels."""
        self.cancel_edit()
        self.tree.see(iid)
        self.tree.update_idletasks()
        box = self.tree.bbox(iid)
        if not box:
            return
        x, y, width, height = box
        depth = 0
        parent = self.tree.parent(iid)
        while parent:
            depth += 1
            parent = self.tree.parent(parent)
        t = self.app.theme
        left = x + (depth + 1) * INDENT + 14
        entry = tk.Entry(self.tree, font=self.app.ui_font, bd=0, relief="flat", highlightthickness=1,
                         highlightbackground=t["accent"], highlightcolor=t["accent"],
                         bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"])
        entry.insert(0, text)
        entry.place(x=left, y=y, width=max(60, self.tree.winfo_width() - left - 4), height=height)
        entry.focus_set()
        stem = os.path.splitext(text)[0] if stem_only and "." in text else text
        entry.selection_range(0, len(stem))
        self.edit = {"entry": entry, "iid": iid, "cancel": cancel, "commit": commit, "after": after, "done": False}
        entry.bind("<Return>", lambda e: self.commit_edit())
        entry.bind("<Escape>", lambda e: self.cancel_edit())
        entry.bind("<FocusOut>", lambda e: self.root_after(self.cancel_edit))

    def root_after(self, func):
        self.after(80, func)

    def commit_edit(self):
        """Accept the name that is typed in the tree (Return)."""
        edit = self.edit
        if not edit or edit["done"]:
            return
        name = edit["entry"].get()
        edit["done"] = True
        problem = edit["commit"](name)
        if problem:                          # keep the entry open so the name can be fixed
            edit["done"] = False
            messagebox.showerror(TITLE, problem, parent=self.app.root)
            if self.edit is edit:
                edit["entry"].focus_set()
            return
        self.remove_edit()
        if edit["after"]:
            edit["after"]()

    def remove_edit(self):
        if self.edit:
            self.edit["entry"].destroy()
            self.edit = None

    def cancel_edit(self):
        edit = self.edit
        if not edit or edit["done"]:
            return
        self.remove_edit()
        if edit["cancel"]:
            edit["cancel"]()
        self.tree.focus_set()

    # ---- new file, new folder -----------------------------------------------------------

    def new_entry(self, folder=None, is_dir=False):
        root = self.app.projects.folder
        if not root:
            self.app.projects.new_dialog()
            return
        folder = folder or self.target_folder()
        if folder != root and self.tree.exists(folder):
            self.tree.item(folder, open=True)
            self.set_folder_icon()
        parent = "" if folder == root else folder
        temp = "<new>"
        if self.tree.exists(temp):
            self.tree.delete(temp)
        # a new folder goes among the folders, a new file among the files (like in VS Code)
        siblings = self.tree.get_children(parent)
        folders = [s for s in siblings if self.tree.set(s, "kind") == "dir"]
        position = 0 if is_dir else len(folders)
        self.tree.insert(parent, position, iid=temp, text="",
                         image=self.app.icons.folder if is_dir else self.app.icons.plain, values=("", "new"))

        made = []

        def commit(name):
            name = name.strip()
            if not is_dir and name and "." not in name:
                name += ".plain"                    # 'pong' means 'pong.plain'
            problem = check_name(name, folder)
            if problem:
                return problem
            target = os.path.join(folder, name)
            try:
                if is_dir:
                    os.makedirs(target)
                else:
                    with open(target, "w", encoding="utf-8", newline="\n") as f:
                        f.write(NEW_PROGRAM if name.endswith(".plain") else "")
            except OSError as exc:
                return f"I cannot create this: {exc.strerror}"
            made.append(target)
            return None

        self.begin_edit(temp, "", commit, cancel=lambda: self.tree.exists(temp) and self.tree.delete(temp),
                        after=lambda: self.created(made[0], is_dir))

    def created(self, path, is_dir):
        self.refresh()
        self.select(path)
        if not is_dir:
            self.app.documents.open_path(path)

    # ---- rename, delete ---------------------------------------------------------------------

    def rename(self):
        path, kind = self.selected()
        if kind not in ("file", "dir"):
            return
        folder = os.path.dirname(path)
        renamed = []

        def commit(name):
            name = name.strip()
            problem = check_name(name, folder, current=path)
            if problem:
                return problem
            target = os.path.join(folder, name)
            if target == path:
                return None
            try:
                os.rename(path, target)
            except OSError as exc:
                return f"I cannot rename this: {exc.strerror}"
            self.app.documents.path_renamed(path, target)
            self.app.projects.path_renamed(path, target)
            renamed.append(target)
            return None

        self.begin_edit(path, os.path.basename(path), commit,
                        after=lambda: (self.refresh(), self.select(renamed[0])) if renamed else None)

    def delete(self):
        path, kind = self.selected()
        if kind not in ("file", "dir"):
            return
        name = os.path.basename(path)
        if kind == "dir":
            count = sum(len(files) for _d, _s, files in os.walk(path))
            detail = f"the folder '{name}' and the {count} file(s) in it" if count else f"the folder '{name}'"
        else:
            detail = f"'{name}'"
        if not messagebox.askyesno(TITLE, f"Delete {detail}?\n\nThis cannot be undone.", icon="warning",
                                   parent=self.app.root):
            return
        try:
            shutil.rmtree(path) if kind == "dir" else os.remove(path)
        except OSError as exc:
            messagebox.showerror(TITLE, f"I cannot delete this: {exc.strerror}", parent=self.app.root)
            return
        self.app.documents.path_removed(path)
        self.refresh()
