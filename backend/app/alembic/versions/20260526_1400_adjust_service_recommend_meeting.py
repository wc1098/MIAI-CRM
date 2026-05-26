"""adjust service recommendation and meeting

Revision ID: 20260526_1400
Revises: 20260525_1010
Create Date: 2026-05-26 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260526_1400"
down_revision: str | None = "20260525_1010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _unique_constraints(table_name: str) -> set[str]:
    return {row["name"] for row in sa.inspect(op.get_bind()).get_unique_constraints(table_name)}


def upgrade() -> None:
    constraints = _unique_constraints("service_recommendation")
    if "uq_service_recommendation_plan_item" in constraints:
        op.drop_constraint("uq_service_recommendation_plan_item", "service_recommendation", type_="unique")

    columns = _columns("service_meeting")
    if "matchmaker_opinion" not in columns:
        op.add_column("service_meeting", sa.Column("matchmaker_opinion", sa.Text(), nullable=True, comment="红娘意见"))


def downgrade() -> None:
    columns = _columns("service_meeting")
    if "matchmaker_opinion" in columns:
        op.drop_column("service_meeting", "matchmaker_opinion")

    constraints = _unique_constraints("service_recommendation")
    if "uq_service_recommendation_plan_item" not in constraints:
        op.create_unique_constraint("uq_service_recommendation_plan_item", "service_recommendation", ["plan_item_id"])
