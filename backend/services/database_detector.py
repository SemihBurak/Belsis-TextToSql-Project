from typing import Dict, Any, Tuple
from pathlib import Path
import time

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import TOP_K_CANDIDATES
from indexing.schema_indexer import get_indexer, ensure_index_built
from indexing.schema_parser import get_schemas, DatabaseSchema
from services.llm_service import get_llm_service


class DatabaseDetector:
    """Two-stage database detection: semantic search + LLM confirmation."""

    def __init__(self):
        self.indexer = get_indexer()
        self.llm = get_llm_service()
        self._schemas = None

    @property
    def schemas(self) -> Dict[str, DatabaseSchema]:
        if self._schemas is None:
            self._schemas = get_schemas()
        return self._schemas

    def detect(self, question: str) -> Tuple[str, DatabaseSchema, Dict[str, Any]]:
        """
        Detect the most appropriate database for the given question.

        Returns:
            Tuple of (database_name, schema, detection_info)
        """
        # Ensure index is built
        ensure_index_built()

        # Stage 1: Semantic search for candidate databases
        search_start = time.time()
        candidates = self.indexer.search(question, top_k=TOP_K_CANDIDATES)
        search_time = time.time() - search_start
        print(f"    📊 Semantic search: {search_time:.2f}s (top similarity: {candidates[0]['similarity']:.3f})")

        if not candidates:
            raise ValueError("Uygun veritabanı bulunamadı.")

        # If top candidate has very high similarity, use it directly
        if candidates[0]['similarity'] > 0.85:
            selected = candidates[0]
            detection_info = {
                "method": "semantic_search_high_confidence",
                "candidates": candidates,
                "selected": selected,
                "timing": {"search": search_time, "llm": 0}
            }
            print(f"    ✅ High confidence match - skipped LLM")
        else:
            # Stage 2: LLM confirmation
            llm_start = time.time()
            selected = self.llm.select_database(question, candidates)
            llm_time = time.time() - llm_start
            print(f"    🤖 LLM database selection: {llm_time:.2f}s")
            detection_info = {
                "method": "llm_confirmation",
                "candidates": candidates,
                "selected": selected,
                "timing": {"search": search_time, "llm": llm_time}
            }

        # Get full schema
        db_name = selected['name']
        schema = self.schemas.get(db_name)

        if schema is None:
            raise ValueError(f"Veritabanı şeması bulunamadı: {db_name}")

        return db_name, schema, detection_info


# Singleton instance
_detector = None


def get_database_detector() -> DatabaseDetector:
    """Get or create the database detector instance."""
    global _detector
    if _detector is None:
        _detector = DatabaseDetector()
    return _detector


if __name__ == "__main__":
    # Test database detection
    detector = get_database_detector()

    test_questions = [
        "Şarkıcıların isimleri nelerdir?",
        "Hangi hastanede en çok doktor var?",
        "Futbol takımlarının puanları nedir?",
        "En pahalı uçuşlar hangileri?"
    ]

    for q in test_questions:
        print(f"\nQuestion: {q}")
        try:
            db_name, schema, info = detector.detect(q)
            print(f"  Detected DB: {db_name}")
            print(f"  Method: {info['method']}")
            print(f"  Tables: {', '.join(schema.get_table_names())}")
        except Exception as e:
            print(f"  Error: {e}")
