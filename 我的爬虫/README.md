# 我的爬虫项目集合

这个文件夹包含了所有的网络爬虫项目，每个项目都有独立的子文件夹。

## 📁 项目列表

### 1. `fudan_faculty/` - 复旦大学导师信息爬虫
- **功能**: 爬取复旦大学生命科学学院的教师名录信息
- **输出**: CSV、JSON格式的教师数据
- **用途**: 批量获取教师姓名、职称、邮箱、研究方向等信息

### 2. `neuroevolution_book/` - 神经进化书籍爬虫
- **功能**: 将在线书籍网页保存为PDF格式
- **输出**: PDF文件
- **用途**: 下载并保存在线书籍，方便离线阅读

### 3. `pdf_downloader/` - PDF下载工具
- **功能**: 从PDF查看器页面下载PDF文件
- **输出**: PDF文件和HTML文件
- **用途**: 通用PDF下载工具，支持各种PDF查看器页面

## 🚀 快速开始

### 首次使用（设置虚拟环境）

```bash
# 进入爬虫项目文件夹
cd 我的爬虫

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装所有依赖（只需一次）
pip install -r requirements.txt
```

### 日常使用

```bash
# 进入爬虫项目文件夹
cd 我的爬虫

# 激活虚拟环境（每次使用前）
source venv/bin/activate  # macOS/Linux

# 运行任意项目的脚本
cd neuroevolution_book
python3 scrape_book.py

# 或
cd fudan_faculty
python3 scrape_faculty.py

# 使用完后退出虚拟环境
deactivate
```

> 💡 **提示**：所有项目共用同一个虚拟环境（节省空间，约160MB），因为依赖都兼容。

## 📝 项目结构

```
我的爬虫/
├── README.md                    # 本文件
├── requirements.txt             # 所有项目的依赖汇总
├── venv/                        # 统一的虚拟环境（所有项目共用）
├── fudan_faculty/               # 项目1
│   ├── scrape_faculty.py
│   ├── requirements.txt
│   └── README.md
├── neuroevolution_book/         # 项目2
│   ├── scrape_book.py
│   ├── requirements.txt
│   └── README.md
└── pdf_downloader/              # 项目3
    ├── download_pdf.py
    ├── requirements.txt
    └── README.md
```

## ⚠️ 注意事项

- 请遵守目标网站的robots.txt和使用条款
- 合理控制爬取频率，避免对服务器造成压力
- 仅用于学习和研究目的
- **使用前记得激活虚拟环境**：`source venv/bin/activate`

## 📚 更多说明

- `最优方案说明.md` - 为什么使用统一虚拟环境
- `虚拟环境使用说明.md` - 虚拟环境详细教程
- 各项目文件夹内的 `README.md` - 项目具体使用方法

