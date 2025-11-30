#!/usr/bin/env python3
"""根据 `markdown 文章/` 目录生成随笔页面内容。

运行方式：
    python scripts/build_notes.py

依赖：
    可选依赖 `markdown` 库，用于更完整的 Markdown 转 HTML 解析。
    若未安装，会退回到简单的内置解析器。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import textwrap
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
MARKDOWN_DIR = BASE_DIR / "markdown 文章"
NOTES_FILE = BASE_DIR / "basics.html"
PAPERS_FILE = BASE_DIR / "papers.html"
PATHWAYS_FILE = BASE_DIR / "pathways-methods.html"
STORIES_FILE = BASE_DIR / "stories-evolution.html"
NOTE_OUTPUT_DIR = BASE_DIR / "notes"
PLACEHOLDER_START = "<!-- BEGIN:ARTICLE_LIST -->"
PLACEHOLDER_END = "<!-- END:ARTICLE_LIST -->"

# 板块映射
CATEGORY_MAP = {
    "basics": ("basics.html", "Basics｜基础概念", "hero-sub--basics", "Basics"),
    "papers": ("papers.html", "Papers｜论文拆解", "hero-sub--papers", "Papers"),
    "pathways": ("pathways-methods.html", "Pathways & Methods｜通路与方法区", "hero-sub--pathways", "Pathways"),
    "stories": ("stories-evolution.html", "Stories & Evolution｜人类演化 & 疾病小随笔", "hero-sub--stories", "Stories"),
}

try:
    import markdown  # type: ignore
except ImportError:  # pragma: no cover
    markdown = None

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass(order=True)
class Note:
    sort_index: dt.datetime = field(init=False, repr=False)
    title: str
    date_display: str
    summary: str
    tags: List[str]
    slug: str
    html_body: str
    category: str = "basics"  # 默认分类为 basics

    def __post_init__(self) -> None:
        try:
            self.sort_index = dt.datetime.strptime(self.date_display, "%Y-%m-%d")
        except ValueError:
            # 未注明日期或格式不标准时排在最旧
            self.sort_index = dt.datetime.min

# ---------------------------------------------------------------------------
# Markdown 元信息解析
# ---------------------------------------------------------------------------

FRONT_MATTER_PATTERN = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*):\s*(?P<value>.+)$")
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


def parse_front_matter(lines: List[str]) -> dict:
    meta = {}
    for line in lines:
        match = FRONT_MATTER_PATTERN.match(line.strip())
        if not match:
            continue
        key = match.group("key").lower()
        value = match.group("value").strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                meta[key] = json.loads(value)
            except json.JSONDecodeError:
                meta[key] = [v.strip() for v in re.split(r"[,，、]", value.strip("[]")) if v.strip()]
        else:
            meta[key] = value
    return meta


def extract_meta(text: str, path: Path) -> tuple[dict, str]:
    lines = text.splitlines()
    meta = {}
    body_start = 0

    if lines and lines[0].strip() == "---":
        body_start = 1
        front_lines: List[str] = []
        while body_start < len(lines) and lines[body_start].strip() != "---":
            front_lines.append(lines[body_start])
            body_start += 1
        meta.update(parse_front_matter(front_lines))
        body_start += 1  # 跳过结束分隔线
    else:
        body_start = 0

    body_lines = lines[body_start:]

    # 标题
    if "title" not in meta:
        for line in body_lines:
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
                break
        else:
            meta["title"] = path.stem

    # 解析 blockquote 元信息
    for line in body_lines:
        if not line.lstrip().startswith(">"):  # 非引用行忽略
            continue
        clean = line.lstrip("> ")
        if "日期" in clean and "date" not in meta:
            date_match = DATE_PATTERN.search(clean)
            if date_match:
                meta["date"] = date_match.group(1)
        if "标签" in clean and "tags" not in meta:
            tag_part = clean.split("：", 1)[-1]
            meta["tags"] = [t.strip() for t in re.split(r"[,，、]", tag_part) if t.strip()]
        if "摘要" in clean and "summary" not in meta:
            meta["summary"] = clean.split("：", 1)[-1].strip()

    if "tags" not in meta:
        meta["tags"] = []

    return meta, "\n".join(body_lines)

# ---------------------------------------------------------------------------
# Markdown 转 HTML
# ---------------------------------------------------------------------------

LIST_ITEM_PATTERN = re.compile(r"^\s*([*+-]|\d+[.)])\s+")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
BLOCKQUOTE_PATTERN = re.compile(r"^>\s?(.*)$")
HORIZONTAL_RULE_PATTERN = re.compile(r"^\s*([-*_])\s*\1\s*\1\s*$")
TABLE_ROW_PATTERN = re.compile(r"^\s*\|(.+)\|\s*$")
TABLE_SEPARATOR_PATTERN = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")


def parse_table_row(line: str) -> List[str]:
    """解析表格行，返回单元格列表"""
    if not line.strip().startswith("|"):
        return []
    cells = [cell.strip() for cell in line.strip().split("|")[1:-1]]
    return cells


def is_table_separator(line: str) -> bool:
    """判断是否是表格分隔符行"""
    return bool(TABLE_SEPARATOR_PATTERN.match(line))


def simple_markdown_to_html(text: str) -> str:
    """极简 Markdown 解析器，覆盖标题、引用、列表、段落、表格。"""
    lines = text.splitlines()
    html_parts: List[str] = []
    list_stack: List[str] = []
    in_blockquote = False
    paragraph_lines: List[str] = []
    table_rows: List[List[str]] = []
    in_table = False

    def flush_paragraph() -> None:
        if paragraph_lines:
            paragraph = " ".join(paragraph_lines).strip()
            if paragraph:
                html_parts.append(f"<p>{html.escape(paragraph)}</p>")
            paragraph_lines.clear()

    def flush_table() -> None:
        if not table_rows:
            return
        html_parts.append("<table>")
        # 第一行是表头
        if table_rows:
            html_parts.append("  <thead>")
            html_parts.append("    <tr>")
            for cell in table_rows[0]:
                html_parts.append(f"      <th>{html.escape(cell)}</th>")
            html_parts.append("    </tr>")
            html_parts.append("  </thead>")
            html_parts.append("  <tbody>")
            # 后续行是数据行
            for row in table_rows[1:]:
                html_parts.append("    <tr>")
                for cell in row:
                    html_parts.append(f"      <td>{html.escape(cell)}</td>")
                html_parts.append("    </tr>")
            html_parts.append("  </tbody>")
        html_parts.append("</table>")
        table_rows.clear()

    def close_lists(to_level: int = 0) -> None:
        while len(list_stack) > to_level:
            tag = list_stack.pop()
            html_parts.append(f"</{tag}>")

    for raw in lines:
        line = raw.rstrip()
        
        # 先检查是否是表格分隔符行（必须在表格行检查之前）
        if is_table_separator(line):
            # 表格分隔符行，跳过
            continue
        
        # 检查是否是表格行
        if TABLE_ROW_PATTERN.match(line):
            cells = parse_table_row(line)
            if cells:
                if not in_table:
                    flush_paragraph()
                    close_lists()
                    if in_blockquote:
                        html_parts.append("</blockquote>")
                        in_blockquote = False
                    in_table = True
                table_rows.append(cells)
                continue
        else:
            # 不是表格行，如果之前在表格中，先结束表格
            if in_table:
                flush_table()
                in_table = False
        
        if not line.strip():
            flush_paragraph()
            close_lists()
            if in_blockquote:
                html_parts.append("</blockquote>")
                in_blockquote = False
            continue

        if HORIZONTAL_RULE_PATTERN.match(line):
            flush_paragraph()
            close_lists()
            if in_blockquote:
                html_parts.append("</blockquote>")
                in_blockquote = False
            html_parts.append("<hr>")
            continue

        heading = HEADING_PATTERN.match(line)
        if heading:
            flush_paragraph()
            close_lists()
            if in_blockquote:
                html_parts.append("</blockquote>")
                in_blockquote = False
            level = len(heading.group(1))
            content = heading.group(2).strip()
            html_parts.append(f"<h{level}>{html.escape(content)}</h{level}>")
            continue

        blockquote = BLOCKQUOTE_PATTERN.match(line)
        if blockquote:
            flush_paragraph()
            close_lists()
            if not in_blockquote:
                html_parts.append("<blockquote>")
                in_blockquote = True
            html_parts.append(f"  <p>{html.escape(blockquote.group(1).strip())}</p>")
            continue

        list_match = LIST_ITEM_PATTERN.match(line)
        if list_match:
            marker = list_match.group(1)
            list_type = "ol" if marker[0].isdigit() else "ul"
            if not list_stack or list_stack[-1] != list_type:
                close_lists(0)
                html_parts.append(f"<{list_type}>")
                list_stack.append(list_type)
            item_text = line[list_match.end():].strip()
            html_parts.append(f"  <li>{html.escape(item_text)}</li>")
            continue

        paragraph_lines.append(line)

    # 处理最后可能残留的表格或段落
    if in_table:
        flush_table()
    flush_paragraph()
    close_lists()
    if in_blockquote:
        html_parts.append("</blockquote>")

    return "\n".join(html_parts)


def markdown_to_html(text: str) -> str:
    if markdown is not None:  # pragma: no cover - 外部依赖
        return markdown.markdown(
            text,
            extensions=["fenced_code", "tables", "toc", "sane_lists"]
        )
    return simple_markdown_to_html(text)

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

NON_ASCII_PATTERN = re.compile(r"[^a-z0-9-]")
MULTI_HYPHEN_PATTERN = re.compile(r"-+")


def _normalize_slug(text: str) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    ascii_text = NON_ASCII_PATTERN.sub("-", ascii_text)
    ascii_text = MULTI_HYPHEN_PATTERN.sub("-", ascii_text).strip("-")
    return ascii_text


def slugify(value: str, fallback_seed: str, sequence: int) -> str:
    primary = _normalize_slug(value)
    if primary:
        return primary
    fallback = _normalize_slug(fallback_seed)
    if fallback:
        return fallback
    hash_part = fallback_seed.encode("utf-8", "ignore").hex()[:8]
    if hash_part:
        return f"note-{hash_part}"
    return f"note-{sequence:03d}"


def strip_markdown(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"[*_~]", "", text)
    text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*([-*_])\s*\1\s*\1\s*$", "", text, flags=re.MULTILINE)
    return text


def collect_notes() -> List[Note]:
    if not MARKDOWN_DIR.exists():
        print(f"未找到目录：{MARKDOWN_DIR}", file=sys.stderr)
        return []

    notes: List[Note] = []
    all_paths = sorted(MARKDOWN_DIR.glob("*.md")) + sorted(MARKDOWN_DIR.glob("*.markdown"))
    for idx, md_path in enumerate(all_paths, start=1):
        raw_text = md_path.read_text(encoding="utf-8")
        meta, body_raw = extract_meta(raw_text, md_path)
        title: str = meta.get("title", md_path.stem)
        date_display: str = meta.get("date", "未注明日期")
        tags: List[str] = meta.get("tags", [])
        summary: str = meta.get("summary", "")
        category: str = meta.get("category", "basics")  # 默认分类为 basics

        body_lines = body_raw.splitlines()
        summary_lines = []
        for line in body_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith(">"):
                summary_lines.append("")
                continue
            if stripped.startswith("#"):
                summary_lines.append("")
                continue
            summary_lines.append(line)

        body_for_summary = "\n".join(summary_lines)
        paragraphs = [seg.strip() for seg in re.split(r"\n\s*\n", body_for_summary) if seg.strip()]
        plain_text = strip_markdown(paragraphs[0] if paragraphs else body_for_summary)
        if not summary:
            clean_summary = plain_text.strip().replace("\n", " ")
            summary = clean_summary[:140] + "…" if len(clean_summary) > 140 else clean_summary

        # 使用文件名作为 slug 的基础，避免标题 slug 冲突
        slug = slugify(md_path.stem, fallback_seed=title, sequence=idx)
        body_without_meta = []
        for line in body_lines:
            stripped = line.strip()
            if stripped.startswith(">") and any(key in stripped for key in ["date", "tags", "title"]):
                continue
            body_without_meta.append(line)

        body_clean = "\n".join(body_without_meta).strip()

        # 构建展现用的 meta 信息（在正文最前面显示）
        html_body = markdown_to_html(body_clean)

        notes.append(
            Note(
                title=title,
                date_display=date_display,
                summary=summary,
                tags=tags,
                slug=slug,
                html_body=html_body,
                category=category,
            )
        )
    notes.sort(reverse=True)
    return notes


def render_note(note: Note) -> str:
    tags_html = "，".join(note.tags) if note.tags else "暂无标签"
    meta_line = f"{note.date_display} · {tags_html}"

    return f"""
        <article class=\"article-card\" id=\"{html.escape(note.slug)}\">
          <header class=\"article-card__header\">
            <h3>{html.escape(note.title)}</h3>
            <p class=\"article-card__meta\">{html.escape(meta_line)}</p>
          </header>
          <p class=\"article-card__summary\">{html.escape(note.summary)}</p>
          <div class=\"article-card__actions\">
            <a class=\"article-card__link\" href=\"notes/{html.escape(note.slug)}.html\">阅读全文</a>
          </div>
        </article>""".strip()


def indent_lines(text: str, spaces: int) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in text.splitlines())


def build_article_html(notes: List[Note]) -> str:
    if not notes:
        return "        <p class=\"empty-state\">暂时还没有内容，欢迎稍后再来。</p>"

    rendered = [textwrap.indent(render_note(note), "        ") for note in notes]
    return "\n".join(rendered)


def render_note_detail_page(note: Note, combined_body_html: str, meta_line: str) -> str:
    """渲染文章详情页 HTML"""
    category = note.category if note.category in CATEGORY_MAP else "basics"
    html_file, page_title, hero_class, badge = CATEGORY_MAP[category]

    nav_config = [
        ("../index.html", "首页", None),
        ("../papers.html", CATEGORY_MAP["papers"][1], "papers"),
        ("../pathways-methods.html", CATEGORY_MAP["pathways"][1], "pathways"),
        ("../basics.html", CATEGORY_MAP["basics"][1], "basics"),
        ("../stories-evolution.html", CATEGORY_MAP["stories"][1], "stories"),
        ("../contact.html", "联系我", None),
    ]
    nav_links = []
    for href, label, key in nav_config:
        active_class = ' class="active"' if key == category else ""
        nav_links.append(f'      <a href="{href}"{active_class}>{label}</a>')
    nav_html = "\n".join(nav_links)

    back_text_map = {
        "basics": "← 返回基础概念列表",
        "papers": "← 返回论文拆解列表",
        "pathways": "← 返回通路与方法区列表",
        "stories": "← 返回人类演化 & 疾病小随笔列表",
    }
    back_text = back_text_map.get(category, "← 返回列表")

    body_indented = textwrap.indent(combined_body_html.strip(), "        ")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(note.title)} - {page_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../styles.css">
</head>
<body>
  <header class="site-header">
    <div class="brand">
      <span class="brand-mark">IA</span>
      <div>
        <h1>炎症衰老研究笔记</h1>
        <p class="tagline">{page_title}</p>
      </div>
    </div>
    <nav class="site-nav">
{nav_html}
    </nav>
  </header>

  <main class="content">
    <section class="hero hero-sub {hero_class}">
      <div class="hero-copy">
        <span class="badge">{badge}</span>
        <h1>{html.escape(note.title)}</h1>
        <p class="article-detail__meta">{html.escape(meta_line)}</p>
        <a class="article-detail__back" href="../{html_file}">{back_text}</a>
      </div>
      <div class="hero-illustration hero-illustration--mini" aria-hidden="true">
        <div class="blob blob-2"></div>
        <div class="spark spark-3"></div>
      </div>
    </section>

    <section class="section article-detail">
      <article class="article-detail__card">
{body_indented}
      </article>
    </section>
  </main>

  <footer class="site-footer">
    <p>© <span id="year"></span> 炎症衰老研究笔记</p>
  </footer>

  <script>
    document.getElementById('year').textContent = new Date().getFullYear();
  </script>
</body>
</html>
"""


