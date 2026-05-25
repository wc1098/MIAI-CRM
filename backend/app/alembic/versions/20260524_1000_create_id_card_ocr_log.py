"""create id card ocr log

Revision ID: 20260524_1000
Revises: 20260523_1020
Create Date: 2026-05-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260524_1000"
down_revision: str | None = "20260523_1020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "id_card_ocr_log"
    if table_name not in inspector.get_table_names():
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
            sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
            sa.Column("status", sa.String(length=10), nullable=False, server_default="0", comment="状态"),
            sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
            sa.Column("created_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="更新时间"),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已删除"),
            sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("person_id", sa.Integer(), nullable=True, comment="人员ID"),
            sa.Column("operator_id", sa.Integer(), nullable=True, comment="操作人ID"),
            sa.Column("business_type", sa.String(length=64), nullable=False, comment="业务类型"),
            sa.Column("business_id", sa.Integer(), nullable=True, comment="业务ID"),
            sa.Column("file_url", sa.String(length=1000), nullable=True, comment="图片URL"),
            sa.Column("ocr_status", sa.String(length=32), nullable=False, comment="识别状态"),
            sa.Column("id_card_no", sa.String(length=32), nullable=True, comment="身份证号"),
            sa.Column("name", sa.String(length=64), nullable=True, comment="姓名"),
            sa.Column("sex", sa.String(length=16), nullable=True, comment="性别"),
            sa.Column("ethnicity", sa.String(length=32), nullable=True, comment="民族"),
            sa.Column("birth_date", sa.String(length=64), nullable=True, comment="出生日期"),
            sa.Column("address", sa.Text(), nullable=True, comment="住址"),
            sa.Column("issue_authority", sa.String(length=255), nullable=True, comment="签发机关"),
            sa.Column("valid_period", sa.String(length=128), nullable=True, comment="有效期限"),
            sa.Column("quality_info", sa.JSON(), nullable=True, comment="质量检测结果"),
            sa.Column("response_snapshot", sa.JSON(), nullable=True, comment="原始响应"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
            sa.Column("recognized_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="识别时间"),
            sa.PrimaryKeyConstraint("id"),
            comment="身份证OCR识别日志表",
        )
        existing_indexes: set[str] = set()
    else:
        existing_indexes = {row["name"] for row in inspector.get_indexes(table_name)}

    def create_index(name: str, columns: list[str], unique: bool = False) -> None:
        if name not in existing_indexes:
            op.create_index(name, table_name, columns, unique=unique)
            existing_indexes.add(name)

    create_index("ix_id_card_ocr_log_uuid", ["uuid"], unique=True)
    create_index("ix_id_card_ocr_log_status", ["status"])
    create_index("ix_id_card_ocr_log_created_time", ["created_time"])
    create_index("ix_id_card_ocr_log_updated_time", ["updated_time"])
    create_index("ix_id_card_ocr_log_deleted_time", ["deleted_time"])
    create_index("ix_id_card_ocr_log_brand_id", ["brand_id"])
    create_index("ix_id_card_ocr_log_person_id", ["person_id"])
    create_index("ix_id_card_ocr_log_operator_id", ["operator_id"])
    create_index("ix_id_card_ocr_log_business_type", ["business_type"])
    create_index("ix_id_card_ocr_log_business_id", ["business_id"])
    create_index("ix_id_card_ocr_log_ocr_status", ["ocr_status"])
    create_index("ix_id_card_ocr_log_id_card_no", ["id_card_no"])
    create_index("ix_id_card_ocr_log_recognized_at", ["recognized_at"])
    create_index("ix_id_card_ocr_log_is_deleted", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_id_card_ocr_log_deleted_time", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_updated_time", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_created_time", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_status", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_uuid", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_is_deleted", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_recognized_at", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_id_card_no", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_ocr_status", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_business_id", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_business_type", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_operator_id", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_person_id", table_name="id_card_ocr_log")
    op.drop_index("ix_id_card_ocr_log_brand_id", table_name="id_card_ocr_log")
    op.drop_table("id_card_ocr_log")
