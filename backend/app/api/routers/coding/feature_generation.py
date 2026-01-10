"""
功能Prompt生成路由

处理编程项目功能的Prompt生成、内容保存和版本管理。
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.dependencies import (
    get_default_user,
    get_coding_project_service,
    get_llm_service,
    get_prompt_service,
    get_vector_store,
)
from ....core.config import settings
from ....db.session import get_session
from ....exceptions import (
    InvalidParameterError,
    ResourceNotFoundError,
)
from ....schemas.user import UserInDB
from ....serializers.coding_serializer import CodingSerializer
from ....services.llm_service import LLMService
from ....services.coding import CodingProjectService
from ....services.prompt_service import PromptService
from ....utils.sse_helpers import sse_event, create_sse_response
from ....utils.prompt_helpers import ensure_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== 请求/响应模型 ====================

class GenerateFeaturePromptRequest(BaseModel):
    """生成功能Prompt请求"""
    feature_index: int = Field(..., description="功能索引（从0开始）")
    writing_notes: Optional[str] = Field(None, description="写作指导/额外要求")


class FeatureContent(BaseModel):
    """功能内容"""
    feature_index: int
    title: str
    content: str
    review_prompt: str = ""  # 审查Prompt
    version_count: int = 1
    selected_version_index: int = 0
    word_count: int = 0


class FeatureVersion(BaseModel):
    """功能版本"""
    version_index: int
    content: str
    created_at: str


class SaveFeatureContentRequest(BaseModel):
    """保存功能内容请求"""
    content: str = Field(..., description="功能内容")


class SelectVersionRequest(BaseModel):
    """选择版本请求"""
    version_index: int = Field(..., description="版本索引")


# ==================== 辅助函数 ====================

def get_coding_blueprint(project) -> Optional[dict]:
    """从项目中获取编程蓝图数据

    编程项目的蓝图通过 CodingSerializer 从项目的各个关联表
    （blueprint、systems、modules、features等）中构建。
    """
    if not project.blueprint:
        return None

    # 使用 CodingSerializer 构建编程蓝图
    coding_blueprint_schema = CodingSerializer.build_blueprint_schema(project)
    if not coding_blueprint_schema:
        return None

    # 转换为字典
    return coding_blueprint_schema.model_dump()


def get_feature_from_blueprint(coding_blueprint: dict, feature_number: int) -> Optional[dict]:
    """从蓝图中获取指定功能

    Args:
        coding_blueprint: 编程蓝图数据
        feature_number: 功能编号（1-based，对应feature_number字段）

    Returns:
        功能数据字典，如果不存在返回None

    Note:
        在三层架构中：
        - systems: 系统列表
        - modules: 模块列表
        - features: 功能列表
        功能通过 feature_number 字段唯一标识
    """
    # 优先从features字段获取（新的三层架构）
    features = coding_blueprint.get('features', [])

    # 回退兼容：如果没有features，尝试chapter_outline
    if not features:
        features = coding_blueprint.get('chapter_outline', [])

    if not features:
        return None

    # 根据feature_number查找功能（不是索引！）
    for feature in features:
        fn = feature.get('feature_number') or feature.get('chapter_number', 0)
        if fn == feature_number:
            return feature

    return None


# ==================== 路由 ====================

@router.get("/coding/{project_id}/features")
async def list_features(
    project_id: str,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[dict]:
    """
    获取编程项目的功能列表

    返回coding_blueprint中的功能大纲（modules或chapter_outline）
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository

    coding_blueprint = get_coding_blueprint(project)
    if not coding_blueprint:
        return []

    # 获取所有功能记录
    feature_repo = CodingFeatureRepository(session)
    db_features = await feature_repo.get_by_project_ordered(project_id)

    # 构建功能编号到记录的映射
    feature_map = {f.feature_number: f for f in db_features}

    # 优先返回modules，其次是chapter_outline
    features = coding_blueprint.get('modules', [])
    if not features:
        features = coding_blueprint.get('chapter_outline', [])

    # 添加索引和生成状态
    result = []
    for idx, feature in enumerate(features):
        feature_number = idx + 1
        # 检查是否已有生成内容（通过coding_features表）
        db_feature = feature_map.get(feature_number)

        result.append({
            "index": idx,
            "title": feature.get('title') or feature.get('name', f'功能{idx + 1}'),
            "summary": feature.get('summary') or feature.get('description', ''),
            "priority": feature.get('priority', 'medium'),
            "status": db_feature.status if db_feature else 'not_generated',
            "has_content": bool(db_feature and db_feature.selected_version_id),
            "version_count": len(db_feature.versions) if db_feature and hasattr(db_feature, 'versions') else 0,
        })

    return result


