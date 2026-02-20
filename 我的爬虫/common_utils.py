#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫项目公共工具函数
供各个爬虫项目共享使用
"""

from typing import Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_session(
    retry_total: int = 3,
    retry_backoff: float = 1.0,
    retry_status_forcelist: Optional[list] = None,
    user_agent: Optional[str] = None,
    accept_language: str = "zh-CN,zh;q=0.9,en;q=0.8",
) -> requests.Session:
    """
    创建带重试机制的 requests 会话
    
    Args:
        retry_total: 最大重试次数，默认3次
        retry_backoff: 重试退避因子，默认1.0秒
        retry_status_forcelist: 需要重试的HTTP状态码列表，默认[429, 500, 502, 503, 504]
        user_agent: 自定义User-Agent，默认使用Chrome的UA
        accept_language: Accept-Language头，默认中文优先
    
    Returns:
        配置好的 requests.Session 对象
    """
    if retry_status_forcelist is None:
        retry_status_forcelist = [429, 500, 502, 503, 504]
    
    if user_agent is None:
        user_agent = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    
    session = requests.Session()
    retry_strategy = Retry(
        total=retry_total,
        backoff_factor=retry_backoff,
        status_forcelist=retry_status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': accept_language,
    })
    return session


def normalize_url(base_url: str, href: str) -> str:
    """
    规范化URL，移除片段并补全域名
    
    Args:
        base_url: 基础URL
        href: 相对或绝对URL
    
    Returns:
        规范化后的完整URL，如果href无效则返回空字符串
    """
    from urllib.parse import urljoin, urlparse, urlunparse
    
    # 过滤无效的href
    if not href or href.startswith("javascript:") or href.startswith("#"):
        return ""
    
    # 移除fragment（#后面的部分）
    clean_href = href.split("#", 1)[0].strip()
    if not clean_href:
        return ""
    
    # 使用urljoin合并URL
    full_url = urljoin(base_url, clean_href)
    
    # 解析并确保有scheme
    parsed = urlparse(full_url)
    if not parsed.scheme:
        base_parsed = urlparse(base_url)
        parsed = parsed._replace(scheme=base_parsed.scheme)
    
    # 重新组合URL（移除fragment）
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # 移除fragment
    ))
    
    return normalized









