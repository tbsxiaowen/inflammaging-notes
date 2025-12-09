# 复旦生科院教师名录爬虫

一个简单脚本组合，用于批量抓取复旦大学生命科学学院「教师名录」分页下的全部教师信息，并整理成易读表格。

## 功能

- 自动遍历 `https://life.fudan.edu.cn/28175/list*.htm` 全部分页；
- 提取教师姓名、发布时间、详情页链接、照片链接等基础字段；
- 抓取教师详情页正文，解析 “职称 / 邮箱 / 办公地点 / 研究方向 / 代表性论文” 等栏目；
- 输出原始 JSON、原始 CSV，以及整理后的 `faculty_directory_clean.csv`（信息按列分类，更易在表格中阅读）；
- 可保存所有列表页 HTML 供校验。

## 目录结构

```
我的爬虫/fudan_faculty/
├── scrape_faculty.py          # 主爬虫脚本
├── format_faculty_table.py    # 将 JSON 整理成清晰表格
└── output/
    ├── faculty_directory.json       # 全字段 JSON
    ├── faculty_directory.csv        # 原始 CSV
    ├── faculty_directory_clean.csv  # 整理后的 CSV
    └── raw_html/list*.html          # 每个列表页的快照
```

## 依赖

```bash
pip install requests beautifulsoup4 lxml
```

> 若未安装 `lxml`，脚本会自动退回到 Python 内置解析器，但推荐安装以提高解析鲁棒性。

## 使用方法

1. **抓取教师数据**
   ```bash
   cd "/Users/tuboshu/土拨鼠的蛋/我的爬虫/fudan_faculty"
   python3 scrape_faculty.py --delay 0.3 --insecure
   ```
   - `--delay`：访问详情页的节流秒数（默认 0.4，可根据网络情况调整）；
   - `--pages N`：仅抓前 N 页，调试用；
   - `--insecure`：忽略 HTTPS 证书校验（如无需可删除）。

2. **生成整理后的表格**
   ```bash
   python3 format_faculty_table.py
   ```
   运行后会得到 `output/faculty_directory_clean.csv`，列包含：
   - 姓名、职称、职务、电子邮箱、办公地点/电话、个人主页；
   - 研究方向、个人简介、授课情况、招生专业、代表性论文、其他信息；
   - 详情链接、照片链接。

## 注意事项

- 尊重目标网站的 robots/版权要求，仅用于科研或学习。访问频率请保持适度（脚本已自带节流）。
- 若网络环境对学校证书校验不友好，可使用 `--insecure`；如环境正常，建议去掉该参数。
- 如需增量更新，可在 `scrape_faculty.py` 内加上“已抓取 URL 去重/缓存”逻辑。

有需要进一步拆分字段或导入数据库，可基于 `faculty_directory.json` 进行二次处理。欢迎根据个人需求扩展。

