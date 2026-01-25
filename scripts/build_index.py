#!/usr/bin/env python3
"""
Build schema index for TURSpider databases.
Run this script once before starting the server.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from indexing.schema_parser import parse_all_databases, save_schemas_to_cache
from indexing.schema_indexer import SchemaIndexer


def main():
    print("=" * 60)
    print("TURSpider Schema Index Builder")
    print("=" * 60)

    # Step 1: Parse all database schemas
    print("\nStep 1: Parsing database schemas...")
    schemas = parse_all_databases()
    print(f"Parsed {len(schemas)} databases")

    # Step 2: Save to cache
    print("\nStep 2: Saving schemas to cache...")
    save_schemas_to_cache(schemas)

    # Step 3: Build ChromaDB index
    print("\nStep 3: Building ChromaDB index...")
    indexer = SchemaIndexer()
    indexer.build_index(schemas)

    print("\n" + "=" * 60)
    print("Index build complete!")
    print("=" * 60)

    # Test search
    print("\nTesting search functionality...")
    test_queries = [
        "Şarkıcıların isimleri nelerdir?",
        "Hastanedeki doktorlar",
        "Futbol takımları"
    ]

    for query in test_queries:
        results = indexer.search(query, top_k=3)
        print(f"\nQuery: {query}")
        for r in results:
            print(f"  - {r['name']} (similarity: {r['similarity']:.3f})")


if __name__ == "__main__":
    main()
