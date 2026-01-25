import sqlite3
import signal
from typing import Dict, Any, List
from pathlib import Path
from contextlib import contextmanager

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import SQL_TIMEOUT, MAX_RESULT_ROWS
from services.sql_validator import validate_sql


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Sorgu zaman aşımına uğradı.")


@contextmanager
def timeout(seconds: int):
    """Context manager for query timeout (Unix only)."""
    # Note: signal-based timeout only works on Unix
    if hasattr(signal, 'SIGALRM'):
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # On Windows, just yield without timeout
        yield


class SQLExecutor:
    """Execute SQL queries safely on SQLite databases."""

    def __init__(self, timeout_seconds: int = SQL_TIMEOUT, max_rows: int = MAX_RESULT_ROWS):
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

    def execute(self, db_path: str, sql: str) -> Dict[str, Any]:
        """
        Execute a SQL query on the specified database.

        Args:
            db_path: Path to the SQLite database file
            sql: The SQL query to execute

        Returns:
            Dict with 'success', 'columns', 'rows', 'row_count', 'error' keys
        """
        # Validate SQL first
        is_valid, error = validate_sql(sql)
        if not is_valid:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": error
            }

        # Check if database file exists
        if not Path(db_path).exists():
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Veritabanı bulunamadı: {db_path}"
            }

        try:
            # Connect in read-only mode
            conn = sqlite3.connect(
                f"file:{db_path}?mode=ro",
                uri=True,
                timeout=self.timeout_seconds
            )
            cursor = conn.cursor()

            # Execute with timeout
            with timeout(self.timeout_seconds):
                cursor.execute(sql)
                rows = cursor.fetchmany(self.max_rows)

            # Get column names
            columns = [description[0] for description in cursor.description] if cursor.description else []

            # Convert rows to list of lists (for JSON serialization)
            rows_list = [list(row) for row in rows]

            # Check if there are more rows
            has_more = len(rows_list) == self.max_rows

            conn.close()

            return {
                "success": True,
                "columns": columns,
                "rows": rows_list,
                "row_count": len(rows_list),
                "has_more": has_more,
                "error": ""
            }

        except TimeoutError as e:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": str(e)
            }
        except sqlite3.Error as e:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Veritabanı hatası: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "error": f"Beklenmeyen hata: {str(e)}"
            }


# Singleton instance
_executor = None


def get_sql_executor() -> SQLExecutor:
    """Get or create the SQL executor instance."""
    global _executor
    if _executor is None:
        _executor = SQLExecutor()
    return _executor


if __name__ == "__main__":
    from indexing.schema_parser import get_schemas

    # Test SQL execution
    executor = get_sql_executor()
    schemas = get_schemas()

    if "şarkıcı" in schemas:
        schema = schemas["şarkıcı"]
        db_path = schema.path

        print(f"Database: {schema.name}")
        print(f"Path: {db_path}")

        # Test valid query
        sql = "SELECT * FROM şarkıcı LIMIT 5;"
        print(f"\nQuery: {sql}")
        result = executor.execute(db_path, sql)
        print(f"Success: {result['success']}")
        print(f"Columns: {result['columns']}")
        print(f"Row count: {result['row_count']}")
        if result['rows']:
            print("Sample rows:")
            for row in result['rows'][:3]:
                print(f"  {row}")

        # Test invalid query
        sql_invalid = "DELETE FROM şarkıcı"
        print(f"\nInvalid Query: {sql_invalid}")
        result = executor.execute(db_path, sql_invalid)
        print(f"Success: {result['success']}")
        print(f"Error: {result['error']}")
