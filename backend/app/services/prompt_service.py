"""
提示词服务

提供提示词的缓存加速与CRUD能力，采用并发安全的缓存机制。
"""

import asyncio
import logging
from typing import Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Prompt
from ..repositories.prompt_repository import PromptRepository
from ..schemas.prompt import PromptCreate, PromptRead, PromptUpdate

logger = logging.getLogger(__name__)


class PromptCache:
    """
    并发安全的提示词缓存

    使用双重检查锁定模式（DCLP）确保：
    1. 只初始化一次
    2. 数据库查询不在锁内执行
    3. 多个协程安全访问
    """

    def __init__(self):
        self._cache: Dict[str, PromptRead] = {}
        self._lock = asyncio.Lock()
        self._loaded = False
        self._loading = False  # 防止并发加载

    async def ensure_loaded(self, loader_func) -> None:
        """
        确保缓存已加载（双重检查锁定）

        Args:
            loader_func: 异步加载函数，返回提示词列表
        """
        # 第一次检查（无锁）
        if self._loaded:
            return

        async with self._lock:
            # 第二次检查（有锁）
            if self._loaded:
                return

            # 防止并发加载
            if self._loading:
                return

            self._loading = True

        # 在锁外执行数据库查询
        try:
            prompts = await loader_func()
            new_cache = {item.name: PromptRead.model_validate(item) for item in prompts}

            async with self._lock:
                self._cache = new_cache
                self._loaded = True
                self._loading = False
                logger.debug("提示词缓存已加载，共 %d 条", len(new_cache))

        except Exception as exc:
            async with self._lock:
                self._loading = False
            logger.error("加载提示词缓存失败: %s", exc)
            raise

    def get(self, name: str) -> Optional[PromptRead]:
        """获取缓存项（同步方法，无锁）"""
        return self._cache.get(name)

    async def set(self, name: str, value: PromptRead) -> None:
        """设置缓存项"""
        async with self._lock:
            self._cache[name] = value

    async def remove(self, name: str) -> None:
        """移除缓存项"""
        async with self._lock:
            self._cache.pop(name, None)

    async def invalidate(self) -> None:
        """使缓存失效，下次访问时重新加载"""
        async with self._lock:
            self._loaded = False

    @property
    def is_loaded(self) -> bool:
        """缓存是否已加载"""
        return self._loaded


# 全局缓存单例
_prompt_cache = PromptCache()


def get_prompt_cache() -> PromptCache:
    """获取全局提示词缓存"""
    return _prompt_cache


class PromptService:
    """
    提示词服务，提供缓存加速与CRUD能力。

    架构说明：
    此Service是配置管理层，CRUD操作内部commit是合理的：
    - 每个方法是独立的原子操作（create/update/delete）
    - commit后立即更新全局缓存，保证数据库与缓存的强一致性
    - 路由层与Service 1:1映射，符合配置管理的常见模式
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PromptRepository(session)
        self._cache = get_prompt_cache()

    async def preload(self) -> None:
        """预加载所有提示词到缓存"""
        await self._cache.ensure_loaded(self.repo.list_all)

    async def get_prompt(self, name: str) -> Optional[str]:
        """
        获取提示词内容（优先从缓存）

        Args:
            name: 提示词名称

        Returns:
            提示词内容，不存在返回None
        """
        # 确保缓存已加载
        await self._cache.ensure_loaded(self.repo.list_all)

        # 从缓存获取
        cached = self._cache.get(name)
        if cached:
            return cached.content

        # 缓存未命中，从数据库加载
        prompt = await self.repo.get_by_name(name)
        if not prompt:
            return None

        # 更新缓存
        prompt_read = PromptRead.model_validate(prompt)
        await self._cache.set(name, prompt_read)
        return prompt_read.content

    async def list_prompts(self) -> list[PromptRead]:
        """列出所有提示词"""
        prompts = await self.repo.list_all()
        return [PromptRead.model_validate(item) for item in prompts]

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[PromptRead]:
        """根据ID获取提示词"""
        instance = await self.repo.get(id=prompt_id)
        if not instance:
            return None
        return PromptRead.model_validate(instance)

    async def create_prompt(self, payload: PromptCreate) -> PromptRead:
        """创建新提示词"""
        data = payload.model_dump()
        tags = data.get("tags")
        if tags is not None:
            data["tags"] = ",".join(tags)
        prompt = Prompt(**data)
        await self.repo.add(prompt)
        await self.session.commit()

        prompt_read = PromptRead.model_validate(prompt)
        await self._cache.set(prompt_read.name, prompt_read)
        return prompt_read

    async def update_prompt(self, prompt_id: int, payload: PromptUpdate) -> Optional[PromptRead]:
        """更新提示词"""
        instance = await self.repo.get(id=prompt_id)
        if not instance:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        if "tags" in update_data and update_data["tags"] is not None:
            update_data["tags"] = ",".join(update_data["tags"])

        await self.repo.update_fields(instance, **update_data)
        await self.session.commit()

        prompt_read = PromptRead.model_validate(instance)
        await self._cache.set(prompt_read.name, prompt_read)
        return prompt_read

    async def delete_prompt(self, prompt_id: int) -> bool:
        """删除提示词"""
        instance = await self.repo.get(id=prompt_id)
        if not instance:
            return False

        name = instance.name
        await self.repo.delete(instance)
        await self.session.commit()
        await self._cache.remove(name)
        return True
