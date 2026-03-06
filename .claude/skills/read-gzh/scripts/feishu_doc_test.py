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
import re
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

    def create_and_move_to_folder(self, title: str, content: str, folder_token: str) -> Dict[str, Any]:
        """
        创建文档、写入内容、移动到文件夹（三步流程）

        使用 convert API 将 Markdown 转换为文档块

        Args:
            title: 文档标题
            content: Markdown 格式的内容
            folder_token: 目标文件夹的 token

        Returns:
            {
                "document_id": "xxx",
                "url": "https://xxx.feishu.cn/docx/xxx",
                "moved": True/False  # 是否成功移动到文件夹
            }
        """
        token = self.get_tenant_access_token()

        logger.info("=== 开始三步流程：创建 → 写入 → 移动 ===")

        # 步骤 1: 创建空白文档
        logger.info(f"步骤 1/3: 创建文档 '{title}'")
        create_url = f"{self.base_url}/docx/v1/documents"
        create_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        create_payload = {
            "title": title
        }

        try:
            response = requests.post(create_url, headers=create_headers, json=create_payload, timeout=10)
            result = response.json()

            if result.get("code") != 0:
                error_msg = f"创建文档失败: {result.get('msg', 'Unknown error')}"
                logger.error(error_msg)
                raise Exception(error_msg)

            document_id = result["data"]["document"]["document_id"]
            logger.info(f"✅ 步骤 1 完成: 文档 ID = {document_id}")

        except Exception as e:
            logger.error(f"步骤 1 失败: {e}")
            raise

        # 步骤 2: 使用 convert API 转换 Markdown 并写入
        logger.info("步骤 2/3: 转换 Markdown 内容")
        try:
            self._convert_and_write_content(document_id, content)
            logger.info("✅ 步骤 2 完成: 内容写入成功")
        except Exception as e:
            logger.error(f"步骤 2 失败: {e}")
            raise

        # 步骤 3: 移动到目标文件夹
        logger.info(f"步骤 3/3: 移动到文件夹 {folder_token}")
        # 修正 API 路径：使用正确的移动接口
        move_url = f"{self.base_url}/drive/v1/files/{document_id}/move"
        move_headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # 参考 API 文档的请求格式
        move_payload = {
            "type": "docx",
            "folder_token": folder_token
        }

        moved_successfully = False
        try:
            response = requests.post(move_url, headers=move_headers, json=move_payload, timeout=10)

            # 先打印响应状态和内容
            logger.info(f"移动 API 响应状态码: {response.status_code}")
            logger.info(f"移动 API 响应内容: {response.text}")

            result = response.json()

            if result.get("code") == 0:
                moved_successfully = True
                logger.info("✅ 步骤 3 完成: 文档已移动到目标文件夹")
            else:
                logger.warning(f"移动到文件夹失败: {result.get('msg', 'Unknown error')}")
                logger.warning(f"错误码: {result.get('code')}")

                # 移动失败时，删除根目录中的残留文件
                # 注意：document_id 和 token 可能不同，需要查询文件列表获取正确的 token
                logger.warning("正在删除根目录中的残留文档...")
                file_token = self._get_file_token_by_document_id(document_id, token)
                if file_token:
                    self._delete_document(file_token, token)

        except Exception as e:
            logger.warning(f"移动到文件夹异常: {e}")

            # 异常时，删除根目录中的残留文件
            # 注意：document_id 和 token 可能不同，需要查询文件列表获取正确的 token
            logger.warning("正在删除根目录中的残留文档...")
            file_token = self._get_file_token_by_document_id(document_id, token)
            if file_token:
                try:
                    self._delete_document(file_token, token)
                except Exception as delete_error:
                    logger.warning(f"删除残留文档失败: {delete_error}")
            else:
                logger.warning("无法找到文件 token，跳过删除")

        # 返回结果
        doc_url = f"https://vcwdkeb3m0i.feishu.cn/docx/{document_id}"
        logger.info(f"=== 三步流程完成 ===")
        logger.info(f"文档链接: {doc_url}")
        logger.info(f"移动状态: {'成功' if moved_successfully else '失败（已删除根目录残留）'}")

        return {
            "document_id": document_id,
            "url": doc_url,
            "moved": moved_successfully
        }

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
                "url": "https://xxx.feishu.cn/docx/xxx",
                "name": "文件名"
            }
        """
        import mimetypes

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

    def _delete_document(self, document_id: str, token: str):
        """
        删除文档

        Args:
            document_id: 文档 ID
            token: 访问令牌
        """
        delete_url = f"{self.base_url}/docx/v1/documents/{document_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.delete(delete_url, headers=headers, timeout=10)

            # 先打印响应
            logger.info(f"删除 API 响应状态码: {response.status_code}")
            logger.info(f"删除 API 响应内容: {response.text}")

            # 检查是否成功（某些删除操作返回 204 无内容）
            if response.status_code in [200, 204]:
                logger.info(f"✅ 成功删除根目录残留文档: {document_id}")
            else:
                # 尝试解析 JSON
                try:
                    result = response.json()
                    logger.warning(f"删除残留文档失败: {result.get('msg', 'Unknown error')}")
                except:
                    logger.warning(f"删除残留文档失败，状态码: {response.status_code}")

        except Exception as e:
            logger.warning(f"删除残留文档异常: {e}")
            # 不再抛出异常，避免影响主流程

    def _get_file_token_by_document_id(self, document_id: str, token: str) -> str:
        """
        根据 document_id 查询文件的 token

        Args:
            document_id: 文档 ID
            token: 访问令牌

        Returns:
            文件 token，如果找不到返回 None
        """
        list_url = f"{self.base_url}/drive/v1/files"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        params = {
            "page_size": 50,
            "type": "docx"
        }

        try:
            response = requests.get(list_url, headers=headers, params=params, timeout=10)
            result = response.json()

            if result.get("code") == 0:
                files = result.get("data", {}).get("files", [])
                # 查找匹配的文件（通过 document_id 或 URL）
                for file in files:
                    # 检查 URL 是否包含 document_id
                    file_url = file.get("url", "")
                    if document_id in file_url or file.get("token") == document_id:
                        file_token = file.get("token")
                        logger.info(f"找到文件 token: {file_token}")
                        return file_token

                logger.warning(f"无法根据 document_id {document_id} 找到文件 token")
                return None
            else:
                logger.warning(f"查询文件列表失败: {result.get('msg')}")
                return None
        except Exception as e:
            logger.warning(f"查询文件 token 异常: {e}")
            return None

    def _convert_and_write_content(self, document_id: str, markdown_content: str):
        """
        使用 convert API 将 Markdown 转换为文档块并写入

        流程：
        1. 调用 convert API 将 Markdown 转换为块结构
        2. 调用创建嵌套块 API 将块插入文档

        Args:
            document_id: 文档 ID
            markdown_content: Markdown 内容
        """
        logger.info("使用 convert API 转换 Markdown...")
        token = self.get_tenant_access_token()

        # 步骤 1: 调用 convert API 获取转换后的块结构
        convert_url = f"{self.base_url}/docx/v1/documents/blocks/convert"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        convert_payload = {
            "content_type": "markdown",
            "content": markdown_content
        }

        try:
            response = requests.post(convert_url, headers=headers, json=convert_payload, timeout=30)

            logger.info(f"Convert API 响应状态码: {response.status_code}")
            logger.info(f"Convert API 响应内容: {response.text[:500]}")

            # 检查响应状态
            if response.status_code != 200:
                logger.warning(f"Convert API 失败: 状态码 {response.status_code}, 响应: {response.text[:200]}")
                # 降级到手动写入方式
                self._write_markdown_content(document_id, markdown_content)
                return

            result = response.json()

            if result.get("code") != 0:
                logger.warning(f"Convert API 失败: {result.get('msg')}, 将使用手动写入方式")
                self._write_markdown_content(document_id, markdown_content)
                return

            # 获取转换后的块结构 - 正确的字段名是 "blocks"
            data = result.get("data", {})
            blocks = data.get("blocks", [])
            first_level_block_ids = data.get("first_level_block_ids", [])

            if not blocks:
                logger.warning("Convert API 返回空块, 将使用手动写入方式")
                self._write_markdown_content(document_id, markdown_content)
                return

            logger.info(f"✅ Markdown 转换成功, 获得 {len(blocks)} 个块")

            # 步骤 2: 调用创建嵌套块 API 插入块
            # 根据文档，需要使用 first_level_block_ids 来获取顶层块
            if first_level_block_ids:
                # 过滤出顶层块
                top_level_blocks = [b for b in blocks if b.get("block_id") in first_level_block_ids]
                logger.info(f"插入 {len(top_level_blocks)} 个顶层块")
                blocks_to_insert = top_level_blocks
            else:
                blocks_to_insert = blocks

            # 步骤 2: 调用创建嵌套块 API 插入块
            # 正确的 API 路径: /docx/v1/documents/{document_id}/blocks/{block_id}/descendant
            # 需要使用文档的根块作为父块 (block_id = document_id)
            insert_url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/descendant"
            insert_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }

            # 构建请求体 - 使用 children_id 和 descendants
            children_id = [b.get("block_id") for b in blocks_to_insert if b.get("block_id")]
            insert_payload = {
                "index": 0,
                "children_id": children_id,
                "descendants": blocks_to_insert
            }

            logger.info(f"插入块 payload: {insert_payload}")

            logger.info(f"插入块 payload: {insert_payload}")

            try:
                insert_response = requests.post(insert_url, headers=insert_headers, json=insert_payload, timeout=30)

                logger.info(f"插入块响应状态码: {insert_response.status_code}")
                logger.info(f"插入块响应内容: {insert_response.text[:500]}")

                insert_result = insert_response.json()

                if insert_result.get("code") != 0:
                    logger.warning(f"插入块失败: {insert_result.get('msg')}, 将使用手动写入方式")
                    self._write_markdown_content(document_id, markdown_content)
                    return

                logger.info("✅ 块插入成功")
            except Exception as insert_err:
                logger.warning(f"插入块异常: {insert_err}, 将使用手动写入方式")
                self._write_markdown_content(document_id, markdown_content)

        except Exception as e:
            logger.warning(f"Convert API 异常: {e}, 降级到手动写入方式")
            self._write_markdown_content(document_id, markdown_content)

    def _write_markdown_content(self, document_id: str, content: str):
        """
        将 Markdown 内容正确转换为飞书块结构并写入

        支持的 Markdown 语法：
        - 标题 (#, ##, ###)
        - 列表 (-, *)
        - 引用 (>)
        - 代码块 (```)
        - 表格 (|)
        - 强调 (**, *, ~~, `")
        - 链接 [text](url)
        - 图片 ![](url)
        - 分割线 (---)
        """
        logger.info("正在写入文档内容...")
        token = self.get_tenant_access_token()

        # 使用正确的 API：向根块添加子块
        url = f"{self.base_url}/docx/v1/documents/{document_id}/blocks/{document_id}/children"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # 解析 Markdown 并转换为飞书块结构
        lines = content.split('\n')
        children = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # 标题处理 - 使用加粗的文本块代替标题
            if line.startswith('# '):
                children.append(self._create_text_block(line[2:], bold=True))
                i += 1
            elif line.startswith('## '):
                children.append(self._create_text_block(line[3:], bold=True))
                i += 1
            elif line.startswith('### '):
                children.append(self._create_text_block(line[4:], bold=True))
                i += 1

            # 列表处理 - 使用多个文本块代替列表块
            elif line.startswith('- ') or line.startswith('* '):
                children.append(self._create_text_block(line))
                i += 1

            # 有序列表
            elif re.match(r'^\d+\. ', line):
                children.append(self._create_text_block(line))
                i += 1

            # 引用处理 - 使用文本块代替引用块
            elif line.startswith('> '):
                children.append(self._create_text_block(line))
                i += 1

            # 代码块处理 - 使用带样式的文本块代替代码块
            elif line.startswith('```'):
                lang = line[3:].strip()
                code_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith('```'):
                    code_lines.append(lines[j])
                    j += 1

                if j < len(lines):
                    code_content = '\n'.join(code_lines)
                    # 使用文本块代替代码块，并添加代码提示
                    lang_info = f"```{lang}\n" if lang else "```\n"
                    children.append(self._create_text_block(lang_info + code_content + "\n```"))
                    i = j + 1
                else:
                    # 未闭合的代码块，当作普通文本
                    children.append(self._create_text_block(line))
                    i += 1

            # 表格处理 - 暂时用文本块代替表格
            elif '|' in line and re.match(r'^\s*\|.*\|\s*$', line):
                # 表头
                if i + 1 < len(lines) and '|' in lines[i + 1] and re.match(r'^\s*\|[-:]+\|.*\|\s*$', lines[i + 1]):
                    table_headers = [cell.strip() for cell in line.split('|')[1:-1]]
                    separator = lines[i + 1]
                    table_rows = []
                    k = i + 2
                    while k < len(lines) and '|' in lines[k] and re.match(r'^\s*\|.*\|\s*$', lines[k]):
                        cells = [cell.strip() for cell in lines[k].split('|')[1:-1]]
                        table_rows.append(cells)
                        k += 1

                    # 将表格转换为文本块
                    table_text = "\n".join(
                        [" | ".join(row) for row in [table_headers] + table_rows]
                    )
                    children.append(self._create_text_block(table_text))
                    i = k
                else:
                    children.append(self._create_text_block(line))
                    i += 1

            # 分割线 - 使用文本块代替
            elif re.match(r'^\s*[-*]{3,}\s*$', line):
                children.append(self._create_text_block("---"))
                i += 1

            # 普通文本行（跳过空行）
            elif line.strip() != "":
                # 收集连续的非空行作为段落
                paragraph_lines = []
                j = i
                while j < len(lines) and lines[j].strip() != "":
                    paragraph_lines.append(lines[j])
                    j += 1

                # 创建段落块
                paragraph_content = '\n'.join(paragraph_lines)
                children.append(self._create_text_block(paragraph_content))

                i = j
            else:
                # 空行，跳过
                i += 1

        # 逐个写入块（避免批量写入的问题）
        total_blocks = len(children)
        for idx, child in enumerate(children):
            payload = {
                "children": [child],
                "index": -1  # 每次都追加到最后
            }

            # 调试：打印部分 payload
            if idx == 0:
                logger.info(f"准备写入 {total_blocks} 个块")
                logger.info(f"第一个块: {child}")

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                result = response.json()

                if result.get("code") != 0:
                    logger.warning(f"写入块 {idx + 1}/{total_blocks} 失败: {result.get('msg', 'Unknown error')}")
                    logger.warning(f"错误码: {result.get('code')}")
                    # 不中断，继续写入后续块
                else:
                    if (idx + 1) % 10 == 0 or idx == total_blocks - 1:
                        logger.info(f"已写入 {idx + 1}/{total_blocks} 个块")
            except Exception as e:
                logger.warning(f"写入块 {idx + 1}/{total_blocks} 异常: {e}")

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

    def create_document_simple(self, title: str, content: str, folder_token: str = None) -> str:
        """
        简化接口：创建文档并返回链接

        使用三步流程（创建 → 写入 → 移动）

        Args:
            title: 文档标题
            content: Markdown 内容
            folder_token: 目标文件夹 token（可选）

        Returns:
            文档链接
        """
        try:
            # 如果没有提供 folder_token，从环境变量读取
            if not folder_token:
                folder_token = os.getenv("FEISHU_DOC_FOLDER_TOKEN")

            # 必须提供 folder_token
            if not folder_token:
                raise Exception("需要提供 folder_token 参数或设置 FEISHU_DOC_FOLDER_TOKEN 环境变量")

            logger.info(f"使用三步流程创建文档到文件夹: {folder_token}")
            result = self.create_and_move_to_folder(title, content, folder_token)
            return result["url"]
        except Exception as e:
            logger.error(f"创建文档失败: {e}")
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
    import tempfile

    client = FeishuDocClient()
    folder_token = os.getenv("FEISHU_DOC_FOLDER_TOKEN")

    if not folder_token:
        raise Exception("需要设置 FEISHU_DOC_FOLDER_TOKEN 环境变量")

    # 获取日期前缀
    from datetime import datetime
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
    # 测试连接
    test_connection()

    # 示例：创建文档
    # client = FeishuDocClient()
    # url = client.create_document_simple(
    #     title="测试文档",
    #     content="# 测试\n\n这是一段测试内容"
    # )
    # print(f"文档链接: {url}")