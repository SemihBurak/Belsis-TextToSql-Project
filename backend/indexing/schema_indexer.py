import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import Dict, List
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import CHROMA_DB_DIR, EMBEDDING_MODEL, TOP_K_CANDIDATES
from indexing.schema_parser import DatabaseSchema, get_schemas


# Collection name for database schemas
COLLECTION_NAME = "turspider_schemas"


class SchemaIndexer:
    def __init__(self):
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def _create_embedding_text(self, schema: DatabaseSchema) -> str:
        """Create text representation of schema for embedding."""
        parts = [
            f"Veritabanı: {schema.name}",
            f"Tablolar: {', '.join(schema.get_table_names())}",
        ]

        # Add column information
        for table in schema.tables:
            col_names = [c.name for c in table.columns]
            parts.append(f"{table.name} tablosu: {', '.join(col_names)}")

        return " | ".join(parts)

    def _prepare_passage(self, text: str) -> str:
        """Prepare text for E5 model embedding (passage/document)."""
        return f"passage: {text}"

    def _prepare_query(self, text: str) -> str:
        """Prepare text for E5 model embedding (query)."""
        return f"query: {text}"

    def build_index(self, schemas: Dict[str, DatabaseSchema]) -> None:
        """Build ChromaDB index from database schemas."""
        print(f"Building index for {len(schemas)} databases...")

        # Clear existing collection
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

        self._collection = self.client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        # Prepare data for indexing
        ids = []
        documents = []
        metadatas = []

        for name, schema in schemas.items():
            embedding_text = self._create_embedding_text(schema)

            ids.append(name)
            documents.append(embedding_text)
            metadatas.append({
                "name": schema.name,
                "path": schema.path,
                "tables": ",".join(schema.get_table_names()),
                "table_count": len(schema.tables)
            })

        # Generate embeddings with E5 passage prefix
        passages = [self._prepare_passage(doc) for doc in documents]
        embeddings = self.embedding_model.encode(passages).tolist()

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        print(f"Indexed {len(ids)} database schemas")

    def search(self, query: str, top_k: int = TOP_K_CANDIDATES) -> List[Dict]:
        """Search for similar database schemas given a query."""
        # Generate query embedding with E5 query prefix
        query_with_prefix = self._prepare_query(query)
        query_embedding = self.embedding_model.encode([query_with_prefix]).tolist()

        # Search in collection
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        candidates = []
        for i in range(len(results["ids"][0])):
            candidates.append({
                "name": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
                "similarity": 1 - results["distances"][0][i]  # Convert distance to similarity
            })

        return candidates

    def is_indexed(self) -> bool:
        """Check if schemas are already indexed."""
        try:
            count = self.collection.count()
            return count > 0
        except Exception:
            return False


# Singleton instance
_indexer = None


def get_indexer() -> SchemaIndexer:
    """Get or create the schema indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = SchemaIndexer()
    return _indexer


def ensure_index_built() -> None:
    """Ensure the schema index is built."""
    indexer = get_indexer()

    if not indexer.is_indexed():
        print("Index not found, building...")
        schemas = get_schemas()
        indexer.build_index(schemas)
    else:
        print(f"Index already exists with {indexer.collection.count()} entries")


if __name__ == "__main__":
    # Build or verify index
    ensure_index_built()

    # Test search
    indexer = get_indexer()

    test_queries = [
        "Şarkıcıların isimleri nelerdir?",
        "Hangi hastanede en çok doktor var?",
        "Futbol takımlarının puanları",
        "Uçuş bilgileri"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        results = indexer.search(query, top_k=3)
        for r in results:
            print(f"  - {r['name']} (similarity: {r['similarity']:.3f})")
