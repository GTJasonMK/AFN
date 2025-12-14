"""
图片生成服务模块

提供多厂商兼容的图片生成能力，支持：
- OpenAI兼容接口（DALL-E、nano-banana-pro等）
- Stability AI
- 本地ComfyUI
- 其他第三方服务
"""

from .service import ImageGenerationService
from .pdf_export import PDFExportService
from .schemas import (
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageConfigCreate,
    ImageConfigUpdate,
    ImageConfigResponse,
    ProviderType,
    PDFExportRequest,
    PDFExportResult,
)

__all__ = [
    "ImageGenerationService",
    "PDFExportService",
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "ImageConfigCreate",
    "ImageConfigUpdate",
    "ImageConfigResponse",
    "ProviderType",
    "PDFExportRequest",
    "PDFExportResult",
]
