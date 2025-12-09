#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF页面内容抓取工具
支持从PDF查看器页面下载PDF文件和HTML内容
"""

import os
import sys
import re
import urllib.parse
from pathlib import Path
from typing import Optional

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("❌ 缺少依赖包: requests")
    print("请运行: pip install requests")
    sys.exit(1)


class PDFDownloader:
    """PDF下载器"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化下载器
        
        Args:
            output_dir: 输出目录，默认为当前目录下的 'downloaded_pdfs' 文件夹
        """
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "downloaded_pdfs"
        
        self.output_dir.mkdir(exist_ok=True)
        
        # 配置session，添加重试机制
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置请求头，模拟浏览器
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def extract_pdf_url(self, viewer_url: str) -> Optional[str]:
        """
        从PDF查看器URL中提取实际的PDF文件URL
        
        Args:
            viewer_url: PDF查看器页面URL
            
        Returns:
            PDF文件的直接URL，如果提取失败返回None
        """
        try:
            # 解析URL参数
            parsed = urllib.parse.urlparse(viewer_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            # 获取file参数
            if 'file' in query_params:
                file_param = query_params['file'][0]
                # file参数可能是编码的，需要解码
                file_param = urllib.parse.unquote(file_param)
                
                # 如果file参数是相对路径，需要拼接完整URL
                if file_param.startswith('/'):
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    pdf_url = base_url + file_param
                elif file_param.startswith('http'):
                    pdf_url = file_param
                else:
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    pdf_url = base_url + '/' + file_param
                
                return pdf_url
            else:
                # 如果没有file参数，尝试从URL路径中提取
                # 例如: /gsapp/sys/gglglyy/pdf/loadPdf.do?...
                if 'loadPdf.do' in parsed.path or 'pdf' in parsed.path.lower():
                    base_url = f"{parsed.scheme}://{parsed.netloc}"
                    pdf_url = base_url + parsed.path
                    if parsed.query:
                        pdf_url += '?' + parsed.query
                    return pdf_url
                
        except Exception as e:
            print(f"⚠️  URL解析失败: {e}")
        
        return None
    
    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """
        下载PDF文件
        
        Args:
            url: PDF文件URL或查看器URL
            filename: 保存的文件名，如果不指定则自动生成
            
        Returns:
            保存的文件路径，如果失败返回None
        """
        print(f"🔍 正在分析URL: {url}")
        
        # 先尝试提取PDF URL
        pdf_url = self.extract_pdf_url(url)
        if not pdf_url:
            # 如果提取失败，直接使用原URL
            pdf_url = url
            print("⚠️  无法提取PDF URL，将直接使用原URL")
        else:
            print(f"✅ 提取到PDF URL: {pdf_url}")
        
        # 生成文件名
        if not filename:
            # 尝试从URL中提取文件名
            parsed = urllib.parse.urlparse(pdf_url)
            filename = os.path.basename(parsed.path)
            
            # 如果还是没有文件名，使用默认名称
            if not filename or '.' not in filename:
                # 尝试从URL参数中获取标题
                query_params = urllib.parse.parse_qs(parsed.query)
                if 'synr' in query_params:
                    title = query_params['synr'][0]
                    filename = f"{urllib.parse.unquote(title)}.pdf"
                else:
                    filename = "downloaded_document.pdf"
            
            # 清理文件名中的非法字符
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            if not filename.endswith('.pdf'):
                filename += '.pdf'
        
        output_path = self.output_dir / filename
        
        print(f"📥 开始下载PDF文件...")
        print(f"   目标文件: {output_path}")
        
        try:
            # 下载文件
            response = self.session.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 检查内容类型
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not pdf_url.endswith('.pdf'):
                print(f"⚠️  警告: 内容类型为 {content_type}，可能不是PDF文件")
            
            # 保存文件
            total_size = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r   进度: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
            
            print(f"\n✅ PDF文件下载完成: {output_path}")
            print(f"   文件大小: {downloaded:,} bytes")
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ 下载失败: {e}")
            return None
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            return None
    
    def download_html(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """
        下载HTML页面内容
        
        Args:
            url: 页面URL
            filename: 保存的文件名，如果不指定则自动生成
            
        Returns:
            保存的文件路径，如果失败返回None
        """
        print(f"📄 正在下载HTML页面: {url}")
        
        if not filename:
            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path) or "downloaded_page.html"
            if not filename.endswith('.html'):
                filename += '.html'
        
        output_path = self.output_dir / filename
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 保存HTML
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"✅ HTML页面下载完成: {output_path}")
            print(f"   文件大小: {len(response.text):,} bytes")
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            print(f"❌ 下载失败: {e}")
            return None
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            return None
    
    def download_all(self, url: str) -> dict:
        """
        下载PDF和HTML内容
        
        Args:
            url: PDF查看器URL或PDF文件URL
            
        Returns:
            包含下载结果的字典
        """
        results = {
            'pdf_path': None,
            'html_path': None,
            'success': False
        }
        
        print("=" * 60)
        print("🚀 开始抓取PDF页面内容")
        print("=" * 60)
        
        # 下载PDF
        pdf_path = self.download_pdf(url)
        results['pdf_path'] = pdf_path
        
        # 下载HTML（如果是查看器页面）
        if 'viewer.html' in url or 'viewer' in url.lower():
            html_path = self.download_html(url)
            results['html_path'] = html_path
        
        results['success'] = pdf_path is not None
        
        print("=" * 60)
        if results['success']:
            print("✅ 抓取完成！")
            if results['pdf_path']:
                print(f"   PDF文件: {results['pdf_path']}")
            if results['html_path']:
                print(f"   HTML文件: {results['html_path']}")
        else:
            print("❌ 抓取失败")
        print("=" * 60)
        
        return results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF页面内容抓取工具')
    parser.add_argument('url', help='PDF查看器URL或PDF文件URL')
    parser.add_argument('-o', '--output', help='输出目录', default=None)
    parser.add_argument('-f', '--filename', help='PDF文件名（可选）', default=None)
    parser.add_argument('--html-only', action='store_true', help='仅下载HTML页面')
    parser.add_argument('--pdf-only', action='store_true', help='仅下载PDF文件')
    
    args = parser.parse_args()
    
    downloader = PDFDownloader(output_dir=args.output)
    
    if args.html_only:
        downloader.download_html(args.url, args.filename)
    elif args.pdf_only:
        downloader.download_pdf(args.url, args.filename)
    else:
        downloader.download_all(args.url)


if __name__ == "__main__":
    main()

