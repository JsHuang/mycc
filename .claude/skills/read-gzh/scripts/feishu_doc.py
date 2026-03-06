#!/usr/bin/env python3
"""
飞书云文档 API 封装 - 简版

功能：
- 上传 Markdown 文件到云盘文件夹

依赖环境变量：
- FEISHU_APP_ID: 飞书应用 ID
- FEISHU_APP_SECRET: 飞书应用密钥
- FEISHU_DOC_FOLDER_TOKEN: 云盘文件夹 token
"""

import os
import tempfile
import requests
import logging
from datetime import datetime
from typing import Dict, Any

# 自动加载 .env 文件
from dotenv import load_dotenv
load_dotenv()  # 默认从当前目录查找 .env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FeishuDocClient:
    """飞书云文档客户端"""

    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or os.getenv("FEISHU_APP_ID")
        self.app_secret = app_secret or os.getenv("FEISHU_APP_SECRET")
        self.tenant_access_token = None
        self.base_url = "https://open.feishu.cn/open-apis"

    def get_tenant_access_token(self) -> str:
        """获取 tenant_access_token"""
        if self.tenant_access_token:
            return self.tenant_access_token

        logger.info("正在获取飞书访问令牌...")
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()

            if result.get("code") != 0:
                error_msg = f"获取 token 失败: {result.get('msg', 'Unknown error')}"
                logger.error(error_msg)
                raise Exception(error_msg)

            self.tenant_access_token = result["tenant_access_token"]
            logger.info("✅ 成功获取访问令牌")
            return self.tenant_access_token

        except requests.exceptions.Timeout:
            error_msg = "获取访问令牌超时"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def upload_md_to_folder(self, md_path: str, folder_token: str, file_name: str = None) -> Dict[str, Any]:
        """
        上传 Markdown 文件到指定文件夹

        Args:
            md_path: Markdown 文件路径
            folder_token: 目标文件夹的 token
            file_name: （可选）文件名，默认使用原文件名

        Returns:
            {
                "file_token": "xxx",
                "url": "https://xxx.feishu.cn/file/xxx",
                "name": "文件名"
            }
        """
        token = self.get_tenant_access_token()

        # 获取文件名
        if not file_name:
            file_name = os.path.basename(md_path)

        # 获取文件大小
        with open(md_path, 'rb') as f:
            file_content = f.read()
            file_size = len(file_content)

        logger.info(f"上传文件: {file_name} ({file_size} bytes) 到文件夹: {folder_token}")

        # 调用上传 API
        url = f"{self.base_url}/drive/v1/files/upload_all"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        # 构建文件上传请求
        files = {
            "file": (file_name, open(md_path, "rb"), "text/markdown"),
            "file_name": (None, file_name),
            "parent_type": (None, "explorer"),
            "parent_node": (None, folder_token),
            "size": (None, str(file_size))
        }

        try:
            response = requests.post(url, headers=headers, files=files, timeout=60)
            result = response.json()

            if result.get("code") != 0:
                error_msg = f"上传文件失败: {result.get('msg', 'Unknown error')}"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 获取 file_token 并构造链接
            file_token = result.get("data", {}).get("file_token")
            # markdown 文件上传后是云盘文件，链接格式
            file_url = f"https://hcnchcidr5jg.feishu.cn/file/{file_token}"

            logger.info(f"✅ 文件上传成功: {file_name}")
            logger.info(f"文件 token: {file_token}")
            logger.info(f"文件链接: {file_url}")

            return {
                "file_token": file_token,
                "url": file_url,
                "name": file_name
            }

        except Exception as e:
            logger.error(f"上传文件异常: {e}")
            raise


def upload_summary(title: str, content: str) -> Dict[str, Any]:
    """
    上传 AI 总结到飞书云盘

    Args:
        title: 文档标题（不含 .md 后缀）
        content: Markdown 内容

    Returns:
        {
            "file_token": "xxx",
            "url": "https://xxx.feishu.cn/file/xxx",
            "name": "文件名"
        }
    """
    client = FeishuDocClient()
    folder_token = os.getenv("FEISHU_DOC_FOLDER_TOKEN")

    if not folder_token:
        raise Exception("需要设置 FEISHU_DOC_FOLDER_TOKEN 环境变量")

    # 获取日期前缀
    date_prefix = datetime.now().strftime("%Y-%m-%d")

    # 清理标题中的非法字符，添加日期前缀
    safe_title = "".join(c for c in title if c not in r'<>:"/\|?*')
    file_name = f"{date_prefix}-{safe_title}.md"

    # 保存内容到临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name

    try:
        # 上传文件
        result = client.upload_md_to_folder(
            md_path=temp_path,
            folder_token=folder_token,
            file_name=file_name
        )
        logger.info(f"✅ 上传成功: {result['url']}")

        return {
            "file_token": result.get("file_token"),
            "url": result.get("url"),
            "name": result.get("name")
        }

    finally:
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_connection():
    """测试飞书 API 连接"""
    client = FeishuDocClient()
    try:
        token = client.get_tenant_access_token()
        logger.info(f"✅ 连接成功，token: {token[:20]}...")
        return True
    except Exception as e:
        logger.error(f"❌ 连接失败: {e}")
        return False


if __name__ == "__main__":
    test_connection()
