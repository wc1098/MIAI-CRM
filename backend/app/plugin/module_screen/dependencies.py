from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import db_getter
from app.core.exceptions import CustomException

from .model import ScreenDeviceModel
from .service import ScreenService


async def get_screen_device(
    db: Annotated[AsyncSession, Depends(db_getter)],
    authorization: Annotated[str | None, Header()] = None,
    x_screen_device_token: Annotated[str | None, Header()] = None,
) -> ScreenDeviceModel:
    token = x_screen_device_token
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "screendevice":
            token = parts[1].strip()
    if not token:
        raise CustomException(msg="大屏设备未授权", code=10401, status_code=401)
    return await ScreenService.device_by_token(db, token)
