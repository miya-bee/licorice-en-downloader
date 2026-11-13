"""Japanese desktop UI. Only the main thread touches Tk widgets."""
from __future__ import annotations

from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser

from . import APP_NAME, __version__
from .core import AppError, Cancelled
from .network import Client
from .service import SaveOptions, acquire, output_paths
from .storage import Settings, app_directory


class Application:
    def __init__(self, root: tk.Tk, base: Path | None = None, auto_check: bool = True):
        self.root, self.base = root, base or app_directory()
        self.settings, warning = Settings.load(self.base)
        self.release = None
        self.saved_path = None
        self.busy = False
        self.closing = False
        self.report = "まだ処理を実行していません。"
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.startup_timers = []
        self.logger = logging.getLogger(f"licorice.{id(self)}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.addHandler(logging.NullHandler())
        try:
            (self.base / "logs").mkdir(exist_ok=True)
            handler = RotatingFileHandler(self.base / "logs" / "app.log", maxBytes=262144,
                                          backupCount=2, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self.logger.addHandler(handler)
        except OSError:
            warning = (warning + "\n" if warning else "") + "ログを保存できません。アプリフォルダの書き込み権限を確認してください。"
        self._build()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_timer = self.root.after(80, self._poll)
        if warning:
            self.startup_timers.append(self.root.after(200, lambda: messagebox.showwarning("設定・保存の確認", warning, parent=root)))
        if auto_check:
            self.startup_timers.append(self.root.after(350, self.check))

    def _build(self):
        root = self.root
        root.title(f"{APP_NAME}  v{__version__}")
        root.configure(background="#f2f5f1")
        # Tk scales point-sized fonts with Windows DPI, but geometry is pixels.
        # Scale the initial geometry too, so action buttons remain visible.
        scale = max(1.0, float(root.tk.call("tk", "scaling")) / (96 / 72))
        max_width, max_height = root.winfo_screenwidth() - 80, root.winfo_screenheight() - 100
        root.minsize(min(max_width, round(790 * scale)), min(max_height, round(730 * scale)))
        try:
            geometry = self.settings.geometry
            if geometry == "920x830":
                geometry = f"{min(max_width, round(920 * scale))}x{min(max_height, round(830 * scale))}"
            else:
                dimensions = re.match(r"(\d+)x(\d+)(.*)", geometry)
                if dimensions:
                    geometry = f"{min(max_width, int(dimensions[1]))}x{min(max_height, int(dimensions[2]))}{dimensions[3]}"
            root.geometry(geometry)
            root.update_idletasks()
            if (root.winfo_x() < -20 or root.winfo_y() < -20
                    or root.winfo_x() > root.winfo_screenwidth() - 120
                    or root.winfo_y() > root.winfo_screenheight() - 120):
                root.geometry("920x830+60+40")
        except tk.TclError:
            root.geometry("920x830")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", font=("Yu Gothic UI", 10), background="#f2f5f1", foreground="#20372b")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Card.TLabel", background="#ffffff")
        style.configure("Muted.TLabel", foreground="#5a6b61", background="#ffffff")
        style.configure("Heading.TLabel", font=("Yu Gothic UI", 12, "bold"), background="#ffffff")
        style.configure("Version.TLabel", font=("Yu Gothic UI", 24, "bold"), background="#ffffff")
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background="#286148", foreground="#ffffff", padding=(16, 9))
        style.map("Accent.TButton", background=[("disabled", "#b9c5bd"), ("active", "#1b4c36")])
        style.configure("TProgressbar", background="#377e5b", troughcolor="#e6ece6", borderwidth=0)
        header = tk.Frame(root, bg="#193c2c", padx=28, pady=18)
        header.pack(fill="x")
        tk.Label(header, text=APP_NAME, bg="#193c2c", fg="#ffffff",
                 font=("Yu Gothic UI", 21, "bold")).pack(anchor="w")
        self.subtitle = tk.Label(header, text=f"X4 Pro用  ·  Licorice EN版を取得して、検証済みBINとして保存  /  アプリ v{__version__}",
                 bg="#193c2c", fg="#c7ded0", font=("Yu Gothic UI", 10), anchor="w", justify="left")
        self.subtitle.pack(anchor="w", pady=(5, 0))
        # Primary actions stay outside the scrolling content. Small displays
        # and high DPI must never hide Download / Cancel / Settings / Manual.
        actions = ttk.Frame(root, padding=(24, 10, 24, 16))
        actions.pack(side="bottom", fill="x")
        viewport = ttk.Frame(root)
        viewport.pack(fill="both", expand=True)
        self.content_canvas = tk.Canvas(viewport, background="#f2f5f1", highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(viewport, orient="vertical", command=self.content_canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.content_canvas.pack(side="left", fill="both", expand=True)
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        self.content_body = body = ttk.Frame(self.content_canvas, padding=(24, 16))
        self.content_window = self.content_canvas.create_window((0, 0), window=body, anchor="nw")
        body.bind("<Configure>", self._fit_body)
        self.content_canvas.bind("<Configure>", self._fit_body)
        root.bind("<MouseWheel>", self._scroll_body, add="+")

        card = ttk.Frame(body, style="Card.TFrame", padding=18)
        card.pack(fill="x")
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text="公式APIが案内する配布FW", style="Heading.TLabel").pack(side="left")
        self.check_button = ttk.Button(row, text="再確認", command=self.check)
        self.check_button.pack(side="right")
        self.version_var = tk.StringVar(value="配布情報を未確認")
        ttk.Label(card, textvariable=self.version_var, style="Version.TLabel").pack(anchor="w", pady=(3, 0))
        self.release_var = tk.StringVar(value="対象：X4 Pro ／ EN版")
        ttk.Label(card, textvariable=self.release_var, style="Muted.TLabel").pack(anchor="w")
        self.time_var = tk.StringVar(value="確認日時：—")
        ttk.Label(card, textvariable=self.time_var, style="Muted.TLabel").pack(anchor="w", pady=(3, 0))

        changelog_card = ttk.Frame(body, style="Card.TFrame", padding=(18, 12))
        changelog_card.pack(fill="both", expand=True, pady=(12, 0))
        ttk.Label(changelog_card, text="配布元の更新内容（原文）", style="Heading.TLabel").pack(anchor="w")
        self.changelog = scrolledtext.ScrolledText(changelog_card, height=3, wrap="word", relief="flat",
                                                  font=("Yu Gothic UI", 10), background="#ffffff",
                                                  foreground="#34493c", borderwidth=0, padx=2, pady=6)
        self.changelog.pack(fill="both", expand=True)
        self._set_changelog("配布情報の取得後に表示します。")

        saving = ttk.Frame(body, style="Card.TFrame", padding=(18, 12))
        saving.pack(fill="x", pady=(12, 0))
        ttk.Label(saving, text="保存先", style="Heading.TLabel").pack(anchor="w")
        row = ttk.Frame(saving, style="Card.TFrame")
        row.pack(fill="x", pady=(5, 0))
        self.destination_var = tk.StringVar(value=self._destination_display())
        self.destination_entry = ttk.Entry(row, textvariable=self.destination_var, state="readonly")
        self.destination_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.choose_button = ttk.Button(row, text="変更…", command=self.choose_destination)
        self.choose_button.pack(side="right")
        self.filename_var = tk.StringVar(value="保存するファイル：配布情報の取得後に表示")
        ttk.Label(saving, textvariable=self.filename_var, style="Muted.TLabel").pack(anchor="w", pady=(5, 0))

        self.status_var = tk.StringVar(value="配布情報を確認してください。")
        self.status_label = ttk.Label(actions, textvariable=self.status_var, wraplength=820)
        self.status_label.pack(anchor="w", pady=(0, 7))
        self.progress = ttk.Progressbar(actions, mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        controls = ttk.Frame(actions)
        controls.pack(fill="x", pady=(12, 0))
        self.download_button = ttk.Button(controls, text="BINをダウンロード", style="Accent.TButton", command=self.download, state="disabled")
        self.download_button.pack(side="left")
        self.cancel_button = ttk.Button(controls, text="キャンセル", command=self.request_cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(controls, text="保存先を開く", command=self.open_destination, state="disabled")
        self.open_button.pack(side="left")
        self.settings_button = ttk.Button(controls, text="設定", command=self.show_settings)
        self.settings_button.pack(side="right")
        footer = ttk.Frame(actions)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Button(footer, text="マニュアル・導入手順", command=self.open_manual).pack(side="left")
        ttk.Button(footer, text="詳細・報告用情報", command=self.show_report).pack(side="left", padx=8)
        ttk.Button(footer, text="このアプリについて", command=self.about).pack(side="right")
        self.notice_label = ttk.Label(actions, text="非公式ツールです。公式配布物からアプリBINを抽出します。端末への書き込みはRescue OSから行ってください。",
                  wraplength=830, foreground="#617165")
        self.notice_label.pack(anchor="w", pady=(10, 0))

    def _fit_body(self, event=None):
        width = max(1, self.content_canvas.winfo_width())
        height = max(self.content_body.winfo_reqheight(), self.content_canvas.winfo_height())
        self.content_canvas.itemconfigure(self.content_window, width=width, height=height)
        self.content_canvas.configure(scrollregion=(0, 0, width, height))
        wrap = max(160, self.root.winfo_width() - 64)
        self.subtitle.configure(wraplength=wrap)
        self.status_label.configure(wraplength=wrap)
        self.notice_label.configure(wraplength=wrap)

    def _scroll_body(self, event):
        if event.widget is self.changelog:
            return
        if self.content_canvas.yview() != (0.0, 1.0):
            self.content_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _set_changelog(self, text):
        self.changelog.configure(state="normal")
        self.changelog.delete("1.0", "end")
        self.changelog.insert("1.0", text)
        self.changelog.configure(state="disabled")

    def _persist(self):
        try:
            self.settings.geometry = self.root.geometry()
            self.settings.save(self.base)
            return True
        except AppError:
            messagebox.showwarning("設定を保存できません", "設定を保存できませんでした。この操作で選んだ内容は今回の起動中は有効です。\nアプリフォルダの書き込み権限を確認してください。", parent=self.root)
            return False

    def _start(self, operation, task):
        if self.busy or self.closing:
            return
        self.busy = True
        self.cancel.clear()
        self.progress.configure(value=0)
        for button in (self.check_button, self.download_button, self.choose_button, self.settings_button):
            button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        def run():
            try:
                result = task()
                self.events.put(("success", (operation, result)))
            except AppError as exc:
                self.events.put(("error", (exc.code, str(exc))))
            except Exception as exc:
                # Report only the exception type; raw messages may contain paths/URLs.
                self.events.put(("error", ("unexpected", f"予期しないエラーが発生しました（{type(exc).__name__}）。報告用情報を確認してください。")))
            finally:
                self.events.put(("idle", None))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def check(self):
        if self.busy or self.closing:
            return
        if self.release:
            self.time_var.set("前回確認時の情報です。再確認中…")
        self.status_var.set("公式APIで配布情報を確認しています…")
        self._start("check", lambda: Client().check(self.cancel))

    def choose_destination(self):
        if self.busy:
            return
        selected = filedialog.askdirectory(parent=self.root, title="FWの保存先を選択", mustexist=True)
        if selected:
            try:
                self.settings.set_destination(Path(selected), self.base)
            except OSError:
                messagebox.showerror("保存先を選べません", "フォルダが存在し、利用できるか確認してください。", parent=self.root)
                return
            self.destination_var.set(self._destination_display())
            self._persist()

    def _destination_display(self):
        path = Path(self.settings.destination)
        return str(path) if path.is_absolute() else f"アプリのフォルダ / {path.as_posix()}"

    def download(self):
        if self.busy or self.closing or not self.release:
            return
        directory = self.settings.destination_path(self.base)
        options = SaveOptions(self.settings.save_xota, self.settings.save_metadata)
        try:
            conflicts = [p.name for p in output_paths(self.release, directory, options) if p.exists()]
        except OSError:
            messagebox.showerror("保存先を確認できません", "保存先の権限と接続状態を確認してください。", parent=self.root)
            return
        if conflicts:
            if not messagebox.askyesno("同名ファイルの確認", "以下のファイルを、検証成功後に上書きしますか？\n\n" + "\n".join(conflicts), parent=self.root):
                return
            options = SaveOptions(options.xota, options.metadata, True, frozenset(conflicts))
        release = self.release
        self._start("download", lambda: acquire(release, directory, options, self.cancel,
                    lambda kind, value: self.events.put((kind, value))))

    def request_cancel(self):
        self.cancel.set()
        self.cancel_button.configure(state="disabled")
        self.status_var.set("中止を要求しました。通信や保存の終了を待っています…")

    def _poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    current, total = value
                    self.progress.configure(value=100 * current / total if total else 0)
                    self.status_var.set(f"ダウンロード中：{current / 1048576:.2f} / {total / 1048576:.2f} MiB")
                elif kind == "stage":
                    self.status_var.set(value)
                    self.logger.info("stage %s", value)
                elif kind == "error":
                    code, message = value
                    self.status_var.set(message)
                    self.progress.configure(value=0)
                    if self.release:
                        self.time_var.set(f"前回確認時の情報：{self._local_time(self.release.checked)}")
                    self.report = self._report_header() + f"\nエラー分類：{code}\n内容：{message}"
                    self.logger.info("error %s", code)
                elif kind == "success":
                    operation, result = value
                    if operation == "check":
                        self.release = result
                        if result:
                            self.version_var.set(result.version)
                            self.release_var.set(f"X4 Pro ／ EN版　転送サイズ：{result.size:,} バイト")
                            self.time_var.set(f"確認：{self._local_time(result.checked)}　配布日時（配布元表記）：{result.uploaded or '不明'}")
                            self.filename_var.set(f"保存するファイル：{result.stem}.bin")
                            self._set_changelog(result.changelog or "更新内容の記載はありません。")
                            self.status_var.set("配布情報を確認しました。保存先を確認し、ダウンロードしてください。")
                            self.report = self._report_header() + "\n配布情報の取得：成功"
                        else:
                            self.version_var.set("現在の配布物はありません")
                            self.release_var.set("対象：X4 Pro ／ EN版")
                            self.time_var.set("今回の照会では更新なしの応答でした。")
                            self.filename_var.set("保存するファイル：—")
                            self._set_changelog("現在取得できる配布物がありません。時間をおいて再確認してください。")
                            self.status_var.set("公式APIから「更新なし」の応答がありました。")
                            self.report = self._report_header() + "\n配布情報：更新なし"
                    else:
                        self.saved_path = result.path
                        self.progress.configure(value=100)
                        self.open_button.configure(state="normal")
                        self.status_var.set("ダウンロード・検証完了。BINを保存しました。" + ("　追加保存に問題があります。詳細をご確認ください。" if result.warnings else ""))
                        self.report = self._report_header() + "\nBIN保存：成功\nサイズ・SHA-256・ESPイメージ検証：成功\nSHA-256：" + result.verification["plain_sha256"]
                        if result.warnings:
                            self.report += "\n" + "\n".join(result.warnings)
                            if not self.closing:
                                messagebox.showwarning("追加保存について", "\n".join(result.warnings), parent=self.root)
                        self.logger.info("BIN verified and saved")
                elif kind == "idle":
                    self.busy = False
                    self.cancel_button.configure(state="disabled")
                    for button in (self.check_button, self.choose_button, self.settings_button):
                        button.configure(state="normal")
                    self.download_button.configure(state="normal" if self.release else "disabled")
        except queue.Empty:
            pass
        if self.closing and not self.busy:
            self._finish_close()
            return
        self.poll_timer = self.root.after(80, self._poll)

    @staticmethod
    def _local_time(value):
        return datetime.fromisoformat(value).astimezone().strftime("%Y/%m/%d %H:%M:%S %Z")

    def _report_header(self):
        return f"{APP_NAME} v{__version__}\nOS：{platform.system()} {platform.release()} {platform.machine()}\n対象：X4 Pro / EN\nFW版：{self.release.version if self.release else '未取得'}"

    def show_settings(self):
        if self.busy:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("保存設定")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="BINに加えて保存するファイル", font=("Yu Gothic UI", 12, "bold")).pack(anchor="w")
        xota = tk.BooleanVar(value=self.settings.save_xota)
        metadata = tk.BooleanVar(value=self.settings.save_metadata)
        ttk.Checkbutton(frame, text="配布元のXOTAも保存する", variable=xota).pack(anchor="w", pady=(14, 6))
        ttk.Checkbutton(frame, text="取得情報JSONも保存する", variable=metadata).pack(anchor="w")
        ttk.Label(frame, text="設定はEXEと同じフォルダの settings.json に保存します。\n取得情報には機種・版・取得元・検証結果を記録します。", padding=(0, 16)).pack(anchor="w")
        def save():
            self.settings.save_xota, self.settings.save_metadata = xota.get(), metadata.get()
            self._persist()
            dialog.destroy()
        ttk.Button(frame, text="設定を保存", command=save).pack(anchor="e")
        dialog.grab_set()

    def show_report(self):
        report = self.report
        dialog = tk.Toplevel(self.root)
        dialog.title("詳細・報告用情報")
        dialog.transient(self.root)
        text = scrolledtext.ScrolledText(dialog, width=82, height=17, wrap="word", font=("Yu Gothic UI", 10))
        text.pack(fill="both", expand=True, padx=16, pady=16)
        text.insert("1.0", report)
        text.configure(state="disabled")
        def copy():
            self.root.clipboard_clear()
            self.root.clipboard_append(report)
        ttk.Button(dialog, text="報告用情報をコピー", command=copy).pack(pady=(0, 16))

    def open_destination(self):
        path = self.settings.destination_path(self.base)
        try:
            if not path.is_dir():
                raise OSError()
            if os.name == "nt":
                os.startfile(path)
            else:
                webbrowser.open(path.as_uri())
        except OSError:
            messagebox.showerror("保存先を開けません", "保存先フォルダが存在するか確認してください。", parent=self.root)

    def open_manual(self):
        # A bundled manual works before the GitHub Pages site is published.
        manual = self.base / "docs" / "index.html"
        if manual.is_file():
            webbrowser.open(manual.as_uri())
        else:
            messagebox.showinfo("マニュアル", "配布ZIPの docs/index.html を確認してください。", parent=self.root)

    def about(self):
        messagebox.showinfo("このアプリについて", f"{APP_NAME}\nアプリ v{__version__}\n\nX4 Pro用Licorice EN版ファームウェア取得ツール\nXTEINK非公式・開発版\n\nFWは公式Global配布先から取得します。\n本アプリは端末への書き込みや地域設定の変更を行いません。\n\n第三者表記：THIRD_PARTY_NOTICES.md", parent=self.root)

    def close(self):
        if self.closing:
            return
        if self.busy:
            if not messagebox.askyesno("処理中です", "処理の中止を要求して、終了を待ってから閉じますか？", parent=self.root):
                return
            self.closing = True
            self.request_cancel()
        else:
            self._finish_close()

    def _finish_close(self):
        self.closing = True
        self.root.after_cancel(self.poll_timer)
        for timer in self.startup_timers:
            self.root.after_cancel(timer)
        self._persist()
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        self.root.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    Application(root)
    root.mainloop()
