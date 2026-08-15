import sqlite3
import sys

db_path = 'data/ssas.db'

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=== DATABASE STRUCTURE ===")
    print("\nTables and Views:")
    cur.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]})")

    print("\n=== SSA_TABLE SCHEMA ===")
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ssa_table'")
    result = cur.fetchone()
    if result:
        print(result[0])

    print("\n=== SSA_TABLE DATA ===")
    cur.execute("SELECT COUNT(*) FROM ssa_table")
    count = cur.fetchone()[0]
    print(f"Total records: {count}")

    cur.execute("PRAGMA table_info(ssa_table)")
    columns = cur.fetchall()
    print(f"\nColumns ({len(columns)}):")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    print("\n=== SAMPLE DATA ===")
    cur.execute("SELECT * FROM ssa_table LIMIT 1")
    sample = cur.fetchone()
    if sample:
        print("First record has data: YES")

    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
