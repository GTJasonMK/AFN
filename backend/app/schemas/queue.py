"""
队列相关的Pydantic数据模型
"""

from typing import Optional
from pydantic import BaseModel, Field


class QueueStatus(BaseModel):
    """单个队列的状态"""
    active: int = Field(..., description="正在执行的请求数")
    waiting: int = Field(..., description="等待中的请求数")
    max_concurrent: int = Field(..., description="最大并发数")
    total_processed: int = Field(..., description="已处理的请求总数")


class QueueStatusResponse(BaseModel):
    """所有队列的状态响应"""
    llm: QueueStatus = Field(..., description="LLM队列状态")
    image: QueueStatus = Field(..., description="图片生成队列状态")


class QueueConfigResponse(BaseModel):
    """队列配置响应"""
    llm_max_concurrent: int = Field(..., description="LLM最大并发数")
    image_max_concurrent: int = Field(..., description="图片生成最大并发数")


class QueueConfigUpdate(BaseModel):
    """队列配置更新请求"""
    llm_max_concurrent: Optional[int] = Field(
        None,
        ge=1,
        le=10,
        description="LLM最大并发数（1-10）"
    )
    image_max_concurrent: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="图片生成最大并发数（1-5）"
    )
