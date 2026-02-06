from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Any, Dict
import time

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.sql_executor import get_sql_executor
from services.llm_service import get_llm_service
from indexing.schema_indexer import get_indexer, ensure_index_built
from indexing.schema_parser import get_schemas
from services.sql_validator import validate_sql
from config import TOP_K_CANDIDATES


router = APIRouter()


def calculate_confidence_score(
    similarity: float,
    sql_valid: bool,
    execution_success: bool,
    row_count: int
) -> float:
    """
    Calculate confidence score based on multiple factors.

    Returns:
        float: Confidence score between 0 and 100
    """
    # Weights for each factor
    SIMILARITY_WEIGHT = 0.5  # 50% - Most important
    SQL_VALIDITY_WEIGHT = 0.2  # 20%
    EXECUTION_WEIGHT = 0.2  # 20%
    RESULT_WEIGHT = 0.1  # 10%

    # Similarity score (0-1) -> (0-100)
    similarity_score = similarity * 100

    # SQL validity score
    sql_score = 100 if sql_valid else 0

    # Execution success score
    execution_score = 100 if execution_success else 0

    # Result score (has results)
    result_score = 100 if row_count > 0 else 50  # 50 points even if no results (query might be correct)

    # Weighted average
    confidence = (
        similarity_score * SIMILARITY_WEIGHT +
        sql_score * SQL_VALIDITY_WEIGHT +
        execution_score * EXECUTION_WEIGHT +
        result_score * RESULT_WEIGHT
    )

    # Clamp between 0 and 100
    return max(0.0, min(100.0, confidence))


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
    explanation: str = ""  # Açıklama metni
    confidence_score: float = 0.0  # Güven skoru (0-100)
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

    # Check if question contains modification keywords (DELETE, UPDATE, INSERT, etc.)
    question_upper = question.upper()
    modification_keywords = [
        "SİL", "SILL", "DELETE", "KALDIR",
        "GÜNCELLE", "UPDATE", "DEĞİŞTİR",
        "EKLE", "INSERT", "KAYDET", "YAZ",
        "OLUŞTUR", "CREATE", "YAP",
        "DROP", "DÜŞÜR"
    ]

    for keyword in modification_keywords:
        if keyword in question_upper:
            return ChatResponse(
                success=False,
                question=question,
                database="",
                sql="",
                columns=[],
                rows=[],
                row_count=0,
                confidence_score=0.0,  # Low confidence for blocked queries
                error="Üzgünüm, sadece veri sorgulama işlemlerini destekliyorum. Veri ekleme, güncelleme veya silme işlemleri yapamam. Başka nasıl yardımcı olabilirim?",
                detection_info={},
                timing={"detection": 0, "generation": 0, "execution": 0, "total": time.time() - total_start}
            )

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

        # Check if question is unclear/ambiguous
        if sql.startswith("BELIRSIZ"):
            clarification = sql.replace("BELIRSIZ:", "").strip()
            total_time = time.time() - total_start
            confidence = calculate_confidence_score(
                similarity=selected['similarity'],
                sql_valid=False,
                execution_success=False,
                row_count=0
            )
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql="",
                columns=[],
                rows=[],
                row_count=0,
                explanation="",
                confidence_score=confidence,
                error=f"❓ Sorunuz biraz belirsiz. {clarification}",
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": 0, "total": total_time}
            )

        # Check if question is irrelevant
        if sql.startswith("ALAKASIZ"):
            suggestion = sql.replace("ALAKASIZ:", "").strip()
            total_time = time.time() - total_start
            confidence = calculate_confidence_score(
                similarity=selected['similarity'],
                sql_valid=False,
                execution_success=False,
                row_count=0
            )
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql="",
                columns=[],
                rows=[],
                row_count=0,
                explanation="",
                confidence_score=confidence,
                error=f"Sanırım sorunuzu tam anlayamadım. Şunu mu sormak istediniz: '{suggestion}'? Veya bu konuda size nasıl yardımcı olabilirim?",
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": 0, "total": total_time}
            )

        # Check if LLM indicated data is not available
        if sql.startswith("VERI_YOK"):
            error_msg = sql.replace("VERI_YOK:", "").strip()
            total_time = time.time() - total_start
            confidence = calculate_confidence_score(
                similarity=selected['similarity'],
                sql_valid=False,
                execution_success=False,
                row_count=0
            )
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql="",
                columns=[],
                rows=[],
                row_count=0,
                explanation="",
                confidence_score=confidence,
                error=f"Bu veritabanında istenen bilgi bulunamadı: {error_msg}",
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": 0, "total": total_time}
            )

        # Validate SQL
        is_valid, error = validate_sql(sql)
        if not is_valid:
            total_time = time.time() - total_start
            confidence = calculate_confidence_score(
                similarity=selected['similarity'],
                sql_valid=False,
                execution_success=False,
                row_count=0
            )
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                explanation="",
                confidence_score=confidence,
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
            confidence = calculate_confidence_score(
                similarity=selected['similarity'],
                sql_valid=is_valid,
                execution_success=False,
                row_count=0
            )
            return ChatResponse(
                success=False,
                question=question,
                database=db_name,
                sql=sql,
                columns=[],
                rows=[],
                row_count=0,
                explanation="",
                confidence_score=confidence,
                error=exec_result["error"],
                detection_info=detection_info,
                timing={"detection": search_time, "generation": llm_time, "execution": step3_time, "total": total_time}
            )

        # Step 4: Generate explanation
        explanation_start = time.time()
        explanation = llm.generate_explanation(
            question=question,
            sql=sql,
            row_count=exec_result["row_count"],
            db_name=db_name
        )
        explanation_time = time.time() - explanation_start
        print(f"⏱️  [Step 4] Explanation Generation: {explanation_time:.2f}s")

        total_time = time.time() - total_start
        print(f"⏱️  [TOTAL] {total_time:.2f}s ✅")
        print(f"    └─ Breakdown: Search={search_time:.2f}s | LLM={llm_time:.2f}s | Execution={step3_time:.2f}s | Explanation={explanation_time:.2f}s")

        # Step 5: Calculate confidence score
        confidence = calculate_confidence_score(
            similarity=selected['similarity'],
            sql_valid=is_valid,
            execution_success=True,
            row_count=exec_result["row_count"]
        )

        # Step 6: Return success response
        return ChatResponse(
            success=True,
            question=question,
            database=db_name,
            sql=sql,
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            row_count=exec_result["row_count"],
            explanation=explanation,
            confidence_score=confidence,
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
