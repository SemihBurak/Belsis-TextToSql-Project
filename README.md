# TURSpider Text-to-SQL Chatbot

A Turkish natural language to SQL query chatbot using the TURSpider dataset (166 SQLite databases) and Gemma 3 27B API.

## Features

- Turkish natural language to SQL conversion
- Automatic database detection from 166 databases
- SELECT-only queries for security
- Modern React chat interface
- FastAPI backend

## Project Structure

```
projebels/
├── TURSpider database/     # 166 SQLite databases
│   └── database/
├── backend/                # Python FastAPI backend
│   ├── main.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   └── indexing/
├── frontend/               # React + TypeScript frontend
│   └── src/
├── scripts/
│   └── build_index.py
└── README.md
```

## Setup

### 1. Get Google AI Studio API Key

1. Go to https://aistudio.google.com/
2. Create an API key
3. Copy `.env.example` to `.env` and add your key:

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 2. Create Virtual Environment & Install Backend Dependencies

```bash
# From project root
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

### 3. Build Schema Index (First Time Only)

```bash
source venv/bin/activate
python scripts/build_index.py
```

### 4. Start Backend Server

```bash
source venv/bin/activate
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 5. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 6. Start Frontend Server

```bash
cd frontend
npm run dev
```

### 7. Open Browser

Go to http://localhost:5173

## Usage

Type a Turkish question in the chat interface. Examples:

- "Sarkicilarin isimleri nelerdir?"
- "Hangi hastanede en cok doktor var?"
- "Futbol takimlarinin puanlari nedir?"
- "En pahali ucuslar hangileri?"

The system will:
1. Detect the appropriate database
2. Generate SQL query
3. Execute and display results

## API Endpoints

- `POST /api/chat` - Send a question and get SQL results
- `GET /api/databases` - List all available databases
- `GET /api/database/{name}/schema` - Get schema for a specific database

## Security

- Only SELECT queries are allowed
- SQL validation blocks INSERT, UPDATE, DELETE, DROP, etc.
- Databases are opened in read-only mode
- Query timeout protection

## Technologies

- **Backend**: Python, FastAPI, SQLite
- **Frontend**: React, TypeScript, Tailwind CSS, Vite
- **LLM**: Gemma 3 27B via Google AI Studio
- **Vector DB**: ChromaDB with multilingual embeddings
- **Dataset**: TURSpider (Turkish Text-to-SQL)
