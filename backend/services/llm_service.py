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

    def generate(self, prompt: str, temperature: float = 0.0) -> str:
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

## ZORUNLU ADIMLAR (İÇİNDE TAKİP ET, KULLANICIYA GÖSTERME):
ADIM 1: Soruda geçen TÜM anahtar kelimeleri/kavramları listele (sadece zihninde)
ADIM 2: Her kavram için şemadaki sütunlarda TAM EŞLEŞMEYİ kontrol et (sadece zihninde)
ADIM 3: Eğer HERHANGI BIR kavram şemada YOKSA veya FARKLI bir kelimeyse -> BELIRSIZ dön (kullanıcıya sadece düzeltilmiş soruyu öner, teknik detay verme)
ADIM 4: Eğer tüm kavramlar eşleşiyorsa -> SQL oluştur

ÖNEMLİ: Bu adımları kullanıcıya ASLA gösterme! Sadece BELIRSIZ durumunda kısa ve net bir öneri ver.

## KATKI SEMANTİK KURALLAR (ASLA İHLAL ETME):
❌ YANLIŞ ÖRNEKLER (ASLA YAPMA):
1. Soru: "Bankadaki mal varlığı en yüksek kimdir?"
   → Şemada "banka", "bankadaki", "mal varlığı" kelimesi YOK, sadece "öz_varlık" var
   → "bankadaki mal varlığı" ≠ "öz_varlık" (FARKLI KAVRAMLAR!)
   → DOĞRU CEVAP: BELIRSIZ: Serveti en yüksek sanatçı kimdir?
   → YANLIŞ CEVAP: SELECT ... ORDER BY öz_varlık (BU HALÜSINASYON!)
   → YANLIŞ CEVAP: Teknik adımları/şema detaylarını göstermek (KULLANICIYA TEKNİK DETAY VERME!)

2. Soru: "Banka hesabındaki para miktarı en yüksek kimdir?"
   → Şemada "banka", "hesap", "para" kelimesi YOK
   → DOĞRU CEVAP: BELIRSIZ: Ne sormak istediniz?
   → YANLIŞ CEVAP: Herhangi bir SQL üretmek (BU HALÜSINASYON!)

3. Soru: "Banka bakiyesi en yüksek kimdir?"
   → Şemada "banka", "bakiye" kelimesi YOK
   → DOĞRU CEVAP: BELIRSIZ: Lütfen sorunuzu daha net belirtin.
   → YANLIŞ CEVAP: SQL üretmek (BU HALÜSINASYON!)

4. Soru: "Maaşı en yüksek kimdir?" (ama şemada "maaş" yok, sadece "gelir" var)
   → Şemada "maaş" YOK, sadece "gelir" var
   → "maaş" ≠ "gelir" (benzer ama AYNI DEĞİL!)
   → DOĞRU CEVAP: BELIRSIZ: Geliri en yüksek olanı mı sormak istediniz?
   → YANLIŞ CEVAP: SELECT ... ORDER BY gelir (BU HALÜSINASYON!)

✅ DOĞRU ÖRNEKLER:
1. Soru: "Serveti en yüksek sanatçı kimdir?"
   → Şemada "öz_varlık" VAR
   → "servet" = "öz_varlık" (EŞ ANLAMLI, şemada var)
   → DOĞRU: SELECT isim FROM şarkıcı ORDER BY öz_varlık DESC LIMIT 1;

2. Soru: "Öz varlığı en yüksek kimdir?"
   → Şemada "öz_varlık" VAR
   → "öz varlığı" = "öz_varlık" (TAM EŞLEŞİYOR)
   → DOĞRU: SELECT isim FROM şarkıcı ORDER BY öz_varlık DESC LIMIT 1;

## Ek Kurallar:
- SADECE SELECT sorgusu üret
- Tablo ve sütun isimlerini şemadaki gibi AYNEN kullan (Türkçe karakterler: ş, ı, ö, ü, ç, ğ)
- ÖNEMLİ: Şemada OLMAYAN tablo veya sütun ASLA KULLANMA. Uydurma, varsayma!
- ÖNEMLİ: Birden fazla tablo gerekiyorsa MUTLAKA JOIN kullan (INNER JOIN, LEFT JOIN vb.)
- Kabul edilebilir genel eş anlamlılar: satış≈sipariş, müşteri≈alıcı, ürün≈mal, isim≈ad, sayı≈miktar≈adet, servet≈öz_varlık
- UYARI: Eş anlamlılar dışındaki tüm kavramlar şemadaki KELIMELERLE TAM EŞLEŞMELİ!

