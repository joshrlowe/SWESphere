"""Add new features: likes, comments, notifications, email verification, lockout, avatars

Revision ID: add_new_features
Revises: 61e464b229eb
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_new_features'
down_revision = '61e464b229eb'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('email_verified_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True, default=0))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('lockout_count', sa.Integer(), nullable=True, default=0))
        batch_op.add_column(sa.Column('avatar_filename', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # Set default values for existing rows
    op.execute("UPDATE user SET email_verified = 0 WHERE email_verified IS NULL")
    op.execute("UPDATE user SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL")
    op.execute("UPDATE user SET lockout_count = 0 WHERE lockout_count IS NULL")

    # Create post_likes table
    op.create_table('post_likes',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('user_id', 'post_id')
    )

    # Create comment table
    op.create_table('comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('body', sa.String(length=280), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_comment_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_comment_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_comment_post_id'), ['post_id'], unique=False)

    # Create notification table
    op.create_table('notification',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('payload_json', sa.Text(), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=False, default=False),
        sa.ForeignKeyConstraint(['actor_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_notification_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_timestamp'), ['timestamp'], unique=False)
        batch_op.create_index(batch_op.f('ix_notification_user_id'), ['user_id'], unique=False)


def downgrade():
    # Drop notification table
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notification_user_id'))
        batch_op.drop_index(batch_op.f('ix_notification_timestamp'))
        batch_op.drop_index(batch_op.f('ix_notification_name'))
    op.drop_table('notification')

    # Drop comment table
    with op.batch_alter_table('comment', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comment_post_id'))
        batch_op.drop_index(batch_op.f('ix_comment_user_id'))
        batch_op.drop_index(batch_op.f('ix_comment_timestamp'))
    op.drop_table('comment')

    # Drop post_likes table
    op.drop_table('post_likes')

    # Remove new columns from user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('created_at')
        batch_op.drop_column('avatar_filename')
        batch_op.drop_column('lockout_count')
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_login_attempts')
        batch_op.drop_column('email_verified_at')
        batch_op.drop_column('email_verified')
