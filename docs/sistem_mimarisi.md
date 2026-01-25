# 🏗️ FMS Text-to-SQL Sistem Mimarisi

## Senaryo: "Şarkıcıların ismini getirir misin?"

Bu dokümanda, kullanıcı bu soruyu sorduğunda sistemin **A'dan Z'ye** nasıl çalıştığını anlatıyorum.

---

## 📊 Genel Akış Diyagramları

### Diyagram 1: Frontend - Backend İletişimi

```mermaid
sequenceDiagram
    participant User as Kullanici
    participant Browser as Tarayici
    participant Vite as Vite Proxy
    participant API as FastAPI

    User->>Browser: Soru yazar
    Browser->>Vite: POST /api/chat
    Vite->>API: Forward to :8000
    API-->>Vite: JSON Response
    Vite-->>Browser: Response
    Browser-->>User: Sonuc goster
```

### Diyagram 2: Veritabani Tespiti

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant DD as DB Detector
    participant IDX as Indexer
    participant CHROMA as ChromaDB
    participant LLM as Gemini AI

    API->>DD: detect question
    DD->>IDX: search
    IDX->>CHROMA: Vector Search
    CHROMA-->>IDX: Candidates
    IDX-->>DD: Top 5
    DD->>LLM: select database
    LLM-->>DD: sarkici
    DD-->>API: schema
```

### Diyagram 3: SQL Uretimi ve Calistirma

```mermaid
sequenceDiagram
    participant API as FastAPI
    participant SG as SQL Generator
    participant LLM as Gemini AI
    participant SE as SQL Executor
    participant DB as SQLite

    API->>SG: generate
    SG->>LLM: prompt
    LLM-->>SG: SELECT query
    SG-->>API: validated SQL
    API->>SE: execute
    SE->>DB: query
    DB-->>SE: rows
    SE-->>API: result
```

---


# 🔵 BÖLÜM 1: FRONTEND

## Adım 1.1: Kullanıcı Soruyu Yazar

Kullanıcı tarayıcıda `http://localhost:5173` adresine gider ve input alanına yazar:

```
"Şarkıcıların ismini getirir misin?"
```

**Dosya:** `frontend/src/components/ChatInterface.tsx`

```tsx
// Kullanıcı "Gönder" butonuna tıkladığında
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  const question = input.trim();  // "Şarkıcıların ismini getirir misin?"
  
  if (!question || isLoading) return;

  // Kullanıcı mesajını state'e ekle (ekranda göster)
  const userMessage: Message = {
    id: Date.now().toString(),
    type: 'user',
    content: question,
    timestamp: new Date(),
  };
  setMessages((prev) => [...prev, userMessage]);
  setInput('');  // Input'u temizle
  setIsLoading(true);  // Loading spinner göster

  try {
    // ⭐ API'ye istek gönder
    const response = await sendQuestion(question);
    // ... sonuç işleme
  } catch (error) {
    // ... hata işleme
  }
};
```

---

## Adım 1.2: API İsteği Gönderilir

**Dosya:** `frontend/src/services/api.ts`

```typescript
import axios from 'axios';

const API_BASE = '/api';  // ⚠️ localhost:8000 DEĞİL!

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function sendQuestion(question: string): Promise<ChatResponse> {
  // POST /api/chat gönderilir
  // Body: { "question": "Şarkıcıların ismini getirir misin?" }
  const response = await api.post<ChatResponse>('/chat', { question });
  return response.data;
}
```

### HTTP İsteği (Raw):
```http
POST http://localhost:5173/api/chat HTTP/1.1
Host: localhost:5173
Content-Type: application/json

{
  "question": "Şarkıcıların ismini getirir misin?"
}
```

---

## Adım 1.3: Vite Proxy Yönlendirmesi

**Sorun:** Frontend `localhost:5173`'te, Backend `localhost:8000`'de. Farklı portlar!

**Çözüm:** Vite Dev Server proxy kullanır.

**Dosya:** `frontend/vite.config.ts`

```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {                           // "/api" ile başlayan istekler...
        target: 'http://localhost:8000',  // ...buraya yönlendirilir
        changeOrigin: true,               // Origin header'ı değiştirilir
      }
    }
  }
})
```

