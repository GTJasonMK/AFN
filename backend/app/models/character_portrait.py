"""
角色立绘模型

存储角色立绘信息，支持多种风格的立绘生成和管理。
生成的立绘可在漫画生成时作为参考图（img2img）使用，以保持人物一致性。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class CharacterPortrait(Base):
    """角色立绘

    存储项目中各角色的立绘信息，包括：
    - 角色名称和描述
    - 立绘风格（动漫/漫画/写实）
    - 生成的图片路径
    - 是否为当前激活的立绘

    存储路径: storage/generated_images/{project_id}/portraits/{character_name}/
    """

    __tablename__ = "character_portraits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("novel_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 角色信息
    character_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    character_description: Mapped[Optional[str]] = mapped_column(Text())  # 角色外貌描述

    # 立绘信息
    style: Mapped[str] = mapped_column(
        String(50), nullable=False, default="anime"
    )  # anime, manga, realistic
    prompt: Mapped[Optional[str]] = mapped_column(Text())  # 生成时使用的提示词
    custom_prompt: Mapped[Optional[str]] = mapped_column(Text())  # 用户自定义提示词

    # 图片信息
    image_path: Mapped[Optional[str]] = mapped_column(Text())  # 相对于storage目录的路径
    file_name: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)

    # 生成信息
    model_name: Mapped[Optional[str]] = mapped_column(String(100))  # 使用的模型
    source_url: Mapped[Optional[str]] = mapped_column(Text())  # 来源URL（如果从远程下载）

    # 状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )  # 是否为当前使用的立绘

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    project: Mapped["NovelProject"] = relationship("NovelProject", back_populates="character_portraits")

    @property
    def storage_key(self) -> str:
        """获取存储路径键，用于构建完整文件路径"""
        # 清理角色名用于文件路径（移除特殊字符）
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.character_name)
        return f"images/{self.project_id}/portraits/{safe_name}/{self.file_name}"

    def __repr__(self) -> str:
        return f"<CharacterPortrait(id={self.id}, character={self.character_name}, style={self.style})>"
