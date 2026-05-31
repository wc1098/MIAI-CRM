from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import delete

from app.core.database import async_db_session
from app.core.logger import log
from app.plugin.module_match.model import PersonMatchVectorTaskModel
from app.plugin.module_match.service import MAX_RETRY_COUNT
from app.plugin.module_screen.model import ScreenPromoRecordModel, ScreenUserWallRecordModel
from app.plugin.module_task.cronjob.job.model import JobModel

SYSTEM_RECORD_CLEANUP_JOB_ID = "system_record_cleanup_daily"


class SystemRecordCleanupService:
    """系统流水清理任务。"""

    @classmethod
    def register_scheduler(cls) -> None:
        """注册每天 00:00 的系统流水清理任务。"""

        from app.core.ap_scheduler import scheduler

        scheduler.add_job(
            func=cls.cleanup_daily_records,
            trigger=CronTrigger(hour=0, minute=0, second=0, timezone="Asia/Shanghai"),
            id=SYSTEM_RECORD_CLEANUP_JOB_ID,
            name="系统流水每日清理任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )

    @classmethod
    async def cleanup_daily_records(cls) -> dict[str, int]:
        """清理不需要长期保存的系统流水。"""

        cutoff = datetime.now()
        async with async_db_session() as db:
            screen_user_wall = await db.execute(
                delete(ScreenUserWallRecordModel).where(ScreenUserWallRecordModel.created_time < cutoff)
            )
            screen_promo = await db.execute(
                delete(ScreenPromoRecordModel).where(ScreenPromoRecordModel.created_time < cutoff)
            )
            task_job = await db.execute(delete(JobModel).where(JobModel.created_time < cutoff))
            match_vector_task = await db.execute(
                delete(PersonMatchVectorTaskModel).where(
                    PersonMatchVectorTaskModel.created_time < cutoff,
                    PersonMatchVectorTaskModel.status.in_(["success", "cancelled"]),
                )
            )
            failed_match_vector_task = await db.execute(
                delete(PersonMatchVectorTaskModel).where(
                    PersonMatchVectorTaskModel.created_time < cutoff,
                    PersonMatchVectorTaskModel.status == "failed",
                    PersonMatchVectorTaskModel.retry_count >= MAX_RETRY_COUNT,
                )
            )
            await db.commit()

        result = {
            "screen_user_wall_record": screen_user_wall.rowcount or 0,
            "screen_promo_record": screen_promo.rowcount or 0,
            "task_job": task_job.rowcount or 0,
            "person_match_vector_task": (match_vector_task.rowcount or 0)
            + (failed_match_vector_task.rowcount or 0),
        }
        log.info(f"系统流水每日清理完成: {result}")
        return result
