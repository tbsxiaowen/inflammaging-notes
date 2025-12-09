#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中电变压器产品爬虫 - 爬取所有产品详情页内容
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    raise SystemExit("❌ 缺少依赖，请先运行: pip install requests beautifulsoup4 lxml")

BASE_URL = "https://www.zdbyq.cn"
BASE_URL_PARSED = urlparse(BASE_URL)
PRODUCT_LIST_URL = f"{BASE_URL}/product/"
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
    if not href or href.startswith("javascript"):
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


def is_product_detail(url: str) -> bool:
    """判断是否为产品详情页"""
    parsed = urlparse(url)
    return parsed.path.startswith("/pro-") and parsed.path.endswith(".html")


def get_category_base(url: str) -> Optional[str]:
    """获取分类页的基准路径（用于分页识别）"""
    parsed = urlparse(url)
    path = parsed.path
    if not path.startswith("/pro-"):
        return None
    if path.endswith(".html"):
        return None
    if not path.endswith("/"):
        path = f"{path}/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def parse_links_from_page(soup: BeautifulSoup, current_url: str) -> Tuple[Set[str], Set[str]]:
    """从页面中解析出产品详情链接和分类链接"""
    detail_links: Set[str] = set()
    category_links: Set[str] = set()

    for a_tag in soup.find_all("a", href=True):
        full_url = normalize_url(current_url, a_tag["href"])
        if not full_url or not is_same_domain(full_url):
            continue
        parsed = urlparse(full_url)
        path = parsed.path
        if not path.startswith("/pro-"):
            continue
        if path.endswith(".html"):
            detail_links.add(urlunparse(parsed._replace(fragment="")))
        else:
            category_links.add(urlunparse(parsed._replace(fragment="")))

    return detail_links, category_links


def get_product_links(session) -> List[str]:
    """通过遍历分类及分页，获取所有产品详情链接"""
    print(f"📥 正在获取产品列表: {PRODUCT_LIST_URL}")
    to_visit: Set[str] = {PRODUCT_LIST_URL}
    visited: Set[str] = set()
    product_links: Set[str] = set()

    while to_visit:
        page_url = to_visit.pop()
        if page_url in visited:
            continue
        visited.add(page_url)

        try:
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or "utf-8"
        except Exception as exc:
            print(f"❌ 页面获取失败 {page_url}: {exc}")
            continue

        soup = BeautifulSoup(response.text, "lxml")
        details, categories = parse_links_from_page(soup, page_url)
        product_links.update(details)

        for category_url in categories:
            if category_url not in visited:
                to_visit.add(category_url)

        # 处理分类分页链接（例如 ?page=2）
        category_base = get_category_base(page_url)
        if category_base:
            for link in soup.find_all("a", href=True):
                if "?page=" in link["href"]:
                    full = normalize_url(page_url, link["href"])
                    if full.startswith(category_base) and full not in visited:
                        to_visit.add(full)

    print(f"✅ 找到 {len(product_links)} 个产品链接")
    return sorted(product_links)


def extract_product_details(soup: BeautifulSoup, url: str) -> Dict:
    """从产品详情页提取产品信息"""
    product_info = {
        'url': url,
        'title': '',
        'description': '',
        'content': '',
        'images': [],
        'specifications': {},
        'meta_keywords': '',
        'meta_description': '',
    }
    
    try:
        # 提取标题
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            product_info['title'] = title_tag.get_text(strip=True)
        
        # 提取meta信息
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            product_info['meta_keywords'] = meta_keywords.get('content', '')
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            product_info['meta_description'] = meta_desc.get('content', '')
        
        # 提取描述（通常在class包含description的div中）
        desc_tag = soup.find('div', class_=lambda x: x and 'description' in str(x).lower())
        if desc_tag:
            product_info['description'] = desc_tag.get_text(strip=True)
        
        # 提取主要内容
        content_tags = soup.find_all(['div', 'section'], class_=lambda x: x and ('content' in str(x).lower() or 'detail' in str(x).lower()))
        if content_tags:
            product_info['content'] = '\n'.join([tag.get_text(strip=True) for tag in content_tags])
        else:
            # 如果没有找到特定class，提取body的主要内容
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: x and 'main' in str(x).lower())
            if main_content:
                product_info['content'] = main_content.get_text(strip=True)
        
        # 提取图片
        img_tags = soup.find_all('img', src=True)
        for img in img_tags:
            src = img.get('src', '')
            if src:
                if src.startswith('http'):
                    product_info['images'].append(src)
                elif src.startswith('/'):
                    product_info['images'].append(BASE_URL + src)
                else:
                    product_info['images'].append(f"{BASE_URL}/{src}")
        
        # 提取规格参数（通常在表格中）
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        product_info['specifications'][key] = value
        
    except Exception as e:
        print(f"⚠️  提取产品信息时出错: {e}")
    
    return product_info