def write_note_pages(notes: List[Note]) -> None:
    NOTE_OUTPUT_DIR.mkdir(exist_ok=True)
    existing = {path.stem for path in NOTE_OUTPUT_DIR.glob("*.html")}
    current = set()

    for note in notes:
        current.add(note.slug)
        tags_html = "，".join(note.tags) if note.tags else "暂无标签"
        meta_line = f"{note.date_display} · {tags_html}"
        detail_path = NOTE_OUTPUT_DIR / f"{note.slug}.html"
        meta_lines = []
        if note.date_display and note.date_display != "未注明日期":
            meta_lines.append(f"日期：{html.escape(note.date_display)}")
        if note.tags:
            meta_lines.append(f"标签：{html.escape('、'.join(note.tags))}")

        meta_html = "\n".join(f"<p class=\"article-detail__meta\">{line}</p>" for line in meta_lines)
        body_html = note.html_body
        combined_body = meta_html + "\n" + body_html if meta_html else body_html
        detail_html = render_note_detail_page(note, combined_body, meta_line)
        detail_path.write_text(detail_html, encoding="utf-8")

    for stale in existing - current:
        stale_path = NOTE_OUTPUT_DIR / f"{stale}.html"
        try:
            stale_path.unlink()
        except FileNotFoundError:
            continue

