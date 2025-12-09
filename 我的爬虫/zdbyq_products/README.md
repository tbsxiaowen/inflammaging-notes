# 中电变压器产品爬虫

爬取 https://www.zdbyq.cn/product/ 下所有产品的详情页内容。

## 功能

- 自动获取产品列表页的所有产品链接
- 访问每个产品的详情页
- 提取产品信息（标题、描述、内容、图片、规格参数等）
- 保存为JSON、CSV和单独文本文件

## 安装依赖

```bash
cd 我的爬虫/zdbyq_products
source ../venv/bin/activate  # 使用统一的虚拟环境
pip install -r requirements.txt
```

## 使用方法

```bash
cd 我的爬虫/zdbyq_products
source ../venv/bin/activate
python3 scrape_products.py
```

## 输出文件

- `output/products.json` - 所有产品的JSON数据
- `output/products.csv` - 产品基本信息CSV文件
- `output/product_details/` - 每个产品的详细文本文件

## 注意事项

- 脚本会自动延迟请求，避免对服务器造成压力
- 请遵守网站的robots.txt和使用条款
- 仅用于学习和研究目的

