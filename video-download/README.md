# 视频下载器

支持 **YouTube** 和 **哔哩哔哩** 视频下载。

## 安装依赖

```bash
pip install -r requirements_download_video.txt
```

## 使用方式

### 图形界面（推荐）

```bash
python download_gui.py
```

- 启动后自动监听剪贴板
- 复制视频链接即可自动开始下载
- 也可手动粘贴链接后点击"开始下载"
- 支持自定义保存目录

### 命令行

```bash
python download_video.py <视频链接>
python download_video.py <视频链接> -o ~/Downloads
```

## 支持的链接格式

| 平台 | 链接示例 |
|------|---------|
| YouTube | `https://www.youtube.com/watch?v=xxx` |
| YouTube | `https://youtu.be/xxx` |
| 哔哩哔哩 | `https://www.bilibili.com/video/BVxxx` |
| 哔哩哔哩 | `https://b23.tv/xxx` |

## 下载位置

默认保存到 `downloads/` 目录。
