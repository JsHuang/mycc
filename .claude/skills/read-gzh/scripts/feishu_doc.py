#!/usr/bin/env python3
"""
飞书云文档 API 封装

功能：
- 创建云文档
- 写入 Markdown 内容
- 获取文档链接

依赖环境变量：
- FEISHU_APP_ID: 飞书应用 ID
- FEISHU_APP_SECRET: 飞书应用密钥
- FEISHU_DOC_SPACE_ID: （可选）知识库文件夹 token
"""

import os
import json
import requests
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 尝试从项目根目录加载 .env
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # 如果没有安装 python-dotenv，跳过


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

    def create_wiki_document(self, title: str, content: str, space_id: str) -> Dict[str, Any]:
        """
        在知识库中创建文档

        Args:
            title: 文档标题
            content: Markdown 格式的内容
            space_id: 知识空间 ID（数字格式）

        Returns:
            {
                "document_id": "xxx",
                "node_token": "xxx",
                "url": "https://xxx.feishu.cn/wiki/xxx"
            }
        """
        token = self.get_tenant_access_token()

        logger.info(f"正在知识库中创建文档: {title}")
        logger.info(f"知识空间 ID: {space_id}")

        # 使用知识库 API 创建文档节点
        url = f"{self.base_url}/wiki/v2/spaces/{space_id}/nodes"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "node_type": "origin",  # origin 表示创建新文档
            "obj_type": "docx",     # 文档类型
            "title": title
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            result = response.json()

            if result.get("code") != 0:
                error_msg = f"在知识库创建文档失败: {result.get('msg', 'Unknown error')}"
                logger.warning(error_msg)
                return None

            node = result.get('data', {}).get('node', {})
            node_token = node.get('node_token')
            obj_token = node.get('obj_token')  # 文档的实际 token

            logger.info(f"✅ 成功在知识库创建文档")
            logger.info(f"节点 token: {node_token}")

            # 写入文档内容
            if obj_token:
                self._write_markdown_content(obj_token, content)

            # 返回文档链接
            url = f"https://hcnchcidr5jg.feishu.cn/wiki/{node_token}"
            logger.info(f"文档链接: {url}")

            return {
                "document_id": obj_token,
                "node_token": node_token,
                "url": url
            }

        except requests.exceptions.Timeout:
            logger.warning("在知识库创建文档超时")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"在知识库创建文档失败: {e}")
            return None

    def create_document(self, title: str, content: str, space_id: str = None) -> Dict[str, Any]:
        """
        创建云文档
        优先尝试在知识库中创建，失败则降级到云文档

        Args:
            title: 文档标题
            content: Markdown 格式的内容
            space_id: 知识空间 ID（数字）或知识库文件夹 token（可选）

        Returns:
            {
                "document_id": "xxx",
                "url": "https://xxx.feishu.cn/wiki/xxx" 或 "https://xxx.feishu.cn/docx/xxx"
            }
        """
        # 如果没有传入 space_id，从环境变量读取
        if not space_id:
            space_id = os.getenv("FEISHU_DOC_SPACE_ID")

        # 如果 space_id 是纯数字，使用知识库 API
        if space_id and space_id.isdigit() and len(space_id) >= 5:
            logger.info(f"检测到知识空间 ID，使用知识库 API")
            result = self.create_wiki_document(title, content, space_id)
            if result:
                return result
            else:
                logger.warning("知识库创建失败，降级使用云文档")

        # 使用云文档 API
        token = self.get_tenant_access_token()

        logger.info(f"正在创建云文档: {title}")
        url = f"{self.base_url}/docx/v1/documents"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "title": title
        }

        # 如果提供了文件夹 token，使用它
        if space_id and not space_id.isdigit():
            payload["folder_token"] = space_id
            logger.info(f"尝试使用云文件夹: {space_id}")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            result = response.json()

            if result.get("code") != 0:
                # 如果使用文件夹 ID 失败，尝试不使用文件夹 ID 创建
                if space_id and result.get("code") in [1770039, 1770040]:  # folder not found / no permission
                    logger.warning(f"云文件夹不可用，将在默认位置创建文档")
                    payload.pop("folder_token")
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    result = response.json()

                if result.get("code") != 0:
                    error_msg = f"创建文档失败: {result.get('msg', 'Unknown error')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

            # 飞书 API 返回结构: {code: 0, data: {document: {...}}}
            if "data" not in result or "document" not in result["data"]:
                error_msg = f"响应格式不正确: {result}"
                logger.error(error_msg)
                raise Exception(error_msg)

            document = result["data"]["document"]
            document_id = document["document_id"]
            logger.info(f"✅ 成功创建文档，ID: {document_id}")

            # 写入文档内容
            self._write_markdown_content(document_id, content)

            # 返回文档链接
            url = f"https://vcwdkeb3m0i.feishu.cn/docx/{document_id}"
            logger.info(f"文档链接: {url}")
            return {
                "document_id": document_id,
                "url": url
            }

        except requests.exceptions.Timeout:
            error_msg = "创建文档请求超时"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def _write_markdown_content(self, document_id: str, content: str):
        """
        将 Markdown 内容写入文档

        注意：飞书 API 限制较多，这里使用简化的文本块方式
        标题等格式会在文本中以加粗显示
        """
        logger.info("正在写入文档内容...")
        token = self.get_tenant_access_token()

        # 使用正确的 API：向根块添加子块
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 处理 Markdown 内容，转换为飞书文本块
        lines = content.split('\n')
        children = []
        current_text = []

        for line in lines:
            # 标题转换：加粗显示
            if line.startswith('# '):
                if current_text:
                    # 先保存之前的文本
                    children.append(self._create_text_block('\n'.join(current_text)))
                    current_text = []
                # 添加加粗标题
                children.append(self._create_text_block(line[2:], bold=True))
            elif line.startswith('## '):
                if current_text:
                    children.append(self._create_text_block('\n'.join(current_text)))
                    current_text = []
                children.append(self._create_text_block(line[3:], bold=True))
            elif line.startswith('### '):
                if current_text:
                    children.append(self._create_text_block('\n'.join(current_text)))
                    current_text = []
                children.append(self._create_text_block(line[4:], bold=True))
            # 空行分隔段落
            elif line.strip() == '':
                if current_text:
                    children.append(self._create_text_block('\n'.join(current_text)))
                    current_text = []
            else:
                current_text.append(line)

        # 添加最后的文本
        if current_text:
            children.append(self._create_text_block('\n'.join(current_text)))

        logger.info(f"共生成 {len(children)} 个文本块")

        # 分批写入（飞书 API 限制每次请求的块数量和大小）
        batch_size = 50  # 每批最多50个块
        success_count = 0
        error_count = 0

        for i in range(0, len(children), batch_size):
            batch = children[i:i+batch_size]
            payload = {
                "children": batch,
                "index": i // batch_size
            }

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                result = response.json()

                if result.get("code") != 0:
                    error_msg = f"写入内容失败: {result.get('msg', 'Unknown error')}"
                    logger.warning(error_msg)
                    logger.debug(f"错误码: {result.get('code')}")
                    error_count += 1
                else:
                    success_count += 1
            except requests.exceptions.Timeout:
                logger.warning(f"写入第 {i//batch_size + 1} 批内容超时")
                error_count += 1
            except requests.exceptions.RequestException as e:
                logger.warning(f"写入第 {i//batch_size + 1} 批内容失败: {e}")
                error_count += 1

        if error_count == 0:
            logger.info(f"✅ 内容写入成功，共 {len(children)} 个文本块")
        else:
            logger.warning(f"⚠️  内容写入完成，成功 {success_count} 批，失败 {error_count} 批")

    def _create_text_block(self, text: str, bold: bool = False) -> dict:
        """
        创建文本块

        Args:
            text: 文本内容
            bold: 是否加粗

        Returns:
            飞书文本块结构
        """
        return {
            "block_type": 2,  # text block
            "text": {
                "elements": [
                    {
                        "text_run": {
                            "content": text,
                            "text_element_style": {
                                "bold": bold,
                                "inline_code": False,
                                "italic": False,
                                "strikethrough": False,
                                "underline": False
                            }
                        }
                    }
                ]
            }
        }

    def create_document_simple(self, title: str, content: str) -> str:
        """
        简化接口：创建文档并返回链接

        Args:
            title: 文档标题
            content: Markdown 内容

        Returns:
            文档链接
        """
        try:
            result = self.create_document(title, content)
            return result["url"]
        except Exception as e:
            logger.error(f"创建文档失败: {e}")
            raise


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
    # 测试连接
    test_connection()

    # 示例：创建文档
    # client = FeishuDocClient()
    # url = client.create_document_simple(
    #     title="测试文档",
    #     content="# 测试\n\n这是一段测试内容"
    # )
    # print(f"文档链接: {url}")
