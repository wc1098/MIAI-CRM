"""extend mp unlock flow

Revision ID: 20260515_0900
Revises: 20260514_1300
Create Date: 2026-05-15 09:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "20260515_0900"
down_revision = "20260514_1300"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def _columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table)}


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("uuid", sa.String(length=64), nullable=False, comment="UUID全局唯一标识"),
        sa.Column("status", sa.String(length=10), nullable=False, comment="状态(0:正常 1:禁用)"),
        sa.Column("description", sa.Text(), nullable=True, comment="备注/描述"),
        sa.Column("created_time", sa.DateTime(), nullable=False, comment="创建时间"),
        sa.Column("updated_time", sa.DateTime(), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, comment="是否已删除"),
        sa.Column("deleted_time", sa.DateTime(), nullable=True, comment="删除时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    ]


def _index(table: str, columns: list[str]) -> None:
    for column in columns:
        op.create_index(op.f(f"ix_{table}_{column}"), table, [column], unique=False)


def _add_column(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)
        op.create_index(op.f(f"ix_{table}_{column.name}"), table, [column.name], unique=False)


def upgrade() -> None:
    tables = _tables()

    if "mp_heartbeat_progress" in tables:
        _add_column("mp_heartbeat_progress", sa.Column("target_score", sa.Integer(), nullable=False, server_default="100", comment="目标心动值"))
        _add_column("mp_heartbeat_progress", sa.Column("progress_status", sa.String(length=32), nullable=False, server_default="processing", comment="进度状态"))
        _add_column("mp_heartbeat_progress", sa.Column("free_unlock_eligible", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否可任务免费解锁"))
        _add_column("mp_heartbeat_progress", sa.Column("paid_boost_used", sa.Boolean(), nullable=False, server_default=sa.false(), comment="是否已付费补足"))

    if "mp_contact_unlock" in tables:
        _add_column("mp_contact_unlock", sa.Column("unlock_source", sa.String(length=32), nullable=False, server_default="paid_boost", comment="解锁来源"))
        _add_column("mp_contact_unlock", sa.Column("revoked_at", sa.DateTime(), nullable=True, comment="撤销时间"))
        _add_column("mp_contact_unlock", sa.Column("revoked_by", sa.Integer(), nullable=True, comment="撤销人"))
        _add_column("mp_contact_unlock", sa.Column("revoke_reason", sa.Text(), nullable=True, comment="撤销/屏蔽原因"))

    if "mp_unlock_coupon" in tables:
        _add_column("mp_unlock_coupon", sa.Column("grant_source", sa.String(length=32), nullable=False, server_default="admin", comment="发放来源"))

    if "mp_unlock_task" not in tables:
        op.create_table(
            "mp_unlock_task",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("task_code", sa.String(length=64), nullable=False, comment="任务编码"),
            sa.Column("task_name", sa.String(length=100), nullable=False, comment="任务名称"),
            sa.Column("task_type", sa.String(length=32), nullable=False, comment="任务类型"),
            sa.Column("task_group", sa.String(length=32), nullable=False, comment="任务分组"),
            sa.Column("score", sa.Integer(), nullable=False, comment="加分值"),
            sa.Column("is_global", sa.Boolean(), nullable=False, comment="是否全局任务"),
            sa.Column("is_target", sa.Boolean(), nullable=False, comment="是否目标任务"),
            sa.Column("daily_limit", sa.Integer(), nullable=False, comment="每日次数限制"),
            sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
            sa.UniqueConstraint("task_code", name="uq_mp_unlock_task_code"),
            comment="小程序解锁任务配置表",
        )
        _index("mp_unlock_task", ["brand_id", "task_code", "task_type", "task_group", "sort"])

    if "mp_unlock_task_record" not in tables:
        op.create_table(
            "mp_unlock_task_record",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("task_id", sa.Integer(), nullable=False, comment="任务ID"),
            sa.Column("task_code", sa.String(length=64), nullable=False, comment="任务编码"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="发起用户ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=True, comment="目标用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=True, comment="发起人员ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=True, comment="目标人员ID"),
            sa.Column("score", sa.Integer(), nullable=False, comment="实际加分"),
            sa.Column("source", sa.String(length=32), nullable=False, comment="完成来源"),
            sa.Column("completed_on", sa.String(length=10), nullable=False, comment="完成日期"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="扩展参数"),
            sa.Column("completed_at", sa.DateTime(), nullable=False, comment="完成时间"),
            sa.ForeignKeyConstraint(["task_id"], ["mp_unlock_task.id"], ondelete="CASCADE", onupdate="CASCADE"),
            comment="小程序解锁任务完成记录表",
        )
        _index("mp_unlock_task_record", ["brand_id", "task_id", "task_code", "viewer_user_id", "target_user_id", "completed_on", "completed_at"])

    if "mp_unlock_question" not in tables:
        op.create_table(
            "mp_unlock_question",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("question", sa.String(length=255), nullable=False, comment="题目"),
            sa.Column("options", sa.JSON(), nullable=False, comment="选项"),
            sa.Column("recommended_answer", sa.String(length=64), nullable=True, comment="推荐答案"),
            sa.Column("match_tags", sa.JSON(), nullable=True, comment="匹配标签"),
            sa.Column("correct_score", sa.Integer(), nullable=False, comment="答对加分"),
            sa.Column("wrong_score", sa.Integer(), nullable=False, comment="答错加分"),
            sa.Column("category", sa.String(length=32), nullable=False, comment="题目分类"),
            sa.Column("sort", sa.Integer(), nullable=False, comment="排序"),
            comment="小程序默契题配置表",
        )
        _index("mp_unlock_question", ["brand_id", "category", "sort"])

    if "mp_unlock_question_answer" not in tables:
        op.create_table(
            "mp_unlock_question_answer",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("question_id", sa.Integer(), nullable=False, comment="题目ID"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="答题用户ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=True, comment="答题人员ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=True, comment="目标人员ID"),
            sa.Column("answer_value", sa.String(length=64), nullable=False, comment="作答值"),
            sa.Column("is_correct", sa.Boolean(), nullable=False, comment="是否匹配推荐答案"),
            sa.Column("score", sa.Integer(), nullable=False, comment="得分"),
            sa.Column("answered_at", sa.DateTime(), nullable=False, comment="答题时间"),
            sa.ForeignKeyConstraint(["question_id"], ["mp_unlock_question.id"], ondelete="CASCADE", onupdate="CASCADE"),
            sa.UniqueConstraint("viewer_user_id", "target_user_id", "question_id", name="uq_mp_unlock_answer_once"),
            comment="小程序默契题作答记录表",
        )
        _index("mp_unlock_question_answer", ["brand_id", "question_id", "viewer_user_id", "target_user_id", "answered_at"])

    if "mp_contact_view_log" not in tables:
        op.create_table(
            "mp_contact_view_log",
            *_base_columns(),
            sa.Column("brand_id", sa.Integer(), nullable=False, comment="品牌ID"),
            sa.Column("unlock_id", sa.Integer(), nullable=False, comment="解锁记录ID"),
            sa.Column("viewer_user_id", sa.Integer(), nullable=False, comment="查看用户ID"),
            sa.Column("target_user_id", sa.Integer(), nullable=False, comment="目标用户ID"),
            sa.Column("viewer_person_id", sa.Integer(), nullable=True, comment="查看人员ID"),
            sa.Column("target_person_id", sa.Integer(), nullable=True, comment="目标人员ID"),
            sa.Column("viewed_at", sa.DateTime(), nullable=False, comment="查看时间"),
            sa.Column("payload", sa.JSON(), nullable=True, comment="扩展参数"),
            sa.ForeignKeyConstraint(["unlock_id"], ["mp_contact_unlock.id"], ondelete="CASCADE", onupdate="CASCADE"),
            comment="小程序联系方式查看日志表",
        )
        _index("mp_contact_view_log", ["brand_id", "unlock_id", "viewer_user_id", "target_user_id", "viewed_at"])


def downgrade() -> None:
    for table in [
        "mp_contact_view_log",
        "mp_unlock_question_answer",
        "mp_unlock_question",
        "mp_unlock_task_record",
        "mp_unlock_task",
    ]:
        if table in _tables():
            op.drop_table(table)
