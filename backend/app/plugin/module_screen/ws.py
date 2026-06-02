import json
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.database import async_db_session
from app.core.dependencies import _verify_token
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import ScreenActivityCommandSchema
from .service import ScreenService

ACTIVITY_CONTROL_COMMANDS = {
    "set_scene",
    "set_background",
    "toggle_module",
    "toggle_people_count",
    "toggle_qrcode",
    "refresh",
    "clear_screen",
    "music_play",
    "music_pause",
    "music_next",
    "music_prev",
    "music_set_volume",
    "music_set_track",
    "dominate_play",
}

ScreenWsRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/screen",
    tags=["活动大屏WebSocket"],
)


class ActivityScreenWsManager:
    def __init__(self) -> None:
        self._rooms: dict[int, set[WebSocket]] = defaultdict(set)
        self._roles: dict[WebSocket, str] = {}

    async def connect(self, activity_id: int, websocket: WebSocket, role: str) -> None:
        await websocket.accept()
        self._rooms[activity_id].add(websocket)
        self._roles[websocket] = role
        await self.broadcast(activity_id, {"type": "online_status", "payload": self.online_status(activity_id)})

    async def disconnect(self, activity_id: int, websocket: WebSocket) -> None:
        self._rooms.get(activity_id, set()).discard(websocket)
        self._roles.pop(websocket, None)
        await self.broadcast(activity_id, {"type": "online_status", "payload": self.online_status(activity_id)})

    def online_status(self, activity_id: int) -> dict[str, Any]:
        roles = [self._roles.get(ws) for ws in self._rooms.get(activity_id, set())]
        return {
            "player_online": "player" in roles,
            "remote_online": "remote" in roles,
            "connections": len(roles),
        }

    async def broadcast(self, activity_id: int, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        text = json.dumps(message, ensure_ascii=False, default=str)
        for websocket in list(self._rooms.get(activity_id, set())):
            try:
                await websocket.send_text(text)
            except RuntimeError:
                dead.append(websocket)
        for websocket in dead:
            self._rooms.get(activity_id, set()).discard(websocket)
            self._roles.pop(websocket, None)


activity_ws_manager = ActivityScreenWsManager()


@ScreenWsRouter.websocket("/player/activity/{activity_id}/ws")
async def player_activity_ws_controller(websocket: WebSocket, activity_id: int) -> None:
    token = websocket.query_params.get("token") or ""
    try:
        async with async_db_session() as db:
            await ScreenService.device_by_token(db, token)
            await ScreenService.detail_activity(db, activity_id)
        await activity_ws_manager.connect(activity_id, websocket, "player")
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning(f"活动大屏播放端 WebSocket 断开: {exc}")
        try:
            await websocket.close(code=1008, reason=str(exc))
        except RuntimeError:
            pass
    finally:
        await activity_ws_manager.disconnect(activity_id, websocket)


@ScreenWsRouter.websocket("/admin/activity/{activity_id}/ws")
async def admin_activity_ws_controller(websocket: WebSocket, activity_id: int) -> None:
    token = websocket.query_params.get("token") or ""
    try:
        async with async_db_session() as db:
            auth = await _verify_token(token, db, websocket.app.state.redis)
            await ScreenService.detail_activity(db, activity_id)
        await activity_ws_manager.connect(activity_id, websocket, "remote")
        while True:
            data = await websocket.receive_text()
            if not data:
                continue
            payload = json.loads(data)
            if payload.get("type") not in ACTIVITY_CONTROL_COMMANDS:
                continue
            command = ScreenActivityCommandSchema(command=payload["type"], value=payload.get("value"))
            async with async_db_session() as db:
                auth = await _verify_token(token, db, websocket.app.state.redis)
                result = await ScreenService.activity_command(auth, activity_id, command)
                await db.commit()
            await activity_ws_manager.broadcast(activity_id, {"type": command.command, "payload": result})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning(f"活动大屏遥控端 WebSocket 断开: {exc}")
        try:
            await websocket.close(code=1008, reason=str(exc))
        except RuntimeError:
            pass
    finally:
        await activity_ws_manager.disconnect(activity_id, websocket)


@ScreenWsRouter.websocket("/control/activity/ws")
async def control_activity_ws_controller(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token") or ""
    activity_id = 0
    try:
        async with async_db_session() as db:
            payload = await ScreenService.verify_activity_control_token(db, websocket.app.state.redis, token)
            activity_id = payload["activity_id"]
        await activity_ws_manager.connect(activity_id, websocket, "remote")
        while True:
            data = await websocket.receive_text()
            if not data:
                continue
            payload = json.loads(data)
            if payload.get("type") not in ACTIVITY_CONTROL_COMMANDS:
                continue
            command = ScreenActivityCommandSchema(command=payload["type"], value=payload.get("value"))
            async with async_db_session() as db:
                result = await ScreenService.control_activity_command(db, websocket.app.state.redis, token, command)
                await db.commit()
            await activity_ws_manager.broadcast(activity_id, {"type": command.command, "payload": result})
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        log.warning(f"活动大屏手机控制台 WebSocket 断开: {exc}")
        try:
            await websocket.close(code=1008, reason=str(exc))
        except RuntimeError:
            pass
    finally:
        if activity_id:
            await activity_ws_manager.disconnect(activity_id, websocket)
