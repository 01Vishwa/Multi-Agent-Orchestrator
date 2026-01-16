"""
Utility functions for OmniLife Multi-Agent Orchestrator
"""
import re
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def sanitize_sql(sql: str) -> str:
    """
    Basic SQL sanitization to prevent dangerous operations.
    This is a safety layer - the ORM should be used when possible.
    """
    # Remove comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Check for dangerous keywords
    dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'INSERT', 'UPDATE', 'GRANT', 'REVOKE']
    sql_upper = sql.upper()
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            raise ValueError(f"Dangerous SQL keyword '{keyword}' detected")
    
    return sql.strip()


def extract_json_from_response(response: str) -> Optional[Dict]:
    """
    Extract JSON from an LLM response that may contain markdown code blocks.
    """
    # Try to find JSON in code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to parse the entire response as JSON
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass
    
    # Try to find a JSON object or array in the text
    patterns = [
        r'\{[\s\S]*\}',  # Object
        r'\[[\s\S]*\]',  # Array
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue
    
    return None


def format_agent_result(
    agent_name: str,
    data: Any,
    sql_query: Optional[str] = None,
    success: bool = True,
    error: Optional[str] = None
) -> Dict:
    """
    Format agent result into a standardized structure.
    """
    return {
        "agent_name": agent_name,
        "success": success,
        "data": data,
        "sql_query": sql_query,
        "error": error,
        "timestamp": datetime.utcnow().isoformat()
    }


def build_schema_context(tables: List[Dict]) -> str:
    """
    Build a schema context string for LLM prompts.
    """
    lines = ["Database Schema:"]
    for table in tables:
        table_name = table.get("name", "Unknown")
        columns = table.get("columns", [])
        
        column_defs = []
        for col in columns:
            col_def = f"{col['name']} ({col['type']})"
            if col.get('primary_key'):
                col_def += " [PK]"
            if col.get('foreign_key'):
                col_def += f" [FK -> {col['foreign_key']}]"
            column_defs.append(col_def)
        
        lines.append(f"\nTable: {table_name}")
        lines.append(f"  Columns: {', '.join(column_defs)}")
    
    return '\n'.join(lines)


def parse_user_context(user_id: Optional[str], session_data: Optional[Dict]) -> Dict:
    """
    Parse user context for enriching agent queries.
    """
    context = {
        "user_id": user_id,
        "has_session": session_data is not None,
    }
    
    if session_data:
        context.update({
            "previous_queries": session_data.get("queries", [])[-5:],  # Last 5 queries
            "known_entities": session_data.get("entities", {}),
        })
    
    return context


def truncate_for_display(text: str, max_length: int = 100) -> str:
    """
    Truncate text for display purposes.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
