from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PromptBase(BaseModel):
    """Prompt 基础模型。"""

    name: str = Field(..., description="唯一标识，用于代码引用")
    title: Optional[str] = Field(default=None, description="可读标题")
    content: str = Field(..., description="提示词具体内容")
    description: Optional[str] = Field(default=None, description="使用场景描述")
    tags: Optional[List[str]] = Field(default=None, description="标签集合")


class PromptCreate(PromptBase):
    """创建 Prompt 时使用的模型。"""

    pass


class PromptUpdate(BaseModel):
    """更新 Prompt 时使用的模型（用户只能更新内容）。"""

    content: str = Field(..., description="提示词内容")


class PromptRead(PromptBase):
    """对外暴露的 Prompt 数据结构。"""

    id: int
    is_modified: bool = Field(default=False, description="是否已被用户修改")
    category: Optional[str] = Field(default=None, description="提示词分类")
    status: Optional[str] = Field(default=None, description="提示词状态")
    project_type: Optional[str] = Field(default=None, description="所属项目类型(novel/coding)")

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> "PromptRead":  # type: ignore[override]
        """在转换 ORM 模型时，将字符串标签拆分为列表。"""
        if hasattr(obj, "id") and hasattr(obj, "name"):
            raw_tags = getattr(obj, "tags", None)
            if isinstance(raw_tags, str):
                processed = [tag for tag in raw_tags.split(",") if tag]
            elif isinstance(raw_tags, list):
                processed = raw_tags
            else:
                processed = None
            data = {
                "id": getattr(obj, "id"),
                "name": getattr(obj, "name"),
                "title": getattr(obj, "title", None),
                "content": getattr(obj, "content", None),
                "description": getattr(obj, "description", None),
                "tags": processed,
                "is_modified": getattr(obj, "is_modified", False),
                "category": getattr(obj, "category", None),
                "status": getattr(obj, "status", None),
                "project_type": getattr(obj, "project_type", None),
            }
            return super().model_validate(data, *args, **kwargs)
        return super().model_validate(obj, *args, **kwargs)