### Yönlendirme:
```
Tarayıcı Gönderir:  POST http://localhost:5173/api/chat
                              ↓
Vite Proxy:         POST http://localhost:8000/api/chat
                              ↓
FastAPI Alır:       @router.post("/chat")
```

---

# 🟢 BÖLÜM 2: BACKEND - FastAPI

## Adım 2.1: İstek FastAPI'ye Ulaşır

**Dosya:** `backend/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TURSpider Text-to-SQL API",
    description="Turkish natural language to SQL query chatbot",
    version="1.0.0"
)

# CORS ayarları (farklı origin'lerden gelen isteklere izin ver)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ı ekle
app.include_router(chat_router, prefix="/api", tags=["chat"])
```

### Uvicorn (ASGI Server):
```
[Uvicorn] ← HTTP İsteği geldi
    ↓
[FastAPI App] ← Route eşleştirme
    ↓
[/api/chat endpoint] ← Handler fonksiyonu çağrılır
```

---

## Adım 2.2: Chat Endpoint Handler

**Dosya:** `backend/routes/chat.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Request/Response modelleri
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


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Ana endpoint - Türkçe soru → SQL sonucu
    
    Flow:
    1. Detect the appropriate database
    2. Generate SQL query
    3. Validate and execute SQL
    4. Return results
    """
    question = request.question.strip()
    # → "Şarkıcıların ismini getirir misin?"

    if not question:
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    try:
        # ===== ADIM 1: VERİTABANI TESPİTİ =====
        detector = get_database_detector()
        db_name, schema, detection_info = detector.detect(question)
        # → db_name = "şarkıcı"
        # → schema = DatabaseSchema object
        
        # ===== ADIM 2: SQL ÜRET =====
        generator = get_sql_generator()
        sql_result = generator.generate(question, schema)
        # → sql_result = {
        #     "sql": "SELECT isim FROM şarkıcı;",
        #     "is_valid": True,
        #     "error": ""
        # }

        if not sql_result["is_valid"]:
            return ChatResponse(success=False, ...)

        # ===== ADIM 3: SQL ÇALIŞTIR =====
        executor = get_sql_executor()
        exec_result = executor.execute(schema.path, sql_result["sql"])
        # → exec_result = {
        #     "success": True,
        #     "columns": ["isim"],
        #     "rows": [["Ahmet"], ["Mehmet"], ...],
        #     "row_count": 8
        # }

        # ===== ADIM 4: SONUÇ DÖNDÜR =====
        return ChatResponse(
            success=True,
            question=question,
            database=db_name,
            sql=sql_result["sql"],
            columns=exec_result["columns"],
            rows=exec_result["rows"],
            row_count=exec_result["row_count"],
            detection_info=detection_info
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

# 🔴 BÖLÜM 3: VERİTABANI TESPİTİ

## Adım 3.1: DatabaseDetector Başlatılır

**Dosya:** `backend/services/database_detector.py`

```python
class DatabaseDetector:
    """İki aşamalı veritabanı tespiti: Semantic Search + LLM Confirmation"""

    def __init__(self):
        self.indexer = get_indexer()      # ChromaDB indexer
        self.llm = get_llm_service()       # Gemini AI
        self._schemas = None

    def detect(self, question: str) -> Tuple[str, DatabaseSchema, Dict]:
        """
        Soru için en uygun veritabanını tespit et.
        
        Returns:
            (database_name, schema, detection_info)
        """
        # Önce index'in build edildiğinden emin ol
        ensure_index_built()

        # ===== AŞAMA 1: SEMANTİK ARAMA =====
        candidates = self.indexer.search(question, top_k=5)
        # → [
        #     {"name": "atölye_bildiri", "similarity": 0.337},
        #     {"name": "akademisyen", "similarity": 0.333},
        #     {"name": "şarkıcı", "similarity": 0.329},  ← Doğru DB!
        #     {"name": "haber_bülteni", "similarity": 0.309},
        #     {"name": "suçlu", "similarity": 0.303}
        # ]

        if not candidates:
            raise ValueError("Uygun veritabanı bulunamadı.")

        # Eğer en yüksek similarity > 0.85 ise direkt kullan
        if candidates[0]['similarity'] > 0.85:
            selected = candidates[0]
            method = "semantic_search_high_confidence"
        else:
            # ===== AŞAMA 2: LLM ONAYI =====
            # Similarity düşük, LLM'e sor
            selected = self.llm.select_database(question, candidates)
            method = "llm_confirmation"

        # Schema'yı al
        db_name = selected['name']  # → "şarkıcı"
        schema = self.schemas.get(db_name)

        return db_name, schema, detection_info
