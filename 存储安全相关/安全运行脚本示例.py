#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全运行脚本示例 - 限制文件访问范围

这个脚本演示如何限制 Python 代码只能访问项目目录内的文件，
防止误删项目外的文件。

使用方法：
    python 安全运行脚本示例.py <要运行的脚本.py>

注意：这只是一个示例，实际使用时需要根据具体需求调整。
"""

import os
import sys
import shutil
from pathlib import Path

# ============================================================================
# 配置：允许访问的目录
# ============================================================================

# 只允许访问项目目录
ALLOWED_DIR = Path(__file__).parent.resolve()  # 当前脚本所在目录
ALLOWED_DIR = ALLOWED_DIR.resolve()

print(f"🛡️  安全模式：只允许访问目录: {ALLOWED_DIR}")

# ============================================================================
# 安全检查函数
# ============================================================================

def check_path_safe(path):
    """
    检查路径是否在允许的目录内
    
    Args:
        path: 要检查的路径（字符串或 Path 对象）
    
    Returns:
        bool: 如果路径安全返回 True，否则返回 False
    """
    try:
        resolved = Path(path).resolve()
        allowed_str = str(ALLOWED_DIR)
        path_str = str(resolved)
        
        # 检查路径是否在允许的目录内
        if path_str.startswith(allowed_str):
            return True
        else:
            print(f"❌ 拒绝访问项目外的路径: {path}")
            return False
    except Exception as e:
        print(f"❌ 路径检查失败: {e}")
        return False

# ============================================================================
# 重写危险的文件操作函数
# ============================================================================

# 保存原始函数
_original_remove = os.remove
_original_rmdir = os.rmdir
_original_unlink = os.unlink
_original_rmtree = shutil.rmtree

def safe_remove(path):
    """安全的文件删除"""
    if not check_path_safe(path):
        raise PermissionError(
            f"❌ 安全限制：不允许删除项目外的文件\n"
            f"   尝试删除: {path}\n"
            f"   允许目录: {ALLOWED_DIR}"
        )
    return _original_remove(path)

def safe_rmdir(path):
    """安全的目录删除"""
    if not check_path_safe(path):
        raise PermissionError(
            f"❌ 安全限制：不允许删除项目外的目录\n"
            f"   尝试删除: {path}\n"
            f"   允许目录: {ALLOWED_DIR}"
        )
    return _original_rmdir(path)

def safe_unlink(path):
    """安全的文件删除（unlink）"""
    if not check_path_safe(path):
        raise PermissionError(
            f"❌ 安全限制：不允许删除项目外的文件\n"
            f"   尝试删除: {path}\n"
            f"   允许目录: {ALLOWED_DIR}"
        )
    return _original_unlink(path)

def safe_rmtree(path):
    """安全的递归目录删除"""
    if not check_path_safe(path):
        raise PermissionError(
            f"❌ 安全限制：不允许删除项目外的目录\n"
            f"   尝试删除: {path}\n"
            f"   允许目录: {ALLOWED_DIR}"
        )
    return _original_rmtree(path)

# 替换系统函数
os.remove = safe_remove
os.rmdir = safe_rmdir
os.unlink = safe_unlink
shutil.rmtree = safe_rmtree

# ============================================================================
# 运行用户脚本
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python 安全运行脚本示例.py <要运行的脚本.py>")
        print("\n示例:")
        print("  python 安全运行脚本示例.py 我的爬虫/scrape_products.py")
        sys.exit(1)
    
    script_path = Path(sys.argv[1])
    
    if not script_path.exists():
        print(f"❌ 文件不存在: {script_path}")
        sys.exit(1)
    
    if not check_path_safe(script_path):
        print(f"❌ 不允许运行项目外的脚本: {script_path}")
        sys.exit(1)
    
    print(f"✅ 正在安全模式下运行: {script_path}")
    print("-" * 60)
    
    try:
        # 读取并执行脚本
        with open(script_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 在全局命名空间中执行
        exec(compile(code, str(script_path), 'exec'), {
            '__name__': '__main__',
            '__file__': str(script_path),
            '__builtins__': __builtins__,
        })
        
        print("-" * 60)
        print("✅ 脚本执行完成")
        
    except PermissionError as e:
        print("-" * 60)
        print(f"❌ 安全限制触发: {e}")
        sys.exit(1)
    except Exception as e:
        print("-" * 60)
        print(f"❌ 脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

