"""add full-text search to tasks

Revision ID: 002_fts_tasks
Revises: 01d6798f4d78
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = '002_fts_tasks'
down_revision = '01d6798f4d78'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add the tsvector column
    op.add_column(
        'tasks',
        sa.Column('search_vector', TSVECTOR, nullable=True)
    )

    # 2. Create a GIN index for fast full-text search queries
    op.execute(
        "CREATE INDEX idx_tasks_search_vector ON tasks USING GIN(search_vector)"
    )

    # 3. Populate the column for all existing rows
    op.execute("""
        UPDATE tasks
        SET search_vector = to_tsvector(
            'english',
            coalesce(title, '') || ' ' || coalesce(description, '')
        )
    """)

    # 4. Create a trigger function that keeps the vector updated automatically
    op.execute("""
        CREATE OR REPLACE FUNCTION tasks_search_vector_update() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector(
                'english',
                coalesce(NEW.title, '') || ' ' || coalesce(NEW.description, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # 5. Attach the trigger to the tasks table
    op.execute("""
        CREATE TRIGGER tasks_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, description
        ON tasks
        FOR EACH ROW
        EXECUTE FUNCTION tasks_search_vector_update();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tasks_search_vector_trigger ON tasks")
    op.execute("DROP FUNCTION IF EXISTS tasks_search_vector_update")
    op.execute("DROP INDEX IF EXISTS idx_tasks_search_vector")
    op.drop_column('tasks', 'search_vector')