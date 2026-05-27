import math
import socket
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.params.model import ParamsModel
from app.config.path_conf import BASE_DIR
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_crm.person.model import PersonProfileInsightModel
from app.plugin.module_crm.preference.model import PersonPartnerPreferenceModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel
from app.plugin.module_profile_ai.model import PersonAiProfileModel

from .model import PersonMatchProfileModel, PersonMatchVectorModel, PersonMatchVectorTaskModel

SELF_PROFILE = "self_profile"
PREFERENCE = "preference"
VECTOR_TYPES = {SELF_PROFILE, PREFERENCE}
WORKER_JOB_ID = "person_match_vector_task_worker"
WORKER_SCAN_SECONDS = 30
MAX_RETRY_COUNT = 10
RETRY_DELAYS = [60, 300, 900, 1800, 3600]

GENDER_LABELS = {"0": "男", "1": "女", "2": "未知"}
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


class LocalText2VecProvider:
    """本地 text2vec embedding 提供者。"""

    _model: Any | None = None
    _model_path: str | None = None

    @classmethod
    def _resolve_model_path(cls, configured: str) -> str:
        raw = Path(configured)
        if raw.is_absolute():
            return str(raw)
        parts = raw.parts
        if parts and parts[0].lower() == "backend":
            raw = Path(*parts[1:])
        return str((BASE_DIR / raw).resolve())

    @classmethod
    def _load(cls, model_path: str) -> Any:
        resolved = cls._resolve_model_path(model_path)
        if cls._model is not None and cls._model_path == resolved:
            return cls._model
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            raise CustomException(msg="缺少 sentence-transformers 依赖，无法生成本地向量") from exc
        cls._model = SentenceTransformer(resolved)
        cls._model_path = resolved
        return cls._model

    @classmethod
    def encode(cls, text: str, model_path: str, normalize: bool = True) -> list[float]:
        model = cls._load(model_path)
        vector = model.encode(text, normalize_embeddings=normalize)
        return [float(item) for item in vector.tolist()]