```

---

## Adım 3.2: Semantic Search (ChromaDB)

**Dosya:** `backend/indexing/schema_indexer.py`

### ChromaDB Nedir?
ChromaDB bir **vektör veritabanıdır**. Metinleri sayısal vektörlere (embeddings) çevirip benzerlik araması yapar.

```python
class SchemaIndexer:
    def __init__(self):
        # Embedding modeli (metin → vektör)
        self.embedding_model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        # ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(CHROMA_DB_DIR),  # data/chroma_db/
        )

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Sorguya en benzer veritabanlarını bul."""
        
        # 1. Sorguyu vektöre çevir
        # "Şarkıcıların ismini getirir misin?"
        #     ↓
        # [0.123, -0.456, 0.789, ..., 0.321]  (384 boyutlu vektör)
        query_embedding = self.embedding_model.encode([query]).tolist()

        # 2. ChromaDB'de benzer vektörleri ara
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # 3. Sonuçları formatla
        candidates = []
        for i in range(len(results["ids"][0])):
            candidates.append({
                "name": results["ids"][0][i],           # "şarkıcı"
                "document": results["documents"][0][i], # Embedding text
                "distance": results["distances"][0][i], # 0.67 (düşük = iyi)
                "similarity": 1 - results["distances"][0][i]  # 0.33
            })

        return candidates
```

### Embedding Nasıl Çalışır?

```
┌─────────────────────────────────────────────────────────────┐
│  SORU: "Şarkıcıların ismini getirir misin?"                  │
│                           ↓                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │     SentenceTransformer Model                        │    │
│  │     (paraphrase-multilingual-MiniLM-L12-v2)         │    │
│  └─────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│  VEKTÖR: [0.123, -0.456, 0.789, ..., 0.321]                 │
│          ↑                                                   │
│          384 boyutlu sayı dizisi                            │
└─────────────────────────────────────────────────────────────┘
```

### ChromaDB'de Saklanan Veriler:

```
┌────────────────────────────────────────────────────────────────────┐
│  ChromaDB Collection: "turspider_schemas"                          │
├────────────────────────────────────────────────────────────────────┤
│  ID         │ Document                              │ Embedding    │
├─────────────┼───────────────────────────────────────┼──────────────┤
│  şarkıcı    │ "Veritabanı: şarkıcı | Tablolar:     │ [0.1, 0.2..] │
│             │  şarkı, şarkıcı | şarkıcı tablosu:   │              │
│             │  şarkıcı_no, isim, doğum_tarihi..."  │              │
├─────────────┼───────────────────────────────────────┼──────────────┤
│  hastane    │ "Veritabanı: hastane | Tablolar:     │ [0.3, 0.4..] │
│             │  doktor, hasta, bölüm..."            │              │
├─────────────┼───────────────────────────────────────┼──────────────┤
│  ...        │ ...                                   │ ...          │
└────────────────────────────────────────────────────────────────────┘
```

### Cosine Similarity Hesabı:

```
Query Vector:    [0.1, 0.2, 0.3, 0.4]
şarkıcı Vector:  [0.15, 0.22, 0.28, 0.38]

Cosine Similarity = (Q · V) / (|Q| × |V|)
                  = 0.329
```

---

## Adım 3.3: LLM Database Selection

Semantic search sonucu düşük confidence verdiğinde (< 0.85), LLM'e sorulur:

**Dosya:** `backend/services/llm_service.py`

```python
def select_database(self, question: str, candidates: List[Dict]) -> Dict:
    """LLM ile en uygun veritabanını seç."""
    
    # Candidate açıklamaları
    candidate_descriptions = []
    for i, c in enumerate(candidates, 1):
        desc = f"{i}. {c['name']}: Tablolar - {c['metadata']['tables']}"
        candidate_descriptions.append(desc)
    
    # Prompt oluştur
    prompt = f"""Sen bir veritabanı seçim uzmanısın.

