"""
首页模块

VS风格欢迎页面，包含项目管理、粒子特效背景等功能。

主要导出:
    - HomePage: 首页主类
    - CREATIVE_QUOTES: 创作箴言集
"""

from .core import HomePage
from .constants import CREATIVE_QUOTES, get_title_sort_key
from .particles import ParticleBackground
from .cards import RecentProjectCard, TabButton, TabBar

__all__ = [
    'HomePage',
    'CREATIVE_QUOTES',
    'get_title_sort_key',
    'ParticleBackground',
    'RecentProjectCard',
    'TabButton',
    'TabBar',
]
