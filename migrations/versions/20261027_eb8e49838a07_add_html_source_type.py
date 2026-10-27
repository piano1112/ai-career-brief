"""add html source type

Revision ID: eb8e49838a07
Revises: bbb8c647b0d3
Create Date: 2026-10-27 23:21:39.558801
"""

from collections.abc import Sequence

from alembic import op


revision: str = 'eb8e49838a07'
down_revision: str | None = 'bbb8c647b0d3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL enum에 값 추가. (autogenerate는 enum 값 변경을 감지하지 못해서 직접 작성)
    op.execute("ALTER TYPE source_type ADD VALUE IF NOT EXISTS 'html'")


def downgrade() -> None:
    # PostgreSQL은 enum 값 삭제를 지원하지 않는다. html 타입 소스를 지우거나 바꾼 뒤
    # 타입을 새로 만들어야 하는데, 데이터 손실 위험이 있어 자동으로 하지 않는다.
    raise NotImplementedError("source_type에서 'html' 값은 자동으로 되돌릴 수 없습니다")
