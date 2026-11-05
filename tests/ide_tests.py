"""Tests for the IDE (ide/plainide). They open real windows, so they need tkinter and a display:

    python3 tests/ide_tests.py                 (Windows, macOS, or Linux with a desktop)
    xvfb-run -a python3 tests/ide_tests.py     (Linux without a display, e.g. in CI)

Without tkinter or a display the tests are skipped.
"""

import os
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "ide"))

# The IDE keeps settings, recent projects and crash reports in a data folder: use a throw-away one.
DATA = tempfile.mkdtemp(prefix="plain_ide_test_")
os.environ["LOCALAPPDATA"] = DATA

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    probe = tk.Tk()
    probe.destroy()
    SKIP = None
except Exception as exc:        # no tkinter, or no display
    tk = messagebox = None
    SKIP = f"the IDE tests need tkinter and a display ({exc})"

if SKIP is None:
    from plainide import projects as PROJECTS
    from plainide import quickopen, settings
    from plainide.app import App
    from plainide.explorer import check_name
    from plainide.language import NEW_PROGRAM

PROJECT_FILE = "note: A Plain project.\nname Space Game\nmain main.plain\noutput Space_Game\n"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


@unittest.skipIf(SKIP, SKIP)
class IdeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="plain_ide_project_")
        self.folder = os.path.join(self.tmp, "Space Game")
        write(os.path.join(self.folder, "Space_Game.plainproject"), PROJECT_FILE)
        write(os.path.join(self.folder, "main.plain"), 'say "main"\n')
        write(os.path.join(self.folder, "ball.plain"), 'say "ball"\n')
        write(os.path.join(self.folder, "lessons", "hello.plain"), 'say "Hello"\n')
        write(os.path.join(self.folder, "notes.txt"), "remember the milk\n")
        self.patches = [mock.patch.object(messagebox, name, return_value=True)
                        for name in ("askyesno", "askyesnocancel", "showerror", "showinfo")]
        self.dialogs = {p.attribute: p.start() for p in self.patches}
        for name in ("askdirectory", "askopenfilename", "askopenfilenames", "asksaveasfilename"):
            patch = mock.patch.object(filedialog, name, return_value="")      # no real dialog may open
            patch.start()
            self.patches.append(patch)
        self.root = tk.Tk()
        self.root.geometry("1100x700")
        self.app = App(self.root, [])
        self.pump()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        try:
            self.app.shutdown()
        except tk.TclError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- helpers -----------------------------------------------------------------

    def pump(self, rounds=8):
        for _ in range(rounds):
            self.root.update()

    def wait_for(self, condition, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            self.root.update()
            if condition():
                return True
            time.sleep(0.02)
        return False

    def open_project(self):
        self.app.projects.open_info_file(os.path.join(self.folder, "Space_Game.plainproject"))
        self.pump()

    def path(self, *parts):
        return os.path.join(self.folder, *parts)

    def items(self):
        return list(self.app.explorer.all_items())

    def type_name(self, name):
        entry = self.app.explorer.edit["entry"]
        entry.delete(0, "end")
        entry.insert(0, name)
        self.app.explorer.commit_edit()
        self.pump(20)

    # ---- the window --------------------------------------------------------------

    def test_starts_with_one_tab_and_a_welcome_explorer(self):
        self.assertEqual(len(self.app.documents.tabs()), 1)
        self.assertTrue(self.app.sidebar_visible())
        self.assertEqual(self.app.view, "explorer")
        self.assertEqual(self.items(), [])

    def test_sidebar_views_and_hiding(self):
        self.app.pick_view("values")
        self.assertEqual((self.app.view, self.app.watch_var.get()), ("values", True))
        self.app.pick_view("values")                      # a second click hides the sidebar
        self.assertFalse(self.app.sidebar_visible())
        self.assertFalse(self.app.watch_var.get())
        self.app.toggle_sidebar()
        self.assertEqual(self.app.view, "explorer")

    def test_theme_switch_and_remembering_it(self):
        for name in ("Light", "Dark", "Light"):
            self.app.apply_theme(name)
            self.pump()
        self.assertEqual(settings.load()["theme"], "Light")
        self.app.apply_theme("Dark")

    # ---- tabs --------------------------------------------------------------------

    def test_tabs_dirty_marker_and_closing(self):
        docs = self.app.documents
        first = docs.current()
        second = docs.new()
        second.text.insert("end", "say 1\n")
        self.pump()
        self.assertTrue(second.dirty)
        self.assertEqual(docs.strip.items[second]["close"].cget("text"), "●")
        self.assertEqual(docs.strip.items[first]["close"].cget("text"), "×")
        self.dialogs["askyesnocancel"].return_value = False        # "do not save"
        self.assertTrue(docs.close(second))
        self.assertEqual(docs.tabs(), [first])

    def test_closing_the_last_tab_leaves_an_empty_one(self):
        docs = self.app.documents
        docs.close(docs.current())
        self.assertEqual(len(docs.tabs()), 1)
        self.assertIsNone(docs.current().path)

    def test_type_names_and_helpers_have_their_own_colors(self):
        doc = self.app.documents.current()
        doc.set_text('define P as\n    n as number\nend\nsay number of "4"\nfor i from 10 to 1 step -1 do\nend\n')
        self.pump()
        helpers = [str(r) for r in doc.text.tag_ranges("helper")]
        self.assertNotIn("2.9", helpers)                       # 'number' in 'n as number' is only a type
        self.assertIn("4.4", helpers)                          # 'number' in 'number of' is a helper
        self.assertIn("5.23", helpers)                         # 'step' in a counting loop

    def test_a_text_file_opens_as_text(self):
        self.open_project()
        doc = self.app.documents.open_path(self.path("notes.txt"))
        self.assertEqual(doc.kind, "text")
        self.pump()
        self.assertEqual(doc.text.tag_ranges("keyword"), ())
        self.app.running.run()
        self.assertIn("not a Plain program", self.app.output.get())

    # ---- the project and the Explorer -----------------------------------------------

    def test_open_project_shows_the_files(self):
        self.open_project()
        names = {self.app.explorer.tree.item(i, "text") for i in self.items()}
        self.assertTrue({"lessons", "hello.plain", "main.plain", "ball.plain", "notes.txt",
                         "Space_Game.plainproject"} <= names)
        tree = self.app.explorer.tree
        self.assertIn("main", tree.item(self.path("main.plain"), "tags"))
        self.assertEqual(tree.set(self.path("Space_Game.plainproject"), "kind"), "project")
        self.assertIn("SPACE GAME", self.app.explorer.title.cget("text"))
        self.assertIn("Space Game", self.root.title())

    def test_new_file_is_typed_in_the_tree(self):
        self.open_project()
        self.app.explorer.new_entry(is_dir=False)
        self.assertIsNotNone(self.app.explorer.edit)
        self.type_name("pong")                             # 'pong' means 'pong.plain'
        self.assertEqual(read(self.path("pong.plain")), NEW_PROGRAM)
        self.assertEqual(self.app.documents.current().path, self.path("pong.plain"))
        self.assertTrue(self.app.explorer.tree.exists(self.path("pong.plain")))

    def test_new_folder_and_a_file_inside(self):
        self.open_project()
        self.app.explorer.new_entry(is_dir=True)
        self.type_name("projects")
        self.assertTrue(os.path.isdir(self.path("projects")))
        self.app.explorer.new_entry(self.path("projects"), is_dir=False)
        self.type_name("a.plain")
        self.assertTrue(os.path.isfile(self.path("projects", "a.plain")))

    def test_bad_names_are_refused_and_the_entry_stays_open(self):
        self.open_project()
        self.app.explorer.new_entry(is_dir=False)
        for bad in ("a/b.plain", "main.plain", ""):
            self.type_name(bad)
            self.assertIsNotNone(self.app.explorer.edit, bad)
        self.assertGreaterEqual(self.dialogs["showerror"].call_count, 3)
        self.app.explorer.cancel_edit()
        self.assertIsNone(self.app.explorer.edit)
        self.assertFalse(self.app.explorer.tree.exists("<new>"))

    def test_check_name(self):
        self.assertIsNone(check_name("fine.plain", self.folder))
        self.assertIn("already exists", check_name("main.plain", self.folder))
        self.assertIn("cannot contain", check_name("a:b", self.folder))
        self.assertIsNotNone(check_name(" x", self.folder))
        self.assertIsNone(check_name("main.plain", self.folder, current=self.path("main.plain")))

    def test_rename_moves_the_file_the_tab_and_the_main_program(self):
        self.open_project()
        self.app.documents.open_path(self.path("main.plain"))
        self.app.explorer.select(self.path("main.plain"))
        self.app.explorer.rename()
        self.type_name("start.plain")
        self.assertFalse(os.path.exists(self.path("main.plain")))
        self.assertTrue(os.path.exists(self.path("start.plain")))
        self.assertEqual(self.app.documents.find(self.path("start.plain")).name, "start.plain")
        self.assertEqual(self.app.projects.info.main, "start.plain")
        self.assertIn("main start.plain", read(self.path("Space_Game.plainproject")))

    def test_rename_a_folder_moves_the_tabs_inside(self):
        self.open_project()
        self.app.documents.open_path(self.path("lessons", "hello.plain"))
        self.app.explorer.select(self.path("lessons"))
        self.app.explorer.rename()
        self.type_name("course")
        self.assertEqual(self.app.documents.current().path, self.path("course", "hello.plain"))

    def test_delete_keeps_the_text_of_an_open_tab(self):
        self.open_project()
        doc = self.app.documents.open_path(self.path("ball.plain"))
        self.app.explorer.select(self.path("ball.plain"))
        self.app.explorer.delete()
        self.assertFalse(os.path.exists(self.path("ball.plain")))
        self.assertIsNone(doc.path)
        self.assertTrue(doc.dirty)
        self.assertEqual(doc.source(), 'say "ball"\n')
        self.assertFalse(self.app.explorer.tree.exists(self.path("ball.plain")))

    def test_set_main_program(self):
        self.open_project()
        self.app.projects.set_main(self.path("ball.plain"))
        self.pump()
        self.assertEqual(self.app.projects.info.main, "ball.plain")
        self.assertIn("main ball.plain", read(self.path("Space_Game.plainproject")))
        tags = self.app.explorer.tree.item(self.path("ball.plain"), "tags")
        self.assertIn("main", tags)

    def test_context_menu(self):
        self.open_project()
        explorer = self.app.explorer
        explorer.menu.tk_popup = lambda *a: None

        def labels_for(path):
            self.pump()
            _x, y, _w, h = explorer.tree.bbox(path)
            explorer.on_right_click(types.SimpleNamespace(x=60, y=y + h // 2, x_root=0, y_root=0))
            menu = explorer.menu
            return [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                    if menu.type(i) == "command"]

        program = labels_for(self.path("ball.plain"))
        self.assertIn("Set as main program", program)
        self.assertIn("Rename", program)
        folder = labels_for(self.path("lessons"))
        self.assertIn("New file...", folder)
        self.assertNotIn("Set as main program", folder)
        project = labels_for(self.path("Space_Game.plainproject"))
        self.assertIn("Project settings...", project)

    def test_explorer_notices_changes_made_outside(self):
        self.open_project()
        write(self.path("outside.plain"), "say 1\n")
        self.app.explorer.poll()
        self.pump()
        self.assertTrue(self.app.explorer.tree.exists(self.path("outside.plain")))

    def test_open_folders_stay_open_after_a_refresh(self):
        self.open_project()
        tree = self.app.explorer.tree
        tree.item(self.path("lessons"), open=False)
        self.app.explorer.refresh()
        self.assertFalse(tree.item(self.path("lessons"), "open"))

    # ---- the project file as text ----------------------------------------------------

    def test_editing_the_project_file_changes_the_project(self):
        self.open_project()
        doc = self.app.documents.open_path(self.path("Space_Game.plainproject"))
        self.assertEqual(doc.kind, "project")
        doc.text.delete("1.0", "end")
        doc.text.insert("1.0", "name Star Game\nmain ball.plain\noutput Star_Game\n")
        self.app.documents.save(doc)
        self.pump()
        info = self.app.projects.info
        self.assertEqual((info.name, info.main, info.output), ("Star Game", "ball.plain", "Star_Game"))
        self.assertTrue(os.path.exists(self.path("Space_Game.plainproject")))     # it keeps its file name
        self.assertIn("STAR GAME", self.app.explorer.title.cget("text"))

    def test_a_mistake_in_the_project_file_is_explained(self):
        self.open_project()
        doc = self.app.documents.open_path(self.path("Space_Game.plainproject"))
        doc.text.insert("end", "colour red\n")
        self.app.documents.save(doc)
        self.pump()
        self.assertIn("I do not understand the line 'colour red'", self.app.output.get())
        self.assertEqual(self.app.projects.info.name, "Space Game")         # the old settings stay

    def test_project_settings_rename_keeps_working(self):
        self.open_project()
        info = self.app.projects.info
        old = info.path
        info.name = "Moon Game"
        info.file = None
        info.save()
        os.remove(old)
        self.app.projects.after_settings(old)
        self.assertTrue(os.path.exists(self.path("Moon_Game.plainproject")))

    # ---- Go to file ----------------------------------------------------------------------

    def test_quick_open_matching(self):
        self.assertTrue(quickopen.matches("bg", "ball_game.plain"))
        self.assertFalse(quickopen.matches("gb", "ball_game.plain".replace("g", "x", 1).replace("b", "y")))
        self.assertLess(quickopen.rank("ba", "ball.plain"), quickopen.rank("ba", "lessons/alabama.plain"))

    def test_quick_open_opens_a_file(self):
        self.open_project()
        self.app.quick_open()
        self.app.quick.var.set("hel")
        self.pump()
        self.assertEqual(self.app.quick.win.winfo_width(), quickopen.WIDTH)      # it is as wide as it should be
        self.assertEqual([r for r, _p in self.app.quick.shown], ["lessons/hello.plain"])
        self.app.quick.accept()
        self.assertEqual(self.app.documents.current().path, self.path("lessons", "hello.plain"))
        self.assertIsNone(self.app.quick)

    # ---- running and building --------------------------------------------------------------

    def test_run_shows_the_output(self):
        doc = self.app.documents.current()
        doc.set_text('say "Hello from the test"\nsay 6 * 7\n')
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: "42" in self.app.output.get()))
        self.assertIn("Hello from the test", self.app.output.get())
        self.assertTrue(self.wait_for(lambda: not self.app.runner.running))

    def test_run_with_input(self):
        doc = self.app.documents.current()
        doc.set_text('let name be input "Name?"\nsay "Hi " + name\n')
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: "Name?" in self.app.output.get()))
        self.app.output.entry.insert(0, "Ada")
        self.app.output._submit(None)
        self.assertTrue(self.wait_for(lambda: "Hi Ada" in self.app.output.get()))

    def test_a_mistake_is_shown_and_the_line_is_marked(self):
        doc = self.app.documents.current()
        doc.set_text('say "ok"\nsay oops\n')
        self.app.running.run()
        self.assertIn("Error in", self.app.output.get())
        self.assertTrue(doc.text.tag_ranges("error_line"))

    def test_live_values_appear_behind_the_code(self):
        doc = self.app.documents.current()
        doc.set_text("let x be 5\nset x to x + 1\n")
        self.app.live_var.set(True)
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: bool(doc.inline)))

    def test_run_a_program_that_imports_another_file(self):
        write(self.path("tools.plain"), 'action twice takes(n) do\n    return n * 2\nend\n')
        write(self.path("use.plain"), 'import tools\nsay twice(21)\n')
        self.open_project()
        doc = self.app.documents.open_path(self.path("use.plain"))
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: "42" in self.app.output.get()))

    def test_a_mistake_in_an_imported_file_opens_that_file(self):
        write(self.path("tools.plain"), 'action twice takes(n) do\n    return n + "a" - 1\nend\n')
        write(self.path("use.plain"), 'import tools\nsay twice(21)\n')
        self.open_project()
        self.app.documents.open_path(self.path("use.plain"))
        self.app.running.run()
        self.assertIn("Error in tools.plain, line 2", self.app.output.get())
        shown = self.app.documents.current()
        self.assertEqual(shown.path, self.path("tools.plain"))
        self.assertTrue(shown.text.tag_ranges("error_line"))

    def test_an_unsaved_program_imports_from_the_project_folder(self):
        write(self.path("tools.plain"), 'action twice takes(n) do\n    return n * 2\nend\n')
        self.open_project()
        doc = self.app.documents.new()
        doc.set_text('import tools\nsay twice(5)\n')
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: "10" in self.app.output.get()))

    def test_build_makes_the_python_file(self):
        self.open_project()
        imports = self.app.building.build()
        self.assertEqual(imports, [])
        self.assertTrue(os.path.isfile(self.path("build", "Space_Game.py")))
        self.assertIn("Built build", self.app.output.get())
        self.pump()
        self.assertFalse(self.app.explorer.tree.exists(self.path("build")))      # build output is not listed

    def test_values_panel_lists_variables(self):
        doc = self.app.documents.current()
        doc.set_text("let apples be 3\nset apples to apples + 1\n")
        self.app.toggle_values() if self.app.watch_var.get() else (self.app.watch_var.set(True), self.app.toggle_values())
        self.app.running.run()
        self.assertTrue(self.wait_for(lambda: "apples" in {
            self.app.values.tree.item(i, "text") for i in self.app.values.tree.get_children()}))


@unittest.skipIf(SKIP, SKIP)
class ProjectFileTest(unittest.TestCase):
    def test_from_text_keeps_the_file_name(self):
        info = PROJECTS.Project.from_text("name A b\nmain x.plain\n", os.path.join(DATA, "Other.plainproject"))
        self.assertEqual((info.name, info.main, info.output), ("A b", "x.plain", "A_b"))
        self.assertTrue(info.path.endswith("Other.plainproject"))
        with self.assertRaises(ValueError):
            PROJECTS.Project.from_text("bogus 1", "x.plainproject")


if __name__ == "__main__":
    unittest.main(verbosity=1)
