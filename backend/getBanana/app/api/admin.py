"""
管理员API路由
- 系统状态
- 账号管理（增删改查、测试）
- 配置管理（导入导出）
- 代理测试
"""
import logging
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.utils.auth import require_admin, create_admin_token, generate_api_token
from app.config import config_manager, AccountConfig
from app.services.account_manager import account_manager, CooldownReason
from app.services.conversation_manager import conversation_manager
from app.services.image_service import image_service
from app.services.jwt_service import jwt_service, get_http_client

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class AccountCreate(BaseModel):
    team_id: str
    csesidx: str
    secure_c_ses: str
    host_c_oses: str = ""
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    note: str = ""
    available: bool = True


class AccountUpdate(BaseModel):
    team_id: Optional[str] = None
    csesidx: Optional[str] = None
    secure_c_ses: Optional[str] = None
    host_c_oses: Optional[str] = None
    user_agent: Optional[str] = None
    note: Optional[str] = None
    available: Optional[bool] = None


class ProxyTest(BaseModel):
    proxy: Optional[str] = None


class ConfigUpdate(BaseModel):
    proxy: Optional[str] = None
    admin_password: Optional[str] = None


@router.post("/login")
async def admin_login(request: LoginRequest):
    """
    管理员登录

    验证密码并返回管理员Token
    """
    config = config_manager.config

    # 验证密码
    if request.password != config.admin_password:
        raise HTTPException(status_code=401, detail="密码错误")

    # 生成Token
    token = create_admin_token(config.admin_secret_key, exp_seconds=86400)

    return {
        "token": token,
        "expires_in": 86400
    }


@router.get("/status")
async def get_system_status(token: str = Depends(require_admin)):
    """
    获取系统状态

    包括账号状态、会话统计等
    """
    account_status = account_manager.get_status()
    conversation_status = conversation_manager.get_status()

    return {
        "accounts": account_status,
        "conversations": conversation_status,
        "config": {
            "proxy": config_manager.config.proxy or "未配置",
            "api_tokens_count": len(config_manager.config.api_tokens)
        }
    }


# ==================== 账号管理 ====================

@router.get("/accounts")
async def list_accounts(token: str = Depends(require_admin)):
    """列出所有账号及其状态"""
    return account_manager.get_status()


@router.post("/accounts")
async def add_account(
    request: AccountCreate,
    token: str = Depends(require_admin)
):
    """添加新账号"""
    # 检查是否已存在相同csesidx的账号
    for acc in config_manager.config.accounts:
        if acc.csesidx == request.csesidx:
            raise HTTPException(status_code=400, detail="账号已存在（相同csesidx）")

    # 创建新账号配置
    new_account = AccountConfig(
        team_id=request.team_id,
        csesidx=request.csesidx,
        secure_c_ses=request.secure_c_ses,
        host_c_oses=request.host_c_oses,
        user_agent=request.user_agent,
        note=request.note,
        available=request.available
    )

    # 添加到配置
    config_manager.config.accounts.append(new_account)
    config_manager.save_config()

    # 重新加载账号
    account_manager.load_accounts()

    return {
        "success": True,
        "index": len(config_manager.config.accounts) - 1,
        "message": "账号添加成功"
    }


@router.put("/accounts/{index}")
async def update_account(
    index: int,
    request: AccountUpdate,
    token: str = Depends(require_admin)
):
    """更新账号配置"""
    if index < 0 or index >= len(config_manager.config.accounts):
        raise HTTPException(status_code=404, detail="账号不存在")

    acc_config = config_manager.config.accounts[index]
    account = account_manager.get_account(index)

    # 更新配置
    if request.team_id is not None:
        acc_config.team_id = request.team_id
    if request.csesidx is not None:
        acc_config.csesidx = request.csesidx
    if request.secure_c_ses is not None:
        acc_config.secure_c_ses = request.secure_c_ses
    if request.host_c_oses is not None:
        acc_config.host_c_oses = request.host_c_oses
    if request.user_agent is not None:
        acc_config.user_agent = request.user_agent
    if request.note is not None:
        acc_config.note = request.note
        if account:
            account.note = request.note
    if request.available is not None:
        acc_config.available = request.available
        if account:
            account.available = request.available

    config_manager.save_config()

    return {"success": True, "message": "账号更新成功"}


@router.delete("/accounts/{index}")
async def delete_account(
    index: int,
    token: str = Depends(require_admin)
):
    """删除账号"""
    if index < 0 or index >= len(config_manager.config.accounts):
        raise HTTPException(status_code=404, detail="账号不存在")

    # 从配置中删除
    config_manager.config.accounts.pop(index)
    config_manager.save_config()

    # 重新加载账号
    account_manager.load_accounts()

    return {"success": True, "message": "账号删除成功"}


