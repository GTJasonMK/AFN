# -*- coding: utf-8 -*-
"""LLM请求日志记录器

将每次请求的详细信息保存到JSONL文件，方便调试和分析。
日志文件位置：storage/llm_requests.jsonl（项目根目录的storage）
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMRequestLogger:
    """
    LLM请求日志记录器

    将每次请求的详细信息保存到JSONL文件，方便调试和分析。
    """

    def __init__(self, log_dir: Optional[str] = None, max_entries: int = 1000):
        """
        初始化日志记录器

        Args:
            log_dir: 日志目录，默认为项目根目录的 storage/
            max_entries: 最大保留条目数，超过后自动清理旧记录
        """
        if log_dir is None:
            # 使用统一的 storage 目录（项目根目录）
            from ..core.config import settings
            log_dir = settings.storage_dir
        self.log_dir = Path(log_dir)
        self.log_file = self.log_dir / "llm_requests.jsonl"
        self.max_entries = max_entries

        # 确保目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _truncate_content(self, content: str, max_length: int = 200) -> str:
        """截断内容，保留前后部分"""
        if not content or len(content) <= max_length:
            return content
        half = max_length // 2
        return f"{content[:half]}...({len(content)}chars)...{content[-half:]}"

    def _mask_api_key(self, api_key: str) -> str:
        """遮蔽API Key，仅显示前后4位"""
        if not api_key or len(api_key) < 12:
            return "***"
        return f"{api_key[:4]}...{api_key[-4:]}"

    def log_request(
        self,
        request_id: str,
        api_format: str,
        endpoint: str,
        model: str,
        messages: List[Dict],
        temperature: Optional[float],
        max_tokens: Optional[int],
        timeout: int,
        base_url: str,
        api_key: str,
        extra_params: Optional[Dict] = None,
    ) -> Dict:
        """
        记录请求开始

        Returns:
            请求日志字典（用于后续更新）
        """
        log_entry = {
            "request_id": request_id,
            "timestamp": datetime.now().isoformat(),
            "api_format": api_format,
            "endpoint": endpoint,
            "base_url": base_url,
            "api_key_masked": self._mask_api_key(api_key),
            "model": model,
            "messages_count": len(messages),
            "messages_preview": [
                {
                    "role": msg.get("role", "unknown"),
                    "content_preview": self._truncate_content(msg.get("content", ""))
                }
                for msg in messages[:3]  # 仅保留前3条消息预览
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "extra_params": extra_params,
            "status": "pending",
            "start_time": time.time(),
        }
        return log_entry

    def log_success(
        self,
        log_entry: Dict,
        response_length: int,
        chunk_count: int,
        response_preview: str = "",
    ):
        """记录请求成功"""
        log_entry["status"] = "success"
        log_entry["duration_ms"] = int((time.time() - log_entry["start_time"]) * 1000)
        log_entry["response_length"] = response_length
        log_entry["chunk_count"] = chunk_count
        log_entry["response_preview"] = self._truncate_content(response_preview, 300)
        del log_entry["start_time"]  # 移除临时字段

        self._write_log(log_entry)

    def log_error(
        self,
        log_entry: Dict,
        error_type: str,
        error_message: str,
        status_code: Optional[int] = None,
    ):
        """记录请求失败"""
        log_entry["status"] = "error"
        log_entry["duration_ms"] = int((time.time() - log_entry["start_time"]) * 1000)
        log_entry["error_type"] = error_type
        log_entry["error_message"] = self._truncate_content(error_message, 500)
        if status_code:
            log_entry["status_code"] = status_code
        del log_entry["start_time"]  # 移除临时字段

        self._write_log(log_entry)

    def _write_log(self, log_entry: Dict):
        """写入日志文件"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

            # 检查是否需要清理
            self._cleanup_if_needed()
        except Exception as e:
            logger.warning("写入LLM请求日志失败: %s", e)

    def _cleanup_if_needed(self):
        """清理过多的日志条目"""
        try:
            if not self.log_file.exists():
                return

            # 读取所有条目
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 如果超过最大条目数，保留最新的
            if len(lines) > self.max_entries:
                keep_lines = lines[-self.max_entries:]
                with open(self.log_file, "w", encoding="utf-8") as f:
                    f.writelines(keep_lines)
                logger.info("清理LLM请求日志，保留最新 %d 条", self.max_entries)
        except Exception as e:
            logger.warning("清理LLM请求日志失败: %s", e)

    def get_recent_logs(self, count: int = 50) -> List[Dict]:
        """获取最近的日志条目"""
        try:
            if not self.log_file.exists():
                return []

            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            recent_lines = lines[-count:]
            return [json.loads(line) for line in recent_lines if line.strip()]
        except Exception as e:
            logger.warning("读取LLM请求日志失败: %s", e)
            return []


# 全局日志记录器实例
_request_logger: Optional[LLMRequestLogger] = None


def get_request_logger() -> LLMRequestLogger:
    """获取全局请求日志记录器"""
    global _request_logger
    if _request_logger is None:
        _request_logger = LLMRequestLogger()
    return _request_logger
