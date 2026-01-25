import re
from typing import Tuple


# Dangerous SQL keywords that are not allowed
DANGEROUS_KEYWORDS = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "CREATE",
    "ALTER",
    "TRUNCATE",
    "EXEC",
    "EXECUTE",
    "GRANT",
    "REVOKE",
    "ATTACH",
    "DETACH",
    "PRAGMA",
    "VACUUM",
    "REINDEX",
]

# SQL injection patterns
INJECTION_PATTERNS = [
    r";\s*--",           # Comment after semicolon
    r"--\s*$",           # Trailing comment
    r"/\*.*\*/",         # Block comment
    r"@@",               # System variables
    r"UNION\s+ALL\s+SELECT",  # Union injection
    r"OR\s+1\s*=\s*1",   # Always true condition
    r"OR\s+'1'\s*=\s*'1'",
]


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validate that SQL is SELECT-only and safe to execute.

    Args:
        sql: The SQL query to validate

    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is empty string
    """
    if not sql or not sql.strip():
        return False, "SQL sorgusu boş olamaz."

    # Normalize for checking
    sql_normalized = sql.strip().upper()

    # Rule 1: Must start with SELECT
    if not sql_normalized.startswith("SELECT"):
        return False, "Sadece SELECT sorguları desteklenmektedir."

    # Rule 2: Check for dangerous keywords
    for keyword in DANGEROUS_KEYWORDS:
        # Use word boundary to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_normalized):
            return False, f"Güvenlik ihlali: '{keyword}' ifadesi kullanılamaz."

    # Rule 3: No multiple statements (semicolon followed by non-whitespace)
    # Allow trailing semicolon but not multiple statements
    sql_trimmed = sql.strip()
    if sql_trimmed.endswith(";"):
        sql_trimmed = sql_trimmed[:-1]

    if ";" in sql_trimmed:
        return False, "Çoklu SQL ifadeleri desteklenmemektedir."

    # Rule 4: Check for SQL injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, sql_normalized):
            return False, "Güvenlik ihlali: Şüpheli SQL kalıbı tespit edildi."

    # Rule 5: No subqueries with dangerous operations
    # (Allow subqueries in general but check their content)
    subquery_match = re.findall(r'\(([^)]+)\)', sql_normalized)
    for subquery in subquery_match:
        for keyword in DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', subquery):
                return False, f"Güvenlik ihlali: Alt sorguda '{keyword}' kullanılamaz."

    return True, ""


def sanitize_for_display(sql: str) -> str:
    """
    Sanitize SQL for safe display (escape special characters).
    """
    if not sql:
        return ""

    # Basic HTML entity encoding for display
    sql = sql.replace("&", "&amp;")
    sql = sql.replace("<", "&lt;")
    sql = sql.replace(">", "&gt;")

    return sql


if __name__ == "__main__":
    # Test validation
    test_cases = [
        ("SELECT * FROM users", True),
        ("SELECT isim FROM şarkıcı", True),
        ("select name from table1", True),
        ("SELECT * FROM users; DROP TABLE users;", False),
        ("INSERT INTO users VALUES (1, 'test')", False),
        ("DELETE FROM users WHERE id = 1", False),
        ("UPDATE users SET name = 'test'", False),
        ("SELECT * FROM users WHERE 1=1 OR '1'='1'", False),
        ("SELECT * FROM users -- comment", False),
        ("", False),
        ("   ", False),
    ]

    print("SQL Validation Tests:")
    print("-" * 60)

    for sql, expected_valid in test_cases:
        is_valid, error = validate_sql(sql)
        status = "PASS" if is_valid == expected_valid else "FAIL"
        print(f"[{status}] {sql[:50]:<50}")
        if error:
            print(f"       Error: {error}")