# ---------------------------------------------------------------------------
# 占位符替换
# ---------------------------------------------------------------------------


def update_section(target: Path, start_marker: str, end_marker: str, content: str) -> None:
    if not target.exists():
        raise FileNotFoundError(f"未找到文件：{target}")

    html_text = target.read_text(encoding="utf-8")
    start_idx = html_text.find(start_marker)
    end_idx = html_text.find(end_marker)

    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise ValueError(f"{target.name} 中未找到有效的占位符注释")

    new_html = (
        html_text[: start_idx + len(start_marker)]
        + "\n"
        + content
        + "\n"
        + html_text[end_idx:]
    )
    target.write_text(new_html, encoding="utf-8")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="构建随笔页面")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印生成的 HTML，不写回 notes.html",
    )
    args = parser.parse_args()

    notes = collect_notes()
    
    # 按 category 分组
    notes_by_category: dict[str, List[Note]] = {}
    for note in notes:
        category = note.category if note.category in CATEGORY_MAP else "basics"
        if category not in notes_by_category:
            notes_by_category[category] = []
        notes_by_category[category].append(note)
    
    # 为每个板块生成文章列表
    for category, (html_file, _, _, _) in CATEGORY_MAP.items():
        category_notes = notes_by_category.get(category, [])
        article_html = build_article_html(category_notes)
        
        if args.dry_run:
            print(f"\n=== {category} ===")
            print(article_html)
            continue
        
        target_file = BASE_DIR / html_file
        if target_file.exists():
            update_section(target_file, PLACEHOLDER_START, PLACEHOLDER_END, article_html)
    
    if args.dry_run:
        return
    
    write_note_pages(notes)
    
    # 统计输出
    stats = ", ".join([f"{cat}: {len(notes_by_category.get(cat, []))}" for cat in CATEGORY_MAP.keys()])
    print(f"已处理 {len(notes)} 篇文章，按板块分布：{stats}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"构建失败：{exc}", file=sys.stderr)
        sys.exit(1)
