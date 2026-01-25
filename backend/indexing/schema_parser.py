import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import TURSPIDER_DB_PATH, SCHEMA_CACHE_DIR


@dataclass
class ColumnInfo:
    name: str
    type: str
    is_primary_key: bool
    is_foreign_key: bool
    references: str | None = None


@dataclass
class TableInfo:
    name: str
    columns: List[ColumnInfo]


@dataclass
class DatabaseSchema:
    name: str
    path: str
    tables: List[TableInfo]

    def get_table_names(self) -> List[str]:
        return [t.name for t in self.tables]

    def get_all_columns(self) -> List[str]:
        columns = []
        for table in self.tables:
            columns.extend([f"{table.name}.{c.name}" for c in table.columns])
        return columns

    def to_schema_text(self) -> str:
        """Convert schema to readable text for embedding."""
        lines = [f"Veritabanı: {self.name}"]
        lines.append(f"Tablolar: {', '.join(self.get_table_names())}")

        for table in self.tables:
            cols = [c.name for c in table.columns]
            lines.append(f"  {table.name}: {', '.join(cols)}")

        return "\n".join(lines)

    def to_sql_schema(self) -> str:
        """Convert schema to SQL CREATE statements for LLM context."""
        lines = []
        for table in self.tables:
            cols = []
            for col in table.columns:
                col_def = f"    {col.name} {col.type}"
                if col.is_primary_key:
                    col_def += " PRIMARY KEY"
                if col.is_foreign_key and col.references:
                    col_def += f" REFERENCES {col.references}"
                cols.append(col_def)

            lines.append(f"CREATE TABLE {table.name} (")
            lines.append(",\n".join(cols))
            lines.append(");")
            lines.append("")

        return "\n".join(lines)


def parse_database_schema(db_path: Path) -> DatabaseSchema | None:
    """Parse schema from a single SQLite database."""
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        table_names = [row[0] for row in cursor.fetchall()]

        tables = []
        for table_name in table_names:
            # Get column info using PRAGMA
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns_data = cursor.fetchall()

            # Get foreign key info
            cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
            fk_data = cursor.fetchall()
            fk_columns = {row[3]: f"{row[2]}({row[4]})" for row in fk_data}

            columns = []
            for col in columns_data:
                col_name = col[1]
                col_type = col[2] or "TEXT"
                is_pk = col[5] == 1
                is_fk = col_name in fk_columns
                references = fk_columns.get(col_name)

                columns.append(ColumnInfo(
                    name=col_name,
                    type=col_type,
                    is_primary_key=is_pk,
                    is_foreign_key=is_fk,
                    references=references
                ))

            tables.append(TableInfo(name=table_name, columns=columns))

        conn.close()

        db_name = db_path.stem
        return DatabaseSchema(
            name=db_name,
            path=str(db_path),
            tables=tables
        )

    except Exception as e:
        print(f"Error parsing {db_path}: {e}")
        return None


def parse_all_databases() -> Dict[str, DatabaseSchema]:
    """Parse schemas from all databases in TURSpider."""
    schemas = {}

    if not TURSPIDER_DB_PATH.exists():
        raise FileNotFoundError(f"TURSpider database path not found: {TURSPIDER_DB_PATH}")

    # Each database is in its own folder
    for db_folder in sorted(TURSPIDER_DB_PATH.iterdir()):
        if not db_folder.is_dir():
            continue

        # Find .sqlite file in the folder
        sqlite_files = list(db_folder.glob("*.sqlite"))
        if not sqlite_files:
            continue

        db_path = sqlite_files[0]
        schema = parse_database_schema(db_path)

        if schema:
            schemas[schema.name] = schema
            print(f"Parsed: {schema.name} ({len(schema.tables)} tables)")

    return schemas


def save_schemas_to_cache(schemas: Dict[str, DatabaseSchema]) -> None:
    """Save parsed schemas to cache directory."""
    cache_file = SCHEMA_CACHE_DIR / "schemas.json"

    # Convert to serializable format
    data = {}
    for name, schema in schemas.items():
        data[name] = {
            "name": schema.name,
            "path": schema.path,
            "tables": [
                {
                    "name": t.name,
                    "columns": [asdict(c) for c in t.columns]
                }
                for t in schema.tables
            ]
        }

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(schemas)} schemas to {cache_file}")


def load_schemas_from_cache() -> Dict[str, DatabaseSchema] | None:
    """Load schemas from cache if available."""
    cache_file = SCHEMA_CACHE_DIR / "schemas.json"

    if not cache_file.exists():
        return None

    with open(cache_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    schemas = {}
    for name, schema_data in data.items():
        tables = []
        for t in schema_data["tables"]:
            columns = [ColumnInfo(**c) for c in t["columns"]]
            tables.append(TableInfo(name=t["name"], columns=columns))

        schemas[name] = DatabaseSchema(
            name=schema_data["name"],
            path=schema_data["path"],
            tables=tables
        )

    return schemas


def get_schemas() -> Dict[str, DatabaseSchema]:
    """Get schemas from cache or parse from databases."""
    schemas = load_schemas_from_cache()

    if schemas is None:
        print("Parsing all database schemas...")
        schemas = parse_all_databases()
        save_schemas_to_cache(schemas)
    else:
        print(f"Loaded {len(schemas)} schemas from cache")

    return schemas


if __name__ == "__main__":
    # Test schema parsing
    schemas = get_schemas()
    print(f"\nTotal databases: {len(schemas)}")

    # Show example
    if "şarkıcı" in schemas:
        schema = schemas["şarkıcı"]
        print(f"\nExample - {schema.name}:")
        print(schema.to_schema_text())
