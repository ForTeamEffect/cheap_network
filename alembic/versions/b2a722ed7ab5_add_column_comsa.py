"""Add column Comsa

Revision ID: b2a722ed7ab5
Revises: f6195fd5a18f
Create Date: 2024-02-09 13:51:03.902386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2a722ed7ab5'
down_revision: Union[str, None] = 'f6195fd5a18f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавление нового столбца для timestamp
    op.add_column('commission', sa.Column('new_update_time', sa.Integer(), nullable=True))
    # Здесь может быть код для переноса и преобразования данных из update_time в new_update_time
    # Удаление старого столбца
    op.drop_column('commission', 'update_time')
    # Переименование нового столбца
    op.alter_column('commission', 'new_update_time', new_column_name='update_time')

def downgrade():
    # Для операции отката, если вам нужно вернуться к исходному типу данных
    op.execute('ALTER TABLE commission ALTER COLUMN update_time TYPE original_data_type USING update_time::original_data_type')
    # Замените original_data_type на исходный тип данных столбца
