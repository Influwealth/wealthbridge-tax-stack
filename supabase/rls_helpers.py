"""
Row-Level Security (RLS) policy generators for Supabase PostgreSQL.

Use these helpers to generate SQL policy strings. Apply them in
supabase/migrations/ SQL files or via the Supabase dashboard.
"""
from typing import Literal

Operation = Literal["SELECT", "INSERT", "UPDATE", "DELETE", "ALL"]


def enable_rls(table: str) -> str:
    return f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"


def create_policy(
    table: str,
    policy_name: str,
    operation: Operation,
    role: str,
    using: str,
    with_check: str | None = None,
) -> str:
    sql = (
        f"CREATE POLICY {policy_name}\n"
        f"  ON {table}\n"
        f"  FOR {operation}\n"
        f"  TO {role}\n"
        f"  USING ({using})"
    )
    if with_check:
        sql += f"\n  WITH CHECK ({with_check})"
    return sql + ";"


def tenant_isolation_policy(table: str, tenant_col: str = "tenant_id") -> str:
    """Generate a policy that isolates rows by tenant_id from the JWT claim."""
    return create_policy(
        table=table,
        policy_name=f"{table}_tenant_isolation",
        operation="ALL",
        role="authenticated",
        using=f"({tenant_col} = (auth.jwt() ->> 'tenant_id')::uuid)",
        with_check=f"({tenant_col} = (auth.jwt() ->> 'tenant_id')::uuid)",
    )


def owner_only_policy(table: str, owner_col: str = "created_by") -> str:
    """Generate a policy restricting row access to the row creator."""
    return create_policy(
        table=table,
        policy_name=f"{table}_owner_only",
        operation="ALL",
        role="authenticated",
        using=f"({owner_col}::text = auth.uid()::text)",
        with_check=f"({owner_col}::text = auth.uid()::text)",
    )


def admin_bypass_policy(table: str) -> str:
    """Generate a policy giving admins unrestricted access."""
    return create_policy(
        table=table,
        policy_name=f"{table}_admin_bypass",
        operation="ALL",
        role="service_role",
        using="true",
    )


def generate_wealthbridge_rls(tables: list[str] | None = None) -> str:
    """
    Generate complete RLS SQL for WealthBridge tables.
    Returns a single SQL script string.
    """
    target_tables = tables or ["tax_records", "rd_projects", "tax_documents"]
    statements = []

    for table in target_tables:
        statements.append(f"-- {table}")
        statements.append(enable_rls(table))
        statements.append(owner_only_policy(table))
        statements.append(admin_bypass_policy(table))
        statements.append("")

    return "\n".join(statements)
