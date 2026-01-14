"""
目录树构建器

将第一阶段的扁平化目录/文件列表转换为树形结构。
关键特性：
1. 自动创建缺失的父目录
2. 正确建立父子关系
3. 将文件分配到对应目录
"""

import logging
from typing import Dict, List, Optional, Set, Tuple

from .schemas import PlannedDirectory, PlannedFile
from .schemas import BruteForceOutput, DirectorySpec, FileSpec

logger = logging.getLogger(__name__)


class DirectoryTreeBuilder:
    """目录树构建器"""

    def __init__(self):
        self.path_to_node: Dict[str, PlannedDirectory] = {}
        self.root_nodes: List[PlannedDirectory] = []
        self.all_files: List[PlannedFile] = []

    def build(self, output: BruteForceOutput) -> Tuple[List[PlannedDirectory], List[PlannedFile]]:
        """
        从扁平列表构建目录树

        Args:
            output: 第一阶段的输出

        Returns:
            (根目录列表, 所有文件列表)
        """
        self.path_to_node = {}
        self.root_nodes = []
        self.all_files = []

        # 1. 按路径深度排序目录（浅→深）
        sorted_dirs = sorted(output.directories, key=lambda d: d.path.count('/'))

        # 2. 创建所有目录节点
        for dir_spec in sorted_dirs:
            self._create_directory_node(dir_spec)

        # 3. 分配文件到目录
        for file_spec in output.files:
            self._assign_file(file_spec)

        logger.info(
            "目录树构建完成: 根目录=%d, 总目录=%d, 总文件=%d",
            len(self.root_nodes),
            len(self.path_to_node),
            len(self.all_files),
        )

        return self.root_nodes, self.all_files

    def _create_directory_node(self, dir_spec: DirectorySpec) -> PlannedDirectory:
        """
        创建目录节点，确保父目录存在

        Args:
            dir_spec: 目录规格

        Returns:
            创建的目录节点
        """
        path = dir_spec.path.strip('/')

        # 如果已存在，直接返回
        if path in self.path_to_node:
            return self.path_to_node[path]

        # 解析路径
        parts = path.split('/')
        name = parts[-1]

        # 确定module_number
        module_number = dir_spec.module_numbers[0] if dir_spec.module_numbers else None

        # 创建节点
        node = PlannedDirectory(
            name=name,
            path=path,
            node_type="package" if name == "__init__" else "directory",
            description=dir_spec.description,
            module_number=module_number,
            files=[],
            children=[],
        )

        # 查找或创建父目录
        if len(parts) > 1:
            parent_path = '/'.join(parts[:-1])
            parent_node = self._ensure_parent_exists(parent_path)
            if parent_node:
                parent_node.children.append(node)
            else:
                # 父目录创建失败，作为根节点
                self.root_nodes.append(node)
        else:
            # 顶层目录
            self.root_nodes.append(node)

        self.path_to_node[path] = node
        return node

    def _ensure_parent_exists(self, parent_path: str) -> Optional[PlannedDirectory]:
        """
        确保父目录存在，如不存在则创建

        Args:
            parent_path: 父目录路径

        Returns:
            父目录节点
        """
        if parent_path in self.path_to_node:
            return self.path_to_node[parent_path]

        # 父目录不存在，需要创建
        parts = parent_path.split('/')

        # 递归确保祖先目录存在
        if len(parts) > 1:
            grandparent_path = '/'.join(parts[:-1])
            grandparent = self._ensure_parent_exists(grandparent_path)
        else:
            grandparent = None

        # 创建父目录
        name = parts[-1]
        parent_node = PlannedDirectory(
            name=name,
            path=parent_path,
            node_type="directory",
            description=f"自动创建的目录: {name}",
            module_number=None,
            files=[],
            children=[],
        )

        if grandparent:
            grandparent.children.append(parent_node)
        else:
            self.root_nodes.append(parent_node)

        self.path_to_node[parent_path] = parent_node
        logger.debug("自动创建父目录: %s", parent_path)

        return parent_node

    def _assign_file(self, file_spec: FileSpec) -> None:
        """
        将文件分配到对应目录

        Args:
            file_spec: 文件规格
        """
        file_path = file_spec.path.strip('/')
        parts = file_path.split('/')
        dir_path = '/'.join(parts[:-1]) if len(parts) > 1 else ""

        # 创建PlannedFile
        planned_file = PlannedFile(
            filename=file_spec.filename,
            file_path=file_path,
            file_type=file_spec.file_type,
            language=file_spec.language,
            description=file_spec.description,
            purpose=file_spec.purpose,
            priority=file_spec.priority,
            module_number=file_spec.module_number,
        )

        self.all_files.append(planned_file)

        # 查找目录并添加文件
        if dir_path and dir_path in self.path_to_node:
            self.path_to_node[dir_path].files.append(planned_file)
        elif dir_path:
            # 目录不存在，先创建
            dir_node = self._ensure_parent_exists(dir_path)
            if dir_node:
                dir_node.files.append(planned_file)
            else:
                logger.warning("无法为文件找到目录: %s", file_path)
        else:
            # 文件在根目录
            logger.warning("文件在根目录: %s", file_path)

    def validate_coverage(self, module_numbers: Set[int]) -> Tuple[Set[int], Set[int]]:
        """
        验证模块覆盖情况

        Args:
            module_numbers: 所有模块编号集合

        Returns:
            (已覆盖的模块, 缺失的模块)
        """
        covered = set()

        # 从目录收集
        for node in self.path_to_node.values():
            if node.module_number:
                covered.add(node.module_number)

        # 从文件收集
        for f in self.all_files:
            if f.module_number:
                covered.add(f.module_number)

        missing = module_numbers - covered

        return covered, missing

    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        total_files_in_tree = sum(len(node.files) for node in self.path_to_node.values())

        return {
            "total_directories": len(self.path_to_node),
            "root_directories": len(self.root_nodes),
            "total_files": len(self.all_files),
            "files_in_tree": total_files_in_tree,
            "orphan_files": len(self.all_files) - total_files_in_tree,
        }
