"""
文件上传服务
- 上传文件到Gemini API
- OpenAI file_id <-> Gemini fileId 映射
"""
import asyncio
import base64
import uuid
import time
import logging
import mimetypes
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

import httpx

from app.services.jwt_service import get_http_client

logger = logging.getLogger(__name__)

# API endpoint
ADD_CONTEXT_FILE_URL = "https://biz-discoveryengine.googleapis.com/v1alpha/locations/global/widgetAddContextFile"


def get_upload_headers(jwt: str) -> dict:
    """获取上传请求头"""
    return {
        "accept": "*/*",
        "authorization": f"Bearer {jwt}",
        "content-type": "application/json",
        "origin": "https://business.gemini.google",
        "referer": "https://business.gemini.google/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


@dataclass
class FileMapping:
    """文件映射信息"""
    openai_file_id: str
    gemini_file_id: str
    session_name: str
    filename: str
    mime_type: str
    size: int
    created_at: float = field(default_factory=time.time)
    # 缓存文件内容，用于在session不匹配时重新上传
    file_content: Optional[bytes] = None

    def to_dict(self) -> dict:
        return {
            "id": self.openai_file_id,
            "gemini_file_id": self.gemini_file_id,
            "session_name": self.session_name,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "bytes": self.size,
            "created_at": int(self.created_at),
            "object": "file",
            "purpose": "assistants"
        }


class FileUploadService:
    """
    文件上传服务

    功能：
    1. 上传文件到Gemini API
    2. 维护OpenAI file_id <-> Gemini fileId映射
    3. 支持多种文件类型
    """

    def __init__(self):
        self._mappings: Dict[str, FileMapping] = {}  # openai_file_id -> FileMapping
        self._lock = asyncio.Lock()

    async def upload_to_gemini(
        self,
        jwt: str,
        session_name: str,
        team_id: str,
        file_content: bytes,
        filename: str,
        mime_type: str
    ) -> str:
        """
        上传文件到Gemini API

        Args:
            jwt: JWT令牌
            session_name: Gemini会话名称
            team_id: 团队ID
            file_content: 文件内容
            filename: 文件名
            mime_type: MIME类型

        Returns:
            gemini_file_id: Gemini返回的文件ID
        """
        client = await get_http_client()

        # Base64编码文件内容
        file_b64 = base64.b64encode(file_content).decode('utf-8')

        body = {
            "addContextFileRequest": {
                "fileContents": file_b64,
                "fileName": filename,
                "mimeType": mime_type,
                "name": session_name
            },
            "additionalParams": {"token": "-"},
            "configId": team_id
        }

        logger.debug(f"上传文件到Gemini: {filename}, 大小: {len(file_content)} bytes")

        try:
            response = await client.post(
                ADD_CONTEXT_FILE_URL,
                headers=get_upload_headers(jwt),
                json=body,
                timeout=60.0
            )
        except httpx.RequestError as e:
            raise Exception(f"文件上传请求失败: {e}")

        if response.status_code == 401:
            raise Exception("文件上传认证失败")
        elif response.status_code == 429:
            raise Exception("文件上传触发限额")
        elif response.status_code != 200:
            raise Exception(f"文件上传失败: {response.status_code} - {response.text[:200]}")

        data = response.json()
        gemini_file_id = data.get("addContextFileResponse", {}).get("fileId")

        if not gemini_file_id:
            raise Exception(f"响应中没有fileId: {data}")

        logger.info(f"文件上传成功: {filename} -> {gemini_file_id}")
        return gemini_file_id

    async def upload_and_map(
        self,
        jwt: str,
        session_name: str,
        team_id: str,
        file_content: bytes,
        filename: str,
        mime_type: str,
        cache_content: bool = True
    ) -> FileMapping:
        """
        上传文件并创建映射

        Args:
            cache_content: 是否缓存文件内容（用于session不匹配时重新上传）

        Returns:
            FileMapping: 文件映射信息
        """
        # 上传到Gemini
        gemini_file_id = await self.upload_to_gemini(
            jwt, session_name, team_id, file_content, filename, mime_type
        )

        # 生成OpenAI格式的file_id
        openai_file_id = f"file-{uuid.uuid4().hex[:24]}"

        # 创建映射（可选缓存文件内容）
        mapping = FileMapping(
            openai_file_id=openai_file_id,
            gemini_file_id=gemini_file_id,
            session_name=session_name,
            filename=filename,
            mime_type=mime_type,
            size=len(file_content),
            file_content=file_content if cache_content else None
        )

        async with self._lock:
            self._mappings[openai_file_id] = mapping

        return mapping

    async def reupload_to_session(
        self,
        openai_file_id: str,
        jwt: str,
        new_session_name: str,
        team_id: str
    ) -> Optional[str]:
        """
        将文件重新上传到新的session

        当文件的原session与当前会话session不匹配时使用

        Args:
            openai_file_id: OpenAI格式的文件ID
            jwt: JWT令牌
            new_session_name: 新的session名称
            team_id: 团队ID

        Returns:
            新的gemini_file_id，如果失败返回None
        """
        mapping = self._mappings.get(openai_file_id)
        if not mapping:
            logger.warning(f"找不到文件映射: {openai_file_id}")
            return None

        if not mapping.file_content:
            logger.warning(f"文件内容未缓存，无法重新上传: {openai_file_id}")
            return None

        try:
            # 上传到新session
            new_gemini_file_id = await self.upload_to_gemini(
                jwt=jwt,
                session_name=new_session_name,
                team_id=team_id,
                file_content=mapping.file_content,
                filename=mapping.filename,
                mime_type=mapping.mime_type
            )

            # 更新映射
            async with self._lock:
                mapping.gemini_file_id = new_gemini_file_id
                mapping.session_name = new_session_name

            logger.info(f"文件重新上传成功: {openai_file_id} -> {new_gemini_file_id} (session: {new_session_name})")
            return new_gemini_file_id

        except Exception as e:
            logger.error(f"文件重新上传失败: {e}")
            return None

    def get_mapping(self, openai_file_id: str) -> Optional[FileMapping]:
        """获取文件映射"""
        return self._mappings.get(openai_file_id)

    def get_gemini_file_id(self, openai_file_id: str) -> Optional[str]:
        """通过OpenAI file_id获取Gemini fileId"""
        mapping = self._mappings.get(openai_file_id)
        return mapping.gemini_file_id if mapping else None

    def get_session_for_file(self, openai_file_id: str) -> Optional[str]:
        """获取文件关联的会话名称"""
        mapping = self._mappings.get(openai_file_id)
        return mapping.session_name if mapping else None

    def list_files(self) -> List[dict]:
        """列出所有文件"""
        return [m.to_dict() for m in self._mappings.values()]

    def delete_file(self, openai_file_id: str) -> bool:
        """删除文件映射"""
        if openai_file_id in self._mappings:
            del self._mappings[openai_file_id]
            return True
        return False

    def cleanup_expired(self, max_age_seconds: int = 86400):
        """清理过期的文件映射"""
        now = time.time()
        expired = [
            fid for fid, m in self._mappings.items()
            if now - m.created_at > max_age_seconds
        ]
        for fid in expired:
            del self._mappings[fid]

        if expired:
            logger.info(f"清理了 {len(expired)} 个过期文件映射")


async def upload_inline_image(
    jwt: str,
    session_name: str,
    team_id: str,
    image_data: dict
) -> Optional[str]:
    """
    上传内联图片到Gemini

    支持的格式：
    - {"type": "base64", "mime_type": "image/png", "data": "..."}
    - {"type": "url", "url": "https://..."}

    Args:
        jwt: JWT令牌
        session_name: 会话名称
        team_id: 团队ID
        image_data: 图片数据

    Returns:
        gemini_file_id: 上传成功返回Gemini文件ID，失败返回None
    """
    ext_map = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp"
    }

    try:
        if image_data.get("type") == "base64":
            mime_type = image_data.get("mime_type", "image/png")
            file_content = base64.b64decode(image_data.get("data", ""))
            ext = ext_map.get(mime_type, ".png")
            filename = f"inline_{uuid.uuid4().hex[:8]}{ext}"

        elif image_data.get("type") == "url":
            # 下载URL图片
            url = image_data.get("url", "")
            if not url:
                return None

            client = await get_http_client()
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()

            file_content = response.content
            content_type = response.headers.get("Content-Type", "image/png")
            mime_type = content_type.split(";")[0].strip()
            ext = ext_map.get(mime_type, ".png")
            filename = f"url_{uuid.uuid4().hex[:8]}{ext}"
        else:
            return None

        # 上传到Gemini
        gemini_file_id = await file_upload_service.upload_to_gemini(
            jwt, session_name, team_id, file_content, filename, mime_type
        )
        return gemini_file_id

    except Exception as e:
        logger.error(f"上传内联图片失败: {e}")
        return None


