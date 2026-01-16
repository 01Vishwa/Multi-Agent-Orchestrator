"""
API Views for OmniLife Multi-Agent Orchestrator

This module provides REST API endpoints for:
- Chat: Main conversation endpoint with multi-agent orchestration
- Direct Query: Direct access to individual agents
- Health Check: System health and status
- Conversation History: Retrieve past conversations
"""
import uuid
import time
import logging
from datetime import datetime

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample

from django.conf import settings
from django.db import connection

from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    DirectQueryRequestSerializer,
    DirectQueryResponseSerializer,
    HealthCheckSerializer,
    ConversationHistorySerializer,
)
from apps.orchestrator.graph import OrchestratorService

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """
    Main chat endpoint for customer queries.
    
    This endpoint accepts natural language queries and routes them
    through the multi-agent orchestration system to provide unified
    responses from across all OmniLife products.
    """
    permission_classes = [AllowAny]  # Adjust based on auth requirements
    
    @extend_schema(
        request=ChatRequestSerializer,
        responses={200: ChatResponseSerializer},
        description="Process a customer query through the multi-agent orchestrator",
        examples=[
            OpenApiExample(
                "Order Status Query",
                value={
                    "message": "Where is my order for the Gaming Monitor?",
                    "session_id": "session-123",
                    "user_id": "user-456"
                },
                request_only=True
            ),
            OpenApiExample(
                "Successful Response",
                value={
                    "response": "Your Gaming Monitor order (ORD-12345) is currently at the Mumbai Distribution Hub and is expected to arrive tomorrow.",
                    "session_id": "session-123",
                    "agents_used": ["shopcore", "shipstream"],
                    "success": True,
                    "intent": "delivery_tracking",
                    "intent_confidence": 0.95
                },
                response_only=True
            ),
        ]
    )
    def post(self, request):
        """
        Process a customer query.
        """
        serializer = ChatRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        message = data['message']
        session_id = data.get('session_id') or str(uuid.uuid4())
        user_id = data.get('user_id')
        include_debug = data.get('include_debug', False)
        
        logger.info(f"Chat request - Session: {session_id}, Message: {message[:100]}...")
        
        try:
            # Initialize orchestrator and process query
            orchestrator = OrchestratorService()
            result = orchestrator.process_query(
                query=message,
                session_id=session_id,
                user_id=user_id,
                conversation_history=[]  # TODO: Load from storage
            )
            
            # Build response
            response_data = {
                "response": result['response'],
                "session_id": session_id,
                "agents_used": result['agents_used'],
                "success": result['success'],
                "intent": result.get('intent'),
                "intent_confidence": result.get('intent_confidence', 0),
            }
            
            # Include debug info if requested
            if include_debug:
                response_data["execution_details"] = result.get('execution_details', {})
                response_data["error"] = result.get('error')
            
            logger.info(f"Chat response - Agents used: {result['agents_used']}, Success: {result['success']}")
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error processing chat request: {e}")
            return Response(
                {
                    "response": "I apologize, but I encountered an error processing your request. Please try again.",
                    "session_id": session_id,
                    "agents_used": [],
                    "success": False,
                    "intent": None,
                    "intent_confidence": 0,
                    "error": str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DirectAgentQueryView(APIView):
    """
    Direct access to individual agents for debugging or specialized queries.
    
    This endpoint bypasses the orchestrator and queries a specific agent directly.
    Useful for testing or when you know exactly which agent you need.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=DirectQueryRequestSerializer,
        responses={200: DirectQueryResponseSerializer},
        description="Query a specific agent directly"
    )
    def post(self, request):
        """
        Execute a direct query against a specific agent.
        """
        serializer = DirectQueryRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid request", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = serializer.validated_data
        agent_name = data['agent']
        query = data['query']
        context = data.get('context', {})
        
        logger.info(f"Direct query to {agent_name}: {query[:100]}...")
        
        try:
            # Import and instantiate the appropriate agent
            if agent_name == 'shopcore':
                from apps.shopcore.agent import ShopCoreAgent
                agent = ShopCoreAgent()
            elif agent_name == 'shipstream':
                from apps.shipstream.agent import ShipStreamAgent
                agent = ShipStreamAgent()
            elif agent_name == 'payguard':
                from apps.payguard.agent import PayGuardAgent
                agent = PayGuardAgent()
            elif agent_name == 'caredesk':
                from apps.caredesk.agent import CareDeSkAgent
                agent = CareDeSkAgent()
            else:
                return Response(
                    {"error": f"Unknown agent: {agent_name}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Execute the query
            start_time = time.time()
            result = agent.execute(query=query, context=context, entities=[])
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            response_data = {
                "agent": agent_name,
                "success": result['success'],
                "data": result['data'],
                "sql_query": result.get('sql_query'),
                "error": result.get('error'),
                "execution_time_ms": execution_time_ms
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in direct agent query: {e}")
            return Response(
                {
                    "agent": agent_name,
                    "success": False,
                    "data": {},
                    "sql_query": None,
                    "error": str(e),
                    "execution_time_ms": 0
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatHistoryView(APIView):
    """
    Retrieve conversation history for a session.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: ConversationHistorySerializer(many=True)},
        description="Get conversation history for a session"
    )
    def get(self, request, session_id):
        """
        Get the conversation history for a given session.
        """
        # TODO: Implement actual history retrieval from storage
        # For now, return empty list
        logger.info(f"Fetching history for session: {session_id}")
        
        return Response([], status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """
    System health check endpoint.
    
    Returns the status of the API, database connectivity,
    and agent readiness.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        responses={200: HealthCheckSerializer},
        description="Check system health status"
    )
    def get(self, request):
        """
        Check system health.
        """
        # Check database connectivity
        db_status = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        # Check agents
        agents_status = {}
        agent_classes = [
            ('shopcore', 'apps.shopcore.agent', 'ShopCoreAgent'),
            ('shipstream', 'apps.shipstream.agent', 'ShipStreamAgent'),
            ('payguard', 'apps.payguard.agent', 'PayGuardAgent'),
            ('caredesk', 'apps.caredesk.agent', 'CareDeSkAgent'),
        ]
        
        for name, module, class_name in agent_classes:
            try:
                exec(f"from {module} import {class_name}")
                agents_status[name] = "ready"
            except Exception as e:
                agents_status[name] = f"error: {str(e)}"
        
        # Check LLM configuration (GitHub Models API)
        llm_status = "configured" if settings.GITHUB_TOKEN else "not configured"
        
        response_data = {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "version": "1.0.0",
            "database": db_status,
            "llm": llm_status,
            "agents": agents_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
