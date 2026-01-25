from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
import time

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.database_detector import get_database_detector
from services.sql_generator import get_sql_generator
from services.sql_executor import get_sql_executor
from services.llm_service import get_llm_service
from indexing.schema_indexer import get_indexer, ensure_index_built
from indexing.schema_parser import get_schemas
from services.sql_validator import validate_sql
from config import TOP_K_CANDIDATES


router = APIRouter()


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    success: bool
    question: str
    database: str
    sql: str
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    error: str = ""
    detection_info: Dict[str, Any] = {}
    timing: Dict[str, float] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a Turkish natural language question and return SQL query results.
    
    OPTIMIZED Flow (Single LLM Call):
    1. Semantic search for candidate databases
    2. Combined LLM call: Select DB + Generate SQL
    3. Validate and execute SQL
    4. Return results
    """
    total_start = time.time()
    question = request.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    try:
        # Step 1: Semantic search for candidates
        ensure_index_built()
        indexer = get_indexer()
        schemas = get_schemas()
        
        search_start = time.time()
        candidates = indexer.search(question, top_k=TOP_K_CANDIDATES)
        search_time = time.time() - search_start
        print(f"    📊 Semantic search: {search_time:.2f}s (top similarity: {candidates[0]['similarity']:.3f})")

        if not candidates:
            raise ValueError("Uygun veritabanı bulunamadı.")

        # Step 2: Combined LLM call - Select DB + Generate SQL in ONE call
        llm_start = time.time()
        llm = get_llm_service()
        result = llm.select_database_and_generate_sql(question, candidates, schemas)
        llm_time = time.time() - llm_start
        print(f"    🤖 LLM (DB selection + SQL generation): {llm_time:.2f}s")
        
        db_name = result["db_name"]
        sql = result["sql"]
        selected = result["selected"]
        
        # Get schema for execution
        schema = schemas.get(db_name)
        if schema is None:
            raise ValueError(f"Veritabanı şeması bulunamadı: {db_name}")
        
        step1_time = search_time + llm_time  # Combined time for detection+generation
        
        detection_info = {
            "method": "combined_llm_call",
            "candidates": candidates,
            "selected": selected,
            "timing": {"search": search_time, "llm": llm_time}
        }
        
        print(f"⏱️  [Step 1+2] DB Detection + SQL Generation: {step1_time:.2f}s")

        # Check if LLM indicated data is not available
        if sql.startswith("VERI_YOK"):
            error_msg = sql.replace("VERI_YOK:", "").strip()
            total_time = time.time() - total_start
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql="",
                columns=[],
                rows=[],
                row_count=0,
                error=f"Bu veritabanında istenen bilgi bulunamadı: {error_msg}",
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": 0, "total": total_time}
            )

        # Validate SQL
        is_valid, error = validate_sql(sql)
        if not is_valid:
            total_time = time.time() - total_start
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                error=error,
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": 0, "total": total_time}
            )

        # Step 3: Execute SQL
        step3_start = time.time()
        executor = get_sql_executor()
        exec_result = executor.execute(schema.path, sql)
        step3_time = time.time() - step3_start
        print(f"⏱️  [Step 3] SQL Execution: {step3_time:.2f}s")

        total_time = time.time() - total_start
        print(f"⏱️  [TOTAL] {total_time:.2f}s ✅")
        print(f"    └─ Breakdown: Search={search_time:.2f}s | LLM={llm_time:.2f}s | Execution={step3_time:.2f}s")

        if not exec_result["success"]:
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                error=exec_result["error"],
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": step3_time, "total": total_time}
            )

        # Step 4: Return success response
        return ChatResponse(
            success=True,
            question=question,
            database=db_name,
            sql=sql,
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            row_count=exec_result["row_count"],
            error="",
            detection_info=detection_info,
            timing={"detection": search_time, "generation": llm_time, "execution": step3_time, "total": total_time}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sunucu hatası: {str(e)}")


@router.get("/databases")
async def list_databases():
    """List all available databases."""
    from indexing.schema_parser import get_schemas

    schemas = get_schemas()

    databases = []
    for name, schema in schemas.items():
        databases.append({
            "name": name,
            "tables": schema.get_table_names(),
            "table_count": len(schema.tables)
        })

    return {
        "count": len(databases),
        "databases": sorted(databases, key=lambda x: x["name"])
    }


@router.get("/database/{db_name}/schema")
async def get_database_schema(db_name: str):
    """Get schema for a specific database."""
    from indexing.schema_parser import get_schemas

    schemas = get_schemas()

    if db_name not in schemas:
        raise HTTPException(status_code=404, detail=f"Veritabanı bulunamadı: {db_name}")

    schema = schemas[db_name]

    return {
        "name": schema.name,
        "path": schema.path,
        "schema_text": schema.to_schema_text(),
        "schema_sql": schema.to_sql_schema(),
        "tables": [
            {
                "name": t.name,
                "columns": [
                    {
                        "name": c.name,
                        "type": c.type,
                        "is_primary_key": c.is_primary_key,
                        "is_foreign_key": c.is_foreign_key,
                        "references": c.references
                    }
                    for c in t.columns
                ]
            }
            for t in schema.tables
        ]
    }
