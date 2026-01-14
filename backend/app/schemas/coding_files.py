"""
Coding项目目录结构和文件Prompt的Schema定义

独立于功能大纲的文件级别Prompt生成系统。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 基础枚举 ====================

class DirectoryNodeType(str, Enum):
    """目录节点类型"""
    DIRECTORY = "directory"
    PACKAGE = "package"


class FileType(str, Enum):
    """文件类型"""
    SOURCE = "source"
    CONFIG = "config"
    TEST = "test"
    DOC = "doc"


class FileGenerationStatus(str, Enum):
    """文件Prompt生成状态"""
    NOT_GENERATED = "not_generated"
    GENERATING = "generating"
    GENERATED = "generated"
    FAILED = "failed"


class DirectoryGenerationStatus(str, Enum):
    """目录结构生成状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class FilePriority(str, Enum):
    """文件优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==================== 目录节点相关 ====================

class DirectoryNodeBase(BaseModel):
    """目录节点基础字段"""
    name: str = Field(..., description="目录名称")
    path: str = Field(..., description="完整路径，如 src/services/user")
    node_type: DirectoryNodeType = Field(default=DirectoryNodeType.DIRECTORY, description="节点类型")
    description: Optional[str] = Field(default=None, description="目录说明")
    sort_order: int = Field(default=0, description="排序顺序")


class DirectoryNodeCreate(BaseModel):
    """创建目录节点请求"""
    name: str = Field(..., description="目录名称", min_length=1, max_length=255)
    parent_id: Optional[int] = Field(default=None, description="父目录ID，根目录为空")
    node_type: DirectoryNodeType = Field(default=DirectoryNodeType.DIRECTORY)
    description: Optional[str] = Field(default=None, max_length=1000)


class DirectoryNodeUpdate(BaseModel):
    """更新目录节点请求"""
    name: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    sort_order: Optional[int] = None


class DirectoryNodeResponse(BaseModel):
    """目录节点响应"""
    id: int
    project_id: str
    parent_id: Optional[int] = None
    name: str
    path: str
    node_type: str
    description: Optional[str] = None
    sort_order: int = 0
    module_number: Optional[int] = None
    generation_status: str = "pending"
    is_manual: bool = False
    file_count: int = Field(default=0, description="该目录下的文件数量")
    files: List["SourceFileResponse"] = Field(default_factory=list, description="该目录下的文件列表")
    children: List["DirectoryNodeResponse"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class DirectoryTreeResponse(BaseModel):
    """完整目录树响应"""
    project_id: str
    root_nodes: List[DirectoryNodeResponse] = Field(default_factory=list)
    total_directories: int = 0
    total_files: int = 0


# ==================== 源文件相关 ====================

class SourceFileBase(BaseModel):
    """源文件基础字段"""
    filename: str = Field(..., description="文件名，如 user_service.py")
    file_path: str = Field(..., description="完整文件路径")
    file_type: FileType = Field(default=FileType.SOURCE)
    language: Optional[str] = Field(default=None, description="编程语言：python/typescript/go等")
    description: Optional[str] = Field(default=None, description="文件描述")
    purpose: Optional[str] = Field(default=None, description="文件用途说明")
    priority: FilePriority = Field(default=FilePriority.MEDIUM)


class SourceFileCreate(BaseModel):
    """创建源文件请求"""
    directory_id: int = Field(..., description="所属目录ID")
    filename: str = Field(..., description="文件名", min_length=1, max_length=255)
    file_type: FileType = Field(default=FileType.SOURCE)
    language: Optional[str] = Field(default=None, max_length=64)
    description: Optional[str] = Field(default=None, max_length=2000)
    purpose: Optional[str] = Field(default=None, max_length=2000)
    priority: FilePriority = Field(default=FilePriority.MEDIUM)


class SourceFileUpdate(BaseModel):
    """更新源文件请求"""
    filename: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    purpose: Optional[str] = Field(default=None, max_length=2000)
    priority: Optional[FilePriority] = None
    sort_order: Optional[int] = None


class SourceFileResponse(BaseModel):
    """源文件响应"""
    id: int
    project_id: str
    directory_id: int
    filename: str
    file_path: str
    file_type: str
    language: Optional[str] = None
    description: Optional[str] = None
    purpose: Optional[str] = None
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    module_number: Optional[int] = None
    system_number: Optional[int] = None
    priority: str = "medium"
    sort_order: int = 0
    status: str = "not_generated"
    is_manual: bool = False
    has_content: bool = Field(default=False, description="是否已生成内容")
    selected_version_id: Optional[int] = None
    version_count: int = Field(default=0, description="版本数量")

    class Config:
        from_attributes = True


class SourceFileDetail(SourceFileResponse):
    """源文件详情（包含内容）"""
    content: Optional[str] = Field(default=None, description="当前选中版本的内容")
    review_prompt: Optional[str] = Field(default=None, description="审查Prompt")


class SourceFileListResponse(BaseModel):
    """源文件列表响应"""
    files: List[SourceFileResponse]
    total: int


# ==================== 文件版本相关 ====================

class FileVersionResponse(BaseModel):
    """文件Prompt版本响应"""
    id: int
    file_id: int
    version_label: Optional[str] = None
    provider: Optional[str] = None
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FileVersionListResponse(BaseModel):
    """文件版本列表响应"""
    versions: List[FileVersionResponse]
    selected_version_id: Optional[int] = None


# ==================== 目录结构生成相关 ====================

class GenerateDirectoryStructureRequest(BaseModel):
    """生成目录结构请求"""
    module_number: int = Field(..., description="目标模块编号")
    preference: Optional[str] = Field(default=None, description="生成偏好指导，如：更细粒度划分、偏向特定目录风格等")
    clear_existing: bool = Field(default=True, description="是否清除该模块的现有目录结构")


class GenerateDirectoryStructureResponse(BaseModel):
    """生成目录结构响应"""
    module_number: int
    module_name: str
    directories_created: int
    files_created: int
    root_path: str
    ai_message: str


class BatchGenerateDirectoryRequest(BaseModel):
    """批量生成目录结构请求"""
    module_numbers: List[int] = Field(..., description="要生成目录结构的模块编号列表")
    preference: Optional[str] = Field(default=None, description="生成偏好指导")


# ==================== 文件Prompt生成相关 ====================

class GenerateFilePromptRequest(BaseModel):
    """生成文件Prompt请求"""
    writing_notes: Optional[str] = Field(default=None, description="额外的实现指令")


class GenerateFilePromptResponse(BaseModel):
    """生成文件Prompt响应（非流式）"""
    file_id: int
    version_id: int
    content: str
    ai_message: str


class SaveFilePromptRequest(BaseModel):
    """保存文件Prompt请求"""
    content: str = Field(..., description="Prompt内容", min_length=1)
    version_label: Optional[str] = Field(default=None, description="版本标签")


class SelectFileVersionRequest(BaseModel):
    """选择文件版本请求"""
    version_id: int


# ==================== 审查Prompt相关 ====================

class GenerateReviewPromptRequest(BaseModel):
    """生成审查Prompt请求"""
    writing_notes: Optional[str] = Field(default=None, description="额外的审查指令")


class GenerateReviewPromptResponse(BaseModel):
    """生成审查Prompt响应"""
    file_id: int
    content: str


class SaveReviewPromptRequest(BaseModel):
    """保存审查Prompt请求"""
    content: str = Field(..., description="审查Prompt内容", min_length=1)


# ==================== 目录结构LLM输出相关 ====================

class LLMDirectoryNode(BaseModel):
    """LLM生成的目录节点"""
    name: str
    path: str
    node_type: str = "directory"
    description: str = ""
    module_number: Optional[int] = Field(default=None, description="所属模块编号")
    children: List["LLMDirectoryNode"] = Field(default_factory=list)
    files: List["LLMSourceFile"] = Field(default_factory=list)


class LLMSourceFile(BaseModel):
    """LLM生成的源文件"""
    filename: str
    file_type: str = "source"
    language: str = ""
    description: str = ""
    purpose: str = ""
    priority: str = "medium"
    module_number: Optional[int] = Field(default=None, description="所属模块编号")


class LLMDirectoryStructureOutput(BaseModel):
    """LLM生成目录结构的完整输出"""
    root_path: str = Field(..., description="模块根目录路径")
    directories: List[LLMDirectoryNode] = Field(default_factory=list)
    summary: str = Field(default="", description="目录结构说明")


# 解决循环引用
DirectoryNodeResponse.model_rebuild()
LLMDirectoryNode.model_rebuild()
