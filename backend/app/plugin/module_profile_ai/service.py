import re
import socket
from datetime import date, datetime, timedelta
from typing import Any
from urllib.parse import urljoin

import httpx
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_match.service import MatchProfileService

from .model import PersonAiProfileModel, PersonAiProfileTaskModel

MIAI_IMPRESSION = "miai_impression"
SOURCE_PRIORITIES = {"register": 10, "admin_update": 20, "deep_interview": 100}
MAX_RETRY_COUNT = 10
RETRY_DELAYS = [60, 300, 900, 1800, 3600]
WORKER_JOB_ID = "person_ai_profile_task_worker"
WORKER_SCAN_SECONDS = 60
GENDER_LABELS = {"0": "男", "1": "女", "2": "未知"}
FORBIDDEN_DIRECT_FACT_PATTERN = re.compile(
    r"(\d{2}岁|\d{3}\s?(?:cm|CM|厘米)|体重|公斤|kg|KG|"
    r"硕士|博士|本科|大专|高中|学历|毕业|学校|专业|"
    r"年收入|收入|有车|无车|有房|无房|无贷|房贷|车贷|"
    r"郑州|洛阳|北京大学|北大|律师|教师|模特)"
)
ETHNICITY_LABELS = {
    "han": "汉族",
    "mongol": "蒙古族",
    "hui": "回族",
    "tibetan": "藏族",
    "uyghur": "维吾尔族",
    "miao": "苗族",
    "yi": "彝族",
    "zhuang": "壮族",
    "manchu": "满族",
    "other": "其他",
}
ANNUAL_INCOME_LABELS = {
    "below_100k": "10万以下",
    "100k_200k": "10-20万",
    "200k_500k": "20-50万",
    "above_500k": "50万以上",
}
MARITAL_STATUS_LABELS = {"single": "未婚", "divorced": "离异", "widowed": "丧偶"}
EDUCATION_LABELS = {
    "high_school_or_below": "高中及以下",
    "college": "大专",
    "bachelor": "本科",
    "master": "硕士",
    "doctor_or_above": "博士及以上",
}
HOUSE_STATUS_LABELS = {"none": "无房", "owned": "有房无贷", "mortgage": "有房有贷", "family": "与父母同住"}
CAR_STATUS_LABELS = {"none": "无车", "owned": "有车无贷", "loan": "有车有贷"}


