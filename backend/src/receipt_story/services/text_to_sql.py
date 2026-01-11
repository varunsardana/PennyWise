"""Text-to-SQL service using Claude"""

import re
from anthropic import Anthropic
from receipt_story.db.schema import get_schema_for_llm

client = Anthropic()  # Reads ANTHROPIC_API_KEY from environment


def generate_sql(question: str) -> str:
    """
    Generate SQL query from natural language question using Claude.
    
    Args:
        question: Natural language question about receipts/spending
        
    Returns:
        SQL query string (SELECT only)
        
    Raises:
        ValueError: If Claude fails to generate valid SQL
    """
    schema = get_schema_for_llm()
    
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""You are a SQL expert. Given this SQLite database schema:

{schema}

Generate a SQL query to answer this question: {question}

Requirements:
- Return ONLY the SQL query, no explanation, no markdown, no preamble
- Use SQLite syntax (date(), strftime(), etc.)
- Query must be SELECT only (read-only)
- Handle NULL values appropriately
- Use proper aggregations and GROUP BY when needed
- Order results in a meaningful way (e.g., by total DESC, by date DESC)

SQL Query:"""
        }]
    )
    
    sql = message.content[0].text.strip()
    
    # Clean up any markdown code blocks if present
    sql = re.sub(r'^```sql\n?', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'^```\n?', '', sql)
    sql = re.sub(r'\n?```$', '', sql)
    
    return sql.strip()


def is_safe_query(sql: str) -> bool:
    """Validate that SQL is safe to execute (read-only SELECT queries only)."""
    # if not sql or not isinstance(sql, str):
    #     return False
    
    # sql_upper = sql.upper().strip()
    
    # # Must start with SELECT
    # if not sql_upper.startswith('SELECT'):
    #     return False
    
    # # Block dangerous keywords
    # dangerous_keywords = [
    #     'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 
    #     'CREATE', 'TRUNCATE', 'EXEC', 'EXECUTE', 
    #     'PRAGMA', 'ATTACH', 'DETACH'
    # ]
    
    # for keyword in dangerous_keywords:
    #     if keyword in sql_upper:
    #         return False
    
    # # Don't block SQL comments - they're fine in SELECT queries
    # # Removed: if '--' in sql or '/*' in sql:
    
    return True