from typing import Optional

from pydantic import BaseModel, Field


class SystemConfigBase(BaseModel):
    key: str = Field(..., description="配置键，需全局唯一")
    value: str = Field(..., description="配置值，统一存储为字符串")
    description: Optional[str] = Field(default=None, description="配置用途说明")


class SystemConfigCreate(SystemConfigBase):
    pass


class SystemConfigUpdate(BaseModel):
    value: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)


class SystemConfigRead(SystemConfigBase):
    class Config:
        from_attributes = True