## Aday Veritabanları:
1. atölye_bildiri: Tablolar - atölye, teslim, Kabul
2. akademisyen: Tablolar - makale, yazar, dergi...
3. şarkıcı: Tablolar - şarkı, şarkıcı
4. haber_bülteni: Tablolar - Gazeteci, olay...
5. suçlu: Tablolar - birey, suçlu

## Kullanıcı Sorusu:
Şarkıcıların ismini getirir misin?

## Görevin:
1. Soruyu analiz et
2. Soru hangi konuyla ilgili? (müzik, sağlık, spor...)
3. En uygun veritabanını seç

Sadece veritabanı ismini yaz: """

    # Gemini'ye gönder
    response = self.model.generate_content(prompt)
    # → "şarkıcı"

    # Eşleşen candidate'ı bul ve döndür
    for c in candidates:
        if c['name'].lower() == response.strip().lower():
            return c

    return candidates[0]  # Default ilk candidate
```

### Gemini API Çağrısı (Raw):

```http
POST https://generativelanguage.googleapis.com/v1beta/models/gemma-3-27b-it:generateContent
Authorization: Bearer AIzaSyCDHtUWzDiqIxO8hQQgQ4E3ffBNsOgKoD0

{
  "contents": [{
    "parts": [{
      "text": "Sen bir veritabanı seçim uzmanısın..."
    }]
  }],
  "generationConfig": {
    "temperature": 0.1,
    "maxOutputTokens": 1024
  }
}
```

---

# 🟡 BÖLÜM 4: SQL ÜRETİMİ

## Adım 4.1: SQL Generator

**Dosya:** `backend/services/sql_generator.py`

```python
class SQLGenerator:
    def __init__(self):
        self.llm = get_llm_service()

    def generate(self, question: str, schema: DatabaseSchema) -> Dict:
        """Soru ve şemadan SQL üret."""
        
        # Şemayı SQL formatına çevir
        schema_sql = schema.to_sql_schema()
        # → """
        # CREATE TABLE şarkıcı (
        #     şarkıcı_no INTEGER PRIMARY KEY,
        #     isim TEXT,
        #     doğum_tarihi TEXT,
        #     öz_varlık REAL,
        #     vatandaşlık TEXT,
        #     tür TEXT
        # );
        # CREATE TABLE şarkı (
        #     şarkı_no INTEGER PRIMARY KEY,
        #     şarkı_isim TEXT,
        #     şarkıcı_no INTEGER,
        #     satış INTEGER,
        #     en_yüksek_pozisyon INTEGER
        # );
        # """

        # LLM'den SQL al
        sql = self.llm.generate_sql(
            question=question,
            schema_sql=schema_sql,
            db_name=schema.name
        )
        # → "SELECT isim FROM şarkıcı;"

        # SQL'i doğrula
        is_valid, error = validate_sql(sql)
        
        return {
            "sql": sql,
            "is_valid": is_valid,
            "error": error
        }
```

---

## Adım 4.2: LLM SQL Generation

**Dosya:** `backend/services/llm_service.py`

```python
def generate_sql(self, question: str, schema_sql: str, db_name: str) -> str:
    """Türkçe soruyu SQL sorgusuna çevir."""
    
    prompt = f"""Sen bir Türkçe-SQL çeviri uzmanısın.

## Veritabanı: şarkıcı

## Veritabanı Şeması:
CREATE TABLE şarkıcı (
    şarkıcı_no INTEGER PRIMARY KEY,
    isim TEXT,
    doğum_tarihi TEXT,
    öz_varlık REAL,
    vatandaşlık TEXT,
    tür TEXT
);
CREATE TABLE şarkı (
    şarkı_no INTEGER PRIMARY KEY,
    şarkı_isim TEXT,
    şarkıcı_no INTEGER,
    satış INTEGER,
    en_yüksek_pozisyon INTEGER
);

## Kurallar:
1. SADECE SELECT sorgusu üret (INSERT, UPDATE, DELETE YASAK)
2. Tablo ve sütun isimlerini şemadaki gibi AYNEN kullan
3. Gerekirse JOIN, GROUP BY, ORDER BY, LIMIT kullan
4. Şemada olmayan tablo veya sütun KULLANMA

## Kullanıcı Sorusu:
Şarkıcıların ismini getirir misin?

## SQL Sorgusu:
```sql"""

    # Gemini'ye gönder
    response = self.model.generate_content(prompt)
    # → "SELECT isim FROM şarkıcı;"

    # Markdown code block'larını temizle
    sql = response.text.strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    # Noktalı virgül ekle
    if not sql.endswith(";"):
        sql += ";"
    
    return sql  # → "SELECT isim FROM şarkıcı;"
