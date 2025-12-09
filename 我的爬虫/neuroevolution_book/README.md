# 神经进化书籍爬虫

这个脚本用于爬取 https://neuroevolutionbook.com/ne_book.html 并将内容保存为PDF格式。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
python scrape_book.py
```

脚本会自动：
1. 获取网页内容
2. 清理和优化HTML
3. 生成PDF文件（`neuroevolution_book.pdf`）

## 注意事项

- 如果PDF生成失败，会保存HTML文件作为备选
- 需要安装weasyprint或pdfkit来生成PDF
- 建议使用weasyprint，因为它更易于安装和使用

