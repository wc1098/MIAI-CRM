"""create partner preference

Revision ID: 20260515_1400
Revises: 20260515_0900
Create Date: 2026-05-15 14:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_1400"
down_revision = "20260515_0900"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.Column("created_id", sa.Integer(), nullable=True, comment="创建人ID"),
        sa.Column("updated_id", sa.Integer(), nullable=True, comment="更新人ID"),
        sa.Column("deleted_id", sa.Integer(), nullable=True, comment="删除人ID"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    ]


def _index(table: str, columns: list[str]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def upgrade() -> None:
    tables = _tables()
    if "person_partner_preference" not in tables:
        op.create_table(
            "person_partner_preference",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("age_min", sa.Integer(), nullable=True, comment="期望最小年龄"),
            sa.Column("age_max", sa.Integer(), nullable=True, comment="期望最大年龄"),
            sa.Column("height_min_cm", sa.Integer(), nullable=True, comment="期望最小身高cm"),
            sa.Column("height_max_cm", sa.Integer(), nullable=True, comment="期望最大身高cm"),
            sa.Column("weight_min_kg", sa.Integer(), nullable=True, comment="期望最小体重kg"),
            sa.Column("weight_max_kg", sa.Integer(), nullable=True, comment="期望最大体重kg"),
            sa.Column("preferred_residence_region_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望常驻地范围"),
            sa.Column("preferred_hometown_region_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望籍贯范围"),
            sa.Column("preferred_education_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望学历"),
            sa.Column("preferred_marital_status_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望婚况"),
            sa.Column("preferred_annual_income_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望年收入"),
            sa.Column("preferred_house_status_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望房产"),
            sa.Column("preferred_car_status_codes", sa.JSON(), nullable=False, server_default="[]", comment="期望车辆"),
            sa.Column("accept_long_distance", sa.Boolean(), nullable=True, comment="是否接受异地"),
            sa.Column("accept_divorced", sa.Boolean(), nullable=True, comment="是否接受离异"),
            sa.Column("accept_children", sa.Boolean(), nullable=True, comment="是否接受有子女"),
            sa.Column("children_requirement", sa.String(length=255), nullable=True, comment="子女要求说明"),
            sa.Column("preferred_personality_tags", sa.JSON(), nullable=False, server_default="[]", comment="性格偏好"),
            sa.Column("preferred_lifestyle_tags", sa.JSON(), nullable=False, server_default="[]", comment="生活方式偏好"),
            sa.Column("preferred_relationship_tags", sa.JSON(), nullable=False, server_default="[]", comment="关系期待偏好"),
            sa.Column("hard_reject_items", sa.JSON(), nullable=False, server_default="[]", comment="硬性拒绝项"),
            sa.Column("soft_preference_items", sa.JSON(), nullable=False, server_default="[]", comment="软性偏好"),
            sa.Column("preferred_occupation_text", sa.String(length=255), nullable=True, comment="职业偏好文本"),
            sa.Column("preference_text", sa.Text(), nullable=True, comment="择偶要求自由描述"),
            sa.Column("strictness_level", sa.String(length=16), nullable=False, server_default="normal", comment="严格程度"),
            sa.Column("must_match_fields", sa.JSON(), nullable=False, server_default="[]", comment="必须匹配字段"),
            sa.Column("preferred_match_fields", sa.JSON(), nullable=False, server_default="[]", comment="优先匹配字段"),
            sa.Column("profile_summary", sa.Text(), nullable=True, comment="系统摘要"),
            sa.Column("vector_dirty", sa.Boolean(), nullable=False, server_default=sa.true(), comment="向量是否待更新"),
            sa.Column("last_vectorized_at", sa.DateTime(), nullable=True, comment="最近向量化时间"),
            sa.Column("source_type", sa.String(length=32), nullable=False, server_default="admin", comment="来源类型"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源ID"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="20", comment="优先级"),
            sa.Column("is_effective", sa.Boolean(), nullable=False, server_default=sa.true(), comment="是否当前有效"),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否最终版"),
            sa.Column("version_no", sa.Integer(), nullable=False, server_default="1", comment="版本号"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.UniqueConstraint("person_id", name="uq_person_partner_preference_person_id"),
            comment="人员当前有效择偶要求表",
        )
        _index("person_partner_preference", ["brand_id", "person_id", "strictness_level", "vector_dirty", "source_type", "source_id", "priority", "is_effective", "is_final"])

    if "person_partner_preference_version" not in tables:
        op.create_table(
            "person_partner_preference_version",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("preference_id", sa.Integer(), nullable=True, comment="当前择偶要求ID"),
            sa.Column("version_no", sa.Integer(), nullable=False, comment="版本号"),
            sa.Column("source_type", sa.String(length=32), nullable=False, comment="来源类型"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源ID"),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="20", comment="优先级"),
            sa.Column("is_effective", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否成为当前有效"),
            sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否最终版"),
            sa.Column("snapshot", sa.JSON(), nullable=False, comment="择偶要求快照"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.ForeignKeyConstraint(["preference_id"], ["person_partner_preference.id"], ondelete="SET NULL", onupdate="CASCADE"),
            comment="人员择偶要求历史版本表",
        )
        _index("person_partner_preference_version", ["brand_id", "person_id", "preference_id", "version_no", "source_type", "source_id", "priority", "is_effective", "is_final"])


def downgrade() -> None:
    for table in ["person_partner_preference_version", "person_partner_preference"]:
        if table in _tables():
            op.drop_table(table)
