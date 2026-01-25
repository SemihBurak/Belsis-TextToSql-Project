import google.generativeai as genai
from typing import List, Dict, Any
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).parent.parent))
from config import GOOGLE_API_KEY, GEMMA_MODEL


class LLMService:
    def __init__(self):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not set. Please set it in .env file.")

        genai.configure(api_key=GOOGLE_API_KEY)
        self.model = genai.GenerativeModel(GEMMA_MODEL)

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Generate response from LLM."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=1024,
                )
            )
            return response.text.strip()
        except Exception as e:
            raise RuntimeError(f"LLM generation failed: {e}")

    def select_database(
        self,
        question: str,
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select the most appropriate database from candidates."""
        # Build candidate descriptions with full schema (including columns)
        candidate_descriptions = []
        for i, c in enumerate(candidates, 1):
            desc = f"{i}. {c['document']}"
            candidate_descriptions.append(desc)

        prompt = f"""Sen bir veritabanı seçim uzmanısın. Kullanıcının Türkçe sorusuna göre en uygun veritabanını seç.

## Aday Veritabanları:
{chr(10).join(candidate_descriptions)}

## Kullanıcı Sorusu:
{question}

## Görevin:
1. Soruyu dikkatlice analiz et
2. Soruda geçen anahtar kelimeleri bul (örn: satış, fiyat, isim, tarih, puan vb.)
3. Bu kelimelerin hangi veritabanının SÜTUNLARINDA bulunduğuna bak
5. En uygun veritabanını seç

Sadece veritabanı ismini yaz, başka bir şey yazma. Örnek: şarkıcı"""

        response = self.generate(prompt)

        # Clean response and find matching candidate
        db_name = response.strip().lower().replace('"', '').replace("'", "")

        # Try to find exact match
        for c in candidates:
            if c['name'].lower() == db_name:
                return c

        # Try partial match
        for c in candidates:
            if db_name in c['name'].lower() or c['name'].lower() in db_name:
                return c

        # Default to first candidate
        return candidates[0]

    def select_database_and_generate_sql(
        self,
        question: str,
        candidates: List[Dict[str, Any]],
        schemas: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combined: Select database AND generate SQL in one LLM call."""
        # Build candidate descriptions with FULL schema SQL
        candidate_descriptions = []
        for i, c in enumerate(candidates[:3], 1):  # Top 3 only to save tokens
            db_name = c['name']
            schema = schemas.get(db_name)
            if schema:
                schema_sql = schema.to_sql_schema()
                desc = f"""### {i}. Veritabanı: {db_name}
{schema_sql}
"""
            else:
                desc = f"### {i}. {c['document']}"
            candidate_descriptions.append(desc)

        prompt = f"""Sen bir Türkçe-SQL çeviri uzmanısın. Kullanıcının sorusuna göre:
1. En uygun veritabanını seç
2. SQL sorgusunu üret

## Aday Veritabanları ve Şemaları:
{chr(10).join(candidate_descriptions)}

## Kullanıcı Sorusu:
{question}

## Kurallar:
- SADECE SELECT sorgusu üret
- Tablo ve sütun isimlerini şemadaki gibi AYNEN kullan (Türkçe karakterler: ş, ı, ö, ü, ç, ğ)
- Şemada olmayan tablo/sütun KULLANMA
- Eğer istenen bilgi hiçbir şemada YOKSA: "VERI_YOK: [açıklama]" yaz

## Cevap Formatı (bu formatı AYNEN kullan):
VERITABANI: [veritabanı_ismi]
SQL: [sql_sorgusu]"""

        response = self.generate(prompt)
        
        # Parse response
        lines = response.strip().split('\n')
        db_name = None
        sql = None
        
        for line in lines:
            line = line.strip()
            if line.upper().startswith('VERITABANI:') or line.upper().startswith('VERİTABANI:'):
                db_name = line.split(':', 1)[1].strip().lower().replace('"', '').replace("'", "")
            elif line.upper().startswith('SQL:'):
                sql = line.split(':', 1)[1].strip()
            elif sql is None and line.upper().startswith('SELECT'):
                sql = line
        
        # If SQL spans multiple lines, get the rest
        if sql and not sql.endswith(';'):
            sql_start_idx = None
            for i, line in enumerate(lines):
                if 'SELECT' in line.upper():
                    sql_start_idx = i
                    break
            if sql_start_idx is not None:
                sql_lines = []
                for line in lines[sql_start_idx:]:
                    line = line.strip()
                    if line.upper().startswith('SQL:'):
                        line = line.split(':', 1)[1].strip()
                    sql_lines.append(line)
                    if ';' in line:
                        break
                sql = ' '.join(sql_lines)
        
        # Clean SQL
        if sql:
            sql = sql.replace('```', '').replace('`', '').strip()
            if sql.lower().startswith('sql'):
                sql = sql[3:].strip()
            if not sql.endswith(';'):
                sql += ';'
        
        # Find matching candidate
        selected = candidates[0]  # Default
        if db_name:
            for c in candidates:
                if c['name'].lower() == db_name or db_name in c['name'].lower():
                    selected = c
                    break
        
        return {
            "selected": selected,
            "sql": sql or "",
            "db_name": selected['name']
        }

    def generate_sql(
        self,
        question: str,
        schema_sql: str,
        db_name: str
    ) -> str:
        """Generate SQL query from natural language question."""
        prompt = f"""Sen bir Türkçe-SQL çeviri uzmanısın. Kullanıcının Türkçe sorusunu SQL sorgusuna çevir.

## Veritabanı: {db_name}

## Veritabanı Şeması:
{schema_sql}

## Kurallar:
1. SADECE SELECT sorgusu üret (INSERT, UPDATE, DELETE YASAK)
2. Tablo ve sütun isimlerini şemadaki gibi AYNEN kullan (Türkçe karakterlere dikkat et: ş, ı, ö, ü, ç, ğ)
3. Gerekirse JOIN, GROUP BY, ORDER BY, LIMIT kullan
4. Şemada olmayan tablo veya sütun KULLANMA
5. String karşılaştırmalarında büyük/küçük harf duyarsız karşılaştırma yap: LOWER(sütun) = LOWER('değer') veya sütun COLLATE NOCASE = 'değer'
6. ÖNEMLİ: Eğer kullanıcının sorduğu bilgi şemada YOKSA (örn: puan, skor, fiyat gibi sütunlar yoksa), sadece "VERI_YOK: [eksik bilgi]" yaz. Yakın bir şey üretme!

## Kullanıcı Sorusu:
{question}

## Cevap (SQL sorgusu VEYA "VERI_YOK: [açıklama]"):
```sql"""

        response = self.generate(prompt)

        # Extract SQL from response
        sql = response.strip()

        # Check if LLM says data is not available
        if "VERI_YOK" in sql.upper() or "VERİ_YOK" in sql.upper():
            # Extract the explanation if present
            if ":" in sql:
                explanation = sql.split(":", 1)[1].strip()
                return f"VERI_YOK: {explanation}"
            return "VERI_YOK: İstenen bilgi veritabanında mevcut değil."

        # Remove markdown code blocks - handle various formats
        # Format 1: ```sql\nSELECT...\n```
        # Format 2: SELECT...\n```
        # Format 3: ```\nSELECT...\n```

        # Remove closing ``` if present
        if "```" in sql:
            # Split by ``` and take the SQL part
            parts = sql.split("```")
            # Find the part that looks like SQL
            for part in parts:
                part = part.strip()
                # Remove 'sql' prefix if it's just a language identifier
                if part.lower().startswith("sql\n"):
                    part = part[4:].strip()
                elif part.lower() == "sql":
                    continue
                # Check if this part contains SELECT
                if part.upper().startswith("SELECT"):
                    sql = part
                    break
            else:
                # If no SELECT found, just clean up the first non-empty part
                sql = parts[0].strip()

        # Remove sql prefix if present (standalone)
        if sql.lower().startswith("sql\n"):
            sql = sql[4:].strip()
        elif sql.lower().startswith("sql "):
            sql = sql[4:].strip()

        # Clean up any remaining backticks
        sql = sql.replace("`", "").strip()

        # Ensure it ends with semicolon
        if sql and not sql.endswith(";"):
            sql += ";"

        return sql


# Singleton instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create the LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


if __name__ == "__main__":
    # Test LLM service
    try:
        llm = get_llm_service()
        print("LLM service initialized successfully")

        # Test generation
        response = llm.generate("Merhaba, nasılsın?")
        print(f"Test response: {response[:100]}...")
    except Exception as e:
        print(f"Error: {e}")