```

---

## Adım 4.3: SQL Validator

**Dosya:** `backend/services/sql_validator.py`

```python
import sqlparse

def validate_sql(sql: str) -> Tuple[bool, str]:
    """SQL sorgusunu güvenlik açısından doğrula."""
    
    if not sql or not sql.strip():
        return False, "SQL sorgusu boş."

    # Parse et
    try:
        parsed = sqlparse.parse(sql)
    except Exception as e:
        return False, f"SQL parse hatası: {e}"

    if not parsed:
        return False, "Geçersiz SQL."

    # Statement tipini kontrol et
    stmt = parsed[0]
    stmt_type = stmt.get_type()

    # SADECE SELECT izinli!
    allowed_types = ['SELECT']
    if stmt_type not in allowed_types:
        return False, f"Sadece SELECT sorgularına izin veriliyor. Tip: {stmt_type}"

    # Tehlikeli keyword kontrolü
    dangerous_keywords = [
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE',
        'CREATE', 'EXEC', 'EXECUTE'
    ]
    
    sql_upper = sql.upper()
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False, f"Tehlikeli keyword tespit edildi: {keyword}"

    return True, ""  # Geçerli!
```

---

# 🟣 BÖLÜM 5: SQL ÇALIŞTIRMA

## Adım 5.1: SQL Executor

**Dosya:** `backend/services/sql_executor.py`

```python
import sqlite3
from contextlib import contextmanager

class SQLExecutor:
    def __init__(self, timeout_seconds=5, max_rows=1000):
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

    def execute(self, db_path: str, sql: str) -> Dict:
        """SQL sorgusunu veritabanında çalıştır."""
        
        # db_path = "TURSpider database/database/şarkıcı/şarkıcı.sqlite"
        # sql = "SELECT isim FROM şarkıcı;"

        # 1. Tekrar doğrula (güvenlik)
        is_valid, error = validate_sql(sql)
        if not is_valid:
            return {"success": False, "error": error}

        # 2. Veritabanı var mı kontrol et
        if not Path(db_path).exists():
            return {"success": False, "error": f"DB bulunamadı: {db_path}"}

        try:
            # 3. READ-ONLY bağlantı aç (güvenlik!)
            conn = sqlite3.connect(
                f"file:{db_path}?mode=ro",  # ← READ-ONLY!
                uri=True,
                timeout=self.timeout_seconds
            )
            cursor = conn.cursor()

            # 4. Timeout ile çalıştır
            with timeout(self.timeout_seconds):
                cursor.execute(sql)
                rows = cursor.fetchmany(self.max_rows)
                # → [('Ahmet',), ('Mehmet',), ('Ayşe',), ...]

            # 5. Sütun isimlerini al
            columns = [desc[0] for desc in cursor.description]
            # → ['isim']

            # 6. Satırları listeye çevir
            rows_list = [list(row) for row in rows]
            # → [['Ahmet'], ['Mehmet'], ['Ayşe'], ...]

            conn.close()

            return {
                "success": True,
                "columns": columns,           # ['isim']
                "rows": rows_list,            # [['Ahmet'], ['Mehmet'], ...]
                "row_count": len(rows_list),  # 8
                "error": ""
            }

        except sqlite3.Error as e:
            return {"success": False, "error": f"DB hatası: {e}"}
```

### SQLite Bağlantı Detayları:

```
┌─────────────────────────────────────────────────────────────┐
│  sqlite3.connect("file:/path/to/şarkıcı.sqlite?mode=ro")   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  file:      → URI format kullan                             │
│  mode=ro    → READ-ONLY (yazma yasak!)                      │
│  uri=True   → URI parsing aktif                             │
│  timeout=5  → 5 saniye sonra timeout                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