@router.post("/accounts/{index}/toggle")
async def toggle_account(
    index: int,
    token: str = Depends(require_admin)
):
    """切换账号启用/禁用状态"""
    account = account_manager.get_account(index)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 切换状态
    new_state = not account.available
    account.available = new_state

    # 如果重新启用，清除冷却
    if new_state:
        account_manager.clear_account_cooldown(index)

    # 更新配置
    if index < len(config_manager.config.accounts):
        config_manager.config.accounts[index].available = new_state
        config_manager.save_config()

    return {
        "success": True,
        "available": new_state,
        "message": f"账号已{'启用' if new_state else '禁用'}"
    }


@router.get("/accounts/{index}/test")
async def test_account(
    index: int,
    token: str = Depends(require_admin)
):
    """测试账号JWT获取"""
    account = account_manager.get_account(index)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    try:
        # 强制刷新JWT
        jwt, expires_at = await jwt_service.get_jwt_for_account(account, force_refresh=True)
        return {
            "success": True,
            "message": "JWT获取成功",
            "expires_at": expires_at
        }
    except Exception as e:
        # 根据错误类型设置冷却
        error_msg = str(e)
        if "401" in error_msg or "认证" in error_msg:
            account_manager.mark_account_cooldown(index, CooldownReason.AUTH_ERROR)
        elif "429" in error_msg or "限额" in error_msg:
            account_manager.mark_account_cooldown(index, CooldownReason.RATE_LIMIT)
        else:
            account_manager.mark_account_cooldown(index, CooldownReason.GENERIC_ERROR)

        return {
            "success": False,
            "message": error_msg
        }


@router.post("/accounts/{index}/clear-cooldown")
async def clear_account_cooldown(
    index: int,
    token: str = Depends(require_admin)
):
    """清除账号冷却状态"""
    account = account_manager.get_account(index)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account_manager.clear_account_cooldown(index)

    return {"message": f"账号 {index} 冷却已清除"}


@router.post("/accounts/{index}/cooldown")
async def set_account_cooldown(
    index: int,
    seconds: int = 300,
    reason: str = "manual",
    token: str = Depends(require_admin)
):
    """手动设置账号冷却"""
    account = account_manager.get_account(index)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account_manager.mark_account_cooldown(
        index,
        CooldownReason.GENERIC_ERROR,
        custom_seconds=seconds
    )

    return {"message": f"账号 {index} 已进入冷却期 {seconds} 秒"}


# ==================== API Token管理 ====================

@router.get("/api-tokens")
async def list_api_tokens(token: str = Depends(require_admin)):
    """列出所有API Token（包含用量统计）"""
    from app.services.token_manager import token_manager

    tokens = token_manager.list_tokens(include_legacy=True)
    stats = token_manager.get_stats()

    return {
        "stats": stats.model_dump(),
        "tokens": tokens
    }


@router.post("/api-tokens")
async def create_api_token_route(
    name: str = "",
    expires_days: int = None,
    token: str = Depends(require_admin)
):
    """
    创建新的API Token

    Args:
        name: Token 名称/备注
        expires_days: 有效天数（不填则永不过期）
    """
    from app.services.token_manager import token_manager

    new_token = token_manager.create_token(name=name, expires_days=expires_days)

    return {
        "token": new_token.token,  # 只有创建时返回完整 token
        "name": new_token.name,
        "expires_at": new_token.expires_at
    }


@router.get("/api-tokens/{token_prefix}")
async def get_api_token_detail(
    token_prefix: str,
    token: str = Depends(require_admin)
):
    """通过 Token 前缀获取详情"""
    from app.services.token_manager import token_manager

    api_token = token_manager.get_token_by_prefix(token_prefix)
    if not api_token:
        raise HTTPException(status_code=404, detail="Token不存在")

    return api_token.to_dict(hide_token=True)


@router.delete("/api-tokens/{api_token}")
async def delete_api_token(
    api_token: str,
    token: str = Depends(require_admin)
):
    """删除API Token"""
    from app.services.token_manager import token_manager

    # 先尝试从新的 TokenManager 删除
    if token_manager.delete_token(api_token):
        return {"deleted": True}

    # 再尝试从旧配置中删除
    if api_token in config_manager.config.api_tokens:
        config_manager.config.api_tokens.remove(api_token)
        config_manager.save_config()
        # 重新加载 token_manager
        token_manager.load(config_manager.config.api_tokens)
        return {"deleted": True}

    raise HTTPException(status_code=404, detail="Token不存在")


