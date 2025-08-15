"""Initial generic schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create initial generic schema with example User and Post models.
    
    This migration demonstrates common patterns and relationships
    that can be adapted for your specific application needs.
    """
    
    # Create user table - example entity with basic fields
    op.create_table('user',
        # Base model fields (id, timestamps)
        sa.Column('id', sa.String(length=36), nullable=False, comment='Primary key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record last update timestamp'),
        
        # Soft delete mixin fields
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft deletion timestamp'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False, comment='Soft deletion flag'),
        
        # Audit mixin fields
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='ID of user who created the record'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='ID of user who last updated the record'),
        
        # User-specific fields (example)
        sa.Column('username', sa.String(length=50), nullable=False, comment='Unique username'),
        sa.Column('email', sa.String(length=255), nullable=False, comment='User email address'),
        sa.Column('hashed_password', sa.String(length=255), nullable=False, comment='Hashed password'),
        sa.Column('full_name', sa.String(length=100), nullable=True, comment="User's full name"),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending', comment='User account status'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='Account active status'),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    
    # Create indexes for user table
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=False)
    op.create_index(op.f('ix_user_is_active'), 'user', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_status'), 'user', ['status'], unique=False)
    
    # Create post table - example related entity demonstrating relationships
    op.create_table('post',
        # Base model fields
        sa.Column('id', sa.String(length=36), nullable=False, comment='Primary key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False, comment='Record last update timestamp'),
        
        # Soft delete mixin fields
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Soft deletion timestamp'),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, default=False, comment='Soft deletion flag'),
        
        # Audit mixin fields
        sa.Column('created_by', sa.String(length=36), nullable=True, comment='ID of user who created the record'),
        sa.Column('updated_by', sa.String(length=36), nullable=True, comment='ID of user who last updated the record'),
        
        # Post-specific fields (example)
        sa.Column('title', sa.String(length=200), nullable=False, comment='Post title'),
        sa.Column('content', sa.Text(), nullable=True, comment='Post content'),
        sa.Column('is_published', sa.Boolean(), nullable=False, default=False, comment='Publication status'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True, comment='Publication timestamp'),
        sa.Column('view_count', sa.Integer(), nullable=False, default=0, comment='Number of views'),
        
        # Foreign key relationship (example of many-to-one)
        sa.Column('author_id', sa.String(length=36), nullable=False, comment='ID of the user who authored this post'),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['author_id'], ['user.id'], ondelete='CASCADE')
    )
    
    # Create indexes for post table
    op.create_index(op.f('ix_post_author_id'), 'post', ['author_id'], unique=False)
    op.create_index(op.f('ix_post_is_published'), 'post', ['is_published'], unique=False)
    op.create_index('idx_post_published_at', 'post', ['published_at'])
    op.create_index('idx_post_author_published', 'post', ['author_id', 'is_published'])


def downgrade() -> None:
    """
    Drop the generic schema tables.
    """
    
    # Drop post table
    op.drop_index('idx_post_author_published', table_name='post')
    op.drop_index('idx_post_published_at', table_name='post')
    op.drop_index(op.f('ix_post_is_published'), table_name='post')
    op.drop_index(op.f('ix_post_author_id'), table_name='post')
    op.drop_table('post')
    
    # Drop user table
    op.drop_index(op.f('ix_user_status'), table_name='user')
    op.drop_index(op.f('ix_user_is_active'), table_name='user')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')