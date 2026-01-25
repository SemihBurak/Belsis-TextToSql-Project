from typing import Dict, Any
from pathlib import Path
import time

import sys
sys.path.append(str(Path(__file__).parent.parent))
from indexing.schema_parser import DatabaseSchema
from services.llm_service import get_llm_service
from services.sql_validator import validate_sql


class SQLGenerator:
    """Generate SQL queries from natural language questions."""

    def __init__(self):
        self.llm = get_llm_service()

    def generate(
        self,
        question: str,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """
        Generate SQL query for the given question and database schema.

        Returns:
            Dict with 'sql', 'is_valid', 'error' keys
        """
        # Get SQL schema representation
        schema_sql = schema.to_sql_schema()

        # Generate SQL using LLM
        llm_start = time.time()
        sql = self.llm.generate_sql(
            question=question,
            schema_sql=schema_sql,
            db_name=schema.name
        )
        llm_time = time.time() - llm_start
        print(f"    🤖 LLM SQL generation: {llm_time:.2f}s")

        # Check if LLM indicated data is not available
        if sql.startswith("VERI_YOK"):
            error_msg = sql.replace("VERI_YOK:", "").strip()
            return {
                "sql": "",
                "is_valid": False,
                "error": f"Bu veritabanında istenen bilgi bulunamadı: {error_msg}"
            }

        # Validate the generated SQL
        validate_start = time.time()
        is_valid, error = validate_sql(sql)
        validate_time = time.time() - validate_start
        print(f"    ✓ SQL validation: {validate_time:.3f}s")

        return {
            "sql": sql,
            "is_valid": is_valid,
            "error": error
        }


# Singleton instance
_generator = None


def get_sql_generator() -> SQLGenerator:
    """Get or create the SQL generator instance."""
    global _generator
    if _generator is None:
        _generator = SQLGenerator()
    return _generator


if __name__ == "__main__":
    from indexing.schema_parser import get_schemas

    # Test SQL generation
    generator = get_sql_generator()
    schemas = get_schemas()

    # Test with singer database
    if "şarkıcı" in schemas:
        schema = schemas["şarkıcı"]
        question = "Şarkıcıların isimleri nelerdir?"

        print(f"Question: {question}")
        print(f"Database: {schema.name}")
        print(f"\nSchema:\n{schema.to_sql_schema()}")

        result = generator.generate(question, schema)
        print(f"\nGenerated SQL: {result['sql']}")
        print(f"Is valid: {result['is_valid']}")
        if result['error']:
            print(f"Error: {result['error']}")
