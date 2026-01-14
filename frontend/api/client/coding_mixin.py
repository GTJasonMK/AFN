"""
编程项目 Mixin

提供编程项目功能生成相关的API方法。
支持两层结构：系统(System) -> 模块(Module)
"""

from typing import Any, Dict, List, Optional


class CodingMixin:
    """编程项目方法 Mixin"""

    # ==================== 项目(Project) API ====================

    def list_coding_projects(
        self,
        page: int = 1,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取编程项目列表

        Args:
            page: 页码（从1开始）
            page_size: 每页数量

        Returns:
            项目列表
        """
        return self._request(
            'GET',
            '/api/coding',
            params={'page': page, 'page_size': page_size}
        )

    def create_coding_project(
        self,
        title: str,
        initial_prompt: str = "",
        skip_conversation: bool = False
    ) -> Dict[str, Any]:
        """
        创建编程项目

        Args:
            title: 项目标题
            initial_prompt: 初始提示词（需求描述）
            skip_conversation: 是否跳过需求对话（直接进入蓝图状态）

        Returns:
            创建的项目信息
        """
        return self._request(
            'POST',
            '/api/coding',
            {
                'title': title,
                'initial_prompt': initial_prompt,
                'skip_conversation': skip_conversation
            }
        )

    def get_coding_project(self, project_id: str) -> Dict[str, Any]:
        """
        获取编程项目详情

        Args:
            project_id: 项目ID

        Returns:
            项目详情
        """
        return self._request('GET', f'/api/coding/{project_id}')

    def update_coding_project(
        self,
        project_id: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新编程项目

        Args:
            project_id: 项目ID
            title: 新标题

        Returns:
            更新后的项目信息
        """
        payload = {}
        if title is not None:
            payload['title'] = title

        return self._request('PATCH', f'/api/coding/{project_id}', payload)

    def delete_coding_project(self, project_id: str) -> None:
        """
        删除编程项目

        Args:
            project_id: 项目ID
        """
        return self._request('DELETE', f'/api/coding/{project_id}')

    def delete_coding_projects(self, project_ids: List[str]) -> None:
        """
        批量删除编程项目

        Args:
            project_ids: 项目ID列表
        """
        return self._request('POST', '/api/coding/batch-delete', project_ids)

    # ==================== 系统(System) API ====================

    def list_coding_systems(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取编程项目的系统列表

        Args:
            project_id: 项目ID

        Returns:
            系统列表，每个系统包含:
            - system_number: 系统编号
            - name: 系统名称
            - description: 系统描述
            - responsibilities: 职责列表
            - tech_requirements: 技术要求
            - module_count: 模块数量
            - generation_status: 生成状态
            - progress: 进度
        """
        return self._request('GET', f'/api/coding/{project_id}/systems')

    def get_coding_system(
        self,
        project_id: str,
        system_number: int
    ) -> Dict[str, Any]:
        """
        获取指定系统详情

        Args:
            project_id: 项目ID
            system_number: 系统编号

        Returns:
            系统详情数据
        """
        return self._request(
            'GET',
            f'/api/coding/{project_id}/systems/{system_number}'
        )

    def create_coding_system(
        self,
        project_id: str,
        name: str,
        description: str = "",
        responsibilities: Optional[List[str]] = None,
        tech_requirements: str = ""
    ) -> Dict[str, Any]:
        """
        手动创建系统

        Args:
            project_id: 项目ID
            name: 系统名称
            description: 系统描述
            responsibilities: 职责列表
            tech_requirements: 技术要求

        Returns:
            创建的系统数据
        """
        payload = {
            'name': name,
            'description': description,
            'responsibilities': responsibilities or [],
            'tech_requirements': tech_requirements,
        }
        return self._request('POST', f'/api/coding/{project_id}/systems', payload)

    def update_coding_system(
        self,
        project_id: str,
        system_number: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        responsibilities: Optional[List[str]] = None,
        tech_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新系统信息

        Args:
            project_id: 项目ID
            system_number: 系统编号
            name: 系统名称
            description: 系统描述
            responsibilities: 职责列表
            tech_requirements: 技术要求

        Returns:
            更新后的系统数据
        """
        payload = {}
        if name is not None:
            payload['name'] = name
        if description is not None:
            payload['description'] = description
        if responsibilities is not None:
            payload['responsibilities'] = responsibilities
        if tech_requirements is not None:
            payload['tech_requirements'] = tech_requirements

        return self._request(
            'PUT',
            f'/api/coding/{project_id}/systems/{system_number}',
            payload
        )

    def delete_coding_system(
        self,
        project_id: str,
        system_number: int
    ) -> Dict[str, Any]:
        """
        删除系统（同时删除关联的模块）

        Args:
            project_id: 项目ID
            system_number: 系统编号

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/coding/{project_id}/systems/{system_number}'
        )

    def generate_coding_systems(
        self,
        project_id: str,
        min_systems: int = 3,
        max_systems: int = 8,
        preference: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        根据架构设计自动生成系统划分

        Args:
            project_id: 项目ID
            min_systems: 最少系统数
            max_systems: 最多系统数
            preference: 重新生成时的偏好指导（可选）

        Returns:
            生成的系统列表
        """
        payload = {
            'min_systems': min_systems,
            'max_systems': max_systems,
        }
        if preference:
            payload['preference'] = preference
        return self._request(
            'POST',
            f'/api/coding/{project_id}/systems/generate',
            payload,
            timeout=180
        )

    # ==================== 模块(Module) API ====================

    def list_coding_modules(
        self,
        project_id: str,
        system_number: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        获取模块列表

        Args:
            project_id: 项目ID
            system_number: 按系统编号过滤（可选）

        Returns:
            模块列表，每个模块包含:
            - module_number: 全局模块编号
            - system_number: 所属系统编号
            - name: 模块名称
            - type: 模块类型
            - description: 模块描述
            - interface: 接口说明
            - dependencies: 依赖模块列表
            - generation_status: 生成状态
        """
        params = {}
        if system_number is not None:
            params['system_number'] = system_number

        return self._request('GET', f'/api/coding/{project_id}/modules', params=params)

    def get_coding_module(
        self,
        project_id: str,
        module_number: int
    ) -> Dict[str, Any]:
        """
        获取指定模块详情

        Args:
            project_id: 项目ID
            module_number: 模块编号

        Returns:
            模块详情数据
        """
        return self._request(
            'GET',
            f'/api/coding/{project_id}/modules/{module_number}'
        )

    def create_coding_module(
        self,
        project_id: str,
        system_number: int,
        name: str,
        module_type: str = "service",
        description: str = "",
        interface: str = "",
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        手动创建模块

        Args:
            project_id: 项目ID
            system_number: 所属系统编号
            name: 模块名称
            module_type: 模块类型
            description: 模块描述
            interface: 接口说明
            dependencies: 依赖模块列表

        Returns:
            创建的模块数据
        """
        payload = {
            'system_number': system_number,
            'name': name,
            'type': module_type,
            'description': description,
            'interface': interface,
            'dependencies': dependencies or [],
        }
        return self._request('POST', f'/api/coding/{project_id}/modules', payload)

    def update_coding_module(
        self,
        project_id: str,
        module_number: int,
        name: Optional[str] = None,
        module_type: Optional[str] = None,
        description: Optional[str] = None,
        interface: Optional[str] = None,
        dependencies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        更新模块信息

        Args:
            project_id: 项目ID
            module_number: 模块编号
            name: 模块名称
            module_type: 模块类型
            description: 模块描述
            interface: 接口说明
            dependencies: 依赖模块列表

        Returns:
            更新后的模块数据
        """
        payload = {}
        if name is not None:
            payload['name'] = name
        if module_type is not None:
            payload['type'] = module_type
        if description is not None:
            payload['description'] = description
        if interface is not None:
            payload['interface'] = interface
        if dependencies is not None:
            payload['dependencies'] = dependencies

        return self._request(
            'PUT',
            f'/api/coding/{project_id}/modules/{module_number}',
            payload
        )

    def delete_coding_module(
        self,
        project_id: str,
        module_number: int
    ) -> Dict[str, Any]:
        """
        删除模块

        Args:
            project_id: 项目ID
            module_number: 模块编号

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/coding/{project_id}/modules/{module_number}'
        )

    def generate_coding_modules(
        self,
        project_id: str,
        system_number: int,
        min_modules: int = 3,
        max_modules: int = 8,
        preference: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        为指定系统生成模块列表

        Args:
            project_id: 项目ID
            system_number: 目标系统编号
            min_modules: 最少模块数
            max_modules: 最多模块数
            preference: 重新生成时的偏好指导（可选）

        Returns:
            生成的模块列表
        """
        payload = {
            'system_number': system_number,
            'min_modules': min_modules,
            'max_modules': max_modules,
        }
        if preference:
            payload['preference'] = preference
        return self._request(
            'POST',
            f'/api/coding/{project_id}/modules/generate',
            payload,
            timeout=180
        )

    def get_generate_all_modules_stream_url(self, project_id: str) -> str:
        """
        获取批量生成所有系统模块的SSE流式URL

        Args:
            project_id: 项目ID

        Returns:
            SSE流式URL
        """
        return f"{self.base_url}/api/coding/{project_id}/modules/generate-all"

    # ==================== 依赖关系(Dependencies) API ====================

    def list_coding_dependencies(self, project_id: str) -> List[Dict[str, Any]]:
        """
        获取模块依赖关系列表

        Args:
            project_id: 项目ID

        Returns:
            依赖关系列表
        """
        return self._request('GET', f'/api/coding/{project_id}/dependencies')

    def create_coding_dependency(
        self,
        project_id: str,
        from_module: str,
        to_module: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        创建模块依赖关系

        Args:
            project_id: 项目ID
            from_module: 源模块名称
            to_module: 目标模块名称
            description: 依赖描述

        Returns:
            创建的依赖关系
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/dependencies',
            {
                'from_module': from_module,
                'to_module': to_module,
                'description': description
            }
        )

    def delete_coding_dependency(
        self,
        project_id: str,
        dependency_id: int,
        from_module: str,
        to_module: str
    ) -> Dict[str, Any]:
        """
        删除模块依赖关系

        Args:
            project_id: 项目ID
            dependency_id: 依赖关系ID（伪ID，用于兼容）
            from_module: 源模块名称
            to_module: 目标模块名称

        Returns:
            删除结果
        """
        return self._request(
            'DELETE',
            f'/api/coding/{project_id}/dependencies/{dependency_id}',
            params={'from_module': from_module, 'to_module': to_module}
        )

    def sync_coding_dependencies(self, project_id: str) -> Dict[str, Any]:
        """
        根据模块的dependencies字段同步依赖关系表

        遍历所有模块，将其dependencies字段中声明的依赖同步到relationships_表。
        这是一个幂等操作，会清除旧的依赖关系并重新创建。

        Args:
            project_id: 项目ID

        Returns:
            同步结果:
            - success: 是否成功
            - synced_count: 同步的依赖数量
            - dependencies: 同步的依赖列表
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/dependencies/sync'
        )

    # ==================== RAG 入库和检索 API ====================

    def reindex_coding_project(self, project_id: str) -> Dict[str, Any]:
        """
        将编程项目的功能Prompt入库到向量数据库

        遍历所有已生成内容的功能，将其Prompt内容向量化并存储到ChromaDB。
        这是一个幂等操作，会清除旧的索引并重新创建。

        Args:
            project_id: 项目ID

        Returns:
            入库结果:
            - success: 是否成功
            - indexed_count: 入库的功能数量
            - message: 结果消息
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/rag/reindex',
            timeout=120
        )

    def query_coding_rag(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
        data_types: Optional[List[str]] = None,
        use_type_weights: bool = True
    ) -> Dict[str, Any]:
        """
        检索编程项目的RAG上下文

        根据查询内容从向量数据库中检索相关的功能Prompt片段。

        Args:
            project_id: 项目ID
            query: 查询内容
            top_k: 返回结果数量
            data_types: 限定数据类型列表（可选）
            use_type_weights: 是否使用类型权重

        Returns:
            检索结果:
            - chunks: 相关片段列表
            - summaries: 相关摘要列表
        """
        payload = {
            'query': query,
            'top_k': top_k,
            'use_type_weights': use_type_weights
        }
        if data_types:
            payload['data_types'] = data_types

        return self._request(
            'POST',
            f'/api/coding/{project_id}/rag/query',
            payload
        )

    def check_rag_completeness(self, project_id: str) -> Dict[str, Any]:
        """
        检查编程项目的RAG入库完整性

        对比数据库记录数和向量库记录数，返回各类型的完整性状态。

        Args:
            project_id: 项目ID

        Returns:
            完整性报告:
            - project_id: 项目ID
            - complete: 是否完整
            - total_db_count: 数据库总记录数
            - total_vector_count: 向量库总记录数
            - types: 各类型详情字典
        """
        return self._request(
            'GET',
            f'/api/coding/{project_id}/rag/completeness'
        )

    def ingest_all_rag_data(
        self,
        project_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        智能入库 - 将编程项目数据入库到向量数据库

        智能模式（默认）：先检查完整性，只入库不完整的类型。
        强制模式（force=True）：遍历10种数据类型，全部重新入库。

        Args:
            project_id: 项目ID
            force: 是否强制全量入库（默认False）

        Returns:
            入库结果:
            - success: 是否成功
            - is_complete: 入库前是否已完整（True表示无需入库）
            - total_items: 总项目数
            - added: 成功入库数
            - skipped: 跳过的类型数
            - failed: 失败数
            - details: 各类型详情
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            "=== ingest_all_rag_data 被调用 === project_id=%s force=%s",
            project_id, force
        )

        # 始终发送请求体，即使 force=False
        payload = {'force': force}
        logger.info("发送请求到 /api/coding/%s/rag/ingest-all payload=%s", project_id, payload)

        return self._request(
            'POST',
            f'/api/coding/{project_id}/rag/ingest-all',
            payload,
            timeout=300  # 完整入库可能需要较长时间
        )

    # ==================== 需求分析对话 API ====================

    def get_coding_inspiration_history(
        self,
        project_id: str
    ) -> List[Dict[str, Any]]:
        """
        获取编程项目的需求分析对话历史

        Args:
            project_id: 项目ID

        Returns:
            对话历史列表，每条包含:
            - id: 记录ID
            - role: 角色 (user/assistant)
            - content: 消息内容
            - created_at: 创建时间
        """
        return self._request(
            'GET',
            f'/api/coding/{project_id}/inspiration/history'
        )

    def generate_coding_blueprint(
        self,
        project_id: str,
        allow_incomplete: bool = False,
        preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成编程项目的架构设计蓝图

        基于需求分析对话内容，生成项目的架构设计文档。

        Args:
            project_id: 项目ID
            allow_incomplete: 是否允许在对话未完成时生成（自动补全模式）
            preference: 重新生成时的偏好指导（可选）

        Returns:
            生成结果:
            - success: 是否成功
            - blueprint: 蓝图数据
        """
        payload = {
            'allow_incomplete': allow_incomplete,
        }
        if preference:
            payload['preference'] = preference

        return self._request(
            'POST',
            f'/api/coding/{project_id}/blueprint/generate',
            payload,
            timeout=180
        )

    # ==================== 目录结构 API ====================

    def get_directory_tree(self, project_id: str) -> Dict[str, Any]:
        """
        获取项目的完整目录树

        Args:
            project_id: 项目ID

        Returns:
            目录树数据:
            - project_id: 项目ID
            - root_nodes: 根目录节点列表
            - total_directories: 目录总数
            - total_files: 文件总数
        """
        return self._request('GET', f'/api/coding/{project_id}/directories/tree')

    def generate_directory_structure(
        self,
        project_id: str,
        module_number: int,
        preference: Optional[str] = None,
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        为指定模块生成目录结构

        Args:
            project_id: 项目ID
            module_number: 模块编号
            preference: 生成偏好指导
            clear_existing: 是否清除该模块的现有目录结构

        Returns:
            生成结果:
            - module_number: 模块编号
            - module_name: 模块名称
            - directories_created: 创建的目录数
            - files_created: 创建的文件数
            - root_path: 根目录路径
            - ai_message: AI消息
        """
        payload = {
            'module_number': module_number,
            'clear_existing': clear_existing,
        }
        if preference:
            payload['preference'] = preference

        return self._request(
            'POST',
            f'/api/coding/{project_id}/directories/generate',
            payload,
            timeout=180
        )

    def create_directory(
        self,
        project_id: str,
        name: str,
        parent_id: Optional[int] = None,
        node_type: str = "directory",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        手动创建目录

        Args:
            project_id: 项目ID
            name: 目录名称
            parent_id: 父目录ID（可选，为空则创建根目录）
            node_type: 节点类型（directory/package）
            description: 目录说明

        Returns:
            创建的目录节点数据
        """
        payload = {
            'name': name,
            'node_type': node_type,
        }
        if parent_id is not None:
            payload['parent_id'] = parent_id
        if description:
            payload['description'] = description

        return self._request('POST', f'/api/coding/{project_id}/directories', payload)

    def update_directory(
        self,
        project_id: str,
        node_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        更新目录

        Args:
            project_id: 项目ID
            node_id: 目录节点ID
            name: 新名称
            description: 新描述
            sort_order: 排序顺序

        Returns:
            更新后的目录节点数据
        """
        payload = {}
        if name is not None:
            payload['name'] = name
        if description is not None:
            payload['description'] = description
        if sort_order is not None:
            payload['sort_order'] = sort_order

        return self._request('PATCH', f'/api/coding/{project_id}/directories/{node_id}', payload)

    def delete_directory(self, project_id: str, node_id: int) -> Dict[str, Any]:
        """
        删除目录（级联删除子目录和文件）

        Args:
            project_id: 项目ID
            node_id: 目录节点ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/coding/{project_id}/directories/{node_id}')

    # ==================== 源文件 API ====================

    def list_source_files(
        self,
        project_id: str,
        module_number: Optional[int] = None,
        directory_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        获取源文件列表

        Args:
            project_id: 项目ID
            module_number: 按模块筛选
            directory_id: 按目录筛选

        Returns:
            文件列表:
            - files: 文件列表
            - total: 总数
        """
        params = {}
        if module_number is not None:
            params['module_number'] = module_number
        if directory_id is not None:
            params['directory_id'] = directory_id

        return self._request('GET', f'/api/coding/{project_id}/files', params=params)

    def get_source_file(self, project_id: str, file_id: int) -> Dict[str, Any]:
        """
        获取源文件详情

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            文件详情（包含内容）
        """
        return self._request('GET', f'/api/coding/{project_id}/files/{file_id}')

    def create_source_file(
        self,
        project_id: str,
        directory_id: int,
        filename: str,
        file_type: str = "source",
        language: Optional[str] = None,
        description: Optional[str] = None,
        purpose: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        手动创建源文件

        Args:
            project_id: 项目ID
            directory_id: 所属目录ID
            filename: 文件名
            file_type: 文件类型（source/config/test/doc）
            language: 编程语言
            description: 文件描述
            purpose: 文件用途
            priority: 优先级

        Returns:
            创建的文件数据
        """
        payload = {
            'directory_id': directory_id,
            'filename': filename,
            'file_type': file_type,
            'priority': priority,
        }
        if language:
            payload['language'] = language
        if description:
            payload['description'] = description
        if purpose:
            payload['purpose'] = purpose

        return self._request('POST', f'/api/coding/{project_id}/files', payload)

    def update_source_file(
        self,
        project_id: str,
        file_id: int,
        filename: Optional[str] = None,
        description: Optional[str] = None,
        purpose: Optional[str] = None,
        priority: Optional[str] = None,
        sort_order: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        更新源文件信息

        Args:
            project_id: 项目ID
            file_id: 文件ID
            filename: 新文件名
            description: 新描述
            purpose: 新用途
            priority: 新优先级
            sort_order: 排序顺序

        Returns:
            更新后的文件数据
        """
        payload = {}
        if filename is not None:
            payload['filename'] = filename
        if description is not None:
            payload['description'] = description
        if purpose is not None:
            payload['purpose'] = purpose
        if priority is not None:
            payload['priority'] = priority
        if sort_order is not None:
            payload['sort_order'] = sort_order

        return self._request('PATCH', f'/api/coding/{project_id}/files/{file_id}', payload)

    def delete_source_file(self, project_id: str, file_id: int) -> Dict[str, Any]:
        """
        删除源文件

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            删除结果
        """
        return self._request('DELETE', f'/api/coding/{project_id}/files/{file_id}')

    # ==================== 文件Prompt生成 API ====================

    def generate_file_prompt(
        self,
        project_id: str,
        file_id: int,
        writing_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成文件Prompt（同步模式）

        Args:
            project_id: 项目ID
            file_id: 文件ID
            writing_notes: 额外的写作指导

        Returns:
            生成结果:
            - success: 是否成功
            - file_id: 文件ID
            - version_id: 版本ID
            - content: 生成的内容
        """
        payload = {}
        if writing_notes:
            payload['writing_notes'] = writing_notes

        return self._request(
            'POST',
            f'/api/coding/{project_id}/files/{file_id}/generate',
            payload if payload else None,
            timeout=300
        )

    def get_file_prompt_generate_stream_url(
        self,
        project_id: str,
        file_id: int
    ) -> str:
        """
        获取文件Prompt生成的SSE流式URL

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            SSE流式URL
        """
        return f"{self.base_url}/api/coding/{project_id}/files/{file_id}/generate-stream"

    def save_file_prompt(
        self,
        project_id: str,
        file_id: int,
        content: str,
        version_label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存文件Prompt内容

        Args:
            project_id: 项目ID
            file_id: 文件ID
            content: Prompt内容
            version_label: 版本标签

        Returns:
            保存结果:
            - success: 是否成功
            - version_id: 版本ID
            - word_count: 字数
        """
        payload = {'content': content}
        if version_label:
            payload['version_label'] = version_label

        return self._request(
            'POST',
            f'/api/coding/{project_id}/files/{file_id}/save',
            payload
        )

    def get_file_versions(self, project_id: str, file_id: int) -> Dict[str, Any]:
        """
        获取文件的所有版本

        Args:
            project_id: 项目ID
            file_id: 文件ID

        Returns:
            版本列表:
            - versions: 版本列表
            - selected_version_id: 当前选中的版本ID
        """
        return self._request('GET', f'/api/coding/{project_id}/files/{file_id}/versions')

    def select_file_version(
        self,
        project_id: str,
        file_id: int,
        version_id: int
    ) -> Dict[str, Any]:
        """
        选择文件版本

        Args:
            project_id: 项目ID
            file_id: 文件ID
            version_id: 版本ID

        Returns:
            选择结果:
            - success: 是否成功
            - selected_version_id: 选中的版本ID
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/files/{file_id}/select-version',
            {'version_id': version_id}
        )

    # ==================== 审查Prompt API ====================

    def generate_file_review(
        self,
        project_id: str,
        file_id: int,
        writing_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成文件审查Prompt

        Args:
            project_id: 项目ID
            file_id: 文件ID
            writing_notes: 额外的写作指导

        Returns:
            生成结果:
            - success: 是否成功
            - file_id: 文件ID
            - content: 生成的审查内容
        """
        payload = {}
        if writing_notes:
            payload['writing_notes'] = writing_notes

        return self._request(
            'POST',
            f'/api/coding/{project_id}/files/{file_id}/generate-review',
            payload if payload else None,
            timeout=300
        )

    def save_file_review(
        self,
        project_id: str,
        file_id: int,
        content: str
    ) -> Dict[str, Any]:
        """
        保存文件审查Prompt

        Args:
            project_id: 项目ID
            file_id: 文件ID
            content: 审查Prompt内容

        Returns:
            保存结果
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/files/{file_id}/save-review',
            {'content': content}
        )

    # ==================== 目录规划Agent API ====================

    def get_directory_plan_agent_url(
        self,
        project_id: str,
    ) -> str:
        """
        获取目录规划Agent的SSE流式URL（真正调用LLM）

        Args:
            project_id: 项目ID

        Returns:
            SSE流式URL
        """
        return f"{self.base_url}/api/coding/{project_id}/directories/plan-agent"

    def get_directory_agent_state(self, project_id: str) -> dict:
        """
        获取目录规划Agent的状态

        用于检查是否有可恢复的暂停状态。

        Args:
            project_id: 项目ID

        Returns:
            状态信息:
            - has_paused_state: 是否有暂停状态
            - current_phase: 当前阶段
            - total_directories: 已生成目录数
            - total_files: 已生成文件数
            - progress_percent: 进度百分比
            - progress_message: 进度消息
            - paused_at: 暂停时间
        """
        return self._request(
            'GET',
            f'/api/coding/{project_id}/directories/agent-state'
        )

    def pause_directory_agent(
        self,
        project_id: str,
        reason: str = "用户手动停止"
    ) -> dict:
        """
        暂停目录规划Agent

        保存当前状态以便后续恢复。

        Args:
            project_id: 项目ID
            reason: 暂停原因

        Returns:
            暂停结果:
            - success: 是否成功
            - total_directories: 已生成目录数
            - total_files: 已生成文件数
            - current_phase: 当前阶段
        """
        return self._request(
            'POST',
            f'/api/coding/{project_id}/directories/pause-agent',
            {'reason': reason}
        )

    def clear_directory_agent_state(self, project_id: str) -> dict:
        """
        清除目录规划Agent的状态

        用于放弃暂停的状态，重新开始。

        Args:
            project_id: 项目ID

        Returns:
            清除结果:
            - success: 是否成功
            - deleted: 是否有状态被删除
        """
        return self._request(
            'DELETE',
            f'/api/coding/{project_id}/directories/agent-state'
        )
