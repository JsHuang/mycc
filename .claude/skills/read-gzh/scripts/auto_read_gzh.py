#!/usr/bin/env python3
"""
read-gzh 自动化脚本
整合：抓取文章 → AI 总结 → 上传飞书云盘
"""

import sys
import io
import subprocess
import os
import datetime
from typing import Dict, Any, Optional

# 设置UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加 scripts 目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from feishu_doc import upload_summary, FeishuDocClient


def fetch_article(url: str) -> Dict[str, Optional[str]]:
    """
    抓取公众号文章

    Returns:
        {
            "title": "文章标题",
            "author": "作者",
            "content": "正文内容",
            "error": None
        }
    """
    print(f"\n📖 正在抓取文章...")
    result = subprocess.run(
        [sys.executable, "fetch_wechat_article.py", url],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        return {"error": f"抓取失败: {result.stderr}"}

    # 解析输出
    output = result.stdout
    title = None
    author = None
    content = None

    for line in output.split('\n'):
        if line.startswith('【标题】'):
            title = line.replace('【标题】', '').strip()
        elif line.startswith('【作者】'):
            author = line.replace('【作者】', '').strip()

    # 正文内容在正文之后
    if '【正文】' in output:
        content = output.split('【正文】', 1)[1].split('==================================================', 1)[0].strip()

    return {
        "title": title,
        "author": author,
        "content": content,
        "error": None
    }


def check_feishu_config() -> bool:
    """检查飞书配置是否完整"""
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_DOC_FOLDER_TOKEN']
    missing = [v for v in required_vars if not os.getenv(v)]

    if missing:
        print(f"⚠️  缺少飞书配置: {', '.join(missing)}")
        print(f"   上传步骤将被跳过")
        return False

    return True


def main(url: Optional[str] = None):
    """主函数"""
    if not url:
        print("❌ 请提供公众号链接")
        print("用法: python3 auto_read_gzh.py <公众号链接>")
        sys.exit(1)

    print(f"🚀 开始处理: {url}")

    # Step 1: 抓取文章
    article = fetch_article(url)

    if article["error"]:
        print(f"❌ {article['error']}")
        sys.exit(1)

    title = article["title"]
    author = article["author"]
    content = article["content"]

    print(f"📝 标题: {title}")
    print(f"✍️  作者: {author}")
    print(f"📄 正文长度: {len(content)} 字符")

    # Step 2: 生成总结 - 这里需要 AI 参与
    # 在 skill 调用中，AI 会基于抓取的内容生成总结
    # 然后调用本脚本的上传部分

    # Step 3: 上传到飞书（可选）
    if os.getenv("FEISHU_SAVE_TO_DOC") == "true" and check_feishu_config():
        # 等待 AI 总结生成
        print(f"\n💾 等待 AI 生成总结...")
        print(f"   AI 请生成总结后调用 upload_to_feishu() 函数")


def upload_to_feishu(title: str, summary_content: str) -> Dict[str, Any]:
    """
    上传总结到飞书云盘
    AI 生成总结后调用此函数

    Args:
        title: 文章标题
        summary_content: AI 生成的总结内容

    Returns:
        {
            "file_token": "xxx",
            "url": "https://xxx.feishu.cn/file/xxx",
            "name": "文件名"
        }
    """
    print(f"\n📤 正在上传到飞书云盘...")

    try:
        result = upload_summary(title=title, content=summary_content)
        print(f"✅ 上传成功!")
        print(f"   文件名: {result['name']}")
        print(f"   链接: {result['url']}")
        return result
    except Exception as e:
        print(f"❌ 上传失败: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        main()
    else:
        url = sys.argv[1]
        # 检查是否是上传模式（第二个参数是总结内容文件）
        if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
            # 上传模式
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                summary_content = f.read()
            upload_to_feishu(title=sys.argv[3], summary_content=summary_content)
        else:
            # 完整模式
            main(url)
