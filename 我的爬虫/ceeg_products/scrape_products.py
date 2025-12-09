#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中电电气产品爬虫 - 爬取所有产品详情页内容
"""

import os
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse, urlunparse

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

# 需要爬取的分类页面
CATEGORY_URLS = [
    "https://www.ceeg.cn/cn/categories/gan-shi-bian-ya-qi-xi-lie",
    "https://www.ceeg.cn/cn/categories/you-jin-shi-bian-ya-qi-xi-lie",
    "https://www.ceeg.cn/cn/categories/te-zhong-bian-ya-qi-xi-lie",
    "https://www.ceeg.cn/cn/categories/kai-guan-gui-xi-lie",
    "https://www.ceeg.cn/cn/categories/xiang-shi-bian-dian-zhan-xi-lie",
]

# 需要搜索的产品名称（格式：{product_name: category_name}）
# 代码会自动搜索这些产品的URL
PRODUCTS_TO_SEARCH = {
    # 智能变压器终端栏目
    "TAT600-3KR智能型 干式变压器温控器非标定制款": "智能变压器终端",
    "TAT602智能型 干式变压器温控器标准版": "智能变压器终端",
    "无线测温在线监测装置": "智能变压器终端",
    "10寸综合在线监测接收装置无线温度监测系统": "智能变压器终端",
    "智能除湿装置": "智能变压器终端",
    "TAT603智能型 干式变压器温控器标准版": "智能变压器终端",
    
    # 智能一体化电源栏目
    "IDC智能一体化电力模组电靓毕方": "智能一体化电源",
    
    # 工商业储能系统栏目
    "储能升压变流一体机": "工商业储能系统",
    "1000kWh工商业储能系统": "工商业储能系统",
    "372kWh液冷储能系统": "工商业储能系统",
    "215kWh风冷储能系统": "工商业储能系统",
    "200kWh风冷储能系统": "工商业储能系统",
    "100kWh风冷储能系统": "工商业储能系统",
    "工商业储能PCS": "工商业储能系统",
}

# 直接指定的产品URL（格式：{url: category_name}）
# 如果自动搜索失败，可以在这里手动指定URL
SPECIFIC_PRODUCTS = {
    # 示例：
    # "https://www.ceeg.cn/cn/archives/tat600-3kr": "智能变压器终端",
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


def get_product_links_from_category(session, category_url: str) -> Set[str]:
    """从分类页面获取所有产品链接"""
    product_links: Set[str] = set()
    visited: Set[str] = {category_url}
    to_visit: Set[str] = {category_url}
    
    # 保存分类信息，用于后续关联产品
    category_name = category_url.split('/')[-1]
    
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
        
        # 查找分页链接 - 检查URL参数中的page
        for a_tag in soup.find_all("a", href=True):
            href = a_tag.get("href", "")
            if not href or 'page=' not in href:
                continue
            full_url = normalize_url(page_url, href)
            if is_same_domain(full_url) and full_url not in visited:
                # 确保是同一个分类的分页
                parsed_current = urlparse(page_url)
                parsed_new = urlparse(full_url)
                if parsed_current.path == parsed_new.path:
                    to_visit.add(full_url)
                    visited.add(full_url)
    
    return product_links, category_name


def search_product_urls(session, product_names: List[str], category_name: str = '') -> Dict[str, str]:
    """
    根据产品名称搜索产品URL
    返回: {product_name: url} 的字典
    """
    found_urls = {}
    
    # 尝试从可能的分类页面搜索
    # 根据分类名称猜测可能的URL
    category_url_map = {
        "智能变压器终端": [
            "https://www.ceeg.cn/cn/categories/zhi-neng-bian-ya-qi-zhong-duan",
            "https://www.ceeg.cn/cn/categories/zhi-neng-bian-ya-qi",
            "https://www.ceeg.cn/cn/categories/bian-ya-qi-zhong-duan",
        ],
        "智能一体化电源": [
            "https://www.ceeg.cn/cn/categories/zhi-neng-yi-ti-hua-dian-yuan",
            "https://www.ceeg.cn/cn/categories/yi-ti-hua-dian-yuan",
            "https://www.ceeg.cn/cn/categories/zhi-neng-dian-yuan",
        ],
        "工商业储能系统": [
            "https://www.ceeg.cn/cn/categories/gong-shang-ye-chu-neng-xi-tong",
            "https://www.ceeg.cn/cn/categories/chu-neng-xi-tong",
            "https://www.ceeg.cn/cn/categories/gong-shang-ye-chu-neng",
        ],
    }
    
    search_urls = category_url_map.get(category_name, [])
    # 也尝试从首页搜索
    search_urls.append("https://www.ceeg.cn/cn")
    
    print(f"🔍 正在搜索 {len(product_names)} 个产品（分类: {category_name}）...")
    
    all_product_urls = set()
    
    # 第一步：收集所有可能的产品URL
    for search_url in search_urls:
        try:
            response = session.get(search_url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
            soup = BeautifulSoup(response.text, "lxml")
            
            # 查找所有产品链接
            for a_tag in soup.find_all("a", href=True):
                href = a_tag.get("href", "")
                if not href:
                    continue
                full_url = normalize_url(search_url, href)
                if not is_same_domain(full_url):
                    continue
                parsed = urlparse(full_url)
                path = parsed.path
                
                # 产品详情页在 /cn/archives/ 路径下
                if path.startswith("/cn/archives/") and path != "/cn/archives/":
                    all_product_urls.add(full_url)
                    
        except Exception as exc:
            print(f"⚠️  搜索页面失败 {search_url}: {exc}")
            continue
    
    # 第二步：访问每个产品页面，检查标题是否匹配
    print(f"📋 找到 {len(all_product_urls)} 个产品链接，正在检查标题匹配...")
    for product_url in all_product_urls:
        if len(found_urls) == len(product_names):
            break
            
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
                continue
            
            # 检查标题是否匹配任何产品名称
            for product_name in product_names:
                if product_name in found_urls:
                    continue
                
                # 精确匹配
                if product_name in title or title in product_name:
                    found_urls[product_name] = product_url
                    print(f"✅ 找到（精确匹配）: {product_name} -> {product_url}")
                    break
                
                # 关键词匹配：检查产品名称的主要关键词是否都在标题中
                name_keywords = [kw for kw in product_name.split() if len(kw) > 1]
                # 移除常见无意义词
                name_keywords = [kw for kw in name_keywords if kw not in ['的', '和', '与', '型', '版', '系统', '装置']]
                
                if len(name_keywords) >= 2:
                    # 如果至少2个关键词都在标题中，认为匹配
                    matched_keywords = sum(1 for kw in name_keywords if kw in title)
                    if matched_keywords >= min(2, len(name_keywords)):
                        found_urls[product_name] = product_url
                        print(f"✅ 找到（关键词匹配）: {product_name} -> {product_url}")
                        break
                
                # 特殊处理：对于包含型号的产品（如TAT600-3KR），检查型号部分
                if '-' in product_name or any(char.isdigit() for char in product_name):
                    # 提取型号部分（如TAT600-3KR, 1000kWh等）
                    import re
                    model_patterns = re.findall(r'[A-Z]+\d+[-\dA-Z]*|\d+[kK]?[WwHh]', product_name)
                    if model_patterns:
                        for pattern in model_patterns:
                            if pattern in title:
                                found_urls[product_name] = product_url
                                print(f"✅ 找到（型号匹配）: {product_name} -> {product_url}")
                                break
                        if product_name in found_urls:
                            break
                    
        except Exception as exc:
            # 静默失败，继续下一个
            continue
    
    return found_urls


def extract_product_details_from_html(html_content: str, url: str, category_name: str = '') -> Dict:
    """从产品详情页提取产品信息"""
    product_info = {
        'url': url,
        'title': '',
        'category': '',
        'description': '',
        'content': '',
        'specifications': {},
        'images': [],
    }
    
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 提取标题 - 优先从h1获取，如果没有则从title标签提取并清理
        title_tag = soup.find('h1')
        if title_tag:
            product_info['title'] = title_tag.get_text(strip=True)
        
        if not product_info['title']:
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # 清理title标签中的网站名称等
                if ' - ' in title_text:
                    product_info['title'] = title_text.split(' - ')[0].strip()
                elif ' · ' in title_text:
                    product_info['title'] = title_text.split(' · ')[0].strip()
                else:
                    product_info['title'] = title_text
        
        # 提取分类信息
        category_map = {
            'gan-shi-bian-ya-qi-xi-lie': '干式变压器系列',
            'you-jin-shi-bian-ya-qi-xi-lie': '油浸式变压器系列',
            'te-zhong-bian-ya-qi-xi-lie': '特种变压器系列',
            'kai-guan-gui-xi-lie': '开关柜系列',
            'xiang-shi-bian-dian-zhan-xi-lie': '箱式变电站系列',
            '智能变压器终端': '智能变压器终端',
            '智能一体化电源': '智能一体化电源',
            '工商业储能系统': '工商业储能系统',
        }
        if category_name and category_name in category_map:
            product_info['category'] = category_map[category_name]
        elif category_name:
            # 如果category_name不在映射中，直接使用
            product_info['category'] = category_name
        
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
        
        # 提取主要内容
        content_selectors = [
            '.product-content',
            '.content',
            '.product-detail',
            '.detail',
            'article',
            'main',
            '.main-content',
        ]
        
        # 需要移除的导航和页脚关键词
        unwanted_keywords = [
            '为世界输出优质动力',
            '资料中心',
            '24小时服务热线',
            '关于中电',
            '中电概況',
            '中电荣誉',
            '发展历程',
            '数说中电',
            '合作伙伴',
            '新闻资讯',
            '全球足迹',
            '经典项目',
            '企业文化',
            '社会责任',
            '经营发展',
            '加入中电',
            '热销产品',
            '变压器',
            '一体化电源',
            '储能系统',
            '电力物联网',
            '解决方案',
            '定制解决方案',
            '产品解决方案',
            '行业解决方案',
            '联系我们',
            '地址：',
            '邮箱：',
            '产品咨询热线',
            '销售对接微信',
            '版权所有',
            '苏ICP备',
            '法律条款',
            '点击咨询',
            '下载产品手册',
            '电话咨询',
            '400-080-0008',
        ]
        
        # 首先查找主要内容区域（这个网站的内容在特定div中）
        # 查找包含大量文本的div（通常是主要内容区域）
        main_content_div = None
        body = soup.find('body')
        if body:
            # 查找包含产品介绍、规格参数等关键词的div
            content_keywords = ['产品介绍', '规格参数', '选型产品', '空载低耗', '先进工艺', '三维设计', '高压绕组', '产品业绩']
            for keyword in content_keywords:
                elements = body.find_all(string=lambda text: text and keyword in str(text))
                if elements:
                    # 找到包含关键词的元素的父容器
                    for elem in elements:
                        parent = elem.parent
                        # 向上查找包含大量文本的父div
                        while parent and parent.name != 'body':
                            if parent.name == 'div':
                                text = parent.get_text(strip=True)
                                if len(text) > 1000:  # 包含大量文本
                                    main_content_div = parent
                                    break
                            parent = parent.parent
                        if main_content_div:
                            break
                if main_content_div:
                    break
        
        # 如果找到了主要内容div，提取其内容
        if main_content_div:
            # 移除不需要的元素
            for elem in main_content_div(["script", "style", "nav", "header", "footer", "aside", "form"]):
                elem.decompose()
            
            # 提取固定部分的内容
            content_parts = []
            
            # 1. 提取产品介绍（class包含text-[14px]或text-[16px]的描述性文本）
            intro_divs = main_content_div.find_all('div', class_=lambda x: x and ('text-[14px]' in str(x) or 'text-[16px]' in str(x)))
            for div in intro_divs:
                text = div.get_text(strip=True)
                # 产品介绍通常是较长的描述性文本
                if text and len(text) > 50 and len(text) < 500:
                    # 排除明显是参数表格的内容
                    if not any(kw in text for kw in ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸']):
                        if text not in content_parts:
                            content_parts.append(text)
            
            # 2. 提取标签（tags，如"创新工艺"、"甄选材料"等）
            tags_divs = main_content_div.find_all('div', class_=lambda x: x and 'tags' in str(x).lower())
            for tags_div in tags_divs:
                tag_items = tags_div.find_all('div', class_=lambda x: x and ('px-' in str(x) or 'py-' in str(x)))
                if tag_items:
                    tags = [item.get_text(strip=True) for item in tag_items if item.get_text(strip=True)]
                    if tags:
                        content_parts.append('标签: ' + '、'.join(tags))
            
            # 3. 提取特性说明（text-[24px]的标题 + text-[16px]的描述）
            feature_items = main_content_div.find_all('div', class_=lambda x: x and 'item' in str(x).lower() and 'flex' in str(x).lower())
            for item in feature_items:
                # 查找标题（text-[24px]）
                title = item.find('div', class_=lambda x: x and 'text-[24px]' in str(x))
                # 查找描述（text-[16px]）
                desc = item.find('div', class_=lambda x: x and 'text-[16px]' in str(x))
                if title and desc:
                    title_text = title.get_text(strip=True)
                    desc_text = desc.get_text(strip=True)
                    if title_text and desc_text:
                        content_parts.append(f'{title_text}\n{desc_text}')
            
            # 4. 提取技术说明部分（title class的标题 + 描述文本）
            tech_sections = main_content_div.find_all('div', class_=lambda x: x and 'product2-item' in str(x).lower())
            for section in tech_sections:
                # 查找标题（class包含title和text-[58px]）
                title = section.find('div', class_=lambda x: x and 'title' in str(x).lower() and 'text-[58px]' in str(x))
                # 查找描述（text-[20px]）
                desc = section.find('div', class_=lambda x: x and 'text-[20px]' in str(x))
                if title and desc:
                    title_text = title.get_text(strip=True)
                    desc_text = desc.get_text(strip=True)
                    if title_text and desc_text:
                        content_parts.append(f'{title_text}\n{desc_text}')
            
            # 5. 提取产品业绩
            performance_section = main_content_div.find('div', class_=lambda x: x and 'performance' in str(x).lower())
            if performance_section:
                performance_items = performance_section.find_all('div', class_=lambda x: x and 'flex' in str(x).lower())
                if performance_items:
                    performances = [item.get_text(strip=True) for item in performance_items if item.get_text(strip=True)]
                    if performances:
                        content_parts.append('产品业绩\n' + '\n'.join(performances))
            
            # 6. 如果没有找到结构化内容，尝试提取其他重要部分
            if not content_parts:
                # 查找所有包含重要关键词的标题
                important_keywords = ['三维设计', '高压绕组', '低压绕组', '铁心', '试验与检测技术', '产品业绩', '绝缘', '绕组', '全自动叠片']
                for keyword in important_keywords:
                    elements = main_content_div.find_all(string=lambda text: text and keyword in str(text))
                    for elem in elements:
                        parent = elem.parent
                        if parent:
                            classes = ' '.join(parent.get('class', []))
                            # 如果是标题样式
                            if 'title' in classes.lower() or 'text-[58px]' in classes or 'text-[24px]' in classes:
                                title_text = parent.get_text(strip=True)
                                if title_text not in content_parts:
                                    content_parts.append(title_text)
                                    # 查找描述
                                    next_sib = parent.find_next_sibling()
                                    if next_sib:
                                        desc = next_sib.get_text(strip=True)
                                        if desc and len(desc) > 20:
                                            content_parts.append(desc)
            
            if content_parts:
                # 过滤掉技术参数相关内容
                filtered_parts = []
                param_keywords = ['产品型号', 'UK%', '空损', '负损', 'I0(%)', 'LPA', 'dB', '轨矩', '本体尺寸', '外壳尺寸', 
                                 '额定电压', '联结组别', '分接范围', '注：上述参数', 'SC(B)', 'SC10-', 'SC11-', 'SC12-', 'SC13-', 'SC14-', 'SC18-']
                
                for part in content_parts:
                    # 跳过包含技术参数关键词的内容
                    if any(kw in part for kw in param_keywords):
                        continue
                    # 跳过看起来像参数表格的行（包含多个数字和单位）
                    if len(part.split()) > 10 and any(char.isdigit() for char in part) and ('kV' in part or 'mm' in part or 'W' in part):
                        # 进一步检查：如果包含多个连续的数字+单位组合，可能是参数表格
                        import re
                        if len(re.findall(r'\d+[kK]?[VvWw]|mm|%', part)) > 3:
                            continue
                    filtered_parts.append(part)
                
                # 去重但保持顺序
                seen = set()
                unique_parts = []
                for part in filtered_parts:
                    if len(part) < 10:
                        continue
                    
                    # 检查是否已经被包含在其他部分中
                    is_duplicate = False
                    for existing in seen:
                        if part in existing and part != existing:
                            is_duplicate = True
                            break
                        if existing in part and part != existing:
                            # 如果现有内容被新内容包含，移除现有内容
                            if existing in unique_parts:
                                unique_parts.remove(existing)
                                seen.remove(existing)
                            break
                    
                    if not is_duplicate and part not in seen:
                        seen.add(part)
                        unique_parts.append(part)
                
                product_info['content'] = '\n\n'.join(unique_parts)
        
        # 如果还没有内容，尝试查找article或main
        if not product_info['content']:
            article = soup.find('article') or soup.find('main')
            if article:
                # 移除不需要的元素
                for elem in article(["script", "style", "nav", "header", "footer", "aside", "form"]):
                    elem.decompose()
                
                # 查找主要内容区域（通常包含产品介绍、特点等）
                content_sections = []
                
                # 查找所有段落和列表
                for tag in article.find_all(['p', 'div', 'li', 'h2', 'h3', 'h4', 'section']):
                    text = tag.get_text(strip=True)
                    if not text or len(text) < 10:
                        continue
                    # 跳过明显的导航和页脚
                    if any(keyword in text for keyword in unwanted_keywords[:15]):
                        continue
                    # 跳过太短的行（可能是导航项）
                    if len(text) < 20 and any(nav in text for nav in ['首页', '关于', '产品', '新闻', '联系我们']):
                        continue
                    content_sections.append(text)
                
                if content_sections:
                    product_info['content'] = '\n\n'.join(content_sections)
        
        # 如果还没有内容，尝试其他选择器
        if not product_info['content']:
            for selector in content_selectors:
                content_tag = soup.select_one(selector)
                if content_tag:
                    # 移除脚本和样式
                    for script in content_tag(["script", "style", "nav", "header", "footer", "aside"]):
                        script.decompose()
                    content_text = content_tag.get_text(separator='\n', strip=True)
                    # 清理不需要的内容
                    lines = content_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) < 10:
                            continue
                        # 跳过包含不需要关键词的行
                        if any(keyword in line for keyword in unwanted_keywords):
                            continue
                        cleaned_lines.append(line)
                    if cleaned_lines:
                        product_info['content'] = '\n'.join(cleaned_lines)
                        break
        
        # 如果没有找到特定内容区域，提取body的主要内容
        if not product_info['content']:
            # 尝试查找更具体的内容区域
            content_divs = soup.find_all('div', class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['content', 'detail', 'intro', 'desc', 'text', 'body']
            ))
            if content_divs:
                for div in content_divs:
                    for script in div(["script", "style", "nav", "header", "footer", "aside"]):
                        script.decompose()
                    content_text = div.get_text(separator='\n', strip=True)
                    if len(content_text) > 100:  # 只保留有实际内容的
                        # 清理不需要的内容
                        lines = content_text.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            line = line.strip()
                            if not line or len(line) < 3:
                                continue
                            # 只过滤明显是导航/页脚的长行
                            if len(line) > 50 and any(keyword in line for keyword in unwanted_keywords[:10]):
                                continue
                            cleaned_lines.append(line)
                        if cleaned_lines:
                            product_info['content'] = '\n'.join(cleaned_lines)
                            break
            
            # 如果还是没有，从main提取
            if not product_info['content']:
                main_content = soup.find('main') or soup.find('article')
                if main_content:
                    for script in main_content(["script", "style", "nav", "header", "footer", "aside"]):
                        script.decompose()
                    content_text = main_content.get_text(separator='\n', strip=True)
                    # 清理不需要的内容
                    lines = content_text.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        line = line.strip()
                        if not line or len(line) < 3:
                            continue
                        # 只过滤明显是导航/页脚的长行
                        if len(line) > 50 and any(keyword in line for keyword in unwanted_keywords[:10]):
                            continue
                        cleaned_lines.append(line)
                    product_info['content'] = '\n'.join(cleaned_lines)
        
        # 提取图片
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = img.get('src', '')
            if src:
                full_img_url = normalize_url(url, src)
                if is_same_domain(full_img_url) or 'ceeg.cn' in full_img_url:
                    product_info['images'].append(full_img_url)
        
        # 不提取规格参数表格（用户要求删除）
        
    except Exception as e:
        print(f"⚠️  提取产品信息时出错: {e}")
    
    return product_info


def get_product_details_with_playwright(url: str, category_name: str = '') -> Optional[Dict]:
    """使用Playwright获取产品详情（支持JavaScript渲染）"""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            page.goto(url, wait_until='networkidle', timeout=60000)
            # 等待页面完全加载
            page.wait_for_timeout(2000)
            
            # 获取渲染后的HTML
            html_content = page.content()
            browser.close()
            
            return extract_product_details_from_html(html_content, url, category_name)
    except Exception as e:
        print(f"⚠️  Playwright获取失败: {e}")
        return None


def get_product_details(session, url: str, category_name: str = '', delay: float = 0.5, use_playwright: bool = True) -> Optional[Dict]:
    """获取单个产品详情页内容"""
    print(f"📄 正在获取: {url}")
    
    # 优先使用Playwright（如果可用）
    if use_playwright and HAS_PLAYWRIGHT:
        product_info = get_product_details_with_playwright(url, category_name)
        if product_info:
            if product_info.get('title'):
                print(f"✅ 成功获取: {product_info['title']}")
            else:
                print(f"✅ 成功获取: {url}")
            return product_info
    
    # 回退到requests方式
    try:
        time.sleep(delay)  # 延迟，避免请求过快
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
    # 根据URL中的分类信息分组
    category_map = {
        'gan-shi-bian-ya-qi-xi-lie': '干式变压器系列',
        'you-jin-shi-bian-ya-qi-xi-lie': '油浸式变压器系列',
        'te-zhong-bian-ya-qi-xi-lie': '特种变压器系列',
        'kai-guan-gui-xi-lie': '开关柜系列',
        'xiang-shi-bian-dian-zhan-xi-lie': '箱式变电站系列',
        '智能变压器终端': '智能变压器终端',
        '智能一体化电源': '智能一体化电源',
        '工商业储能系统': '工商业储能系统',
    }
    
    # 按分类分组（根据来源URL推断分类）
    categories = {}
    for product in products:
        url = product.get('url', '')
        category = '其他'
        # 尝试从产品数据中获取分类
        if product.get('category'):
            category = product.get('category')
        else:
            # 从URL推断（需要知道是从哪个分类页爬取的）
            # 这里我们按顺序分配，或者保持为"其他"
            category = '其他'
        if category not in categories:
            categories[category] = []
        categories[category].append(product)
    
    with open(output_path, 'w', encoding='utf-8') as f:
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
                    if desc and len(desc) > 20:  # 过滤太短的描述
                        f.write(f"产品介绍:\n{desc}\n\n")
                
                if product.get('content'):
                    content = product.get('content', '').strip()
                    if content:
                        f.write(f"产品详情:\n{content}\n\n")
                
                # 不再输出技术参数（用户要求删除）
        
        f.write(f"\n{'='*80}\n")
        f.write(f"总计: {len(products)} 个产品\n")
        f.write(f"{'='*80}\n")


def main():
    """主函数"""
    print("🚀 开始爬取中电电气产品...")
    
    session = create_session()
    all_product_links: Dict[str, str] = {}  # url -> category_name
    
    # 从所有分类页面获取产品链接
    for category_url in CATEGORY_URLS:
        print(f"\n📂 处理分类: {category_url}")
        product_links, category_name = get_product_links_from_category(session, category_url)
        for link in product_links:
            all_product_links[link] = category_name
        print(f"✅ 从该分类找到 {len(product_links)} 个产品链接")
    
    # 搜索指定的产品
    if PRODUCTS_TO_SEARCH:
        print(f"\n🔍 搜索指定的产品 ({len(PRODUCTS_TO_SEARCH)} 个)...")
        # 按分类分组搜索
        products_by_category = {}
        for product_name, category_name in PRODUCTS_TO_SEARCH.items():
            if category_name not in products_by_category:
                products_by_category[category_name] = []
            products_by_category[category_name].append(product_name)
        
        # 对每个分类的产品进行搜索
        for category_name, product_names in products_by_category.items():
            print(f"\n📂 搜索分类 '{category_name}' 下的产品...")
            found_urls = search_product_urls(session, product_names, category_name)
            for product_name, url in found_urls.items():
                all_product_links[url] = category_name
                print(f"✅ 找到产品: {product_name} -> {url}")
            
            # 检查未找到的产品
            not_found = [name for name in product_names if name not in found_urls]
            if not_found:
                print(f"⚠️  以下产品未找到URL，请手动添加到SPECIFIC_PRODUCTS:")
                for name in not_found:
                    print(f"   - {name}")
    
    # 添加直接指定的产品URL
    if SPECIFIC_PRODUCTS:
        print(f"\n📂 处理直接指定的产品 ({len(SPECIFIC_PRODUCTS)} 个)...")
        for product_url, category_name in SPECIFIC_PRODUCTS.items():
            all_product_links[product_url] = category_name
            print(f"✅ 添加指定产品: {product_url} ({category_name})")
    
    if not all_product_links:
        print("\n❌ 未找到产品链接，请检查网站结构")
        print("💡 尝试直接访问分类页面查看结构...")
        return
    
    print(f"\n📋 共找到 {len(all_product_links)} 个产品，开始爬取详情...\n")
    
    # 获取每个产品的详情
    products = []
    for i, (link, category_name) in enumerate(sorted(all_product_links.items()), 1):
        print(f"\n[{i}/{len(all_product_links)}] ", end='')
        product_info = get_product_details(session, link, category_name, delay=0.5)
        if product_info:
            products.append(product_info)
    
    # 保存数据
    if products:
        print(f"\n💾 正在保存 {len(products)} 个产品的数据...")
        
        # 保存为JSON（备用）
        json_path = OUTPUT_DIR / "products.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON已保存: {json_path}")
        
        # 保存为TXT
        txt_path = OUTPUT_DIR / "产品资料汇总.txt"
        save_to_txt(products, txt_path)
        print(f"✅ TXT已保存: {txt_path}")
        
        print(f"\n✅ 完成！共爬取 {len(products)} 个产品")
    else:
        print("\n❌ 未成功爬取任何产品")


if __name__ == "__main__":
    main()

