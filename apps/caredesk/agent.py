"""
CareDesk Agent - Text-to-SQL for Customer Support Database

This agent handles queries related to:
- Support tickets and their status
- Ticket messages and history
- Customer satisfaction surveys
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
from .schemas import get_schema_prompt, CAREDESK_SCHEMA
from .models import Ticket, TicketMessage, SatisfactionSurvey

logger = logging.getLogger(__name__)


CAREDESK_SYSTEM_PROMPT = """You are a SQL expert for the CareDesk customer support database.
Your job is to convert natural language queries into safe, read-only SQL queries.

{schema}

IMPORTANT RULES:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, or DROP
2. Always use table aliases for clarity
3. Use proper JOINs when combining tables
4. Tickets can reference orders via reference_id where reference_type = 'order'
5. Table names: caredesk_tickets, caredesk_ticket_messages, caredesk_satisfaction_surveys
6. caredesk_tickets.user_id links to shopcore_users.id

When returning results, format as JSON:
{{
    "sql": "SELECT ...",
    "explanation": "Brief explanation of what this query does"
}}
"""


class CareDeSkAgent:
    """
    Text-to-SQL agent for CareDesk database.
    Handles: Tickets, TicketMessages, SatisfactionSurveys
    """
    
    def __init__(self):
        self.name = "caredesk"
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
        Execute a query against the CareDesk database.
        """
        logger.info(f"CareDesk agent executing: {query[:100]}")
        
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
            logger.error(f"Unexpected error in CareDesk agent: {e}")
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
        
        # Get IDs from context
        user_id = context.get('user_id')
        order_id = context.get('order_id')
        ticket_id = context.get('ticket_id')
        
        if context.get('shopcore_result'):
            shopcore_data = context['shopcore_result']
            if isinstance(shopcore_data, list) and len(shopcore_data) > 0:
                user_id = user_id or shopcore_data[0].get('user_id')
                order_id = order_id or shopcore_data[0].get('order_id')
        
        # Ticket status queries
        if any(word in query_lower for word in ['ticket', 'support', 'issue', 'help', 'assigned', 'agent']):
            tickets = Ticket.objects.all().order_by('-created_at')
            
            if ticket_id:
                tickets = tickets.filter(id=ticket_id)
            elif user_id:
                tickets = tickets.filter(user_id=user_id)
            elif order_id:
                tickets = tickets.filter(reference_id=order_id, reference_type='order')
            
            for ticket in tickets[:5]:
                # Get message count
                msg_count = TicketMessage.objects.filter(ticket=ticket).count()
                
                results.append({
                    'ticket_id': str(ticket.id),
                    'subject': ticket.subject,
                    'status': ticket.status,
                    'priority': ticket.priority,
                    'issue_type': ticket.issue_type,
                    'assigned_to': ticket.assigned_agent_name or 'Unassigned',
                    'created_at': ticket.created_at.isoformat(),
                    'reference_order': str(ticket.reference_id) if ticket.reference_type == 'order' else None,
                    'message_count': msg_count
                })
        
        # Ticket messages/conversation
        elif any(word in query_lower for word in ['message', 'conversation', 'reply', 'response']):
            if ticket_id:
                messages = TicketMessage.objects.filter(ticket_id=ticket_id).order_by('-created_at')[:10]
            elif user_id:
                tickets = Ticket.objects.filter(user_id=user_id)
                messages = TicketMessage.objects.filter(ticket__in=tickets).order_by('-created_at')[:10]
            else:
                messages = TicketMessage.objects.all().order_by('-created_at')[:10]
            
            for msg in messages:
                results.append({
                    'message_id': str(msg.id),
                    'ticket_id': str(msg.ticket_id),
                    'sender': msg.sender,
                    'sender_name': msg.sender_name,
                    'content': msg.content[:200] + '...' if len(msg.content) > 200 else msg.content,
                    'sent_at': msg.created_at.isoformat()
                })
        
        # Survey/feedback queries
        elif any(word in query_lower for word in ['survey', 'satisfaction', 'rating', 'feedback']):
            surveys = SatisfactionSurvey.objects.select_related('ticket').all()
            
            if ticket_id:
                surveys = surveys.filter(ticket_id=ticket_id)
            elif user_id:
                surveys = surveys.filter(ticket__user_id=user_id)
            
            for survey in surveys[:5]:
                results.append({
                    'survey_id': str(survey.id),
                    'ticket_id': str(survey.ticket_id),
                    'rating': survey.rating,
                    'would_recommend': survey.would_recommend,
                    'comments': survey.comments,
                    'submitted_at': survey.created_at.isoformat()
                })
        
        # Open/pending tickets
        elif any(word in query_lower for word in ['open', 'pending', 'active', 'waiting']):
            tickets = Ticket.objects.filter(status__in=['open', 'in_progress']).order_by('-created_at')
            
            if user_id:
                tickets = tickets.filter(user_id=user_id)
            
            for ticket in tickets[:5]:
                results.append({
                    'ticket_id': str(ticket.id),
                    'subject': ticket.subject,
                    'status': ticket.status,
                    'priority': ticket.priority,
                    'assigned_to': ticket.assigned_agent_name or 'Unassigned',
                    'created_at': ticket.created_at.isoformat()
                })
        
        # Default: show recent tickets
        else:
            tickets = Ticket.objects.all().order_by('-created_at')[:5]
            for ticket in tickets:
                results.append({
                    'ticket_id': str(ticket.id),
                    'subject': ticket.subject,
                    'status': ticket.status,
                    'issue_type': ticket.issue_type,
                    'assigned_to': ticket.assigned_agent_name or 'Unassigned',
                    'created_at': ticket.created_at.isoformat()
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
            context_parts.append(f"User ID to find tickets for: {context['user_id']}")
        if context.get('order_id'):
            context_parts.append(f"Order ID (can be used as reference_id): {context['order_id']}")
        if context.get('ticket_id'):
            context_parts.append(f"Ticket ID: {context['ticket_id']}")
        
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

Generate a SQL query to answer this question. Only query the caredesk_* tables.
"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=CAREDESK_SYSTEM_PROMPT.format(schema=self.schema_prompt)),
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
            "Find ticket status for an order",
            "Check if ticket is assigned to agent",
            "View ticket conversation history",
            "Get customer satisfaction rating",
            "List open tickets for a user",
        ]
