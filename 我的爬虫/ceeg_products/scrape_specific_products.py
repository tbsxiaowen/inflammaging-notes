#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中电电气产品爬虫 - 爬取指定产品并生成单独的txt文档
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse, urlunparse, unquote

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    raise SystemExit("❌ 缺少依赖，请先运行: pip install requests beautifulsoup4 lxml")

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    print("⚠️  未安装Playwright，将使用requests（可能无法获取动态内容）")

BASE_URL = "https://www.ceeg.cn"
BASE_URL_PARSED = urlparse(BASE_URL)

# 需要爬取的分类页面和对应的产品名称
CATEGORY_CONFIG = {
    "智能硬件": {
        "category_url": "https://www.ceeg.cn/cn/categories/rx-zhi-neng-ying-jian",
        "products": [
            "TAT600-3KR智能型 干式变压器温控器非标定制款",
            "TAT602智能型 干式变压器温控器标准版",
            "无线测温在线监测装置",
            "10寸综合在线监测接收装置无线温度监测系统",
            "智能除湿装置",
            "TAT603智能型 干式变压器温控器标准版",
        ]
    },
    "智能一体化电源": {
        "category_url": "https://www.ceeg.cn/cn/archives/idczhi-neng-yi-ti-hua-dian-li-mo-zu-dian-jing-bi-fang1",
        "products": [
            "IDC智能一体化电力模组电靓毕方",
        ]
    },
    "工商业储能系统": {
        "category_url": "https://www.ceeg.cn/cn/categories/rx-gong-shang-ye-chu-neng",
        "products": [
            "储能升压变流一体机",
            "1000kWh工商业储能系统",
            "372kWh液冷储能系统",
            "215kWh风冷储能系统",
            "200kWh风冷储能系统",
            "100kWh风冷储能系统",
            "工商业储能PCS",
        ]
    }
}

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def create_session():
    """创建带重试机制的会话"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    return session


def normalize_url(base_url: str, href: str) -> str:
    """规范化url，移除片段并补全域名"""
    if not href or href.startswith("javascript") or href.startswith("#"):
        return ""
    clean_href = href.split("#", 1)[0].strip()
    full_url = urljoin(base_url, clean_href)
    parsed = urlparse(full_url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme=BASE_URL_PARSED.scheme)
    if not parsed.netloc:
        parsed = parsed._replace(netloc=BASE_URL_PARSED.netloc)
    return urlunparse(parsed)


def is_same_domain(url: str) -> bool:
    """判断URL是否属于目标域名"""
    parsed = urlparse(url)
    return parsed.netloc == BASE_URL_PARSED.netloc


def get_all_product_links_from_category(session, category_url: str) -> Set[str]:
    """从分类页面获取所有产品链接"""
    product_links: Set[str] = set()
    visited: Set[str] = {category_url}
    to_visit: Set[str] = {category_url}
    
    print(f"📥 正在获取分类页面: {category_url}")
    
    while to_visit:
        page_url = to_visit.pop()
        
        try:
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
        except Exception as exc:
            print(f"❌ 页面获取失败 {page_url}: {exc}")
            continue
        
        soup = BeautifulSoup(response.text, "lxml")
        
        # 查找产品链接 - 这个网站的产品详情页在 /cn/archives/ 路径下
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if not href:
                continue
            full_url = normalize_url(page_url, href)
            if not is_same_domain(full_url):
                continue
            parsed = urlparse(full_url)
            path = parsed.path
            
            # 产品详情页在 /cn/archives/ 路径下
            if path.startswith("/cn/archives/") and path != "/cn/archives/":
                product_links.add(full_url)
        
        # 查找分页链接
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if not href or 'page=' not in href:
                continue
            full_url = normalize_url(page_url, href)
            if is_same_domain(full_url) and full_url not in visited:
                parsed_current = urlparse(page_url)
                parsed_new = urlparse(full_url)
                if parsed_current.path == parsed_new.path:
                    to_visit.add(full_url)
                    visited.add(full_url)
    
    return product_links


def match_product_by_name(session, product_url: str, target_name: str) -> bool:
    """检查产品URL是否匹配目标产品名称"""
    try:
        response = session.get(product_url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or "utf-8"
        soup = BeautifulSoup(response.text, "lxml")
        
        # 获取产品标题
        title = ""
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.get_text(strip=True)
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                if ' - ' in title:
                    title = title.split(' - ')[0].strip()
        
        if not title:
            return False
        
        # 精确匹配
        if target_name in title or title in target_name:
            return True
        
        # 关键词匹配
        name_keywords = [kw for kw in target_name.split() if len(kw) > 1]
        name_keywords = [kw for kw in name_keywords if kw not in ['的', '和', '与', '型', '版', '系统', '装置']]
        
        if len(name_keywords) >= 2:
            matched_keywords = sum(1 for kw in name_keywords if kw in title)
            if matched_keywords >= min(2, len(name_keywords)):
                return True
        
        # 型号匹配（如TAT600-3KR, 1000kWh等）
        if '-' in target_name or any(char.isdigit() for char in target_name):
            model_patterns = re.findall(r'[A-Z]+\d+[-\dA-Z]*|\d+[kK]?[WwHh]', target_name)
            if model_patterns:
                for pattern in model_patterns:
                    if pattern in title:
                        return True
        
        return False
        
    except Exception as exc:
        print(f"⚠️  检查产品失败 {product_url}: {exc}")
        return False


def extract_product_details_from_html(html_content: str, url: str, category_name: str = '') -> Dict:
    """从产品详情页提取产品信息（复用原有逻辑）"""
    product_info = {
        'url': url,
        'title': '',
        'category': category_name,
        'description': '',
        'content': '',
        'specifications': {},
        'images': [],
    }
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取标题
        title_tag = soup.find('h1')
        if title_tag:
            product_info['title'] = title_tag.get_text(strip=True)
        
        if not product_info['title']:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if ' - ' in title_text:
                    product_info['title'] = title_text.split(' - ')[0].strip()
                elif ' · ' in title_text:
                    product_info['title'] = title_text.split(' · ')[0].strip()
                else:
                    product_info['title'] = title_text
        
        # 提取描述
        desc_selectors = [
            '.product-description',
            '.description',
            '.product-intro',
            '.intro',
            'meta[name="description"]',
        ]
        for selector in desc_selectors:
            if selector.startswith('meta'):
                meta = soup.find('meta', attrs={'name': 'description'})
                if meta:
                    product_info['description'] = meta.get('content', '')
                    break
            else:
                desc_tag = soup.select_one(selector)
                if desc_tag:
                    product_info['description'] = desc_tag.get_text(strip=True)
                    break
        
        # 提取主要内容（复用原有逻辑）
        unwanted_keywords = [
            '为世界输出优质动力', '资料中心', '24小时服务热线', '关于中电', '中电概況',
            '中电荣誉', '发展历程', '数说中电', '合作伙伴', '新闻资讯', '全球足迹',
            '经典项目', '企业文化', '社会责任', '经营发展', '加入中电', '热销产品',
            '变压器', '一体化电源', '储能系统', '电力物联网', '解决方案', '定制解决方案',
            '产品解决方案', '行业解决方案', '联系我们', '地址：', '邮箱：', '产品咨询热线',
            '销售对接微信', '版权所有', '苏ICP备', '法律条款', '点击咨询', '下载产品手册',
            '电话咨询', '400-080-0008', 'WHO NEEDS HELP', 'Project Consultation', '项目咨询',
            'Customerservice consultation', '客服咨询', '我要咨询', '获得支持', '如果您有想要购买的产品',
            '我们的客服团队', '我们的团队非常愿意为您提供帮助', '注：上述参数提供的尺寸',
            '如需其他型号参数以及容量定制', '可拨打热线', '微信同号', '18013345718',
        ]
        
        main_content_div = None
        body = soup.find('body')
        if body:
            content_keywords = ['产品介绍', '规格参数', '选型产品', '空载低耗', '先进工艺', 
                              '三维设计', '高压绕组', '产品业绩']
            for keyword in content_keywords:
                elements = body.find_all(string=lambda text: text and keyword in str(text))
                if elements:
                    for elem in elements:
                        parent = elem.parent
                        while parent and parent.name != 'body':
                            if parent.name == 'div':
                                text = parent.get_text(strip=True)
                                if len(text) > 1000:
                                    main_content_div = parent
                                    break
                            parent = parent.parent
                        if main_content_div:
                            break
                if main_content_div:
                    break
        
        if main_content_div:
            for elem in main_content_div(["script", "style", "nav", "header", "footer", "aside", "form"]):
                elem.decompose()
            
            content_parts = []
            
            # 1. 提取所有 text-[14px] text-[#09131e] 的内容（更全面的提取）
            text_14px_divs = main_content_div.find_all('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
            for div in text_14px_divs:
                text = div.get_text(strip=True)
                if text and len(text) > 10:  # 降低长度限制，提取更多内容
                    # 排除明显的参数表格内容
                    if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸', '额定电压', '联结组别']):
                        if text not in content_parts:
                            content_parts.append(text)
            
            # 2. 提取所有 text-[14px] 的内容（不限制颜色）
            text_14px_all = main_content_div.find_all('div', class_=lambda x: x and 'text-[14px]' in str(x))
            for div in text_14px_all:
                text = div.get_text(strip=True)
                if text and len(text) > 10:
                    if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸', '额定电压', '联结组别']):
                        if text not in content_parts:
                            content_parts.append(text)
            
            # 3. 提取所有 text-[16px] 的内容
            text_16px_divs = main_content_div.find_all('div', class_=lambda x: x and 'text-[16px]' in str(x))
            for div in text_16px_divs:
                text = div.get_text(strip=True)
                if text and len(text) > 10:
                    if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸']):
                        if text not in content_parts:
                            content_parts.append(text)
            
            # 4. 提取 item flex flex-col justify-center items-center 的内容（更全面的提取）
            # 先查找包含这些item的容器（如tab1, product1等）
            containers = main_content_div.find_all('div', class_=lambda x: x and ('tab1' in str(x) or 'product1' in str(x) or 'bg-gradient-to-b' in str(x)))
            for container in containers:
                item_divs = container.find_all('div', class_=lambda x: x and 'item' in str(x) and 'flex' in str(x) and 'flex-col' in str(x))
                for item in item_divs:
                    # 提取结构化的标题和描述
                    title_elem = item.find('div', class_=lambda x: x and 'text-[24px]' in str(x))
                    desc_elem = item.find('div', class_=lambda x: x and 'text-[16px]' in str(x))
                    
                    if title_elem:
                        title_text = title_elem.get_text(strip=True)
                        if title_text:
                            # 如果有描述，组合标题和描述
                            if desc_elem:
                                desc_text = desc_elem.get_text(strip=True)
                                if desc_text:
                                    combined = f'{title_text}\n{desc_text}'
                                    if combined not in content_parts:
                                        content_parts.append(combined)
                                else:
                                    # 描述为空，只添加标题
                                    if title_text not in content_parts:
                                        content_parts.append(title_text)
                            else:
                                # 没有描述元素，只添加标题
                                if title_text not in content_parts:
                                    content_parts.append(title_text)
                    
                    # 特别提取 text-[14px] text-[#09131e] 的内容（在item内部或后面）
                    text_14px_elem = item.find('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                    if text_14px_elem:
                        text_14px = text_14px_elem.get_text(strip=True)
                        if text_14px and len(text_14px) > 20:
                            if text_14px not in content_parts:
                                content_parts.append(text_14px)
                    
                    # 也检查item后面的兄弟元素
                    next_sibling = item.find_next_sibling('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                    if next_sibling:
                        next_text = next_sibling.get_text(strip=True)
                        if next_text and len(next_text) > 20:
                            if next_text not in content_parts:
                                content_parts.append(next_text)
            
            # 也直接查找所有 item flex flex-col justify-center items-center
            item_divs = main_content_div.find_all('div', class_=lambda x: x and 'item' in str(x) and 'flex' in str(x) and 'flex-col' in str(x) and 'justify-center' in str(x) and 'items-center' in str(x))
            for item in item_divs:
                # 提取结构化的标题和描述
                title_elem = item.find('div', class_=lambda x: x and 'text-[24px]' in str(x))
                desc_elem = item.find('div', class_=lambda x: x and 'text-[16px]' in str(x))
                
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    if title_text:
                        # 如果有描述，组合标题和描述
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if desc_text:
                                combined = f'{title_text}\n{desc_text}'
                                if combined not in content_parts:
                                    content_parts.append(combined)
                            else:
                                # 描述为空，只添加标题
                                if title_text not in content_parts:
                                    content_parts.append(title_text)
                        else:
                            # 没有描述元素，只添加标题
                            if title_text not in content_parts:
                                content_parts.append(title_text)
                
                # 特别提取 text-[14px] text-[#09131e] 的内容
                text_14px_elem = item.find('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                if text_14px_elem:
                    text_14px = text_14px_elem.get_text(strip=True)
                    if text_14px and len(text_14px) > 20:
                        if text_14px not in content_parts:
                            content_parts.append(text_14px)
            
            # 5. 提取所有包含 item 和 flex 的div（更宽泛的匹配）
            all_item_divs = main_content_div.find_all('div', class_=lambda x: x and 'item' in str(x) and 'flex' in str(x))
            for item in all_item_divs:
                # 跳过已经处理过的
                if 'flex-col' in str(item.get('class', [])):
                    continue
                
                item_text = item.get_text(separator='\n', strip=True)
                if item_text and len(item_text) > 20:
                    # 查找标题和描述
                    title_elem = item.find(['div', 'h2', 'h3', 'h4'], class_=lambda x: x and any(size in str(x) for size in ['text-[24px]', 'text-[20px]', 'text-[18px]', 'text-[16px]']))
                    if title_elem:
                        title_text = title_elem.get_text(strip=True)
                        # 查找描述（在标题后面的div）
                        desc_elem = title_elem.find_next('div', class_=lambda x: x and ('text-[16px]' in str(x) or 'text-[14px]' in str(x)))
                        if desc_elem:
                            desc_text = desc_elem.get_text(strip=True)
                            if title_text and desc_text:
                                combined = f'{title_text}\n{desc_text}'
                                if combined not in content_parts:
                                    content_parts.append(combined)
                        else:
                            # 只有标题
                            if title_text not in content_parts and len(title_text) > 5:
                                content_parts.append(title_text)
            
            # 6. 提取标签
            tags_divs = main_content_div.find_all('div', class_=lambda x: x and 'tags' in str(x).lower())
            for tags_div in tags_divs:
                tag_items = tags_div.find_all('div', class_=lambda x: x and ('px-' in str(x) or 'py-' in str(x)))
                if tag_items:
                    tags = [item.get_text(strip=True) for item in tag_items if item.get_text(strip=True)]
                    if tags:
                        content_parts.append('标签: ' + '、'.join(tags))
            
            # 7. 提取技术说明（product2-item）
            tech_sections = main_content_div.find_all('div', class_=lambda x: x and 'product2-item' in str(x).lower())
            for section in tech_sections:
                title = section.find('div', class_=lambda x: x and 'title' in str(x).lower() and 'text-[58px]' in str(x))
                desc = section.find('div', class_=lambda x: x and 'text-[20px]' in str(x))
                if title and desc:
                    title_text = title.get_text(strip=True)
                    desc_text = desc.get_text(strip=True)
                    if title_text and desc_text:
                        content_parts.append(f'{title_text}\n{desc_text}')
                else:
                    # 如果没有找到结构化内容，提取整个section的文本
                    section_text = section.get_text(separator='\n', strip=True)
                    if section_text and len(section_text) > 20:
                        if section_text not in content_parts:
                            content_parts.append(section_text)
            
            # 8. 提取产品业绩
            performance_section = main_content_div.find('div', class_=lambda x: x and 'performance' in str(x).lower())
            if performance_section:
                performance_items = performance_section.find_all('div', class_=lambda x: x and 'flex' in str(x).lower())
                if performance_items:
                    performances = [item.get_text(strip=True) for item in performance_items if item.get_text(strip=True)]
                    if performances:
                        content_parts.append('产品业绩\n' + '\n'.join(performances))
            
            # 9. 提取所有包含重要关键词的段落和div
            important_keywords = ['产品介绍', '产品特点', '产品优势', '技术特点', '技术优势', '应用场景', '适用范围', 
                                 '三维设计', '高压绕组', '低压绕组', '铁心', '试验与检测', '产品业绩', '绝缘', 
                                 '智能', '高效', '节能', '安全', '可靠', '模块化', '定制']
            for keyword in important_keywords:
                # 查找包含关键词的文本节点
                keyword_elements = main_content_div.find_all(string=lambda text: text and keyword in str(text))
                for elem in keyword_elements:
                    parent = elem.parent
                    if parent and parent.name in ['div', 'p', 'section']:
                        # 获取父元素的完整文本
                        parent_text = parent.get_text(separator='\n', strip=True)
                        if parent_text and len(parent_text) > 20:
                            # 检查是否包含参数表格关键词
                            if not any(kw in parent_text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB']):
                                if parent_text not in content_parts:
                                    content_parts.append(parent_text)
            
            # 过滤技术参数相关内容和不想要的内容（更宽松的过滤）
            filtered_parts = []
            param_keywords = ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸',
                             '额定电压', '联结组别', '分接范围', '注：上述参数', 'SC(B)', 'SC10-', 'SC11-', 'SC12-', 'SC13-', 'SC14-', 'SC18-']
            
            for part in content_parts:
                # 过滤不想要的关键词（更严格的检查）
                # 如果内容主要是这些不需要的关键词，则跳过
                part_lower = part.lower()
                unwanted_count = sum(1 for kw in unwanted_keywords if kw in part)
                # 如果内容很短且包含不需要的关键词，跳过
                if len(part) < 50 and unwanted_count > 0:
                    continue
                # 如果内容较长但主要是不需要的内容，跳过
                if len(part) >= 50 and unwanted_count >= 2 and len(part) < 100:
                    continue
                
                # 只过滤明显是参数表格的内容（包含多个参数关键词）
                param_count = sum(1 for kw in param_keywords if kw in part)
                if param_count >= 3:  # 只有包含3个或以上参数关键词才过滤
                    continue
                # 更宽松的数字+单位检查
                if len(part.split()) > 15 and any(char.isdigit() for char in part) and ('kV' in part or 'mm' in part or 'W' in part):
                    if len(re.findall(r'\d+[kK]?[VvWw]|mm|%', part)) > 5:  # 提高阈值
                        continue
                filtered_parts.append(part)
            
            # 去重（更智能的去重，保留更多内容）
            seen = set()
            unique_parts = []
            for part in filtered_parts:
                if len(part.strip()) < 5:  # 降低最小长度要求
                    continue
                
                # 检查是否是完全重复
                if part in seen:
                    continue
                
                # 检查是否被其他内容包含（但允许部分重叠）
                is_duplicate = False
                is_superset = False
                for existing in list(seen):
                    if part == existing:
                        is_duplicate = True
                        break
                    # 如果新内容是现有内容的子集，跳过
                    if part in existing and len(part) < len(existing) * 0.8:
                        is_duplicate = True
                        break
                    # 如果新内容包含现有内容，替换现有内容
                    if existing in part and len(existing) < len(part) * 0.8:
                        if existing in unique_parts:
                            unique_parts.remove(existing)
                            seen.remove(existing)
                        is_superset = True
                        break
                
                if not is_duplicate:
                    seen.add(part)
                    unique_parts.append(part)
            
            product_info['content'] = '\n\n'.join(unique_parts)
        
        # 如果还没有内容或内容太少，尝试从body直接提取特定class的内容
        if not product_info['content'] or len(product_info['content']) < 200:
            body = soup.find('body')
            if body:
                content_parts = []
                
                # 1. 查找包含item的容器（tab1, product1, bg-gradient-to-b等）
                containers = body.find_all('div', class_=lambda x: x and ('tab1' in str(x) or 'product1' in str(x) or 'bg-gradient-to-b' in str(x)))
                for container in containers:
                    # 提取容器内的所有item
                    item_divs = container.find_all('div', class_=lambda x: x and 'item' in str(x) and 'flex' in str(x) and 'flex-col' in str(x))
                    for item in item_divs:
                        # 提取标题和描述
                        title_elem = item.find('div', class_=lambda x: x and 'text-[24px]' in str(x))
                        desc_elem = item.find('div', class_=lambda x: x and 'text-[16px]' in str(x))
                        
                        if title_elem:
                            title_text = title_elem.get_text(strip=True)
                            if title_text:
                                # 如果有描述，组合标题和描述
                                if desc_elem:
                                    desc_text = desc_elem.get_text(strip=True)
                                    if desc_text:
                                        combined = f'{title_text}\n{desc_text}'
                                        if combined not in content_parts:
                                            content_parts.append(combined)
                                    else:
                                        # 描述为空，只添加标题
                                        if title_text not in content_parts:
                                            content_parts.append(title_text)
                                else:
                                    # 没有描述元素，只添加标题
                                    if title_text not in content_parts:
                                        content_parts.append(title_text)
                        
                        # 提取 text-[14px] text-[#09131e]
                        text_14px_elem = item.find('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                        if text_14px_elem:
                            text_14px = text_14px_elem.get_text(strip=True)
                            if text_14px and len(text_14px) > 20:
                                if text_14px not in content_parts:
                                    content_parts.append(text_14px)
                    
                    # 也查找容器内的 text-[14px] text-[#09131e]（可能在item外面）
                    container_text_14px = container.find_all('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                    for div in container_text_14px:
                        text = div.get_text(strip=True)
                        if text and len(text) > 20:
                            if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB']):
                                if text not in content_parts:
                                    content_parts.append(text)
                
                # 2. 提取所有 text-[14px] text-[#09131e] 的内容（从整个body）
                text_14px_divs = body.find_all('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                for div in text_14px_divs:
                    text = div.get_text(strip=True)
                    if text and len(text) > 20:  # 提高最小长度要求
                        if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB']):
                            if text not in content_parts:
                                content_parts.append(text)
                
                # 3. 提取所有 item flex flex-col justify-center items-center 的内容
                item_divs = body.find_all('div', class_=lambda x: x and 'item' in str(x) and 'flex' in str(x) and 'flex-col' in str(x) and 'justify-center' in str(x) and 'items-center' in str(x))
                for item in item_divs:
                    title_elem = item.find('div', class_=lambda x: x and 'text-[24px]' in str(x))
                    desc_elem = item.find('div', class_=lambda x: x and 'text-[16px]' in str(x))
                    
                    if title_elem:
                        title_text = title_elem.get_text(strip=True)
                        if title_text:
                            # 如果有描述，组合标题和描述
                            if desc_elem:
                                desc_text = desc_elem.get_text(strip=True)
                                if desc_text:
                                    combined = f'{title_text}\n{desc_text}'
                                    if combined not in content_parts:
                                        content_parts.append(combined)
                                else:
                                    # 描述为空，只添加标题
                                    if title_text not in content_parts:
                                        content_parts.append(title_text)
                            else:
                                # 没有描述元素，只添加标题
                                if title_text not in content_parts:
                                    content_parts.append(title_text)
                    
                    # 提取item内的 text-[14px] text-[#09131e]
                    text_14px_elem = item.find('div', class_=lambda x: x and 'text-[14px]' in str(x) and 'text-[#09131e]' in str(x))
                    if text_14px_elem:
                        text_14px = text_14px_elem.get_text(strip=True)
                        if text_14px and len(text_14px) > 20:
                            if text_14px not in content_parts:
                                content_parts.append(text_14px)
                
                # 4. 提取所有 text-[16px] 的内容
                text_16px_divs = body.find_all('div', class_=lambda x: x and 'text-[16px]' in str(x))
                for div in text_16px_divs:
                    text = div.get_text(strip=True)
                    if text and len(text) > 10:
                        if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损']):
                            if text not in content_parts:
                                content_parts.append(text)
                
                if content_parts:
                    # 合并到现有内容或替换
                    if product_info['content']:
                        product_info['content'] = product_info['content'] + '\n\n' + '\n\n'.join(content_parts)
                    else:
                        product_info['content'] = '\n\n'.join(content_parts)
        
        # 如果还是没有内容，尝试其他方式提取
        if not product_info['content']:
            article = soup.find('article') or soup.find('main')
            if article:
                for elem in article(["script", "style", "nav", "header", "footer", "aside", "form"]):
                    elem.decompose()
                content_sections = []
                for tag in article.find_all(['p', 'div', 'li', 'h2', 'h3', 'h4', 'section']):
                    text = tag.get_text(strip=True)
                    if not text or len(text) < 10:
                        continue
                    if any(keyword in text for keyword in unwanted_keywords[:15]):
                        continue
                    if len(text) < 20 and any(nav in text for nav in ['首页', '关于', '产品', '新闻', '联系我们']):
                        continue
                    content_sections.append(text)
                if content_sections:
                    product_info['content'] = '\n\n'.join(content_sections)
        
        # 提取图片
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = img.get('src', '')
            if src:
                full_img_url = normalize_url(url, src)
                if is_same_domain(full_img_url) or 'ceeg.cn' in full_img_url:
                    product_info['images'].append(full_img_url)
        
    except Exception as e:
        print(f"⚠️  提取产品信息时出错: {e}")
    
    return product_info


def get_product_details_with_playwright(url: str, category_name: str = '') -> Optional[Dict]:
    """使用Playwright获取产品详情"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            page.goto(url, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(2000)
            html_content = page.content()
            browser.close()
            return extract_product_details_from_html(html_content, url, category_name)
    except Exception as e:
        print(f"⚠️  Playwright获取失败: {e}")
        return None


