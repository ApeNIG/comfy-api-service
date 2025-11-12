"""Create Creator platform tables

Revision ID: 001_creator_tables
Revises:
Create Date: 2025-11-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_creator_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Authentication
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=False),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('reset_token', sa.String(255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),

        # Profile
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),

        # Role
        sa.Column('role', sa.Enum('USER', 'ADMIN', name='userrole'), default='USER', nullable=False),

        # Subscription
        sa.Column('subscription_tier', sa.Enum('FREE', 'CREATOR', 'STUDIO', name='subscriptiontier'), default='FREE', nullable=False),
        sa.Column('subscription_status', sa.Enum('ACTIVE', 'CANCELLED', 'PAST_DUE', 'TRIALING', 'INCOMPLETE', name='subscriptionstatus'), default='ACTIVE', nullable=False),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True, unique=True),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True, unique=True),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),

        # Usage
        sa.Column('monthly_generation_count', sa.Integer(), default=0, nullable=False),
        sa.Column('monthly_generation_reset_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_generations', sa.Integer(), default=0, nullable=False),

        # API
        sa.Column('api_key', sa.String(255), nullable=True, unique=True),
        sa.Column('api_key_created_at', sa.DateTime(timezone=True), nullable=True),

        # Preferences
        sa.Column('email_notifications', sa.Boolean(), default=True, nullable=False),
        sa.Column('webhook_url', sa.String(500), nullable=True),

        # Activity
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), default=0, nullable=False),
    )

    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_api_key', 'users', ['api_key'])

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('folder', sa.String(255), nullable=True),
        sa.Column('tags', postgresql.JSONB(), default=[], nullable=False),
        sa.Column('color', sa.String(7), default='#FF6E6B', nullable=False),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_public', sa.Boolean(), default=False, nullable=False),
        sa.Column('public_slug', sa.String(255), nullable=True, unique=True),
        sa.Column('custom_metadata', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('workflow_count', sa.Integer(), default=0, nullable=False),
        sa.Column('generation_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_generation_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_projects_user_id', 'projects', ['user_id'])
    op.create_index('ix_projects_public_slug', 'projects', ['public_slug'])

    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('TEXT_TO_IMAGE', 'IMAGE_TO_IMAGE', 'INPAINTING', 'UPSCALING', 'CUSTOM', name='workflowcategory'), default='TEXT_TO_IMAGE', nullable=False),
        sa.Column('workflow_json', postgresql.JSONB(), nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('preview_image_url', sa.String(500), nullable=True),
        sa.Column('tags', postgresql.JSONB(), default=[], nullable=False),
        sa.Column('parameters', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='SET NULL'), nullable=True),
        sa.Column('version_notes', sa.Text(), nullable=True),
        sa.Column('visibility', sa.Enum('PRIVATE', 'PUBLIC', 'UNLISTED', name='workflowvisibility'), default='PRIVATE', nullable=False),
        sa.Column('public_slug', sa.String(255), nullable=True, unique=True),
        sa.Column('is_template', sa.Boolean(), default=False, nullable=False),
        sa.Column('use_count', sa.Integer(), default=0, nullable=False),
        sa.Column('copy_count', sa.Integer(), default=0, nullable=False),
        sa.Column('features', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('estimated_credits', sa.Integer(), default=1, nullable=False),
    )

    op.create_index('ix_workflows_user_id', 'workflows', ['user_id'])
    op.create_index('ix_workflows_project_id', 'workflows', ['project_id'])
    op.create_index('ix_workflows_category', 'workflows', ['category'])
    op.create_index('ix_workflows_visibility', 'workflows', ['visibility'])
    op.create_index('ix_workflows_public_slug', 'workflows', ['public_slug'])
    op.create_index('ix_workflows_is_template', 'workflows', ['is_template'])

    # Create generations table
    op.create_table(
        'generations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=True),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workflows.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED', name='generationstatus'), default='QUEUED', nullable=False),
        sa.Column('comfyui_prompt_id', sa.String(255), nullable=True, unique=True),
        sa.Column('input_parameters', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('workflow_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('output_urls', postgresql.JSONB(), default=[], nullable=False),
        sa.Column('output_count', sa.Integer(), default=0, nullable=False),
        sa.Column('thumbnail_url', sa.String(500), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('progress_percent', sa.Integer(), default=0, nullable=False),
        sa.Column('progress_message', sa.String(255), nullable=True),
        sa.Column('is_favorited', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), default=[], nullable=False),
        sa.Column('custom_metadata', postgresql.JSONB(), default={}, nullable=False),
        sa.Column('credits_used', sa.Integer(), default=1, nullable=False),
        sa.Column('webhook_sent', sa.Boolean(), default=False, nullable=False),
        sa.Column('webhook_sent_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('ix_generations_user_id', 'generations', ['user_id'])
    op.create_index('ix_generations_project_id', 'generations', ['project_id'])
    op.create_index('ix_generations_workflow_id', 'generations', ['workflow_id'])
    op.create_index('ix_generations_status', 'generations', ['status'])
    op.create_index('ix_generations_comfyui_prompt_id', 'generations', ['comfyui_prompt_id'])
    op.create_index('ix_generations_is_favorited', 'generations', ['is_favorited'])


def downgrade() -> None:
    op.drop_table('generations')
    op.drop_table('workflows')
    op.drop_table('projects')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS generationstatus')
    op.execute('DROP TYPE IF EXISTS workflowvisibility')
    op.execute('DROP TYPE IF EXISTS workflowcategory')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS subscriptiontier')
    op.execute('DROP TYPE IF EXISTS userrole')
