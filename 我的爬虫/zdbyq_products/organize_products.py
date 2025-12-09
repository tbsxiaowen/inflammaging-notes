#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据 products.json 生成结构化的产品资料，按“一级分类/二级分类/产品”目录输出，
并将内容整理为“产品标题、产品介绍、适用范围、产品说明、产品特点、主要参数、
执行标准、技术优势”八个板块。
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse


BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "output" / "products.json"
OUTPUT_DIR = BASE_DIR / "output" / "product_details"
RAW_DIR = BASE_DIR / "output" / "product_details_raw"

SECTIONS = [
    "产品标题",
    "产品介绍",
    "适用范围",
    "产品说明",
    "产品特点",
    "主要参数",
    "执行标准",
    "技术优势",
]
SECTION_LIMITS = {
    "产品介绍": 6,
    "适用范围": 5,
    "产品说明": 8,
    "产品特点": 8,
    "主要参数": 4,
    "执行标准": 4,
    "技术优势": 4,
}

NAV_TERMS = ["中电变压器", "您的位置", "产品中心", "在线咨询", "400", "干式变压器油浸变压器"]


def load_products() -> List[Dict]:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_raw_map() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    if not RAW_DIR.exists():
        return mapping
    for path in RAW_DIR.glob("*.txt"):
        content = path.read_text(encoding="utf-8", errors="ignore")
        match = re.search(r"^产品标题:\s*(.+)$", content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            mapping[title] = content
    return mapping


RAW_TEXT_MAP = load_raw_map()
IMG_PATTERN = re.compile(r"https?://\S+\.(?:jpg|jpeg|png|gif|webp|svg)", re.IGNORECASE)
BANNED_PREFIXES = [
    "图片链接",
    "咨询热线",
    "扫码拨打",
    "一键拨号",
    "欢迎咨询",
    "欢迎联系我们",
    "请使用IOS",
    "品牌:",
    "：>",
    ">>",
    "- _",
    "箱式变压器成套开关柜矿用变压器",
    "轨道矿山电网船用数据中心制氢风光储",
]
BANNED_PHRASES = [
    "欢迎咨询",
    "欢迎联系我们",
    "扫码拨打",
    "一键拨号",
    "了解更多",
    "客服热线",
    "联系我们",
    "咨询电话",
    "获取更多信息",
    "了解详情",
]


def split_sentences(text: str) -> List[str]:
    tokens = re.split(r"(?<=[。！？；;.!?])", text)
    sentences: List[str] = []
    buffer = ""
    for token in tokens:
        if not token:
            continue
        buffer += token
        if re.search(r"[。！？；;.!?]$", token):
            sentences.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        sentences.append(buffer.strip())
    return sentences


def should_drop(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    for prefix in BANNED_PREFIXES:
        if stripped.startswith(prefix):
            return True
    for phrase in BANNED_PHRASES:
        if phrase in stripped:
            return True
    return False


def clean_paragraph(text: str) -> str:
    text = IMG_PATTERN.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text or should_drop(text):
        return ""
    sentences = split_sentences(text) or [text]
    merged: List[str] = []
    skip_next = False
    for idx, sentence in enumerate(sentences):
        if skip_next:
            skip_next = False
            continue
        stripped = sentence.strip()
        if not stripped:
            continue
        match_num_only = re.match(r"^(\d+)[\.\)]$", stripped)
        if match_num_only and idx + 1 < len(sentences):
            combined = f"{match_num_only.group(1)}. {sentences[idx + 1].strip()}"
            merged.append(combined)
            skip_next = True
            continue
        merged.append(stripped)

    cleaned: List[str] = []
    for sentence in merged:
        sentence = sentence.strip(" -")
        if not sentence or should_drop(sentence):
            continue
        cleaned.append(sentence)
    return "\n".join(cleaned).strip()


def sentence_signature(text: str) -> str:
    return re.sub(r"[\s，,。．.、/:：；;（）()\\-–_•·【】\"“”‘’]+", "", text.lower())


def is_similar(existing: str, candidate: str, threshold: float = 0.9) -> bool:
    if not existing or not candidate:
        return False
    return SequenceMatcher(None, existing, candidate).ratio() >= threshold


def classify_product(title: str, url: str) -> Tuple[str, str, str]:
    """返回 (一级分类, 二级分类, 分组名称)"""
    path_prefix = urlparse(url).path.split("/", 2)[1]
    clean_title = title.split(" - ")[0]

    def scb_group():
        if any(k in clean_title for k in ["整流", "ZPSG", "牵引"]):
            return "干式整流变压器"
        if "储能" in clean_title:
            return "储能干式变压器"
        if any(k in clean_title for k in ["隔离", "三相"]):
            return "隔离干式变压器"
        return "SCB干式变压器"

    if path_prefix in {"pro-gsb", "pro-sgsb"}:
        return ("干式变压器", "SCB 干式变压器", scb_group())
    if path_prefix == "pro-fjhj":
        return ("干式变压器", "非晶合金变压器", "非晶合金干式变压器")
    if path_prefix == "pro-yjb":
        if any(k in clean_title for k in ["牵引", "车载", "海洋", "船用", "氢能"]):
            return ("油浸变压器", "特种油浸变压器", "特种油浸式变压器")
        if any(k in clean_title for k in ["耐高温", "液浸", "全铝"]):
            return ("油浸变压器", "耐高温及液浸系列", "耐高温油浸式变压器")
        return ("油浸变压器", "油浸式电力变压器", "油浸式电力变压器")
    if path_prefix == "pro-kyb":
        if "配电" in clean_title or "装置" in clean_title:
            return ("矿用变压器", "矿用配电装置", "矿用配电及保护装置")
        return ("矿用变压器", "矿用隔爆干式变压器", "矿用隔爆干式变压器")
    if path_prefix == "pro-xsb":
        if "储能变流升压" in clean_title:
            return ("pcs储能升压一体机", "储能变流升压一体机", "储能变流升压一体机")
        if "美式" in clean_title:
            return ("箱式变压器", "美式箱式变电站", "美式箱式变电站")
        if "欧式" in clean_title:
            return ("箱式变压器", "欧式箱式变电站", "欧式箱式变电站")
        if any(k in clean_title for k in ["模块化", "预制舱", "华式", "新能源", "风力", "光伏", "非晶"]):
            return ("箱式变压器", "模块化/新能源箱变", "模块化箱式变电站")
        return ("箱式变压器", "通用箱式变压器", "箱式变电站")
    if path_prefix == "pro-ctg":
        if "矿用" in clean_title:
            return ("矿用变压器", "矿用配电装置", "矿用配电及保护装置")
        if "GGD" in clean_title:
            return ("成套开关柜", "GGD低压配电柜", "GGD低压配电柜")
        if "MNS" in clean_title:
            return ("成套开关柜", "MNS抽出式开关柜", "MNS抽出式开关柜")
        if "GCS" in clean_title:
            return ("成套开关柜", "GCS低压抽出式开关柜", "GCS低压抽出式开关柜")
        if "GCK" in clean_title:
            return ("成套开关柜", "GCK低压开关设备", "GCK低压抽出式开关柜")
        return ("成套开关柜", "矿用/高压配电装置", "矿用配电及保护装置")
    if path_prefix == "pro-tzb":
        if "保护箱" in clean_title or "配电装置" in clean_title:
            return ("成套开关柜", "矿用防爆装置", "矿用配电及保护装置")
        return ("油浸变压器", "特种油浸变压器", "特种油浸式变压器")
    if path_prefix == "pro-wlw":
        if "温度" in clean_title:
            return ("智能变压器终端", "温度监测终端", "温度监测终端")
        if "监测" in clean_title:
            return ("智能变压器终端", "在线监测终端", "在线监测终端")
        if "除湿" in clean_title or "控制器" in clean_title or "母线槽" in clean_title:
            return ("智能变压器终端", "智能辅件", "智能辅件及控制终端")
        return ("智能变压器终端", "物联网终端", "物联网智能终端")
    if path_prefix == "pro-zndy":
        if "不间断" in clean_title or "UPS" in clean_title.upper():
            return ("智能一体化电源", "UPS一体化电源", "UPS一体化电源")
        return ("智能一体化电源", "智能一体化电源系统", "智能一体化电源系统")
    if path_prefix == "pro-cnj":
        return ("工商业储能系统", "工商业储能一体机", "工商业储能一体机")
    if path_prefix == "pro-gscn":
        return ("pcs储能升压一体机", "储能变流升压一体机", "储能变流升压一体机")

    # 默认回退
    return ("其他", "其他", clean_title or "未命名产品")


def extract_sections_from_raw(raw_text: str) -> Dict[str, List[str]]:
    sections = {name: [] for name in SECTIONS}
    if not raw_text:
        return sections

    body = raw_text.split("详细内容:", 1)
    text = body[1] if len(body) > 1 else raw_text
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for term in NAV_TERMS:
        text = text.replace(term, "")

    pattern = re.compile(r"(产品介绍|适用范围|产品说明|产品特点|主要参数|执行标准|技术优势)[：:]")
    matches = list(pattern.finditer(text))
    if not matches:
        cleaned = [line.strip() for line in text.split("\n") if line.strip()]
        if cleaned:
            sections["产品介绍"] = cleaned
        return sections

    for idx, match in enumerate(matches):
        section_name = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            paragraphs = [p.strip() for p in re.split(r"\n+", content) if p.strip()]
            sections[section_name].extend(paragraphs)
    return sections


def build_sections(records: List[Dict], group_name: str) -> Dict[str, List[str]]:
    sections = {name: [] for name in SECTIONS}
    section_seen: Dict[str, set] = {name: set() for name in SECTIONS}
    section_prefix_seen: Dict[str, set] = {name: set() for name in SECTIONS}
    models: List[str] = []

    for record in records:
        title_full = record.get("title", "")
        title = title_full.split(" - ")[0]
        if title:
            model = title.split("_")[0]
            if model not in models:
                models.append(model)

        raw_sections = extract_sections_from_raw(RAW_TEXT_MAP.get(title_full, ""))
        for key in SECTIONS:
            if key == "产品标题":
                continue
            for paragraph in raw_sections.get(key, []):
                cleaned = clean_paragraph(paragraph)
                if not cleaned:
                    continue
                for sentence in cleaned.split("\n"):
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    signature = sentence_signature(sentence)
                    if signature in section_seen[key]:
                        continue
                    prefix = sentence[:40]
                    if prefix in section_prefix_seen[key]:
                        continue
                    if any(is_similar(existing, sentence, 0.78) for existing in sections[key]):
                        continue
                    section_seen[key].add(signature)
                    section_prefix_seen[key].add(prefix)
                    sections[key].append(sentence)

    if models:
        sections["产品介绍"].insert(0, f"涵盖型号：{', '.join(models)}")

    sections["产品标题"] = [group_name]

    for key in SECTIONS:
        if not sections[key]:
            sections[key] = ["暂无信息"]
        limit = SECTION_LIMITS.get(key)
        if limit and len(sections[key]) > limit:
            sections[key] = sections[key][:limit]
    return sections


def write_group_file(category: str, subcategory: str, group_name: str, sections: Dict[str, List[str]]):
    target_dir = OUTPUT_DIR / category / subcategory
    target_dir.mkdir(parents=True, exist_ok=True)
    file_path = target_dir / f"{group_name}.md"

    lines: List[str] = []
    for section in SECTIONS:
        lines.append(f"## {section}")
        for paragraph in sections[section]:
            chunks = [chunk.strip() for chunk in paragraph.split("\n") if chunk.strip()]
            if not chunks:
                continue
            lines.extend(chunks)
            lines.append("")

    file_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main():
    products = load_products()
    grouped: Dict[Tuple[str, str, str], List[Dict]] = defaultdict(list)

    for product in products:
        category, subcategory, group_name = classify_product(product.get("title", ""), product.get("url", ""))
        grouped[(category, subcategory, group_name)].append(product)

    for (category, subcategory, group_name), records in grouped.items():
        sections = build_sections(records, group_name)
        write_group_file(category, subcategory, group_name, sections)

    print(f"✅ 已重新整理 {len(grouped)} 个产品分组，输出目录：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()