def get_product_details(session, url: str, category_name: str = '', delay: float = 0.5, use_playwright: bool = True) -> Optional[Dict]:
    """获取单个产品详情页内容"""
    print(f"📄 正在获取: {url}")
    
    if use_playwright and HAS_PLAYWRIGHT:
        product_info = get_product_details_with_playwright(url, category_name)
        if product_info:
            if product_info.get('title'):
                print(f"✅ 成功获取: {product_info['title']}")
            else:
                print(f"✅ 成功获取: {url}")
            return product_info
    
    try:
        time.sleep(delay)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        product_info = extract_product_details_from_html(response.text, url, category_name)
        if product_info.get('title'):
            print(f"✅ 成功获取: {product_info['title']}")
        else:
            print(f"✅ 成功获取: {url}")
        return product_info
    except Exception as e:
        print(f"❌ 获取产品详情失败 {url}: {e}")
        return None


def save_to_txt(products: List[Dict], output_path: Path):
    """保存产品数据为TXT格式"""
    with open(output_path, 'w', encoding='utf-8') as f:
        # 按分类分组
        categories = {}
        for product in products:
            category = product.get('category', '其他')
            if category not in categories:
                categories[category] = []
            categories[category].append(product)
        
        # 写入内容
        for category, cat_products in categories.items():
            f.write(f"\n{'='*80}\n")
            f.write(f"分类: {category}\n")
            f.write(f"{'='*80}\n\n")
            
            for i, product in enumerate(cat_products, 1):
                f.write(f"\n{'-'*80}\n")
                f.write(f"产品 {i}: {product.get('title', '未知标题')}\n")
                f.write(f"{'-'*80}\n")
                f.write(f"URL: {product.get('url', '')}\n\n")
                
                if product.get('description'):
                    desc = product.get('description', '').strip()
                    if desc and len(desc) > 20:
                        f.write(f"产品介绍:\n{desc}\n\n")
                
                if product.get('content'):
                    content = product.get('content', '').strip()
                    if content:
                        f.write(f"产品详情:\n{content}\n\n")
        
        f.write(f"\n{'='*80}\n")
        f.write(f"总计: {len(products)} 个产品\n")
        f.write(f"{'='*80}\n")