def get_product_details(session, url: str, delay: float = 0.5) -> Optional[Dict]:
    """获取单个产品详情页内容"""
    print(f"📄 正在获取: {url}")
    try:
        time.sleep(delay)  # 延迟，避免请求过快
        response = session.get(url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or 'utf-8'
        
        soup = BeautifulSoup(response.text, 'lxml')
        product_info = extract_product_details(soup, url)
        
        print(f"✅ 成功获取: {product_info.get('title', '未知标题')}")
        return product_info
        
    except Exception as e:
        print(f"❌ 获取产品详情失败 {url}: {e}")
        return None


def save_product_data(products: List[Dict], format: str = 'json'):
    """保存产品数据"""
    if format == 'json':
        output_file = OUTPUT_DIR / "products.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        print(f"✅ 产品数据已保存到: {output_file}")
    
    # 同时保存为CSV格式
    try:
        import csv
        csv_file = OUTPUT_DIR / "products.csv"
        if products:
            fieldnames = ['url', 'title', 'description', 'meta_keywords', 'meta_description']
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for product in products:
                    row = {k: product.get(k, '') for k in fieldnames}
                    writer.writerow(row)
            print(f"✅ CSV数据已保存到: {csv_file}")
    except Exception as e:
        print(f"⚠️  保存CSV失败: {e}")
    
    # 保存每个产品的详细信息为单独文件
    details_dir = OUTPUT_DIR / "product_details"
    details_dir.mkdir(exist_ok=True)
    
    for product in products:
        if product.get('title'):
            # 清理文件名中的非法字符
            safe_title = "".join(c for c in product['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]  # 限制长度
            if not safe_title:
                safe_title = f"product_{products.index(product)}"
            
            detail_file = details_dir / f"{safe_title}.txt"
            with open(detail_file, 'w', encoding='utf-8') as f:
                f.write(f"产品标题: {product.get('title', '')}\n")
                f.write(f"产品链接: {product.get('url', '')}\n")
                f.write(f"关键词: {product.get('meta_keywords', '')}\n")
                f.write(f"描述: {product.get('meta_description', '')}\n")
                f.write(f"\n详细描述:\n{product.get('description', '')}\n")
                f.write(f"\n详细内容:\n{product.get('content', '')}\n")
                if product.get('images'):
                    f.write(f"\n图片链接:\n")
                    for img in product['images']:
                        f.write(f"  - {img}\n")
                if product.get('specifications'):
                    f.write(f"\n规格参数:\n")
                    for key, value in product['specifications'].items():
                        f.write(f"  {key}: {value}\n")


def main():
    """主函数"""
    print("🚀 开始爬取中电变压器产品...")
    
    session = create_session()
    
    # 获取产品列表
    product_links = get_product_links(session)
    
    if not product_links:
        print("❌ 未找到产品链接，请检查网站结构")
        return
    
    print(f"\n📋 共找到 {len(product_links)} 个产品，开始爬取详情...\n")
    
    # 获取每个产品的详情
    products = []
    for i, link in enumerate(product_links, 1):
        print(f"\n[{i}/{len(product_links)}] ", end='')
        product_info = get_product_details(session, link, delay=0.5)
        if product_info:
            products.append(product_info)
    
    # 保存数据
    if products:
        print(f"\n💾 正在保存 {len(products)} 个产品的数据...")
        save_product_data(products)
        print(f"\n✅ 完成！共爬取 {len(products)} 个产品")
    else:
        print("\n❌ 未成功爬取任何产品")


if __name__ == "__main__":
    main()

