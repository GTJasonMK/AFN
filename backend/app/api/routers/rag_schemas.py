"""
RAG 路由共享响应模型

用于复用 RAG 完整性相关的响应结构。
"""

from pydantic import BaseModel, Field


class TypeDetailBase(BaseModel):
    """单类型完整性详情基础结构"""
    display_name: str = Field(description="显示名称")
    db_count: int = Field(description="数据库记录数")
    vector_count: int = Field(description="向量库记录数")
    complete: bool = Field(description="是否完整")


class CompletenessResponseBase(BaseModel):
    """完整性检查响应基础结构"""
    project_id: str = Field(description="项目ID")
    complete: bool = Field(description="总体是否完整")
    total_db_count: int = Field(description="数据库总记录数")
    total_vector_count: int = Field(description="向量库总记录数")


__all__ = [
    "TypeDetailBase",
    "CompletenessResponseBase",
]
