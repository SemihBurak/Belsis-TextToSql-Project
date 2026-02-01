import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
TURSPIDER_DB_PATH = BASE_DIR / "TURSpider-database" / "database"
DATA_DIR = Path(__file__).parent / "data"
SCHEMA_CACHE_DIR = DATA_DIR / "schema_cache"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"

# Ensure directories exist
SCHEMA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

# Google AI Studio API
GOOGLE_API_KEY = "AIzaSyBoM3LawfUGMxyFFQUsefvTgoH6wORGaH4"

# Model settings
GEMMA_MODEL = "gemma-3-27b-it"  # Fast model with new API key

# Embedding model
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"

# Database detection settings
TOP_K_CANDIDATES = 5  # Number of candidate databases from semantic search

# SQL execution settings
SQL_TIMEOUT = 5  # seconds
MAX_RESULT_ROWS = 1000

# API settings
API_HOST = "0.0.0.0"
API_PORT = 8000
