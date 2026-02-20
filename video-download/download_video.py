"""
命令行视频下载器 — 支持 YouTube 和哔哩哔哩
用法: python download_video.py <URL> [-o 目录]
"""

import argparse
import os
import sys

try:
    import yt_dlp
except ImportError:
    print("缺少 yt-dlp，正在安装…")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])
    import yt_dlp

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(SCRIPT_DIR, "downloads")


def download(url: str, output_dir: str = DEFAULT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    is_bilibili = "bilibili.com" in url or "b23.tv" in url

    opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "noplaylist": True,
    }

    if is_bilibili:
        opts["http_headers"] = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
        }

    def hook(d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "?")
            speed = d.get("_speed_str", "")
            print(f"\r  下载中 {pct} {speed}", end="", flush=True)
        elif d["status"] == "finished":
            print(f"\n  ✅ 下载完成: {os.path.basename(d['filename'])}")

    opts["progress_hooks"] = [hook]

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        print(f"  标题: {info.get('title', '未知')}")
        print(f"  保存: {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="下载 YouTube / 哔哩哔哩 视频")
    parser.add_argument("url", help="视频链接")
    parser.add_argument("-o", "--output", default=DEFAULT_DIR, help="保存目录")
    args = parser.parse_args()
    download(args.url, args.output)


if __name__ == "__main__":
    main()
