"""
视频下载器 — 支持 YouTube 和哔哩哔哩
粘贴链接即可自动识别并下载，基于 yt-dlp。
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

try:
    import yt_dlp
except ImportError:
    print("缺少 yt-dlp，正在安装…")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOWNLOAD_DIR = os.path.join(SCRIPT_DIR, "downloads")

URL_PATTERNS = [
    re.compile(r'https?://(www\.)?youtube\.com/watch\?v='),
    re.compile(r'https?://youtu\.be/'),
    re.compile(r'https?://(www\.)?bilibili\.com/video/'),
    re.compile(r'https?://b23\.tv/'),
    re.compile(r'https?://m\.bilibili\.com/video/'),
]


def looks_like_video_url(text: str) -> bool:
    text = text.strip()
    return any(p.search(text) for p in URL_PATTERNS)


def detect_platform(url: str) -> str:
    if "bilibili.com" in url or "b23.tv" in url:
        return "哔哩哔哩"
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    return "未知"


class DownloadApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("视频下载器  ▶  YouTube + 哔哩哔哩")
        self.geometry("720x560")
        self.minsize(600, 480)
        self.configure(bg="#f5f5f5")

        self._download_dir = tk.StringVar(value=DEFAULT_DOWNLOAD_DIR)
        self._url_var = tk.StringVar()
        self._status_var = tk.StringVar(value="就绪 — 粘贴视频链接即可开始下载")
        self._progress_var = tk.DoubleVar(value=0)
        self._downloading = False
        self._last_clipboard = ""

        self._build_ui()
        self._poll_clipboard()

    # ── UI ────────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Helvetica", 18, "bold"),
                        background="#f5f5f5", foreground="#333")
        style.configure("Sub.TLabel", font=("Helvetica", 11),
                        background="#f5f5f5", foreground="#666")
        style.configure("Status.TLabel", font=("Helvetica", 10),
                        background="#f5f5f5", foreground="#888")
        style.configure("Accent.TButton", font=("Helvetica", 12, "bold"))
        style.configure("TFrame", background="#f5f5f5")
        style.configure("Log.TFrame", background="#fff")

        pad = {"padx": 20, "pady": (6, 2)}

        # 标题
        ttk.Label(self, text="🎬 视频下载器", style="Title.TLabel").pack(
            pady=(18, 0))
        ttk.Label(self, text="支持 YouTube 和哔哩哔哩，粘贴链接自动下载",
                  style="Sub.TLabel").pack(pady=(2, 12))

        # URL 输入
        url_frame = ttk.Frame(self)
        url_frame.pack(fill="x", **pad)
        ttk.Label(url_frame, text="视频链接：", background="#f5f5f5",
                  font=("Helvetica", 11)).pack(side="left")
        self._url_entry = ttk.Entry(url_frame, textvariable=self._url_var,
                                     font=("Helvetica", 12))
        self._url_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # 保存目录
        dir_frame = ttk.Frame(self)
        dir_frame.pack(fill="x", **pad)
        ttk.Label(dir_frame, text="保存位置：", background="#f5f5f5",
                  font=("Helvetica", 11)).pack(side="left")
        ttk.Entry(dir_frame, textvariable=self._download_dir,
                  font=("Helvetica", 11), state="readonly").pack(
            side="left", fill="x", expand=True, padx=(6, 6))
        ttk.Button(dir_frame, text="选择…",
                   command=self._choose_dir).pack(side="right")

        # 按钮行
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=20, pady=(10, 4))
        self._dl_btn = ttk.Button(btn_frame, text="⬇  开始下载",
                                   style="Accent.TButton",
                                   command=self._start_download)
        self._dl_btn.pack(side="left")
        ttk.Button(btn_frame, text="粘贴链接",
                   command=self._paste_url).pack(side="left", padx=(10, 0))
        ttk.Button(btn_frame, text="清空日志",
                   command=self._clear_log).pack(side="right")

        # 进度条
        self._progress = ttk.Progressbar(self, variable=self._progress_var,
                                          maximum=100, length=400)
        self._progress.pack(fill="x", padx=20, pady=(8, 2))

        # 状态
        ttk.Label(self, textvariable=self._status_var,
                  style="Status.TLabel").pack(anchor="w", padx=20)

        # 日志
        log_frame = ttk.Frame(self, style="Log.TFrame")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(8, 16))
        self._log = tk.Text(log_frame, height=10, font=("Menlo", 10),
                            bg="#fff", fg="#333", relief="flat",
                            state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._log.pack(side="left", fill="both", expand=True)

    # ── 辅助方法 ──────────────────────────────────────────────────────

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self._download_dir.get())
        if d:
            self._download_dir.set(d)

    def _paste_url(self):
        try:
            text = self.clipboard_get().strip()
            if text:
                self._url_var.set(text)
        except tk.TclError:
            pass

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _append_log(self, msg: str):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _poll_clipboard(self):
        """每秒检测剪贴板，发现视频链接自动填入"""
        try:
            text = self.clipboard_get().strip()
            if text != self._last_clipboard and looks_like_video_url(text):
                self._last_clipboard = text
                self._url_var.set(text)
                platform = detect_platform(text)
                self._status_var.set(f"检测到 {platform} 链接，点击下载或等待自动下载")
                self._append_log(f"[剪贴板] 检测到 {platform} 链接：{text}")
                if not self._downloading:
                    self.after(500, self._start_download)
            elif text != self._last_clipboard:
                self._last_clipboard = text
        except tk.TclError:
            pass
        self.after(1000, self._poll_clipboard)

    # ── 下载逻辑 ──────────────────────────────────────────────────────

    def _start_download(self):
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先粘贴视频链接")
            return
        if self._downloading:
            self._append_log("[提示] 下载进行中，请等待当前任务完成")
            return

        self._downloading = True
        self._dl_btn.configure(state="disabled")
        self._progress_var.set(0)
        platform = detect_platform(url)
        self._status_var.set(f"正在下载 {platform} 视频…")
        self._append_log(f"\n{'='*50}")
        self._append_log(f"[开始] {datetime.now().strftime('%H:%M:%S')}  {platform}")
        self._append_log(f"  URL: {url}")

        thread = threading.Thread(target=self._do_download, args=(url,),
                                  daemon=True)
        thread.start()

    def _do_download(self, url: str):
        out_dir = self._download_dir.get()
        os.makedirs(out_dir, exist_ok=True)

        def progress_hook(d):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                if total > 0:
                    pct = downloaded / total * 100
                    self._progress_var.set(pct)
                    speed = d.get("_speed_str", "")
                    eta = d.get("_eta_str", "")
                    self.after(0, self._status_var.set,
                              f"下载中 {pct:.1f}%  {speed}  ETA {eta}")
            elif d["status"] == "finished":
                self._progress_var.set(100)
                filename = os.path.basename(d.get("filename", ""))
                self.after(0, self._append_log,
                           f"[完成] {filename}")

        is_bilibili = "bilibili.com" in url or "b23.tv" in url

        ydl_opts = {
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }

        if is_bilibili:
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
            ydl_opts["http_headers"] = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
            }
        else:
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "未知")
                self.after(0, self._on_success, title)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_success(self, title: str):
        self._downloading = False
        self._dl_btn.configure(state="normal")
        self._progress_var.set(100)
        self._status_var.set(f"✅ 下载完成：{title}")
        self._append_log(f"[成功] {title}")
        self._append_log(f"  保存到：{self._download_dir.get()}")

    def _on_error(self, error: str):
        self._downloading = False
        self._dl_btn.configure(state="normal")
        self._progress_var.set(0)
        self._status_var.set("❌ 下载失败")
        self._append_log(f"[错误] {error}")


def main():
    os.makedirs(DEFAULT_DOWNLOAD_DIR, exist_ok=True)
    app = DownloadApp()
    app.mainloop()


if __name__ == "__main__":
    main()