@router.post("/api-tokens/{token_prefix}/disable")
async def disable_api_token(
    token_prefix: str,
    token: str = Depends(require_admin)
):
    """禁用 Token"""
    from app.services.token_manager import token_manager

    api_token = token_manager.get_token_by_prefix(token_prefix)
    if not api_token:
        raise HTTPException(status_code=404, detail="Token不存在")

    token_manager.disable_token(api_token.token)
    return {"success": True, "message": "Token 已禁用"}


@router.post("/api-tokens/{token_prefix}/enable")
async def enable_api_token(
    token_prefix: str,
    token: str = Depends(require_admin)
):
    """启用 Token"""
    from app.services.token_manager import token_manager

    api_token = token_manager.get_token_by_prefix(token_prefix)
    if not api_token:
        raise HTTPException(status_code=404, detail="Token不存在")

    token_manager.enable_token(api_token.token)
    return {"success": True, "message": "Token 已启用"}


# ==================== 代理管理 ====================

@router.get("/proxy/status")
async def get_proxy_status(token: str = Depends(require_admin)):
    """获取代理状态"""
    proxy = config_manager.config.proxy
    if not proxy:
        return {"enabled": False, "url": None, "available": False}

    # 测试代理
    available = await _test_proxy(proxy)

    return {
        "enabled": True,
        "url": proxy,
        "available": available
    }


@router.post("/proxy/test")
async def test_proxy(
    request: ProxyTest,
    token: str = Depends(require_admin)
):
    """测试代理可用性"""
    proxy_url = request.proxy or config_manager.config.proxy

    if not proxy_url:
        return {"success": False, "message": "未配置代理地址"}

    available = await _test_proxy(proxy_url)

    return {
        "success": available,
        "message": "代理可用" if available else "代理不可用或连接超时"
    }


async def _test_proxy(proxy_url: str) -> bool:
    """测试代理是否可用"""
    try:
        async with httpx.AsyncClient(
            proxy=proxy_url,
            verify=False,
            timeout=10.0
        ) as client:
            response = await client.get("https://www.google.com")
            return response.status_code == 200
    except Exception:
        return False


# ==================== 配置管理 ====================

@router.get("/config")
async def get_config(token: str = Depends(require_admin)):
    """获取当前配置（脱敏）"""
    config = config_manager.config

    return {
        "proxy": config.proxy or "未配置",
        "host": config.host,
        "port": config.port,
        "cooldown": config.cooldown.model_dump(),
        "models": [m.model_dump() for m in config.models],
        "accounts_count": len(config.accounts),
        "api_tokens_count": len(config.api_tokens)
    }


@router.put("/config")
async def update_config(
    request: ConfigUpdate,
    token: str = Depends(require_admin)
):
    """更新配置"""
    if request.proxy is not None:
        config_manager.config.proxy = request.proxy

    if request.admin_password is not None:
        config_manager.config.admin_password = request.admin_password

    config_manager.save_config()

    return {"success": True, "message": "配置已更新"}


@router.get("/config/export")
async def export_config(token: str = Depends(require_admin)):
    """导出完整配置"""
    return config_manager.config.model_dump()


@router.post("/config/import")
async def import_config(
    config_data: dict,
    token: str = Depends(require_admin)
):
    """导入配置"""
    try:
        from app.config import AppConfig

        # 验证配置格式
        new_config = AppConfig(**config_data)

        # 保存配置
        config_manager.config = new_config
        config_manager.save_config()

        # 重新加载账号
        account_manager.load_accounts()

        return {"success": True, "message": "配置导入成功"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"配置格式错误: {e}")


@router.post("/reload")
async def reload_config(token: str = Depends(require_admin)):
    """重新加载配置"""
    try:
        config_manager.load_config()
        account_manager.load_accounts()

        return {"message": "配置已重新加载"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载失败: {e}")


# ==================== 系统清理 ====================

@router.post("/cleanup")
async def cleanup_system(
    max_conversation_age: int = 86400,
    max_image_age: int = 24,
    token: str = Depends(require_admin)
):
    """
    清理系统

    - 清理过期会话
    - 清理旧图片
    - 清理图片缓存
    """
    # 清理过期会话
    conversation_manager.cleanup_expired(max_conversation_age)

    # 清理旧图片
    image_service.cleanup_old_images(max_image_age)

    # 清理图片缓存
    image_service.cleanup_cache()

    return {"message": "清理完成"}