def main():
    """主函数"""
    print("🚀 开始爬取指定产品...")
    
    session = create_session()
    all_products = []
    
    # 处理每个分类
    for category_name, config in CATEGORY_CONFIG.items():
        print(f"\n{'='*60}")
        print(f"📂 处理分类: {category_name}")
        print(f"{'='*60}\n")
        
        category_url = config['category_url']
        target_products = config['products']
        
        # 检查是否是直接的产品URL
        if category_url.startswith("https://www.ceeg.cn/cn/archives/"):
            # 这是直接的产品URL，直接爬取
            print(f"📄 直接爬取产品URL: {category_url}")
            product_info = get_product_details(session, category_url, category_name, delay=0.5)
            if product_info:
                # 检查是否匹配目标产品名称
                for target_name in target_products:
                    if match_product_by_name(session, category_url, target_name):
                        product_info['category'] = category_name
                        all_products.append(product_info)
                        print(f"✅ 匹配产品: {target_name}")
                        break
        else:
            # 这是分类页面，需要先获取所有产品链接，然后匹配
            print(f"📥 从分类页面获取产品链接: {category_url}")
            all_product_links = get_all_product_links_from_category(session, category_url)
            print(f"✅ 找到 {len(all_product_links)} 个产品链接")
            
            # 匹配目标产品
            matched_urls = {}
            for target_name in target_products:
                print(f"\n🔍 搜索产品: {target_name}")
                found = False
                for product_url in all_product_links:
                    if match_product_by_name(session, product_url, target_name):
                        matched_urls[target_name] = product_url
                        print(f"✅ 找到: {target_name} -> {product_url}")
                        found = True
                        break
                if not found:
                    print(f"⚠️  未找到: {target_name}")
            
            # 爬取匹配的产品
            for target_name, product_url in matched_urls.items():
                product_info = get_product_details(session, product_url, category_name, delay=0.5)
                if product_info:
                    all_products.append(product_info)
    
    # 保存数据
    if all_products:
        print(f"\n💾 正在保存 {len(all_products)} 个产品的数据...")
        
        # 保存为JSON
        json_path = OUTPUT_DIR / "specific_products.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON已保存: {json_path}")
        
        # 保存为TXT
        txt_path = OUTPUT_DIR / "指定产品资料汇总.txt"
        save_to_txt(all_products, txt_path)
        print(f"✅ TXT已保存: {txt_path}")
        
        print(f"\n✅ 完成！共爬取 {len(all_products)} 个产品")
    else:
        print("\n❌ 未成功爬取任何产品")


if __name__ == "__main__":
    main()
