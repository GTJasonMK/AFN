"""
提示词服务

提供提示词的缓存加速与CRUD能力，采用并发安全的缓存机制。
支持基于_registry.yaml的目录结构管理。
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Prompt
from ..repositories.prompt_repository import PromptRepository
from ..schemas.prompt import PromptCreate, PromptRead, PromptUpdate
from ..utils.prompt_include import parse_yaml_frontmatter, resolve_prompt_includes

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


class PromptRegistry:
    """
    提示词注册表管理器

    负责加载和管理_registry.yaml中的提示词元数据，
    提供名称到路径的映射、分类查询等功能。
    """

    def __init__(self, prompts_dir: Path):
        self._prompts_dir = prompts_dir
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._categories: Dict[str, Dict[str, Any]] = {}
        self._statuses: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def _load(self) -> None:
        """加载注册表文件"""
        if self._loaded:
            return

        registry_file = self._prompts_dir / "_registry.yaml"
        if not registry_file.is_file():
            logger.debug("注册表文件不存在: %s，使用兼容模式", registry_file)
            self._loaded = True
            return

        try:
            with open(registry_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            self._registry = data.get('prompts', {})
            self._categories = data.get('categories', {})
            self._statuses = data.get('statuses', {})
            self._loaded = True
            logger.info("已加载提示词注册表，共 %d 个提示词", len(self._registry))

        except Exception as e:
            logger.error("加载注册表失败: %s", e)
            self._loaded = True  # 标记为已加载，避免重复尝试

    def get_path(self, name: str) -> Optional[str]:
        """
        获取提示词的相对路径

        Args:
            name: 提示词名称

        Returns:
            相对路径（如 "01_inspiration/inspiration.md"），不存在返回None
        """
        self._load()
        if name in self._registry:
            return self._registry[name].get('path')
        return None

    def get_meta(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取提示词的完整元数据

        Args:
            name: 提示词名称

        Returns:
            元数据字典，不存在返回None
        """
        self._load()
        return self._registry.get(name)

    def get_all_names(self) -> List[str]:
        """获取所有已注册的提示词名称"""
        self._load()
        return list(self._registry.keys())

    def get_by_category(self, category: str) -> List[str]:
        """按分类获取提示词名称列表"""
        self._load()
        return [
            name for name, meta in self._registry.items()
            if meta.get('category') == category
        ]

    def get_by_status(self, status: str) -> List[str]:
        """按状态获取提示词名称列表"""
        self._load()
        return [
            name for name, meta in self._registry.items()
            if meta.get('status') == status
        ]

    def get_dependencies(self, name: str) -> List[str]:
        """获取提示词的依赖列表"""
        self._load()
        meta = self._registry.get(name)
        if meta:
            return meta.get('dependencies', [])
        return []

    def get_used_by(self, name: str) -> List[str]:
        """获取使用此提示词的服务列表"""
        self._load()
        meta = self._registry.get(name)
        if meta:
            return meta.get('used_by', [])
        return []

    def get_category_info(self, category: str) -> Optional[Dict[str, Any]]:
        """获取分类信息"""
        self._load()
        return self._categories.get(category)

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """获取所有分类定义"""
        self._load()
        return self._categories.copy()

    def is_registry_available(self) -> bool:
        """检查注册表是否可用"""
        self._load()
        return len(self._registry) > 0


# 全局注册表缓存
_prompt_registry: Optional[PromptRegistry] = None


