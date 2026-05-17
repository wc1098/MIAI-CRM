"""批量投递小程序注册用户匹配向量任务。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

CURRENT = Path(__file__).resolve()
BACKEND_DIR = CURRENT.parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


async def enqueue(limit: int | None = None, env: str = "dev") -> None:
    import os

    os.environ["ENVIRONMENT"] = env
    from app.config.setting import get_settings

    get_settings.cache_clear()
    from sqlalchemy import select

    from app.core.database import async_db_session
    from app.plugin.module_match.service import MatchProfileService
    from app.plugin.module_mp.auth.model import MiniProgramUserModel

    async with async_db_session() as db:
        stmt = select(MiniProgramUserModel.person_id).where(
            MiniProgramUserModel.is_deleted == False,
            MiniProgramUserModel.person_id.is_not(None),
            MiniProgramUserModel.registered_at.is_not(None),
        )
        if limit:
            stmt = stmt.limit(limit)
        person_ids = [row[0] for row in (await db.execute(stmt)).all()]
        for person_id in person_ids:
            await MatchProfileService.mark_dirty(
                db=db,
                person_id=person_id,
                dirty_parts=["self_profile", "preference"],
                source_type="script_backfill",
                source_id=None,
            )
        await db.commit()
        print(f"enqueued={len(person_ids)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--env", default="dev", choices=["dev", "prod"])
    args = parser.parse_args()
    asyncio.run(enqueue(args.limit, args.env))


if __name__ == "__main__":
    main()
