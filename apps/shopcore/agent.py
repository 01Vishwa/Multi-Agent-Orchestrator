"""
ShopCore Agent - Text-to-SQL for E-commerce Database

This agent handles queries related to:
- User accounts and profiles
- Product catalog and information
- Order placement and status
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
from .schemas import get_schema_prompt, SHOPCORE_SCHEMA
from .models import User, Product, Order

logger = logging.getLogger(__name__)


SHOPCORE_SYSTEM_PROMPT = """You are a SQL expert for the ShopCore e-commerce database.
Your job is to convert natural language queries into safe, read-only SQL queries.

{schema}

IMPORTANT RULES:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, or DROP
2. Always use table aliases for clarity
3. Use proper JOINs when combining tables
4. Limit results to 10 rows unless specified otherwise
5. The table names are: shopcore_users, shopcore_products, shopcore_orders
6. For Orders table: user_id is a foreign key, product_id is a foreign key
7. Search product names with LIKE '%keyword%' for partial matches

When returning results, format as JSON:
{{
    "sql": "SELECT ...",
    "explanation": "Brief explanation of what this query does"
}}
"""


class ShopCoreAgent:
    """
    Text-to-SQL agent for ShopCore database.
    Handles: Users, Products, Orders
    """
    
    def __init__(self):
        self.name = "shopcore"
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
        Execute a query against the ShopCore database.
        """
        logger.info(f"ShopCore agent executing: {query[:100]}")
        
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
            logger.error(f"Unexpected error in ShopCore agent: {e}")
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
        
        # Extract product names from query
        product_keywords = []
        common_products = ['gaming monitor', 'laptop', 'headphones', 'keyboard', 'mouse', 
                          'speaker', 'webcam', 'phone', 'tablet', 'watch', 'tv', 'monitor']
        for product in common_products:
            if product in query_lower:
                product_keywords.append(product)
        
        # Order-related queries
        if any(word in query_lower for word in ['order', 'ordered', 'bought', 'purchase']):
            orders = Order.objects.select_related('user', 'product').all()[:10]
            
            # Filter by product if mentioned
            if product_keywords:
                for keyword in product_keywords:
                    orders = orders.filter(product__name__icontains=keyword)
            
            # Filter by user if context has user_id
            if context.get('user_id'):
                orders = orders.filter(user_id=context['user_id'])
            
            for order in orders[:5]:
                results.append({
                    'order_id': str(order.id),
                    'user_id': str(order.user_id),
                    'user_name': order.user.name,
                    'product_name': order.product.name,
                    'product_id': str(order.product_id),
                    'order_date': order.order_date.isoformat(),
                    'status': order.status,
                    'total_amount': str(order.total_amount)
                })
        
        # Product search
        elif any(word in query_lower for word in ['product', 'find', 'search', 'show']):
            products = Product.objects.all()
            
            if product_keywords:
                for keyword in product_keywords:
                    products = products.filter(name__icontains=keyword)
            
            for product in products[:5]:
                results.append({
                    'product_id': str(product.id),
                    'name': product.name,
                    'category': product.category,
                    'price': str(product.price),
                    'stock': product.stock_quantity
                })
        
        # User info
        elif any(word in query_lower for word in ['user', 'account', 'profile', 'customer']):
            if context.get('user_id'):
                users = User.objects.filter(id=context['user_id'])
            else:
                users = User.objects.all()[:5]
            
            for user in users:
                results.append({
                    'user_id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'premium': user.premium_status
                })
        
        # Default: return recent orders
        else:
            orders = Order.objects.select_related('user', 'product').order_by('-order_date')[:5]
            for order in orders:
                results.append({
                    'order_id': str(order.id),
                    'user_name': order.user.name,
                    'product_name': order.product.name,
                    'status': order.status,
                    'order_date': order.order_date.isoformat()
                })
        
        return results
    
    def _generate_sql(
        self,
        query: str,
        context: Dict[str, Any],
        entities: List[Dict] = None
    ) -> Optional[str]:
        """
        Generate SQL from natural language using LLM.
        """
        context_parts = []
        if context.get('user_id'):
            context_parts.append(f"User ID: {context['user_id']}")
        if context.get('order_id'):
            context_parts.append(f"Order ID: {context['order_id']}")
        
        if entities:
            for entity in entities:
                context_parts.append(f"{entity.get('entity_type', 'Entity')}: {entity.get('value', '')}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context"
        
        user_prompt = f"""Query: {query}

Context:
{context_str}

Generate a SQL query to answer this question. Only query the shopcore_* tables.
Remember: table names are shopcore_users, shopcore_products, shopcore_orders.
"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=SHOPCORE_SYSTEM_PROMPT.format(schema=self.schema_prompt)),
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
        """
        Execute SQL query safely and return results.
        """
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
            "Find orders by user or product",
            "Get order status and details",
            "Search products by name or category",
            "Look up user information",
            "List recent orders",
        ]
