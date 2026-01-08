"""
NovelDetail Mixins - 提供页面功能的模块化实现

- HeaderManagerMixin: Header创建和样式
- TabManagerMixin: Tab导航管理
- SectionLoaderMixin: Section加载
- AvatarHandlerMixin: 头像处理
- EditDispatcherMixin: 编辑请求分发
- SaveManagerMixin: 保存管理
- BlueprintRefinerMixin: 蓝图优化
- ImportAnalyzerMixin: 导入分析
- RAGManagerMixin: RAG数据同步管理
"""

from .header_manager import HeaderManagerMixin
from .tab_manager import TabManagerMixin
from .section_loader import SectionLoaderMixin
from .avatar_handler import AvatarHandlerMixin
from .edit_dispatcher import EditDispatcherMixin
from .save_manager import SaveManagerMixin
from .blueprint_refiner import BlueprintRefinerMixin
from .import_analyzer import ImportAnalyzerMixin
from .rag_manager import RAGManagerMixin

__all__ = [
    'HeaderManagerMixin',
    'TabManagerMixin',
    'SectionLoaderMixin',
    'AvatarHandlerMixin',
    'EditDispatcherMixin',
    'SaveManagerMixin',
    'BlueprintRefinerMixin',
    'ImportAnalyzerMixin',
    'RAGManagerMixin',
]
