"""rename api_tokens to api_keys

Revision ID: a1b2c3d4e5f6
Revises: d52391f4d70c
Create Date: 2026-03-12 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd52391f4d70c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 重命名表 api_tokens -> api_keys
    op.rename_table('api_tokens', 'api_keys')

    # 重命名列 token_hash -> key_hash
    op.alter_column('api_keys', 'token_hash', new_column_name='key_hash')

    # 重建索引（旧索引名 -> 新索引名）
    op.drop_index('ix_api_tokens_token_hash', table_name='api_keys')
    op.drop_index('ix_api_tokens_user_id', table_name='api_keys')
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'], unique=True)
    op.create_index('ix_api_keys_user_id', 'api_keys', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_api_keys_user_id', table_name='api_keys')
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.create_index('ix_api_tokens_user_id', 'api_keys', ['user_id'], unique=False)
    op.create_index('ix_api_tokens_token_hash', 'api_keys', ['key_hash'], unique=True)
    op.alter_column('api_keys', 'key_hash', new_column_name='token_hash')
    op.rename_table('api_keys', 'api_tokens')
