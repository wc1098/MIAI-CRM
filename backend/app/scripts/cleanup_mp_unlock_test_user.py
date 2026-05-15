r"""清理小程序用户联系方式解锁测试记录。

用法：
    cd backend
    .\.venv3.13\Scripts\python.exe app/scripts/cleanup_mp_unlock_test_user.py --user-id 3 --env dev
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


ACTION_TYPES = [
    "view",
    "view_invisible",
    "task_view_profile",
    "task_like_profile",
    "task_favorite_profile",
    "task_share_card",
    "question_answer",
    "like",
    "cancel_like",
    "favorite",
    "cancel_favorite",
    "unlock_heartbeat_attempt",
    "unlock_coupon_attempt",
    "unlock_pay_attempt",
    "unlock_success",
    "contact_view",
]


async def _count(session, sql: str, **params) -> int:
    return int((await session.execute(text(sql), params)).scalar() or 0)


async def cleanup(user_id: int, env: str) -> None:
    os.environ["ENVIRONMENT"] = env

    from app.config.setting import get_settings

    get_settings.cache_clear()

    from app.core.database import Redis, async_db_session, settings

    async with async_db_session() as session:
        async with session.begin():
            before = {
                "heart_progress": await _count(session, "select count(*) from mp_heartbeat_progress where viewer_user_id=:uid", uid=user_id),
                "task_records": await _count(session, "select count(*) from mp_unlock_task_record where viewer_user_id=:uid", uid=user_id),
                "question_answers": await _count(session, "select count(*) from mp_unlock_question_answer where viewer_user_id=:uid", uid=user_id),
                "likes": await _count(session, "select count(*) from mp_user_like where viewer_user_id=:uid", uid=user_id),
                "favorites": await _count(session, "select count(*) from mp_user_favorite where viewer_user_id=:uid", uid=user_id),
                "contact_unlocks": await _count(session, "select count(*) from mp_contact_unlock where viewer_user_id=:uid", uid=user_id),
                "contact_views": await _count(session, "select count(*) from mp_contact_view_log where viewer_user_id=:uid", uid=user_id),
                "actions": await _count(
                    session,
                    "select count(*) from mp_user_profile_action where viewer_user_id=:uid and action_type = any(:actions)",
                    uid=user_id,
                    actions=ACTION_TYPES,
                ),
            }

            unlock_ids = [
                row[0]
                for row in (await session.execute(text("select id from mp_contact_unlock where viewer_user_id=:uid"), {"uid": user_id})).all()
            ]
            if unlock_ids:
                await session.execute(text("delete from mp_contact_view_log where unlock_id = any(:ids)"), {"ids": unlock_ids})
            await session.execute(text("delete from mp_contact_view_log where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_contact_unlock where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_unlock_question_answer where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_unlock_task_record where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_heartbeat_progress where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_user_like where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(text("delete from mp_user_favorite where viewer_user_id=:uid"), {"uid": user_id})
            await session.execute(
                text("delete from mp_user_profile_action where viewer_user_id=:uid and action_type = any(:actions)"),
                {"uid": user_id, "actions": ACTION_TYPES},
            )

            after = {
                "heart_progress": await _count(session, "select count(*) from mp_heartbeat_progress where viewer_user_id=:uid", uid=user_id),
                "task_records": await _count(session, "select count(*) from mp_unlock_task_record where viewer_user_id=:uid", uid=user_id),
                "question_answers": await _count(session, "select count(*) from mp_unlock_question_answer where viewer_user_id=:uid", uid=user_id),
                "likes": await _count(session, "select count(*) from mp_user_like where viewer_user_id=:uid", uid=user_id),
                "favorites": await _count(session, "select count(*) from mp_user_favorite where viewer_user_id=:uid", uid=user_id),
                "contact_unlocks": await _count(session, "select count(*) from mp_contact_unlock where viewer_user_id=:uid", uid=user_id),
                "contact_views": await _count(session, "select count(*) from mp_contact_view_log where viewer_user_id=:uid", uid=user_id),
                "actions": await _count(
                    session,
                    "select count(*) from mp_user_profile_action where viewer_user_id=:uid and action_type = any(:actions)",
                    uid=user_id,
                    actions=ACTION_TYPES,
                ),
            }

    redis_deleted = 0
    if settings.REDIS_ENABLE:
        redis = await Redis.from_url(url=settings.REDIS_URI, encoding="utf-8", decode_responses=True)
        try:
            keys = await redis.keys(f"mp:unlock:questions:*:{user_id}:*")
            if keys:
                redis_deleted = int(await redis.delete(*keys))
        finally:
            await redis.aclose()

    print(f"cleaned user_id={user_id}")
    print(f"before={before}")
    print(f"after={after}")
    print(f"redis_deleted={redis_deleted}")


def main() -> None:
    parser = argparse.ArgumentParser(description="清理小程序解锁流程测试数据")
    parser.add_argument("--user-id", type=int, default=3, help="小程序用户 ID，默认 3")
    parser.add_argument("--env", default="dev", choices=["dev", "prod"], help="运行环境，默认 dev")
    args = parser.parse_args()
    asyncio.run(cleanup(args.user_id, args.env))


if __name__ == "__main__":
    main()
