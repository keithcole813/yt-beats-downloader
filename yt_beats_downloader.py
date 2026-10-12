#!/usr/bin/env python3
"""
YT Beats Downloader
Paste a YouTube URL, get a best-quality MP3 ready for sampling.

Uses your proven yt-dlp settings:
  yt-dlp --cookies-from-browser chrome -f "ba/b" -x --audio-format mp3 --audio-quality 0
(The browser cookies are what gets past YouTube's bot check.)
"""
import os
import platform
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from yt_dlp import YoutubeDL

APP_TITLE = "YT Beats Downloader"
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Music", "yt-beats")


def open_folder(path):
    """Open a folder in the system file manager."""
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("560x470")
        self.resizable(True, True)
        self.msg_queue = queue.Queue()
        self.downloading = False

        self._build_ui()
        self.after(100, self._drain_queue)

    # ---------- UI ----------
    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        ttk.Label(self, text="YouTube URL", font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(self, textvariable=self.url_var, font=("Segoe UI", 10))
        url_entry.pack(fill="x", **pad)
        url_entry.focus()

        ttk.Label(self, text="Save to folder", font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)
        folder_row = ttk.Frame(self)
        folder_row.pack(fill="x", **pad)
        self.folder_var = tk.StringVar(value=DEFAULT_DIR)
        ttk.Entry(folder_row, textvariable=self.folder_var).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Browse…", command=self._browse).pack(side="left", padx=(8, 0))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", **pad)
        self.dl_btn = ttk.Button(btn_row, text="⬇ Download MP3", command=self._start)
        self.dl_btn.pack(side="left", fill="x", expand=True)
        self.open_btn = ttk.Button(btn_row, text="📁 Open folder", command=lambda: open_folder(self.folder_var.get()), state="disabled")
        self.open_btn.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(self, mode="determinate", maximum=100)
        self.progress.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="Ready — paste a URL and hit Download.")
        ttk.Label(self, textvariable=self.status_var, font=("Segoe UI", 9)).pack(anchor="w", **pad)

        ttk.Label(self, text="Log", font=("Segoe UI", 10, "bold")).pack(anchor="w", **pad)
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(log_frame, height=8, wrap="word", font=("Consolas", 9), state="disabled")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    # ---------- actions ----------
    def _browse(self):
        chosen = filedialog.askdirectory(initialdir=self.folder_var.get())
        if chosen:
            self.folder_var.set(chosen)

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "status":
                    self._set_status(payload)
                elif kind == "progress":
                    self.progress["value"] = payload
                elif kind == "done":
                    self._on_done(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def _start(self):
        if self.downloading:
            return
        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        if not url:
            messagebox.showwarning(APP_TITLE, "Paste a YouTube URL first.")
            return
        if not shutil.which("ffmpeg"):
            messagebox.showerror(APP_TITLE, "ffmpeg not found.\n\nInstall it and make sure it's on your PATH:\n• Windows: winget install Gyan.FFmpeg\n• Linux Mint: sudo apt install ffmpeg")
            return
        os.makedirs(folder, exist_ok=True)
        self.downloading = True
        self.dl_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self.progress["value"] = 0
        self._log(f"Starting: {url}")
        threading.Thread(target=self._download, args=(url, folder), daemon=True).start()

    def _progress_hook(self, d):
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            pct = (done / total * 100) if total else 0
            speed = d.get("speed")
            eta = d.get("eta")
            info = f"Downloading… {pct:.1f}%"
            if speed:
                info += f"  ({speed / 1024 / 1024:.1f} MB/s"
                info += f", ETA {eta}s)" if eta else ")"
            self.msg_queue.put(("progress", pct))
            self.msg_queue.put(("status", info))
        elif status == "finished":
            self.msg_queue.put(("status", "Download finished — converting to MP3…"))
            self.msg_queue.put(("log", f"Saved: {d.get('filename')}"))

    def _download(self, url, folder):
        ydl_opts = {
            "format": "ba/b",
            "cookiesfrombrowser": ("chrome",),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }],
            "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "audio") if info else "audio"
            self.msg_queue.put(("done", (True, title)))
        except Exception as e:
            self.msg_queue.put(("log", f"ERROR: {e}"))
            self.msg_queue.put(("done", (False, str(e))))

    def _on_done(self, result):
        ok, detail = result
        self.downloading = False
        self.dl_btn.configure(state="normal")
        if ok:
            self.progress["value"] = 100
            self._set_status("Done — MP3 ready for the lab. 🎛️")
            self._log(f"Done: {detail}")
            self.open_btn.configure(state="normal")
        else:
            self._set_status("Download failed — see log.")
            messagebox.showerror(APP_TITLE, f"Download failed:\n{detail}")


if __name__ == "__main__":
    App().mainloop()