class MatchProfileService:
    """匹配画像、向量与候选推荐服务。"""

    @classmethod
    def _scheduler_redis(cls) -> Any | None:
        try:
            from app.core.ap_scheduler import SchedulerUtil

            return SchedulerUtil.redis_instance
        except ImportError:
            return None

    @classmethod
    def register_scheduler(cls) -> None:
        from app.core.ap_scheduler import scheduler

        scheduler.add_job(
            func=cls.process_due_tasks,
            trigger=IntervalTrigger(seconds=WORKER_SCAN_SECONDS, timezone="Asia/Shanghai"),
            id=WORKER_JOB_ID,
            name="匹配画像向量生成任务",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            jobstore="default",
            executor="default",
        )

    @classmethod
    async def _param(cls, db: AsyncSession, key: str, default: str | None = None) -> str | None:
        value = (
            await db.execute(
                select(ParamsModel.config_value).where(
                    ParamsModel.config_key == key,
                    ParamsModel.status == "0",
                    ParamsModel.is_deleted == False,
                )
            )
        ).scalar()
        return value if value not in (None, "") else default

    @classmethod
    async def embedding_settings(cls, db: AsyncSession) -> dict[str, Any]:
        return {
            "enabled": (await cls._param(db, "match.embedding.enabled", "true") or "true").lower() in {"1", "true", "yes", "on"},
            "provider": await cls._param(db, "match.embedding.provider", "local_text2vec"),
            "model_path": await cls._param(db, "match.embedding.model_path", "backend/models/text2vec-base-chinese"),
            "model_name": await cls._param(db, "match.embedding.model_name", "text2vec-base-chinese"),
            "dimension": int(await cls._param(db, "match.embedding.dimension", "768") or 768),
            "batch_size": int(await cls._param(db, "match.embedding.batch_size", "16") or 16),
            "normalize": (await cls._param(db, "match.embedding.normalize", "true") or "true").lower() in {"1", "true", "yes", "on"},
        }

    @classmethod
    def _label(cls, labels: dict[str, str], value: str | None) -> str | None:
        return labels.get(value, value) if value else None

    @classmethod
    def _age(cls, birth_date: date | None) -> int | None:
        if not birth_date:
            return None
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    @classmethod
    def _safe_text(cls, value: str | None, max_len: int = 80) -> str | None:
        if not value:
            return None
        return value.replace("\n", " ").strip()[:max_len]

    @classmethod
    def _person_snapshot(cls, person: CrmPersonModel) -> dict[str, Any]:
        photos = person.photo_urls or []
        return {
            "display_no": person.display_no,
            "gender": cls._label(GENDER_LABELS, person.gender),
            "gender_code": person.gender,
            "age": cls._age(person.birth_date),
            "height_cm": person.height_cm,
            "weight_kg": person.weight_kg,
            "ethnicity": person.ethnicity,
            "occupation": cls._safe_text(person.occupation_code or person.occupation),
            "occupation_code": person.occupation_code,
            "annual_income": cls._label(ANNUAL_INCOME_LABELS, person.annual_income),
            "annual_income_code": person.annual_income,
            "marital_status": cls._label(MARITAL_STATUS_LABELS, person.marital_status),
            "marital_status_code": person.marital_status,
            "education": cls._label(EDUCATION_LABELS, person.education),
            "education_code": person.education,
            "graduated_school": cls._safe_text(person.graduated_school),
            "major": cls._safe_text(person.major),
            "unit_type": person.unit_type,
            "job_title": cls._safe_text(person.job_title),
            "work_company": cls._safe_text(person.work_company),
            "hometown": cls._safe_text(person.hometown),
            "residence": cls._safe_text(person.residence),
            "house_status": cls._label(HOUSE_STATUS_LABELS, person.house_status),
            "house_status_code": person.house_status,
            "car_status": cls._label(CAR_STATUS_LABELS, person.car_status),
            "car_status_code": person.car_status,
            "accept_long_distance_self": person.accept_long_distance_self,
            "accept_flash_marriage": person.accept_flash_marriage,
            "willing_relocate": person.willing_relocate,
            "marriage_plan": person.marriage_plan,
            "family_background": cls._safe_text(person.family_background, 200),
            "photo_count": len(photos),
        }

    @classmethod
    def _preference_snapshot(cls, preference: PersonPartnerPreferenceModel | None) -> dict[str, Any]:
        if not preference:
            return {}
        return {
            "age_min": preference.age_min,
            "age_max": preference.age_max,
            "height_min_cm": preference.height_min_cm,
            "height_max_cm": preference.height_max_cm,
            "preferred_residence_region_codes": preference.preferred_residence_region_codes or [],
            "preferred_hometown_region_codes": preference.preferred_hometown_region_codes or [],
            "preferred_education_codes": preference.preferred_education_codes or [],
            "preferred_marital_status_codes": preference.preferred_marital_status_codes or [],
            "preferred_annual_income_codes": preference.preferred_annual_income_codes or [],
            "preferred_house_status_codes": preference.preferred_house_status_codes or [],
            "preferred_car_status_codes": preference.preferred_car_status_codes or [],
            "accept_long_distance": preference.accept_long_distance,
            "accept_divorced": preference.accept_divorced,
            "accept_children": preference.accept_children,
            "children_requirement": preference.children_requirement,
            "preferred_personality_tags": preference.preferred_personality_tags or [],
            "preferred_lifestyle_tags": preference.preferred_lifestyle_tags or [],
            "preferred_relationship_tags": preference.preferred_relationship_tags or [],
            "hard_reject_items": cls._safe_text(preference.hard_reject_items, 300),
            "soft_preference_items": cls._safe_text(preference.soft_preference_items, 300),
            "preferred_occupation_text": cls._safe_text(preference.preferred_occupation_text, 120),
            "preference_text": cls._safe_text(preference.preference_text, 400),
            "profile_summary": cls._safe_text(preference.profile_summary, 400),
            "strictness_level": preference.strictness_level,
        }

    @classmethod
    def _completion_score(cls, person_snapshot: dict[str, Any], preference_snapshot: dict[str, Any], ai_content: str | None) -> int:
        fields = [
            "gender_code",
            "age",
            "height_cm",
            "occupation",
            "annual_income_code",
            "marital_status_code",
            "education_code",
            "residence",
            "house_status_code",
            "car_status_code",
        ]
        filled = sum(1 for field in fields if person_snapshot.get(field) not in (None, "", []))
        score = int(filled / len(fields) * 70)
        if (person_snapshot.get("photo_count") or 0) > 0:
            score += 10
        if preference_snapshot:
            score += 10
        if ai_content:
            score += 10
        if person_snapshot.get("profile_insight"):
            score += 10
        return min(score, 100)

    @classmethod
    def _insight_snapshot(cls, insight: PersonProfileInsightModel | None) -> dict[str, Any]:
        if not insight or insight.profile_status != "active":
            return {}
        return {
            "性格标签": insight.personality_tags or [],
            "家庭背景": cls._safe_text(insight.family_background, 300),
            "情感经历": cls._safe_text(insight.relationship_history, 300),
            "婚恋观": cls._safe_text(insight.marriage_view, 300),
            "沟通方式": cls._safe_text(insight.communication_style, 200),
            "情感需求": cls._safe_text(insight.emotional_needs, 200),
            "风险等级": insight.risk_level,
            "风险提示": cls._safe_text(insight.risk_notes, 240),
            "沟通禁忌": cls._safe_text(insight.communication_taboo, 240),
            "推荐策略": cls._safe_text(insight.recommendation_strategy, 300),
            "红娘评价": cls._safe_text(insight.matchmaker_comment, 240),
            "红娘印象": cls._safe_text(insight.public_matchmaker_impression, 240),
            "关键词": insight.keywords or [],
        }

    @classmethod
    def _insight_preference_snapshot(cls, insight: PersonProfileInsightModel | None) -> dict[str, Any]:
        if not insight or insight.profile_status != "active":
            return {}
        return {
            "建议新增一票否决项": insight.hard_reject_items or [],
            "建议重点偏好": insight.soft_preference_items or [],
            "建议放宽条件": insight.compromise_items or [],
            "深访推荐策略": cls._safe_text(insight.recommendation_strategy, 300),
        }

    @classmethod
    def _text_from_snapshot(cls, title: str, snapshot: dict[str, Any]) -> str:
        if not snapshot:
            return f"{title}：暂无。"
        parts: list[str] = [f"{title}："]
        for key, value in snapshot.items():
            if value in (None, "", [], {}):
                continue
            parts.append(f"{key}={value}")
        return "；".join(parts)

    @classmethod
    async def _build_profile_payload(cls, db: AsyncSession, person_id: int) -> dict[str, Any] | None:
        person = (
            await db.execute(select(CrmPersonModel).where(CrmPersonModel.id == person_id, CrmPersonModel.is_deleted == False))
        ).scalars().first()
        if not person:
            return None
        preference = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id == person_id,
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().first()
        ai_profile = (
            await db.execute(
                select(PersonAiProfileModel)
                .where(
                    PersonAiProfileModel.person_id == person_id,
                    PersonAiProfileModel.profile_type == "miai_impression",
                    PersonAiProfileModel.is_effective == True,
                    PersonAiProfileModel.is_deleted == False,
                )
                .order_by(PersonAiProfileModel.generated_at.desc(), PersonAiProfileModel.id.desc())
            )
        ).scalars().first()
        insight = (
            await db.execute(
                select(PersonProfileInsightModel)
                .where(
                    PersonProfileInsightModel.person_id == person_id,
                    PersonProfileInsightModel.is_deleted == False,
                )
                .order_by(PersonProfileInsightModel.insight_updated_at.desc(), PersonProfileInsightModel.id.desc())
            )
        ).scalars().first()
        self_snapshot = cls._person_snapshot(person)
        preference_snapshot = cls._preference_snapshot(preference)
        insight_snapshot = cls._insight_snapshot(insight)
        insight_preference_snapshot = cls._insight_preference_snapshot(insight)
        if insight_snapshot:
            self_snapshot["profile_insight"] = insight_snapshot
        if insight_preference_snapshot:
            preference_snapshot["profile_insight"] = insight_preference_snapshot
        ai_content = cls._safe_text(ai_profile.content if ai_profile else None, 600)
        ai_snapshot = {"miai_impression": ai_content} if ai_content else {}
        self_text = "\n".join(
            [
                cls._text_from_snapshot("基础资料", self_snapshot),
                cls._text_from_snapshot("红娘深访画像", insight_snapshot),
                cls._text_from_snapshot("觅AI印象", ai_snapshot),
            ]
        )
        preference_text = "\n".join(
            [
                cls._text_from_snapshot("择偶要求", preference_snapshot),
                cls._text_from_snapshot("深访择偶要求复核建议", insight_preference_snapshot),
            ]
        )
        return {
            "self_snapshot": self_snapshot,
            "preference_snapshot": preference_snapshot,
            "ai_profile_snapshot": ai_snapshot,
            "self_input_text": self_text,
            "preference_input_text": preference_text,
            "completeness_score": cls._completion_score(self_snapshot, preference_snapshot, ai_content),
        }

    @classmethod
    async def _ensure_profile(cls, db: AsyncSession, person_id: int) -> PersonMatchProfileModel | None:
        profile = (
            await db.execute(
                select(PersonMatchProfileModel).where(
                    PersonMatchProfileModel.person_id == person_id,
                    PersonMatchProfileModel.is_deleted == False,
                )
            )
        ).scalars().first()
        payload = await cls._build_profile_payload(db, person_id)
        if payload is None:
            return None
        if profile is None:
            profile = PersonMatchProfileModel(brand_id=1, person_id=person_id)
            db.add(profile)
        profile.self_snapshot = payload["self_snapshot"]
        profile.preference_snapshot = payload["preference_snapshot"]
        profile.ai_profile_snapshot = payload["ai_profile_snapshot"]
        profile.self_input_text = payload["self_input_text"]
        profile.preference_input_text = payload["preference_input_text"]
        profile.completeness_score = payload["completeness_score"]
        profile.last_snapshot_at = datetime.now()
        profile.last_error = None
        await db.flush()
        return profile

    @classmethod
    async def mark_dirty(
        cls,
        db: AsyncSession,
        person_id: int,
        dirty_parts: list[str] | tuple[str, ...] | set[str],
        source_type: str,
        source_id: str | int | None = None,
    ) -> None:
        parts = {part for part in dirty_parts if part in VECTOR_TYPES}
        if not parts:
            return
        profile = await cls._ensure_profile(db, person_id)
        if not profile:
            return
        if SELF_PROFILE in parts:
            profile.self_vector_dirty = True
        if PREFERENCE in parts:
            profile.preference_vector_dirty = True
        for vector_type in parts:
            await cls._enqueue_task(db, person_id, vector_type, source_type, source_id)
        await db.flush()

    @classmethod
    async def _enqueue_task(
        cls,
        db: AsyncSession,
        person_id: int,
        vector_type: str,
        source_type: str,
        source_id: str | int | None = None,
    ) -> PersonMatchVectorTaskModel:
        existing = (
            await db.execute(
                select(PersonMatchVectorTaskModel)
                .where(
                    PersonMatchVectorTaskModel.person_id == person_id,
                    PersonMatchVectorTaskModel.vector_type == vector_type,
                    PersonMatchVectorTaskModel.status.in_(["pending", "failed"]),
                    PersonMatchVectorTaskModel.is_deleted == False,
                )
                .order_by(PersonMatchVectorTaskModel.id.desc())
            )
        ).scalars().first()
        if existing:
            existing.source_type = source_type
            existing.source_id = str(source_id) if source_id is not None else None
            existing.status = "pending"
            existing.retry_count = 0
            existing.next_retry_at = datetime.now()
            existing.last_error = None
            return existing
        task = PersonMatchVectorTaskModel(
            brand_id=1,
            person_id=person_id,
            vector_type=vector_type,
            source_type=source_type,
            source_id=str(source_id) if source_id is not None else None,
            status="pending",
            retry_count=0,
            next_retry_at=datetime.now(),
        )
        db.add(task)
        return task

    @classmethod
    async def process_due_tasks(cls, batch_size: int = 10) -> int:
        processed = 0
        worker_id = f"{socket.gethostname()}:{WORKER_JOB_ID}"
        now = datetime.now()
        stale_cutoff = now - timedelta(minutes=15)
        async with async_db_session() as db:
            tasks = (
                await db.execute(
                    select(PersonMatchVectorTaskModel)
                    .where(
                        PersonMatchVectorTaskModel.is_deleted == False,
                        or_(
                            PersonMatchVectorTaskModel.status.in_(["pending", "failed"]),
                            and_(
                                PersonMatchVectorTaskModel.status == "processing",
                                PersonMatchVectorTaskModel.locked_at <= stale_cutoff,
                            ),
                        ),
                        PersonMatchVectorTaskModel.retry_count < MAX_RETRY_COUNT,
                        PersonMatchVectorTaskModel.next_retry_at <= now,
                    )
                    .order_by(PersonMatchVectorTaskModel.next_retry_at.asc(), PersonMatchVectorTaskModel.id.asc())
                    .limit(batch_size)
                )
            ).scalars().all()
            for task in tasks:
                lock_key = f"match:vector:task:{task.id}"
                lock_value = f"{worker_id}:{datetime.now().timestamp()}"
                redis = cls._scheduler_redis()
                acquired = bool(await redis.set(lock_key, lock_value, ex=600, nx=True)) if redis else True
                if not acquired:
                    continue
                try:
                    task.status = "processing"
                    task.locked_at = datetime.now()
                    task.locked_by = worker_id
                    await db.commit()
                    await cls._process_one(task.id)
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
                    select(PersonMatchVectorTaskModel).where(
                        PersonMatchVectorTaskModel.id == task_id,
                        PersonMatchVectorTaskModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if not task or task.status == "cancelled":
                return
            try:
                settings = await cls.embedding_settings(db)
                if not settings["enabled"]:
                    raise CustomException(msg="匹配向量生成已关闭")
                if settings["provider"] != "local_text2vec":
                    raise CustomException(msg=f"暂不支持的向量提供者: {settings['provider']}")
                if settings["dimension"] != 768:
                    raise CustomException(msg="当前模型固定为768维，请保持 match.embedding.dimension=768")
                profile = await cls._ensure_profile(db, task.person_id)
                if not profile:
                    task.status = "cancelled"
                    await db.commit()
                    return
                input_text = profile.self_input_text if task.vector_type == SELF_PROFILE else profile.preference_input_text
                input_snapshot = profile.self_snapshot if task.vector_type == SELF_PROFILE else profile.preference_snapshot
                if not input_text:
                    input_text = "暂无资料。"
                embedding = LocalText2VecProvider.encode(input_text, settings["model_path"], settings["normalize"])
                vector = (
                    await db.execute(
                        select(PersonMatchVectorModel).where(
                            PersonMatchVectorModel.person_id == task.person_id,
                            PersonMatchVectorModel.vector_type == task.vector_type,
                            PersonMatchVectorModel.is_deleted == False,
                        )
                    )
                ).scalars().first()
                if vector is None:
                    vector = PersonMatchVectorModel(brand_id=1, person_id=task.person_id, vector_type=task.vector_type)
                    db.add(vector)
                vector.embedding = embedding
                vector.embedding_model = settings["model_name"]
                vector.embedding_dimension = settings["dimension"]
                vector.input_text = input_text
                vector.input_snapshot = input_snapshot
                vector.vector_status = "success"
                vector.last_vectorized_at = datetime.now()
                vector.last_error = None
                if task.vector_type == SELF_PROFILE:
                    profile.self_vector_dirty = False
                else:
                    profile.preference_vector_dirty = False
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
        async with async_db_session() as db:
            task = (
                await db.execute(select(PersonMatchVectorTaskModel).where(PersonMatchVectorTaskModel.id == task_id))
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
            task.next_retry_at = datetime.now() + timedelta(seconds=RETRY_DELAYS[delay_index] if retry_count < MAX_RETRY_COUNT else 86400)
            vector = (
                await db.execute(
                    select(PersonMatchVectorModel).where(
                        PersonMatchVectorModel.person_id == task.person_id,
                        PersonMatchVectorModel.vector_type == task.vector_type,
                        PersonMatchVectorModel.is_deleted == False,
                    )
                )
            ).scalars().first()
            if vector:
                vector.vector_status = "failed"
                vector.last_error = task.last_error
            await db.commit()

    @classmethod
    def _cosine_score(cls, left: list[float] | None, right: list[float] | None) -> int | None:
        if left is None or right is None or len(left) != len(right):
            return None
        dot = sum(a * b for a, b in zip(left, right, strict=True))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if not left_norm or not right_norm:
            return None
        similarity = max(min(dot / (left_norm * right_norm), 1), -1)
        return int(round((similarity + 1) * 50))

    @classmethod
    def _range_block(cls, label: str, value: int | None, min_value: int | None, max_value: int | None) -> str | None:
        if value is None:
            return None
        if min_value is not None and value < min_value:
            return f"{label}低于期望"
        if max_value is not None and value > max_value:
            return f"{label}高于期望"
        return None

    @classmethod
    def _region_match(cls, target: str | None, preferred: list[str]) -> bool:
        if not preferred:
            return True
        if not target:
            return False
        target_norm = target.replace("省", "").replace("市", "").replace("区", "").replace("县", "")
        for item in preferred:
            item_norm = str(item).replace("省", "").replace("市", "").replace("区", "").replace("县", "")
            if item_norm and (target_norm.startswith(item_norm) or item_norm in target_norm):
                return True
        return False

    @classmethod
    def _dedupe_texts(cls, items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

    @classmethod
    def _hard_filter(cls, source: CrmPersonModel, target: CrmPersonModel, preference: PersonPartnerPreferenceModel | None) -> list[str]:
        reasons: list[str] = []
        if source.id == target.id:
            reasons.append("不能推荐本人")
        if source.gender in {"0", "1"} and target.gender in {"0", "1"} and source.gender == target.gender:
            reasons.append("性别方向不匹配")
        if source.gender not in {"0", "1"} or target.gender not in {"0", "1"}:
            reasons.append("性别资料不完整")
        if preference:
            target_age = cls._age(target.birth_date)
            age_block = cls._range_block("年龄", target_age, preference.age_min, preference.age_max)
            if age_block:
                reasons.append(age_block)
            height_block = cls._range_block("身高", target.height_cm, preference.height_min_cm, preference.height_max_cm)
            if height_block:
                reasons.append(height_block)
            if preference.preferred_marital_status_codes and target.marital_status not in preference.preferred_marital_status_codes:
                reasons.append("婚况不符合期望")
            if not cls._region_match(target.residence, preference.preferred_residence_region_codes or []):
                reasons.append("常驻地不符合期望")
        return reasons

    @classmethod
    def _structured_score(
        cls,
        source: CrmPersonModel,
        target: CrmPersonModel,
        preference: PersonPartnerPreferenceModel | None,
    ) -> tuple[int, list[str], list[str]]:
        matched: list[str] = []
        risks: list[str] = []
        if not preference:
            return 70, ["暂未填写择偶要求，按基础资料计算"], ["择偶要求缺失，匹配精度较低"]
        score = 70
        checks = [
            ("学历", target.education, preference.preferred_education_codes, EDUCATION_LABELS),
            ("收入", target.annual_income, preference.preferred_annual_income_codes, ANNUAL_INCOME_LABELS),
            ("房产", target.house_status, preference.preferred_house_status_codes, HOUSE_STATUS_LABELS),
            ("车辆", target.car_status, preference.preferred_car_status_codes, CAR_STATUS_LABELS),
        ]
        for label, value, preferred, _labels in checks:
            if not preferred:
                continue
            if value in preferred:
                score += 7
                matched.append(f"{label}符合期望")
            else:
                score -= 5
                risks.append(f"{label}与期望略有差异")
        if preference.age_min or preference.age_max:
            matched.append("年龄在期望范围内")
        if preference.height_min_cm or preference.height_max_cm:
            matched.append("身高在期望范围内")
        if preference.preferred_residence_region_codes:
            matched.append("常驻地符合期望")
        if source.residence and target.residence and cls._region_match(target.residence, [source.residence.split("/")[0].strip()]):
            score += 5
            matched.append("生活城市或区域接近")
        if not matched and not risks:
            matched.append("结构化择偶条件较少，按基础资料试算")
            risks.append("择偶条件不完整，建议补充后再精细匹配")
        return max(0, min(score, 100)), matched, risks

    @classmethod
    async def candidate_debug(cls, db: AsyncSession, person_id: int | None, display_no: str | None, scene: str, page_no: int, page_size: int) -> dict[str, Any]:
        source = None
        display_no = display_no.strip() if display_no else None
        conditions = [CrmPersonModel.is_deleted == False]
        if person_id:
            conditions.append(CrmPersonModel.id == person_id)
        if display_no:
            conditions.append(CrmPersonModel.display_no == display_no)
        if person_id or display_no:
            source = (await db.execute(select(CrmPersonModel).where(*conditions))).scalars().first()
        if not source:
            raise CustomException(msg="未找到匹配发起用户")
        return await cls.match_candidates(db, source.id, scene, page_no, page_size)

    @classmethod
    async def match_candidates(cls, db: AsyncSession, person_id: int, scene: str, page_no: int = 1, page_size: int = 20) -> dict[str, Any]:
        source = (
            await db.execute(select(CrmPersonModel).where(CrmPersonModel.id == person_id, CrmPersonModel.is_deleted == False))
        ).scalars().first()
        if not source:
            raise CustomException(msg="未找到匹配发起用户")
        source_pref = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id == source.id,
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().first()
        await cls.mark_dirty(db, source.id, [SELF_PROFILE, PREFERENCE], "match_debug", None)
        await db.flush()

        candidate_conditions = [
            MiniProgramUserModel.is_deleted == False,
            MiniProgramUserModel.person_id.is_not(None),
            MiniProgramUserModel.is_invisible == False,
            CrmPersonModel.is_deleted == False,
            CrmPersonModel.id != source.id,
        ]
        if not await cls._subscription_include_pending_users(db):
            candidate_conditions.append(MiniProgramUserModel.registered_at.is_not(None))

        rows = (
            await db.execute(
                select(MiniProgramUserModel, CrmPersonModel)
                .join(CrmPersonModel, MiniProgramUserModel.person_id == CrmPersonModel.id)
                .where(*candidate_conditions)
            )
        ).all()
        scored_items = await cls.score_people(
            db=db,
            source=source,
            target_rows=[person for _user, person in rows],
            scene=scene,
            user_map={person.id: user for user, person in rows},
            source_pref=source_pref,
        )
        total = len(scored_items)
        offset = (page_no - 1) * page_size
        page_items = scored_items[offset : offset + page_size]
        source_vectors = await cls._person_vector_status_map(db, {source.id})
        settings = await cls.embedding_settings(db)
        return {
            "query_person_id": source.id,
            "query_display_no": source.display_no,
            "scene": scene,
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": offset + page_size < total,
            "model_info": {
                "provider": settings["provider"],
                "model_name": settings["model_name"],
                "dimension": settings["dimension"],
                "enabled": settings["enabled"],
            },
            "vector_status": source_vectors,
            "items": page_items,
        }

    @classmethod
    async def _person_vector_status_map(cls, db: AsyncSession, person_ids: set[int]) -> dict[str, Any]:
        vector_rows = (
            await db.execute(
                select(PersonMatchVectorModel).where(
                    PersonMatchVectorModel.person_id.in_(person_ids or {-1}),
                    PersonMatchVectorModel.is_deleted == False,
                )
            )
        ).scalars().all()
        vector_map = {(row.person_id, row.vector_type): row for row in vector_rows}
        person_id = next(iter(person_ids), None)
        if not person_id:
            return {}
        return {
            vector_type: cls._vector_status_out(vector_map.get((person_id, vector_type)))
            for vector_type in (SELF_PROFILE, PREFERENCE)
        }

    @classmethod
    async def score_people(
        cls,
        db: AsyncSession,
        source: CrmPersonModel,
        target_rows: list[CrmPersonModel],
        scene: str = "matchmaker_service",
        user_map: dict[int, MiniProgramUserModel] | None = None,
        source_pref: PersonPartnerPreferenceModel | None = None,
    ) -> list[dict[str, Any]]:
        if source_pref is None:
            source_pref = (
                await db.execute(
                    select(PersonPartnerPreferenceModel).where(
                        PersonPartnerPreferenceModel.person_id == source.id,
                        PersonPartnerPreferenceModel.is_deleted == False,
                    )
                )
            ).scalars().first()
        await cls.mark_dirty(db, source.id, [SELF_PROFILE, PREFERENCE], "match_debug" if scene == "debug" else scene, None)
        await db.flush()

        candidate_person_ids = {person.id for person in target_rows}
        candidate_person_ids.add(source.id)
        pref_rows = (
            await db.execute(
                select(PersonPartnerPreferenceModel).where(
                    PersonPartnerPreferenceModel.person_id.in_(candidate_person_ids),
                    PersonPartnerPreferenceModel.is_deleted == False,
                )
            )
        ).scalars().all()
        pref_map = {row.person_id: row for row in pref_rows}
        profile_rows = (
            await db.execute(
                select(PersonMatchProfileModel).where(
                    PersonMatchProfileModel.person_id.in_(candidate_person_ids),
                    PersonMatchProfileModel.is_deleted == False,
                )
            )
        ).scalars().all()
        profile_map = {row.person_id: row for row in profile_rows}
        vector_rows = (
            await db.execute(
                select(PersonMatchVectorModel).where(
                    PersonMatchVectorModel.person_id.in_(candidate_person_ids),
                    PersonMatchVectorModel.is_deleted == False,
                )
            )
        ).scalars().all()
        vector_map = {(row.person_id, row.vector_type): row for row in vector_rows}

        items: list[dict[str, Any]] = []
        user_map = user_map or {}
        for target in target_rows:
            blocked = cls._hard_filter(source, target, source_pref)
            target_pref = pref_map.get(target.id)
            reverse_blocked = cls._hard_filter(target, source, target_pref)
            if blocked or reverse_blocked:
                continue
            structured_score, matched_points, risk_points = cls._structured_score(source, target, source_pref)
            reverse_structured, reverse_matched, reverse_risks = cls._structured_score(target, source, target_pref)
            structured_score = int(round((structured_score * 0.65) + (reverse_structured * 0.35)))
            matched_points.extend([f"对方也匹配：{item}" for item in reverse_matched[:2]])
            risk_points.extend(reverse_risks[:2])

            source_preference_vector = vector_map.get((source.id, PREFERENCE))
            source_self_vector = vector_map.get((source.id, SELF_PROFILE))
            target_preference_vector = vector_map.get((target.id, PREFERENCE))
            target_self_vector = vector_map.get((target.id, SELF_PROFILE))
            forward_score = cls._cosine_score(source_preference_vector.embedding if source_preference_vector else None, target_self_vector.embedding if target_self_vector else None)
            reverse_score = cls._cosine_score(target_preference_vector.embedding if target_preference_vector else None, source_self_vector.embedding if source_self_vector else None)
            vector_status = "success" if forward_score is not None and reverse_score is not None else "missing"
            if vector_status == "missing":
                await cls.mark_dirty(db, target.id, [SELF_PROFILE, PREFERENCE], "match_missing_vector", None)
                vector_score = None
                effective_vector_score = 70
                risk_points.append("画像向量暂未完整生成，当前为结构化试算")
            else:
                vector_score = int(round((forward_score or 0) * 0.65 + (reverse_score or 0) * 0.35))
                effective_vector_score = vector_score
                if vector_score >= 80:
                    matched_points.append("画像语义相似度较高")
                elif vector_score >= 65:
                    matched_points.append("画像语义有一定相似度")
                elif vector_score < 45:
                    risk_points.append("画像语义相似度偏低")
            match_score = int(round(structured_score * 0.55 + effective_vector_score * 0.45))
            target_profile = profile_map.get(target.id)
            completeness_score = target_profile.completeness_score if target_profile else 50
            confidence_score = min(100, int(round((completeness_score * 0.75) + (100 if vector_status == "success" else 45) * 0.25)))
            user = user_map.get(target.id)
            activity_score = 80 if user and user.last_login_at and user.last_login_at > datetime.now() - timedelta(days=30) else 50
            freshness_score = 80 if user and user.registered_at and user.registered_at > datetime.now() - timedelta(days=30) else 50
            rank_score = int(round(match_score * 0.85 + completeness_score * 0.07 + activity_score * 0.05 + freshness_score * 0.03))
            matched_points = cls._dedupe_texts(matched_points)
            risk_points = cls._dedupe_texts(risk_points)
            user_reason = cls._user_reason(target, matched_points, risk_points)
            admin_reason = cls._admin_reason(structured_score, vector_score, matched_points, risk_points)
            items.append(
                {
                    "person_id": target.id,
                    "display_no": target.display_no,
                    "nickname": user.nickname if user else target.name,
                    "gender": cls._label(GENDER_LABELS, target.gender),
                    "age": cls._age(target.birth_date),
                    "height_cm": target.height_cm,
                    "residence": target.residence,
                    "education": cls._label(EDUCATION_LABELS, target.education),
                    "annual_income": cls._label(ANNUAL_INCOME_LABELS, target.annual_income),
                    "marital_status": cls._label(MARITAL_STATUS_LABELS, target.marital_status),
                    "match_score": match_score,
                    "rank_score": rank_score,
                    "confidence_score": confidence_score,
                    "structured_score": structured_score,
                    "vector_score": vector_score,
                    "vector_status": vector_status,
                    "matched_points": matched_points[:6],
                    "risk_points": risk_points[:5],
                    "blocked_reasons": [],
                    "user_reason": user_reason,
                    "admin_reason": admin_reason,
                }
            )
        items.sort(key=lambda item: (item["rank_score"], item["match_score"]), reverse=True)
        return items

    @classmethod
    async def _subscription_include_pending_users(cls, db: AsyncSession) -> bool:
        value = (
            await db.execute(
                select(ParamsModel.config_value).where(
                    ParamsModel.config_key == "miniprogram.plaza.show_pending_users",
                    ParamsModel.is_deleted == False,
                    ParamsModel.status == "0",
                )
            )
        ).scalar()
        return str(value or "").lower() in {"true", "1", "yes", "on"}

    @classmethod
    def _vector_status_out(cls, vector: PersonMatchVectorModel | None) -> dict[str, Any]:
        if not vector:
            return {"status": "missing"}
        return {
            "status": vector.vector_status,
            "model": vector.embedding_model,
            "dimension": vector.embedding_dimension,
            "last_vectorized_at": vector.last_vectorized_at,
            "last_error": vector.last_error,
        }

    @classmethod
    def _user_reason(cls, target: CrmPersonModel, matched: list[str], risks: list[str]) -> str:
        basis = "、".join(matched[:3]) if matched else "基础条件有一定匹配度"
        risk_tail = "，也有少量需要进一步了解的地方" if risks else ""
        return f"你们在{basis}方面比较接近{risk_tail}，可以从生活节奏和未来规划开始轻松了解。"

    @classmethod
    def _admin_reason(cls, structured_score: int, vector_score: int | None, matched: list[str], risks: list[str]) -> str:
        vector_text = f"{vector_score}" if vector_score is not None else "缺失"
        return (
            f"结构化分{structured_score}，向量分{vector_text}。"
            f"命中：{'、'.join(matched[:5]) or '暂无'}。"
            f"风险：{'、'.join(risks[:5]) or '暂无'}。"
        )
