"""Add prestige_orgs table with seed data.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED_ORGS = [
    # tier 1 — global elite
    ("mit", 1),
    ("stanford", 1),
    ("harvard", 1),
    ("caltech", 1),
    ("oxford", 1),
    ("cambridge", 1),
    ("eth zurich", 1),
    ("epfl", 1),
    ("princeton", 1),
    ("carnegie mellon", 1),
    ("cmu", 1),
    ("berkeley", 1),
    ("toronto", 1),
    ("deepmind", 1),
    ("google research", 1),
    ("google brain", 1),
    ("microsoft research", 1),
    ("meta ai", 1),
    ("openai", 1),
    ("anthropic", 1),
    # tier 2 — top research orgs
    ("imperial college", 2),
    ("ucl", 2),
    ("edinburgh", 2),
    ("amsterdam", 2),
    ("max planck", 2),
    ("inria", 2),
    ("tsinghua", 2),
    ("peking university", 2),
    ("columbia university", 2),
    ("yale", 2),
    ("cornell", 2),
    ("university of michigan", 2),
    ("university of washington", 2),
    ("nyu", 2),
    ("uc san diego", 2),
    ("ucsd", 2),
    ("university of illinois", 2),
    ("uiuc", 2),
    ("georgia tech", 2),
    ("apple", 2),
    ("nvidia", 2),
    ("ibm research", 2),
    ("amazon science", 2),
    ("salesforce research", 2),
    ("allen institute", 2),
    ("vector institute", 2),
    ("mila", 2),
    ("facebook ai research", 2),
    ("adobe research", 2),
]


def upgrade() -> None:
    prestige_orgs = op.create_table(
        "prestige_orgs",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
    )
    op.bulk_insert(prestige_orgs, [{"name": name, "tier": tier} for name, tier in _SEED_ORGS])


def downgrade() -> None:
    op.drop_table("prestige_orgs")
