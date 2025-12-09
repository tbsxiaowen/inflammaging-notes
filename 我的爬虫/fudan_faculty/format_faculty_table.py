#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将抓取到的教师名录数据整理成字段更清晰的表格。
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, List


SECTION_TITLES = [
    "教师基本信息",
    "研究方向",
    "个人简介",
    "教育经历",
    "工作经历",
    "授课情况",
    "招生专业",
    "招生信息",
    "承担项目",
    "科研项目",
    "科研成果",
    "获奖情况",
    "代表性论文和论著",
    "出版著作",
    "社会任职",
    "联系方式",
]


def load_profiles(json_path: Path) -> List[Dict]:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, List[str]] = {}
    current_key = None
    pattern = re.compile(rf"^({'|'.join(map(re.escape, SECTION_TITLES))})([:：]|\s|$)")

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = pattern.match(line)
        if match:
            current_key = match.group(1)
            sections.setdefault(current_key, [])
            # 去掉标题后的内容
            suffix = line[match.end():].strip()
            if suffix:
                sections[current_key].append(suffix)
            continue
        if current_key:
            sections[current_key].append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def extract_field(info: Dict[str, str], keys: List[str]) -> str:
    for key in keys:
        if key in info and info[key]:
            return info[key]
    return ""


def build_rows(profiles: List[Dict]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for profile in profiles:
        info = profile.get("basic_info", {}) or {}
        sections = parse_sections(profile.get("content_text", ""))
        rows.append(
            {
                "姓名": profile.get("name", ""),
                "职称": extract_field(info, ["职称"]),
                "职务": extract_field(info, ["职务"]),
                "电子邮箱": extract_field(info, ["电子邮箱", "邮箱"]),
                "办公地点": extract_field(info, ["办公地点", "办公室"]),
                "办公电话": extract_field(info, ["办公电话", "电话"]),
                "个人主页": extract_field(info, ["个人网页", "主页", "课题组主页"]),
                "研究方向": sections.get("研究方向", ""),
                "个人简介": sections.get("个人简介", "") or sections.get("教育经历", ""),
                "授课情况": sections.get("授课情况", ""),
                "招生专业": sections.get("招生专业", "") or sections.get("招生信息", ""),
                "代表性论文": sections.get("代表性论文和论著", ""),
                "其他信息": sections.get("科研项目", "")
                or sections.get("科研成果", "")
                or sections.get("承担项目", "")
                or sections.get("社会任职", ""),
                "详情链接": profile.get("detail_url", ""),
                "照片链接": profile.get("photo_url", ""),
            }
        )
    return rows


def write_csv(rows: List[Dict[str, str]], output_path: Path) -> None:
    if not rows:
        print("⚠️ 没有可写入的数据")
        return
    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ 已生成整理后的表格: {output_path}")


def main() -> None:
    base_dir = Path(__file__).parent
    json_path = base_dir / "output" / "faculty_directory.json"
    output_csv = base_dir / "output" / "faculty_directory_clean.csv"

    if not json_path.exists():
        raise SystemExit(f"❌ 未找到数据文件: {json_path}")

    profiles = load_profiles(json_path)
    rows = build_rows(profiles)
    write_csv(rows, output_csv)


if __name__ == "__main__":
    main()

