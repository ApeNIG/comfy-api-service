"""Initial migration: users, subscriptions, jobs tables

Revision ID: 202511102256_initial
Revises:
Create Date: 2025-11-10T22:56:14.526440

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '202511102256_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=False),
    sa.Column('role', sa.String(length=50), nullable=False),
    sa.Column('google_id', sa.String(length=255), nullable=True),
    sa.Column('google_access_token', sa.String(length=500), nullable=True),
    sa.Column('google_refresh_token', sa.String(length=500), nullable=True),
    sa.Column('google_token_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('drive_folder_id', sa.String(length=255), nullable=True),
    sa.Column('drive_output_folder_id', sa.String(length=255), nullable=True),
    sa.Column('drive_webhook_id', sa.String(length=255), nullable=True),
    sa.Column('drive_webhook_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('avatar_url', sa.String(length=500), nullable=True),
    sa.Column('total_jobs_run', sa.Integer(), nullable=False),
    sa.Column('total_credits_used', sa.Integer(), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)

    # Create subscriptions table
    op.create_table('subscriptions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('tier', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancel_at_period_end', sa.String(length=50), nullable=False),
    sa.Column('stripe_customer_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_subscription_id', sa.String(length=255), nullable=True),
    sa.Column('stripe_price_id', sa.String(length=255), nullable=True),
    sa.Column('monthly_job_limit', sa.Integer(), nullable=False),
    sa.Column('monthly_credit_limit', sa.Integer(), nullable=False),
    sa.Column('jobs_used_this_period', sa.Integer(), nullable=False),
    sa.Column('credits_used_this_period', sa.Integer(), nullable=False),
    sa.Column('price_amount', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('price_currency', sa.String(length=3), nullable=False),
    sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_stripe_subscription_id'), 'subscriptions', ['stripe_subscription_id'], unique=True)
    op.create_index(op.f('ix_subscriptions_tier'), 'subscriptions', ['tier'], unique=False)
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)

    # Create jobs table
    op.create_table('jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('input_file_id', sa.String(length=255), nullable=False),
    sa.Column('input_file_name', sa.String(length=500), nullable=False),
    sa.Column('input_file_url', sa.String(length=1000), nullable=True),
    sa.Column('input_file_size', sa.Integer(), nullable=True),
    sa.Column('preset_name', sa.String(length=100), nullable=False),
    sa.Column('workflow_id', sa.String(length=100), nullable=False),
    sa.Column('workflow_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('output_file_id', sa.String(length=255), nullable=True),
    sa.Column('output_file_name', sa.String(length=500), nullable=True),
    sa.Column('output_file_url', sa.String(length=1000), nullable=True),
    sa.Column('output_file_size', sa.Integer(), nullable=True),
    sa.Column('comfyui_prompt_id', sa.String(length=255), nullable=True),
    sa.Column('comfyui_node_errors', postgresql.JSON(astext_type=sa.Text()), nullable=True),
    sa.Column('comfyui_execution_time', sa.Integer(), nullable=True),
    sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('error_type', sa.String(length=100), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('max_retries', sa.Integer(), nullable=False),
    sa.Column('credits_consumed', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_comfyui_prompt_id'), 'jobs', ['comfyui_prompt_id'], unique=False)
    op.create_index(op.f('ix_jobs_input_file_id'), 'jobs', ['input_file_id'], unique=False)
    op.create_index(op.f('ix_jobs_output_file_id'), 'jobs', ['output_file_id'], unique=False)
    op.create_index(op.f('ix_jobs_preset_name'), 'jobs', ['preset_name'], unique=False)
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_user_id'), 'jobs', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop jobs table
    op.drop_index(op.f('ix_jobs_user_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_preset_name'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_output_file_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_input_file_id'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_comfyui_prompt_id'), table_name='jobs')
    op.drop_table('jobs')

    # Drop subscriptions table
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_tier'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_subscription_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_table('subscriptions')

    # Drop users table
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