def get_prompt_registry(prompts_dir: Path) -> PromptRegistry:
    """获取或创建全局提示词注册表"""
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry(prompts_dir)
    return _prompt_registry


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
        self._prompts_dir = self._get_prompts_dir()
        self._registry = get_prompt_registry(self._prompts_dir)

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

    async def get_prompt_or_fallback(
        self,
        name: str,
        fallback: str,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> str:
        """
        获取提示词内容，失败或不存在时返回默认模板

        Args:
            name: 提示词名称
            fallback: 默认模板内容
            logger: 可选日志实例，用于记录加载异常
        """
        try:
            prompt = await self.get_prompt(name)
        except Exception as e:
            if logger:
                logger.warning("无法加载 %s 提示词: %s", name, e)
            return fallback

        if not prompt:
            return fallback
        return prompt

    async def get_prompt_or_default(
        self,
        name: str,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> str:
        """
        获取提示词内容，失败时回退到默认模板

        Args:
            name: 提示词名称
            logger: 可选日志实例，用于记录加载异常
        """
        try:
            prompt = await self.get_prompt(name)
        except Exception as e:
            if logger:
                logger.warning("无法加载 %s 提示词: %s", name, e)
            prompt = None

        if prompt:
            return prompt

        default_content = await self.get_default_content(name)
        if default_content:
            return default_content

        if logger:
            logger.warning("提示词不存在: %s", name)
        return ""

    async def get_prompt_or_fallback_name(
        self,
        name: str,
        fallback_name: str,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> str:
        """
        获取提示词内容，失败时回退到另一个提示词名称

        Args:
            name: 首选提示词名称
            fallback_name: 回退提示词名称
            logger: 可选日志实例，用于记录加载异常
        """
        try:
            prompt = await self.get_prompt(name)
        except Exception as e:
            if logger:
                logger.warning("无法加载 %s 提示词: %s", name, e)
            prompt = None

        if prompt:
            return prompt

        try:
            fallback_prompt = await self.get_prompt(fallback_name)
        except Exception as e:
            if logger:
                logger.warning("无法加载 %s 提示词: %s", fallback_name, e)
            fallback_prompt = None

        if fallback_prompt:
            return fallback_prompt

        if logger:
            logger.warning("提示词不存在: %s/%s", name, fallback_name)
        return ""

    async def list_prompts(self) -> list[PromptRead]:
        """
        列出所有提示词

        从数据库获取提示词，并从registry补充category、status和project_type元数据
        """
        prompts = await self.repo.list_all()
        result = []
        for item in prompts:
            prompt_read = PromptRead.model_validate(item)
            # 从registry补充元数据
            meta = self._registry.get_meta(item.name)
            if meta:
                prompt_read.category = meta.get('category')
                prompt_read.status = meta.get('status')
                # 如果数据库中没有title/description，也从registry补充
                if not prompt_read.title:
                    prompt_read.title = meta.get('title')
                if not prompt_read.description:
                    prompt_read.description = meta.get('description')
                # 从分类定义获取project_type
                category = meta.get('category')
                if category:
                    cat_info = self._registry.get_category_info(category)
                    if cat_info:
                        prompt_read.project_type = cat_info.get('project_type')
            result.append(prompt_read)
        return result

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

    def _get_prompts_dir(self) -> Path:
        """获取提示词目录路径"""
        prompts_dir_env = os.environ.get('PROMPTS_DIR')
        if prompts_dir_env:
            return Path(prompts_dir_env)
        return Path(__file__).resolve().parents[2] / "prompts"

    async def get_default_content(self, name: str) -> Optional[str]:
        """
        获取提示词的默认内容（从文件读取）

        优先使用注册表中的路径，如果注册表不可用则回退到平铺结构。

        Args:
            name: 提示词名称

        Returns:
            默认内容（不含YAML元数据），不存在返回None
        """
        prompts_dir = self._prompts_dir

        # 优先从注册表获取路径
        registry_path = self._registry.get_path(name)
        if registry_path:
            prompt_file = prompts_dir / registry_path
        else:
            # 回退到旧的平铺结构
            prompt_file = prompts_dir / f"{name}.md"

        if not prompt_file.is_file():
            # 尝试在子目录中搜索（兼容迁移过程）
            for subdir in prompts_dir.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('_'):
                    candidate = subdir / f"{name}.md"
                    if candidate.is_file():
                        prompt_file = candidate
                        break

        if not prompt_file.is_file():
            return None

        file_content = prompt_file.read_text(encoding="utf-8")
        _, body_content = parse_yaml_frontmatter(file_content)
        return resolve_prompt_includes(
            body_content,
            current_file=prompt_file,
            prompts_dir=prompts_dir,
        )

    async def reset_prompt(self, name: str) -> Optional[PromptRead]:
        """
        恢复单个提示词到默认值

        Args:
            name: 提示词名称

        Returns:
            恢复后的提示词，不存在返回None
        """
        # 获取数据库中的提示词
        instance = await self.repo.get_by_name(name)
        if not instance:
            return None

        # 获取默认内容
        default_content = await self.get_default_content(name)
        if default_content is None:
            logger.warning(f"无法找到提示词 '{name}' 的默认文件")
            return None

        # 更新内容并标记为未修改
        await self.repo.update_fields(
            instance,
            content=default_content,
            is_modified=False,
        )
        await self.session.commit()

        prompt_read = PromptRead.model_validate(instance)
        await self._cache.set(prompt_read.name, prompt_read)
        logger.info(f"提示词 '{name}' 已恢复默认值")
        return prompt_read

    async def reset_all_prompts(self) -> int:
        """
        恢复所有提示词到默认值

        优先使用注册表中的提示词列表，回退到遍历子目录。

        Returns:
            恢复的提示词数量
        """
        prompts_dir = self._prompts_dir
        if not prompts_dir.is_dir():
            logger.warning(f"提示词目录不存在: {prompts_dir}")
            return 0

        reset_count = 0

        # 优先使用注册表
        if self._registry.is_registry_available():
            for name in self._registry.get_all_names():
                result = await self.reset_prompt(name)
                if result:
                    reset_count += 1
        else:
            # 回退到遍历目录结构
            # 先遍历子目录
            for subdir in prompts_dir.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('_'):
                    for prompt_file in subdir.glob("*.md"):
                        name = prompt_file.stem
                        result = await self.reset_prompt(name)
                        if result:
                            reset_count += 1

            # 再遍历根目录（兼容旧结构）
            for prompt_file in prompts_dir.glob("*.md"):
                name = prompt_file.stem
                result = await self.reset_prompt(name)
                if result:
                    reset_count += 1

        logger.info(f"已恢复 {reset_count} 个提示词到默认值")
        return reset_count

    async def update_prompt_content(self, name: str, content: str) -> Optional[PromptRead]:
        """
        更新提示词内容（用户编辑）

        Args:
            name: 提示词名称
            content: 新内容

        Returns:
            更新后的提示词，不存在返回None
        """
        instance = await self.repo.get_by_name(name)
        if not instance:
            return None

        # 更新内容并标记为已修改
        await self.repo.update_fields(
            instance,
            content=content,
            is_modified=True,
        )
        await self.session.commit()

        prompt_read = PromptRead.model_validate(instance)
        await self._cache.set(prompt_read.name, prompt_read)
        logger.info(f"提示词 '{name}' 已更新")
        return prompt_read

    async def get_prompt_by_name(self, name: str) -> Optional[PromptRead]:
        """
        根据名称获取提示词完整信息

        Args:
            name: 提示词名称

        Returns:
            提示词信息，不存在返回None
        """
        # 确保缓存已加载
        await self._cache.ensure_loaded(self.repo.list_all)

        # 从缓存获取
        cached = self._cache.get(name)
        if cached:
            # 从registry补充元数据（缓存可能没有这些信息）
            prompt_read = cached.model_copy()
            meta = self._registry.get_meta(name)
            if meta:
                prompt_read.category = meta.get('category')
                prompt_read.status = meta.get('status')
                if not prompt_read.title:
                    prompt_read.title = meta.get('title')
                if not prompt_read.description:
                    prompt_read.description = meta.get('description')
                # 从分类定义获取project_type
                category = meta.get('category')
                if category:
                    cat_info = self._registry.get_category_info(category)
                    if cat_info:
                        prompt_read.project_type = cat_info.get('project_type')
            return prompt_read

        # 缓存未命中，从数据库加载
        prompt = await self.repo.get_by_name(name)
        if not prompt:
            return None

        prompt_read = PromptRead.model_validate(prompt)
        # 从registry补充元数据
        meta = self._registry.get_meta(name)
        if meta:
            prompt_read.category = meta.get('category')
            prompt_read.status = meta.get('status')
            if not prompt_read.title:
                prompt_read.title = meta.get('title')
            if not prompt_read.description:
                prompt_read.description = meta.get('description')
            # 从分类定义获取project_type
            category = meta.get('category')
            if category:
                cat_info = self._registry.get_category_info(category)
                if cat_info:
                    prompt_read.project_type = cat_info.get('project_type')
        await self._cache.set(name, prompt_read)
        return prompt_read

    async def export_prompts(self) -> Dict[str, Any]:
        """
        导出所有已修改的提示词配置

        Returns:
            包含提示词配置的字典，仅导出用户已修改的提示词
        """
        prompts = await self.list_prompts()

        # 只导出已修改的提示词（用户自定义的）
        modified_prompts = []
        for p in prompts:
            if p.is_modified:
                modified_prompts.append({
                    "name": p.name,
                    "content": p.content,
                    "title": p.title,
                    "description": p.description,
                    "tags": p.tags,
                })

        return {
            "count": len(modified_prompts),
            "prompts": modified_prompts,
        }

    async def import_prompts(self, import_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入提示词配置

        Args:
            import_data: 导入数据，包含prompts列表

        Returns:
            导入结果
        """
        prompts_data = import_data.get("prompts", [])
        if not prompts_data:
            return {
                "success": True,
                "message": "没有提示词需要导入",
                "imported": 0,
                "skipped": 0,
            }

        imported = 0
        skipped = 0
        details = []

        for prompt_data in prompts_data:
            name = prompt_data.get("name")
            content = prompt_data.get("content")

            if not name or not content:
                skipped += 1
                details.append(f"跳过无效数据（缺少name或content）")
                continue

            # 检查提示词是否存在
            existing = await self.repo.get_by_name(name)
            if existing:
                # 更新现有提示词
                await self.repo.update_fields(
                    existing,
                    content=content,
                    is_modified=True,
                )
                await self.session.commit()

                prompt_read = PromptRead.model_validate(existing)
                await self._cache.set(name, prompt_read)
                imported += 1
                details.append(f"已更新: {name}")
            else:
                # 提示词不存在，跳过（因为提示词需要与默认文件对应）
                skipped += 1
                details.append(f"跳过: {name}（系统中不存在此提示词）")

        return {
            "success": True,
            "message": f"导入完成: {imported} 个成功, {skipped} 个跳过",
            "imported": imported,
            "skipped": skipped,
            "details": details,
        }

    # ==================== 注册表查询方法 ====================

    def get_prompt_meta(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取提示词的注册表元数据

        Args:
            name: 提示词名称

        Returns:
            元数据字典，包含 path, title, category, status, used_by, dependencies 等
        """
        return self._registry.get_meta(name)

    def get_prompts_by_category(self, category: str) -> List[str]:
        """
        按分类获取提示词名称列表

        Args:
            category: 分类名（inspiration, blueprint, outline, writing, analysis, manga, protagonist）

        Returns:
            提示词名称列表
        """
        return self._registry.get_by_category(category)

    def get_prompts_by_status(self, status: str) -> List[str]:
        """
        按状态获取提示词名称列表

        Args:
            status: 状态（active, experimental, unused, deprecated）

        Returns:
            提示词名称列表
        """
        return self._registry.get_by_status(status)

    def get_prompt_dependencies(self, name: str) -> List[str]:
        """获取提示词的依赖列表"""
        return self._registry.get_dependencies(name)

    def get_prompt_used_by(self, name: str) -> List[str]:
        """获取使用此提示词的服务列表"""
        return self._registry.get_used_by(name)

    def get_all_categories(self) -> Dict[str, Dict[str, Any]]:
        """获取所有分类定义"""
        return self._registry.get_all_categories()

    def get_registry_summary(self) -> Dict[str, Any]:
        """
        获取注册表摘要信息

        Returns:
            摘要信息，包含各分类和状态的提示词数量
        """
        if not self._registry.is_registry_available():
            return {"available": False}

        all_names = self._registry.get_all_names()
        categories = self._registry.get_all_categories()

        # 按分类统计
        category_counts = {}
        for cat in categories:
            category_counts[cat] = len(self._registry.get_by_category(cat))

        # 按状态统计
        status_counts = {
            "active": len(self._registry.get_by_status("active")),
            "experimental": len(self._registry.get_by_status("experimental")),
            "unused": len(self._registry.get_by_status("unused")),
            "deprecated": len(self._registry.get_by_status("deprecated")),
        }

        return {
            "available": True,
            "total": len(all_names),
            "by_category": category_counts,
            "by_status": status_counts,
            "categories": categories,
        }

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """
        获取依赖关系图

        Returns:
            字典，key为提示词名称，value为其依赖的提示词列表
        """
        if not self._registry.is_registry_available():
            return {}

        return {
            name: self._registry.get_dependencies(name)
            for name in self._registry.get_all_names()
        }

    def get_usage_map(self) -> Dict[str, List[str]]:
        """
        获取使用关系图（prompt -> services）

        Returns:
            字典，key为提示词名称，value为使用该提示词的服务列表
        """
        if not self._registry.is_registry_available():
            return {}

        return {
            name: self._registry.get_used_by(name)
            for name in self._registry.get_all_names()
        }

    def validate_registry(self) -> List[str]:
        """
        验证注册表完整性

        检查：
        1. 注册表中的文件是否都存在
        2. 依赖的提示词是否都存在

        Returns:
            错误消息列表，空列表表示验证通过
        """
        if not self._registry.is_registry_available():
            return ["注册表不可用"]

        errors = []
        prompts_dir = self._prompts_dir

        for name in self._registry.get_all_names():
            # 检查文件是否存在
            path = self._registry.get_path(name)
            if path:
                full_path = prompts_dir / path
                if not full_path.is_file():
                    errors.append(f"文件不存在: {path}")

            # 检查依赖是否存在
            for dep in self._registry.get_dependencies(name):
                if dep not in self._registry.get_all_names():
                    errors.append(f"依赖不存在: {name} -> {dep}")

        return errors

    def get_reverse_dependencies(self, name: str) -> List[str]:
        """
        获取反向依赖（哪些提示词依赖此提示词）

        Args:
            name: 提示词名称

        Returns:
            依赖此提示词的提示词名称列表
        """
        if not self._registry.is_registry_available():
            return []

        reverse_deps = []
        for prompt_name in self._registry.get_all_names():
            if name in self._registry.get_dependencies(prompt_name):
                reverse_deps.append(prompt_name)
        return reverse_deps


