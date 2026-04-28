"""initial_sync

Revision ID: b0b08126b3bc
Revises:
Create Date: 2026-04-27 22:18:40.299756

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b0b08126b3bc'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Drop FK audits → users BEFORE dropping the users table ─────────
    op.drop_constraint('audits_user_id_fkey', 'audits', type_='foreignkey')

    # ── 2. Drop legacy tables ──────────────────────────────────────────────
    op.drop_table('reports')
    op.drop_table('remediation_logs')
    op.drop_table('users')

    # ── 3. Reshape audit_results ───────────────────────────────────────────
    # New columns — add nullable first to avoid rejecting any existing rows
    op.add_column('audit_results', sa.Column('model_name', sa.String(),  nullable=True, server_default=''))
    op.add_column('audit_results', sa.Column('group_rates', sa.JSON(),   nullable=True, server_default='{}'))
    op.add_column('audit_results', sa.Column('di_ratio',   sa.Float(),   nullable=True))
    op.add_column('audit_results', sa.Column('dp_diff',    sa.Float(),   nullable=True))
    op.add_column('audit_results', sa.Column('eq_odds_diff', sa.Float(), nullable=True))
    op.add_column('audit_results', sa.Column('accuracy',   sa.Float(),   nullable=True))
    op.add_column('audit_results', sa.Column('legal_pass', sa.Boolean(), nullable=True, server_default='false'))

    op.create_index('ix_audit_results_audit_id', 'audit_results', ['audit_id'], unique=False)

    # Drop old columns
    for col in ['disparate_impact_ratio', 'created_at', 'predictive_parity_diff',
                'positive_rate', 'protected_attr', 'demographic_parity_diff',
                'sample_size', 'equalized_odds_diff', 'flag_level', 'group_name',
                'p_value', 'theil_index']:
        op.drop_column('audit_results', col)

    # Enforce NOT NULL now that existing rows have the server_default values
    op.alter_column('audit_results', 'model_name', nullable=False, server_default=None)
    op.alter_column('audit_results', 'group_rates', nullable=False, server_default=None)
    op.alter_column('audit_results', 'legal_pass',  nullable=False, server_default=None)

    # ── 4. Reshape audits ──────────────────────────────────────────────────
    # New columns — nullable first
    op.add_column('audits', sa.Column('domain',        sa.String(), nullable=True, server_default='custom'))
    op.add_column('audits', sa.Column('target_col',    sa.String(), nullable=True, server_default=''))
    op.add_column('audits', sa.Column('sensitive_col', sa.String(), nullable=True, server_default=''))
    op.add_column('audits', sa.Column('fairness_config', sa.JSON(), nullable=True, server_default='{}'))
    op.add_column('audits', sa.Column('verified_di_ratio_after_retraining', sa.Float(), nullable=True))

    # user_id: UUID → VARCHAR (cast with ::text)
    op.alter_column(
        'audits', 'user_id',
        existing_type=sa.UUID(),
        type_=sa.String(),
        nullable=False,
        postgresql_using='user_id::text',
    )
    # status: ensure NOT NULL
    op.alter_column('audits', 'status', existing_type=sa.VARCHAR(length=50), nullable=False)

    op.create_index('ix_audits_user_id', 'audits', ['user_id'], unique=False)

    # Drop old columns
    for col in ['schema_json', 'file_path', 'completed_at', 'column_count', 'row_count', 'overall_risk']:
        op.drop_column('audits', col)

    # Enforce NOT NULL on required new columns
    op.alter_column('audits', 'domain',          nullable=False, server_default=None)
    op.alter_column('audits', 'target_col',      nullable=False, server_default=None)
    op.alter_column('audits', 'sensitive_col',   nullable=False, server_default=None)
    op.alter_column('audits', 'fairness_config', nullable=False, server_default=None)

    # saved_models already exists with correct UUID schema — no action needed.


def downgrade() -> None:
    op.drop_index('ix_audits_user_id', table_name='audits')
    op.drop_index('ix_audit_results_audit_id', table_name='audit_results')

    op.drop_column('audits', 'verified_di_ratio_after_retraining')
    op.drop_column('audits', 'fairness_config')
    op.drop_column('audits', 'sensitive_col')
    op.drop_column('audits', 'target_col')
    op.drop_column('audits', 'domain')
    op.alter_column('audits', 'status', existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column('audits', 'user_id', existing_type=sa.String(),
                    type_=sa.UUID(), nullable=True,
                    postgresql_using='user_id::uuid')

    op.drop_column('audit_results', 'legal_pass')
    op.drop_column('audit_results', 'accuracy')
    op.drop_column('audit_results', 'eq_odds_diff')
    op.drop_column('audit_results', 'dp_diff')
    op.drop_column('audit_results', 'di_ratio')
    op.drop_column('audit_results', 'group_rates')
    op.drop_column('audit_results', 'model_name')
