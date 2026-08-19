"""
postgres_db.py — Database Engine & Knowledge Retrieval Layer.
Supports live PostgreSQL connections via `POSTGRES_URL` / `DATABASE_URL` with
an automatic embedded SQLite fallback for seamless zero-config local development.
"""

import os
import sqlite3
import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("DatabaseEngine")

# Path for local SQLite storage fallback
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
os.makedirs(DB_DIR, exist_ok=True)
SQLITE_DB_PATH = os.path.join(DB_DIR, "projects.db")

SAMPLE_PROJECTS = [
    (
        1,
        "Project Apollo",
        "High-speed AI knowledge engine with RAG retrieval and vector indexing.",
        "Engineering",
        "Active",
        120000,
        "Vishal Reddy",
        "Evidence: Successfully indexed 50,000 enterprise docs with <500ms latency. Passed Phase 1 load testing.",
        "2026-01-15"
    ),
    (
        2,
        "Cloud Migration 2.0",
        "AWS Multi-Region infrastructure migration and container orchestration.",
        "Operations",
        "Completed",
        85000,
        "Manoj Bonthu",
        "Evidence: 99.99% uptime achieved across 3 AWS availability zones. Cloud compute cost reduced by 35%.",
        "2025-11-01"
    ),
    (
        3,
        "Security Audit v2",
        "Zero-Trust RBAC security hardening, prompt injection defense, and cryptographic audit logging.",
        "Security",
        "In Review",
        45000,
        "Vinod Kumar",
        "Evidence: Passed SOC2 & ISO 27001 audit with zero high-severity vulnerabilities.",
        "2026-02-10"
    ),
    (
        4,
        "Enterprise MCP Gateway",
        "Streamable HTTP + SSE protocol gateway consolidating microservices into unified AI agent interfaces.",
        "Engineering",
        "Active",
        150000,
        "Vishal Reddy",
        "Evidence: Handles 10,000 concurrent MCP agent tool calls across Gmail, Time, and Postgres servers.",
        "2026-03-01"
    ),
    (
        5,
        "Data Lake Pipeline",
        "Real-time Kafka & Spark streaming data pipeline processing 10M+ daily events.",
        "AI & Data",
        "Active",
        95000,
        "Priya Sharma",
        "Evidence: Ingests 10M+ daily events into central analytical warehouse with zero data loss.",
        "2026-02-20"
    )
]


def get_db_connection():
    """
    Returns a database connection. Connects to PostgreSQL if configured,
    otherwise uses embedded SQLite database.
    """
    pg_url = os.getenv("POSTGRES_URL") or os.getenv("DATABASE_URL")
    if pg_url and pg_url.startswith("postgres"):
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            conn = psycopg2.connect(pg_url)
            return conn, "postgres"
        except Exception as exc:
            logger.warning(f"Could not connect to PostgreSQL ({exc}). Using local SQLite engine.")
    
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def init_database():
    """Initializes schema and seeds sample project rows."""
    conn, engine = get_db_connection()
    cursor = conn.cursor()
    try:
        if engine == "sqlite":
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    department TEXT NOT NULL,
                    status TEXT NOT NULL,
                    budget INTEGER NOT NULL,
                    lead_name TEXT NOT NULL,
                    evidence_summary TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.executemany("""
                    INSERT INTO projects (id, name, description, department, status, budget, lead_name, evidence_summary, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, SAMPLE_PROJECTS)
                conn.commit()
                logger.info(f"Initialized SQLite database with {len(SAMPLE_PROJECTS)} project records.")
        else:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    budget INTEGER NOT NULL,
                    lead_name VARCHAR(100) NOT NULL,
                    evidence_summary TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("SELECT COUNT(*) FROM projects")
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.executemany("""
                    INSERT INTO projects (id, name, description, department, status, budget, lead_name, evidence_summary, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, SAMPLE_PROJECTS)
                conn.commit()
                logger.info(f"Initialized PostgreSQL database with {len(SAMPLE_PROJECTS)} project records.")
    except Exception as exc:
        logger.error(f"Database initialization error: {exc}")
    finally:
        conn.close()


# Ensure database is initialized on import
init_database()


def validate_read_only_query(sql: str) -> Tuple[bool, Optional[str]]:
    """Strictly enforces read-only query policy."""
    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "REPLACE", "CREATE", "GRANT", "REVOKE"]
    cleaned = sql.strip().upper()
    
    # Must start with SELECT, WITH, EXPLAIN, or PRAGMA
    if not (cleaned.startswith("SELECT") or cleaned.startswith("WITH") or cleaned.startswith("EXPLAIN") or cleaned.startswith("PRAGMA")):
        return False, "Only read-only queries (SELECT) are permitted by the MCP database security policy."
    
    for kw in forbidden:
        pattern = r"\b" + kw + r"\b"
        if re.search(pattern, cleaned):
            return False, f"Query rejected: modifying keyword '{kw}' is prohibited."
            
    return True, None


def execute_sql_query(sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Executes a validated read-only SQL query."""
    is_valid, err_msg = validate_read_only_query(sql)
    if not is_valid:
        return {"status": "failed", "error": "query_not_allowed", "message": err_msg}

    conn, engine = get_db_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        if engine == "sqlite":
            rows = [dict(row) for row in cursor.fetchall()]
        else:
            columns = [desc[0] for desc in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return {
            "status": "success",
            "engine": engine,
            "query": sql,
            "row_count": len(rows),
            "rows": rows,
        }
    except Exception as exc:
        return {"status": "failed", "error": "sql_execution_error", "message": str(exc)}
    finally:
        conn.close()


def query_projects_by_filter(
    department: Optional[str] = None,
    status: Optional[str] = None,
    lead_name: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """Queries projects table with dynamic filters."""
    sql = "SELECT id, name, department, status, budget, lead_name, description, evidence_summary, created_at FROM projects WHERE 1=1"
    params = []

    if department:
        sql += " AND LOWER(department) LIKE ?"
        params.append(f"%{department.strip().lower()}%")
    if status:
        sql += " AND LOWER(status) = ?"
        params.append(status.strip().lower())
    if lead_name:
        sql += " AND LOWER(lead_name) LIKE ?"
        params.append(f"%{lead_name.strip().lower()}%")

    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)

    return execute_sql_query(sql, params)


def get_project_evidence_by_name(project_name_or_id: str) -> Dict[str, Any]:
    """Retrieves specific project evidence by name or ID."""
    cleaned = project_name_or_id.strip()
    if cleaned.isdigit():
        sql = "SELECT id, name, department, status, budget, lead_name, description, evidence_summary, created_at FROM projects WHERE id = ?"
        params = [int(cleaned)]
    else:
        sql = "SELECT id, name, department, status, budget, lead_name, description, evidence_summary, created_at FROM projects WHERE LOWER(name) LIKE ? LIMIT 1"
        params = [f"%{cleaned.lower()}%"]

    res = execute_sql_query(sql, params)
    rows = res.get("rows", [])
    if rows:
        return {
            "status": "success",
            "project": rows[0],
            "evidence": rows[0].get("evidence_summary"),
        }
    return {
        "status": "not_found",
        "message": f"No project found matching '{project_name_or_id}'."
    }
