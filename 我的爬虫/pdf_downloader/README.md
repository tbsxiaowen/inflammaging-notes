# PDF下载工具

一个用于从PDF查看器页面下载PDF文件和HTML内容的工具。

## 功能

- 从PDF查看器URL中提取实际的PDF文件URL
- 下载PDF文件
- 下载HTML页面内容
- 自动重试机制
- 支持自定义输出目录

## 依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
cd "/Users/tuboshu/土拨鼠的蛋/我的爬虫/pdf_downloader"
python3 download_pdf.py <URL> [选项]
```

### 参数说明

- `URL`: PDF查看器URL或PDF文件URL（必需）
- `-o, --output`: 输出目录（可选，默认为项目目录下的 `downloaded_pdfs` 文件夹）
- `-f, --filename`: PDF文件名（可选，默认从URL提取）
- `--html-only`: 仅下载HTML页面
- `--pdf-only`: 仅下载PDF文件

### 示例

```bash
# 下载PDF和HTML
python3 download_pdf.py "https://example.com/viewer.html?file=document.pdf"

# 仅下载PDF
python3 download_pdf.py "https://example.com/viewer.html?file=document.pdf" --pdf-only

# 指定输出目录
python3 download_pdf.py "https://example.com/viewer.html?file=document.pdf" -o ./output
```

## 注意事项

- 工具会自动处理URL编码和路径拼接
- 如果无法提取PDF URL，会直接使用原URL尝试下载
- 下载的文件会保存在指定的输出目录中

