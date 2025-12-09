# 炎症衰老研究笔记 (Inflammaging Notes)

一个聚焦炎症衰老（Inflammaging）的静态网站，用来汇总论文链接、分享研究随笔，并保留联系信息。站点基于纯 HTML/CSS 构建，可直接托管在 GitHub Pages、Vercel 等静态服务上。

## 目录结构

```text
inflammaging_site/
├── index.html               # 首页
├── papers.html              # Papers｜论文拆解
├── pathways-methods.html    # Pathways & Methods｜通路与方法区
├── basics.html              # Basics｜基础概念（由脚本生成）
├── stories-evolution.html   # Stories & Evolution｜人类演化 & 疾病小随笔
├── notes/                   # 文章详情页（脚本生成）
│   └── *.html
├── markdown 文章/           # Markdown 原稿
│   └── *.markdown
├── scripts/
│   └── build_notes.py       # 构建脚本
├── styles.css               # 全站样式
└── README.md
```

## 写作与构建流程

1. **撰写 Markdown 内容**
   - 在 `markdown 文章/` 目录新增 `.markdown` 文件。
   - 开头添加 front matter，务必指明 `category`（决定文章出现在哪个板块）：
   ```markdown
   ---
   title: 生存压力导致慢性炎症和衰老？
   date: 2025-11-11
   tags: [Inflammaging, 灵感笔记]
   category: basics   # 可选：basics / papers / pathways / stories
   ---
   
   ## 小节标题
   - 要点 1
   - 要点 2
   ```
   - `category` 对应关系：
     | category 值 | 页面 |
     | --- | --- |
     | `basics` | Basics｜基础概念 |
     | `papers` | Papers｜论文拆解 |
     | `pathways` | Pathways & Methods｜通路与方法区 |
     | `stories` | Stories & Evolution｜人类演化 & 疾病小随笔 |
   - 其余内容直接写 Markdown 正文即可。

2. **生成页面**
   在项目根目录执行脚本，让列表页与详情页保持最新：
   ```bash
   python3 scripts/build_notes.py
   ```
   运行后会在终端看到 `已处理 X 篇文章，按板块分布：...` 的提示。

3. **预览与提交**
   本地用浏览器打开任意 `.html` 文件确认样式无误，然后提交：
   ```bash
   git add .
   git commit -m "Update notes"
   git push origin main
   ```

## 发布到 GitHub Pages

1. 初始化仓库并推送到 GitHub：
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<username>/<repo>.git
   git push -u origin main
   ```

2. 在 GitHub 仓库 `Settings → Pages` 中，选择 `Deploy from a branch`，分支设为 `main`、目录选 `/(root)`，保存后等待几分钟。

3. 访问 `https://<username>.github.io/<repo>/` 即可查看站点。

> 提示：若需要自定义域名，可在仓库根目录添加 `CNAME` 文件，并配置 DNS。

## 联系

- 表单：`contact.html` 使用 Formspree 端点（记得将 `YOUR_FORM_ID` 替换为真实 ID）
- 邮箱：在页面中替换为你的真实地址

欢迎持续记录灵感，在 markdown 中发挥想象力即可，其余构建工作交给脚本完成。
