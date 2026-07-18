"""create_events_table

Revision ID: 003_create_events
Revises: 8a6d7558209f
Create Date: 2026-07-18

"""

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_create_events"
down_revision: Union[str, None] = "8a6d7558209f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Buat ENUM type terlebih dahulu
    event_genre_enum = postgresql.ENUM(
        "cultural",
        "sports",
        "convention",
        "concert",
        "festival",
        name="eventgenre",
        create_type=True,
    )
    event_status_enum = postgresql.ENUM(
        "pending_review",
        "approved",
        "rejected",
        name="eventstatus",
        create_type=True,
    )
    event_genre_enum.create(op.get_bind(), checkfirst=True)
    event_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "events",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "genre",
            sa.Enum(
                "cultural",
                "sports",
                "convention",
                "concert",
                "festival",
                name="eventgenre",
                create_constraint=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("venue_name", sa.String(length=150), nullable=True),
        sa.Column("estimated_attendee_count", sa.Integer(), nullable=False),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending_review",
                "approved",
                "rejected",
                name="eventstatus",
                create_constraint=False,
            ),
            server_default="pending_review",
            nullable=False,
        ),
        sa.Column("reviewed_by_admin_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Index GIST untuk spatial query
    op.create_index(
        "idx_events_location",
        "events",
        ["location"],
        postgresql_using="gist",
    )
    # Index untuk filter by status (sering dipakai)
    op.create_index(
        "idx_events_status",
        "events",
        ["status"],
    )
    # Index untuk filter upcoming events
    op.create_index(
        "idx_events_end_datetime",
        "events",
        ["end_datetime"],
    )


def downgrade() -> None:
    op.drop_index("idx_events_end_datetime", table_name="events")
    op.drop_index("idx_events_status", table_name="events")
    op.drop_index("idx_events_location", table_name="events", postgresql_using="gist")
    op.drop_table("events")

    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS eventgenre")
