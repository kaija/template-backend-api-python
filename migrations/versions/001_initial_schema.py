"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user table
    op.create_table('user',
        sa.Column('id', sa.String(length=36), nullable=False, comment='Primary key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record last update timestamp'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft deletion timestamp'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='Soft deletion flag'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='ID of user who created the record'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='ID of user who last updated the record'),
        sa.Column('username', sa.String(length=50), nullable=False, comment='Unique username for login'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='User email address'),
        sa.Column('hashed_password', sa.String(length=255), nullable=False, comment='Bcrypt hashed password'),
        sa.Column('full_name', sa.String(length=100), nullable=True, comment="User's full name"),
        sa.Column('first_name', sa.String(length=50), nullable=True, comment="User's first name"),
        sa.Column('last_name', sa.String(length=50), nullable=True, comment="User's last name"),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'SUSPENDED', 'PENDING', 'DELETED', name='userstatus'), nullable=False, comment='User account status'),
        sa.Column('role', sa.Enum('GUEST', 'USER', 'PREMIUM_USER', 'MODERATOR', 'EDITOR', 'ADMIN', 'SUPER_ADMIN', 'API_USER', 'API_SERVICE', 'SYSTEM', name='userrole'), nullable=False, comment='User role for permissions'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, comment='Email verification status'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Account active status'),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True, comment='Last successful login timestamp'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, comment='Number of consecutive failed login attempts'),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True, comment='Account lock expiration timestamp'),
        sa.Column('email_verification_token', sa.String(length=255), nullable=True, comment='Email verification token'),
        sa.Column('email_verification_expires', sa.DateTime(timezone=True), nullable=True, comment='Email verification token expiration'),
        sa.Column('password_reset_token', sa.String(length=255), nullable=True, comment='Password reset token'),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True), nullable=True, comment='Password reset token expiration'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create indexes for user table
    op.create_index('idx_user_email_status', 'user', ['email', 'status'])
    op.create_index('idx_user_username_active', 'user', ['username', 'is_active'])
    op.create_index('idx_user_role_active', 'user', ['role', 'is_active'])
    op.create_index('idx_user_last_login', 'user', ['last_login_at'])
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
    op.create_index(op.f('ix_user_is_active'), 'user', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_role'), 'user', ['role'], unique=False)
    op.create_index(op.f('ix_user_status'), 'user', ['status'], unique=False)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=False)
    
    # Create api_key table
    op.create_table('api_key',
        sa.Column('id', sa.String(length=36), nullable=False, comment='Primary key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record last update timestamp'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft deletion timestamp'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, comment='Soft deletion flag'),
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='ID of user who created the record'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='ID of user who last updated the record'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Human-readable name for the API key'),
        sa.Column('key_hash', sa.String(length=255), nullable=False, comment='Hashed API key value'),
        sa.Column('key_prefix', sa.String(length=10), nullable=False, comment='First few characters of the key for identification'),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'REVOKED', 'EXPIRED', name='apikeystatus'), nullable=False, comment='API key status'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True, comment='Last time this key was used'),
        sa.Column('usage_count', sa.Integer(), nullable=False, comment='Total number of times this key has been used'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='API key expiration timestamp'),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='ID of the user who owns this API key'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    
    # Create indexes for api_key table
    op.create_index('idx_apikey_user_status', 'api_key', ['user_id', 'status'])
    op.create_index('idx_apikey_prefix_status', 'api_key', ['key_prefix', 'status'])
    op.create_index('idx_apikey_expires', 'api_key', ['expires_at'])
    op.create_index('idx_apikey_last_used', 'api_key', ['last_used_at'])
    op.create_index(op.f('ix_api_key_key_hash'), 'api_key', ['key_hash'], unique=False)
    op.create_index(op.f('ix_api_key_key_prefix'), 'api_key', ['key_prefix'], unique=False)
    op.create_index(op.f('ix_api_key_status'), 'api_key', ['status'], unique=False)
    op.create_index(op.f('ix_api_key_user_id'), 'api_key', ['user_id'], unique=False)
    
    # Create user_session table
    op.create_table('user_session',
        sa.Column('id', sa.String(length=36), nullable=False, comment='Primary key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record last update timestamp'),
        sa.Column('session_token', sa.String(length=255), nullable=False, comment='Unique session token'),
        sa.Column('user_id', sa.String(length=36), nullable=False, comment='ID of the user who owns this session'),
        sa.Column('ip_address', sa.String(length=45), nullable=True, comment='IP address of the session'),
        sa.Column('user_agent', sa.Text(), nullable=True, comment='User agent string'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, comment='Session expiration timestamp'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Last activity timestamp'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Session active status'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    
    # Create indexes for user_session table
    op.create_index('idx_session_user_active', 'user_session', ['user_id', 'is_active'])
    op.create_index('idx_session_expires', 'user_session', ['expires_at'])
    op.create_index('idx_session_activity', 'user_session', ['last_activity_at'])
    op.create_index(op.f('ix_user_session_expires_at'), 'user_session', ['expires_at'], unique=False)
    op.create_index(op.f('ix_user_session_is_active'), 'user_session', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_session_session_token'), 'user_session', ['session_token'], unique=False)
    op.create_index(op.f('ix_user_session_user_id'), 'user_session', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop user_session table
    op.drop_index(op.f('ix_user_session_user_id'), table_name='user_session')
    op.drop_index(op.f('ix_user_session_session_token'), table_name='user_session')
    op.drop_index(op.f('ix_user_session_is_active'), table_name='user_session')
    op.drop_index(op.f('ix_user_session_expires_at'), table_name='user_session')
    op.drop_index('idx_session_activity', table_name='user_session')
    op.drop_index('idx_session_expires', table_name='user_session')
    op.drop_index('idx_session_user_active', table_name='user_session')
    op.drop_table('user_session')
    
    # Drop api_key table
    op.drop_index(op.f('ix_api_key_user_id'), table_name='api_key')
    op.drop_index(op.f('ix_api_key_status'), table_name='api_key')
    op.drop_index(op.f('ix_api_key_key_prefix'), table_name='api_key')
    op.drop_index(op.f('ix_api_key_key_hash'), table_name='api_key')
    op.drop_index('idx_apikey_last_used', table_name='api_key')
    op.drop_index('idx_apikey_expires', table_name='api_key')
    op.drop_index('idx_apikey_prefix_status', table_name='api_key')
    op.drop_index('idx_apikey_user_status', table_name='api_key')
    op.drop_table('api_key')
    
    # Drop user table
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_status'), table_name='user')
    op.drop_index(op.f('ix_user_role'), table_name='user')
    op.drop_index(op.f('ix_user_is_active'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_index('idx_user_last_login', table_name='user')
    op.drop_index('idx_user_role_active', table_name='user')
    op.drop_index('idx_user_username_active', table_name='user')
    op.drop_index('idx_user_email_status', table_name='user')
    op.drop_table('user')