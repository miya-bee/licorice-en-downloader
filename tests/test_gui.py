"""Widget-level regressions without network I/O or OS input automation."""
from pathlib import Path
import os
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from licorice import i18n
from licorice.gui import Application
from licorice.i18n import tr
from test_workflow import sample

if os.name == "nt":
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)


class GuiTests(unittest.TestCase):
    language = "ja"

    def setUp(self):
        environment = patch.dict(os.environ, {"LICORICE_LANG": self.language})
        environment.start()
        self.addCleanup(environment.stop)
        self.addCleanup(setattr, i18n, "_language", None)
        self.folder = tempfile.TemporaryDirectory()
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.folder.cleanup()
            self.skipTest("Tk display unavailable")
        self.root.tk.call("tk", "scaling", 1.6683)  # Windows 125% regression.
        self.app = Application(self.root, Path(self.folder.name), auto_check=False)
        self.root.update()

    def tearDown(self):
        self.app.close()
        self.folder.cleanup()

    def test_all_action_buttons_fit_at_125_percent(self):
        def inspect(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "TButton":
                    bottom = child.winfo_rooty() - self.root.winfo_rooty() + child.winfo_height()
                    self.assertTrue(child.winfo_ismapped(), str(child.cget("text")))
                    self.assertLessEqual(bottom, self.root.winfo_height(), str(child.cget("text")))
                inspect(child)
        # Content controls may be below the viewport on a small CI desktop;
        # the fixed action area must always remain visible.
        inspect(self.app.download_button.master.master)

    def test_no_update_removes_previous_release(self):
        _, release, _, _ = sample()
        self.app.release = release
        self.app.busy = True
        self.app.events.put(("success", ("check", None)))
        self.app.events.put(("idle", None))
        self.root.after_cancel(self.app.poll_timer)
        self.app._poll()
        self.assertIsNone(self.app.release)
        self.assertTrue(self.app.download_button.instate(["disabled"]))
        self.assertIn(tr("\n配布情報：更新なし"), self.app.report)

    def test_error_does_not_expose_output_path(self):
        self.app.events.put(("error", ("network", "通信に失敗しました。")))
        self.root.after_cancel(self.app.poll_timer)
        self.app._poll()
        self.assertNotIn(str(self.folder.name), self.app.report)
        self.assertNotIn(str(self.folder.name), self.app.destination_var.get())

    def test_open_destination_follows_current_selection(self):
        current = Path(self.folder.name) / "new"
        current.mkdir()
        self.app.saved_path = Path(self.folder.name) / "old" / "saved.bin"
        self.app.settings.set_destination(current, self.app.base)
        with patch("licorice.gui.os.startfile", create=True) as opened, patch("licorice.gui.messagebox.showerror"):
            self.app.open_destination()
        opened.assert_called_once_with(current)

    def test_report_copy_matches_the_text_shown_in_dialog(self):
        self.app.report = "shown report"
        self.app.show_report()
        self.app.report = "new background result"
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        button = next(w for w in dialog.winfo_children() if w.winfo_class() == "TButton")
        with patch.object(self.root, "clipboard_clear"), patch.object(self.root, "clipboard_append") as copied:
            button.invoke()
        copied.assert_called_once_with("shown report")
        dialog.destroy()

    def test_closing_app_does_not_start_another_background_task(self):
        self.app.closing = True
        try:
            with patch("licorice.gui.threading.Thread") as worker:
                self.app._start("check", lambda: None)
            worker.assert_not_called()
        finally:
            self.app.closing = False
            self.app.busy = False

    def test_close_cancels_pending_startup_callbacks(self):
        ran = []
        timer = self.root.after(0, lambda: ran.append(True))
        self.app.startup_timers.append(timer)
        try:
            with patch.object(self.root, "destroy"), patch.object(self.app, "_persist", return_value=True):
                self.app._finish_close()
                self.root.update()
            self.assertEqual(ran, [])
        finally:
            self.app.closing = False

    def test_small_screen_content_remains_reachable_by_scrolling(self):
        self.root.geometry("1000x668")
        self.root.minsize(790, 668)
        self.root.update()
        canvas = self.app.content_canvas
        self.assertLess(canvas.yview()[1], 1.0)
        canvas.yview_moveto(1.0)
        self.root.update()
        bottom = self.app.choose_button.winfo_rooty() + self.app.choose_button.winfo_height()
        self.assertLessEqual(bottom, canvas.winfo_rooty() + canvas.winfo_height())

    def test_touchpad_small_wheel_deltas_accumulate(self):
        self.root.geometry("1000x668")
        self.root.minsize(790, 668)
        self.root.update()
        canvas = self.app.content_canvas
        self.assertLess(canvas.yview()[1], 1.0)
        event = type("Event", (), {"widget": canvas, "delta": -30})()
        for _ in range(3):
            self.app._scroll_body(event)
        self.assertEqual(canvas.yview()[0], 0.0)  # 90 of 120: not yet one notch
        self.app._scroll_body(event)
        self.assertGreater(canvas.yview()[0], 0.0)

    def test_high_dpi_and_small_screen_keep_primary_actions_accessible(self):
        self.root.tk.call("tk", "scaling", 2.6666)
        self.root.geometry("1286x668")
        self.root.minsize(790, 668)
        self.root.update()
        for button in (self.app.download_button, self.app.cancel_button, self.app.settings_button):
            self.assertTrue(button.winfo_ismapped())
            self.assertLessEqual(button.winfo_rooty() - self.root.winfo_rooty() + button.winfo_height(), self.root.winfo_height())


class EnglishGuiTests(GuiTests):
    """Same regressions with the (longer) English labels."""
    language = "en"

    def test_english_labels_and_messages(self):
        self.assertEqual(self.app.download_button.cget("text"), "Download BIN")
        self.assertEqual(self.app.font, "Segoe UI")
        self.app.events.put(("progress", (1048576, 2097152)))
        self.root.after_cancel(self.app.poll_timer)
        self.app._poll()
        self.assertEqual(self.app.status_var.get(), "Downloading: 1.00 / 2.00 MiB")

    def test_language_choice_is_saved(self):
        self.app.show_settings()
        dialog = next(w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel))
        self.app.language_box.set("日本語")
        frame = dialog.winfo_children()[0]
        button = next(w for w in frame.winfo_children() if w.winfo_class() == "TButton")
        with patch("licorice.gui.messagebox.showinfo") as notice:
            button.invoke()
        notice.assert_called_once()
        self.assertEqual(self.app.settings.language, "ja")
        self.assertIn('"language": "ja"', (Path(self.folder.name) / "settings.json").read_text(encoding="utf-8"))
