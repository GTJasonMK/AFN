"""
目录生成器Schema定义

定义目录树节点和LLM输出格式。
使用扁平化列表而非嵌套结构，便于后处理构建目录树。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== 目录树节点（用于构建树结构） ====================

@dataclass
class PlannedFile:
    """规划的源文件

    包含完整的文件规划信息，用于后续生成代码Prompt。
    """
    filename: str
    file_path: str
    file_type: str = "source"  # source/config/test/doc
    language: str = "python"
    description: str = ""      # 文件功能描述
    purpose: str = ""          # 文件存在理由
    priority: str = "medium"   # high/medium/low
    module_number: Optional[int] = None

    # 依赖相关
    dependencies: List[int] = field(default_factory=list)  # 依赖的模块编号
    dependency_reasons: str = ""  # 依赖原因说明

    # 实现指导
    implementation_notes: str = ""  # 实现备注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "language": self.language,
            "description": self.description,
            "purpose": self.purpose,
            "priority": self.priority,
            "module_number": self.module_number,
            "dependencies": self.dependencies,
            "dependency_reasons": self.dependency_reasons,
            "implementation_notes": self.implementation_notes,
        }


@dataclass
class PlannedDirectory:
    """规划的目录节点"""
    name: str
    path: str
    node_type: str = "directory"  # directory/package
    description: str = ""
    module_number: Optional[int] = None
    files: List[PlannedFile] = field(default_factory=list)
    children: List["PlannedDirectory"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "node_type": self.node_type,
            "description": self.description,
            "module_number": self.module_number,
            "files": [f.to_dict() for f in self.files],
            "children": [c.to_dict() for c in self.children],
        }

    def count_files(self) -> int:
        """递归统计文件数量"""
        count = len(self.files)
        for child in self.children:
            count += child.count_files()
        return count

    def count_directories(self) -> int:
        """递归统计目录数量"""
        count = 1  # 自己
        for child in self.children:
            count += child.count_directories()
        return count


# ==================== LLM输出Schema ====================

class DirectorySpec(BaseModel):
    """目录规格（扁平化）"""
    path: str = Field(..., description="完整路径，如 src/services/auth")
    description: str = Field(default="", description="目录用途说明")
    module_numbers: List[int] = Field(default_factory=list, description="关联的模块编号列表")


class FileSpec(BaseModel):
    """文件规格

    每个文件需要完整说明：
    1. 为什么需要这个文件（purpose）
    2. 这个文件要实现什么功能（description）
    3. 依赖哪些模块（dependencies）
    4. 为什么需要这些依赖（dependency_reasons）
    """
    path: str = Field(..., description="完整文件路径，如 src/services/auth/service.py")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(default="source", description="文件类型：source/config/test/doc")
    language: str = Field(default="python", description="编程语言")
    description: str = Field(default="", description="文件功能描述：这个文件要实现什么功能")
    purpose: str = Field(default="", description="文件存在理由：为什么需要这个文件，解决什么问题")
    module_number: int = Field(..., description="所属模块编号")
    priority: str = Field(default="medium", description="优先级：high/medium/low")

    # 依赖相关字段
    dependencies: List[int] = Field(
        default_factory=list,
        description="依赖的模块编号列表，如 [1, 3, 5] 表示依赖模块1、3、5"
    )
    dependency_reasons: str = Field(
        default="",
        description="依赖原因说明：为什么需要这些依赖，每个依赖解决什么问题"
    )

    # 实现指导
    implementation_notes: str = Field(
        default="",
        description="实现备注：关键实现细节、注意事项、与其他模块的交互方式"
    )


class BruteForceOutput(BaseModel):
    """目录结构生成的输出格式"""
    root_path: str = Field(..., description="项目根路径，如 src 或 backend")
    directories: List[DirectorySpec] = Field(..., description="完整的目录列表（扁平化）")
    files: List[FileSpec] = Field(..., description="完整的文件列表")
    shared_modules: List[str] = Field(default_factory=list, description="识别出的共享模块目录路径")
    architecture_notes: str = Field(default="", description="架构说明")
