"""
PayGuard Agent - Text-to-SQL for FinTech Database

This agent handles queries related to:
- Wallet balances and management
- Transaction history
- Refunds and payment issues
"""
import json
import logging
import re
from typing import Dict, List, Any, Optional

from django.db import connection
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from django.conf import settings
from apps.core.utils import sanitize_sql, extract_json_from_response
from apps.core.exceptions import SQLGenerationException, SQLExecutionException
from .schemas import get_schema_prompt, PAYGUARD_SCHEMA
from .models import Wallet, Transaction, PaymentMethod

logger = logging.getLogger(__name__)


PAYGUARD_SYSTEM_PROMPT = """You are a SQL expert for the PayGuard FinTech database.
Your job is to convert natural language queries into safe, read-only SQL queries.

{schema}

IMPORTANT RULES:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, or DROP
2. Always use table aliases for clarity
3. Use proper JOINs when combining tables
4. For refund queries, look for transaction_type = 'refund'
5. Table names: payguard_wallets, payguard_transactions, payguard_payment_methods
6. payguard_wallets.user_id links to shopcore_users.id

When returning results, format as JSON:
{{
    "sql": "SELECT ...",
    "explanation": "Brief explanation of what this query does"
}}
"""


class PayGuardAgent:
    """
    Text-to-SQL agent for PayGuard database.
    Handles: Wallets, Transactions, PaymentMethods
    """
    
    def __init__(self):
        self.name = "payguard"
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.GITHUB_TOKEN,
            base_url=settings.LLM_BASE_URL,
            temperature=0,
        )
        self.schema_prompt = get_schema_prompt()
    
    def execute(
        self,
        query: str,
        context: Dict[str, Any],
        entities: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute a query against the PayGuard database.
        """
        logger.info(f"PayGuard agent executing: {query[:100]}")
        
        try:
            # Try LLM-generated SQL first
            sql_query = self._generate_sql(query, context, entities)
            
            if sql_query:
                try:
                    results = self._execute_sql(sql_query)
                    if results:
                        return {
                            "success": True,
                            "data": results,
                            "sql_query": sql_query,
                            "error": None
                        }
                except Exception as e:
                    logger.warning(f"SQL execution failed, trying ORM fallback: {e}")
            
            # Fallback to ORM-based queries
            results = self._orm_fallback(query, context, entities)
            
            return {
                "success": True,
                "data": results,
                "sql_query": "ORM Query",
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Unexpected error in PayGuard agent: {e}")
            return {
                "success": False,
                "data": {},
                "sql_query": None,
                "error": str(e)
            }
    
    def _orm_fallback(self, query: str, context: Dict[str, Any], entities: List[Dict] = None) -> List[Dict]:
        """
        Fallback to Django ORM for common query patterns.
        """
        query_lower = query.lower()
        results = []
        
        # Get user_id from context
        user_id = context.get('user_id')
        order_id = context.get('order_id')
        
        if not user_id and context.get('shopcore_result'):
            shopcore_data = context['shopcore_result']
            if isinstance(shopcore_data, list) and len(shopcore_data) > 0:
                user_id = shopcore_data[0].get('user_id')
                order_id = order_id or shopcore_data[0].get('order_id')
        
        # Refund queries
        if any(word in query_lower for word in ['refund', 'returned', 'return']):
            transactions = Transaction.objects.filter(transaction_type='refund').select_related('wallet')
            
            if order_id:
                transactions = transactions.filter(order_id=order_id)
            elif user_id:
                transactions = transactions.filter(wallet__user_id=user_id)
            
            for trans in transactions[:5]:
                results.append({
                    'transaction_id': str(trans.id),
                    'type': trans.transaction_type,
                    'status': trans.status,
                    'amount': str(trans.amount),
                    'order_id': str(trans.order_id) if trans.order_id else None,
                    'date': trans.created_at.isoformat(),
                    'reference': trans.reference_number
                })
        
        # Wallet balance queries
        elif any(word in query_lower for word in ['wallet', 'balance', 'available']):
            wallets = Wallet.objects.all()
            
            if user_id:
                wallets = wallets.filter(user_id=user_id)
            
            for wallet in wallets[:5]:
                results.append({
                    'wallet_id': str(wallet.id),
                    'user_id': str(wallet.user_id),
                    'balance': str(wallet.balance),
                    'currency': wallet.currency,
                    'active': wallet.is_active
                })
        
        # Transaction history queries
        elif any(word in query_lower for word in ['transaction', 'history', 'payment', 'recent']):
            transactions = Transaction.objects.select_related('wallet').order_by('-created_at')
            
            if user_id:
                transactions = transactions.filter(wallet__user_id=user_id)
            if order_id:
                transactions = transactions.filter(order_id=order_id)
            
            for trans in transactions[:5]:
                results.append({
                    'transaction_id': str(trans.id),
                    'type': trans.transaction_type,
                    'status': trans.status,
                    'amount': str(trans.amount),
                    'description': trans.description,
                    'date': trans.created_at.isoformat(),
                    'reference': trans.reference_number
                })
        
        # Payment methods
        elif any(word in query_lower for word in ['card', 'payment method', 'credit', 'debit']):
            methods = PaymentMethod.objects.select_related('wallet').filter(is_active=True)
            
            if user_id:
                methods = methods.filter(wallet__user_id=user_id)
            
            for method in methods[:5]:
                results.append({
                    'method_id': str(method.id),
                    'provider': method.provider,
                    'last_four': method.last_four_digits,
                    'nickname': method.nickname,
                    'is_default': method.is_default,
                    'expiry': method.expiry_date.isoformat() if method.expiry_date else None
                })
        
        # Default: show recent transactions
        else:
            transactions = Transaction.objects.select_related('wallet').order_by('-created_at')[:5]
            for trans in transactions:
                results.append({
                    'transaction_id': str(trans.id),
                    'type': trans.transaction_type,
                    'status': trans.status,
                    'amount': str(trans.amount),
                    'date': trans.created_at.isoformat()
                })
        
        return results
    
    def _generate_sql(
        self,
        query: str,
        context: Dict[str, Any],
        entities: List[Dict] = None
    ) -> Optional[str]:
        """Generate SQL from natural language using LLM."""
        context_parts = []
        
        if context.get('user_id'):
            context_parts.append(f"User ID to look up wallet for: {context['user_id']}")
        if context.get('order_id'):
            context_parts.append(f"Order ID to find transactions for: {context['order_id']}")
        
        if context.get('shopcore_result'):
            shopcore_data = context['shopcore_result']
            if isinstance(shopcore_data, list) and len(shopcore_data) > 0:
                order_info = shopcore_data[0]
                if 'user_id' in order_info:
                    context_parts.append(f"User ID from ShopCore: {order_info['user_id']}")
                if 'order_id' in order_info:
                    context_parts.append(f"Order ID from ShopCore: {order_info['order_id']}")
        
        if entities:
            for entity in entities:
                context_parts.append(f"{entity.get('entity_type', 'Entity')}: {entity.get('value', '')}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context"
        
        user_prompt = f"""Query: {query}

Context from other systems:
{context_str}

Generate a SQL query to answer this question. Only query the payguard_* tables.
"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=PAYGUARD_SYSTEM_PROMPT.format(schema=self.schema_prompt)),
                HumanMessage(content=user_prompt)
            ])
            
            result = extract_json_from_response(response.content)
            
            if result and 'sql' in result:
                sql = result['sql']
            else:
                sql_match = re.search(r'SELECT[^;]+', response.content, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    sql = sql_match.group(0)
                else:
                    return None
            
            sql = sanitize_sql(sql)
            logger.info(f"Generated SQL: {sql}")
            return sql
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return None
    
    def _execute_sql(self, sql: str) -> List[Dict]:
        """Execute SQL query safely and return results."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    result = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        elif hasattr(value, '__str__'):
                            value = str(value)
                        result[col] = value
                    results.append(result)
                
                logger.info(f"SQL returned {len(results)} rows")
                return results
                
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            raise SQLExecutionException(self.name, sql, str(e))
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities this agent supports."""
        return [
            "Check wallet balance",
            "View transaction history",
            "Check refund status for an order",
            "List payment methods",
            "Find failed transactions",
        ]