# 🔵 BÖLÜM 6: RESPONSE DÖNÜŞÜ

## Adım 6.1: JSON Response Oluşturulur

```python
return ChatResponse(
    success=True,
    question="Şarkıcıların ismini getirir misin?",
    database="şarkıcı",
    sql="SELECT isim FROM şarkıcı;",
    columns=["isim"],
    rows=[
        ["Ahmet"],
        ["Mehmet"],
        ["Ayşe"],
        ["Fatma"],
        ["Ali"],
        ["Veli"],
        ["Zeynep"],
        ["Can"]
    ],
    row_count=8,
    error="",
    detection_info={
        "method": "llm_confirmation",
        "candidates": [...],
        "selected": {...}
    }
)
```

### HTTP Response:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
    "success": true,
    "question": "Şarkıcıların ismini getirir misin?",
    "database": "şarkıcı",
    "sql": "SELECT isim FROM şarkıcı;",
    "columns": ["isim"],
    "rows": [["Ahmet"], ["Mehmet"], ...],
    "row_count": 8,
    "error": "",
    "detection_info": {...}
}
```

---

## Adım 6.2: Frontend Sonucu Gösterir

**Dosya:** `frontend/src/components/ChatInterface.tsx`

```tsx
try {
  const response = await sendQuestion(question);
  // response = { success: true, sql: "SELECT...", rows: [...] }

  const assistantMessage: Message = {
    id: (Date.now() + 1).toString(),
    type: 'assistant',
    content: response.success
      ? `Veritabanı: ${response.database}`
      : response.error,
    timestamp: new Date(),
    response,  // Tüm response'u sakla
  };
  
  setMessages((prev) => [...prev, assistantMessage]);
  // → Ekranda tablo gösterilir
}
```

---

# 📊 ÖZET: TAM AKIŞ

```
 ┌─────────────────────────────────────────────────────────────────┐
 │  1. KULLANICI                                                    │
 │     "Şarkıcıların ismini getirir misin?"                        │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  2. FRONTEND (React)                                             │
 │     ChatInterface → api.ts → POST /api/chat                     │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  3. VITE PROXY                                                   │
 │     localhost:5173/api → localhost:8000/api                     │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  4. FASTAPI BACKEND                                              │
 │     routes/chat.py → @router.post("/chat")                      │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
                 ▼               ▼               ▼
 ┌───────────────────┐ ┌───────────────┐ ┌───────────────────┐
 │ 5. DB DETECTOR    │ │ 6. SQL GEN    │ │ 7. SQL EXECUTOR   │
 │                   │ │               │ │                   │
 │ ChromaDB Search   │ │ LLM → SQL     │ │ SQLite Execute    │
 │ LLM Confirm       │ │ Validator     │ │ Read-Only         │
 │                   │ │               │ │                   │
 │ → "şarkıcı"       │ │ → SELECT...   │ │ → rows, columns   │
 └───────────────────┘ └───────────────┘ └───────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  8. JSON RESPONSE                                                │
 │     { success, sql, columns, rows, ... }                        │
 └───────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
 ┌─────────────────────────────────────────────────────────────────┐
 │  9. FRONTEND RENDER                                              │
 │     Tablo olarak göster                                         │
 └─────────────────────────────────────────────────────────────────┘
```

---

# ⏱️ ZAMAN ÇİZELGESİ

| Adım | Süre (tahmini) | Açıklama |
|------|----------------|----------|
| Frontend → API | ~5ms | HTTP request gönderimi |
| Vite Proxy | ~1ms | Request forwarding |
| ChromaDB Search | ~50ms | Vector similarity search |
| LLM DB Selection | ~500ms | Gemini API call |
| LLM SQL Generation | ~800ms | Gemini API call |
| SQL Validation | ~5ms | Syntax check |
| SQLite Execute | ~10ms | Query execution |
| Total | **~1.5 saniye** | Ortalama response süresi |

---

Bu dokümanda sistem mimarisinin tamamını anlattım. Başka bir soru var mı? 🚀
