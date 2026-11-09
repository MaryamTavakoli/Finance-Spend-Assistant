"""
database.py: the agent's only door to the data.

What this file does:
  1. Loads the two CSV files (invoices, vendors) into an in-memory DuckDB database.
  2. Locks the database, so queries can no longer read files, websites or change settings.
  3. Offers run_query(sql): runs ONE read-only SELECT and returns the result.

Safety comes from two independent layers:
  - run_query only accepts a single SELECT statement (no DELETE, UPDATE, DROP, ...).
  - The lock means even a SELECT can only see the two tables we loaded.
"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

# ------------------------------------------------------------------------------------------
# File locations
# ------------------------------------------------------------------------------------------
#  Project layout:  <project>/backend/database.py  and  <project>/data/
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# .as_posix() writes the path with forward slashes ("C:/.../file.csv"), which DuckDB understands on every operating system, including Windows.
INVOICES_CSV = (DATA_DIR / "invoices_2025_clean.csv").as_posix()
VENDORS_CSV = (DATA_DIR / "vendor_master.csv").as_posix()

# ------------------------------------------------------------------------------------------
# Step 1: load the CSV files into tables
# ------------------------------------------------------------------------------------------
# Create an in-memory database  
con = duckdb.connect()

# Copy the data from the CSV files into DuckDB tables: invoices and vendors
#   amount       -> DECIMAL(18,2): exact money values with 2 decimals (no float rounding errors)
#   invoice_date -> DATE: so date filters and MIN/MAX work as real dates
con.execute(f"""
    CREATE TABLE invoices AS
    SELECT * FROM read_csv('{INVOICES_CSV}', types={{'amount': 'DECIMAL(18,2)', 'invoice_date': 'DATE'}})
""")

con.execute(f"""
CREATE TABLE vendors AS SELECT * FROM read_csv('{VENDORS_CSV}')
""")

# ------------------------------------------------------------------------------------------
# Step 2: lock the database (must happen AFTER loading)
# ------------------------------------------------------------------------------------------
# Disable DuckDB access to external resources, including local files and remote data sources.
con.execute("SET enable_external_access = false")

# Lock the DuckDB configuration, preventing subsequent queries from re-enabling external access.
con.execute("SET lock_configuration = true")

# ------------------------------------------------------------------------------------------
# Step 3: the guarded query function
# ------------------------------------------------------------------------------------------
MAX_ROWS = 200   # Limit the maximum number of rows that a query returns 

def run_query(sql):
    """
    Run one read-only SELECT query. Return errors in case of failure.
    Args:
        sql (str): The SQL query to run.
    Returns a dictionary:
        success -> {"columns": [...], "rows": [[...], ...], truncated -> True/False}
        failure -> {"error": "error message"}
    """
    sql = sql.strip().rstrip(";")  # remove trailing semicolon if present

    try:
        statements = duckdb.extract_statements(sql) # parse the query with DuckDB parser
    except duckdb.Error as e:
        return {"error": f"SQL could not be parsed: {str(e)}"} # block invalid SQL statements
    if len(statements) != 1:
        return {"error": "Exactly one SQL statement is allowed."} # block multiple SQL statements
    if statements[0].type != duckdb.StatementType.SELECT:
        return {"error": "Only read-ony SELECT queries are allowed."} # block DELETE, UPDATE, DROP, SET, ...

    # Create a separate connection to the same DuckDB database instance to prevent queries from different web requests from interfering with one another.
    cur = con.cursor()
    try:
        result = cur.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchmany(MAX_ROWS + 1)
    except duckdb.Error as e:
        return {"error": f"{type(e).__name__}: {e}"}
    finally:
        cur.close() 

    cleaned_rows =[[clean(v) for v in row] for row in rows[:MAX_ROWS]]
    return {"columns": columns, "rows": cleaned_rows, "truncated": len(rows) > MAX_ROWS}

def clean(value):
    """ 
    Convert DuckDB values into plain types that can be printed and sent as JSON.
    Decimal('1234.56') -> 1234.56
    date(2026, 9, 11) -> '2026-09-11' 
    Everything else (text, integers, None) is returned unchanged.
    """
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

# ------------------------------------------------------------------------------------------
# Self-test: run  `python database.py`  to check that every attack is blocked.
# ------------------------------------------------------------------------------------------
if __name__ == "__main__":
    questions = [
    "SELEC COUNT(*) FROM invoces",
    "DELETE FROM invoices",
    "UPDATE invoices SET amount=0",
    "INSERT INTO vendors VALUES ('V-9999', 'Evil Ltd', 'X', 'X', 'ACTIVE')",
    "DROP TABLE vendors",
    "SELECT 1; SELECT COUNT(*) FROM invoices",
    "COPY invoices TO 'stolen.csv'",
    "ATTACH 'other.db'",
    "SET enable_external_access=true",
    "SELECT * FROM read_csv('/etc/passwd')",
    "SELECT * FROM read_text('/etc/hosts')",
    f"SELECT * FROM '{INVOICES_CSV}'",
    ]

    for sql in questions:
        print(f"{sql} -> {run_query(sql).get("error", "NOT BLOCKED")[:70]}")