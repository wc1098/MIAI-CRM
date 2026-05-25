import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import Request, UploadFile
from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.module_common.upload.schema import UploadConfirmRequestSchema
from app.api.v1.module_common.upload.service import CommonUploadService
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.params.model import ParamsModel
from app.api.v1.module_system.user.model import UserModel
from app.core.base_schema import UploadResponseSchema
from app.core.exceptions import CustomException
from app.core.logger import log as logger
from app.plugin.module_crm.customer.model import CrmCustomerCertificationMaterialModel
from app.plugin.module_crm.lead.model import CrmPersonModel
from app.plugin.module_mp.auth.model import MiniProgramUserModel, SourceEventModel
from app.plugin.module_mp.plaza.model import MpUnlockCouponModel
from app.plugin.module_payment.core.model import PaymentOrderModel
from app.plugin.module_payment.core.service import PaymentService
from app.utils.storage_config import StorageConfig
from app.utils.upload_util import UploadUtil

from .model import (
    CertificationApplicationModel,
    CertificationItemModel,
    CertificationMaterialModel,
    CertificationPackageModel,
    CertificationRecordModel,
    CertificationSensitiveAccessLogModel,
    CertificationVerificationLogModel,
    FaceDetectionLogModel,
    IdCardOcrLogModel,
)
from .schema import (
    ID_CARD_PATTERN,
    MANUAL_ITEM_CODES,
    CertificationApplicationQueryParam,
    CertificationLogQueryParam,
    CertificationRecordQueryParam,
)

CERTIFICATION_BIZ_TYPE = "certification_package"
STAFF_UPLOAD_SOURCE = "staff_upload"
STAFF_UPLOAD_LEVEL_CODE = "staff_archive"
STAFF_UPLOAD_LEVEL_NAME = "工作人员提交认证"
STAFF_MATERIAL_ITEM_MAP = {"id_card_photo": "real_name"}
DEFAULT_ITEMS = [
    ("phone", "手机认证", "auto_api", "phone_bound", False, "注册绑定手机号后自动完成", None, 1),
    ("real_name", "实名认证", "auto_api", "real_name_3_meta", False, "姓名、手机号、身份证号三要素核验", None, 2),
    ("real_photo", "真人照片认证", "auto_api", "face_photo_detect", True, "上传本人清晰单人照片", None, 3),
    ("education", "学历认证", "manual", None, True, "上传学历证明材料", 3650, 4),
    ("income", "收入认证", "manual", None, True, "上传收入证明材料", 365, 5),
    ("marital", "婚况认证", "manual", None, True, "上传婚况证明材料", 3650, 6),
    ("house", "房产认证", "manual", None, True, "上传房产证明材料", 3650, 7),
    ("car", "车辆认证", "manual", None, True, "上传车辆证明材料", 3650, 8),
    ("visit", "到店认证", "manual", None, False, "总部根据到店记录或门店证明审核", 3650, 9),
    ("occupation", "职业认证", "manual", None, True, "上传职业证明材料", 365, 10),
]
DEFAULT_PACKAGES = [
    ("basic", "基础认证", Decimal("0.00"), ["phone", "real_name", "real_photo"], 1, 7, "实名与真人照片基础可信认证", 1),
    ("advanced", "高级认证", Decimal("0.00"), ["phone", "real_name", "real_photo", "education", "income", "marital"], 2, 7, "补充学历、收入、婚况认证", 2),
    ("premium", "尊享认证", Decimal("0.00"), ["phone", "real_name", "real_photo", "education", "income", "marital", "house", "car", "visit", "occupation"], 3, 7, "完整高可信资料认证", 3),
]

LEVEL_LABELS = {"none": "未认证", "basic": "基础认证", "advanced": "高级认证", "premium": "尊享认证"}