@router.get("/coding/{project_id}/features/{feature_index}")
async def get_feature_content(
    project_id: str,
    feature_index: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> FeatureContent:
    """
    获取指定功能的生成内容

    feature_index: 0-based索引，内部转换为feature_number = feature_index + 1
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository
    from ....models.coding import CodingFeatureVersion
    from sqlalchemy import select

    coding_blueprint = get_coding_blueprint(project)
    if not coding_blueprint:
        raise ResourceNotFoundError("project", project_id, "编程蓝图不存在")

    # 转换为feature_number（1-based）
    feature_number = feature_index + 1
    feature = get_feature_from_blueprint(coding_blueprint, feature_number)
    if not feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 查找对应的功能记录
    feature_repo = CodingFeatureRepository(session)
    db_feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    content = ""
    review_prompt = ""
    version_count = 0
    selected_version_index = 0
    word_count = 0

    if db_feature:
        # 查询版本数量
        result = await session.execute(
            select(CodingFeatureVersion)
            .where(CodingFeatureVersion.feature_id == db_feature.id)
            .order_by(CodingFeatureVersion.created_at)
        )
        versions = list(result.scalars().all())
        version_count = len(versions)
        review_prompt = db_feature.review_prompt or ""

        if db_feature.selected_version_id:
            # 查找选中的版本
            for idx, v in enumerate(versions):
                if v.id == db_feature.selected_version_id:
                    content = v.content or ""
                    word_count = len(content)
                    selected_version_index = idx
                    break

    return FeatureContent(
        feature_index=feature_index,
        title=feature.get('title') or feature.get('name', f'功能{feature_index + 1}'),
        content=content,
        review_prompt=review_prompt,
        version_count=version_count,
        selected_version_index=selected_version_index,
        word_count=word_count,
    )


@router.get("/coding/{project_id}/features/{feature_index}/versions")
async def get_feature_versions(
    project_id: str,
    feature_index: int,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> List[FeatureVersion]:
    """
    获取指定功能的所有版本
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository
    from ....models.coding import CodingFeatureVersion
    from sqlalchemy import select

    feature_repo = CodingFeatureRepository(session)
    feature_number = feature_index + 1
    db_feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    if not db_feature:
        return []

    # 查询所有版本
    result = await session.execute(
        select(CodingFeatureVersion)
        .where(CodingFeatureVersion.feature_id == db_feature.id)
        .order_by(CodingFeatureVersion.created_at)
    )
    db_versions = list(result.scalars().all())

    versions = []
    for idx, version in enumerate(db_versions):
        versions.append(FeatureVersion(
            version_index=idx,
            content=version.content or "",
            created_at=version.created_at.isoformat() if version.created_at else "",
        ))

    return versions


@router.post("/coding/{project_id}/features/{feature_index}/generate")
async def generate_feature_prompt(
    project_id: str,
    feature_index: int,
    request: GenerateFeaturePromptRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    生成功能的Prompt内容（同步模式）

    根据功能描述和项目蓝图，生成对应的实现Prompt。
    """
    logger.info(
        "收到功能Prompt生成请求: project_id=%s feature_index=%s user_id=%s",
        project_id, feature_index, desktop_user.id
    )

    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)


    coding_blueprint = get_coding_blueprint(project)
    if not coding_blueprint:
        raise ResourceNotFoundError("project", project_id, "编程蓝图不存在")

    # 转换为feature_number（1-based）
    feature_number = feature_index + 1
    feature = get_feature_from_blueprint(coding_blueprint, feature_number)
    if not feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能不存在")

    # 构建系统提示词
    system_prompt = await _build_coding_system_prompt(prompt_service)

    # 构建用户提示词
    user_prompt = _build_feature_prompt(
        coding_blueprint=coding_blueprint,
        feature=feature,
        feature_number=feature_number,
        writing_notes=request.writing_notes,
    )

    # 调用LLM生成
    response = await llm_service.get_llm_response(
        system_prompt=system_prompt,
        conversation_history=[{"role": "user", "content": user_prompt}],
        user_id=desktop_user.id,
        max_tokens=settings.llm_max_tokens_coding_prompt,
        response_format=None,  # 不要求JSON格式
    )

    # 提取生成内容
    from ....utils.json_utils import extract_llm_content
    content, _ = extract_llm_content(response)

    # 保存到数据库
    from ....repositories.coding_repository import CodingFeatureRepository
    from ....models.coding import CodingFeatureVersion
    from sqlalchemy import select, func

    feature_repo = CodingFeatureRepository(session)
    feature_number = feature_index + 1

    # 获取功能记录
    db_feature = await feature_repo.get_by_project_and_number(project_id, feature_number)
    if not db_feature:
        raise ResourceNotFoundError("feature", str(feature_number), "功能大纲不存在，请先生成功能大纲")

    # 查询版本数量
    result = await session.execute(
        select(func.count(CodingFeatureVersion.id)).where(CodingFeatureVersion.feature_id == db_feature.id)
    )
    version_count = result.scalar() or 0

    # 创建版本
    version = CodingFeatureVersion(
        feature_id=db_feature.id,
        version_label=f"v{version_count + 1}",
        content=content,
    )
    session.add(version)
    await session.flush()

    # 选中此版本
    db_feature.selected_version_id = version.id
    db_feature.status = "generated"

    await session.commit()

    logger.info(
        "功能Prompt生成完成: project_id=%s feature_index=%s content_length=%d",
        project_id, feature_index, len(content)
    )

    return {
        "success": True,
        "feature_index": feature_index,
        "content": content,
        "version_count": version_count + 1,
    }


@router.post("/coding/{project_id}/features/{feature_index}/generate-stream")
async def generate_feature_prompt_stream(
    project_id: str,
    feature_index: int,
    request: GenerateFeaturePromptRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    生成功能的Prompt内容（SSE流式返回）

    事件类型：
    - token: 流式内容 {"token": "..."}
    - progress: 进度信息 {"stage": "...", "message": "..."}
    - complete: 完成 {"content": "...", "version_count": N}
    - error: 错误 {"message": "..."}
    """
    logger.info(
        "收到功能Prompt生成请求（SSE模式）: project_id=%s feature_index=%s user_id=%s",
        project_id, feature_index, desktop_user.id
    )

    async def event_generator():
        try:
            # 验证项目
            yield sse_event("progress", {"stage": "validating", "message": "验证项目..."})

            project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

            coding_blueprint = get_coding_blueprint(project)
            if not coding_blueprint:
                yield sse_event("error", {"message": "编程蓝图不存在"})
                return

            # 转换为feature_number（1-based）
            feature_number = feature_index + 1
            feature = get_feature_from_blueprint(coding_blueprint, feature_number)
            if not feature:
                yield sse_event("error", {"message": f"功能{feature_number}不存在"})
                return

            # 构建提示词
            yield sse_event("progress", {"stage": "preparing", "message": "准备提示词..."})

            system_prompt = await _build_coding_system_prompt(prompt_service)
            user_prompt = _build_feature_prompt(
                coding_blueprint=coding_blueprint,
                feature=feature,
                feature_number=feature_number,
                writing_notes=request.writing_notes,
            )

            # 流式生成
            yield sse_event("progress", {"stage": "generating", "message": "正在生成..."})

            full_content = ""
            conversation_history = [{"role": "user", "content": user_prompt}]
            async for chunk in llm_service.stream_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_id=desktop_user.id,
                response_format=None,  # 不要求JSON格式
                max_tokens=settings.llm_max_tokens_coding_prompt,
            ):
                content = chunk.get("content", "")
                if content:
                    full_content += content
                    yield sse_event("token", {"token": content})

            # 保存结果
            yield sse_event("progress", {"stage": "saving", "message": "保存结果..."})

            from ....repositories.coding_repository import CodingFeatureRepository, CodingFeatureVersionRepository
            from ....models.coding import CodingFeature as CodingFeatureModel, CodingFeatureVersion
            from sqlalchemy import select, func

            feature_repo = CodingFeatureRepository(session)

            # 使用 feature_number（1-based）
            feature_number = feature_index + 1
            feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

            if not feature:
                # 功能大纲不存在时抛出错误（功能应该先通过大纲生成创建）
                raise ResourceNotFoundError("feature", str(feature_number), "功能大纲不存在，请先生成功能大纲")

            # 查询当前版本数量
            result = await session.execute(
                select(func.count(CodingFeatureVersion.id)).where(CodingFeatureVersion.feature_id == feature.id)
            )
            version_count = result.scalar() or 0

            version = CodingFeatureVersion(
                feature_id=feature.id,
                version_label=f"v{version_count + 1}",
                content=full_content,
            )
            session.add(version)
            await session.flush()

            feature.selected_version_id = version.id
            feature.status = "generated"

            await session.commit()

            # RAG入库：将功能Prompt内容写入向量库，供后续检索
            try:
                from ....services.coding_rag import schedule_ingestion, CodingDataType
                from ....core.dependencies import get_vector_store

                vector_store = await get_vector_store()
                if vector_store:
                    schedule_ingestion(
                        project_id=project_id,
                        user_id=desktop_user.id,
                        data_type=CodingDataType.FEATURE_PROMPT,
                        vector_store=vector_store,
                        llm_service=llm_service,
                    )
                    logger.info("功能 %s Prompt已调度RAG入库: project=%s", feature_index + 1, project_id)
            except Exception as exc:
                # RAG入库失败不影响主流程
                logger.warning("功能 %s Prompt向量入库调度失败: %s", feature_index + 1, exc)

            yield sse_event("complete", {
                "content": full_content,
                "version_count": version_count + 1,
                "feature_index": feature_index,
            })

        except Exception as e:
            logger.exception("功能Prompt生成失败: %s", str(e))
            yield sse_event("error", {"message": str(e)})

    return create_sse_response(event_generator())


@router.post("/coding/{project_id}/features/{feature_index}/save")
async def save_feature_content(
    project_id: str,
    feature_index: int,
    request: SaveFeatureContentRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    保存功能内容（编辑后）
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository
    from ....models.coding import CodingFeatureVersion
    from sqlalchemy import select

    feature_repo = CodingFeatureRepository(session)
    feature_number = feature_index + 1
    feature = await feature_repo.get_with_versions(project_id, feature_number)

    if not feature or not feature.selected_version_id:
        raise ResourceNotFoundError("feature", str(feature_index), "功能内容不存在")

    # 获取选中的版本
    result = await session.execute(
        select(CodingFeatureVersion).where(CodingFeatureVersion.id == feature.selected_version_id)
    )
    selected_version = result.scalars().first()

    if not selected_version:
        raise ResourceNotFoundError("feature_version", str(feature.selected_version_id), "功能版本不存在")

    # 更新选中版本的内容
    old_content = selected_version.content or ""
    selected_version.content = request.content

    await session.commit()

    # 记录保存操作的详细信息
    import hashlib
    old_hash = hashlib.md5(old_content.encode('utf-8')).hexdigest()[:16] if old_content else "empty"
    new_hash = hashlib.md5(request.content.encode('utf-8')).hexdigest()[:16]
    logger.info(
        "保存功能内容: project=%s feature=%d old_hash=%s new_hash=%s changed=%s",
        project_id, feature_number, old_hash, new_hash, old_hash != new_hash
    )

    # RAG入库：更新向量库中的内容
    try:
        from ....services.coding_rag import schedule_ingestion, CodingDataType

        vector_store = await get_vector_store()
        if vector_store:
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.FEATURE_PROMPT,
                vector_store=vector_store,
                llm_service=llm_service,
            )
            logger.info("功能 %s 内容已调度RAG入库: project=%s", feature_number, project_id)
    except Exception as exc:
        logger.warning("功能 %s 内容向量更新调度失败: %s", feature_number, exc)

    return {"success": True, "word_count": len(request.content)}


@router.post("/coding/{project_id}/features/{feature_index}/select-version")
async def select_feature_version(
    project_id: str,
    feature_index: int,
    request: SelectVersionRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    选择功能的版本
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository
    from ....models.coding import CodingFeatureVersion
    from sqlalchemy import select

    feature_repo = CodingFeatureRepository(session)
    feature_number = feature_index + 1
    feature = await feature_repo.get_with_versions(project_id, feature_number)

    if not feature:
        raise ResourceNotFoundError("feature", str(feature_index), "功能不存在")

    # 查询功能的所有版本
    result = await session.execute(
        select(CodingFeatureVersion)
        .where(CodingFeatureVersion.feature_id == feature.id)
        .order_by(CodingFeatureVersion.created_at)
    )
    versions = list(result.scalars().all())

    if request.version_index < 0 or request.version_index >= len(versions):
        raise InvalidParameterError(f"版本索引{request.version_index}超出范围", parameter="version_index")

    target_version = versions[request.version_index]
    feature.selected_version_id = target_version.id

    await session.commit()

    return {
        "success": True,
        "selected_version_index": request.version_index,
        "word_count": len(target_version.content or ""),
    }


# ==================== 内部函数 ====================

async def _build_coding_system_prompt(prompt_service: PromptService) -> str:
    """构建编程项目的系统提示词"""
    # 尝试获取专门的coding提示词
    try:
        prompt = await prompt_service.get_prompt("prompt_generation")
        if prompt:
            return prompt
    except Exception:
        pass

    # 默认系统提示词 - Markdown格式输出
    return """你是一位资深软件工程师，擅长编写清晰、完整的功能实现Prompt。

输出原则：
1. 可直接使用：输出的内容是可以直接复制给AI编程助手使用的Prompt
2. 描述清晰：说明功能的作用、解决什么问题
3. 实现明确：描述核心算法和实现思路
4. 接口规范：明确函数签名、参数、返回值
5. 使用Markdown格式，不要输出JSON

输出模板：
# {功能名称}

## 功能描述
{这个功能做什么，解决什么问题，2-3句话}

## 实现思路
{核心算法或实现方案，为什么选择这个方案，3-5句话}

## 接口定义
**函数签名**
```{语言}
{完整函数签名}
```

**参数说明**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ... | ... | ... | ... |

**返回值**
- 类型：{类型}
- 说明：{说明}

## 实现步骤
1. **步骤名**：做什么，为什么
2. ...

## 错误处理
| 错误场景 | 处理方式 |
|----------|----------|
| ... | ... |

## 依赖模块
- **模块名**：用途

## 注意事项
{实现注意点，性能优化，安全考虑}

直接输出Markdown格式，不要任何前缀说明。"""


def _build_feature_prompt(
    coding_blueprint: dict,
    feature: dict,
    feature_number: int,
    writing_notes: Optional[str] = None,
) -> str:
    """构建功能生成的用户提示词

    确保使用当前功能的正确名称和所属模块信息。
    传递完整的技术栈信息，确保生成的Prompt遵循一致的技术约束。

    Args:
        coding_blueprint: 完整的编程蓝图数据
        feature: 当前功能的数据字典
        feature_number: 功能编号（1-based）
        writing_notes: 用户额外的写作指导

    Returns:
        格式化的用户提示词
    """
    import json

    # 提取项目基本信息
    project_name = coding_blueprint.get('title', '未命名项目')

    # 提取完整的技术栈信息
    tech_stack = coding_blueprint.get('tech_stack', {})
    if isinstance(tech_stack, dict):
        core_constraints = tech_stack.get('core_constraints', '')
        # 提取技术组件摘要
        components = tech_stack.get('components', [])
        components_summary = ', '.join(
            c.get('name', '') for c in components if isinstance(c, dict) and c.get('name')
        ) if components else ''
        # 提取技术领域摘要
        domains = tech_stack.get('domains', [])
        domains_summary = ', '.join(
            f"{d.get('name', '')}: {d.get('description', '')}"
            for d in domains if isinstance(d, dict) and d.get('name')
        ) if domains else ''
    else:
        core_constraints = ''
        components_summary = ''
        domains_summary = ''

    # 提取当前功能信息（优先使用 name 字段，这是 CodingFeature 的标准字段）
    feature_name = feature.get('name') or feature.get('title') or f'功能{feature_number}'
    feature_desc = feature.get('description') or feature.get('summary') or ''
    feature_inputs = feature.get('inputs', '')
    feature_outputs = feature.get('outputs', '')
    feature_priority = feature.get('priority', 'medium')

    # 获取所属系统和模块编号
    system_number = feature.get('system_number', 0)
    module_number = feature.get('module_number', 0)

    # 查找所属系统名称
    systems = coding_blueprint.get('systems', [])
    parent_system = next(
        (s for s in systems if s.get('system_number') == system_number),
        None
    )
    system_name = parent_system.get('name', '') if parent_system else ''

    # 查找所属模块名称
    modules = coding_blueprint.get('modules', [])
    parent_module = next(
        (m for m in modules if m.get('module_number') == module_number),
        None
    )
    module_name = parent_module.get('name', '') if parent_module else ''

    logger.debug(
        "构建功能Prompt: feature_number=%d, feature_name=%s, module=%s, system=%s",
        feature_number, feature_name, module_name, system_name
    )

    # 构建用户提示词（明确标注当前功能信息和完整技术栈）
    input_data = {
        "project": {
            "name": project_name,
        },
        "tech_stack": {
            "constraints": core_constraints[:500] if core_constraints else "",
            "components": components_summary[:300] if components_summary else "",
            "domains": domains_summary[:500] if domains_summary else "",
        },
        "current_feature": {
            "number": feature_number,
            "name": feature_name,
            "description": feature_desc[:500] if feature_desc else "",
            "inputs": feature_inputs[:200] if feature_inputs else "",
            "outputs": feature_outputs[:200] if feature_outputs else "",
            "priority": feature_priority,
        },
        "belongs_to": {
            "system": system_name if system_name else f"系统{system_number}",
            "module": module_name if module_name else f"模块{module_number}",
        }
    }

    if writing_notes:
        input_data["extra_requirements"] = writing_notes[:300]

    return json.dumps(input_data, ensure_ascii=False, indent=2)


# ==================== 审查Prompt API ====================

class GenerateReviewPromptRequest(BaseModel):
    """生成审查Prompt请求"""
    extra_requirements: Optional[str] = Field(None, description="额外的审查要求")


class SaveReviewPromptRequest(BaseModel):
    """保存审查Prompt请求"""
    review_prompt: str = Field(..., description="审查Prompt内容")


@router.post("/coding/{project_id}/features/{feature_index}/review-prompt/generate")
async def generate_review_prompt(
    project_id: str,
    feature_index: int,
    request: Optional[GenerateReviewPromptRequest] = None,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    prompt_service: PromptService = Depends(get_prompt_service),
    llm_service: LLMService = Depends(get_llm_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
):
    """
    生成功能的审查Prompt（SSE流式返回）

    基于实现Prompt生成对应的审查Prompt，用于验证功能实现。
    """
    logger.info(
        "收到审查Prompt生成请求: project_id=%s feature_index=%s",
        project_id, feature_index
    )

    async def event_generator():
        try:
            # 验证项目
            yield sse_event("progress", {"stage": "validating", "message": "验证项目..."})

            project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

            coding_blueprint = get_coding_blueprint(project)
            if not coding_blueprint:
                yield sse_event("error", {"message": "编程蓝图不存在"})
                return

            # 获取功能信息
            feature_number = feature_index + 1
            feature = get_feature_from_blueprint(coding_blueprint, feature_number)
            if not feature:
                yield sse_event("error", {"message": f"功能{feature_number}不存在"})
                return

            # 获取实现Prompt内容
            # 使用 CodingFeatureRepository 直接查询
            from ....repositories.coding_repository import CodingFeatureRepository
            from ....models.coding import CodingFeatureVersion
            from sqlalchemy import select

            feature_repo = CodingFeatureRepository(session)
            db_feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

            # 详细日志：诊断为什么找不到实现Prompt
            logger.info(
                "查询功能结果: project_id=%s, feature_number=%d, feature_exists=%s, "
                "selected_version_id=%s",
                project_id,
                feature_number,
                db_feature is not None,
                db_feature.selected_version_id if db_feature else "N/A",
            )

            implementation_prompt = ""
            if db_feature and db_feature.selected_version_id:
                # 查询选中的版本
                result = await session.execute(
                    select(CodingFeatureVersion).where(CodingFeatureVersion.id == db_feature.selected_version_id)
                )
                selected_version = result.scalars().first()
                if selected_version:
                    implementation_prompt = selected_version.content or ""
                    logger.info(
                        "找到实现Prompt: feature=%d, content_length=%d",
                        feature_number, len(implementation_prompt)
                    )
            else:
                logger.warning(
                    "未找到实现Prompt: feature=%d, db_feature=%s, selected_version_id=%s",
                    feature_number,
                    "exists" if db_feature else "None",
                    db_feature.selected_version_id if db_feature else "None"
                )

            if not implementation_prompt:
                yield sse_event("error", {"message": "请先生成功能Prompt"})
                return

            # 构建提示词
            yield sse_event("progress", {"stage": "preparing", "message": "准备提示词..."})

            system_prompt = await _build_review_system_prompt(prompt_service)
            user_prompt = _build_review_prompt(
                coding_blueprint=coding_blueprint,
                feature=feature,
                feature_number=feature_number,
                implementation_prompt=implementation_prompt,
                extra_requirements=request.extra_requirements if request else None,
            )

            # 流式生成
            yield sse_event("progress", {"stage": "generating", "message": "正在生成审查Prompt..."})

            full_content = ""
            conversation_history = [{"role": "user", "content": user_prompt}]
            async for chunk in llm_service.stream_llm_response(
                system_prompt=system_prompt,
                conversation_history=conversation_history,
                user_id=desktop_user.id,
                response_format=None,
                max_tokens=settings.llm_max_tokens_coding_prompt,
            ):
                content = chunk.get("content", "")
                if content:
                    full_content += content
                    yield sse_event("token", {"token": content})

            # 保存结果
            yield sse_event("progress", {"stage": "saving", "message": "保存结果..."})

            if db_feature:
                db_feature.review_prompt = full_content
                await session.commit()

            # RAG入库：将审查Prompt内容写入向量库
            try:
                from ....services.coding_rag import schedule_ingestion, CodingDataType
                from ....core.dependencies import get_vector_store

                vector_store = await get_vector_store()
                if vector_store:
                    schedule_ingestion(
                        project_id=project_id,
                        user_id=desktop_user.id,
                        data_type=CodingDataType.REVIEW_PROMPT,
                        vector_store=vector_store,
                    )
                    logger.info("功能 %s 审查Prompt已调度RAG入库: project=%s", feature_index + 1, project_id)
            except Exception as exc:
                # RAG入库失败不影响主流程
                logger.warning("功能 %s 审查Prompt向量入库调度失败: %s", feature_index + 1, exc)

            yield sse_event("complete", {
                "review_prompt": full_content,
                "feature_index": feature_index,
            })

        except Exception as e:
            logger.exception("审查Prompt生成失败: %s", str(e))
            yield sse_event("error", {"message": str(e)})

    return create_sse_response(event_generator())


@router.post("/coding/{project_id}/features/{feature_index}/review-prompt/save")
async def save_review_prompt(
    project_id: str,
    feature_index: int,
    request: SaveReviewPromptRequest,
    coding_project_service: CodingProjectService = Depends(get_coding_project_service),
    session: AsyncSession = Depends(get_session),
    desktop_user: UserInDB = Depends(get_default_user),
) -> dict:
    """
    保存审查Prompt（编辑后）
    """
    project = await coding_project_service.ensure_project_owner(project_id, desktop_user.id)

    from ....repositories.coding_repository import CodingFeatureRepository

    feature_repo = CodingFeatureRepository(session)
    feature_number = feature_index + 1
    db_feature = await feature_repo.get_by_project_and_number(project_id, feature_number)

    if not db_feature:
        raise ResourceNotFoundError("feature", str(feature_index), "功能不存在")

    db_feature.review_prompt = request.review_prompt
    await session.commit()

    logger.info(
        "保存审查Prompt: project=%s feature=%d length=%d",
        project_id, feature_number, len(request.review_prompt)
    )

    # RAG入库：更新向量库中的审查Prompt内容
    try:
        from ....services.coding_rag import schedule_ingestion, CodingDataType
        from ....core.dependencies import get_vector_store

        vector_store = await get_vector_store()
        if vector_store:
            schedule_ingestion(
                project_id=project_id,
                user_id=desktop_user.id,
                data_type=CodingDataType.REVIEW_PROMPT,
                vector_store=vector_store,
            )
            logger.info("功能 %s 审查Prompt已调度RAG入库: project=%s", feature_number, project_id)
    except Exception as exc:
        logger.warning("功能 %s 审查Prompt向量更新调度失败: %s", feature_number, exc)

    return {"success": True, "word_count": len(request.review_prompt)}


# ==================== 审查Prompt辅助函数 ====================

async def _build_review_system_prompt(prompt_service: PromptService) -> str:
    """构建审查Prompt的系统提示词"""
    try:
        prompt = await prompt_service.get_prompt("review_prompt_generation")
        if prompt:
            return prompt
    except Exception:
        pass

    # 默认系统提示词 - 专注于单元测试
    return """你是一位资深的测试工程师，擅长编写清晰、可执行的单元测试提示词。

你的任务是根据功能的实现Prompt，生成对应的单元测试Prompt，帮助AI编码助手为该功能编写完整的单元测试。

## 输出内容

1. **测试目标**
   - 简要说明需要测试的功能点

2. **测试用例清单**
   - 正常流程测试（happy path）
   - 边界条件测试
   - 异常/错误处理测试

3. **Mock/Stub 建议**
   - 需要模拟的外部依赖
   - 建议的模拟方式

## 输出格式

使用Markdown格式。直接输出测试Prompt内容，不要添加任何前缀说明。
内容要简洁实用，便于直接复制给AI编码助手使用。"""


def _build_review_prompt(
    coding_blueprint: dict,
    feature: dict,
    feature_number: int,
    implementation_prompt: str,
    extra_requirements: Optional[str] = None,
) -> str:
    """构建审查Prompt生成的用户提示词"""
    import json

    # 提取功能信息
    feature_name = feature.get('name') or feature.get('title') or f'功能{feature_number}'
    feature_desc = feature.get('description') or feature.get('summary') or ''
    feature_inputs = feature.get('inputs', '')
    feature_outputs = feature.get('outputs', '')

    # 提取技术栈信息
    tech_stack = coding_blueprint.get('tech_stack', {})
    core_constraints = tech_stack.get('core_constraints', '') if isinstance(tech_stack, dict) else ''

    input_data = {
        "feature": {
            "name": feature_name,
            "description": feature_desc[:200] if feature_desc else "",
            "inputs": feature_inputs[:150] if feature_inputs else "",
            "outputs": feature_outputs[:150] if feature_outputs else "",
        },
        "tech_stack": core_constraints[:200] if core_constraints else "",
        "implementation_prompt": implementation_prompt[:1500],
    }

    if extra_requirements:
        input_data["extra_requirements"] = extra_requirements[:150]

    return f"""请为以下功能生成单元测试Prompt：

{json.dumps(input_data, ensure_ascii=False, indent=2)}

生成一个简洁的单元测试Prompt，列出需要测试的场景和用例。"""
