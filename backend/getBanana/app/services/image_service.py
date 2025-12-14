"""
图片服务
- 图片下载
- 图片保存（按会话目录）
- 图片缓存管理
"""
import asyncio
import base64
import hashlib
import logging
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, List

import httpx

from app.config import config_manager, IMAGES_DIR
from app.models.chat import ChatImage
from app.services.jwt_service import get_http_client

logger = logging.getLogger(__name__)

# API URLs
DOWNLOAD_BASE_URL = "https://biz-discoveryengine.googleapis.com/v1alpha"
LIST_FILE_METADATA_URL = "https://biz-discoveryengine.googleapis.com/v1alpha/locations/global/widgetListSessionFileMetadata"


def build_download_url(session_name: str, file_id: str) -> str:
    """构建图片下载URL"""
    return f"{DOWNLOAD_BASE_URL}/{session_name}:downloadFile?fileId={file_id}&alt=media"


def get_download_headers(jwt: str) -> dict:
    """获取下载请求头"""
    return {
        "accept": "*/*",
        "authorization": f"Bearer {jwt}",
        "origin": "https://business.gemini.google",
        "referer": "https://business.gemini.google/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


class ImageService:
    """
    图片服务

    功能：
    1. 从 Gemini API 下载图片
    2. 按会话目录保存图片
    3. 图片缓存管理
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._cache: Dict[str, ChatImage] = {}  # file_id -> ChatImage
        self._cache_expiry: Dict[str, float] = {}  # file_id -> expiry_time

    async def download_and_save(
        self,
        jwt: str,
        session_name: str,
        file_id: str,
        mime_type: str,
        conversation_id: str,
        team_id: str = None,
        file_name: Optional[str] = None
    ) -> Optional[ChatImage]:
        """
        下载并保存图片

        Args:
            jwt: JWT令牌
            session_name: Gemini会话名称
            file_id: 文件ID
            mime_type: MIME类型
            conversation_id: 会话ID（用于确定保存目录）
            team_id: 团队ID（用于获取文件元数据）
            file_name: 文件名（可选）

        Returns:
            ChatImage: 图片对象
        """
        # 检查缓存
        cache_key = f"{session_name}:{file_id}"
        if cache_key in self._cache:
            if self._cache_expiry.get(cache_key, 0) > time.time():
                return self._cache[cache_key]

        # 尝试获取文件元数据以确定正确的session
        actual_session = session_name
        if team_id:
            logger.info(f"获取文件元数据: session={session_name}, team_id={team_id}")
            file_metadata = await self._get_session_file_metadata(jwt, session_name, team_id)
            logger.info(f"获取到 {len(file_metadata)} 个文件元数据")
            if file_id in file_metadata:
                meta = file_metadata[file_id]
                actual_session = meta.get("session", session_name)
                file_name = file_name or meta.get("name")
                logger.debug(f"从元数据获取session: {actual_session}")

        # 下载图片
        image_data = await self._download_image(jwt, actual_session, file_id)
        if not image_data:
            return None

        # 保存到会话目录
        saved_path = await self._save_to_conversation_dir(
            image_data,
            mime_type,
            conversation_id,
            file_name
        )

        # 创建ChatImage对象
        b64_data = base64.b64encode(image_data).decode()
        image = ChatImage(
            base64_data=b64_data,
            mime_type=mime_type,
            file_name=saved_path.name if saved_path else None,
            file_path=str(saved_path) if saved_path else None
        )

        # 缓存
        async with self._lock:
            self._cache[cache_key] = image
            self._cache_expiry[cache_key] = time.time() + 3600  # 1小时缓存

        return image

    async def _get_session_file_metadata(
        self,
        jwt: str,
        session_name: str,
        team_id: str
    ) -> Dict[str, dict]:
        """
        获取会话中的文件元数据（AI生成的图片）

        Returns:
            Dict[str, dict]: fileId -> metadata 的映射
        """
        client = await get_http_client()

        body = {
            "configId": team_id,
            "additionalParams": {"token": "-"},
            "listSessionFileMetadataRequest": {
                "name": session_name,
                "filter": "file_origin_type = AI_GENERATED"
            }
        }

        headers = {
            "accept": "*/*",
            "authorization": f"Bearer {jwt}",
            "content-type": "application/json",
            "origin": "https://business.gemini.google",
            "referer": "https://business.gemini.google/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        try:
            response = await client.post(
                LIST_FILE_METADATA_URL,
                headers=headers,
                json=body,
                timeout=30.0
            )
        except httpx.RequestError as e:
            logger.error(f"获取文件元数据请求失败: {e}")
            return {}

        if response.status_code != 200:
            logger.warning(f"获取文件元数据失败: {response.status_code}")
            return {}

        try:
            data = response.json()
            result = {}
            file_metadata_list = data.get("listSessionFileMetadataResponse", {}).get("fileMetadata", [])
            for meta in file_metadata_list:
                fid = meta.get("fileId")
                if fid:
                    result[fid] = meta
            return result
        except Exception as e:
            logger.error(f"解析文件元数据失败: {e}")
            return {}

    async def _download_image(
        self,
        jwt: str,
        session_name: str,
        file_id: str
    ) -> Optional[bytes]:
        """从Gemini API下载图片"""
        client = await get_http_client()

        # 构建正确的下载URL
        url = build_download_url(session_name, file_id)
        logger.info(f"下载图片URL: {url}")

        try:
            response = await client.get(
                url,
                headers=get_download_headers(jwt),
                timeout=60.0,
                follow_redirects=True
            )
            logger.info(f"下载响应: status={response.status_code}, content_length={len(response.content)}")
        except httpx.RequestError as e:
            logger.error(f"下载图片请求失败: {e}")
            return None

        if response.status_code != 200:
            logger.error(f"下载图片失败: {response.status_code}")
            return None

        return response.content

    async def _save_to_conversation_dir(
        self,
        image_data: bytes,
        mime_type: str,
        conversation_id: str,
        file_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        保存图片到会话目录

        目录结构: data/images/{conversation_id}/{filename}
        """
        # 确定文件扩展名
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = ext_map.get(mime_type, ".png")

        # 生成文件名
        if not file_name:
            # 使用内容hash + 时间戳生成唯一文件名
            content_hash = hashlib.md5(image_data).hexdigest()[:8]
            timestamp = int(time.time())
            file_name = f"img_{timestamp}_{content_hash}{ext}"

        # 确保目录存在
        conv_dir = IMAGES_DIR / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_path = conv_dir / file_name
        try:
            file_path.write_bytes(image_data)
            logger.debug(f"图片已保存: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return None

    def save_base64_image(
        self,
        base64_data: str,
        mime_type: str,
        conversation_id: str,
        file_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        保存base64编码的图片

        用于保存生成的图片（已经是base64格式）
        """
        try:
            image_data = base64.b64decode(base64_data)
        except Exception as e:
            logger.error(f"解码base64失败: {e}")
            return None

        # 使用同步方式保存
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        ext = ext_map.get(mime_type, ".png")

        if not file_name:
            content_hash = hashlib.md5(image_data).hexdigest()[:8]
            timestamp = int(time.time())
            file_name = f"gen_{timestamp}_{content_hash}{ext}"

        conv_dir = IMAGES_DIR / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)

        file_path = conv_dir / file_name
        try:
            file_path.write_bytes(image_data)
            logger.debug(f"生成图片已保存: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"保存生成图片失败: {e}")
            return None

    def get_image_path(self, conversation_id: str, file_name: str) -> Optional[Path]:
        """获取图片路径"""
        path = IMAGES_DIR / conversation_id / file_name
        if path.exists():
            return path
        return None

    def list_conversation_images(self, conversation_id: str) -> List[dict]:
        """列出会话的所有图片"""
        conv_dir = IMAGES_DIR / conversation_id
        if not conv_dir.exists():
            return []

        images = []
        for f in conv_dir.iterdir():
            if f.is_file() and f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                images.append({
                    "name": f.name,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "created": f.stat().st_ctime
                })

        return sorted(images, key=lambda x: x["created"], reverse=True)

    def cleanup_cache(self):
        """清理过期缓存"""
        now = time.time()
        expired = [k for k, v in self._cache_expiry.items() if v < now]
        for k in expired:
            self._cache.pop(k, None)
            self._cache_expiry.pop(k, None)

        if expired:
            logger.debug(f"清理了 {len(expired)} 个过期图片缓存")

    def cleanup_old_images(self, max_age_hours: int = 24):
        """
        清理旧图片

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        if not IMAGES_DIR.exists():
            return

        now = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0

        for conv_dir in IMAGES_DIR.iterdir():
            if not conv_dir.is_dir():
                continue

            for f in conv_dir.iterdir():
                if f.is_file():
                    age = now - f.stat().st_mtime
                    if age > max_age_seconds:
                        try:
                            f.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"删除旧图片失败: {e}")

            # 删除空目录
            if conv_dir.exists() and not any(conv_dir.iterdir()):
                try:
                    conv_dir.rmdir()
                except Exception:
                    pass

        if deleted_count:
            logger.info(f"清理了 {deleted_count} 个旧图片")


# 全局图片服务实例
image_service = ImageService()