def mask_id_card(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if len(value) <= 8:
        return value[0:2] + "*" * max(len(value) - 4, 0) + value[-2:]
    return value[:3] + "*" * (len(value) - 7) + value[-4:]


class CertificationService:
    """认证基座服务。"""

    @classmethod
    async def _param(cls, db: AsyncSession, key: str, default: str) -> str:
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
    async def ensure_defaults(cls, db: AsyncSession) -> None:
        rows = (await db.execute(select(CertificationItemModel))).scalars().all()
        by_code = {row.item_code: row for row in rows}
        for code, name, mode, verifier, material_required, material_desc, validity_days, sort in DEFAULT_ITEMS:
            if code not in by_code:
                db.add(
                    CertificationItemModel(
                        brand_id=1,
                        item_code=code,
                        item_name=name,
                        verify_mode=mode,
                        verifier_code=verifier,
                        material_required=material_required,
                        material_desc=material_desc,
                        validity_days=validity_days,
                        sort=sort,
                    )
                )
        packages = (await db.execute(select(CertificationPackageModel))).scalars().all()
        packages_by_level = {row.level_code: row for row in packages}
        for level, name, price, item_codes, coupons, valid_days, desc, sort in DEFAULT_PACKAGES:
            if level not in packages_by_level:
                db.add(
                    CertificationPackageModel(
                        brand_id=1,
                        level_code=level,
                        level_name=name,
                        price=price,
                        item_codes=item_codes,
                        reward_coupon_count=coupons,
                        reward_coupon_valid_days=valid_days,
                        benefit_desc=desc,
                        sort=sort,
                    )
                )
        await db.flush()

    @classmethod
    async def _current_user(cls, db: AsyncSession, user_id: int) -> MiniProgramUserModel:
        user = await db.get(MiniProgramUserModel, user_id, options=[selectinload(MiniProgramUserModel.person)])
        if not user or user.is_deleted or not user.registered_at or not user.person_id:
            raise CustomException(msg="请先完成注册资料")
        return user

    @classmethod
    async def _items_map(cls, db: AsyncSession) -> dict[str, CertificationItemModel]:
        await cls.ensure_defaults(db)
        rows = (await db.execute(select(CertificationItemModel).where(CertificationItemModel.is_deleted == False))).scalars().all()
        return {row.item_code: row for row in rows}

    @classmethod
    async def mp_center(cls, db: AsyncSession, user_id: int) -> dict[str, Any]:
        await cls.ensure_defaults(db)
        user = await cls._current_user(db, user_id)
        items = await cls.list_items(db)
        packages = (
            await db.execute(
                select(CertificationPackageModel)
                .where(CertificationPackageModel.is_deleted == False, CertificationPackageModel.status == "0")
                .order_by(CertificationPackageModel.sort.asc(), CertificationPackageModel.id.asc())
            )
        ).scalars().all()
        apps = (
            await db.execute(
                select(CertificationApplicationModel)
                .where(CertificationApplicationModel.user_id == user.id, CertificationApplicationModel.is_deleted == False)
                .options(selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials))
                .order_by(CertificationApplicationModel.id.desc())
            )
        ).scalars().all()
        current_app = next((app for app in apps if app.application_status in {"pending_payment", "paid_pending_submit", "in_progress"}), None)
        records = list(current_app.records or []) if current_app else []
        real_name_record = next((record for record in records if record.item_code == "real_name"), None)
        limits = await cls._real_name_limit_state(db, real_name_record, user, None) if real_name_record else await cls._real_name_default_limit_state(db)
        return {
            "current_level": getattr(user.person, "certification_level", "none") if user.person else "none",
            "current_level_name": LEVEL_LABELS.get(getattr(user.person, "certification_level", "none") if user.person else "none", "未认证"),
            "certification_summary": getattr(user.person, "certification_summary", None) if user.person else None,
            "items": items,
            "packages": [cls._package_out(row) for row in packages],
            "current_application": cls._application_out(current_app),
            "actionable_records": {
                "not_submitted": [cls._record_out(record) for record in records if record.record_status in {"not_submitted", "rejected"}],
                "pending_review": [cls._record_out(record) for record in records if record.record_status == "pending_review"],
                "approved": [cls._record_out(record) for record in records if record.record_status == "approved"],
            },
            "limits": {"real_name": limits},
            "applications": [cls._application_out(row) for row in apps],
        }

    @classmethod
    async def create_order(cls, db: AsyncSession, request: Request, user_id: int, package_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        await cls.ensure_defaults(db)
        package = await db.get(CertificationPackageModel, package_id)
        if not package or package.is_deleted or package.status != "0":
            raise CustomException(msg="认证套餐不存在或已停用")
        app = CertificationApplicationModel(
            brand_id=1,
            user_id=user.id,
            person_id=user.person_id,
            package_id=package.id,
            level_code=package.level_code,
            level_name=package.level_name,
            item_codes=package.item_codes,
            application_status="pending_payment",
        )
        db.add(app)
        await db.flush()
        order = await PaymentService.create_order(
            db,
            biz_type=CERTIFICATION_BIZ_TYPE,
            biz_id=app.id,
            subject=f"{package.level_name}认证",
            amount=package.price,
            store_id=await cls._default_store_id(db),
            person_id=user.person_id,
            mp_user_id=user.id,
            expire_minutes=24 * 60,
            extra={"package_id": package.id, "level_code": package.level_code},
        )
        app.order_id = order.id
        if package.price <= 0:
            await PaymentService.mark_order_paid(
                db,
                order,
                {"out_order_no": order.order_no, "total_amount": "0.00", "trade_status": "SUCCESS", "zero_price": True},
                None,
            )
            paid_app = await db.get(CertificationApplicationModel, app.id, options=[selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials)])
            return {"application": cls._application_out(paid_app), "order": cls._order_out(order), "payment": {"paid": True}}
        if not user.openid:
            raise CustomException(msg="当前用户缺少微信openid，无法发起支付")
        payment = await PaymentService.create_cloudpay_mp_payment(db, order=order, buyer_id=user.openid, notify_url=cls._notify_url(request))
        return {"application": cls._application_out(app), "order": cls._order_out(order), "payment": payment}

    @classmethod
    async def continue_pay(cls, db: AsyncSession, request: Request, user_id: int, order_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        order = await db.get(PaymentOrderModel, order_id)
        if not order or order.is_deleted or order.biz_type != CERTIFICATION_BIZ_TYPE or order.mp_user_id != user.id:
            raise CustomException(msg="认证订单不存在")
        if order.pay_status == "paid":
            await cls.on_payment_success(db, order)
            app = await db.get(CertificationApplicationModel, order.biz_id, options=[selectinload(CertificationApplicationModel.records)])
            return {"paid": True, "application": cls._application_out(app)}
        if order.expire_at and datetime.now() >= order.expire_at:
            await PaymentService.close_order(db, order)
            raise CustomException(msg="订单已关闭，请重新购买")
        payment = await PaymentService.create_cloudpay_mp_payment(db, order=order, buyer_id=user.openid, notify_url=cls._notify_url(request))
        return {"order": cls._order_out(order), "payment": payment}

    @classmethod
    async def on_payment_success(cls, db: AsyncSession, order: PaymentOrderModel) -> None:
        if order.biz_type != CERTIFICATION_BIZ_TYPE:
            return
        app = await db.get(CertificationApplicationModel, order.biz_id, options=[selectinload(CertificationApplicationModel.records)])
        if not app or app.is_deleted:
            return
        if app.application_status not in {"pending_payment", "paid_pending_submit"}:
            return
        await db.refresh(app, ["records"])
        app.order_id = order.id
        app.paid_at = order.paid_at or datetime.now()
        app.application_status = "paid_pending_submit"
        await cls._ensure_records(db, app)
        await cls._try_complete(db, app)

    @classmethod
    async def _ensure_records(cls, db: AsyncSession, app: CertificationApplicationModel) -> None:
        items = await cls._items_map(db)
        existing_records = app.__dict__.get("records") or []
        existing = {record.item_code for record in existing_records}
        user = await db.get(MiniProgramUserModel, app.user_id, options=[selectinload(MiniProgramUserModel.person)])
        register_photo_url = None
        if user and user.person and user.person.photo_urls:
            register_photo_url = user.person.photo_urls[0]
        register_photo_passed = await cls._photo_has_passed_face_detection(db, register_photo_url) if register_photo_url else False
        for code in app.item_codes:
            if code in existing or code not in items:
                continue
            item = items[code]
            status = "not_submitted"
            submitted_at = None
            verified_at = None
            payload = None
            now = datetime.now()
            if code == "phone" and user and user.mobile:
                status = "approved"
                submitted_at = verified_at = now
            elif code == "real_photo" and register_photo_url and register_photo_passed:
                status = "approved"
                submitted_at = verified_at = now
                payload = {
                    "source": "register_photo",
                    "photo_url": register_photo_url,
                    "message": "复用注册真人照片自动通过",
                }
            record = CertificationRecordModel(
                brand_id=1,
                application_id=app.id,
                user_id=app.user_id,
                person_id=app.person_id,
                item_code=item.item_code,
                item_name=item.item_name,
                verify_mode=item.verify_mode,
                record_status=status,
                submitted_at=submitted_at,
                verified_at=verified_at,
                payload=payload,
            )
            db.add(record)
            await db.flush()
            if code == "real_photo" and register_photo_url and register_photo_passed:
                db.add(
                    CertificationMaterialModel(
                        brand_id=1,
                        application_id=app.id,
                        record_id=record.id,
                        user_id=app.user_id,
                        person_id=app.person_id,
                        item_code=code,
                        material_type="image",
                        file_name=str(register_photo_url).split("/")[-1] or "register_photo",
                        file_path=register_photo_url,
                        file_url=register_photo_url,
                        payload={"origin": "register_photo", "auto_approved": True},
                    )
                )
        await db.flush()
        await db.refresh(app, ["records"])
        for record in app.records or []:
            await cls._reuse_approved_or_pending_record(db, app, record)
            item = items.get(record.item_code)
            if item:
                await cls._attach_archived_materials_to_record(db, app, record, item)
        await db.flush()
        await db.refresh(app, ["records"])

    @classmethod
    async def _reuse_approved_or_pending_record(
        cls,
        db: AsyncSession,
        app: CertificationApplicationModel,
        record: CertificationRecordModel,
    ) -> None:
        if record.record_status != "not_submitted":
            return
        source_record = (
            await db.execute(
                select(CertificationRecordModel)
                .where(
                    CertificationRecordModel.person_id == app.person_id,
                    CertificationRecordModel.item_code == record.item_code,
                    CertificationRecordModel.id != record.id,
                    CertificationRecordModel.record_status.in_(["approved", "pending_review"]),
                    CertificationRecordModel.is_deleted == False,
                )
                .order_by(CertificationRecordModel.record_status.asc(), CertificationRecordModel.id.desc())
                .options(selectinload(CertificationRecordModel.materials))
            )
        ).scalars().first()
        if not source_record:
            return
        record.record_status = source_record.record_status
        record.submitted_at = record.submitted_at or source_record.submitted_at or datetime.now()
        record.verified_at = source_record.verified_at if source_record.record_status == "approved" else None
        record.reviewed_at = source_record.reviewed_at if source_record.record_status == "approved" else None
        record.reviewer_id = source_record.reviewer_id if source_record.record_status == "approved" else None
        record.reject_reason = None
        record.payload = {
            **(source_record.payload or {}),
            "reused_from_record_id": source_record.id,
            "reused_record_status": source_record.record_status,
        }
        existing_urls: set[str] = set()
        for material in source_record.materials or []:
            if material.file_url in existing_urls:
                continue
            db.add(
                CertificationMaterialModel(
                    brand_id=app.brand_id,
                    application_id=app.id,
                    record_id=record.id,
                    user_id=app.user_id,
                    person_id=app.person_id,
                    item_code=record.item_code,
                    material_type=material.material_type,
                    file_name=material.file_name,
                    file_path=material.file_path,
                    file_url=material.file_url,
                    payload={
                        **(material.payload or {}),
                        "origin": "reused_certification_record",
                        "source_record_id": source_record.id,
                        "source_material_id": material.id,
                    },
                )
            )
            existing_urls.add(material.file_url or "")

    @classmethod
    async def _attach_archived_materials_to_record(
        cls,
        db: AsyncSession,
        app: CertificationApplicationModel,
        record: CertificationRecordModel,
        item: CertificationItemModel,
    ) -> None:
        archive_codes = [record.item_code]
        if record.item_code == "real_name":
            archive_codes.append("id_card_photo")
        archived_materials = (
            await db.execute(
                select(CrmCustomerCertificationMaterialModel)
                .where(
                    CrmCustomerCertificationMaterialModel.person_id == app.person_id,
                    CrmCustomerCertificationMaterialModel.item_code.in_(archive_codes),
                    CrmCustomerCertificationMaterialModel.is_deleted == False,
                )
                .order_by(CrmCustomerCertificationMaterialModel.id.asc())
            )
        ).scalars().all()
        if not archived_materials:
            return
        existing_urls = set(
            (
                await db.execute(
                    select(CertificationMaterialModel.file_url).where(
                        CertificationMaterialModel.record_id == record.id,
                        CertificationMaterialModel.is_deleted == False,
                    )
                )
            ).scalars().all()
        )
        copied = False
        for material in archived_materials:
            if material.file_url in existing_urls:
                continue
            db.add(
                CertificationMaterialModel(
                    brand_id=app.brand_id,
                    application_id=app.id,
                    record_id=record.id,
                    user_id=app.user_id,
                    person_id=app.person_id,
                    item_code=record.item_code,
                    material_type=material.material_type,
                    file_name=material.file_name,
                    file_path=material.file_path,
                    file_url=material.file_url,
                    payload={
                        "origin": "customer_archive",
                        "archive_material_id": material.id,
                        "archive_item_code": material.item_code,
                        "archive_item_name": material.item_name,
                    },
                )
            )
            copied = True
        if copied:
            record.payload = {
                **(record.payload or {}),
                "prefilled_from_customer_archive": True,
            }
            if item.verify_mode == "manual" and record.record_status not in {"approved", "pending_review"}:
                record.record_status = "pending_review"
                record.submitted_at = record.submitted_at or datetime.now()

    @classmethod
    async def _photo_has_passed_face_detection(cls, db: AsyncSession, file_url: str | None) -> bool:
        if not file_url:
            return False
        count = (
            await db.execute(
                select(func.count(FaceDetectionLogModel.id)).where(
                    FaceDetectionLogModel.file_url == file_url,
                    FaceDetectionLogModel.passed == True,
                    FaceDetectionLogModel.is_deleted == False,
                )
            )
        ).scalar() or 0
        return count > 0

    @classmethod
    async def submit_real_name(cls, db: AsyncSession, user_id: int, name: str, id_card_no: str) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        id_card_no = id_card_no.upper()
        if not ID_CARD_PATTERN.match(id_card_no):
            raise CustomException(msg="身份证号格式不正确")
        app, record = await cls._active_record(db, user.id, "real_name")
        await cls._assert_real_name_limit(db, app, record, user, id_card_no)
        record.record_status = "verifying"
        record.submitted_at = datetime.now()
        record.payload = {"name": name, "id_card_no_masked": mask_id_card(id_card_no), "mobile": user.mobile}
        await db.flush()
        result = await cls._verify_real_name(db, app, record, name, user.mobile or "", id_card_no)
        if result:
            person = await db.get(CrmPersonModel, user.person_id)
            if person:
                person.name = name
                person.id_card_no = id_card_no
            record.record_status = "approved"
            record.verified_at = datetime.now()
            record.reject_reason = None
            await cls._try_complete(db, app)
        else:
            record.record_status = "rejected"
            record.reject_reason = "姓名、手机号或身份证号不一致，请核对后重新提交"
        await db.flush()
        return cls._record_out(record)

    @classmethod
    async def upload_material(
        cls,
        db: AsyncSession,
        user_id: int,
        item_code: str,
        file: UploadFile,
        base_url: str,
    ) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        app, record = await cls._active_record(db, user.id, item_code)
        filename, filepath, file_url = await UploadUtil.upload_file(file=file, base_url=base_url)
        face = None
        if item_code == "real_photo":
            face = await cls.detect_face_for_url(
                db,
                file_url=file_url,
                business_type="certification_material",
                business_id=record.id,
                user_id=user.id,
                person_id=user.person_id,
                require_pass=True,
            )
            record.record_status = "approved"
            record.submitted_at = record.submitted_at or datetime.now()
            record.verified_at = datetime.now()
            record.reject_reason = None
        elif item_code in MANUAL_ITEM_CODES:
            record.record_status = "pending_review"
            record.submitted_at = datetime.now()
            record.reject_reason = None
        else:
            raise CustomException(msg="该认证项不支持材料上传")
        material = CertificationMaterialModel(
            brand_id=1,
            application_id=app.id,
            record_id=record.id,
            user_id=user.id,
            person_id=user.person_id,
            item_code=item_code,
            material_type="image" if (file.content_type or "").startswith("image/") else "file",
            file_name=filename,
            file_path=str(filepath),
            file_url=file_url,
            payload={"origin_name": file.filename, "content_type": file.content_type, "face_detection": face},
        )
        db.add(material)
        await db.flush()
        await cls._try_complete(db, app)
        return {"material": cls._material_out(material), "record": cls._record_out(record)}

    @classmethod
    async def confirm_material(
        cls,
        db: AsyncSession,
        user_id: int,
        item_code: str,
        data: UploadConfirmRequestSchema,
    ) -> dict[str, Any]:
        if data.scene != "certification_material":
            raise CustomException(msg="上传场景不正确")
        user = await cls._current_user(db, user_id)
        app, record = await cls._active_record(db, user.id, item_code)
        upload = await CommonUploadService.confirm_uploaded_object(data)
        face = None
        if item_code == "real_photo":
            face = await cls.detect_face_for_url(
                db,
                file_url=upload.file_url,
                business_type="certification_material",
                business_id=record.id,
                user_id=user.id,
                person_id=user.person_id,
                require_pass=True,
            )
            record.record_status = "approved"
            record.submitted_at = record.submitted_at or datetime.now()
            record.verified_at = datetime.now()
            record.reject_reason = None
        elif item_code in MANUAL_ITEM_CODES:
            record.record_status = "pending_review"
            record.submitted_at = datetime.now()
            record.reject_reason = None
        else:
            raise CustomException(msg="该认证项不支持材料上传")
        material = CertificationMaterialModel(
            brand_id=1,
            application_id=app.id,
            record_id=record.id,
            user_id=user.id,
            person_id=user.person_id,
            item_code=item_code,
            material_type="image",
            file_name=upload.file_name,
            file_path=upload.object_key,
            file_url=upload.file_url,
            payload={
                "origin_name": upload.origin_name,
                "content_type": upload.content_type,
                "face_detection": face,
            },
        )
        db.add(material)
        await db.flush()
        await cls._try_complete(db, app)
        return {"material": cls._material_out(material), "record": cls._record_out(record)}

    @classmethod
    async def submit_manual(cls, db: AsyncSession, user_id: int, item_code: str, payload: dict | None) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        app, record = await cls._active_record(db, user.id, item_code)
        if item_code not in MANUAL_ITEM_CODES:
            raise CustomException(msg="该认证项不是人工审核项")
        record.record_status = "pending_review"
        record.submitted_at = datetime.now()
        record.payload = payload or {}
        record.reject_reason = None
        await db.flush()
        return cls._record_out(record)

    @classmethod
    async def _active_record(cls, db: AsyncSession, user_id: int, item_code: str) -> tuple[CertificationApplicationModel, CertificationRecordModel]:
        result = await db.execute(
            select(CertificationApplicationModel)
            .where(
                CertificationApplicationModel.user_id == user_id,
                CertificationApplicationModel.application_status.in_(["paid_pending_submit", "in_progress"]),
                CertificationApplicationModel.is_deleted == False,
            )
            .options(selectinload(CertificationApplicationModel.records))
            .order_by(CertificationApplicationModel.id.desc())
        )
        app = result.scalars().first()
        if not app:
            raise CustomException(msg="请先购买认证套餐")
        await cls._ensure_records(db, app)
        record = next((row for row in app.records if row.item_code == item_code), None)
        if not record:
            raise CustomException(msg="当前套餐不包含该认证项")
        if app.application_status == "paid_pending_submit":
            app.application_status = "in_progress"
        return app, record

    @classmethod
    async def _assert_real_name_limit(
        cls,
        db: AsyncSession,
        app: CertificationApplicationModel,
        record: CertificationRecordModel,
        user: MiniProgramUserModel,
        id_card_no: str,
    ) -> None:
        since_day = datetime.now() - timedelta(days=1)
        fail_count = (
            await db.execute(
                select(func.count(CertificationVerificationLogModel.id)).where(
                    CertificationVerificationLogModel.record_id == record.id,
                    CertificationVerificationLogModel.verifier_code == "real_name_3_meta",
                    CertificationVerificationLogModel.verify_status == "failed",
                    CertificationVerificationLogModel.verified_at >= since_day,
                )
            )
        ).scalar() or 0
        max_failed = int(await cls._param(db, "certification.real_name.max_failed_per_application", "3"))
        if fail_count >= max_failed:
            raise CustomException(msg="实名认证失败次数过多，请24小时后再试")
        for column, value, msg in [
            (CertificationVerificationLogModel.user_id, user.id, "今日实名认证次数过多，请明天再试"),
            (CertificationVerificationLogModel.request_snapshot["mobile"].as_string(), user.mobile, "该手机号今日核验次数过多"),
            (CertificationVerificationLogModel.request_snapshot["id_card_no_masked"].as_string(), mask_id_card(id_card_no), "该身份证今日核验次数过多"),
        ]:
            count = (
                await db.execute(
                    select(func.count(CertificationVerificationLogModel.id)).where(
                        CertificationVerificationLogModel.verifier_code == "real_name_3_meta",
                        column == value,
                        CertificationVerificationLogModel.verified_at >= since_day,
                    )
                )
            ).scalar() or 0
            if count >= int(await cls._param(db, "certification.real_name.daily_limit", "5")):
                raise CustomException(msg=msg)

    @classmethod
    async def _real_name_default_limit_state(cls, db: AsyncSession) -> dict[str, Any]:
        return {
            "max_failed_per_application": int(await cls._param(db, "certification.real_name.max_failed_per_application", "3")),
            "daily_limit": int(await cls._param(db, "certification.real_name.daily_limit", "5")),
            "failed_count": 0,
            "cooling": False,
            "cooldown_hours": 24,
            "message": None,
        }

    @classmethod
    async def _real_name_limit_state(
        cls,
        db: AsyncSession,
        record: CertificationRecordModel | None,
        user: MiniProgramUserModel,
        id_card_no: str | None,
    ) -> dict[str, Any]:
        max_failed = int(await cls._param(db, "certification.real_name.max_failed_per_application", "3"))
        daily_limit = int(await cls._param(db, "certification.real_name.daily_limit", "5"))
        since_day = datetime.now() - timedelta(days=1)
        failed_count = 0
        if record:
            failed_count = (
                await db.execute(
                    select(func.count(CertificationVerificationLogModel.id)).where(
                        CertificationVerificationLogModel.record_id == record.id,
                        CertificationVerificationLogModel.verifier_code == "real_name_3_meta",
                        CertificationVerificationLogModel.verify_status == "failed",
                        CertificationVerificationLogModel.verified_at >= since_day,
                    )
                )
            ).scalar() or 0
        user_count = (
            await db.execute(
                select(func.count(CertificationVerificationLogModel.id)).where(
                    CertificationVerificationLogModel.user_id == user.id,
                    CertificationVerificationLogModel.verifier_code == "real_name_3_meta",
                    CertificationVerificationLogModel.verified_at >= since_day,
                )
            )
        ).scalar() or 0
        id_card_count = 0
        if id_card_no:
            id_card_count = (
                await db.execute(
                    select(func.count(CertificationVerificationLogModel.id)).where(
                        CertificationVerificationLogModel.request_snapshot["id_card_no_masked"].as_string() == mask_id_card(id_card_no),
                        CertificationVerificationLogModel.verifier_code == "real_name_3_meta",
                        CertificationVerificationLogModel.verified_at >= since_day,
                    )
                )
            ).scalar() or 0
        cooling = failed_count >= max_failed or user_count >= daily_limit or id_card_count >= daily_limit
        message = "实名认证失败次数过多，请24小时后再试" if failed_count >= max_failed else None
        if user_count >= daily_limit:
            message = "今日实名认证次数过多，请明天再试"
        if id_card_count >= daily_limit:
            message = "该身份证今日核验次数过多"
        return {
            "max_failed_per_application": max_failed,
            "daily_limit": daily_limit,
            "failed_count": failed_count,
            "user_count_today": user_count,
            "id_card_count_today": id_card_count,
            "cooling": cooling,
            "cooldown_hours": 24,
            "message": message,
        }

    @classmethod
    async def _verify_real_name(
        cls,
        db: AsyncSession,
        app: CertificationApplicationModel,
        record: CertificationRecordModel,
        name: str,
        mobile: str,
        id_card_no: str,
    ) -> bool:
        request_snapshot = {"name": name, "mobile": mobile, "id_card_no_masked": mask_id_card(id_card_no)}
        log = CertificationVerificationLogModel(
            brand_id=1,
            application_id=app.id,
            record_id=record.id,
            user_id=app.user_id,
            person_id=app.person_id,
            verifier_code="real_name_3_meta",
            request_snapshot=request_snapshot,
            verify_status="pending",
            verified_at=datetime.now(),
        )
        db.add(log)
        await db.flush()
        try:
            response = await AliyunCertificationClient.mobile_3_meta(name=name, mobile=mobile, id_card_no=id_card_no)
            result_object = response.get("body", {}).get("ResultObject") or response.get("ResultObject") or {}
            sub_code = str(result_object.get("SubCode") or "")
            biz_code = str(result_object.get("BizCode") or "")
            passed = biz_code == "1" or sub_code == "101"
            log.response_snapshot = cls._safe_response(response)
            log.provider_request_id = response.get("headers", {}).get("x-acs-request-id") or response.get("RequestId")
            log.verify_status = "success" if passed else "failed"
            log.error_message = None if passed else "三要素不一致"
            return passed
        except Exception as exc:
            log.verify_status = "failed"
            error_message = str(exc)
            log.error_message = error_message[:1000]
            logger.error(
                "实名认证接口调用失败: application_id={}, record_id={}, user_id={}, person_id={}, error={}",
                app.id,
                record.id,
                app.user_id,
                app.person_id,
                error_message,
            )
            if isinstance(exc, CustomException):
                raise
            raise CustomException(msg="实名认证接口调用失败，请稍后重试") from exc

    @classmethod
    async def detect_face_for_url(
        cls,
        db: AsyncSession,
        *,
        file_url: str,
        business_type: str,
        business_id: int | None = None,
        user_id: int | None = None,
        person_id: int | None = None,
        require_pass: bool = True,
    ) -> dict[str, Any]:
        log = FaceDetectionLogModel(
            brand_id=1,
            user_id=user_id,
            person_id=person_id,
            business_type=business_type,
            business_id=business_id,
            file_url=file_url,
            detected_at=datetime.now(),
        )
        db.add(log)
        await db.flush()
        try:
            response = await AliyunCertificationClient.recognize_face(file_url)
            data = cls._face_data(response)
            face_count = data.get("face_count", 0)
            quality = data.get("quality_score")
            min_quality = int(await cls._param(db, "certification.face.min_quality_score", "60"))
            quality_passed = quality is None or float(quality) >= min_quality
            passed = face_count == 1 and quality_passed
            log.face_count = face_count
            log.quality_score = str(quality) if quality is not None else None
            log.beauty_score = str(data.get("beauty_score")) if data.get("beauty_score") is not None else None
            log.age = str(data.get("age")) if data.get("age") is not None else None
            log.gender = str(data.get("gender")) if data.get("gender") is not None else None
            log.passed = passed
            log.response_snapshot = cls._safe_response(response)
            if not passed:
                log.error_message = cls._face_reject_message(face_count, quality, min_quality)
                if require_pass:
                    raise CustomException(msg=log.error_message)
            return {"passed": passed, **data}
        except CustomException:
            raise
        except Exception as exc:
            log.error_message = str(exc)
            if require_pass:
                raise CustomException(msg="人脸检测失败，请稍后重试") from exc
            return {"passed": False, "error": str(exc)}

    @classmethod
    async def recognize_id_card_for_url(
        cls,
        db: AsyncSession,
        *,
        file_url: str,
        business_type: str,
        business_id: int | None = None,
        operator_id: int | None = None,
        person_id: int | None = None,
    ) -> dict[str, Any]:
        log = IdCardOcrLogModel(
            brand_id=1,
            person_id=person_id,
            operator_id=operator_id,
            business_type=business_type,
            business_id=business_id,
            file_url=file_url,
            recognized_at=datetime.now(),
        )
        db.add(log)
        await db.flush()
        try:
            response = await AliyunCertificationClient.recognize_id_card(file_url)
            log.response_snapshot = cls._safe_response(response)
            data = cls._id_card_data(response)
            id_card_no = (data.get("id_card_no") or "").strip().upper()
            card_side = data.get("card_side") or "unknown"
            log.id_card_side = card_side
            log.id_card_no = id_card_no or None
            log.name = data.get("name")
            log.sex = data.get("sex")
            log.ethnicity = data.get("ethnicity")
            log.birth_date = data.get("birth_date")
            log.address = data.get("address")
            log.issue_authority = data.get("issue_authority")
            log.valid_period = data.get("valid_period")
            log.quality_info = data.get("quality_info")
            if card_side == "back":
                log.ocr_status = "success"
                return cls._id_card_ocr_result(log)
            if not id_card_no:
                log.ocr_status = "failed"
                log.error_message = "未识别到身份证号"
                return cls._id_card_ocr_result(log)
            person = await db.get(CrmPersonModel, person_id) if person_id else None
            if person and not person.is_deleted:
                person.id_card_no = id_card_no
                if not person.birth_date:
                    person.birth_date = cls._parse_id_card_birth_date(data.get("birth_date"), id_card_no)
                if person.gender in (None, "", "2"):
                    person.gender = cls._normalize_id_card_gender(data.get("sex")) or cls._gender_from_id_card_no(id_card_no) or person.gender
            log.ocr_status = "success"
            return cls._id_card_ocr_result(log)
        except Exception as exc:
            log.ocr_status = "failed"
            log.error_message = str(exc)[:1000]
            logger.error(
                "身份证OCR识别失败: person_id={}, business_type={}, business_id={}, error={}",
                person_id,
                business_type,
                business_id,
                exc,
            )
            return cls._id_card_ocr_result(log)

    @classmethod
    def _id_card_data(cls, response: dict[str, Any]) -> dict[str, Any]:
        body = response.get("body") or response.get("Body") or response
        raw_data = body.get("Data") or body.get("data") or {}
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data) if raw_data else {}
        data_root = raw_data.get("data") if isinstance(raw_data, dict) else {}
        face = data_root.get("face") if isinstance(data_root, dict) else {}
        back = data_root.get("back") if isinstance(data_root, dict) else {}
        face_data = face.get("data") if isinstance(face, dict) else {}
        back_data = back.get("data") if isinstance(back, dict) else {}
        if not isinstance(face_data, dict):
            face_data = {}
        if not isinstance(back_data, dict):
            back_data = {}
        issue_authority = back_data.get("issue") or back_data.get("issueAuthority") or back_data.get("issue_authority")
        valid_period = back_data.get("validPeriod") or back_data.get("valid_period")
        id_card_no = face_data.get("idNumber") or face_data.get("id_number")
        card_side = "front" if id_card_no else ("back" if issue_authority or valid_period else "unknown")
        quality_info = {
            "face": face.get("warning") if isinstance(face, dict) else None,
            "back": back.get("warning") if isinstance(back, dict) else None,
        }
        return {
            "card_side": card_side,
            "id_card_no": id_card_no,
            "name": face_data.get("name"),
            "sex": face_data.get("sex"),
            "ethnicity": face_data.get("ethnicity"),
            "birth_date": face_data.get("birthDate") or face_data.get("birth_date"),
            "address": face_data.get("address"),
            "issue_authority": issue_authority,
            "valid_period": valid_period,
            "quality_info": quality_info,
        }

    @staticmethod
    def _id_card_ocr_result(log: IdCardOcrLogModel) -> dict[str, Any]:
        if log.ocr_status == "success" and log.id_card_side == "front":
            message = "身份证人像面已识别，身份证号已写入客户资料"
        elif log.ocr_status == "success" and log.id_card_side == "back":
            message = "身份证国徽面已识别，已保存签发机关和有效期"
        else:
            message = log.error_message or "身份证识别失败"
        return {
            "status": log.ocr_status,
            "card_side": log.id_card_side,
            "id_card_no_masked": mask_id_card(log.id_card_no),
            "name": log.name,
            "sex": log.sex,
            "birth_date": log.birth_date,
            "address": log.address,
            "issue_authority": log.issue_authority,
            "valid_period": log.valid_period,
            "message": message,
        }

    @staticmethod
    def _parse_id_card_birth_date(value: Any, id_card_no: str | None = None) -> date | None:
        raw = str(value or "").strip()
        candidates = []
        if raw:
            candidates.extend([raw, raw.replace("年", "-").replace("月", "-").replace("日", "")])
        if id_card_no and len(id_card_no) >= 14:
            candidates.append(id_card_no[6:14])
        for candidate in candidates:
            text = candidate.strip()
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    return datetime.strptime(text, fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _normalize_id_card_gender(value: Any) -> str | None:
        text = str(value or "").strip().lower()
        if text in {"男", "m", "male", "0"}:
            return "0"
        if text in {"女", "f", "female", "1"}:
            return "1"
        return None

    @staticmethod
    def _gender_from_id_card_no(id_card_no: str | None) -> str | None:
        if not id_card_no or len(id_card_no) < 17 or not id_card_no[16].isdigit():
            return None
        return "0" if int(id_card_no[16]) % 2 == 1 else "1"

    @classmethod
    async def sync_staff_material_to_record(
        cls,
        db: AsyncSession,
        *,
        person_id: int,
        archive_material_id: int,
        archive_item_code: str,
        archive_item_name: str | None,
        material_type: str,
        file_name: str | None,
        file_path: str | None,
        file_url: str,
        operator_id: int | None,
        source_business_type: str,
        source_business_id: int | None,
        ocr_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        item_code = cls._staff_archive_item_code(archive_item_code)
        item = await cls._certification_item(db, item_code)
        if not item:
            return {"status": "skipped", "message": "认证项不存在，资料仅存档"}
        user = await cls._ensure_staff_archive_user(db, person_id)
        if not user:
            return {"status": "skipped", "message": "客户不存在，资料仅存档"}

        record = await cls._target_staff_record(db, user, item)
        if record.record_status == "approved":
            raise CustomException(msg=f"{record.item_name}已通过审核，不能继续上传资料")
        previous_status = record.record_status
        replaced_material_ids: list[int] = []
        if previous_status == "rejected":
            replaced_material_ids = await cls._delete_record_materials(db, record)
        material = await cls._append_staff_material(
            db,
            record=record,
            archive_material_id=archive_material_id,
            archive_item_code=archive_item_code,
            archive_item_name=archive_item_name,
            material_type=material_type,
            file_name=file_name,
            file_path=file_path,
            file_url=file_url,
            operator_id=operator_id,
            source_business_type=source_business_type,
            source_business_id=source_business_id,
            ocr_result=ocr_result,
        )
        if record.record_status != "approved":
            record.record_status = "pending_review"
            record.submitted_at = record.submitted_at or datetime.now()
            record.reject_reason = None
        record.payload = {
            **(record.payload or {}),
            "source": STAFF_UPLOAD_SOURCE,
            "archive_material_id": archive_material_id,
            "archive_item_code": archive_item_code,
            "archive_item_name": archive_item_name,
            "operator_id": operator_id,
            "source_business_type": source_business_type,
            "source_business_id": source_business_id,
            "ocr_result": ocr_result,
        }
        app = await db.get(CertificationApplicationModel, record.application_id, options=[selectinload(CertificationApplicationModel.records)])
        if app and item_code not in (app.item_codes or []):
            app.item_codes = [*(app.item_codes or []), item_code]
        if app:
            await cls._try_complete(db, app)
        await db.flush()
        return {
            "status": record.record_status,
            "message": "资料已提交认证审核" if record.record_status == "pending_review" else "该认证项已通过，资料已追加留档",
            "record_id": record.id,
            "application_id": record.application_id,
            "item_code": record.item_code,
            "item_name": record.item_name,
            "material_id": material.id,
            "previous_status": previous_status,
            "replaced_material_ids": replaced_material_ids,
        }

    @staticmethod
    def _staff_archive_item_code(archive_item_code: str) -> str:
        return STAFF_MATERIAL_ITEM_MAP.get(archive_item_code, archive_item_code)

    @classmethod
    async def _certification_item(cls, db: AsyncSession, item_code: str) -> CertificationItemModel | None:
        return (
            await db.execute(
                select(CertificationItemModel).where(
                    CertificationItemModel.item_code == item_code,
                    CertificationItemModel.is_deleted == False,
                    CertificationItemModel.status == "0",
                )
            )
        ).scalars().first()

    @classmethod
    async def _mini_program_user_by_person(cls, db: AsyncSession, person_id: int) -> MiniProgramUserModel | None:
        return (
            await db.execute(
                select(MiniProgramUserModel)
                .where(MiniProgramUserModel.person_id == person_id, MiniProgramUserModel.is_deleted == False)
                .order_by(MiniProgramUserModel.id.desc())
            )
        ).scalars().first()

    @classmethod
    async def _ensure_staff_archive_user(cls, db: AsyncSession, person_id: int) -> MiniProgramUserModel | None:
        user = await cls._mini_program_user_by_person(db, person_id)
        if user:
            return user
        person = await db.get(CrmPersonModel, person_id)
        if not person or person.is_deleted:
            return None
        user = MiniProgramUserModel(
            brand_id=person.brand_id or 1,
            person_id=person.id,
            nickname=person.name,
            avatar_url=(person.photo_urls or [None])[0],
        )
        db.add(user)
        await db.flush()
        logger.info("为工作人员认证资料创建后台占位小程序用户: person_id={}, user_id={}", person.id, user.id)
        return user

    @classmethod
    async def _target_staff_record(
        cls,
        db: AsyncSession,
        user: MiniProgramUserModel,
        item: CertificationItemModel,
    ) -> CertificationRecordModel:
        approved = await cls._latest_person_record(db, user.person_id or 0, item.item_code, ["approved"])
        if approved:
            return approved
        existing = await cls._latest_person_record(db, user.person_id or 0, item.item_code, ["pending_review", "not_submitted", "rejected"])
        if existing:
            return existing
        app = await cls._staff_application(db, user, item.item_code)
        record = CertificationRecordModel(
            brand_id=1,
            application_id=app.id,
            user_id=user.id,
            person_id=user.person_id or 0,
            item_code=item.item_code,
            item_name=item.item_name,
            verify_mode=item.verify_mode,
            record_status="pending_review",
            submitted_at=datetime.now(),
            payload={"source": STAFF_UPLOAD_SOURCE},
        )
        db.add(record)
        await db.flush()
        return record

    @classmethod
    async def _latest_person_record(
        cls,
        db: AsyncSession,
        person_id: int,
        item_code: str,
        statuses: list[str],
    ) -> CertificationRecordModel | None:
        return (
            await db.execute(
                select(CertificationRecordModel)
                .where(
                    CertificationRecordModel.person_id == person_id,
                    CertificationRecordModel.item_code == item_code,
                    CertificationRecordModel.record_status.in_(statuses),
                    CertificationRecordModel.is_deleted == False,
                )
                .order_by(CertificationRecordModel.id.desc())
            )
        ).scalars().first()

    @classmethod
    async def _staff_application(cls, db: AsyncSession, user: MiniProgramUserModel, item_code: str) -> CertificationApplicationModel:
        app = (
            await db.execute(
                select(CertificationApplicationModel)
                .where(
                    CertificationApplicationModel.user_id == user.id,
                    CertificationApplicationModel.person_id == user.person_id,
                    CertificationApplicationModel.description == STAFF_UPLOAD_SOURCE,
                    CertificationApplicationModel.is_deleted == False,
                )
                .order_by(CertificationApplicationModel.id.desc())
            )
        ).scalars().first()
        if app:
            if item_code not in (app.item_codes or []):
                app.item_codes = [*(app.item_codes or []), item_code]
                await db.flush()
            return app
        package = (
            await db.execute(
                select(CertificationPackageModel)
                .where(CertificationPackageModel.is_deleted == False, CertificationPackageModel.status == "0")
                .order_by(CertificationPackageModel.sort.asc(), CertificationPackageModel.id.asc())
            )
        ).scalars().first()
        if not package:
            raise CustomException(msg="认证套餐配置不存在，无法创建工作人员认证承载记录")
        app = CertificationApplicationModel(
            brand_id=1,
            user_id=user.id,
            person_id=user.person_id or 0,
            package_id=package.id,
            level_code=STAFF_UPLOAD_LEVEL_CODE,
            level_name=STAFF_UPLOAD_LEVEL_NAME,
            item_codes=[item_code],
            application_status="in_progress",
            description=STAFF_UPLOAD_SOURCE,
            paid_at=datetime.now(),
        )
        db.add(app)
        await db.flush()
        return app

    @classmethod
    async def _append_staff_material(
        cls,
        db: AsyncSession,
        *,
        record: CertificationRecordModel,
        archive_material_id: int,
        archive_item_code: str,
        archive_item_name: str | None,
        material_type: str,
        file_name: str | None,
        file_path: str | None,
        file_url: str,
        operator_id: int | None,
        source_business_type: str,
        source_business_id: int | None,
        ocr_result: dict[str, Any] | None,
    ) -> CertificationMaterialModel:
        existing = (
            await db.execute(
                select(CertificationMaterialModel).where(
                    CertificationMaterialModel.record_id == record.id,
                    CertificationMaterialModel.file_url == file_url,
                    CertificationMaterialModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if existing:
            return existing
        material = CertificationMaterialModel(
            brand_id=record.brand_id,
            application_id=record.application_id,
            record_id=record.id,
            user_id=record.user_id,
            person_id=record.person_id,
            item_code=record.item_code,
            material_type=material_type,
            file_name=file_name,
            file_path=file_path,
            file_url=file_url,
            payload={
                "origin": STAFF_UPLOAD_SOURCE,
                "archive_material_id": archive_material_id,
                "archive_item_code": archive_item_code,
                "archive_item_name": archive_item_name,
                "operator_id": operator_id,
                "source_business_type": source_business_type,
                "source_business_id": source_business_id,
                "ocr_result": ocr_result,
            },
        )
        db.add(material)
        await db.flush()
        return material

    @staticmethod
    async def _delete_record_materials(db: AsyncSession, record: CertificationRecordModel) -> list[int]:
        rows = (
            await db.execute(
                select(CertificationMaterialModel).where(
                    CertificationMaterialModel.record_id == record.id,
                    CertificationMaterialModel.is_deleted == False,
                )
            )
        ).scalars().all()
        now = datetime.now()
        material_ids: list[int] = []
        for row in rows:
            row.is_deleted = True
            row.deleted_time = now
            material_ids.append(row.id)
        if material_ids:
            await db.flush()
        return material_ids

    @classmethod
    async def revoke_staff_material_review(cls, db: AsyncSession, archive_material_id: int) -> dict[str, Any] | None:
        material = (
            await db.execute(
                select(CertificationMaterialModel).where(
                    CertificationMaterialModel.payload["archive_material_id"].as_integer() == archive_material_id,
                    CertificationMaterialModel.payload["origin"].as_string() == STAFF_UPLOAD_SOURCE,
                    CertificationMaterialModel.is_deleted == False,
                )
            )
        ).scalars().first()
        if not material:
            return None
        record = await db.get(CertificationRecordModel, material.record_id)
        if not record or record.is_deleted:
            return None
        if record.record_status == "approved":
            raise CustomException(msg="认证项已通过，不能删除认证资料")

        deleted_material_ids = await cls._delete_record_materials(db, record)
        record.record_status = "not_submitted"
        record.submitted_at = None
        record.reviewed_at = None
        record.reviewer_id = None
        record.reject_reason = None
        record.payload = {
            **(record.payload or {}),
            "source": STAFF_UPLOAD_SOURCE,
            "withdrawn_archive_material_id": archive_material_id,
            "withdrawn_at": datetime.now().isoformat(),
        }
        app = await db.get(CertificationApplicationModel, record.application_id, options=[selectinload(CertificationApplicationModel.records)])
        if app and app.application_status in {"approved", "rejected"}:
            app.application_status = "in_progress"
        await db.flush()
        return {"record_id": record.id, "record_status": record.record_status, "deleted_material_ids": deleted_material_ids}

    @staticmethod
    def _face_reject_message(face_count: int, quality: Any, min_quality: int) -> str:
        if face_count <= 0:
            return "照片中未检测到人脸，请上传本人清晰正脸照片"
        if face_count > 1:
            return "照片中检测到多张人脸，请上传只有本人一人的照片"
        if quality is not None and float(quality) < min_quality:
            return "照片人脸不够清晰，请重新上传光线充足、无遮挡的正脸照片"
        return "照片必须包含单人清晰人脸"

    @classmethod
    def _face_data(cls, response: dict[str, Any]) -> dict[str, Any]:
        body = response.get("body") or response
        data = body.get("Data") or body.get("data") or {}
        face_count_raw = data.get("FaceCount")
        qualities = data.get("Qualities") or data.get("QualityList") or data.get("FaceQualityList") or []
        quality_scores = qualities.get("ScoreList") if isinstance(qualities, dict) else qualities
        beauties = data.get("BeautyList") or data.get("BeautyScores") or []
        ages = data.get("AgeList") or []
        genders = data.get("GenderList") or []
        probabilities = data.get("FaceProbabilityList") or []
        pose_list = data.get("PoseList") or []
        face_count = int(face_count_raw if face_count_raw is not None else len(probabilities) or len(quality_scores) or 0)
        return {
            "face_count": face_count,
            "quality_score": quality_scores[0] if isinstance(quality_scores, list) and quality_scores else None,
            "beauty_score": beauties[0] if isinstance(beauties, list) and beauties else None,
            "age": ages[0] if isinstance(ages, list) and ages else None,
            "gender": genders[0] if isinstance(genders, list) and genders else None,
            "face_probability": probabilities[0] if isinstance(probabilities, list) and probabilities else None,
            "pose": pose_list[:3] if isinstance(pose_list, list) else None,
        }

    @classmethod
    async def review_record(cls, db: AsyncSession, record_id: int, reviewer_id: int | None, action: str, reject_reason: str | None) -> dict[str, Any]:
        record = await db.get(CertificationRecordModel, record_id)
        if not record or record.is_deleted:
            raise CustomException(msg="认证记录不存在")
        if record.item_code not in MANUAL_ITEM_CODES and not cls._is_staff_upload_record(record):
            raise CustomException(msg="该认证项不需要人工审核")
        if action == "reject" and not reject_reason:
            raise CustomException(msg="驳回必须填写原因")
        record.record_status = "approved" if action == "approve" else "rejected"
        record.reviewed_at = datetime.now()
        record.reviewer_id = reviewer_id
        record.reject_reason = None if action == "approve" else reject_reason
        app = await db.get(CertificationApplicationModel, record.application_id, options=[selectinload(CertificationApplicationModel.records)])
        if app:
            await cls._try_complete(db, app)
        await db.flush()
        return cls._record_out(record)

    @classmethod
    async def _try_complete(cls, db: AsyncSession, app: CertificationApplicationModel) -> None:
        await db.refresh(app, ["records"])
        if not app.records:
            return
        statuses = {row.item_code: row.record_status for row in app.records}
        if all(statuses.get(code) == "approved" for code in app.item_codes):
            if app.application_status != "approved":
                app.application_status = "approved"
                app.approved_at = datetime.now()
                if not cls._is_staff_upload_application(app):
                    person = await db.get(CrmPersonModel, app.person_id)
                    if person:
                        person.certification_level = app.level_code
                        person.certification_summary = {
                            "level_code": app.level_code,
                            "level_name": app.level_name,
                            "item_status": statuses,
                            "approved_at": app.approved_at.isoformat(),
                        }
                    db.add(
                        SourceEventModel(
                            brand_id=1,
                            person_id=app.person_id,
                            user_id=app.user_id,
                            event_type="certification_approved",
                            source_channel="MINIAPP_REGISTER",
                            source_id=str(app.id),
                            payload={"level_code": app.level_code, "level_name": app.level_name},
                            occurred_at=datetime.now(),
                        )
                    )
            if not cls._is_staff_upload_application(app):
                await cls._grant_reward(db, app)
        elif any(status == "pending_review" for status in statuses.values()):
            app.application_status = "in_progress"

    @staticmethod
    def _is_staff_upload_application(app: CertificationApplicationModel | None) -> bool:
        return bool(app and (app.description == STAFF_UPLOAD_SOURCE or app.level_code == STAFF_UPLOAD_LEVEL_CODE))

    @staticmethod
    def _is_staff_upload_record(record: CertificationRecordModel | None) -> bool:
        payload = record.payload if record else None
        return isinstance(payload, dict) and payload.get("source") == STAFF_UPLOAD_SOURCE

    @classmethod
    async def _grant_reward(cls, db: AsyncSession, app: CertificationApplicationModel) -> None:
        if app.reward_granted_at:
            return
        package = await db.get(CertificationPackageModel, app.package_id)
        if not package or package.reward_coupon_count <= 0:
            app.reward_granted_at = datetime.now()
            return
        now = datetime.now()
        for _ in range(package.reward_coupon_count):
            db.add(
                MpUnlockCouponModel(
                    brand_id=1,
                    user_id=app.user_id,
                    person_id=app.person_id,
                    coupon_name=f"{package.level_name}认证奖励券",
                    coupon_status="unused",
                    valid_from=now,
                    valid_to=now + timedelta(days=package.reward_coupon_valid_days),
                    grant_reason=f"{package.level_name}认证通过奖励",
                    grant_source="certification",
                )
            )
        app.reward_granted_at = now

    @classmethod
    async def page_applications(cls, db: AsyncSession, page_no: int, page_size: int, search: CertificationApplicationQueryParam) -> dict[str, Any]:
        stmt = select(CertificationApplicationModel, MiniProgramUserModel, CrmPersonModel).join(MiniProgramUserModel, CertificationApplicationModel.user_id == MiniProgramUserModel.id).join(CrmPersonModel, CertificationApplicationModel.person_id == CrmPersonModel.id)
        conditions = [CertificationApplicationModel.is_deleted == False]
        if search.status:
            conditions.append(CertificationApplicationModel.application_status == search.status)
        if search.level_code:
            conditions.append(CertificationApplicationModel.level_code == search.level_code)
        if search.keyword:
            keyword = f"%{search.keyword}%"
            conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.primary_mobile.like(keyword), CrmPersonModel.display_no.like(keyword)))
        count_stmt = select(func.count(CertificationApplicationModel.id)).join(MiniProgramUserModel, CertificationApplicationModel.user_id == MiniProgramUserModel.id).join(CrmPersonModel, CertificationApplicationModel.person_id == CrmPersonModel.id).where(and_(*conditions))
        rows = (
            await db.execute(
                stmt.where(and_(*conditions))
                .options(selectinload(CertificationApplicationModel.records))
                .order_by(CertificationApplicationModel.id.desc())
                .offset((page_no - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        total = (await db.execute(count_stmt)).scalar() or 0
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": page_no * page_size < total, "items": [cls._application_admin_out(app, user, person) for app, user, person in rows]}

    @classmethod
    async def page_records(cls, db: AsyncSession, page_no: int, page_size: int, search: CertificationRecordQueryParam) -> dict[str, Any]:
        stmt = select(CertificationRecordModel, MiniProgramUserModel, CrmPersonModel).join(MiniProgramUserModel, CertificationRecordModel.user_id == MiniProgramUserModel.id).join(CrmPersonModel, CertificationRecordModel.person_id == CrmPersonModel.id)
        conditions = [CertificationRecordModel.is_deleted == False]
        if search.status:
            conditions.append(CertificationRecordModel.record_status == search.status)
        if search.item_code:
            conditions.append(CertificationRecordModel.item_code == search.item_code)
        if search.keyword:
            keyword = f"%{search.keyword}%"
            conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.primary_mobile.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(select(func.count(CertificationRecordModel.id)).join(MiniProgramUserModel, CertificationRecordModel.user_id == MiniProgramUserModel.id).join(CrmPersonModel, CertificationRecordModel.person_id == CrmPersonModel.id).where(and_(*conditions)))).scalar() or 0
        rows = (await db.execute(stmt.where(and_(*conditions)).options(selectinload(CertificationRecordModel.materials)).order_by(CertificationRecordModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size))).all()
        operator_ids = {
            int((record.payload or {}).get("operator_id"))
            for record, _, _ in rows
            if isinstance(record.payload, dict) and (record.payload or {}).get("operator_id")
        }
        operator_map: dict[int, UserModel] = {}
        if operator_ids:
            operators = (
                await db.execute(
                    select(UserModel).where(
                        UserModel.id.in_(operator_ids),
                        UserModel.is_deleted == False,
                    )
                )
            ).scalars().all()
            operator_map = {operator.id: operator for operator in operators}
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [cls._record_admin_out(record, user, person, operator_map) for record, user, person in rows],
        }

    @classmethod
    async def admin_application_detail(cls, db: AsyncSession, application_id: int) -> dict[str, Any]:
        row = (
            await db.execute(
                select(CertificationApplicationModel, MiniProgramUserModel, CrmPersonModel, PaymentOrderModel)
                .join(MiniProgramUserModel, CertificationApplicationModel.user_id == MiniProgramUserModel.id)
                .join(CrmPersonModel, CertificationApplicationModel.person_id == CrmPersonModel.id)
                .outerjoin(PaymentOrderModel, CertificationApplicationModel.order_id == PaymentOrderModel.id)
                .where(CertificationApplicationModel.id == application_id, CertificationApplicationModel.is_deleted == False)
                .options(selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials))
            )
        ).first()
        if not row:
            raise CustomException(msg="认证申请不存在")
        app, user, person, order = row
        data = cls._application_admin_out(app, user, person)
        data.update(
            {
                "order": cls._order_out(order) if order else None,
                "id_card_no_masked": mask_id_card(person.id_card_no),
                "reward_granted": bool(app.reward_granted_at),
                "progress": cls._progress_out(app),
            }
        )
        return data

    @classmethod
    async def admin_person_summary(cls, db: AsyncSession, person_id: int) -> dict[str, Any]:
        person = await db.get(CrmPersonModel, person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="用户不存在")
        applications = (
            await db.execute(
                select(CertificationApplicationModel, MiniProgramUserModel, PaymentOrderModel)
                .join(MiniProgramUserModel, CertificationApplicationModel.user_id == MiniProgramUserModel.id)
                .outerjoin(PaymentOrderModel, CertificationApplicationModel.order_id == PaymentOrderModel.id)
                .where(CertificationApplicationModel.person_id == person_id, CertificationApplicationModel.is_deleted == False)
                .options(selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials))
                .order_by(CertificationApplicationModel.id.desc())
            )
        ).all()
        verification_logs = (
            await db.execute(
                select(CertificationVerificationLogModel)
                .where(CertificationVerificationLogModel.person_id == person_id, CertificationVerificationLogModel.is_deleted == False)
                .order_by(CertificationVerificationLogModel.id.desc())
                .limit(10)
            )
        ).scalars().all()
        face_logs = (
            await db.execute(
                select(FaceDetectionLogModel)
                .where(FaceDetectionLogModel.person_id == person_id, FaceDetectionLogModel.is_deleted == False)
                .order_by(FaceDetectionLogModel.id.desc())
                .limit(10)
            )
        ).scalars().all()
        latest_app = applications[0][0] if applications else None
        return {
            "person_id": person.id,
            "display_no": person.display_no,
            "person_name": person.name,
            "mobile": person.primary_mobile,
            "id_card_no_masked": mask_id_card(person.id_card_no),
            **cls.certification_level_out(person),
            "latest_application": cls._application_out(latest_app),
            "applications": [
                cls._person_application_out(app, user, order)
                for app, user, order in applications
            ],
            "verification_logs": [cls._verification_log_out(log, None, person) for log in verification_logs],
            "face_logs": [cls._face_log_out(log, None, person) for log in face_logs],
        }

    @classmethod
    async def mp_application_detail(cls, db: AsyncSession, user_id: int, application_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        app = await db.get(
            CertificationApplicationModel,
            application_id,
            options=[selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials)],
        )
        if not app or app.is_deleted or app.user_id != user.id:
            raise CustomException(msg="认证申请不存在")
        return {"application": cls._application_out(app), "progress": cls._progress_out(app)}

    @classmethod
    async def mp_order_detail(cls, db: AsyncSession, user_id: int, order_id: int) -> dict[str, Any]:
        user = await cls._current_user(db, user_id)
        order = await db.get(PaymentOrderModel, order_id)
        if not order or order.is_deleted or order.biz_type != CERTIFICATION_BIZ_TYPE or order.mp_user_id != user.id:
            raise CustomException(msg="认证订单不存在")
        app = await db.get(CertificationApplicationModel, order.biz_id, options=[selectinload(CertificationApplicationModel.records).selectinload(CertificationRecordModel.materials)])
        if order.pay_status == "paid" and app:
            await cls.on_payment_success(db, order)
        return {"order": cls._order_out(order), "application": cls._application_out(app)}

    @classmethod
    async def page_verification_logs(cls, db: AsyncSession, page_no: int, page_size: int, search: CertificationLogQueryParam) -> dict[str, Any]:
        stmt = select(CertificationVerificationLogModel, MiniProgramUserModel, CrmPersonModel).outerjoin(MiniProgramUserModel, CertificationVerificationLogModel.user_id == MiniProgramUserModel.id).outerjoin(CrmPersonModel, CertificationVerificationLogModel.person_id == CrmPersonModel.id)
        conditions = [CertificationVerificationLogModel.is_deleted == False]
        if search.application_id:
            conditions.append(CertificationVerificationLogModel.application_id == search.application_id)
        if search.record_id:
            conditions.append(CertificationVerificationLogModel.record_id == search.record_id)
        if search.status:
            conditions.append(CertificationVerificationLogModel.verify_status == search.status)
        if search.keyword:
            keyword = f"%{search.keyword}%"
            conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.primary_mobile.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(select(func.count(CertificationVerificationLogModel.id)).outerjoin(MiniProgramUserModel, CertificationVerificationLogModel.user_id == MiniProgramUserModel.id).outerjoin(CrmPersonModel, CertificationVerificationLogModel.person_id == CrmPersonModel.id).where(and_(*conditions)))).scalar() or 0
        rows = (await db.execute(stmt.where(and_(*conditions)).order_by(CertificationVerificationLogModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size))).all()
        return {"page_no": page_no, "page_size": page_size, "total": total, "has_next": page_no * page_size < total, "items": [cls._verification_log_out(log, user, person) for log, user, person in rows]}

    @classmethod
    async def page_face_logs(cls, db: AsyncSession, page_no: int, page_size: int, search: CertificationLogQueryParam) -> dict[str, Any]:
        stmt = select(FaceDetectionLogModel, MiniProgramUserModel, CrmPersonModel).outerjoin(MiniProgramUserModel, FaceDetectionLogModel.user_id == MiniProgramUserModel.id).outerjoin(CrmPersonModel, FaceDetectionLogModel.person_id == CrmPersonModel.id)
        conditions = [FaceDetectionLogModel.is_deleted == False]
        if search.record_id:
            conditions.append(FaceDetectionLogModel.business_id == search.record_id)
        if search.status:
            conditions.append(FaceDetectionLogModel.passed == (search.status == "passed"))
        if search.keyword:
            keyword = f"%{search.keyword}%"
            conditions.append(or_(MiniProgramUserModel.nickname.like(keyword), MiniProgramUserModel.mobile.like(keyword), CrmPersonModel.name.like(keyword), CrmPersonModel.primary_mobile.like(keyword), CrmPersonModel.display_no.like(keyword)))
        total = (await db.execute(select(func.count(FaceDetectionLogModel.id)).outerjoin(MiniProgramUserModel, FaceDetectionLogModel.user_id == MiniProgramUserModel.id).outerjoin(CrmPersonModel, FaceDetectionLogModel.person_id == CrmPersonModel.id).where(and_(*conditions)))).scalar() or 0
        rows = (await db.execute(stmt.where(and_(*conditions)).order_by(FaceDetectionLogModel.id.desc()).offset((page_no - 1) * page_size).limit(page_size))).all()
        fallback_person_map = await cls._face_log_person_map_by_photo_url(
            db,
            [log.file_url for log, _, person in rows if not person and log.file_url],
        )
        return {
            "page_no": page_no,
            "page_size": page_size,
            "total": total,
            "has_next": page_no * page_size < total,
            "items": [
                cls._face_log_out(log, user, person or fallback_person_map.get(log.file_url or ""))
                for log, user, person in rows
            ],
        }

    @staticmethod
    async def _face_log_person_map_by_photo_url(
        db: AsyncSession,
        file_urls: list[str | None],
    ) -> dict[str, CrmPersonModel]:
        urls = [url for url in set(file_urls) if url]
        if not urls:
            return {}
        conditions = [cast(CrmPersonModel.photo_urls, String).like(f"%{url}%") for url in urls]
        rows = (
            await db.execute(
                select(CrmPersonModel).where(
                    CrmPersonModel.is_deleted == False,
                    CrmPersonModel.photo_urls.is_not(None),
                    or_(*conditions),
                )
            )
        ).scalars().all()
        result: dict[str, CrmPersonModel] = {}
        for person in rows:
            for url in person.photo_urls or []:
                if url in urls and url not in result:
                    result[url] = person
        return result

    @classmethod
    async def list_items(cls, db: AsyncSession) -> list[dict[str, Any]]:
        await cls.ensure_defaults(db)
        rows = (await db.execute(select(CertificationItemModel).where(CertificationItemModel.is_deleted == False).order_by(CertificationItemModel.sort.asc(), CertificationItemModel.id.asc()))).scalars().all()
        return [cls._item_out(row) for row in rows]

    @classmethod
    async def save_item(cls, db: AsyncSession, item_code: str, data) -> dict[str, Any]:
        item = (await db.execute(select(CertificationItemModel).where(CertificationItemModel.item_code == item_code, CertificationItemModel.is_deleted == False))).scalars().first()
        if not item:
            raise CustomException(msg="认证项不存在")
        for field, value in data.model_dump().items():
            setattr(item, field, value)
        await db.flush()
        return cls._item_out(item)

    @classmethod
    async def list_packages(cls, db: AsyncSession) -> list[dict[str, Any]]:
        await cls.ensure_defaults(db)
        rows = (await db.execute(select(CertificationPackageModel).where(CertificationPackageModel.is_deleted == False).order_by(CertificationPackageModel.sort.asc(), CertificationPackageModel.id.asc()))).scalars().all()
        return [cls._package_out(row) for row in rows]

    @classmethod
    async def save_package(cls, db: AsyncSession, level_code: str, data) -> dict[str, Any]:
        package = (await db.execute(select(CertificationPackageModel).where(CertificationPackageModel.level_code == level_code, CertificationPackageModel.is_deleted == False))).scalars().first()
        if not package:
            raise CustomException(msg="认证套餐不存在")
        items = await cls._items_map(db)
        unknown = [code for code in data.item_codes if code not in items]
        if unknown:
            raise CustomException(msg=f"认证项不存在：{','.join(unknown)}")
        for field, value in data.model_dump().items():
            setattr(package, field, value)
        await db.flush()
        return cls._package_out(package)

    @classmethod
    async def view_id_card(cls, db: AsyncSession, person_id: int, operator_id: int | None, reason: str | None) -> dict[str, Any]:
        if not reason or not reason.strip():
            raise CustomException(msg="查看完整身份证号必须填写原因")
        person = await db.get(CrmPersonModel, person_id)
        if not person or person.is_deleted:
            raise CustomException(msg="用户不存在")
        db.add(CertificationSensitiveAccessLogModel(brand_id=1, operator_id=operator_id, person_id=person_id, access_type="view_id_card", reason=reason.strip(), accessed_at=datetime.now()))
        await db.flush()
        return {"person_id": person_id, "id_card_no": person.id_card_no, "id_card_no_masked": mask_id_card(person.id_card_no)}

    @staticmethod
    async def _default_store_id(db: AsyncSession) -> int:
        result = await db.execute(select(DeptModel.id).where(DeptModel.is_deleted == False, DeptModel.status == "0", DeptModel.parent_id.is_not(None)).order_by(DeptModel.order.asc(), DeptModel.id.asc()))
        store_id = result.scalar()
        if not store_id:
            raise CustomException(msg="请先创建或启用一个门店用于收款")
        return int(store_id)

    @staticmethod
    def _notify_url(request: Request) -> str:
        try:
            return str(request.url_for("cloudpay_notify_controller"))
        except Exception:
            root_path = request.scope.get("root_path", "")
            return f"{str(request.base_url).rstrip('/')}{root_path}/cloudpay/notify/trade"

    @staticmethod
    def _safe_response(response: dict[str, Any]) -> dict[str, Any]:
        return response if len(str(response)) < 12000 else {"truncated": True, "raw": str(response)[:12000]}

    @staticmethod
    def certification_level_out(person: CrmPersonModel | None) -> dict[str, Any]:
        level = getattr(person, "certification_level", None) or "none"
        summary = getattr(person, "certification_summary", None) if person else None
        return {"certification_level": level, "certification_level_name": LEVEL_LABELS.get(level, "未认证"), "certification_summary": summary}

    @staticmethod
    def _item_out(row: CertificationItemModel) -> dict[str, Any]:
        return {"id": row.id, "item_code": row.item_code, "item_name": row.item_name, "verify_mode": row.verify_mode, "verifier_code": row.verifier_code, "material_required": row.material_required, "material_desc": row.material_desc, "validity_days": row.validity_days, "sort": row.sort, "status": row.status}

    @staticmethod
    def _package_out(row: CertificationPackageModel) -> dict[str, Any]:
        return {"id": row.id, "level_code": row.level_code, "level_name": row.level_name, "price": str(row.price), "item_codes": row.item_codes, "reward_coupon_count": row.reward_coupon_count, "reward_coupon_valid_days": row.reward_coupon_valid_days, "benefit_desc": row.benefit_desc, "sort": row.sort, "status": row.status}

    @classmethod
    def _application_out(cls, row: CertificationApplicationModel | None) -> dict[str, Any] | None:
        if not row:
            return None
        records = row.__dict__.get("records") or []
        source = STAFF_UPLOAD_SOURCE if cls._is_staff_upload_application(row) else "miniprogram"
        data = {"id": row.id, "user_id": row.user_id, "person_id": row.person_id, "package_id": row.package_id, "order_id": row.order_id, "level_code": row.level_code, "level_name": row.level_name, "item_codes": row.item_codes, "application_status": row.application_status, "paid_at": row.paid_at, "approved_at": row.approved_at, "reward_granted_at": row.reward_granted_at, "source": source, "records": [cls._record_out(record) for record in records]}
        data["progress"] = cls._progress_out(row)
        return data

    @classmethod
    def _application_admin_out(cls, app: CertificationApplicationModel, user: MiniProgramUserModel, person: CrmPersonModel) -> dict[str, Any]:
        data = cls._application_out(app) or {}
        data.update(
            {
                "nickname": user.nickname or person.name,
                "mobile": user.mobile or person.primary_mobile,
                "display_no": person.display_no,
                "person_name": person.name,
                "person": cls._admin_person_brief(person),
                "current_level": person.certification_level,
                "current_level_name": LEVEL_LABELS.get(person.certification_level or "none", "未认证"),
            }
        )
        return data

    @classmethod
    def _person_application_out(cls, app: CertificationApplicationModel, user: MiniProgramUserModel, order: PaymentOrderModel | None) -> dict[str, Any]:
        data = cls._application_out(app) or {}
        data.update({"nickname": user.nickname, "mobile": user.mobile, "order": cls._order_out(order) if order else None, "reward_granted": bool(app.reward_granted_at)})
        return data

    @classmethod
    def _record_out(cls, row: CertificationRecordModel) -> dict[str, Any]:
        materials = row.__dict__.get("materials") or []
        return {"id": row.id, "application_id": row.application_id, "user_id": row.user_id, "person_id": row.person_id, "item_code": row.item_code, "item_name": row.item_name, "verify_mode": row.verify_mode, "record_status": row.record_status, "submitted_at": row.submitted_at, "verified_at": row.verified_at, "reviewed_at": row.reviewed_at, "reviewer_id": row.reviewer_id, "reject_reason": row.reject_reason, "expire_at": row.expire_at, "payload": row.payload, "materials": [cls._material_out(item) for item in materials]}

    @classmethod
    def _record_admin_out(cls, record: CertificationRecordModel, user: MiniProgramUserModel, person: CrmPersonModel, operator_map: dict[int, UserModel] | None = None) -> dict[str, Any]:
        data = cls._record_out(record)
        payload = record.payload or {}
        operator_id = payload.get("operator_id")
        operator = operator_map.get(int(operator_id)) if operator_map and operator_id else None
        data.update(
            {
                "nickname": user.nickname or person.name,
                "mobile": user.mobile or person.primary_mobile,
                "display_no": person.display_no,
                "person_name": person.name,
                "person": cls._admin_person_brief(person),
                "id_card_no_masked": mask_id_card(person.id_card_no),
                "source": payload.get("source") or "miniprogram",
                "source_business_type": payload.get("source_business_type"),
                "source_business_id": payload.get("source_business_id"),
                "operator_id": operator_id,
                "operator_name": operator.name if operator else None,
                "operator_username": operator.username if operator else None,
                "operator_mobile": operator.mobile if operator else None,
                "archive_material_id": payload.get("archive_material_id"),
                "archive_item_code": payload.get("archive_item_code"),
                "archive_item_name": payload.get("archive_item_name"),
            }
        )
        return data

    @staticmethod
    def _admin_person_brief(person: CrmPersonModel) -> dict[str, Any]:
        return {
            "id": person.id,
            "display_no": person.display_no,
            "name": person.name,
            "gender": person.gender,
            "primary_mobile": person.primary_mobile,
            "birth_date": person.birth_date,
            "photo_urls": person.photo_urls or [],
            "certification_level": person.certification_level,
            "certification_summary": person.certification_summary,
        }

    @staticmethod
    def _material_out(row: CertificationMaterialModel) -> dict[str, Any]:
        return {"id": row.id, "item_code": row.item_code, "material_type": row.material_type, "file_name": row.file_name, "file_path": row.file_path, "file_url": row.file_url, "payload": row.payload, "created_time": row.created_time}

    @staticmethod
    def _order_out(row: PaymentOrderModel) -> dict[str, Any]:
        return {"id": row.id, "order_no": row.order_no, "biz_type": row.biz_type, "biz_id": row.biz_id, "amount": str(row.amount), "payable_amount": str(row.payable_amount), "order_status": row.order_status, "pay_status": row.pay_status, "expire_at": row.expire_at, "paid_at": row.paid_at}

    @staticmethod
    def _progress_out(row: CertificationApplicationModel) -> dict[str, Any]:
        records = row.__dict__.get("records") or []
        total = len(row.item_codes or [])
        approved = sum(1 for record in records if record.record_status == "approved")
        pending_review = sum(1 for record in records if record.record_status == "pending_review")
        rejected = sum(1 for record in records if record.record_status == "rejected")
        return {"total": total, "approved": approved, "pending_review": pending_review, "rejected": rejected, "percent": int(approved * 100 / total) if total else 0}

    @classmethod
    def _verification_log_out(cls, log: CertificationVerificationLogModel, user: MiniProgramUserModel | None, person: CrmPersonModel | None) -> dict[str, Any]:
        return {
            "id": log.id,
            "application_id": log.application_id,
            "record_id": log.record_id,
            "user_id": log.user_id,
            "person_id": log.person_id,
            "nickname": user.nickname if user else None,
            "mobile": user.mobile if user else None,
            "display_no": person.display_no if person else None,
            "person_name": person.name if person else None,
            "verifier_code": log.verifier_code,
            "request_snapshot": log.request_snapshot,
            "response_snapshot": log.response_snapshot,
            "verify_status": log.verify_status,
            "provider_request_id": log.provider_request_id,
            "error_message": log.error_message,
            "verified_at": log.verified_at,
        }

    @classmethod
    def _face_log_out(cls, log: FaceDetectionLogModel, user: MiniProgramUserModel | None, person: CrmPersonModel | None) -> dict[str, Any]:
        return {
            "id": log.id,
            "user_id": log.user_id,
            "person_id": log.person_id,
            "nickname": user.nickname if user else None,
            "mobile": user.mobile if user else None,
            "display_no": person.display_no if person else None,
            "person_name": person.name if person else None,
            "business_type": log.business_type,
            "business_id": log.business_id,
            "file_url": log.file_url,
            "face_count": log.face_count,
            "quality_score": log.quality_score,
            "beauty_score": log.beauty_score,
            "age": log.age,
            "gender": log.gender,
            "passed": log.passed,
            "response_snapshot": log.response_snapshot,
            "error_message": log.error_message,
            "detected_at": log.detected_at,
        }


class AliyunCertificationClient:
    """阿里云认证核验客户端。"""

    @staticmethod
    async def _ak_config() -> tuple[str, str]:
        config = await StorageConfig.get_aliyun_oss_config()
        if not config.access_key_id or not config.access_key_secret:
            raise CustomException(msg="请先配置阿里云OSS AccessKey，用于认证接口调用")
        return config.access_key_id, config.access_key_secret

    @classmethod
    async def mobile_3_meta(cls, *, name: str, mobile: str, id_card_no: str) -> dict[str, Any]:
        try:
            from alibabacloud_cloudauth20190307.client import Client
            from alibabacloud_cloudauth20190307.models import Mobile3MetaDetailVerifyRequest
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_tea_util.models import RuntimeOptions
        except Exception as exc:
            raise CustomException(msg="缺少阿里云实人认证SDK，请安装 alibabacloud_cloudauth20190307") from exc
        ak, sk = await cls._ak_config()
        client = Client(open_api_models.Config(access_key_id=ak, access_key_secret=sk, endpoint="cloudauth.aliyuncs.com"))
        request = Mobile3MetaDetailVerifyRequest(param_type="normal", identify_num=id_card_no, user_name=name, mobile=mobile)
        response = client.mobile_3meta_detail_verify_with_options(request, RuntimeOptions())
        return response.to_map() if hasattr(response, "to_map") else dict(response)

    @classmethod
    async def recognize_face(cls, image_url: str) -> dict[str, Any]:
        try:
            from alibabacloud_facebody20191230.client import Client
            from alibabacloud_facebody20191230.models import RecognizeFaceRequest
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_tea_util.models import RuntimeOptions
        except Exception as exc:
            raise CustomException(msg="缺少阿里云人脸人体SDK，请安装 alibabacloud_facebody20191230") from exc
        ak, sk = await cls._ak_config()
        client = Client(open_api_models.Config(access_key_id=ak, access_key_secret=sk, endpoint="facebody.cn-shanghai.aliyuncs.com"))
        request = RecognizeFaceRequest(image_url=image_url)
        response = client.recognize_face_with_options(request, RuntimeOptions())
        return response.to_map() if hasattr(response, "to_map") else dict(response)

    @classmethod
    async def recognize_id_card(cls, image_url: str) -> dict[str, Any]:
        try:
            from alibabacloud_ocr_api20210707.client import Client
            from alibabacloud_ocr_api20210707.models import RecognizeIdcardRequest
            from alibabacloud_tea_openapi import models as open_api_models
            from alibabacloud_tea_util.models import RuntimeOptions
        except Exception as exc:
            raise CustomException(msg="缺少阿里云OCR SDK，请安装 alibabacloud_ocr_api20210707") from exc
        ak, sk = await cls._ak_config()
        client = Client(open_api_models.Config(access_key_id=ak, access_key_secret=sk, endpoint="ocr-api.cn-hangzhou.aliyuncs.com"))
        request = RecognizeIdcardRequest(url=image_url, output_quality_info=True)
        response = client.recognize_idcard_with_options(request, RuntimeOptions())
        return response.to_map() if hasattr(response, "to_map") else dict(response)


async def detect_and_upload_photo(db: AsyncSession, base_url: str, file: UploadFile, user_id: int | None = None, person_id: int | None = None, business_type: str = "photo_upload") -> dict[str, Any]:
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise CustomException(msg="只能上传图片文件")
    filename, filepath, file_url = await UploadUtil.upload_file(file=file, base_url=base_url)
    face = await CertificationService.detect_face_for_url(db, file_url=file_url, business_type=business_type, user_id=user_id, person_id=person_id, require_pass=True)
    return UploadResponseSchema(file_path=f"{filepath}", file_name=filename, origin_name=file.filename, file_url=f"{file_url}").model_dump() | {"face_detection": face}
