"""SQL helpers used by Alembic migrations."""

from alembic import op

FORBID_MUTATION_FUNCTION = """
CREATE OR REPLACE FUNCTION lims_forbid_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Table % is append-only: % is not permitted', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""


def create_forbid_mutation_function() -> None:
    op.execute(FORBID_MUTATION_FUNCTION)


def make_append_only(table: str) -> None:
    """Reject UPDATE, DELETE and TRUNCATE on `table` for every database role."""
    op.execute(
        f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION lims_forbid_mutation()"
    )
    op.execute(
        f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} "
        f"FOR EACH STATEMENT EXECUTE FUNCTION lims_forbid_mutation()"
    )


def drop_append_only(table: str) -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute(f"DROP TRIGGER IF EXISTS {table}_no_truncate ON {table}")
