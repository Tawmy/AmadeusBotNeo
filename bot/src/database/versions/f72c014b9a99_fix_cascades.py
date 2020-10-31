"""fix_cascades

Revision ID: f72c014b9a99
Revises: a4ce5df2cbf8
Create Date: 2020-10-31 19:26:53.175234

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f72c014b9a99'
down_revision = 'a4ce5df2cbf8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('attachment_message_id_fkey', 'attachment', type_='foreignkey')
    op.create_foreign_key(None, 'attachment', 'message', ['message_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('avatar_user_id_fkey', 'avatar', type_='foreignkey')
    op.create_foreign_key(None, 'avatar', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('message_user_id_fkey', 'message', type_='foreignkey')
    op.create_foreign_key(None, 'message', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('name_user_id_fkey', 'name', type_='foreignkey')
    op.create_foreign_key(None, 'name', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'name', type_='foreignkey')
    op.create_foreign_key('name_user_id_fkey', 'name', 'user', ['user_id'], ['id'])
    op.drop_constraint(None, 'message', type_='foreignkey')
    op.create_foreign_key('message_user_id_fkey', 'message', 'user', ['user_id'], ['id'])
    op.drop_constraint(None, 'avatar', type_='foreignkey')
    op.create_foreign_key('avatar_user_id_fkey', 'avatar', 'user', ['user_id'], ['id'])
    op.drop_constraint(None, 'attachment', type_='foreignkey')
    op.create_foreign_key('attachment_message_id_fkey', 'attachment', 'message', ['message_id'], ['id'])
    # ### end Alembic commands ###
