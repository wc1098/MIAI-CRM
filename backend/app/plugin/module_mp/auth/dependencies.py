from fastapi import Depends

from app.core.security import OAuth2Schema

from .service import MpAuthService


async def get_current_mp_user_id(token: str = Depends(OAuth2Schema)) -> int:
    """解析当前小程序用户ID。"""

    payload = MpAuthService.decode_mp_token(token)
    return int(payload["mp_user_id"])
