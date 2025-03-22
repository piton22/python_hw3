"""init_tables

Revision ID: 5c4185ff88ce
Revises: 
Create Date: 2025-03-21 16:11:12.869496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c4185ff88ce'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('descr', sa.String(), nullable=True),
    sa.Column('started_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('finished_at', sa.TIMESTAMP(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('links',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('short', sa.String(), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('last_usage', sa.TIMESTAMP(), nullable=True),
    sa.Column('cnt_usage', sa.Integer(), nullable=True),
    sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('deleted', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_links_id'), 'links', ['id'], unique=False)
    op.create_index(op.f('ix_links_short'), 'links', ['short'], unique=True)
    op.create_table('link_usage',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('link_id', sa.Integer(), nullable=True),
    sa.Column('dt', sa.TIMESTAMP(), nullable=True),
    sa.ForeignKeyConstraint(['link_id'], ['links.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('link_usage')
    op.drop_index(op.f('ix_links_short'), table_name='links')
    op.drop_index(op.f('ix_links_id'), table_name='links')
    op.drop_table('links')
    op.drop_table('projects')
    # ### end Alembic commands ###
