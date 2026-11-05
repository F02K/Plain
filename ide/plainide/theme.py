"""Colors, fonts and the look of the widgets. The colors follow Visual Studio Code ("Dark+" and "Light+")."""

import sys
from tkinter import font as tkfont
from tkinter import ttk

# Colors follow Visual Studio Code: "Dark+" and "Light+".
DARK = {
    "bg": "#1e1e1e", "fg": "#d4d4d4", "gutter_bg": "#1e1e1e", "gutter_fg": "#858585",
    "keyword": "#569cd6", "helper": "#c586c0", "string": "#ce9178", "number": "#b5cea8",
    "comment": "#6a9955", "error_line": "#5a1d1d", "current_line": "#282828", "select_bg": "#264f78",
    "out_err": "#f48771", "out_in": "#4fc1ff", "out_info": "#9d9d9d",
    "pop_bg": "#252526", "pop_sel": "#04395e",
    "symbol": "#3a3d41", "symbol_def": "#575c66", "watch_changed": "#4d4a1f",
    "inline_fg": "#7aa2d6", "inline_bg": "#232b3a",
    "ui_bg": "#252526", "toolbar_bg": "#333333", "side_bg": "#252526", "panel_bg": "#1e1e1e",
    "tab_bg": "#2d2d2d", "border": "#3c3c3c", "input_bg": "#3c3c3c",
    "button_bg": "#3c3c3c", "button_hover": "#505050", "accent": "#007acc",
    "run_bg": "#2e7d32", "run_hover": "#388e3c", "scroll": "#424242", "scroll_hover": "#686868",
    "status_bg": "#007acc", "status_fg": "#ffffff", "busy_bg": "#cc6633",
    "activity_bg": "#333333", "activity_fg": "#858585", "activity_active": "#ffffff",
    "tabstrip_bg": "#252526", "tab_hover_bg": "#2a2d2e",
    "find_match": "#5a4520", "find_current": "#9a5a00",
}

LIGHT = {
    "bg": "#ffffff", "fg": "#1f1f1f", "gutter_bg": "#ffffff", "gutter_fg": "#237893",
    "keyword": "#0000ff", "helper": "#af00db", "string": "#a31515", "number": "#098658",
    "comment": "#008000", "error_line": "#ffd9d9", "current_line": "#f3f3f3", "select_bg": "#add6ff",
    "out_err": "#c62828", "out_in": "#0451a5", "out_info": "#6b6b6b",
    "pop_bg": "#f3f3f3", "pop_sel": "#cce4f7",
    "symbol": "#e8e8e8", "symbol_def": "#cfd6e4", "watch_changed": "#fff1b8",
    "inline_fg": "#4a5d86", "inline_bg": "#eef2fb",
    "ui_bg": "#f3f3f3", "toolbar_bg": "#e6e6e6", "side_bg": "#f3f3f3", "panel_bg": "#ffffff",
    "tab_bg": "#ececec", "border": "#d4d4d4", "input_bg": "#ffffff",
    "button_bg": "#dcdcdc", "button_hover": "#c8c8c8", "accent": "#007acc",
    "run_bg": "#2e7d32", "run_hover": "#388e3c", "scroll": "#c1c1c1", "scroll_hover": "#a0a0a0",
    "status_bg": "#007acc", "status_fg": "#ffffff", "busy_bg": "#cc6633",
    "activity_bg": "#2c2c2c", "activity_fg": "#858585", "activity_active": "#ffffff",
    "tabstrip_bg": "#f3f3f3", "tab_hover_bg": "#e4e4e4",
    "find_match": "#ffe7a3", "find_current": "#f5b942",
}

THEMES = {"Dark": DARK, "Light": LIGHT}


def make_fonts(root):
    """Returns (editor font, small font for live values, bold editor-size UI font, UI font tuple)."""
    base = tkfont.nametofont("TkFixedFont", root=root).copy()
    family = "Consolas" if sys.platform.startswith("win") else base.actual("family")
    editor = tkfont.Font(root=root, family=family, size=13)
    small = tkfont.Font(root=root, family=family, size=10)
    ui_family = "Segoe UI" if sys.platform.startswith("win") else tkfont.nametofont("TkDefaultFont", root=root).actual("family")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name, root=root).configure(family=ui_family, size=10)
    ui_bold = tkfont.Font(root=root, family=ui_family, size=10, weight="bold")
    return editor, small, ui_bold, (ui_family, 10)


def style_menu(menu, t):
    """Give a pop-up menu the colors of the theme."""
    menu.config(bg=t["pop_bg"], fg=t["fg"], activebackground=t["pop_sel"], activeforeground=t["fg"],
                bd=0, relief="flat", disabledforeground=t["out_info"])


