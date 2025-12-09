#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复旦大学生命科学学院教师名录抓取脚本
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "❌ 缺少依赖，请先运行: pip install requests beautifulsoup4 lxml"
    ) from exc

try:
    import lxml  # type: ignore  # noqa: F401

    SOUP_PARSER = "lxml"
except Exception:  # pragma: no cover
    SOUP_PARSER = "html.parser"


BASE_URL = "https://life.fudan.edu.cn"
LIST_PATH = "/28175/list{suffix}.htm"


@dataclass
class FacultyProfile:
    """结构化教师信息"""

    name: str
    detail_url: str
    publish_date: str
    list_page: int
    photo_url: Optional[str]
    basic_info: Dict[str, str]
    content_text: str
    content_html: str


class FudanFacultyScraper:
    """抓取教师名录"""

    def __init__(
        self,
        output_dir: Path,
        delay: float = 0.4,
        max_workers: int = 1,
        verify_ssl: bool = True,
    ) -> None:
        self.output_dir = output_dir
        self.delay = max(delay, 0.0)
        self.max_workers = max_workers  # 预留参数，目前串行抓取
        self.verify_ssl = verify_ssl

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir = self.output_dir / "raw_html"
        self.raw_dir.mkdir(exist_ok=True)

        self.session = self._build_session()
        if not self.verify_ssl:
            import urllib3  # 延迟导入，避免未使用

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )
        return session

    def list_url(self, page: int) -> str:
        suffix = "" if page == 1 else str(page)
        return f"{BASE_URL}{LIST_PATH.format(suffix=suffix)}"

    def fetch(self, url: str) -> str:
        resp = self.session.get(url, timeout=20, verify=self.verify_ssl)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def save_raw(self, name: str, html: str) -> None:
        (self.raw_dir / name).write_text(html, encoding="utf-8")

    def extract_total_pages(self, html: str) -> int:
        soup = BeautifulSoup(html, SOUP_PARSER)
        pages = soup.select_one("#wp_paging_w6 .all_pages")
        if pages and pages.text.strip().isdigit():
            return int(pages.text.strip())
        # 回退策略：根据“尾页”链接推断
        last_link = soup.select_one("#wp_paging_w6 .page_nav .last")
        if last_link and "href" in last_link.attrs:
            match = re.search(r"list(\d+)\.htm", last_link["href"])
            if match:
                return int(match.group(1))
        raise RuntimeError("无法解析总页数，请检查页面结构是否变化")

    def parse_list_page(self, html: str, page: int) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, SOUP_PARSER)
        items: List[Dict[str, str]] = []
        for li in soup.select("ul.news_list li.news"):
            anchor = li.find("a")
            date_span = li.select_one(".news_meta")
            if not anchor:
                continue
            href = anchor.get("href", "").strip()
            if not href:
                continue
            full_url = self.to_absolute_url(href)
            items.append(
                {
                    "name": anchor.get_text(strip=True),
                    "detail_url": full_url,
                    "publish_date": date_span.get_text(strip=True) if date_span else "",
                    "list_page": page,
                }
            )
        return items

    @staticmethod
    def to_absolute_url(path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{BASE_URL}{path}"

    def parse_detail(self, entry: Dict[str, str]) -> FacultyProfile:
        html = self.fetch(entry["detail_url"])
        detail_soup = BeautifulSoup(html, SOUP_PARSER)
        article = detail_soup.select_one(".wp_articlecontent")
        if not article:
            raise RuntimeError(f"未找到正文: {entry['detail_url']}")

        photo = article.find("img")
        photo_url = None
        if photo and photo.get("src"):
            photo_url = self.to_absolute_url(photo["src"])

        content_html = article.decode()
        content_text = article.get_text("\n", strip=True)
        basic_info = self.extract_basic_info(article)

        return FacultyProfile(
            name=entry["name"],
            detail_url=entry["detail_url"],
            publish_date=entry["publish_date"],
            list_page=entry["list_page"],
            photo_url=photo_url,
            basic_info=basic_info,
            content_text=content_text,
            content_html=content_html,
        )

    @staticmethod
    def extract_basic_info(article_soup: BeautifulSoup) -> Dict[str, str]:
        """尝试从正文前段抽取“职称/邮箱”等字段"""
        info: Dict[str, str] = {}
        candidates = article_soup.find_all(["p", "li"])
        for block in candidates:
            text = block.get_text(" ", strip=True)
            if not text:
                continue
            match = re.match(r"^([^\s：:]{1,12})[：:]\s*(.+)$", text)
            if match:
                key, value = match.groups()
                key = key.strip()
                value = value.strip()
                if key and value and key not in info:
                    info[key] = value
        return info

    def run(self, max_pages: Optional[int] = None) -> List[FacultyProfile]:
        first_page_html = self.fetch(self.list_url(1))
        self.save_raw("list1.html", first_page_html)
        total_pages = self.extract_total_pages(first_page_html)
        if max_pages:
            total_pages = min(total_pages, max_pages)
        print(f"🔎 共检测到 {total_pages} 页教师名录")

        results: List[FacultyProfile] = []
        for page in range(1, total_pages + 1):
            if page == 1:
                html = first_page_html
            else:
                list_url = self.list_url(page)
                html = self.fetch(list_url)
                self.save_raw(f"list{page}.html", html)
            entries = self.parse_list_page(html, page)
            print(f"📄 第 {page} 页：解析到 {len(entries)} 条记录")
            for entry in entries:
                try:
                    profile = self.parse_detail(entry)
                except Exception as exc:  # pragma: no cover
                    print(f"⚠️  抓取失败 {entry['detail_url']}: {exc}")
                    continue
                results.append(profile)
                time.sleep(self.delay)
        return results

    def save_results(self, profiles: Iterable[FacultyProfile]) -> None:
        profiles_list = list(profiles)
        json_path = self.output_dir / "faculty_directory.json"
        csv_path = self.output_dir / "faculty_directory.csv"

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(
                [asdict(p) for p in profiles_list],
                f,
                ensure_ascii=False,
                indent=2,
            )
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "name",
                    "detail_url",
                    "publish_date",
                    "list_page",
                    "photo_url",
                    "basic_info",
                    "content_text",
                ]
            )
            for profile in profiles_list:
                writer.writerow(
                    [
                        profile.name,
                        profile.detail_url,
                        profile.publish_date,
                        profile.list_page,
                        profile.photo_url or "",
                        json.dumps(profile.basic_info, ensure_ascii=False),
                        profile.content_text,
                    ]
                )
        print("💾 数据已保存：")
        print(f"   - JSON: {json_path}")
        print(f"   - CSV : {csv_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="复旦生科院教师名录抓取工具")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=Path(__file__).parent / "output",
        type=Path,
        help="数据输出目录（默认为脚本目录下 output/）",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="仅抓取前 N 页（调试用）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help="访问详情页的节流时间（秒），默认 0.4",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="忽略 HTTPS 证书校验（仅在必要时使用）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scraper = FudanFacultyScraper(
        output_dir=args.output_dir,
        delay=args.delay,
        verify_ssl=not args.insecure,
    )
    profiles = scraper.run(max_pages=args.pages)
    scraper.save_results(profiles)
    print(f"✅ 完成，共抓取 {len(profiles)} 位教师")


if __name__ == "__main__":
    main()

