"""
ShipStream Agent - Text-to-SQL for Logistics Database

This agent handles queries related to:
- Shipment tracking and status
- Warehouse information
- Delivery events and history
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
from .schemas import get_schema_prompt, SHIPSTREAM_SCHEMA
from .models import Shipment, Warehouse, TrackingEvent

logger = logging.getLogger(__name__)


SHIPSTREAM_SYSTEM_PROMPT = """You are a SQL expert for the ShipStream logistics database.
Your job is to convert natural language queries into safe, read-only SQL queries.

{schema}

IMPORTANT RULES:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, or DROP
2. Always use table aliases for clarity
3. Use proper JOINs when combining tables
4. Order tracking events by timestamp DESC to show most recent first
5. Table names: shipstream_shipments, shipstream_warehouses, shipstream_tracking_events
6. shipstream_shipments.order_id links to shopcore_orders.id

When returning results, format as JSON:
{{
    "sql": "SELECT ...",
    "explanation": "Brief explanation of what this query does"
}}
"""


class ShipStreamAgent:
    """
    Text-to-SQL agent for ShipStream database.
    Handles: Shipments, Warehouses, TrackingEvents
    """
    
    def __init__(self):
        self.name = "shipstream"
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
        Execute a query against the ShipStream database.
        """
        logger.info(f"ShipStream agent executing: {query[:100]}")
        
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
            logger.error(f"Unexpected error in ShipStream agent: {e}")
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
        
        # Get order_id from context (from ShopCore results)
        order_id = context.get('order_id')
        if not order_id and context.get('shopcore_result'):
            shopcore_data = context['shopcore_result']
            if isinstance(shopcore_data, list) and len(shopcore_data) > 0:
                order_id = shopcore_data[0].get('order_id') or shopcore_data[0].get('id')
        
        # Tracking/shipment queries
        if any(word in query_lower for word in ['track', 'where', 'shipment', 'delivery', 'package', 'arrive', 'delayed']):
            shipments = Shipment.objects.select_related('current_warehouse').all()
            
            if order_id:
                shipments = shipments.filter(order_id=order_id)
            
            for shipment in shipments[:5]:
                # Get latest tracking event
                latest_event = TrackingEvent.objects.filter(shipment=shipment).order_by('-timestamp').first()
                
                results.append({
                    'shipment_id': str(shipment.id),
                    'order_id': str(shipment.order_id),
                    'tracking_number': shipment.tracking_number,
                    'status': shipment.current_status,
                    'estimated_arrival': shipment.estimated_arrival.isoformat() if shipment.estimated_arrival else None,
                    'current_location': shipment.current_warehouse.location if shipment.current_warehouse else 'In Transit',
                    'warehouse': shipment.current_warehouse.name if shipment.current_warehouse else None,
                    'latest_update': latest_event.status_update if latest_event else None,
                    'latest_event_time': latest_event.timestamp.isoformat() if latest_event else None
                })
        
        # Tracking history
        elif any(word in query_lower for word in ['history', 'events', 'journey']):
            if order_id:
                shipment = Shipment.objects.filter(order_id=order_id).first()
                if shipment:
                    events = TrackingEvent.objects.filter(shipment=shipment).order_by('-timestamp')[:10]
                    for event in events:
                        results.append({
                            'timestamp': event.timestamp.isoformat(),
                            'status': event.status_update,
                            'location': event.location or (event.warehouse.location if event.warehouse else 'Unknown'),
                            'description': event.description
                        })
        
        # Warehouse info
        elif any(word in query_lower for word in ['warehouse', 'hub', 'facility']):
            warehouses = Warehouse.objects.all()[:5]
            for wh in warehouses:
                results.append({
                    'warehouse_id': str(wh.id),
                    'name': wh.name,
                    'location': wh.location,
                    'region': wh.region,
                    'manager': wh.manager_name
                })
        
        # Default: show recent shipments
        else:
            shipments = Shipment.objects.select_related('current_warehouse').order_by('-created_at')[:5]
            for shipment in shipments:
                results.append({
                    'tracking_number': shipment.tracking_number,
                    'order_id': str(shipment.order_id),
                    'status': shipment.current_status,
                    'location': shipment.current_warehouse.location if shipment.current_warehouse else 'In Transit',
                    'estimated_arrival': shipment.estimated_arrival.isoformat() if shipment.estimated_arrival else None
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
        
        if context.get('order_id'):
            context_parts.append(f"Order ID to look up shipment for: {context['order_id']}")
        if context.get('tracking_number'):
            context_parts.append(f"Tracking Number: {context['tracking_number']}")
        if context.get('shopcore_result'):
            shopcore_data = context['shopcore_result']
            if isinstance(shopcore_data, list) and len(shopcore_data) > 0:
                order_info = shopcore_data[0]
                if 'order_id' in order_info:
                    context_parts.append(f"Order ID from ShopCore: {order_info['order_id']}")
                elif 'id' in order_info:
                    context_parts.append(f"Order ID from ShopCore: {order_info['id']}")
        
        if entities:
            for entity in entities:
                context_parts.append(f"{entity.get('entity_type', 'Entity')}: {entity.get('value', '')}")
        
        context_str = "\n".join(context_parts) if context_parts else "No additional context"
        
        user_prompt = f"""Query: {query}

Context from other systems:
{context_str}

Generate a SQL query to answer this question. Only query the shipstream_* tables.
"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=SHIPSTREAM_SYSTEM_PROMPT.format(schema=self.schema_prompt)),
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
            "Track shipment by order ID or tracking number",
            "Get current package location",
            "View delivery history and events",
            "Check estimated arrival time",
            "Find package at specific warehouse",
        ]
