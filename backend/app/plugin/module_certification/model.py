from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin, UserMixin


class CertificationItemModel(ModelMixin, UserMixin):
    """认证项配置。"""

    __tablename__ = "certification_item"
    __table_args__ = (
        UniqueConstraint("item_code", name="uq_certification_item_code"),
        {"comment": "认证项配置表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="认证项编码")
    item_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="认证项名称")
    verify_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", index=True, comment="核验方式")
    verifier_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="核验器编码")
    material_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否需要材料")
    material_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="材料说明")
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="有效期天数")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class CertificationPackageModel(ModelMixin, UserMixin):
    """认证等级套餐配置。"""

    __tablename__ = "certification_package"
    __table_args__ = (
        UniqueConstraint("level_code", name="uq_certification_package_level"),
        {"comment": "认证套餐配置表"},
    )

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    level_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="认证等级")
    level_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="等级名称")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0, comment="价格")
    item_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="包含认证项")
    reward_coupon_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="赠送解锁券数量")
    reward_coupon_valid_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7, comment="赠券有效天数")
    benefit_desc: Mapped[str | None] = mapped_column(Text, nullable=True, comment="权益说明")
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True, comment="排序")


class CertificationApplicationModel(ModelMixin):
    """用户认证申请。"""

    __tablename__ = "certification_application"
    __table_args__: dict[str, str] = {"comment": "用户认证申请表"}
    __loader_options__ = ["records", "package"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("mini_program_user.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="小程序用户ID")
    person_id: Mapped[int] = mapped_column(Integer, ForeignKey("crm_person.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="人员ID")
    package_id: Mapped[int] = mapped_column(Integer, ForeignKey("certification_package.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True, comment="套餐ID")
    order_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payment_order.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True, comment="支付订单ID")
    level_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="申请等级")
    level_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="申请等级名称")
    item_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False, comment="申请认证项")
    application_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_payment", index=True, comment="申请状态")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="支付时间")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="通过时间")
    reward_granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="奖励发放时间")

    package: Mapped[CertificationPackageModel] = relationship("CertificationPackageModel", lazy="selectin")
    records: Mapped[list["CertificationRecordModel"]] = relationship("CertificationRecordModel", lazy="selectin")


class CertificationRecordModel(ModelMixin):
    """单项认证记录。"""

    __tablename__ = "certification_record"
    __table_args__ = (
        UniqueConstraint("application_id", "item_code", name="uq_cert_record_application_item"),
        {"comment": "单项认证记录表"},
    )
    __loader_options__ = ["materials"]

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("certification_application.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="申请ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="小程序用户ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="认证项编码")
    item_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="认证项名称")
    verify_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", index=True, comment="核验方式")
    record_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_submitted", index=True, comment="单项状态")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="提交时间")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="核验时间")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="审核时间")
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="审核人ID")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="驳回原因")
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True, comment="过期时间")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="提交摘要")

    materials: Mapped[list["CertificationMaterialModel"]] = relationship("CertificationMaterialModel", lazy="selectin")


class CertificationMaterialModel(ModelMixin):
    """认证材料。"""

    __tablename__ = "certification_material"
    __table_args__: dict[str, str] = {"comment": "认证材料表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    application_id: Mapped[int] = mapped_column(Integer, ForeignKey("certification_application.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="申请ID")
    record_id: Mapped[int] = mapped_column(Integer, ForeignKey("certification_record.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True, comment="单项记录ID")
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="小程序用户ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="认证项编码")
    material_type: Mapped[str] = mapped_column(String(32), nullable=False, default="file", index=True, comment="材料类型")
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="文件名")
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="文件路径")
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="文件URL")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="材料扩展")


class CertificationVerificationLogModel(ModelMixin):
    """第三方核验日志。"""

    __tablename__ = "certification_verification_log"
    __table_args__: dict[str, str] = {"comment": "认证第三方核验日志表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    application_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="申请ID")
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="单项记录ID")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="小程序用户ID")
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="人员ID")
    verifier_code: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="核验器编码")
    request_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="请求摘要")
    response_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="响应摘要")
    verify_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="核验状态")
    provider_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="供应商请求ID")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    verified_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="核验时间")


class FaceDetectionLogModel(ModelMixin):
    """人脸检测日志。"""

    __tablename__ = "face_detection_log"
    __table_args__: dict[str, str] = {"comment": "人脸检测日志表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="小程序用户ID")
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="人员ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务类型")
    business_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="业务ID")
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="图片URL")
    face_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="人脸数量")
    quality_score: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="质量分")
    beauty_score: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="颜值分")
    age: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="年龄")
    gender: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="性别")
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否通过")
    response_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="响应摘要")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="检测时间")


class IdCardOcrLogModel(ModelMixin):
    """身份证OCR识别日志。"""

    __tablename__ = "id_card_ocr_log"
    __table_args__: dict[str, str] = {"comment": "身份证OCR识别日志表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    person_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="人员ID")
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="操作人ID")
    business_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务类型")
    business_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="业务ID")
    file_url: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="图片URL")
    id_card_side: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True, comment="身份证面")
    ocr_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True, comment="识别状态")
    id_card_no: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True, comment="身份证号")
    name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="姓名")
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True, comment="性别")
    ethnicity: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="民族")
    birth_date: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="出生日期")
    address: Mapped[str | None] = mapped_column(Text, nullable=True, comment="住址")
    issue_authority: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="签发机关")
    valid_period: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="有效期限")
    quality_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="质量检测结果")
    response_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="原始响应")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    recognized_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="识别时间")


class CertificationSensitiveAccessLogModel(ModelMixin):
    """认证敏感字段访问日志。"""

    __tablename__ = "certification_sensitive_access_log"
    __table_args__: dict[str, str] = {"comment": "认证敏感字段访问日志表"}

    brand_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True, comment="品牌ID")
    operator_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True, comment="操作人ID")
    person_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="人员ID")
    access_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="访问类型")
    permission_result: Mapped[str] = mapped_column(String(32), nullable=False, default="allowed", index=True, comment="权限结果")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原因")
    accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, index=True, comment="访问时间")
