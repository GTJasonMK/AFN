"""
Coding 文件相关路由：共享依赖与常量

说明：
- 本文件从 `coding/files.py` 拆分而来，用于集中管理 Depends 与共享常量，降低各路由模块的重复与漂移风险。
"""

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from ....db.session import get_session
from ....services.coding_files import DirectoryStructureService, FilePromptService


# 目录规划 Agent 类型（用于状态读写）
DIRECTORY_AGENT_TYPE = "directory_planning_v2"


async def get_directory_service(
    session: AsyncSession = Depends(get_session),
) -> DirectoryStructureService:
    """获取目录结构服务"""
    return DirectoryStructureService(session)


async def get_file_prompt_service(
    session: AsyncSession = Depends(get_session),
) -> FilePromptService:
    """获取文件 Prompt 服务"""
    return FilePromptService(session)


__all__ = [
    "DIRECTORY_AGENT_TYPE",
    "get_directory_service",
    "get_file_prompt_service",
]

