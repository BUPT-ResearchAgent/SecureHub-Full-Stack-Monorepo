# Status: real

"""Disable the historical smoke-only job skill binding.

Revision ID: 20260712_1040
Revises: 20260711_1030
Create Date: 2026-07-12 17:30:00

Older ``seed_smoke`` revisions inserted ``AnalyzeJobSkillGap`` for
``job_analyst`` after the frozen catalog migration had already inserted the
canonical ``SkillGapAnalysis`` binding. The extra enabled binding correctly
blocks RuntimeEngine startup. Keep the row for audit/FK safety, but disable it
so only the frozen 28 bindings remain executable.
"""

from collections.abc import Sequence
from uuid import NAMESPACE_URL, UUID, uuid5

import sqlalchemy as sa
from alembic import op


revision: str = "20260712_1040"
down_revision: str | None = "20260711_1030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _agent_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"securehub:agent:{name}")


def upgrade() -> None:
    statement = sa.text(
        "UPDATE agent_skills SET enabled = false "
        "WHERE agent_id = :agent_id AND skill_name = :skill_name AND version = 1"
    ).bindparams(
        sa.bindparam("agent_id", value=_agent_id("job_analyst"), type_=sa.Uuid()),
        sa.bindparam("skill_name", value="AnalyzeJobSkillGap"),
    )
    op.execute(statement)


def downgrade() -> None:
    # Do not re-enable a legacy binding during rollback: it is never executable
    # under the frozen catalog and may have been deliberately disabled already.
    pass
