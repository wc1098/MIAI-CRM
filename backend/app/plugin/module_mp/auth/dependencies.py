from fastapi import Depends

from app.core.security import CustomOAuth2PasswordBearer, OAuth2Schema

from .service import MpAuthService

OptionalOAuth2Schema = CustomOAuth2PasswordBearer(token_url="system/auth/login", description="可选认证", auto_error=False)


async def get_current_mp_user_id(token: str = Depends(OAuth2Schema)) -> int:
    """解析当前小程序用户ID。"""

    payload = MpAuthService.decode_mp_token(token)
    return int(payload["mp_user_id"])


async def get_optional_mp_user_id(token: str | None = Depends(OptionalOAuth2Schema)) -> int | None:
    """有小程序登录态时解析用户ID，游客或失效登录态按未登录处理。"""

    if not token:
        return None
    try:
        payload = MpAuthService.decode_mp_token(token)
        return int(payload["mp_user_id"])
    except Exception:
        return None
