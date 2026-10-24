"""allow mairie declarations without hospital

Revision ID: 497ec5a812a6
Revises: 785574c627ff
Create Date: 2026-10-23 06:32:01.986215

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '497ec5a812a6'
down_revision = '785574c627ff'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('dossiers_naissance', schema=None) as batch_op:
        batch_op.alter_column('hopital_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=True)
        batch_op.drop_constraint(batch_op.f('dossiers_naissance_ibfk_1'), type_='foreignkey')
        batch_op.create_foreign_key(
            'fk_dossiers_naissance_hopital_id_hopitaux',
            'hopitaux',
            ['hopital_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade():
    connection = op.get_bind()
    null_hospital_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM dossiers_naissance WHERE hopital_id IS NULL"
        )
    ).scalar_one()
    if null_hospital_count:
        raise RuntimeError(
            "Cannot make dossiers_naissance.hopital_id required while "
            "mairie-created declarations without a hospital exist."
        )

    with op.batch_alter_table('dossiers_naissance', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_dossiers_naissance_hopital_id_hopitaux',
            type_='foreignkey',
        )
        batch_op.create_foreign_key(batch_op.f('dossiers_naissance_ibfk_1'), 'hopitaux', ['hopital_id'], ['id'], ondelete='CASCADE')
        batch_op.alter_column('hopital_id',
               existing_type=mysql.INTEGER(display_width=11),
               nullable=False)