class PersonAiProfileService:
    """觅AI印象画像服务。"""

    @classmethod
    def register_scheduler(cls) -> None:
        """注册固定内置任务，周期扫描到期画像任务。"""

        from app.core.ap_scheduler import scheduler

        scheduler.add_job(
            func=cls.process_due_tasks,
            trigger=IntervalTrigger(seconds=WORKER_SCAN_SECONDS, timezone="Asia/Shanghai"),
            id=WORKER_JOB_ID,
            name="觅AI印象生成任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )

    @classmethod
    def _priority(cls, source_type: str) -> int:
        return SOURCE_PRIORITIES.get(source_type, 10)

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _safe_location(cls, value: str | None) -> str | None:
        if not value:
            return None
        parts = [part.strip() for part in value.replace(" / ", "/").split("/") if part.strip()]
        return " / ".join(parts[:2]) if parts else None

    @classmethod
    def _label(cls, labels: dict[str, str], value: str | None) -> str | None:
        if not value:
            return None
        return labels.get(value, value)

    @classmethod
    def _build_snapshot(cls, person: CrmPersonModel, source_type: str, source_id: str | None = None) -> dict[str, Any]:
        """构造脱敏输入快照，不包含手机号、微信号、证件、证明、合同、支付等敏感信息。"""

        return {
            "source_type": source_type,
            "source_id": source_id,
            "display_no": person.display_no,
            "gender": cls._label(GENDER_LABELS, person.gender),
            "age": cls._age(person.birth_date),
            "height_cm": person.height_cm,
            "ethnicity": cls._label(ETHNICITY_LABELS, person.ethnicity),
            "occupation": person.occupation_code or person.occupation,
            "annual_income": cls._label(ANNUAL_INCOME_LABELS, person.annual_income),
            "marital_status": cls._label(MARITAL_STATUS_LABELS, person.marital_status),
            "education": cls._label(EDUCATION_LABELS, person.education),
            "graduated_school": person.graduated_school,
            "major": person.major,
            "unit_type": person.unit_type,
            "job_title": person.job_title,
            "work_company": person.work_company,
            "hometown": cls._safe_location(person.hometown),
            "residence": cls._safe_location(person.residence),
            "house_status": cls._label(HOUSE_STATUS_LABELS, person.house_status),
            "car_status": cls._label(CAR_STATUS_LABELS, person.car_status),
            "accept_long_distance_self": person.accept_long_distance_self,
            "accept_flash_marriage": person.accept_flash_marriage,
            "willing_relocate": person.willing_relocate,
            "marriage_plan": person.marriage_plan,
            "family_background": person.family_background,
            "profile_remark": person.profile_remark,
        }

    @classmethod
    async def enqueue_miai_impression(
        cls,
        db: AsyncSession,
        person_id: int,
        source_type: str,
        source_id: str | int | None = None,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> PersonAiProfileTaskModel | None:
        """投递觅AI印象生成任务。"""

        if source_type not in SOURCE_PRIORITIES:
            raise CustomException(msg=f"不支持的画像来源类型: {source_type}")

        person = None
        if payload_snapshot is None:
            result = await db.execute(
                select(CrmPersonModel).where(CrmPersonModel.id == person_id, CrmPersonModel.is_deleted == False)
            )
            person = result.scalars().first()
            if not person:
                return None
            payload_snapshot = cls._build_snapshot(person, source_type=source_type, source_id=str(source_id) if source_id else None)

        task = PersonAiProfileTaskModel(
            person_id=person_id,
            profile_type=MIAI_IMPRESSION,
            source_type=source_type,
            source_id=str(source_id) if source_id is not None else None,
            priority=cls._priority(source_type),
            status="pending",
            retry_count=0,
            next_retry_at=datetime.now(),
            payload_snapshot=payload_snapshot,
        )
        db.add(task)
        await db.flush()
        return task

    @classmethod
    async def enqueue_deep_interview_impression(
        cls,
        db: AsyncSession,
        person_id: int,
        source_id: str | int,
        payload_snapshot: dict[str, Any] | None = None,
    ) -> PersonAiProfileTaskModel | None:
        """预留给后续深访模块的高优先级投递入口。"""

        return await cls.enqueue_miai_impression(
            db=db,
            person_id=person_id,
            source_type="deep_interview",
            source_id=source_id,
            payload_snapshot=payload_snapshot,
        )

    @classmethod
    async def effective_profile_map(cls, db: AsyncSession, person_ids: set[int]) -> dict[int, dict[str, Any]]:
        if not person_ids:
            return {}
        rows = (
            await db.execute(
                select(PersonAiProfileModel).where(
                    PersonAiProfileModel.person_id.in_(person_ids),
                    PersonAiProfileModel.profile_type == MIAI_IMPRESSION,
                    PersonAiProfileModel.is_effective == True,
                    PersonAiProfileModel.is_deleted == False,
                )
            )
        ).scalars().all()
        return {row.person_id: cls._profile_out(row) for row in rows}

    @classmethod
    async def latest_task_map(cls, db: AsyncSession, person_ids: set[int]) -> dict[int, dict[str, Any]]:
        if not person_ids:
            return {}
        rows = (
            await db.execute(
                select(PersonAiProfileTaskModel)
                .where(
                    PersonAiProfileTaskModel.person_id.in_(person_ids),
                    PersonAiProfileTaskModel.profile_type == MIAI_IMPRESSION,
                    PersonAiProfileTaskModel.is_deleted == False,
                )
                .order_by(PersonAiProfileTaskModel.person_id.asc(), PersonAiProfileTaskModel.created_time.desc(), PersonAiProfileTaskModel.id.desc())
            )
        ).scalars().all()
        result: dict[int, dict[str, Any]] = {}
        for row in rows:
            result.setdefault(row.person_id, cls._task_out(row))
        return result

    @classmethod
    async def admin_info_map(cls, db: AsyncSession, person_ids: set[int]) -> dict[int, dict[str, Any]]:
        profile_map = await cls.effective_profile_map(db, person_ids)
        task_map = await cls.latest_task_map(db, person_ids)
        return {
            person_id: {"profile": profile_map.get(person_id), "latest_task": task_map.get(person_id)}
            for person_id in person_ids
        }

    @classmethod
    def _profile_out(cls, profile: PersonAiProfileModel) -> dict[str, Any]:
        return {
            "id": profile.id,
            "profile_type": profile.profile_type,
            "source_type": profile.source_type,
            "source_id": profile.source_id,
            "priority": profile.priority,
            "content": profile.content,
            "generation_status": profile.generation_status,
            "is_effective": profile.is_effective,
            "model_name": profile.model_name,
            "generated_at": profile.generated_at,
            "updated_time": profile.updated_time,
            "last_error": profile.last_error,
        }

    @classmethod
    def _task_out(cls, task: PersonAiProfileTaskModel) -> dict[str, Any]:
        return {
            "id": task.id,
            "profile_type": task.profile_type,
            "status": task.status,
            "source_type": task.source_type,
            "source_id": task.source_id,
            "priority": task.priority,
            "retry_count": task.retry_count,
            "next_retry_at": task.next_retry_at,
            "updated_time": task.updated_time,
            "last_error": task.last_error,
        }

    @classmethod
    async def process_due_tasks(cls, batch_size: int = 5) -> int:
        """扫描并处理到期任务。"""

        processed = 0
        worker_id = f"{socket.gethostname()}:{WORKER_JOB_ID}"
        now = datetime.now()
        async with async_db_session() as db:
            rows = (
                await db.execute(
                    select(PersonAiProfileTaskModel)
                    .where(
                        PersonAiProfileTaskModel.is_deleted == False,
                        PersonAiProfileTaskModel.status.in_(["pending", "failed"]),
                        PersonAiProfileTaskModel.retry_count < MAX_RETRY_COUNT,
                        PersonAiProfileTaskModel.next_retry_at <= now,
                    )
                    .order_by(PersonAiProfileTaskModel.priority.desc(), PersonAiProfileTaskModel.next_retry_at.asc(), PersonAiProfileTaskModel.id.asc())
                    .limit(batch_size)
                )
            ).scalars().all()

            from app.core.ap_scheduler import SchedulerUtil

            for task in rows:
                lock_key = f"profile_ai:miai_impression:task:{task.id}"
                lock_value = f"{worker_id}:{datetime.now().timestamp()}"
                redis = SchedulerUtil.redis_instance
                if redis:
                    acquired = bool(await redis.set(lock_key, lock_value, ex=600, nx=True))
                else:
                    acquired = True
                if not acquired:
                    continue
                try:
                    task.status = "processing"
                    task.locked_at = datetime.now()
                    task.locked_by = worker_id
                    await db.commit()
                    await cls._process_one(task_id=task.id)
                    processed += 1
                finally:
                    if redis:
                        script = """
                        if redis.call('get', KEYS[1]) == ARGV[1] then
                            return redis.call('del', KEYS[1])
                        else
                            return 0
                        end
                        """
                        await redis.eval(script, 1, lock_key, lock_value)
        return processed

    @classmethod
    async def _process_one(cls, task_id: int) -> None:
        async with async_db_session() as db:
            task = (
                await db.execute(
                    select(PersonAiProfileTaskModel).where(
                        PersonAiProfileTaskModel.id == task_id,
                        PersonAiProfileTaskModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if not task or task.status == "cancelled":
                return
            try:
                content = await cls._generate_content(task.payload_snapshot or {})
                await cls._write_profile(db, task, content)
                task.status = "success"
                task.last_error = None
                task.locked_at = None
                task.locked_by = None
                await db.commit()
            except Exception as exc:
                await db.rollback()
                await cls._mark_failed(task_id, exc)

    @classmethod
    async def _mark_failed(cls, task_id: int, exc: Exception) -> None:
        delay_index = 0
        async with async_db_session() as db:
            task = (
                await db.execute(select(PersonAiProfileTaskModel).where(PersonAiProfileTaskModel.id == task_id))
            ).scalars().first()
            if not task:
                return
            retry_count = int(task.retry_count or 0) + 1
            delay_index = min(retry_count - 1, len(RETRY_DELAYS) - 1)
            task.retry_count = retry_count
            task.status = "failed"
            task.last_error = str(exc)[:2000]
            task.locked_at = None
            task.locked_by = None
            if retry_count < MAX_RETRY_COUNT:
                task.next_retry_at = datetime.now() + timedelta(seconds=RETRY_DELAYS[delay_index])
            else:
                task.next_retry_at = datetime.now() + timedelta(hours=24)
            await db.commit()

    @classmethod
    async def _generate_content(cls, snapshot: dict[str, Any]) -> str:
        if not settings.OPENAI_API_KEY or not settings.OPENAI_MODEL or not settings.OPENAI_BASE_URL:
            raise CustomException(msg="AI大模型配置不完整")
        prompt = cls._build_prompt(snapshot)
        url = urljoin(settings.OPENAI_BASE_URL.rstrip("/") + "/", "chat/completions")
        async with httpx.AsyncClient(timeout=max(settings.HTTPX_DEFAULT_TIMEOUT, 30.0)) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": settings.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是婚恋平台的专业画像文案助手，只输出安全、脱敏、温和、真实的中文展示文案。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.5,
                    "max_tokens": 600,
                },
            )
        if response.status_code >= 400:
            raise CustomException(msg=f"AI生成失败: HTTP {response.status_code}", data=response.text[:1000])
        payload = response.json()
        choice = (payload.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "length":
            raise CustomException(msg="AI生成结果被截断，等待重试")
        content = ((choice.get("message") or {}).get("content") or "").strip()
        content = cls._clean_content(content)
        cls._validate_content(content)
        return content

    @classmethod
    def _build_prompt(cls, snapshot: dict[str, Any]) -> str:
        return (
            "请基于以下脱敏资料，为婚恋小程序用户详情页生成一段“觅AI印象”。\n"
            "要求：120-220字；不要写标题；必须是完整段落，结尾要自然收束，不能以半句话或条件句结尾；"
            "必须严格按资料中的性别称呼，gender=男时只能使用“他/这位男士”，gender=女时只能使用“她/这位女士”；"
            "年龄、身高、学历、职业、收入、婚况、籍贯、常驻地、房车等资料字段可以作为判断生活阶段、气质、稳定性和关系期待的背景素材，但不能直接输出原字段数字、单位或枚举值，不能写“35岁”“172cm”“身高172厘米”等；"
            "体重不可作为素材，也不能输出体重相关描述；"
            "不要复述资料页已经单独展示的结构化字段，不要罗列学历、学校、专业、职业、收入、婚况、民族、籍贯、常驻地、房车情况，要转化成生活状态、相处气质、沟通建议或关系期待；"
            "不要用“这位女士35岁、身高172cm”“硕士学历、从事某职业、有车无贷”这类资料罗列开场；"
            "不要编造具体姓名、手机号、微信号、公司、收入精确值、住址、证件、证明、合同、支付信息；"
            "避免绝对化承诺和诊断式评价；语气温和可信，突出性格、生活状态、关系期待与相处建议。\n"
            f"脱敏资料：{snapshot}"
        )

    @classmethod
    def _clean_content(cls, content: str) -> str:
        for prefix in ["觅AI印象：", "觅AI印象:", "红娘印象：", "红娘印象:"]:
            if content.startswith(prefix):
                content = content[len(prefix):].strip()
        return content[:800]

    @classmethod
    def _validate_content(cls, content: str) -> None:
        if FORBIDDEN_DIRECT_FACT_PATTERN.search(content):
            raise CustomException(msg="AI生成结果直接复述了资料字段，等待重试")

    @classmethod
    async def _write_profile(cls, db: AsyncSession, task: PersonAiProfileTaskModel, content: str) -> None:
        now = datetime.now()
        current = (
            await db.execute(
                select(PersonAiProfileModel).where(
                    PersonAiProfileModel.person_id == task.person_id,
                    PersonAiProfileModel.profile_type == task.profile_type,
                    PersonAiProfileModel.is_effective == True,
                    PersonAiProfileModel.is_deleted == False,
                )
            )
        ).scalars().first()
        can_effective = current is None or task.priority >= current.priority
        profile = PersonAiProfileModel(
            person_id=task.person_id,
            profile_type=task.profile_type,
            source_type=task.source_type,
            source_id=task.source_id,
            priority=task.priority,
            content=content,
            input_snapshot=task.payload_snapshot,
            model_name=settings.OPENAI_MODEL,
            generation_status="success",
            is_effective=can_effective,
            generated_at=now,
        )
        db.add(profile)
        await db.flush()
        if can_effective:
            await db.execute(
                update(PersonAiProfileModel)
                .where(
                    PersonAiProfileModel.person_id == task.person_id,
                    PersonAiProfileModel.profile_type == task.profile_type,
                    PersonAiProfileModel.id != profile.id,
                    PersonAiProfileModel.is_effective == True,
                )
                .values(is_effective=False)
            )
            await MatchProfileService.mark_dirty(
                db=db,
                person_id=task.person_id,
                dirty_parts=["self_profile"],
                source_type="ai_profile",
                source_id=profile.id,
            )