def apply_styles(root, t, ui_font):
    """Give every ttk widget the look of the theme (flat, like Visual Studio Code)."""
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=t["ui_bg"])
    s.configure(".", background=t["ui_bg"], foreground=t["fg"], fieldbackground=t["input_bg"],
                bordercolor=t["border"], darkcolor=t["ui_bg"], lightcolor=t["ui_bg"], troughcolor=t["bg"],
                focuscolor=t["ui_bg"], selectbackground=t["select_bg"], selectforeground=t["fg"],
                insertcolor=t["fg"], font=ui_font)

    s.configure("TFrame", background=t["ui_bg"])
    s.configure("Toolbar.TFrame", background=t["toolbar_bg"])
    s.configure("Side.TFrame", background=t["side_bg"])
    s.configure("Panel.TFrame", background=t["panel_bg"])
    s.configure("PanelHead.TFrame", background=t["panel_bg"])
    s.configure("Activity.TFrame", background=t["activity_bg"])
    s.configure("Status.TFrame", background=t["status_bg"])
    s.configure("StatusBusy.TFrame", background=t["busy_bg"])

    s.configure("TLabel", background=t["ui_bg"], foreground=t["fg"])
    s.configure("Side.TLabel", background=t["side_bg"], foreground=t["fg"])
    s.configure("SideHead.TLabel", background=t["side_bg"], foreground=t["out_info"], font=(ui_font[0], 8, "bold"))
    s.configure("SideTitle.TLabel", background=t["side_bg"], foreground=t["fg"], font=(ui_font[0], 9, "bold"))
    s.configure("Info.TLabel", background=t["tab_bg"], foreground=t["out_info"])
    s.configure("PanelTitle.TLabel", background=t["panel_bg"], foreground=t["fg"], font=(ui_font[0], 8, "bold"))
    s.configure("Panel.TLabel", background=t["panel_bg"], foreground=t["out_info"])
    s.configure("Status.TLabel", background=t["status_bg"], foreground=t["status_fg"], padding=(10, 2))
    s.configure("StatusBusy.TLabel", background=t["busy_bg"], foreground=t["status_fg"], padding=(10, 2))

    flat = dict(relief="flat", borderwidth=0, focusthickness=0)
    s.configure("TButton", background=t["button_bg"], foreground=t["fg"], padding=(12, 5), **flat)
    s.map("TButton", background=[("disabled", t["button_bg"]), ("pressed", t["button_hover"]),
                                 ("active", t["button_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Tool.TButton", background=t["button_bg"], foreground=t["fg"], padding=(11, 4), **flat)
    s.map("Tool.TButton", background=[("disabled", t["toolbar_bg"]), ("pressed", t["button_hover"]),
                                      ("active", t["button_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Run.TButton", background=t["run_bg"], foreground="#ffffff", padding=(14, 4), **flat)
    s.map("Run.TButton", background=[("disabled", t["button_bg"]), ("pressed", t["run_hover"]),
                                     ("active", t["run_hover"])],
          foreground=[("disabled", t["out_info"])])
    s.configure("Toolbar.TCheckbutton", background=t["toolbar_bg"], foreground=t["fg"], padding=(4, 2))
    s.map("Toolbar.TCheckbutton", background=[("active", t["toolbar_bg"])],
          indicatorcolor=[("selected", t["accent"]), ("!selected", t["input_bg"])])
    s.configure("TSeparator", background=t["border"])

    s.configure("Treeview", background=t["side_bg"], fieldbackground=t["side_bg"], foreground=t["fg"],
                borderwidth=0, rowheight=24)
    s.map("Treeview", background=[("selected", t["select_bg"])], foreground=[("selected", t["fg"])])
    s.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    s.configure("Treeview.Heading", background=t["tab_bg"], foreground=t["out_info"], relief="flat",
                borderwidth=0, padding=(6, 4))
    s.map("Treeview.Heading", background=[("active", t["tab_bg"])])

    for orient in ("Vertical", "Horizontal"):
        name = f"{orient}.TScrollbar"
        thumb = f"{orient}.Scrollbar.thumb"
        side = "ns" if orient == "Vertical" else "ew"
        s.layout(name, [(f"{orient}.Scrollbar.trough", {"children": [(thumb, {"expand": "1", "sticky": "nswe"})],
                                                         "sticky": side})])
        s.configure(name, background=t["scroll"], troughcolor=t["bg"], bordercolor=t["bg"], relief="flat",
                    borderwidth=0, width=12)
        s.map(name, background=[("active", t["scroll_hover"]), ("pressed", t["scroll_hover"])])

    s.configure("TEntry", fieldbackground=t["input_bg"], foreground=t["fg"], bordercolor=t["border"],
                insertcolor=t["fg"], padding=4)
    s.map("TEntry", bordercolor=[("focus", t["accent"])])
    s.configure("TCombobox", fieldbackground=t["input_bg"], background=t["button_bg"], foreground=t["fg"],
                arrowcolor=t["fg"], bordercolor=t["border"], padding=4)
    s.map("TCombobox", fieldbackground=[("readonly", t["input_bg"])], foreground=[("readonly", t["fg"])],
          selectbackground=[("readonly", t["input_bg"])], selectforeground=[("readonly", t["fg"])])
    root.option_add("*TCombobox*Listbox.background", t["input_bg"])
    root.option_add("*TCombobox*Listbox.foreground", t["fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", t["select_bg"])
    root.option_add("*TCombobox*Listbox.selectForeground", t["fg"])
    s.configure("TPanedwindow", background=t["border"])
    s.configure("Sash", sashthickness=3, gripcount=0, background=t["border"])
