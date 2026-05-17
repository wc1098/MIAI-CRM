"""create match vector

Revision ID: 20260515_1900
Revises: 20260515_1400
Create Date: 2026-05-15 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "20260515_1900"
down_revision = "20260515_1400"
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
        sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注"),
        sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
    ]


def _index(table: str, columns: list[str], unique: bool = False) -> None:
    name = f"ix_{table}_{'_'.join(columns)}"
    op.create_index(op.f(name), table, columns, unique=unique)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    tables = _tables()
    if "person_match_profile" not in tables:
        op.create_table(
            "person_match_profile",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("self_snapshot", sa.JSON(), nullable=True, comment="个人画像脱敏快照"),
            sa.Column("preference_snapshot", sa.JSON(), nullable=True, comment="择偶要求脱敏快照"),
            sa.Column("ai_profile_snapshot", sa.JSON(), nullable=True, comment="AI画像摘要快照"),
            sa.Column("self_input_text", sa.Text(), nullable=True, comment="个人画像向量输入文本"),
            sa.Column("preference_input_text", sa.Text(), nullable=True, comment="择偶要求向量输入文本"),
            sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0", comment="资料完整度"),
            sa.Column("self_vector_dirty", sa.Boolean(), nullable=False, server_default=sa.true(), comment="个人画像向量待更新"),
            sa.Column("preference_vector_dirty", sa.Boolean(), nullable=False, server_default=sa.true(), comment="择偶向量待更新"),
            sa.Column("last_snapshot_at", sa.DateTime(), nullable=True, comment="最近快照时间"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("person_id", name="uq_person_match_profile_person"),
            comment="人员匹配画像快照表",
        )
        for column in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "person_id", "self_vector_dirty", "preference_vector_dirty", "last_snapshot_at"]:
            _index("person_match_profile", [column], unique=(column == "uuid"))

    if "person_match_vector" not in tables:
        op.create_table(
            "person_match_vector",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("vector_type", sa.String(length=32), nullable=False, comment="向量类型"),
            sa.Column("embedding", Vector(768), nullable=True, comment="向量"),
            sa.Column("embedding_model", sa.String(length=128), nullable=True, comment="向量模型"),
            sa.Column("embedding_dimension", sa.Integer(), nullable=False, server_default="768", comment="向量维度"),
            sa.Column("input_text", sa.Text(), nullable=True, comment="向量输入文本"),
            sa.Column("input_snapshot", sa.JSON(), nullable=True, comment="向量输入快照"),
            sa.Column("vector_status", sa.String(length=16), nullable=False, server_default="pending", comment="向量状态"),
            sa.Column("last_vectorized_at", sa.DateTime(), nullable=True, comment="最近向量化时间"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("person_id", "vector_type", name="uq_person_match_vector_person_type"),
            comment="人员匹配向量表",
        )
        for column in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "person_id", "vector_type", "embedding_model", "vector_status", "last_vectorized_at"]:
            _index("person_match_vector", [column], unique=(column == "uuid"))
        op.execute("CREATE INDEX IF NOT EXISTS ix_person_match_vector_embedding ON person_match_vector USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)")

    if "person_match_vector_task" not in tables:
        op.create_table(
            "person_match_vector_task",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, server_default="1", comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=False, comment="人员ID"),
            sa.Column("vector_type", sa.String(length=32), nullable=False, comment="向量类型"),
            sa.Column("source_type", sa.String(length=64), nullable=False, comment="来源类型"),
            sa.Column("source_id", sa.String(length=128), nullable=True, comment="来源对象ID"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0", comment="重试次数"),
            sa.Column("next_retry_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="下次执行时间"),
            sa.Column("locked_at", sa.DateTime(), nullable=True, comment="锁定时间"),
            sa.Column("locked_by", sa.String(length=64), nullable=True, comment="锁定者"),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近错误"),
            sa.Column("payload_snapshot", sa.JSON(), nullable=True, comment="载荷快照"),
            sa.ForeignKeyConstraint(["person_id"], ["crm_person.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            comment="人员匹配向量任务表",
        )
        for column in ["uuid", "status", "created_time", "updated_time", "is_deleted", "deleted_time", "brand_id", "person_id", "vector_type", "source_type", "source_id", "next_retry_at", "locked_at", "locked_by"]:
            _index("person_match_vector_task", [column], unique=(column == "uuid"))


def downgrade() -> None:
    tables = _tables()
    if "person_match_vector_task" in tables:
        op.drop_table("person_match_vector_task")
    if "person_match_vector" in tables:
        op.drop_index("ix_person_match_vector_embedding", table_name="person_match_vector")
        op.drop_table("person_match_vector")
    if "person_match_profile" in tables:
        op.drop_table("person_match_profile")