def parse_base64_data_url(data_url: str) -> Optional[dict]:
    """
    解析base64 data URL

    格式: data:image/png;base64,xxxxx

    Returns:
        {"type": "base64", "mime_type": "image/png", "data": "..."} 或 None
    """
    if not data_url or not data_url.startswith("data:"):
        return None

    import re
    match = re.match(r"data:([^;]+);base64,(.+)", data_url)
    if match:
        return {
            "type": "base64",
            "mime_type": match.group(1),
            "data": match.group(2)
        }
    return None


def extract_images_from_openai_content(content) -> Tuple[str, List[dict]]:
    """
    从OpenAI格式的content中提取文本和图片

    支持的格式：
    1. 纯文本: "Hello"
    2. 数组格式: [{"type": "text", "text": "..."}, {"type": "image_url", "image_url": {"url": "..."}}]

    Returns:
        (text, images): 文本内容和图片列表
    """
    if isinstance(content, str):
        return content, []

    if not isinstance(content, list):
        return str(content), []

    text_parts = []
    images = []

    for item in content:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type", "")

        if item_type == "text":
            text_parts.append(item.get("text", ""))

        elif item_type == "image_url":
            image_url_obj = item.get("image_url", {})
            if isinstance(image_url_obj, str):
                url = image_url_obj
            else:
                url = image_url_obj.get("url", "")

            # 尝试解析base64 data URL
            parsed = parse_base64_data_url(url)
            if parsed:
                images.append(parsed)
            elif url:
                # 普通URL
                images.append({
                    "type": "url",
                    "url": url
                })

        # 支持直接的image类型
        elif item_type == "image" and item.get("data"):
            parsed = parse_base64_data_url(item.get("data"))
            if parsed:
                images.append(parsed)

    return "\n".join(text_parts), images


def extract_file_ids_from_content(content) -> List[str]:
    """
    从OpenAI格式的content中提取file_id

    支持的格式：
    1. {"type": "file", "file_id": "xxx"}
    2. {"type": "file", "file": {"file_id": "xxx"}}
    3. {"type": "file", "file": {"id": "xxx"}}

    Returns:
        file_ids: 文件ID列表
    """
    if not isinstance(content, list):
        return []

    file_ids = []

    for item in content:
        if not isinstance(item, dict):
            continue

        if item.get("type") != "file":
            continue

        # 格式1: {"type": "file", "file_id": "xxx"}
        if item.get("file_id"):
            file_ids.append(item["file_id"])
            continue

        # 格式2/3: {"type": "file", "file": {...}}
        file_obj = item.get("file")
        if isinstance(file_obj, dict):
            fid = file_obj.get("file_id") or file_obj.get("id")
            if fid:
                file_ids.append(fid)

    return file_ids


# 全局文件上传服务实例
file_upload_service = FileUploadService()
