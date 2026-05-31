"""add performance indexes

Revision ID: 20260529_1000
Revises: 20260528_1020
Create Date: 2026-05-29 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260529_1000"
down_revision: str | None = "20260528_1020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEXES: tuple[tuple[str, str, list[str]], ...] = (
    ("ix_perf_person_ai_task_due", "person_ai_profile_task", ["is_deleted", "status", "retry_count", "next_retry_at", "priority", "id"]),
    ("ix_perf_match_vector_task_due", "person_match_vector_task", ["is_deleted", "status", "retry_count", "next_retry_at", "id"]),
    ("ix_perf_match_vector_task_stale", "person_match_vector_task", ["is_deleted", "status", "locked_at"]),
    ("ix_perf_subscription_rec_due", "subscription_recommendation", ["is_deleted", "recommendation_status", "unlock_at", "last_match_at", "subscription_id"]),
    ("ix_perf_user_subscription_active", "user_subscription", ["is_deleted", "subscription_status", "expired_at", "id"]),
    ("ix_perf_subscription_reason_task_due", "subscription_recommendation_reason_task", ["is_deleted", "status", "retry_count", "next_retry_at", "id"]),
    ("ix_perf_mp_task_record_today", "mp_unlock_task_record", ["viewer_user_id", "completed_on", "task_id", "target_user_id", "is_deleted"]),
    ("ix_perf_mp_contact_unlock_daily", "mp_contact_unlock", ["viewer_user_id", "unlock_status", "unlocked_at", "is_deleted"]),
    ("ix_perf_mp_unlock_coupon_available", "mp_unlock_coupon", ["user_id", "coupon_status", "valid_to", "is_deleted"]),
    ("ix_perf_crm_lead_reclaim", "crm_lead_profile", ["pool_type", "lead_type", "owner_sales_id", "store_id", "assigned_at", "latest_follow_at", "is_deleted"]),
    ("ix_perf_service_case_page", "service_case", ["is_deleted", "store_id", "owner_matchmaker_id", "case_status", "created_time", "id"]),
    ("ix_perf_deep_interview_case_active", "deep_interview", ["service_case_id", "is_deleted", "interview_status"]),
    ("ix_perf_entitlement_usage_case", "entitlement_usage_log", ["service_case_id", "is_deleted"]),
    ("ix_perf_service_entitlement_case", "service_entitlement", ["service_case_id", "is_deleted"]),
    ("ix_perf_backup_pool_page", "backup_pool_item", ["is_deleted", "matchmaker_id", "source_type", "created_time", "id"]),
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _indexes(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if table_name in _tables() and index_name not in _indexes(table_name):
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_exists(index_name: str, table_name: str) -> None:
    if table_name in _tables() and index_name in _indexes(table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    for index_name, table_name, columns in INDEXES:
        _create_index_if_missing(index_name, table_name, columns)


def downgrade() -> None:
    for index_name, table_name, _ in reversed(INDEXES):
        _drop_index_if_exists(index_name, table_name)
