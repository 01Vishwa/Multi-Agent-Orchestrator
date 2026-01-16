"""
API URL Configuration
"""
from django.urls import path
from .views import (
    ChatView,
    DirectAgentQueryView,
    ChatHistoryView,
    HealthCheckView,
)

app_name = 'api'

urlpatterns = [
    # Main chat endpoint
    path('chat/', ChatView.as_view(), name='chat'),
    
    # Conversation history
    path('chat/history/<str:session_id>/', ChatHistoryView.as_view(), name='chat-history'),
    
    # Direct agent access (for debugging/testing)
    path('agents/query/', DirectAgentQueryView.as_view(), name='agent-query'),
    
    # Health check
    path('health/', HealthCheckView.as_view(), name='health'),
]
