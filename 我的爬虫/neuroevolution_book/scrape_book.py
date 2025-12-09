#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
神经进化书籍爬虫 - 将在线书籍保存为PDF
"""

import os
import subprocess
import time
import urllib3
from pathlib import Path

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    try:
        from weasyprint import HTML
        HAS_WEASYPRINT = True
    except ImportError:
        HAS_WEASYPRINT = False
        try:
            import pdfkit
            HAS_PDFKIT = True
        except ImportError:
            HAS_PDFKIT = False

BASE_URL = "https://neuroevolutionbook.com/ne_book.html"
OUTPUT_DIR = Path(__file__).parent
OUTPUT_PDF = OUTPUT_DIR / "neuroevolution_book.pdf"


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
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session


def fetch_page(session, url):
    """获取网页内容"""
    print(f"📥 正在获取: {url}")
    print("⏳ 由于文件较大（约48MB），这可能需要几分钟时间...")
    try:
        response = session.get(url, timeout=300, verify=False, stream=True)
        response.raise_for_status()
        # 对于大文件，使用iter_content逐步读取
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content += chunk
        response.encoding = response.apparent_encoding or 'utf-8'
        return content.decode(response.encoding or 'utf-8', errors='ignore')
    except Exception as e:
        print(f"❌ 获取页面失败: {e}")
        return None


def clean_html(html_content):
    """清理和优化HTML内容"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 移除脚本和样式标签
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
    
    # 确保有基本的HTML结构
    if not soup.html:
        html_tag = soup.new_tag('html')
        html_tag.append(soup.new_tag('head'))
        html_tag.append(soup.new_tag('body'))
        soup.insert(0, html_tag)
    
    if not soup.head:
        soup.html.insert(0, soup.new_tag('head'))
    
    if not soup.body:
        soup.html.append(soup.new_tag('body'))
    
    # 添加基本样式
    if not soup.find('style'):
        style = soup.new_tag('style')
        style.string = """
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1, h2, h3 {
            color: #333;
        }
        pre {
            background-color: #f4f4f4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        code {
            background-color: #f4f4f4;
            padding: 2px 5px;
            border-radius: 3px;
        }
        """
        soup.head.append(style)
    
    # 将内容移到body中
    main_content = soup.find('body') or soup
    if soup.body and len(soup.body.contents) == 0:
        # 如果body为空，尝试找到主要内容
        for tag in soup.find_all(['div', 'article', 'main', 'section']):
            if tag.get('class') or tag.get('id'):
                soup.body.append(tag)
    
    return str(soup)


def save_as_pdf_with_playwright(url, output_path):
    """使用Playwright将网页保存为PDF"""
    print(f"📄 正在使用Playwright生成PDF: {output_path}")
    print("⏳ 由于文件较大（约48MB），这可能需要几分钟时间，请耐心等待...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                ignore_https_errors=True,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = context.new_page()
            
            # 设置更长的超时时间（文件很大）
            print("📥 正在加载网页...")
            page.goto(url, wait_until='domcontentloaded', timeout=300000)
            
            # 等待页面完全加载
            print("⏳ 等待页面完全渲染...")
            page.wait_for_timeout(5000)
            
            print("📄 正在生成PDF（这可能需要几分钟）...")
            page.pdf(
                path=str(output_path),
                format='A4',
                margin={'top': '20mm', 'right': '20mm', 'bottom': '20mm', 'left': '20mm'},
                print_background=True
            )
            browser.close()
        print(f"✅ PDF已保存: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Playwright生成PDF失败: {e}")
        return False


def save_as_pdf(html_content, output_path, url=None):
    """将HTML内容保存为PDF"""
    print(f"📄 正在生成PDF: {output_path}")
    
    # 优先使用Playwright（最可靠）
    if HAS_PLAYWRIGHT and url:
        return save_as_pdf_with_playwright(url, output_path)
    
    if HAS_WEASYPRINT:
        try:
            HTML(string=html_content).write_pdf(output_path)
            print(f"✅ PDF已保存: {output_path}")
            return True
        except Exception as e:
            print(f"❌ WeasyPrint生成PDF失败: {e}")
            return False
    
    elif HAS_PDFKIT:
        try:
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }
            pdfkit.from_string(html_content, output_path, options=options)
            print(f"✅ PDF已保存: {output_path}")
            return True
        except Exception as e:
            print(f"❌ pdfkit生成PDF失败: {e}")
            return False
    
    else:
        print("❌ 未找到PDF生成库，请安装: pip install playwright 或 pip install weasyprint")
        return False


def download_with_curl(url, output_path):
    """使用curl下载文件（绕过Python SSL问题）"""
    print(f"📥 使用curl下载网页: {url}")
    print("⏳ 由于文件较大（约48MB），这可能需要几分钟时间...")
    try:
        result = subprocess.run(
            ['curl', '-L', '--max-time', '600', '--retry', '3', '-o', str(output_path), url],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode == 0 and output_path.exists():
            file_size = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ 下载完成！文件大小: {file_size:.2f} MB")
            return True
        else:
            print(f"❌ curl下载失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ curl下载失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 开始爬取神经进化书籍...")
    
    html_path = OUTPUT_DIR / "neuroevolution_book.html"
    
    # 方法1: 使用curl下载HTML（绕过Python SSL问题）
    if not html_path.exists():
        if download_with_curl(BASE_URL, html_path):
            print("✅ HTML文件下载成功")
        else:
            print("❌ 无法下载网页内容")
            return
    
    # 方法2: 使用Playwright将本地HTML转换为PDF
    if HAS_PLAYWRIGHT:
        print("📄 使用Playwright将HTML转换为PDF...")
        print("⏳ 这可能需要几分钟时间，请耐心等待...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080}
                )
                page = context.new_page()
                
                # 加载本地HTML文件
                file_url = f"file://{html_path.absolute()}"
                print(f"📥 正在加载本地文件: {file_url}")
                page.goto(file_url, wait_until='domcontentloaded', timeout=300000)
                
                # 等待页面完全加载
                print("⏳ 等待页面完全渲染...")
                page.wait_for_timeout(5000)
                
                print("📄 正在生成PDF（这可能需要几分钟）...")
                page.pdf(
                    path=str(OUTPUT_PDF),
                    format='A4',
                    margin={'top': '20mm', 'right': '20mm', 'bottom': '20mm', 'left': '20mm'},
                    print_background=True
                )
                browser.close()
            
            file_size = OUTPUT_PDF.stat().st_size / (1024 * 1024)  # MB
            print(f"✅ 完成！PDF文件大小: {file_size:.2f} MB")
            return
        except Exception as e:
            print(f"❌ Playwright生成PDF失败: {e}")
            print(f"⚠️  HTML文件已保存在: {html_path}")
    
    # 如果Playwright不可用，至少HTML文件已经下载了
    print(f"⚠️  无法生成PDF，但HTML文件已保存在: {html_path}")


if __name__ == "__main__":
    main()

