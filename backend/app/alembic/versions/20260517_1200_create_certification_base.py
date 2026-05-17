"""create certification base

Revision ID: 20260517_1200
Revises: 20260517_0900
Create Date: 2026-05-17 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "20260517_1200"
down_revision = "20260517_0900"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
    ]


def _user_columns() -> list[sa.Column]:
    return [
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
    ]


def _idx(table: str, columns: list[str], unique: bool = False) -> None:
    name = op.f(f"ix_{table}_{'_'.join(columns)}")
    op.create_index(name, table, columns, unique=unique)


def _base_indexes(table: str, extra: list[str] | None = None) -> None:
    for col in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", *(extra or [])]:
        _idx(table, [col], unique=(col == "uuid"))


def upgrade() -> None:
    tables = _tables()
    if "crm_person" in tables:
        cols = _columns("crm_person")
        if "id_card_no" not in cols:
            op.add_column("crm_person", sa.Column("id_card_no", sa.String(length=32), nullable=True, comment="身份证号"))
            _idx("crm_person", ["id_card_no"])
        if "certification_level" not in cols:
            op.add_column("crm_person", sa.Column("certification_level", sa.String(length=32), nullable=False, server_default="none", comment="当前认证等级"))
            _idx("crm_person", ["certification_level"])
        if "certification_summary" not in cols:
            op.add_column("crm_person", sa.Column("certification_summary", sa.JSON(), nullable=True, comment="认证摘要"))

    if "certification_item" not in tables:
        op.create_table(
            "certification_item",
            *_base_columns(),
            *_user_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("item_code", sa.String(length=64), nullable=False, comment="认证项编码"),
            sa.Column("item_name", sa.String(length=64), nullable=False, comment="认证项名称"),
            sa.Column("verify_mode", sa.String(length=32), nullable=False, server_default="manual", comment="核验方式"),
            sa.Column("verifier_code", sa.String(length=64), nullable=True, comment="核验器编码"),
            sa.Column("material_required", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否需要材料"),
            sa.Column("material_desc", sa.Text(), nullable=True, comment="材料说明"),
            sa.Column("validity_days", sa.Integer(), nullable=True, comment="有效期天数"),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0", comment="排序"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("item_code", name="uq_certification_item_code"),
            comment="认证项配置表",
        )
        _base_indexes("certification_item", ["brand_id", "item_code", "verify_mode", "verifier_code", "sort"])

    if "certification_package" not in tables:
        op.create_table(
            "certification_package",
            *_base_columns(),
            *_user_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("level_code", sa.String(length=32), nullable=False, comment="认证等级"),
            sa.Column("level_name", sa.String(length=64), nullable=False, comment="等级名称"),
            sa.Column("price", sa.Numeric(10, 2), nullable=False, server_default="0", comment="价格"),
            sa.Column("item_codes", sa.JSON(), nullable=False, comment="包含认证项"),
            sa.Column("reward_coupon_count", sa.Integer(), nullable=False, server_default="0", comment="赠送解锁券数量"),
            sa.Column("reward_coupon_valid_days", sa.Integer(), nullable=False, server_default="7", comment="赠券有效天数"),
            sa.Column("benefit_desc", sa.Text(), nullable=True, comment="权益说明"),
            sa.Column("sort", sa.Integer(), nullable=False, server_default="0", comment="排序"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("level_code", name="uq_certification_package_level"),
            comment="认证套餐配置表",
        )
        _base_indexes("certification_package", ["brand_id", "level_code", "sort"])

    if "certification_application" not in tables:
        op.create_table(
            "certification_application",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("package_id", sa.Integer(), nullable=False, comment="套餐ID"),
            sa.Column("order_id", sa.Integer(), nullable=True, comment="支付订单ID"),
            sa.Column("level_code", sa.String(length=32), nullable=False, comment="申请等级"),
            sa.Column("level_name", sa.String(length=64), nullable=False, comment="申请等级名称"),
            sa.Column("item_codes", sa.JSON(), nullable=False, comment="申请认证项"),
            sa.Column("application_status", sa.String(length=32), nullable=False, server_default="pending_payment", comment="申请状态"),
            sa.Column("paid_at", sa.DateTime(), nullable=True, comment="支付时间"),
            sa.Column("approved_at", sa.DateTime(), nullable=True, comment="通过时间"),
            sa.Column("reward_granted_at", sa.DateTime(), nullable=True, comment="奖励发放时间"),
            sa.ForeignKeyConstraint(["user_id"], ["mini_program_user.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["package_id"], ["certification_package.id"], ondelete="RESTRICT", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["payment_order.id"], ondelete="SET NULL", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="用户认证申请表",
        )
        _base_indexes("certification_application", ["brand_id", "user_id", "person_id", "package_id", "order_id", "level_code", "application_status", "paid_at", "approved_at", "reward_granted_at"])

    if "certification_record" not in tables:
        op.create_table(
            "certification_record",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("application_id", sa.Integer(), nullable=False, comment="申请ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("item_code", sa.String(length=64), nullable=False, comment="认证项编码"),
            sa.Column("item_name", sa.String(length=64), nullable=False, comment="认证项名称"),
            sa.Column("verify_mode", sa.String(length=32), nullable=False, server_default="manual", comment="核验方式"),
            sa.Column("record_status", sa.String(length=32), nullable=False, server_default="not_submitted", comment="单项状态"),
            sa.Column("submitted_at", sa.DateTime(), nullable=True, comment="提交时间"),
            sa.Column("verified_at", sa.DateTime(), nullable=True, comment="核验时间"),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="审核时间"),
            sa.Column("reviewer_id", sa.Integer(), nullable=True, comment="审核人ID"),
            sa.Column("reject_reason", sa.Text(), nullable=True, comment="驳回原因"),
            sa.Column("expire_at", sa.DateTime(), nullable=True, comment="过期时间"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="提交摘要"),
            sa.ForeignKeyConstraint(["application_id"], ["certification_application.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("application_id", "item_code", name="uq_cert_record_application_item"),
            comment="单项认证记录表",
        )
        _base_indexes("certification_record", ["brand_id", "application_id", "user_id", "person_id", "item_code", "verify_mode", "record_status", "submitted_at", "verified_at", "reviewed_at", "reviewer_id", "expire_at"])

    if "certification_material" not in tables:
        op.create_table(
            "certification_material",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("application_id", sa.Integer(), nullable=False, comment="申请ID"),
            sa.Column("record_id", sa.Integer(), nullable=False, comment="单项记录ID"),
            sa.Column("user_id", sa.Integer(), nullable=False, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("item_code", sa.String(length=64), nullable=False, comment="认证项编码"),
            sa.Column("material_type", sa.String(length=32), nullable=False, server_default="file", comment="材料类型"),
            sa.Column("file_name", sa.String(length=255), nullable=True, comment="文件名"),
            sa.Column("file_path", sa.String(length=512), nullable=True, comment="文件路径"),
            sa.Column("file_url", sa.String(length=1000), nullable=True, comment="文件URL"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="材料扩展"),
            sa.ForeignKeyConstraint(["application_id"], ["certification_application.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["record_id"], ["certification_record.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="认证材料表",
        )
        _base_indexes("certification_material", ["brand_id", "application_id", "record_id", "user_id", "person_id", "item_code", "material_type"])

    if "certification_verification_log" not in tables:
        op.create_table(
            "certification_verification_log",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("application_id", sa.Integer(), nullable=True, comment="申请ID"),
            sa.Column("record_id", sa.Integer(), nullable=True, comment="单项记录ID"),
            sa.Column("user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="人员ID"),
            sa.Column("verifier_code", sa.String(length=64), nullable=False, comment="核验器编码"),
            sa.Column("request_snapshot", sa.JSON(), nullable=True, comment="请求摘要"),
            sa.Column("response_snapshot", sa.JSON(), nullable=True, comment="响应摘要"),
            sa.Column("verify_status", sa.String(length=32), nullable=False, server_default="pending", comment="核验状态"),
            sa.Column("provider_request_id", sa.String(length=128), nullable=True, comment="供应商请求ID"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("verified_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="核验时间"),
            sa.PrimaryKeyConstraint("id"),
            comment="认证第三方核验日志表",
        )
        _base_indexes("certification_verification_log", ["brand_id", "application_id", "record_id", "user_id", "person_id", "verifier_code", "verify_status", "provider_request_id", "verified_at"])

    if "face_detection_log" not in tables:
        op.create_table(
            "face_detection_log",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("user_id", sa.Integer(), nullable=True, comment="小程序用户ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="人员ID"),
            sa.Column("business_type", sa.String(length=64), nullable=False, comment="业务类型"),
            sa.Column("business_id", sa.Integer(), nullable=True, comment="业务ID"),
            sa.Column("file_url", sa.String(length=1000), nullable=True, comment="图片URL"),
            sa.Column("face_count", sa.Integer(), nullable=False, server_default="0", comment="人脸数量"),
            sa.Column("quality_score", sa.String(length=64), nullable=True, comment="质量分"),
            sa.Column("beauty_score", sa.String(length=64), nullable=True, comment="颜值分"),
            sa.Column("age", sa.String(length=64), nullable=True, comment="年龄"),
            sa.Column("gender", sa.String(length=64), nullable=True, comment="性别"),
            sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否通过"),
            sa.Column("response_snapshot", sa.JSON(), nullable=True, comment="响应摘要"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("detected_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="检测时间"),
            sa.PrimaryKeyConstraint("id"),
            comment="人脸检测日志表",
        )
        _base_indexes("face_detection_log", ["brand_id", "user_id", "person_id", "business_type", "business_id", "passed", "detected_at"])

    if "certification_sensitive_access_log" not in tables:
        op.create_table(
            "certification_sensitive_access_log",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("operator_id", sa.Integer(), nullable=True, comment="操作人ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("access_type", sa.String(length=64), nullable=False, comment="访问类型"),
            sa.Column("permission_result", sa.String(length=32), nullable=False, server_default="allowed", comment="权限结果"),
            sa.Column("reason", sa.Text(), nullable=True, comment="原因"),
            sa.Column("accessed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="访问时间"),
            sa.PrimaryKeyConstraint("id"),
            comment="认证敏感字段访问日志表",
        )
        _base_indexes("certification_sensitive_access_log", ["brand_id", "operator_id", "person_id", "access_type", "permission_result", "accessed_at"])


def downgrade() -> None:
    for table in [
        "certification_sensitive_access_log",
        "face_detection_log",
        "certification_verification_log",
        "certification_material",
        "certification_record",
        "certification_application",
        "certification_package",
        "certification_item",
    ]:
        if table in _tables():
            op.drop_table(table)
    if "crm_person" in _tables():
        cols = _columns("crm_person")
        for col in ["certification_summary", "certification_level", "id_card_no"]:
            if col in cols:
                op.drop_column("crm_person", col)
