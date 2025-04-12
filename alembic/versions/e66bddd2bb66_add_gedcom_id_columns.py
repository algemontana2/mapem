"""Add gedcom_id columns

Revision ID: e66bddd2bb66
Revises: 
Create Date: 2025-04-09 12:58:26.566004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e66bddd2bb66'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('relationships')
    op.drop_table('people')
    op.add_column('events', sa.Column('family_id', sa.Integer(), nullable=True))
    op.alter_column('events', 'event_type',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=False)
    # Fix: Cast existing text column to DATE with explicit USING clause
    op.execute("ALTER TABLE events ALTER COLUMN date TYPE DATE USING date::DATE")

    op.alter_column('events', 'notes',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_constraint('events_person_id_fkey', 'events', type_='foreignkey')
    op.create_foreign_key(None, 'events', 'families', ['family_id'], ['id'])
    op.drop_column('events', 'event_date')
    op.add_column('families', sa.Column('gedcom_id', sa.String(), nullable=True))
    op.add_column('individuals', sa.Column('gedcom_id', sa.String(), nullable=True))
    op.add_column('locations', sa.Column('name', sa.String(), nullable=True))
    op.add_column('locations', sa.Column('timestamp', sa.DateTime(), nullable=True))
    op.add_column('locations', sa.Column('historical_data', sa.JSON(), nullable=True))
    op.alter_column('locations', 'latitude',
               existing_type=sa.NUMERIC(),
               type_=sa.Float(),
               existing_nullable=True)
    op.alter_column('locations', 'longitude',
               existing_type=sa.NUMERIC(),
               type_=sa.Float(),
               existing_nullable=True)
    op.create_unique_constraint(None, 'locations', ['name'])
    op.drop_column('locations', 'place_name')
    op.alter_column('tree_people', 'tree_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tree_people', 'first_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'last_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'full_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               nullable=True)
    op.alter_column('tree_people', 'birth_location',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'death_location',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'gender',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'occupation',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'race',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'external_id',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_people', 'notes',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_constraint('tree_people_birth_location_id_fkey', 'tree_people', type_='foreignkey')
    op.drop_constraint('tree_people_death_location_id_fkey', 'tree_people', type_='foreignkey')
    op.drop_column('tree_people', 'birth_location_id')
    op.drop_column('tree_people', 'death_location_id')
    op.alter_column('tree_relationships', 'tree_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tree_relationships', 'person_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tree_relationships', 'related_person_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('tree_relationships', 'relationship_type',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('tree_relationships', 'notes',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('uploaded_trees', 'original_filename',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('uploaded_trees', 'uploader_name',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('uploaded_trees', 'notes',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('uploaded_trees', 'notes',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('uploaded_trees', 'uploader_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('uploaded_trees', 'original_filename',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_relationships', 'notes',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_relationships', 'relationship_type',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_relationships', 'related_person_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('tree_relationships', 'person_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('tree_relationships', 'tree_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('tree_people', sa.Column('death_location_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('tree_people', sa.Column('birth_location_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('tree_people_death_location_id_fkey', 'tree_people', 'locations', ['death_location_id'], ['id'])
    op.create_foreign_key('tree_people_birth_location_id_fkey', 'tree_people', 'locations', ['birth_location_id'], ['id'])
    op.alter_column('tree_people', 'notes',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'external_id',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'race',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'occupation',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'gender',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'death_location',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'birth_location',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'full_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=False)
    op.alter_column('tree_people', 'last_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'first_name',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('tree_people', 'tree_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.add_column('locations', sa.Column('place_name', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'locations', type_='unique')
    op.alter_column('locations', 'longitude',
               existing_type=sa.Float(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.alter_column('locations', 'latitude',
               existing_type=sa.Float(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.drop_column('locations', 'historical_data')
    op.drop_column('locations', 'timestamp')
    op.drop_column('locations', 'name')
    op.drop_column('individuals', 'gedcom_id')
    op.drop_column('families', 'gedcom_id')
    op.add_column('events', sa.Column('event_date', sa.DATE(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'events', type_='foreignkey')
    op.create_foreign_key('events_person_id_fkey', 'events', 'tree_people', ['individual_id'], ['id'])
    op.alter_column('events', 'notes',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('events', 'date',
               existing_type=sa.Date(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('events', 'event_type',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               nullable=True)
    op.drop_column('events', 'family_id')
    op.create_table('people',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('people_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('full_name', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('birth_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('death_date', sa.DATE(), autoincrement=False, nullable=True),
    sa.Column('birth_location', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('death_location', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('gender', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('occupation', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('race', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('external_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name='people_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_table('relationships',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('person_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('related_person_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('relationship_type', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('notes', sa.TEXT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['person_id'], ['people.id'], name='relationships_person_id_fkey'),
    sa.ForeignKeyConstraint(['related_person_id'], ['people.id'], name='relationships_related_person_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='relationships_pkey')
    )
    # ### end Alembic commands ###
