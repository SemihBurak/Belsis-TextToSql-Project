from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from routes.chat import router as chat_router
from config import API_HOST, API_PORT
from indexing.schema_indexer import ensure_index_built

# Create FastAPI app
app = FastAPI(
    title="TURSpider Text-to-SQL API",
    description="Turkish natural language to SQL query chatbot using TURSpider dataset",
    version="1.0.0"
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api", tags=["chat"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("Starting TURSpider Text-to-SQL API...")

    # Build schema index if not exists
    print("Checking schema index...")
    ensure_index_built()

    # Pre-warm embedding model (loads ~10s on first call, then cached)
    print("Pre-warming embedding model...")
    from indexing.schema_indexer import get_indexer
    indexer = get_indexer()
    # Do a dummy search to load the model
    indexer.search("test", top_k=1)
    print("Embedding model ready!")

    # Pre-warm LLM service
    print("Initializing LLM service...")
    from services.llm_service import get_llm_service
    get_llm_service()
    print("LLM service ready!")

    print("API ready!")


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "TURSpider Text-to-SQL API",
        "version": "1.0.0",
        "description": "Turkish natural language to SQL query chatbot",
        "endpoints": {
            "chat": "/api/chat",
            "databases": "/api/databases",
            "schema": "/api/database/{db_name}/schema"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
