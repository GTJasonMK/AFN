"""
图片生成配置模型

支持多厂商的图片生成API配置，类似于LLMConfig的设计模式。
支持的厂商类型：
- openai_compatible: OpenAI兼容接口（如nano-banana-pro、DALL-E等）
- stability: Stability AI (Stable Diffusion)
- midjourney: Midjourney API
- comfyui: 本地ComfyUI
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class ImageGenerationConfig(Base):
    """图片生成配置

    支持多种图片生成服务的配置管理，包括：
    - OpenAI兼容接口（DALL-E、nano-banana-pro等）
    - Stability AI
    - 本地ComfyUI
    - 其他第三方服务
    """

    __tablename__ = "image_generation_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 配置基本信息
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, default="默认配置")
    provider_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openai_compatible"
    )  # openai_compatible, stability, midjourney, comfyui

    # API配置
    api_base_url: Mapped[Optional[str]] = mapped_column(Text())
    api_key: Mapped[Optional[str]] = mapped_column(Text())
    model_name: Mapped[Optional[str]] = mapped_column(String(100), default="nano-banana-pro")

    # 默认生成参数
    default_style: Mapped[Optional[str]] = mapped_column(String(50), default="anime")
    default_ratio: Mapped[Optional[str]] = mapped_column(String(20), default="16:9")
    default_resolution: Mapped[Optional[str]] = mapped_column(String(20), default="1K")
    default_quality: Mapped[Optional[str]] = mapped_column(String(20), default="standard")

    # 高级参数（JSON格式存储）
    extra_params: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    # 配置状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 测试相关
    last_test_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    test_status: Mapped[Optional[str]] = mapped_column(String(50))  # success, failed, pending
    test_message: Mapped[Optional[str]] = mapped_column(Text())

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="image_configs")


class GeneratedImage(Base):
    """生成的图片记录

    按项目/章节/场景的结构保存图片，方便引用和管理。
    """

    __tablename__ = "generated_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联信息
    project_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    chapter_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scene_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 画格ID：用于精确匹配生成的图片属于哪个画格，格式如 "scene1_page1_panel1"
    panel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    # 章节版本关联：追踪图片是基于哪个版本的内容生成的
    chapter_version_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("chapter_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 图片信息
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text(), nullable=False)  # 相对于storage目录
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(50), default="image/png")
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)

    # 生成信息
    prompt: Mapped[Optional[str]] = mapped_column(Text())  # 使用的提示词
    negative_prompt: Mapped[Optional[str]] = mapped_column(Text())
    model_name: Mapped[Optional[str]] = mapped_column(String(100))
    style: Mapped[Optional[str]] = mapped_column(String(50))
    generation_params: Mapped[Optional[dict]] = mapped_column(JSON)  # 其他生成参数

    # 来源URL（如果是从远程下载的）
    source_url: Mapped[Optional[str]] = mapped_column(Text())

    # 用户选择状态
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否被选中用于导出

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @property
    def storage_key(self) -> str:
        """获取存储路径键，用于构建完整文件路径"""
        return f"images/{self.project_id}/chapter_{self.chapter_number}/scene_{self.scene_id}/{self.file_name}"