## Cevap Formatı (bu formatı AYNEN kullan):
VERITABANI: [veritabanı_ismi]
SQL: [sql_sorgusu]

VEYA belirsizse (TERCIH ET!):
BELIRSIZ: [Düzeltilmiş soru önerin - kısa ve net, teknik detay YOK]
Örnek: BELIRSIZ: Serveti en yüksek sanatçı kimdir?

VEYA alakasız soruysa:
ALAKASIZ: [önerilen yorum]"""

        response = self.generate(prompt)

        # Check if question is unclear/ambiguous
        if "BELIRSIZ" in response.upper():
            # Extract the clarification question
            clarification = response
            if ":" in response:
                clarification = response.split(":", 1)[1].strip()
            return {
                "selected": candidates[0],
                "sql": f"BELIRSIZ: {clarification}",
                "db_name": candidates[0]['name']
            }

        # Check if question is irrelevant
        if "ALAKASIZ" in response.upper() or "ALAKASIZ:" in response.upper():
            # Extract the suggestion
            suggestion = response
            if ":" in response:
                suggestion = response.split(":", 1)[1].strip()
            return {
                "selected": candidates[0],
                "sql": f"ALAKASIZ: {suggestion}",
                "db_name": candidates[0]['name']
            }

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

## ZORUNLU ADIMLAR (İÇİNDE TAKİP ET, KULLANICIYA GÖSTERME):
ADIM 1: Soruda geçen TÜM anahtar kelimeleri/kavramları listele (sadece zihninde)
ADIM 2: Her kavram için şemadaki sütunlarda TAM EŞLEŞMEYİ kontrol et (sadece zihninde)
ADIM 3: Eğer HERHANGI BIR kavram şemada YOKSA veya FARKLI bir kelimeyse -> BELIRSIZ dön (kullanıcıya sadece düzeltilmiş soruyu öner, teknik detay verme)
ADIM 4: Eğer tüm kavramlar eşleşiyorsa -> SQL oluştur

ÖNEMLİ: Bu adımları kullanıcıya ASLA gösterme! Sadece BELIRSIZ durumunda kısa ve net bir öneri ver.

## KATKI SEMANTİK KURALLAR (ASLA İHLAL ETME):
❌ YANLIŞ ÖRNEKLER (ASLA YAPMA):
1. Soru: "Bankadaki mal varlığı en yüksek kimdir?"
   → Şemada "banka", "bankadaki", "mal varlığı" kelimesi YOK, sadece "öz_varlık" var
   → "bankadaki mal varlığı" ≠ "öz_varlık" (FARKLI KAVRAMLAR!)
   → DOĞRU CEVAP: BELIRSIZ: Serveti en yüksek sanatçı kimdir?
   → YANLIŞ CEVAP: SELECT ... ORDER BY öz_varlık (BU HALÜSINASYON!)
   → YANLIŞ CEVAP: Teknik adımları/şema detaylarını göstermek (KULLANICIYA TEKNİK DETAY VERME!)

2. Soru: "Banka hesabındaki para miktarı en yüksek kimdir?"
   → Şemada "banka", "hesap", "para" kelimesi YOK
   → DOĞRU CEVAP: BELIRSIZ: Ne sormak istediniz?
   → YANLIŞ CEVAP: Herhangi bir SQL üretmek (BU HALÜSINASYON!)

3. Soru: "Banka bakiyesi en yüksek kimdir?"
   → Şemada "banka", "bakiye" kelimesi YOK
   → DOĞRU CEVAP: BELIRSIZ: Lütfen sorunuzu daha net belirtin.
   → YANLIŞ CEVAP: SQL üretmek (BU HALÜSINASYON!)

4. Soru: "Maaşı en yüksek kimdir?" (ama şemada "maaş" yok, sadece "gelir" var)
   → Şemada "maaş" YOK, sadece "gelir" var
   → "maaş" ≠ "gelir" (benzer ama AYNI DEĞİL!)
   → DOĞRU CEVAP: BELIRSIZ: Geliri en yüksek olanı mı sormak istediniz?
   → YANLIŞ CEVAP: SELECT ... ORDER BY gelir (BU HALÜSINASYON!)

✅ DOĞRU ÖRNEKLER:
1. Soru: "Serveti en yüksek sanatçı kimdir?"
   → Şemada "öz_varlık" VAR
   → "servet" = "öz_varlık" (EŞ ANLAMLI, şemada var)
   → DOĞRU: SELECT isim FROM şarkıcı ORDER BY öz_varlık DESC LIMIT 1;

2. Soru: "Öz varlığı en yüksek kimdir?"
   → Şemada "öz_varlık" VAR
   → "öz varlığı" = "öz_varlık" (TAM EŞLEŞİYOR)
   → DOĞRU: SELECT isim FROM şarkıcı ORDER BY öz_varlık DESC LIMIT 1;

## Ek Kurallar:
1. SADECE SELECT sorgusu üret (INSERT, UPDATE, DELETE YASAK)
2. Tablo ve sütun isimlerini şemadaki gibi AYNEN kullan (Türkçe karakterlere dikkat et: ş, ı, ö, ü, ç, ğ)
3. Gerekirse JOIN, GROUP BY, ORDER BY, LIMIT kullan
4. ÖNEMLİ: Birden fazla tablo gerekiyorsa MUTLAKA JOIN kullan (INNER JOIN, LEFT JOIN vb.)
5. ÖNEMLİ: Şemada OLMAYAN tablo veya sütun ASLA KULLANMA. Uydurma, varsayma!
6. String karşılaştırmalarında büyük/küçük harf duyarsız karşılaştırma yap: LOWER(sütun) = LOWER('değer')
7. Kabul edilebilir genel eş anlamlılar: satış≈sipariş, müşteri≈alıcı, ürün≈mal, isim≈ad, sayı≈miktar≈adet, servet≈öz_varlık
8. UYARI: Eş anlamlılar dışındaki tüm kavramlar şemadaki KELIMELERLE TAM EŞLEŞMELİ!

## Kullanıcı Sorusu:
{question}

## Cevap (SQL sorgusu VEYA "BELIRSIZ/VERI_YOK/ALAKASIZ: [açıklama]"):
```sql"""

        response = self.generate(prompt)

        # Extract SQL from response
        sql = response.strip()

        # Check if question is unclear/ambiguous
        if "BELIRSIZ" in sql.upper():
            # Extract the clarification question
            if ":" in sql:
                clarification = sql.split(":", 1)[1].strip()
                return f"BELIRSIZ: {clarification}"
            return "BELIRSIZ: Sorunuz net değil, lütfen daha açık bir şekilde sorun."

        # Check if question is irrelevant
        if "ALAKASIZ" in sql.upper():
            # Extract the suggestion if present
            if ":" in sql:
                suggestion = sql.split(":", 1)[1].strip()
                return f"ALAKASIZ: {suggestion}"
            return "ALAKASIZ: Sorunuz veritabanlarıyla alakalı değil gibi görünüyor."

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

    def generate_explanation(
        self,
        question: str,
        sql: str,
        row_count: int,
        db_name: str
    ) -> str:
        """Generate a natural language explanation of the query results."""
        prompt = f"""Sen bir veritabanı asistanısın. Kullanıcının sorusuna verdiğin cevabı açıkla.

## Kullanıcı Sorusu:
{question}

## Kullanılan Veritabanı:
{db_name}

## Çalıştırılan SQL Sorgusu:
{sql}

## Sonuç:
{row_count} kayıt bulundu.

## Görevin:
Kullanıcıya KISA ve NET bir açıklama yaz. Sadece şu formatlardan birini kullan:

- Eğer sonuç varsa (row_count > 0):
  "Sorduğunuz sorunun cevabı:"
  VEYA
  "İşte [soruyla ilgili özet] sonuçları:"
  VEYA
  "[X] adet kayıt bulundu:"

- Eğer sonuç yoksa (row_count = 0):
  "Üzgünüm, bu kriterlere uygun sonuç bulunamadı."
  VEYA
  "[şema/veritabanı] veritabanında bu bilgi bulunamadı."

SADECE açıklama metnini yaz, başka bir şey ekleme. Maksimum 1 cümle olsun."""

        explanation = self.generate(prompt, temperature=0.3)
        return explanation.strip()


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
