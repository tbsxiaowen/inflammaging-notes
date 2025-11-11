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
NOTES_FILE = BASE_DIR / "notes.html"
IDEAS_FILE = BASE_DIR / "ideas.html"
NOTE_OUTPUT_DIR = BASE_DIR / "notes"
PLACEHOLDER_START = "<!-- BEGIN:ARTICLE_LIST -->"
PLACEHOLDER_END = "<!-- END:ARTICLE_LIST -->"
IDEAS_PLACEHOLDER_START = "<!-- BEGIN:IDEA_LIST -->"
IDEAS_PLACEHOLDER_END = "<!-- END:IDEA_LIST -->"

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


def simple_markdown_to_html(text: str) -> str:
    """极简 Markdown 解析器，覆盖标题、引用、列表、段落。"""
    lines = text.splitlines()
    html_parts: List[str] = []
    list_stack: List[str] = []
    in_blockquote = False
    paragraph_lines: List[str] = []

    def flush_paragraph() -> None:
        if paragraph_lines:
            paragraph = " ".join(paragraph_lines).strip()
            if paragraph:
                html_parts.append(f"<p>{html.escape(paragraph)}</p>")
            paragraph_lines.clear()

    def close_lists(to_level: int = 0) -> None:
        while len(list_stack) > to_level:
            tag = list_stack.pop()
            html_parts.append(f"</{tag}>")

    for raw in lines:
        line = raw.rstrip()
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

        summary_lines = []
        for line in body_raw.splitlines():
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

        slug = slugify(title, fallback_seed=md_path.stem, sequence=idx)
        html_body = markdown_to_html(body_raw)

        notes.append(
            Note(
                title=title,
                date_display=date_display,
                summary=summary,
                tags=tags,
                slug=slug,
                html_body=html_body,
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
            <h4>{html.escape(note.title)}</h4>
            <p class=\"article-card__meta\">{html.escape(meta_line)}</p>
          </header>
          <p class=\"article-card__summary\">{html.escape(note.summary)}</p>
          <div class=\"article-card__actions\">
            <a class=\"article-card__link\" href=\"notes/{html.escape(note.slug)}.html\">阅读随笔</a>
          </div>
        </article>""".strip()


def indent_lines(text: str, spaces: int) -> str:
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" if line else "" for line in text.splitlines())


def build_article_html(notes: List[Note]) -> str:
    if not notes:
        return "        <p class=\"empty-state\">暂时还没有随笔，欢迎稍后再来。</p>"

    rendered = [textwrap.indent(render_note(note), "        ") for note in notes]
    return "\n".join(rendered)


NOTE_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{title} - 炎症衰老研究随笔</title>
  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
  <link href=\"https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap\" rel=\"stylesheet\">
  <link rel=\"stylesheet\" href=\"../styles.css\">
</head>
<body>
  <header class=\"site-header\">
    <div class=\"brand\">
      <span class=\"brand-mark\">IA</span>
      <div>
        <h1>炎症衰老研究笔记</h1>
        <p class=\"tagline\">随笔</p>
      </div>
    </div>
    <nav class=\"site-nav\">
      <a href=\"../index.html\">首页</a>
      <a href=\"../papers.html\">论文精选</a>
      <a href=\"../ideas.html\">研究想法</a>
      <a href=\"../resources.html\">工具与资源</a>
      <a href=\"../notes.html\" class=\"active\">随笔</a>
      <a href=\"../contact.html\">联系我</a>
    </nav>
  </header>

  <main class=\"content\">
    <section class=\"hero hero-sub hero-sub--notes\">
      <div class=\"hero-copy\">
        <span class=\"badge\">Field Notes</span>
        <h2>{title}</h2>
        <p class=\"article-detail__meta\">{meta_line}</p>
        <a class=\"article-detail__back\" href=\"../notes.html\">← 返回随笔列表</a>
      </div>
      <div class=\"hero-illustration hero-illustration--mini\" aria-hidden=\"true\">
        <div class=\"blob blob-2\"></div>
        <div class=\"spark spark-3\"></div>
      </div>
    </section>

    <section class=\"section article-detail\">
      <article class=\"article-detail__card\">
{body}
      </article>
    </section>
  </main>

  <footer class=\"site-footer\">
    <p>© <span id=\"year\"></span> 炎症衰老研究笔记</p>
    <p>邮箱：<a href=\"mailto:your.email@example.com\">your.email@example.com</a></p>
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
        detail_html = NOTE_PAGE_TEMPLATE.format(
            title=html.escape(note.title),
            meta_line=html.escape(meta_line),
            body=textwrap.indent(note.html_body, "        ")
        )
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
    article_html = build_article_html(notes)

    if args.dry_run:
        print(article_html)
        return

    update_section(NOTES_FILE, PLACEHOLDER_START, PLACEHOLDER_END, article_html)
    write_note_pages(notes)
    print(f"已处理 {len(notes)} 篇随笔，并更新 notes.html")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover
        print(f"构建失败：{exc}", file=sys.stderr)
        sys.exit(1)
